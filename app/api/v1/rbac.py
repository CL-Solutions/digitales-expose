# ================================
# RBAC API ROUTES (api/v1/rbac.py) - NEW FILE USING RBACSERVICE
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user, require_permission, get_super_admin_user
from app.schemas.rbac import (
    RoleCreate, RoleUpdate, RoleResponse, RoleDetailResponse,
    RoleListResponse, PermissionResponse, PermissionCreate,
    RolePermissionUpdate, UserRoleAssignment, BulkRoleAssignment,
    RBACStatsResponse, RoleUsageReport, PermissionUsageReport,
    RBACComplianceReport
)
from app.schemas.base import SuccessResponse
from app.services.rbac_service import RBACService
from app.models.user import User
from app.core.exceptions import AppException
from typing import List, Optional
import uuid

router = APIRouter()

# ================================
# ROLE MANAGEMENT
# ================================

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "create"))
):
    """Create a new role - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        role = RBACService.create_role(db, role_data, tenant_id, current_user)
        db.commit()
        
        return RoleResponse.model_validate(role)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create role")

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in role names"),
    is_system_role: Optional[bool] = Query(None, description="Filter by system/custom roles"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """List all roles in tenant"""
    try:
        from app.models.rbac import Role
        from sqlalchemy import and_, or_
        
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        # Base query
        query = db.query(Role).filter(Role.tenant_id == tenant_id)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Role.name.ilike(search_term),
                    Role.description.ilike(search_term)
                )
            )
        
        if is_system_role is not None:
            query = query.filter(Role.is_system_role == is_system_role)
        
        # Count total
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        roles = query.order_by(Role.name).offset(offset).limit(page_size).all()
        
        # Get user count for each role
        role_responses = []
        for role in roles:
            from app.models.rbac import UserRole
            user_count = db.query(UserRole).filter(UserRole.role_id == role.id).count()
            
            role_response = RoleResponse.model_validate(role)
            role_response.user_count = user_count
            role_responses.append(role_response)
        
        return RoleListResponse(
            roles=role_responses,
            total=total,
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve roles")

@router.get("/roles/{role_id}", response_model=RoleDetailResponse)
async def get_role_details(
    role_id: uuid.UUID = Path(..., description="Role ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """Get role with permissions - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        role_data = RBACService.get_role_with_permissions(db, role_id, tenant_id)
        
        return RoleDetailResponse(**role_data)
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get role details")

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID = Path(..., description="Role ID"),
    role_update: RoleUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "update"))
):
    """Update role - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        role = RBACService.update_role(db, role_id, role_update, tenant_id, current_user)
        db.commit()
        
        return RoleResponse.model_validate(role)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update role")

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: uuid.UUID = Path(..., description="Role ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "delete"))
):
    """Delete role - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        result = RBACService.delete_role(db, role_id, tenant_id, current_user)
        db.commit()
        
        return SuccessResponse(
            message="Role deleted successfully",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete role")

# ================================
# ROLE PERMISSIONS MANAGEMENT
# ================================

@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: uuid.UUID = Path(..., description="Role ID"),
    permission_update: RolePermissionUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "update"))
):
    """Update role permissions - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        result = RBACService.update_role_permissions(
            db, role_id, 
            permission_update.add_permission_ids or [],
            permission_update.remove_permission_ids or [],
            tenant_id, current_user
        )
        db.commit()
        
        return SuccessResponse(
            message="Role permissions updated successfully",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update role permissions")

@router.post("/roles/{role_id}/clone")
async def clone_role(
    role_id: uuid.UUID = Path(..., description="Source role ID"),
    new_role_name: str = Query(..., description="New role name"),
    new_role_description: Optional[str] = Query(None, description="New role description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "create"))
):
    """Clone an existing role - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        new_role = RBACService.clone_role(
            db, role_id, new_role_name, new_role_description, tenant_id, current_user
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Role cloned successfully as '{new_role_name}'",
            data={"new_role_id": str(new_role.id)}
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clone role")

# ================================
# PERMISSION MANAGEMENT
# ================================

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = Query(None, description="Filter by resource"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """List all available permissions"""
    try:
        from app.models.rbac import Permission
        
        query = db.query(Permission)
        
        if resource:
            query = query.filter(Permission.resource == resource)
        
        permissions = query.order_by(Permission.resource, Permission.action).all()
        
        return [PermissionResponse.model_validate(perm) for perm in permissions]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve permissions")

@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("permissions", "create"))
):
    """Create a new permission - Uses RBACService"""
    try:
        permission = RBACService.create_permission(db, permission_data)
        db.commit()
        
        return PermissionResponse.model_validate(permission)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create permission")

