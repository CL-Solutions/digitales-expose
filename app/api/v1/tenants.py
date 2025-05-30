# ================================
# TENANT MANAGEMENT API ROUTES (api/v1/tenants.py) - Super Admin Only
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.dependencies import get_db, get_super_admin_user
from app.schemas.tenant import (
    TenantCreate, TenantUpdate, TenantResponse, 
    TenantListResponse, TenantFilterParams, TenantStatsResponse,
    MicrosoftIdentityProviderCreate, GoogleIdentityProviderCreate,
    IdentityProviderResponse, IdentityProviderUpdate,
    IdentityProviderListResponse
)
from app.schemas.base import SuccessResponse
from app.models.tenant import Tenant, TenantIdentityProvider
from app.models.user import User
from app.services.auth_service import AuthService
from app.core.exceptions import AppException
from typing import List, Optional
import uuid

router = APIRouter()

# ================================
# TENANT CRUD OPERATIONS
# ================================

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Neuen Tenant erstellen (nur Super-Admin)"""
    try:
        # Check if slug already exists
        existing_tenant = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
        if existing_tenant:
            raise HTTPException(status_code=400, detail="Tenant slug already exists")
        
        # Check if domain already exists
        if tenant_data.domain:
            existing_domain = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
            if existing_domain:
                raise HTTPException(status_code=400, detail="Domain already in use")
        
        # Create tenant
        tenant = Tenant(
            name=tenant_data.name,
            slug=tenant_data.slug,
            domain=tenant_data.domain,
            settings=tenant_data.settings,
            subscription_plan=tenant_data.subscription_plan,
            max_users=tenant_data.max_users,
            is_active=tenant_data.is_active
        )
        
        db.add(tenant)
        db.flush()  # Get tenant.id
        
        # Create default permissions for this tenant
        from app.models.utils import create_default_permissions, create_default_roles_for_tenant
        create_default_permissions(db)
        roles = create_default_roles_for_tenant(db, tenant.id)
        
        # Create tenant admin user
        from app.schemas.auth import CreateUserRequest
        admin_user_data = CreateUserRequest(
            email=tenant_data.admin_email,
            first_name=tenant_data.admin_first_name,
            last_name=tenant_data.admin_last_name,
            password=tenant_data.admin_password,
            send_welcome_email=True,
            require_email_verification=False
        )
        
        admin_user = await AuthService.create_user_by_admin(
            db, admin_user_data, tenant.id, super_admin
        )
        
        # Assign tenant_admin role to the admin user
        from app.models.utils import assign_user_to_role
        assign_user_to_role(db, admin_user.id, "tenant_admin", tenant.id, super_admin.id)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "IDENTITY_PROVIDER_CREATED", super_admin.id, tenant_id,
            {
                "provider": "microsoft",
                "azure_tenant_id": provider_data.azure_tenant_id,
                "auto_provision": provider_data.auto_provision_users
            }
        )
        
        db.commit()
        return IdentityProviderResponse.model_validate(identity_provider)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create Microsoft identity provider")

@router.post("/{tenant_id}/identity-providers/google", response_model=IdentityProviderResponse)
async def create_google_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_data: GoogleIdentityProviderCreate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Google Workspace Provider für Tenant konfigurieren"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Check if Google provider already exists for this tenant
        existing = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == tenant_id,
            TenantIdentityProvider.provider == "google"
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Google provider already configured for this tenant")
        
        # Get default role
        default_role = None
        if provider_data.default_role_name:
            from app.models.rbac import Role
            default_role = db.query(Role).filter(
                Role.tenant_id == tenant_id,
                Role.name == provider_data.default_role_name
            ).first()
        
        # Encrypt client secret
        from app.services.oauth_service import EnterpriseOAuthService
        client_secret_hash = EnterpriseOAuthService._encrypt_secret(provider_data.client_secret)
        
        # Create identity provider
        identity_provider = TenantIdentityProvider(
            tenant_id=tenant_id,
            provider="google",
            provider_type="oauth2",
            client_id=provider_data.client_id,
            client_secret_hash=client_secret_hash,
            discovery_endpoint=provider_data.discovery_endpoint or "https://accounts.google.com/.well-known/openid_configuration",
            user_attribute_mapping=provider_data.user_attribute_mapping,
            role_attribute_mapping=provider_data.role_attribute_mapping,
            auto_provision_users=provider_data.auto_provision_users,
            require_verified_email=provider_data.require_verified_email,
            allowed_domains=provider_data.allowed_domains,
            default_role_id=default_role.id if default_role else None,
            is_active=provider_data.is_active
        )
        
        db.add(identity_provider)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "IDENTITY_PROVIDER_CREATED", super_admin.id, tenant_id,
            {
                "provider": "google",
                "auto_provision": provider_data.auto_provision_users
            }
        )
        
        db.commit()
        return IdentityProviderResponse.model_validate(identity_provider)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create Google identity provider")

@router.get("/{tenant_id}/identity-providers", response_model=IdentityProviderListResponse)
async def list_tenant_identity_providers(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Liste aller Identity Provider für einen Tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        providers = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == tenant_id
        ).order_by(TenantIdentityProvider.provider).all()
        
        return IdentityProviderListResponse(
            providers=[IdentityProviderResponse.model_validate(p) for p in providers],
            total=len(providers)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get identity providers")

@router.put("/{tenant_id}/identity-providers/{provider_id}", response_model=IdentityProviderResponse)
async def update_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_id: uuid.UUID = Path(..., description="Provider ID"),
    provider_update: IdentityProviderUpdate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Identity Provider konfiguration aktualisieren"""
    try:
        provider = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.id == provider_id,
            TenantIdentityProvider.tenant_id == tenant_id
        ).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Identity provider not found")
        
        # Update fields
        if provider_update.client_id is not None:
            provider.client_id = provider_update.client_id
        if provider_update.client_secret is not None:
            from app.services.oauth_service import EnterpriseOAuthService
            provider.client_secret_hash = EnterpriseOAuthService._encrypt_secret(provider_update.client_secret)
        if provider_update.azure_tenant_id is not None:
            provider.azure_tenant_id = provider_update.azure_tenant_id
        if provider_update.discovery_endpoint is not None:
            provider.discovery_endpoint = provider_update.discovery_endpoint
        if provider_update.user_attribute_mapping is not None:
            provider.user_attribute_mapping = provider_update.user_attribute_mapping
        if provider_update.role_attribute_mapping is not None:
            provider.role_attribute_mapping = provider_update.role_attribute_mapping
        if provider_update.auto_provision_users is not None:
            provider.auto_provision_users = provider_update.auto_provision_users
        if provider_update.require_verified_email is not None:
            provider.require_verified_email = provider_update.require_verified_email
        if provider_update.allowed_domains is not None:
            provider.allowed_domains = provider_update.allowed_domains
        if provider_update.is_active is not None:
            provider.is_active = provider_update.is_active
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "IDENTITY_PROVIDER_UPDATED", super_admin.id, tenant_id,
            {
                "provider_id": str(provider_id),
                "provider": provider.provider,
                "updates": provider_update.model_dump(exclude_unset=True, exclude={"client_secret"})
            }
        )
        
        db.commit()
        return IdentityProviderResponse.model_validate(provider)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update identity provider")

