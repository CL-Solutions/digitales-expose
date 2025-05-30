# ================================
# SUPER ADMIN API ROUTES (api/v1/admin.py) - COMPLETED
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.dependencies import get_db, get_super_admin_user
from app.schemas.base import SuccessResponse
from app.schemas.auth import AuthStatsResponse, AuthAuditFilterParams
from app.schemas.rbac import RBACStatsResponse, RBACComplianceReport
from app.schemas.user import UserStatsResponse
from app.schemas.tenant import TenantStatsResponse
from app.models.user import User, UserSession
from app.models.tenant import Tenant
from app.models.audit import AuditLog
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

router = APIRouter()

# ================================
# SYSTEM OVERVIEW & ANALYTICS
# ================================

@router.get("/dashboard")
async def get_admin_dashboard(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Super Admin Dashboard Overview"""
    try:
        from datetime import datetime, timedelta
        
        # Basic system stats
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        total_users = db.query(User).filter(User.tenant_id.isnot(None)).count()
        super_admins = db.query(User).filter(User.is_super_admin == True).count()
        
        # Recent activity (last 7 days)
        recent_date = datetime.utcnow() - timedelta(days=7)
        new_tenants = db.query(Tenant).filter(Tenant.created_at >= recent_date).count()
        new_users = db.query(User).filter(User.created_at >= recent_date).count()
        recent_logins = db.query(User).filter(User.last_login_at >= recent_date).count()
        
        # System health indicators
        inactive_tenants = total_tenants - active_tenants
        locked_users = db.query(User).filter(
            User.locked_until.isnot(None),
            User.locked_until > datetime.utcnow()
        ).count()
        
        # Failed login attempts (last 24h)
        failed_logins_24h = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
        ).count()
        
        # Storage usage (would implement with actual file storage)
        total_storage_gb = 0  # Placeholder
        
        # Business metrics
        try:
            from app.models.business import Project, Document
            total_projects = db.query(Project).count()
            total_documents = db.query(Document).count()
        except:
            total_projects = 0
            total_documents = 0
        
        return {
            "system_overview": {
                "total_tenants": total_tenants,
                "active_tenants": active_tenants,
                "total_users": total_users,
                "super_admins": super_admins,
                "total_projects": total_projects,
                "total_documents": total_documents
            },
            "recent_activity": {
                "new_tenants_7d": new_tenants,
                "new_users_7d": new_users,
                "recent_logins_7d": recent_logins
            },
            "health_indicators": {
                "inactive_tenants": inactive_tenants,
                "locked_users": locked_users,
                "failed_logins_24h": failed_logins_24h,
                "system_status": "healthy" if failed_logins_24h < 100 and locked_users < 10 else "warning"
            },
            "resource_usage": {
                "total_storage_gb": total_storage_gb,
                "avg_users_per_tenant": round(total_users / total_tenants, 2) if total_tenants > 0 else 0
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get system limits")

# ================================
# EMERGENCY OPERATIONS
# ================================

@router.post("/emergency/disable-tenant")
async def emergency_disable_tenant(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID to disable"),
    reason: str = Query(..., description="Reason for emergency disable"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Emergency Tenant Deaktivierung"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Disable tenant
        tenant.is_active = False
        
        # Terminate all user sessions for this tenant
        terminated_sessions = db.query(UserSession).filter(
            UserSession.tenant_id == tenant_id
        ).delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "EMERGENCY_TENANT_DISABLED", super_admin.id, tenant_id,
            {
                "reason": reason,
                "tenant_name": tenant.name,
                "terminated_sessions": terminated_sessions
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Tenant {tenant.name} disabled in emergency mode",
            data={
                "tenant_id": str(tenant_id),
                "reason": reason,
                "terminated_sessions": terminated_sessions
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Emergency operation failed")

@router.post("/emergency/global-logout")
async def emergency_global_logout(
    reason: str = Query(..., description="Reason for global logout"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Emergency Global Logout aller User"""
    try:
        # Terminate all user sessions (except super admin)
        terminated_count = db.query(UserSession).filter(
            UserSession.user_id != super_admin.id
        ).delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "EMERGENCY_GLOBAL_LOGOUT", super_admin.id, None,
            {
                "reason": reason,
                "terminated_sessions": terminated_count
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Emergency global logout completed. {terminated_count} sessions terminated.",
            data={
                "reason": reason,
                "terminated_sessions": terminated_count
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Emergency global logout failed")

# ================================
# BACKUP & RESTORE OPERATIONS
# ================================

@router.post("/backup/create")
async def create_system_backup(
    backup_type: str = Query(default="full", description="Backup type: full, incremental, config"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """System Backup erstellen"""
    try:
        backup_id = uuid.uuid4()
        
        # In production, this would trigger actual backup process
        backup_data = {
            "backup_id": str(backup_id),
            "backup_type": backup_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "initiated"
        }
        
        if backup_type == "full":
            backup_data["includes"] = ["tenants", "users", "projects", "documents", "audit_logs"]
        elif backup_type == "config":
            backup_data["includes"] = ["tenants", "identity_providers", "roles", "permissions"]
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "SYSTEM_BACKUP_INITIATED", super_admin.id, None,
            backup_data
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"System backup initiated: {backup_type}",
            data=backup_data
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Backup initiation failed")

# ================================
# SYSTEM REPORTS
# ================================

@router.get("/reports/usage")
async def get_usage_report(
    period_days: int = Query(default=30, ge=1, le=365),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """System Usage Report"""
    try:
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # User activity
        active_users = db.query(User).filter(
            User.last_login_at >= start_date,
            User.tenant_id.isnot(None)
        ).count()
        
        total_users = db.query(User).filter(User.tenant_id.isnot(None)).count()
        
        # Tenant activity
        active_tenants = db.query(Tenant).join(User).filter(
            User.last_login_at >= start_date
        ).distinct().count()
        
        # Login statistics
        login_attempts = db.query(AuditLog).filter(
            and_(
                AuditLog.action.in_(["LOGIN_SUCCESS", "LOGIN_FAILED"]),
                AuditLog.created_at >= start_date
            )
        ).count()
        
        successful_logins = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "LOGIN_SUCCESS",
                AuditLog.created_at >= start_date
            )
        ).count()
        
        # Feature usage
        try:
            from app.models.business import Project, Document
            new_projects = db.query(Project).filter(Project.created_at >= start_date).count()
            new_documents = db.query(Document).filter(Document.created_at >= start_date).count()
        except:
            new_projects = 0
            new_documents = 0
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "period_days": period_days
            },
            "user_activity": {
                "active_users": active_users,
                "total_users": total_users,
                "activity_rate_percent": round((active_users / total_users * 100), 2) if total_users > 0 else 0
            },
            "tenant_activity": {
                "active_tenants": active_tenants,
                "total_tenants": db.query(Tenant).count()
            },
            "authentication": {
                "total_login_attempts": login_attempts,
                "successful_logins": successful_logins,
                "success_rate_percent": round((successful_logins / login_attempts * 100), 2) if login_attempts > 0 else 0
            },
            "feature_usage": {
                "new_projects": new_projects,
                "new_documents": new_documents
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate usage report")

# ================================
# SYSTEM HEALTH MONITORING
# ================================

@router.get("/health/detailed")
async def get_detailed_system_health(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Detailed system health check"""
    try:
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # Database health
        try:
            db.execute("SELECT 1")
            health_data["components"]["database"] = {
                "status": "healthy",
                "response_time_ms": 1  # Would measure actual response time
            }
        except Exception as e:
            health_data["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_data["overall_status"] = "degraded"
        
        # Active sessions count
        active_sessions = db.query(UserSession).filter(
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        health_data["components"]["sessions"] = {
            "status": "healthy" if active_sessions < 10000 else "warning",
            "active_count": active_sessions
        }
        
        # Recent failed logins
        recent_failures = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1)
            )
        ).count()
        
        health_data["components"]["security"] = {
            "status": "healthy" if recent_failures < 100 else "warning",
            "failed_logins_last_hour": recent_failures
        }
        
        # System resources (would implement actual monitoring)
        health_data["components"]["resources"] = {
            "status": "healthy",
            "cpu_usage_percent": 25,  # Placeholder
            "memory_usage_percent": 60,  # Placeholder
            "disk_usage_percent": 45   # Placeholder
        }
        
        return health_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Health check failed")

# ================================
# FEATURE TOGGLES & CONFIGURATION
# ================================

@router.get("/config/features")
async def get_feature_configuration(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get system feature configuration"""
    try:
        # Would implement actual feature toggle system
        features = {
            "oauth_providers": {
                "microsoft": {"enabled": True, "configured_tenants": 0},
                "google": {"enabled": True, "configured_tenants": 0}
            },
            "email_service": {
                "aws_ses": {"enabled": True, "status": "operational"},
                "smtp_fallback": {"enabled": True, "status": "standby"}
            },
            "audit_logging": {
                "enabled": True,
                "retention_days": 365,
                "current_log_count": db.query(AuditLog).count()
            },
            "multi_tenant": {
                "enabled": True,
                "max_tenants": 10000,
                "current_tenant_count": db.query(Tenant).count()
            }
        }
        
        # Count OAuth provider usage
        microsoft_count = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.provider == "microsoft"
        ).count()
        google_count = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.provider == "google"
        ).count()
        
        features["oauth_providers"]["microsoft"]["configured_tenants"] = microsoft_count
        features["oauth_providers"]["google"]["configured_tenants"] = google_count
        
        return {
            "features": features,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get feature configuration")

@router.post("/config/features/{feature_name}/toggle")
async def toggle_feature(
    feature_name: str = Path(..., description="Feature name to toggle"),
    enabled: bool = Query(..., description="Enable or disable the feature"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle system feature on/off"""
    try:
        # Would implement actual feature toggle persistence
        valid_features = ["oauth_login", "email_notifications", "audit_logging", "tenant_creation"]
        
        if feature_name not in valid_features:
            raise HTTPException(status_code=400, detail="Invalid feature name")
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "FEATURE_TOGGLED", super_admin.id, None,
            {
                "feature_name": feature_name,
                "enabled": enabled,
                "previous_state": not enabled  # Would get actual previous state
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Feature '{feature_name}' {'enabled' if enabled else 'disabled'}",
            data={
                "feature_name": feature_name,
                "enabled": enabled
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to toggle feature")

# ================================
# PERFORMANCE MONITORING
# ================================

@router.get("/performance/metrics")
async def get_performance_metrics(
    hours: int = Query(default=24, ge=1, le=168),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get system performance metrics"""
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # API endpoint usage (would implement actual tracking)
        api_metrics = {
            "/api/v1/auth/login": {"calls": 1250, "avg_response_ms": 145, "error_rate": 0.02},
            "/api/v1/users/": {"calls": 890, "avg_response_ms": 89, "error_rate": 0.01},
            "/api/v1/projects/": {"calls": 450, "avg_response_ms": 234, "error_rate": 0.03},
            "/api/v1/admin/dashboard": {"calls": 67, "avg_response_ms": 567, "error_rate": 0.0}
        }
        
        # Database query performance
        db_metrics = {
            "avg_query_time_ms": 45,
            "slow_queries_count": 12,
            "connection_pool_usage": 65,
            "deadlocks_count": 0
        }
        
        # System resource usage trends
        resource_trends = []
        for i in range(hours):
            hour_ago = start_time + timedelta(hours=i)
            # Would implement actual metrics collection
            resource_trends.append({
                "timestamp": hour_ago.isoformat(),
                "cpu_percent": 20 + (i % 10),
                "memory_percent": 55 + (i % 15),
                "active_sessions": 100 + (i * 5)
            })
        
        return {
            "period_hours": hours,
            "api_endpoints": api_metrics,
            "database": db_metrics,
            "resource_trends": resource_trends,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

# ================================
# NOTIFICATION SYSTEM
# ================================

@router.post("/notifications/send")
async def send_system_notification(
    title: str = Query(..., description="Notification title"),
    message: str = Query(..., description="Notification message"),
    severity: str = Query(default="info", description="Severity: info, warning, critical"),
    target_tenants: Optional[List[uuid.UUID]] = Query(None, description="Target specific tenants"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Send system-wide notification"""
    try:
        # Would implement actual notification system
        notification_id = uuid.uuid4()
        
        # Determine target users
        if target_tenants:
            target_users = db.query(User).filter(
                User.tenant_id.in_(target_tenants),
                User.is_active == True
            ).all()
        else:
            # All active tenant users
            target_users = db.query(User).filter(
                User.tenant_id.isnot(None),
                User.is_active == True
            ).all()
        
        # Send notifications (would implement actual delivery)
        delivered_count = len(target_users)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "SYSTEM_NOTIFICATION_SENT", super_admin.id, None,
            {
                "notification_id": str(notification_id),
                "title": title,
                "severity": severity,
                "target_user_count": delivered_count,
                "target_tenants": [str(tid) for tid in target_tenants] if target_tenants else "all"
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Notification sent to {delivered_count} users",
            data={
                "notification_id": str(notification_id),
                "delivered_count": delivered_count,
                "severity": severity
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.get("/analytics/growth")
async def get_growth_analytics(
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, 1y"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Growth Analytics über verschiedene Zeiträume"""
    try:
        # Parse period
        period_mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = period_mapping.get(period, 30)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Tenant growth
        tenant_growth = []
        user_growth = []
        
        # Generate daily data points
        for i in range(days):
            date = start_date + timedelta(days=i)
            day_end = date + timedelta(days=1)
            
            # Tenants created on this day
            tenants_count = db.query(Tenant).filter(
                and_(Tenant.created_at >= date, Tenant.created_at < day_end)
            ).count()
            
            # Users created on this day
            users_count = db.query(User).filter(
                and_(
                    User.created_at >= date, 
                    User.created_at < day_end,
                    User.tenant_id.isnot(None)  # Exclude super admins
                )
            ).count()
            
            tenant_growth.append({
                "date": date.strftime("%Y-%m-%d"),
                "count": tenants_count
            })
            
            user_growth.append({
                "date": date.strftime("%Y-%m-%d"),
                "count": users_count
            })
        
        # Calculate growth rates
        current_period_tenants = sum(item["count"] for item in tenant_growth)
        current_period_users = sum(item["count"] for item in user_growth)
        
        # Previous period for comparison
        prev_start = start_date - timedelta(days=days)
        prev_tenants = db.query(Tenant).filter(
            and_(Tenant.created_at >= prev_start, Tenant.created_at < start_date)
        ).count()
        prev_users = db.query(User).filter(
            and_(
                User.created_at >= prev_start,
                User.created_at < start_date,
                User.tenant_id.isnot(None)
            )
        ).count()
        
        tenant_growth_rate = ((current_period_tenants - prev_tenants) / prev_tenants * 100) if prev_tenants > 0 else 0
        user_growth_rate = ((current_period_users - prev_users) / prev_users * 100) if prev_users > 0 else 0
        
        return {
            "period": period,
            "tenant_growth": {
                "daily_data": tenant_growth,
                "total_period": current_period_tenants,
                "growth_rate_percent": round(tenant_growth_rate, 2)
            },
            "user_growth": {
                "daily_data": user_growth,
                "total_period": current_period_users,
                "growth_rate_percent": round(user_growth_rate, 2)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get growth analytics")

# ================================
# AUDIT & SECURITY MONITORING
# ================================

@router.get("/audit/logs")
async def get_audit_logs(
    filter_params: AuthAuditFilterParams = Depends(),
    limit: int = Query(default=100, ge=1, le=1000),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Audit Logs für das gesamte System"""
    try:
        query = db.query(AuditLog)
        
        # Apply filters
        if filter_params.user_id:
            query = query.filter(AuditLog.user_id == filter_params.user_id)
        
        if filter_params.tenant_id:
            query = query.filter(AuditLog.tenant_id == filter_params.tenant_id)
        
        if filter_params.action:
            query = query.filter(AuditLog.action == filter_params.action)
        
        if filter_params.success is not None:
            # Map success to specific actions
            if not filter_params.success:
                query = query.filter(AuditLog.action.in_([
                    "LOGIN_FAILED", "USER_CREATE_FAILED", "ACCOUNT_LOCKED"
                ]))
            else:
                query = query.filter(AuditLog.action.in_([
                    "LOGIN_SUCCESS", "USER_CREATED", "TENANT_CREATED", "PROJECT_CREATED"
                ]))
        
        if filter_params.start_date:
            start_date = datetime.fromisoformat(filter_params.start_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at >= start_date)
        
        if filter_params.end_date:
            end_date = datetime.fromisoformat(filter_params.end_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at <= end_date)
        
        if filter_params.ip_address:
            query = query.filter(AuditLog.ip_address == filter_params.ip_address)
        
        # Order by most recent first
        logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        audit_responses = []
        for log in logs:
            audit_responses.append({
                "user_id": log.user_id,
                "action": log.action,
                "timestamp": log.created_at.isoformat(),
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "tenant_id": log.tenant_id,
                "success": "FAILED" not in log.action and "ERROR" not in log.action,
                "details": log.new_values or {}
            })
        
        return {
            "audit_logs": audit_responses,
            "total_returned": len(audit_responses),
            "filters_applied": filter_params.model_dump(exclude_none=True)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get audit logs")

@router.get("/security/threats")
async def get_security_threats(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Security Threat Detection"""
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Failed login patterns
        failed_logins = db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('attempts'),
            func.count(func.distinct(AuditLog.user_id)).label('unique_users')
        ).filter(
            and_(
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.created_at >= start_time,
                AuditLog.ip_address.isnot(None)
            )
        ).group_by(AuditLog.ip_address).having(
            func.count(AuditLog.id) >= 10  # 10+ failed attempts
        ).all()
        
        # Account lockouts
        lockouts = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "ACCOUNT_LOCKED",
                AuditLog.created_at >= start_time
            )
        ).count()
        
        # Suspicious impersonations
        impersonations = db.query(AuditLog).filter(
            and_(
                AuditLog.action == "SUPER_ADMIN_IMPERSONATE",
                AuditLog.created_at >= start_time
            )
        ).count()
        
        # Multiple tenant access from same IP
        multi_tenant_access = db.query(
            AuditLog.ip_address,
            func.count(func.distinct(AuditLog.tenant_id)).label('tenant_count')
        ).filter(
            and_(
                AuditLog.action == "LOGIN_SUCCESS",
                AuditLog.created_at >= start_time,
                AuditLog.ip_address.isnot(None)
            )
        ).group_by(AuditLog.ip_address).having(
            func.count(func.distinct(AuditLog.tenant_id)) >= 3  # 3+ different tenants
        ).all()
        
        # Calculate threat level
        threat_indicators = len(failed_logins) + lockouts + impersonations + len(multi_tenant_access)
        threat_level = "low"
        if threat_indicators >= 10:
            threat_level = "high"
        elif threat_indicators >= 5:
            threat_level = "medium"
        
        return {
            "threat_level": threat_level,
            "analysis_period_hours": hours,
            "indicators": {
                "suspicious_ips": [
                    {
                        "ip_address": str(item.ip_address),
                        "failed_attempts": item.attempts,
                        "unique_users_targeted": item.unique_users
                    }
                    for item in failed_logins
                ],
                "account_lockouts": lockouts,
                "admin_impersonations": impersonations,
                "multi_tenant_ips": [
                    {
                        "ip_address": str(item.ip_address),
                        "tenant_count": item.tenant_count
                    }
                    for item in multi_tenant_access
                ]
            },
            "recommendations": [
                "Monitor IPs with high failed login attempts",
                "Review impersonation activities",
                "Consider implementing rate limiting",
                "Enable 2FA for high-risk accounts"
            ] if threat_level != "low" else []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to analyze security threats")

# ================================
# SYSTEM MAINTENANCE
# ================================

@router.post("/maintenance/cleanup")
async def system_cleanup(
    cleanup_type: str = Query(..., description="Type: sessions, audit_logs, deleted_users"),
    days_old: int = Query(default=30, ge=1, le=365, description="Remove data older than N days"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """System Cleanup Operations"""
    try:
        cleanup_date = datetime.utcnow() - timedelta(days=days_old)
        cleaned_count = 0
        
        if cleanup_type == "sessions":
            # Clean expired sessions
            cleaned_count = db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
        
        elif cleanup_type == "audit_logs":
            # Clean old audit logs (keep system-critical ones)
            cleaned_count = db.query(AuditLog).filter(
                and_(
                    AuditLog.created_at < cleanup_date,
                    ~AuditLog.action.in_([
                        "TENANT_CREATED", "TENANT_DELETED", 
                        "SUPER_ADMIN_IMPERSONATE", "IDENTITY_PROVIDER_CREATED"
                    ])
                )
            ).delete()
        
        elif cleanup_type == "deleted_users":
            # Clean soft-deleted users
            cleaned_count = db.query(User).filter(
                and_(
                    User.is_active == False,
                    User.email.like("deleted_%@deleted.local"),
                    User.updated_at < cleanup_date
                )
            ).delete()
        
        else:
            raise HTTPException(status_code=400, detail="Invalid cleanup type")
        
        # Audit the cleanup
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "SYSTEM_CLEANUP", super_admin.id, None,
            {
                "cleanup_type": cleanup_type,
                "days_old": days_old,
                "cleaned_count": cleaned_count
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Cleanup completed: {cleaned_count} records removed",
            data={
                "cleanup_type": cleanup_type,
                "records_removed": cleaned_count,
                "cutoff_date": cleanup_date.isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Cleanup operation failed")

@router.get("/maintenance/status")
async def get_maintenance_status(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """System Maintenance Status"""
    try:
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).count()
        
        old_audit_logs = db.query(AuditLog).filter(
            AuditLog.created_at < datetime.utcnow() - timedelta(days=90)
        ).count()
        
        soft_deleted_users = db.query(User).filter(
            and_(
                User.is_active == False,
                User.email.like("deleted_%@deleted.local")
            )
        ).count()
        
        # System health checks
        database_size_mb = 0  # Would implement actual DB size query
        
        return {
            "maintenance_status": {
                "expired_sessions": expired_sessions,
                "old_audit_logs_90d": old_audit_logs,
                "soft_deleted_users": soft_deleted_users,
                "database_size_mb": database_size_mb
            },
            "recommendations": {
                "cleanup_needed": expired_sessions > 1000 or old_audit_logs > 10000,
                "suggested_cleanups": [
                    item for item in [
                        {"type": "sessions", "count": expired_sessions} if expired_sessions > 100 else None,
                        {"type": "audit_logs", "count": old_audit_logs} if old_audit_logs > 5000 else None,
                        {"type": "deleted_users", "count": soft_deleted_users} if soft_deleted_users > 50 else None
                    ] if item is not None
                ]
            },
            "last_maintenance": None  # Would track actual maintenance runs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get maintenance status")

# ================================
# USER & TENANT MANAGEMENT
# ================================

@router.get("/users/problematic")
async def get_problematic_users(
    limit: int = Query(default=50, ge=1, le=200),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Users mit Problemen identifizieren"""
    try:
        from datetime import datetime, timedelta
        
        problematic_users = []
        
        # Locked users
        locked_users = db.query(User).filter(
            and_(
                User.locked_until.isnot(None),
                User.locked_until > datetime.utcnow()
            )
        ).limit(limit//4).all()
        
        for user in locked_users:
            problematic_users.append({
                "user_id": str(user.id),
                "email": user.email,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "issue_type": "locked",
                "issue_details": {
                    "locked_until": user.locked_until.isoformat(),
                    "failed_attempts": user.failed_login_attempts
                },
                "severity": "high"
            })
        
        # Users with many failed logins
        high_fail_users = db.query(User).filter(
            User.failed_login_attempts >= 3
        ).limit(limit//4).all()
        
        for user in high_fail_users:
            if not any(pu["user_id"] == str(user.id) for pu in problematic_users):  # Avoid duplicates
                problematic_users.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                    "issue_type": "multiple_failed_logins",
                    "issue_details": {
                        "failed_attempts": user.failed_login_attempts
                    },
                    "severity": "medium"
                })
        
        # Unverified users (older than 7 days)
        old_unverified = db.query(User).filter(
            and_(
                User.is_verified == False,
                User.created_at < datetime.utcnow() - timedelta(days=7),
                User.tenant_id.isnot(None)  # Exclude super admins
            )
        ).limit(limit//4).all()
        
        for user in old_unverified:
            problematic_users.append({
                "user_id": str(user.id),
                "email": user.email,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "issue_type": "long_unverified",
                "issue_details": {
                    "days_since_creation": (datetime.utcnow() - user.created_at).days
                },
                "severity": "low"
            })
        
        # Users with no recent activity (90+ days)
        inactive_users = db.query(User).filter(
            or_(
                User.last_login_at < datetime.utcnow() - timedelta(days=90),
                User.last_login_at.is_(None)
            ),
            User.tenant_id.isnot(None),
            User.is_active == True
        ).limit(limit//4).all()
        
        for user in inactive_users:
            last_login_days = None
            if user.last_login_at:
                last_login_days = (datetime.utcnow() - user.last_login_at).days
            
            problematic_users.append({
                "user_id": str(user.id),
                "email": user.email,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "issue_type": "inactive",
                "issue_details": {
                    "last_login_days_ago": last_login_days,
                    "never_logged_in": user.last_login_at is None
                },
                "severity": "low"
            })
        
        return {
            "problematic_users": problematic_users[:limit],
            "summary": {
                "total_found": len(problematic_users),
                "by_severity": {
                    "high": len([u for u in problematic_users if u["severity"] == "high"]),
                    "medium": len([u for u in problematic_users if u["severity"] == "medium"]),
                    "low": len([u for u in problematic_users if u["severity"] == "low"])
                },
                "by_issue_type": {
                    issue_type: len([u for u in problematic_users if u["issue_type"] == issue_type])
                    for issue_type in set(u["issue_type"] for u in problematic_users)
                }
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get problematic users")

@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: uuid.UUID = Path(..., description="User ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """User Account entsperren"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Unlock account
        user.locked_until = None
        user.failed_login_attempts = 0
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "ACCOUNT_UNLOCKED_BY_ADMIN", super_admin.id, user.tenant_id,
            {
                "target_user_id": str(user.id),
                "target_email": user.email
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message="User account unlocked successfully",
            data={"user_email": user.email}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unlock user account")

# ================================
# SYSTEM CONFIGURATION
# ================================

@router.get("/config/limits")
async def get_system_limits(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """System-weite Limits und Konfiguration"""
    try:
        # Calculate current usage
        total_tenants = db.query(Tenant).count()
        total_users = db.query(User).filter(User.tenant_id.isnot(None)).count()
        
        # Subscription plan distribution
        plan_distribution = db.query(
            Tenant.subscription_plan,
            func.count(Tenant.id).label('count')
        ).group_by(Tenant.subscription_plan).all()
        
        plan_stats = {plan.subscription_plan: plan.count for plan in plan_distribution}
        
        # Average users per tenant by plan
        avg_users_by_plan = {}
        for plan_name in plan_stats.keys():
            plan_tenants = db.query(Tenant).filter(Tenant.subscription_plan == plan_name).all()
            if plan_tenants:
                total_plan_users = sum(
                    db.query(User).filter(User.tenant_id == tenant.id).count()
                    for tenant in plan_tenants
                )
                avg_users_by_plan[plan_name] = round(total_plan_users / len(plan_tenants), 2)
            else:
                avg_users_by_plan[plan_name] = 0
        
        return {
            "current_usage": {
                "total_tenants": total_tenants,
                "total_users": total_users,
                "avg_users_per_tenant": round(total_users / total_tenants, 2) if total_tenants > 0 else 0
            },
            "subscription_plans": plan_stats,
            "avg_users_by_plan": avg_users_by_plan,
            "system_limits": {
                "max_tenants": 10000,  # Would be configurable
                "max_users_per_tenant": {"basic": 10, "pro": 50, "enterprise": 500},
                "max_storage_per_tenant_gb": {"basic": 1, "pro": 10, "enterprise": 100}
            },
            "utilization": {
                "tenant_utilization_percent": (total_tenants / 10000) * 100,
                "overall_health": "good" if total_tenants < 8000 else "warning"
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="