# ================================
# BULK ROLE OPERATIONS
# ================================

@router.post("/roles/bulk-assign")
async def bulk_assign_roles(
    assignment_data: BulkRoleAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "assign"))
):
    """Assign roles to multiple users - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        result = RBACService.bulk_assign_roles(
            db, assignment_data.user_ids, assignment_data.role_ids,
            tenant_id, assignment_data.expires_at, current_user
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Bulk assignment completed: {result['successful_assignments']} successful",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to perform bulk role assignment")

# ================================
# USER PERMISSION CHECKS
# ================================

@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """Get all permissions for a user - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        permissions_data = RBACService.get_user_permissions(db, user_id, tenant_id)
        
        return permissions_data
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user permissions")

@router.get("/users/{user_id}/permissions/check")
async def check_user_permission(
    user_id: uuid.UUID = Path(..., description="User ID"),
    resource: str = Query(..., description="Resource name"),
    action: str = Query(..., description="Action name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """Check if user has specific permission - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        result = RBACService.check_user_permission(db, user_id, tenant_id, resource, action)
        
        return {
            "user_id": str(user_id),
            "resource": resource,
            "action": action,
            "has_permission": result["has_permission"],
            "granted_via_roles": result["granted_via_roles"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to check user permission")

# ================================
# RBAC STATISTICS & REPORTS
# ================================

@router.get("/stats", response_model=RBACStatsResponse)
async def get_rbac_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """Get RBAC statistics - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id if not current_user.is_super_admin else None
        stats = RBACService.get_rbac_statistics(db, tenant_id)
        
        return RBACStatsResponse(**stats)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get RBAC statistics")

@router.get("/reports/role-usage")
async def get_role_usage_report(
    days: int = Query(default=30, ge=1, le=365, description="Report period in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """Get role usage report - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        report = RBACService.get_role_usage_report(db, tenant_id, days)
        
        return {
            "tenant_id": str(tenant_id),
            "report_period_days": days,
            "role_usage": report
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate role usage report")

@router.get("/reports/permission-usage")
async def get_permission_usage_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("permissions", "read"))
):
    """Get permission usage report - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id if not current_user.is_super_admin else None
        report = RBACService.get_permission_usage_report(db, tenant_id)
        
        return {
            "tenant_id": str(tenant_id) if tenant_id else "global",
            "permission_usage": report
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate permission usage report")

@router.get("/reports/compliance")
async def get_rbac_compliance_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "read"))
):
    """Get RBAC compliance report - Uses RBACService"""
    try:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        report = RBACService.get_rbac_compliance_report(db, tenant_id)
        
        return RBACComplianceReport(**report)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")

# ================================
# SUPER ADMIN RBAC OPERATIONS
# ================================

@router.get("/global/stats")
async def get_global_rbac_statistics(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get global RBAC statistics (Super Admin only) - Uses RBACService"""
    try:
        stats = RBACService.get_rbac_statistics(db, tenant_id=None)
        
        return {
            "global_stats": stats,
            "generated_at": "2024-01-01T12:00:00Z"  # Would use actual timestamp
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get global RBAC statistics")

@router.get("/global/reports/permission-usage")
async def get_global_permission_usage_report(
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Get global permission usage report (Super Admin only) - Uses RBACService"""
    try:
        report = RBACService.get_permission_usage_report(db, tenant_id=None)
        
        return {
            "scope": "global",
            "permission_usage": report
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate global permission usage report")