@router.delete("/{tenant_id}/identity-providers/{provider_id}")
async def delete_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_id: uuid.UUID = Path(..., description="Provider ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Identity Provider löschen"""
    try:
        provider = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.id == provider_id,
            TenantIdentityProvider.tenant_id == tenant_id
        ).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Identity provider not found")
        
        # Check if users are using this provider
        oauth_users_count = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.auth_method == provider.provider
        ).count()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "IDENTITY_PROVIDER_DELETED", super_admin.id, tenant_id,
            {
                "provider_id": str(provider_id),
                "provider": provider.provider,
                "affected_users": oauth_users_count
            }
        )
        
        db.delete(provider)
        db.commit()
        
        return SuccessResponse(
            message="Identity provider deleted successfully",
            data={"affected_users": oauth_users_count}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete identity provider")

# ================================
# TENANT STATISTICS & ANALYTICS
# ================================

@router.get("/stats", response_model=TenantStatsResponse)
async def get_tenant_statistics(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Gesamt-Statistiken aller Tenants"""
    try:
        from datetime import datetime, timedelta
        
        # Basic counts
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        total_users = db.query(User).filter(User.tenant_id.isnot(None)).count()
        
        # Tenants by subscription plan
        plan_stats = db.query(
            Tenant.subscription_plan,
            func.count(Tenant.id).label('count')
        ).group_by(Tenant.subscription_plan).all()
        
        tenants_by_plan = {stat.subscription_plan: stat.count for stat in plan_stats}
        
        # Recent signups (last 30 days)
        recent_date = datetime.utcnow() - timedelta(days=30)
        recent_signups = db.query(Tenant).filter(
            Tenant.created_at >= recent_date
        ).count()
        
        return TenantStatsResponse(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            tenants_by_plan=tenants_by_plan,
            recent_signups=recent_signups
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get tenant statistics")

@router.get("/{tenant_id}/stats")
async def get_tenant_details_stats(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Detaillierte Statistiken für einen spezifischen Tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        from datetime import datetime, timedelta
        
        # User statistics
        total_users = db.query(User).filter(User.tenant_id == tenant_id).count()
        active_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_active == True
        ).count()
        verified_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.is_verified == True
        ).count()
        
        # Users by auth method
        auth_method_stats = db.query(
            User.auth_method,
            func.count(User.id).label('count')
        ).filter(User.tenant_id == tenant_id).group_by(User.auth_method).all()
        
        users_by_auth_method = {stat.auth_method: stat.count for stat in auth_method_stats}
        
        # Recent activity
        recent_date = datetime.utcnow() - timedelta(days=7)
        recent_logins = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.last_login_at >= recent_date
        ).count()
        
        # Business data counts (if exists)
        project_count = 0
        document_count = 0
        try:
            from app.models.business import Project, Document
            project_count = db.query(Project).filter(Project.tenant_id == tenant_id).count()
            document_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()
        except:
            pass  # Business models might not be available
        
        return {
            "tenant_info": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "subscription_plan": tenant.subscription_plan,
                "max_users": tenant.max_users,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat()
            },
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "verified_users": verified_users,
                "users_by_auth_method": users_by_auth_method,
                "recent_logins": recent_logins
            },
            "business_stats": {
                "project_count": project_count,
                "document_count": document_count
            },
            "capacity": {
                "user_usage_percentage": (total_users / tenant.max_users * 100) if tenant.max_users > 0 else 0,
                "users_remaining": max(0, tenant.max_users - total_users)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get tenant statistics")

# ================================
# TENANT ACTIONS
# ================================

@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Tenant aktivieren"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant.is_active = True
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "TENANT_ACTIVATED", super_admin.id, tenant_id,
            {"tenant_name": tenant.name}
        )
        
        db.commit()
        return SuccessResponse(message="Tenant activated successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to activate tenant")

@router.post("/{tenant_id}/deactivate")
async def deactivate_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Tenant deaktivieren"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        tenant.is_active = False
        
        # Invalidate all user sessions for this tenant
        from app.models.user import UserSession
        deleted_sessions = db.query(UserSession).filter(
            UserSession.tenant_id == tenant_id
        ).delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "TENANT_DEACTIVATED", super_admin.id, tenant_id,
            {
                "tenant_name": tenant.name,
                "invalidated_sessions": deleted_sessions
            }
        )
        
        db.commit()
        return SuccessResponse(
            message="Tenant deactivated successfully",
            data={"invalidated_sessions": deleted_sessions}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to deactivate tenant")

# ================================
# TENANT DATA EXPORT & BACKUP
# ================================

@router.get("/{tenant_id}/export")
async def export_tenant_data(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    include_users: bool = Query(default=True, description="Include user data"),
    include_projects: bool = Query(default=True, description="Include project data"),
    include_audit_logs: bool = Query(default=False, description="Include audit logs"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Tenant-Daten für Backup/Migration exportieren"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        export_data = {
            "tenant_info": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "domain": tenant.domain,
                "settings": tenant.settings,
                "subscription_plan": tenant.subscription_plan,
                "max_users": tenant.max_users,
                "created_at": tenant.created_at.isoformat(),
                "export_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Export users
        if include_users:
            users = db.query(User).filter(User.tenant_id == tenant_id).all()
            export_data["users"] = []
            
            for user in users:
                user_data = {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "auth_method": user.auth_method,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
                }
                
                # Get user roles
                from app.models.rbac import UserRole, Role
                user_roles = db.query(Role).join(UserRole).filter(
                    UserRole.user_id == user.id,
                    UserRole.tenant_id == tenant_id
                ).all()
                user_data["roles"] = [role.name for role in user_roles]
                
                export_data["users"].append(user_data)
        
        # Export projects and documents
        if include_projects:
            try:
                from app.models.business import Project, Document
                
                projects = db.query(Project).filter(Project.tenant_id == tenant_id).all()
                export_data["projects"] = []
                
                for project in projects:
                    project_data = {
                        "id": str(project.id),
                        "name": project.name,
                        "description": project.description,
                        "status": project.status,
                        "created_at": project.created_at.isoformat(),
                        "created_by": str(project.created_by)
                    }
                    
                    # Get project documents
                    documents = db.query(Document).filter(Document.project_id == project.id).all()
                    project_data["documents"] = []
                    
                    for doc in documents:
                        doc_data = {
                            "id": str(doc.id),
                            "title": doc.title,
                            "file_size": doc.file_size,
                            "mime_type": doc.mime_type,
                            "created_at": doc.created_at.isoformat(),
                            "created_by": str(doc.created_by)
                        }
                        project_data["documents"].append(doc_data)
                    
                    export_data["projects"].append(project_data)
            
            except ImportError:
                export_data["projects"] = "Business models not available"
        
        # Export audit logs (optional)
        if include_audit_logs:
            recent_logs = db.query(AuditLog).filter(
                AuditLog.tenant_id == tenant_id
            ).order_by(desc(AuditLog.created_at)).limit(1000).all()
            
            export_data["audit_logs"] = []
            for log in recent_logs:
                log_data = {
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": str(log.resource_id) if log.resource_id else None,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "created_at": log.created_at.isoformat(),
                    "ip_address": str(log.ip_address) if log.ip_address else None
                }
                export_data["audit_logs"].append(log_data)
        
        # Audit the export
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "TENANT_DATA_EXPORTED", super_admin.id, tenant_id,
            {
                "include_users": include_users,
                "include_projects": include_projects,
                "include_audit_logs": include_audit_logs,
                "export_size_kb": len(str(export_data)) // 1024
            }
        )
        
        db.commit()
        
        return export_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to export tenant data")

@router.get("/{tenant_id}/usage-report")
async def get_tenant_usage_report(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    days: int = Query(default=30, ge=1, le=365, description="Report period in days"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Detaillierter Nutzungsbericht für einen Tenant"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # User activity
        total_users = db.query(User).filter(User.tenant_id == tenant_id).count()
        active_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.last_login_at >= start_date
        ).count()
        
        # Login activity
        login_events = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == "LOGIN_SUCCESS",
                AuditLog.created_at >= start_date
            )
        ).count()
        
        # Feature usage
        try:
            from app.models.business import Project, Document
            
            projects_created = db.query(Project).filter(
                and_(
                    Project.tenant_id == tenant_id,
                    Project.created_at >= start_date
                )
            ).count()
            
            documents_created = db.query(Document).filter(
                and_(
                    Document.tenant_id == tenant_id,
                    Document.created_at >= start_date
                )
            ).count()
            
            total_storage_bytes = db.query(func.sum(Document.file_size)).filter(
                Document.tenant_id == tenant_id,
                Document.file_size.isnot(None)
            ).scalar() or 0
            
        except ImportError:
            projects_created = 0
            documents_created = 0
            total_storage_bytes = 0
        
        # Calculate usage percentages
        user_utilization = (total_users / tenant.max_users * 100) if tenant.max_users > 0 else 0
        activity_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "tenant_info": {
                "id": str(tenant.id),
                "name": tenant.name,
                "subscription_plan": tenant.subscription_plan,
                "max_users": tenant.max_users
            },
            "report_period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat()
            },
            "user_metrics": {
                "total_users": total_users,
                "active_users_period": active_users,
                "user_utilization_percent": round(user_utilization, 2),
                "activity_rate_percent": round(activity_rate, 2)
            },
            "activity_metrics": {
                "total_logins": login_events,
                "avg_logins_per_day": round(login_events / days, 2),
                "avg_logins_per_active_user": round(login_events / active_users, 2) if active_users > 0 else 0
            },
            "feature_usage": {
                "projects_created": projects_created,
                "documents_created": documents_created,
                "total_storage_bytes": total_storage_bytes,
                "total_storage_mb": round(total_storage_bytes / (1024 * 1024), 2)
            },
            "recommendations": [
                "Consider upgrading plan" if user_utilization > 80 else None,
                "Low user activity detected" if activity_rate < 20 else None,
                "High storage usage" if total_storage_bytes > 100 * 1024 * 1024 else None
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate usage report")(
            db, "TENANT_CREATED", super_admin.id, tenant.id,
            {
                "tenant_name": tenant.name,
                "tenant_slug": tenant.slug,
                "admin_email": admin_user.email
            }
        )
        
        db.commit()
        return TenantResponse.model_validate(tenant)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create tenant")

@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    filter_params: TenantFilterParams = Depends(),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Liste aller Tenants (nur Super-Admin)"""
    try:
        query = db.query(Tenant)
        
        # Apply filters
        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            query = query.filter(
                or_(
                    Tenant.name.ilike(search_term),
                    Tenant.slug.ilike(search_term),
                    Tenant.domain.ilike(search_term)
                )
            )
        
        if filter_params.subscription_plan:
            query = query.filter(Tenant.subscription_plan == filter_params.subscription_plan)
        
        if filter_params.is_active is not None:
            query = query.filter(Tenant.is_active == filter_params.is_active)
        
        if filter_params.has_domain is not None:
            if filter_params.has_domain:
                query = query.filter(Tenant.domain.isnot(None))
            else:
                query = query.filter(Tenant.domain.is_(None))
        
        # Count total
        total = query.count()
        
        # Apply sorting
        if filter_params.sort_by == "name":
            sort_field = Tenant.name
        elif filter_params.sort_by == "slug":
            sort_field = Tenant.slug
        else:
            sort_field = Tenant.created_at
        
        if filter_params.sort_order == "desc":
            sort_field = sort_field.desc()
        
        query = query.order_by(sort_field)
        
        # Apply pagination
        offset = (filter_params.page - 1) * filter_params.page_size
        tenants = query.offset(offset).limit(filter_params.page_size).all()
        
        # Add user count to each tenant
        tenant_responses = []
        for tenant in tenants:
            user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
            tenant_response = TenantResponse.model_validate(tenant)
            tenant_response.user_count = user_count
            tenant_responses.append(tenant_response)
        
        return TenantListResponse(
            tenants=tenant_responses,
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve tenants")

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant_by_id(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Spezifischen Tenant abrufen"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Add user count
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        tenant_response = TenantResponse.model_validate(tenant)
        tenant_response.user_count = user_count
        
        return tenant_response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get tenant")

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    tenant_update: TenantUpdate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Tenant aktualisieren"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Store old values for audit
        old_values = {
            "name": tenant.name,
            "domain": tenant.domain,
            "subscription_plan": tenant.subscription_plan,
            "max_users": tenant.max_users,
            "is_active": tenant.is_active
        }
        
        # Update fields
        update_data = {}
        if tenant_update.name is not None:
            tenant.name = tenant_update.name
            update_data["name"] = tenant_update.name
        if tenant_update.domain is not None:
            # Check domain uniqueness
            if tenant_update.domain != tenant.domain:
                existing = db.query(Tenant).filter(
                    Tenant.domain == tenant_update.domain,
                    Tenant.id != tenant_id
                ).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Domain already in use")
            tenant.domain = tenant_update.domain
            update_data["domain"] = tenant_update.domain
        if tenant_update.settings is not None:
            tenant.settings = tenant_update.settings
            update_data["settings"] = tenant_update.settings
        if tenant_update.subscription_plan is not None:
            tenant.subscription_plan = tenant_update.subscription_plan
            update_data["subscription_plan"] = tenant_update.subscription_plan
        if tenant_update.max_users is not None:
            tenant.max_users = tenant_update.max_users
            update_data["max_users"] = tenant_update.max_users
        if tenant_update.is_active is not None:
            tenant.is_active = tenant_update.is_active
            update_data["is_active"] = tenant_update.is_active
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "TENANT_UPDATED", super_admin.id, tenant.id,
            {"old_values": old_values, "new_values": update_data}
        )
        
        db.commit()
        
        # Add user count
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        tenant_response = TenantResponse.model_validate(tenant)
        tenant_response.user_count = user_count
        
        return tenant_response
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Tenant update failed")

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Tenant löschen (mit allen Daten!)"""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Count users for audit
        user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
        
        # Audit log before deletion
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "TENANT_DELETED", super_admin.id, tenant_id,
            {
                "tenant_name": tenant.name,
                "tenant_slug": tenant.slug,
                "user_count": user_count
            }
        )
        
        # Delete tenant (cascade will handle related data)
        db.delete(tenant)
        db.commit()
        
        return SuccessResponse(
            message="Tenant deleted successfully",
            data={"deleted_users": user_count}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Tenant deletion failed")

# ================================
# TENANT IDENTITY PROVIDERS
# ================================

@router.post("/{tenant_id}/identity-providers/microsoft", response_model=IdentityProviderResponse)
async def create_microsoft_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_data: MicrosoftIdentityProviderCreate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Microsoft Entra ID Provider für Tenant konfigurieren"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Check if Microsoft provider already exists for this tenant
        existing = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == tenant_id,
            TenantIdentityProvider.provider == "microsoft"
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Microsoft provider already configured for this tenant")
        
        # Get default role
        default_role = None
        if provider_data.default_role_name:
            from app.models.rbac import Role
            default_role = db.query(Role).filter(
                Role.tenant_id == tenant_id,
                Role.name == provider_data.default_role_name
            ).first()
        
        # Encrypt client secret
        from app.services.oauth_service import EnterpriseOAuthService
        client_secret_hash = EnterpriseOAuthService._encrypt_secret(provider_data.client_secret)
        
        # Create identity provider
        identity_provider = TenantIdentityProvider(
            tenant_id=tenant_id,
            provider="microsoft",
            provider_type="oauth2",
            client_id=provider_data.client_id,
            client_secret_hash=client_secret_hash,
            azure_tenant_id=provider_data.azure_tenant_id,
            discovery_endpoint=provider_data.discovery_endpoint or f"https://login.microsoftonline.com/{provider_data.azure_tenant_id}/v2.0/.well-known/openid_configuration",
            user_attribute_mapping=provider_data.user_attribute_mapping,
            role_attribute_mapping=provider_data.role_attribute_mapping,
            auto_provision_users=provider_data.auto_provision_users,
            require_verified_email=provider_data.require_verified_email,
            allowed_domains=provider_data.allowed_domains,
            default_role_id=default_role.id if default_role else None,
            is_active=provider_data.is_active
        )
        
        db.add(identity_provider)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event