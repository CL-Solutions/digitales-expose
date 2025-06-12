# ================================
# TENANT SERVICE (services/tenant_service.py)
# ================================

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.tenant import Tenant, TenantIdentityProvider
from app.models.user import User, UserSession
from app.models.audit import AuditLog
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

audit_logger = AuditLogger()

class TenantService:
    """Service for tenant management operations"""
    
    @staticmethod
    async def create_tenant_with_admin(
        db: Session,
        tenant_data: TenantCreate,
        super_admin: User
    ) -> Tenant:
        """Create new tenant with admin user"""
        from app.services.auth_service import AuthService
        from app.models.utils import create_default_permissions, create_default_roles_for_tenant, assign_user_to_role
        
        # Check if slug already exists
        existing_tenant = db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
        if existing_tenant:
            raise AppException("Tenant slug already exists", 400, "SLUG_EXISTS")
        
        # Check if domain already exists
        if tenant_data.domain:
            existing_domain = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
            if existing_domain:
                raise AppException("Domain already in use", 400, "DOMAIN_EXISTS")
        
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
        
        # Create default permissions and roles
        create_default_permissions(db)
        roles = create_default_roles_for_tenant(db, tenant.id)
        
        # Flush to ensure roles are committed before creating user
        db.flush()
        
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
        
        # Flush user creation before role assignment
        db.flush()
        
        # Assign tenant_admin role
        try:
            user_role = assign_user_to_role(db, admin_user.id, "tenant_admin", tenant.id, super_admin.id)
            db.flush()  # Ensure role assignment is committed
            
            # Log successful role assignment
            audit_logger.log_auth_event(
                db, "ROLE_ASSIGNED", super_admin.id, tenant.id,
                {
                    "user_id": str(admin_user.id),
                    "user_email": admin_user.email,
                    "role_name": "tenant_admin"
                }
            )
        except Exception as e:
            # Log the error but don't fail tenant creation
            print(f"Failed to assign tenant_admin role to user {admin_user.email}: {str(e)}")
            # Try to find and assign the role manually
            from app.models.rbac import Role, UserRole
            tenant_admin_role = db.query(Role).filter(
                Role.tenant_id == tenant.id,
                Role.name == "tenant_admin"
            ).first()
            
            if tenant_admin_role:
                user_role = UserRole(
                    user_id=admin_user.id,
                    role_id=tenant_admin_role.id,
                    tenant_id=tenant.id,
                    granted_by=super_admin.id
                )
                db.add(user_role)
                db.flush()
                print(f"Successfully assigned tenant_admin role manually to {admin_user.email}")
            else:
                print(f"tenant_admin role not found for tenant {tenant.id}")
        
        # Audit log
        audit_logger.log_auth_event(
            db, "TENANT_CREATED", super_admin.id, tenant.id,
            {
                "tenant_name": tenant.name,
                "tenant_slug": tenant.slug,
                "admin_email": admin_user.email
            }
        )
        
        return tenant
    
    @staticmethod
    def update_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        tenant_update: TenantUpdate,
        super_admin: User
    ) -> Tenant:
        """Update tenant information"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        # Store old values for audit
        old_values = {
            "name": tenant.name,
            "domain": tenant.domain,
            "subscription_plan": tenant.subscription_plan,
            "max_users": tenant.max_users,
            "is_active": tenant.is_active,
            "investagon_organization_id": tenant.investagon_organization_id,
            "investagon_sync_enabled": tenant.investagon_sync_enabled
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
                    raise AppException("Domain already in use", 400, "DOMAIN_EXISTS")
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
        
        # Update Investagon fields
        if tenant_update.investagon_organization_id is not None:
            tenant.investagon_organization_id = tenant_update.investagon_organization_id
            update_data["investagon_organization_id"] = tenant_update.investagon_organization_id
        if tenant_update.investagon_api_key is not None:
            tenant.investagon_api_key = tenant_update.investagon_api_key
            update_data["investagon_api_key"] = "***" # Don't log the actual API key
        if tenant_update.investagon_sync_enabled is not None:
            tenant.investagon_sync_enabled = tenant_update.investagon_sync_enabled
            update_data["investagon_sync_enabled"] = tenant_update.investagon_sync_enabled
        
        # Update Contact Information fields
        if tenant_update.contact_email is not None:
            tenant.contact_email = tenant_update.contact_email
            update_data["contact_email"] = tenant_update.contact_email
        if tenant_update.contact_phone is not None:
            tenant.contact_phone = tenant_update.contact_phone
            update_data["contact_phone"] = tenant_update.contact_phone
        if tenant_update.contact_street is not None:
            tenant.contact_street = tenant_update.contact_street
            update_data["contact_street"] = tenant_update.contact_street
        if tenant_update.contact_house_number is not None:
            tenant.contact_house_number = tenant_update.contact_house_number
            update_data["contact_house_number"] = tenant_update.contact_house_number
        if tenant_update.contact_city is not None:
            tenant.contact_city = tenant_update.contact_city
            update_data["contact_city"] = tenant_update.contact_city
        if tenant_update.contact_state is not None:
            tenant.contact_state = tenant_update.contact_state
            update_data["contact_state"] = tenant_update.contact_state
        if tenant_update.contact_zip_code is not None:
            tenant.contact_zip_code = tenant_update.contact_zip_code
            update_data["contact_zip_code"] = tenant_update.contact_zip_code
        if tenant_update.contact_country is not None:
            tenant.contact_country = tenant_update.contact_country
            update_data["contact_country"] = tenant_update.contact_country
        
        # Audit log
        audit_logger.log_auth_event(
            db, "TENANT_UPDATED", super_admin.id, tenant.id,
            {"old_values": old_values, "new_values": update_data}
        )
        
        return tenant
    
    @staticmethod
    def delete_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        super_admin: User
    ) -> Dict[str, Any]:
        """Delete tenant and all related data"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        # Count users for audit
        user_count = db.query(User).filter(User.tenant_id == tenant_id).count()
        
        # Audit log before deletion
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
        
        return {"deleted_users": user_count}
    
    @staticmethod
    def activate_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        super_admin: User
    ) -> Tenant:
        """Activate tenant"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        tenant.is_active = True
        
        audit_logger.log_auth_event(
            db, "TENANT_ACTIVATED", super_admin.id, tenant_id,
            {"tenant_name": tenant.name}
        )
        
        return tenant
    
    @staticmethod
    def deactivate_tenant(
        db: Session,
        tenant_id: uuid.UUID,
        super_admin: User
    ) -> Dict[str, Any]:
        """Deactivate tenant and terminate sessions"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        tenant.is_active = False
        
        # Invalidate all user sessions for this tenant
        deleted_sessions = db.query(UserSession).filter(
            UserSession.tenant_id == tenant_id
        ).delete()
        
        audit_logger.log_auth_event(
            db, "TENANT_DEACTIVATED", super_admin.id, tenant_id,
            {
                "tenant_name": tenant.name,
                "invalidated_sessions": deleted_sessions
            }
        )
        
        return {"invalidated_sessions": deleted_sessions}
    
    @staticmethod
    def get_tenant_statistics(db: Session) -> Dict[str, Any]:
        """Get overall tenant statistics"""
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
        
        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_users": total_users,
            "tenants_by_plan": tenants_by_plan,
            "recent_signups": recent_signups
        }
    
    @staticmethod
    def get_tenant_details_stats(
        db: Session,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get detailed statistics for a specific tenant"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
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
        
        # Business data counts
        project_count = 0
        document_count = 0
        try:
            from app.models.business import Project, Document
            project_count = db.query(Project).filter(Project.tenant_id == tenant_id).count()
            document_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()
        except:
            pass
        
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
    
    @staticmethod
    def clone_tenant(
        db: Session,
        source_tenant_id: uuid.UUID,
        new_tenant_name: str,
        new_tenant_slug: str,
        include_users: bool,
        include_data: bool,
        super_admin: User
    ) -> Dict[str, Any]:
        """Clone an existing tenant"""
        from app.models.utils import create_default_permissions, create_default_roles_for_tenant
        
        # Verify source tenant exists
        source_tenant = db.query(Tenant).filter(Tenant.id == source_tenant_id).first()
        if not source_tenant:
            raise AppException("Source tenant not found", 404, "TENANT_NOT_FOUND")
        
        # Check if new slug already exists
        existing_tenant = db.query(Tenant).filter(Tenant.slug == new_tenant_slug).first()
        if existing_tenant:
            raise AppException("New tenant slug already exists", 400, "SLUG_EXISTS")
        
        # Create new tenant
        new_tenant = Tenant(
            name=new_tenant_name,
            slug=new_tenant_slug,
            domain=None,  # Don't clone domain
            settings=source_tenant.settings.copy() if source_tenant.settings else {},
            subscription_plan=source_tenant.subscription_plan,
            max_users=source_tenant.max_users,
            is_active=True
        )
        
        db.add(new_tenant)
        db.flush()  # Get new tenant ID
        
        # Clone default roles and permissions
        create_default_permissions(db)
        create_default_roles_for_tenant(db, new_tenant.id)
        
        # Clone identity providers
        source_providers = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == source_tenant_id
        ).all()
        
        for provider in source_providers:
            new_provider = TenantIdentityProvider(
                tenant_id=new_tenant.id,
                provider=provider.provider,
                provider_type=provider.provider_type,
                client_id=provider.client_id,
                client_secret_hash=provider.client_secret_hash,
                azure_tenant_id=provider.azure_tenant_id,
                discovery_endpoint=provider.discovery_endpoint,
                user_attribute_mapping=provider.user_attribute_mapping,
                role_attribute_mapping=provider.role_attribute_mapping,
                auto_provision_users=provider.auto_provision_users,
                require_verified_email=provider.require_verified_email,
                allowed_domains=provider.allowed_domains,
                is_active=provider.is_active
            )
            db.add(new_provider)
        
        clone_summary = {
            "cloned_tenant_id": str(new_tenant.id),
            "cloned_providers": len(source_providers),
            "cloned_users": 0,
            "cloned_projects": 0
        }
        
        # Clone users if requested
        if include_users:
            source_users = db.query(User).filter(User.tenant_id == source_tenant_id).all()
            for user in source_users:
                # Create new user with modified email to avoid conflicts
                new_email = f"cloned_{user.email}"
                new_user = User(
                    email=new_email,
                    tenant_id=new_tenant.id,
                    auth_method=user.auth_method,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_active=user.is_active,
                    is_verified=user.is_verified
                )
                db.add(new_user)
            
            clone_summary["cloned_users"] = len(source_users)
        
        # Clone business data if requested
        if include_data:
            try:
                from app.models.business import Project, Document
                
                source_projects = db.query(Project).filter(Project.tenant_id == source_tenant_id).all()
                for project in source_projects:
                    new_project = Project(
                        tenant_id=new_tenant.id,
                        name=f"{project.name} (Cloned)",
                        description=project.description,
                        status=project.status,
                        created_by=super_admin.id
                    )
                    db.add(new_project)
                
                clone_summary["cloned_projects"] = len(source_projects)
            except ImportError:
                pass
        
        # Audit log
        audit_logger.log_auth_event(
            db, "TENANT_CLONED", super_admin.id, new_tenant.id,
            {
                "source_tenant_id": str(source_tenant_id),
                "source_tenant_name": source_tenant.name,
                "new_tenant_name": new_tenant_name,
                "include_users": include_users,
                "include_data": include_data,
                "clone_summary": clone_summary
            }
        )
        
        return clone_summary
    
    @staticmethod
    def export_tenant_data(
        db: Session,
        tenant_id: uuid.UUID,
        include_users: bool,
        include_projects: bool,
        include_audit_logs: bool
    ) -> Dict[str, Any]:
        """Export tenant data for backup/migration"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
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
        
        return export_data
    
    @staticmethod
    def get_tenant_usage_report(
        db: Session,
        tenant_id: uuid.UUID,
        days: int
    ) -> Dict[str, Any]:
        """Generate tenant usage report"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # User activity
        total_users = db.query(User).filter(User.tenant_id == tenant_id).count()
        active_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.last_login_at >= start_date
        ).count()
        
        # Login activity
        login_attempts = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action.in_(["LOGIN_SUCCESS", "LOGIN_FAILED"]),
                AuditLog.created_at >= start_date
            )
        ).count()
        
        successful_logins = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == "LOGIN_SUCCESS",
                AuditLog.created_at >= start_date
            )
        ).count()
        
        # Feature usage
        try:
            from app.models.business import Project, Document
            
            new_projects = db.query(Project).filter(
                and_(
                    Project.tenant_id == tenant_id,
                    Project.created_at >= start_date
                )
            ).count()
            
            new_documents = db.query(Document).filter(
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
            new_projects = 0
            new_documents = 0
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
            "authentication_metrics": {
                "total_login_attempts": login_attempts,
                "successful_logins": successful_logins,
                "success_rate_percent": round((successful_logins / login_attempts * 100), 2) if login_attempts > 0 else 0
            },
            "feature_usage": {
                "new_projects": new_projects,
                "new_documents": new_documents,
                "total_storage_bytes": total_storage_bytes,
                "storage_gb": round(total_storage_bytes / (1024**3), 2)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_tenant_health(db: Session, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """Check tenant health status"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        health_data = {
            "tenant_id": str(tenant_id),
            "tenant_name": tenant.name,
            "overall_health": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # User health
        total_users = db.query(User).filter(User.tenant_id == tenant_id).count()
        locked_users = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.locked_until.isnot(None),
            User.locked_until > datetime.utcnow()
        ).count()
        
        user_health = "healthy"
        if locked_users > (total_users * 0.1):  # More than 10% locked
            user_health = "warning"
        
        health_data["checks"]["users"] = {
            "status": user_health,
            "total_users": total_users,
            "locked_users": locked_users,
            "lock_percentage": round((locked_users / total_users * 100), 2) if total_users > 0 else 0
        }
        
        # Session health
        active_sessions = db.query(UserSession).filter(
            UserSession.tenant_id == tenant_id,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        health_data["checks"]["sessions"] = {
            "status": "healthy" if active_sessions < 1000 else "warning",
            "active_sessions": active_sessions
        }
        
        # Recent security events
        recent_failures = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
        ).count()
        
        security_health = "healthy"
        if recent_failures > 50:
            security_health = "warning" if recent_failures < 100 else "critical"
        
        health_data["checks"]["security"] = {
            "status": security_health,
            "failed_logins_24h": recent_failures
        }
        
        # Identity provider health
        identity_providers = db.query(TenantIdentityProvider).filter(
            TenantIdentityProvider.tenant_id == tenant_id,
            TenantIdentityProvider.is_active == True
        ).count()
        
        health_data["checks"]["identity_providers"] = {
            "status": "healthy",
            "active_providers": identity_providers
        }
        
        # Determine overall health
        check_statuses = [check["status"] for check in health_data["checks"].values()]
        if "critical" in check_statuses:
            health_data["overall_health"] = "critical"
        elif "warning" in check_statuses:
            health_data["overall_health"] = "warning"
        
        return health_data
    
    @staticmethod
    def cleanup_tenant_data(
        db: Session,
        tenant_id: uuid.UUID,
        cleanup_type: str,
        days_old: int,
        super_admin: User
    ) -> Dict[str, Any]:
        """Perform maintenance cleanup for specific tenant"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        cleanup_date = datetime.utcnow() - timedelta(days=days_old)
        cleaned_count = 0
        
        if cleanup_type == "sessions":
            # Clean expired sessions for this tenant
            cleaned_count = db.query(UserSession).filter(
                UserSession.tenant_id == tenant_id,
                UserSession.expires_at < datetime.utcnow()
            ).delete()
        
        elif cleanup_type == "audit_logs":
            # Clean old audit logs for this tenant (keep critical ones)
            cleaned_count = db.query(AuditLog).filter(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at < cleanup_date,
                    ~AuditLog.action.in_([
                        "TENANT_CREATED", "TENANT_DELETED", 
                        "USER_CREATED", "IDENTITY_PROVIDER_CREATED"
                    ])
                )
            ).delete()
        
        elif cleanup_type == "inactive_users":
            # Clean users who never logged in and are old
            cleaned_count = db.query(User).filter(
                and_(
                    User.tenant_id == tenant_id,
                    User.last_login_at.is_(None),
                    User.created_at < cleanup_date,
                    User.is_active == False
                )
            ).delete()
        
        else:
            raise AppException("Invalid cleanup type", 400, "INVALID_CLEANUP_TYPE")
        
        # Audit the cleanup
        audit_logger.log_auth_event(
            db, "TENANT_CLEANUP", super_admin.id, tenant_id,
            {
                "cleanup_type": cleanup_type,
                "days_old": days_old,
                "cleaned_count": cleaned_count,
                "tenant_name": tenant.name
            }
        )
        
        return {
            "tenant_name": tenant.name,
            "cleanup_type": cleanup_type,
            "records_removed": cleaned_count,
            "cutoff_date": cleanup_date.isoformat()
        }