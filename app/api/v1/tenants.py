# ================================
# TENANT MANAGEMENT API ROUTES (api/v1/tenants.py) - UPDATED
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_super_admin_user, get_current_user
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
from app.services.tenant_service import TenantService
from app.core.exceptions import AppException
from typing import List, Optional
import uuid

router = APIRouter()

# ================================
# TENANT CRUD OPERATIONS
# ================================

@router.post("/", response_model=TenantResponse, response_model_exclude_none=True)
async def create_tenant(
    tenant_data: TenantCreate,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create new tenant (Super Admin only)"""
    try:
        tenant = await TenantService.create_tenant_with_admin(db, tenant_data, super_admin)
        db.commit()
        
        # Add user count (1 for new tenant - the admin user)
        tenant_dict = tenant.__dict__.copy()
        tenant_dict['user_count'] = 1  # New tenant has 1 user (the admin)
        tenant_dict.pop('_sa_instance_state', None)
        
        return TenantResponse.model_validate(tenant_dict)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create tenant")

@router.get("/", response_model=TenantListResponse, response_model_exclude_none=True)
async def list_tenants(
    filter_params: TenantFilterParams = Depends(),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all tenants (Super Admin only)"""
    try:
        from sqlalchemy import and_, or_, desc
        
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
            
            # Convert to dict and add user_count before validation
            tenant_dict = tenant.__dict__.copy()
            tenant_dict['user_count'] = user_count
            tenant_dict.pop('_sa_instance_state', None)
            
            tenant_response = TenantResponse.model_validate(tenant_dict)
            tenant_responses.append(tenant_response)
        
        return TenantListResponse(
            tenants=tenant_responses,
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve tenants")

@router.get("/{tenant_id}", response_model=TenantResponse, response_model_exclude_none=True)
async def get_tenant_by_id(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific tenant - super admins can access any tenant, regular users only their own"""
    try:
        # Check permissions: super admins can access any tenant, regular users only their own
        if not current_user.is_super_admin and current_user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only access your own tenant")
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Add user count (only for super admins or if it's the user's own tenant)
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        
        # Convert to dict and add user_count before validation
        tenant_dict = tenant.__dict__.copy()
        tenant_dict['user_count'] = user_count
        
        # Remove SQLAlchemy internal state
        tenant_dict.pop('_sa_instance_state', None)
        
        tenant_response = TenantResponse.model_validate(tenant_dict)
        return tenant_response
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error getting tenant {tenant_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to get tenant")

@router.patch("/{tenant_id}", response_model=TenantResponse, response_model_exclude_none=True)
async def update_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    tenant_update: TenantUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update tenant - super admins can update any tenant, tenant admins can update their own"""
    try:
        from app.services.rbac_service import RBACService
        
        # Check permissions: super admins can update any tenant
        # Regular users with tenant:manage permission can update their own tenant
        if not current_user.is_super_admin:
            if current_user.tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail="You can only update your own tenant settings")
            
            # Check if user has tenant:manage permission
            permissions = RBACService.get_user_permissions(db, current_user.id, current_user.tenant_id)
            if "tenant:manage" not in [p["name"] for p in permissions.get("permissions", [])]:
                raise HTTPException(status_code=403, detail="You don't have permission to manage tenant settings")
        
        tenant = TenantService.update_tenant(db, tenant_id, tenant_update, current_user)
        db.commit()
        
        # Add user count
        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        
        # Convert to dict and add user_count before validation
        tenant_dict = tenant.__dict__.copy()
        tenant_dict['user_count'] = user_count
        tenant_dict.pop('_sa_instance_state', None)
        
        tenant_response = TenantResponse.model_validate(tenant_dict)
        return tenant_response
    
    except HTTPException:
        raise
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Tenant update failed")

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Delete tenant"""
    try:
        result = TenantService.delete_tenant(db, tenant_id, super_admin)
        db.commit()
        
        return SuccessResponse(
            message="Tenant deleted successfully",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Tenant deletion failed")

# ================================
# TENANT IDENTITY PROVIDERS
# ================================

@router.post("/{tenant_id}/identity-providers/microsoft", response_model=IdentityProviderResponse, response_model_exclude_none=True)
async def create_microsoft_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_data: MicrosoftIdentityProviderCreate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Configure Microsoft Entra ID Provider for tenant"""
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

@router.post("/{tenant_id}/identity-providers/google", response_model=IdentityProviderResponse, response_model_exclude_none=True)
async def create_google_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_data: GoogleIdentityProviderCreate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Configure Google Workspace Provider for tenant"""
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

@router.get("/{tenant_id}/identity-providers", response_model=IdentityProviderListResponse, response_model_exclude_none=True)
async def list_tenant_identity_providers(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """List all Identity Providers for a tenant"""
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

@router.put("/{tenant_id}/identity-providers/{provider_id}", response_model=IdentityProviderResponse, response_model_exclude_none=True)
async def update_identity_provider(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    provider_id: uuid.UUID = Path(..., description="Provider ID"),
    provider_update: IdentityProviderUpdate = ...,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update Identity Provider configuration"""
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
    """Delete Identity Provider"""
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

@router.get("/stats/", response_model=TenantStatsResponse, response_model_exclude_none=True)
async def get_tenant_statistics(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get overall tenant statistics"""
    try:
        stats = TenantService.get_tenant_statistics(db)
        return TenantStatsResponse(**stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get tenant statistics")

@router.get("/{tenant_id}/stats")
async def get_tenant_details_stats(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed statistics for a specific tenant"""
    try:
        stats = TenantService.get_tenant_details_stats(db, tenant_id)
        return stats
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
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
    """Activate tenant"""
    try:
        TenantService.activate_tenant(db, tenant_id, super_admin)
        db.commit()
        return SuccessResponse(message="Tenant activated successfully")
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to activate tenant")

@router.post("/{tenant_id}/deactivate")
async def deactivate_tenant(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate tenant"""
    try:
        result = TenantService.deactivate_tenant(db, tenant_id, super_admin)
        db.commit()
        return SuccessResponse(
            message="Tenant deactivated successfully",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
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
    """Export tenant data for backup/migration"""
    try:
        export_data = TenantService.export_tenant_data(
            db, tenant_id, include_users, include_projects, include_audit_logs
        )
        
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
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to export tenant data")

@router.get("/{tenant_id}/usage-report")
async def get_tenant_usage_report(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    days: int = Query(default=30, ge=1, le=365, description="Report period in days"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed usage report for a tenant"""
    try:
        report = TenantService.get_tenant_usage_report(db, tenant_id, days)
        return report
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate usage report")

# ================================
# TENANT HEALTH MONITORING
# ================================

@router.get("/{tenant_id}/health")
async def get_tenant_health(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Check tenant health"""
    try:
        health_data = TenantService.get_tenant_health(db, tenant_id)
        return health_data
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get tenant health")

# ================================
# TENANT CLONING
# ================================

@router.post("/{tenant_id}/clone")
async def clone_tenant(
    tenant_id: uuid.UUID = Path(..., description="Source tenant ID"),
    new_tenant_name: str = Query(..., description="New tenant name"),
    new_tenant_slug: str = Query(..., description="New tenant slug"),
    include_users: bool = Query(default=False, description="Include users in clone"),
    include_data: bool = Query(default=False, description="Include business data in clone"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Clone an existing tenant"""
    try:
        clone_summary = TenantService.clone_tenant(
            db, tenant_id, new_tenant_name, new_tenant_slug, 
            include_users, include_data, super_admin
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Tenant cloned successfully as '{new_tenant_name}'",
            data=clone_summary
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clone tenant")

# ================================
# TENANT MAINTENANCE
# ================================

@router.post("/{tenant_id}/maintenance/cleanup")
async def tenant_maintenance_cleanup(
    tenant_id: uuid.UUID = Path(..., description="Tenant ID"),
    cleanup_type: str = Query(..., description="Type: sessions, audit_logs, inactive_users"),
    days_old: int = Query(default=30, ge=1, le=365, description="Remove data older than N days"),
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Perform maintenance cleanup for specific tenant"""
    try:
        result = TenantService.cleanup_tenant_data(
            db, tenant_id, cleanup_type, days_old, super_admin
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Tenant cleanup completed: {result['records_removed']} records removed",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Tenant cleanup operation failed")