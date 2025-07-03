# ================================
# USER MANAGEMENT API ROUTES (api/v1/users.py) - UPDATED TO USE SERVICES
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.config import settings
from app.dependencies import (
    get_db, get_current_user, require_permission, 
    get_pagination_params, get_sort_params,
    require_same_tenant_or_super_admin, get_current_tenant_id
)
from app.schemas.user import (
    UserResponse, UserListResponse, UserUpdate, 
    UserFilterParams, ChangePasswordRequest,
    UserProfileResponse, UserStatsResponse,
    UserSessionResponse, ActiveSessionsResponse,
    SessionTerminateRequest, UserInviteRequest,
    UserInviteResponse, UserBulkCreateRequest,
    UserBulkCreateResponse, UserBulkActionRequest,
    UserBulkActionResponse, UserSecurityInfo
)
from app.schemas.base import SuccessResponse
from app.services.user_service import UserService
from app.services.rbac_service import RBACService
from app.models.user import User, UserSession
from app.core.exceptions import AppException
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

router = APIRouter()

# ================================
# USER PROFILE MANAGEMENT
# ================================

@router.get("/me/", response_model=UserProfileResponse, response_model_exclude_none=True)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile - Uses RBACService for permissions"""
    try:
        # Get user permissions using RBACService
        permissions = []
        if current_user.tenant_id:
            permissions_data = RBACService.get_user_permissions(db, current_user.id, current_user.tenant_id)
            permissions = [perm["name"] for perm in permissions_data.get("permissions", [])]
        
        # Create profile response
        profile_data = UserProfileResponse.model_validate(current_user)
        profile_data.permissions = permissions
        profile_data.settings = current_user.settings or {}
        
        return profile_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@router.put("/me/", response_model=UserResponse, response_model_exclude_none=True)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile - Uses UserService"""
    try:
        user = UserService.update_user_profile(db, current_user.id, user_update, current_user)
        db.commit()
        return UserResponse.model_validate(user)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Profile update failed")

# ================================
# USER MANAGEMENT (ADMIN)
# ================================

@router.get("/", response_model=UserListResponse, response_model_exclude_none=True)
async def list_users(
    request: Request,
    filter_params: UserFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """List all users in tenant (with filtering/pagination)"""
    try:
        # Use the tenant_id from dependency (which handles impersonation)
        # If no tenant_id is available, use the user's tenant_id
        effective_tenant_id = tenant_id or current_user.tenant_id
        
        if not effective_tenant_id:
            # For super admins without tenant context, return empty list
            if current_user.is_super_admin:
                return UserListResponse(users=[], total=0, page=1, page_size=filter_params.page_size)
            else:
                raise HTTPException(status_code=400, detail="Tenant context required")
        
        # Base query - only users in the effective tenant
        query = db.query(User).filter(User.tenant_id == effective_tenant_id)
        
        # Apply filters
        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
        
        if filter_params.auth_method:
            query = query.filter(User.auth_method == filter_params.auth_method)
        
        if filter_params.is_active is not None:
            query = query.filter(User.is_active == filter_params.is_active)
        
        if filter_params.is_verified is not None:
            query = query.filter(User.is_verified == filter_params.is_verified)
        
        if filter_params.role_id:
            from app.models.rbac import UserRole
            query = query.join(UserRole).filter(UserRole.role_id == filter_params.role_id)
        
        # Count total
        total = query.count()
        
        # Apply sorting
        if filter_params.sort_by == "name":
            sort_field = User.first_name
        elif filter_params.sort_by == "email":
            sort_field = User.email
        elif filter_params.sort_by == "last_login":
            sort_field = User.last_login_at
        else:
            sort_field = User.created_at
        
        if filter_params.sort_order == "desc":
            sort_field = sort_field.desc()
        
        query = query.order_by(sort_field)
        
        # Apply pagination with eager loading of roles
        from sqlalchemy.orm import joinedload
        from app.models.rbac import UserRole, Role
        offset = (filter_params.page - 1) * filter_params.page_size
        users = query.options(
            joinedload(User.user_roles).joinedload(UserRole.role)
        ).offset(offset).limit(filter_params.page_size).all()
        
        # Get all managers for these users
        from app.services.user_team_service import UserTeamService
        
        # Build user responses with roles and managers
        user_responses = []
        for user in users:
            # Get roles from user_roles relationship, filtered by effective tenant
            user_roles = []
            for user_role in user.user_roles:
                if user_role.tenant_id == effective_tenant_id and user_role.role:
                    role_data = {
                        "id": str(user_role.role.id),
                        "name": user_role.role.name,
                        "description": user_role.role.description,
                        "is_system_role": user_role.role.is_system_role,
                        "tenant_id": str(user_role.role.tenant_id) if user_role.role.tenant_id else None,
                        "created_at": user_role.role.created_at,
                        "updated_at": user_role.role.updated_at,
                        "permissions": []  # We can populate this if needed
                    }
                    user_roles.append(role_data)
            
            # Get manager for this user (only one manager per user)
            managers = UserTeamService.get_user_managers(
                db=db,
                member_id=user.id,
                tenant_id=effective_tenant_id
            )
            
            # Format manager information (take first manager if exists)
            manager_info = None
            if managers:
                manager = managers[0]  # User can only have one manager
                manager_info = {
                    "id": str(manager.id),
                    "email": manager.email,
                    "first_name": manager.first_name,
                    "last_name": manager.last_name,
                    "full_name": f"{manager.first_name} {manager.last_name}".strip()
                }
            
            # Create user response dict and add roles
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "auth_method": user.auth_method,
                "is_super_admin": user.is_super_admin,
                "is_verified": user.is_verified,
                "last_login_at": user.last_login_at,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "roles": user_roles,
                "manager": manager_info
            }
            user_responses.append(UserResponse(**user_dict))
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        import traceback
        print(f"Error retrieving users: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@router.get("/{user_id}", response_model=UserProfileResponse, response_model_exclude_none=True)
async def get_user_by_id(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Get specific user - Uses RBACService for permissions"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user permissions using RBACService
        permissions = []
        if user.tenant_id:
            permissions_data = RBACService.get_user_permissions(db, user.id, user.tenant_id)
            permissions = [perm["name"] for perm in permissions_data.get("permissions", [])]
        
        profile_data = UserProfileResponse.model_validate(user)
        profile_data.permissions = permissions
        
        return profile_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user")

@router.put("/{user_id}", response_model=UserResponse, response_model_exclude_none=True)
async def update_user(
    user_update: UserUpdate,
    request: Request,
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "update"))
):
    """Update user - Uses UserService"""
    try:
        # Get the target user
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use the tenant_id from dependency (which handles impersonation)
        effective_tenant_id = tenant_id or current_user.tenant_id
        
        # Check tenant access
        if current_user.is_super_admin:
            # Super admin can only update users in the current tenant context
            if target_user.tenant_id != effective_tenant_id:
                raise HTTPException(status_code=403, detail="Access denied: user not in current tenant context")
        else:
            # Regular users can only update users in their own tenant
            if target_user.tenant_id != effective_tenant_id:
                raise HTTPException(status_code=403, detail="Access denied: different tenant")
        
        user = UserService.update_user_profile(db, user_id, user_update, current_user)
        db.commit()
        return UserResponse.model_validate(user)
    
    except HTTPException:
        raise
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="User update failed")

@router.delete("/{user_id}")
async def deactivate_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "delete")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Deactivate user (soft delete) - Uses UserService"""
    try:
        result = UserService.deactivate_user(db, user_id, current_user)
        db.commit()
        return SuccessResponse(message="User deactivated successfully")
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="User deletion failed")

# ================================
# USER SESSIONS MANAGEMENT
# ================================

@router.get("/{user_id}/sessions", response_model=ActiveSessionsResponse, response_model_exclude_none=True)
async def get_user_sessions(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Get active sessions for a user - Uses UserService"""
    try:
        # Users can only see their own sessions (except admins)
        if not current_user.is_super_admin and user_id != current_user.id:
            from app.dependencies import check_user_permission
            if not check_user_permission(db, current_user.id, current_user.tenant_id, "users", "read"):
                raise HTTPException(status_code=403, detail="Access denied")
        
        sessions_data = UserService.get_user_sessions(db, user_id)
        
        session_responses = []
        for session in sessions_data:
            session_responses.append(UserSessionResponse(
                id=uuid.UUID(session["id"]),
                user_id=user_id,
                ip_address=session["ip_address"],
                user_agent=session["user_agent"],
                expires_at=datetime.fromisoformat(session["expires_at"]),
                last_accessed_at=datetime.fromisoformat(session["last_accessed_at"]),
                is_impersonation=session["is_impersonation"],
                impersonated_tenant_id=None,  # Would parse from session data
                created_at=datetime.fromisoformat(session["created_at"]),
                updated_at=datetime.fromisoformat(session["created_at"])
            ))
        
        return ActiveSessionsResponse(
            sessions=session_responses,
            total_active=len(session_responses)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user sessions")

@router.delete("/{user_id}/sessions")
async def terminate_user_sessions(
    user_id: uuid.UUID = Path(..., description="User ID"),
    session_data: SessionTerminateRequest = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "update"))
):
    """Terminate user sessions - Uses UserService"""
    try:
        # Users can only terminate their own sessions (except admins)
        if not current_user.is_super_admin and user_id != current_user.id:
            from app.dependencies import check_user_permission
            if not check_user_permission(db, current_user.id, current_user.tenant_id, "users", "update"):
                raise HTTPException(status_code=403, detail="Access denied")
        
        result = UserService.terminate_user_sessions(
            db, user_id, session_data.session_id, session_data.terminate_all, current_user
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Terminated {result['terminated_count']} session(s)",
            data={"terminated_count": result["terminated_count"]}
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to terminate sessions")

# ================================
# USER INVITATIONS
# ================================

@router.post("/invite/", response_model=UserInviteResponse, response_model_exclude_none=True)
async def invite_user(
    invite_data: UserInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "invite"))
):
    """Invite a new user - Uses UserService"""
    try:
        result = await UserService.invite_user(db, invite_data, current_user)
        db.commit()
        
        # Return invitation response (would use actual InviteToken model)
        return UserInviteResponse(
            id=uuid.uuid4(),  # Would be actual invite ID
            email=invite_data.email,
            invited_by=current_user.id,
            expires_at=datetime.fromisoformat(result["expires_at"]),
            is_accepted=False,
            accepted_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send invitation")

# ================================
# BULK OPERATIONS
# ================================

@router.post("/bulk/create/", response_model=UserBulkCreateResponse, response_model_exclude_none=True)
async def bulk_create_users(
    bulk_data: UserBulkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "create"))
):
    """Create multiple users at once - Uses UserService"""
    try:
        result = await UserService.bulk_create_users(db, bulk_data, current_user)
        db.commit()
        
        return UserBulkCreateResponse(
            created_users=result["created_users"],
            failed_users=result["failed_users"],
            total_created=result["total_created"],
            total_failed=result["total_failed"]
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Bulk user creation failed")

@router.post("/bulk/action/", response_model=UserBulkActionResponse, response_model_exclude_none=True)
async def bulk_user_action(
    action_data: UserBulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "update"))
):
    """Perform bulk actions on users - Uses UserService"""
    try:
        result = UserService.bulk_user_action(db, action_data, current_user)
        db.commit()
        
        return UserBulkActionResponse(
            successful_user_ids=result["successful_user_ids"],
            failed_user_ids=result["failed_user_ids"],
            errors=result["errors"],
            total_processed=result["total_processed"],
            total_successful=result["total_successful"]
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Bulk action failed")

# ================================
# USER STATISTICS & ANALYTICS
# ================================

@router.get("/stats/", response_model=UserStatsResponse, response_model_exclude_none=True)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """User statistics for current tenant - Uses UserService"""
    try:
        tenant_id = None if current_user.is_super_admin else current_user.tenant_id
        stats = UserService.get_user_statistics(db, tenant_id)
        
        return UserStatsResponse(
            total_users=stats["total_users"],
            active_users=stats["active_users"],
            verified_users=stats["verified_users"],
            users_by_auth_method=stats["users_by_auth_method"],
            recent_logins=stats["recent_logins"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user statistics")

# ================================
# USER SECURITY INFO
# ================================

@router.get("/{user_id}/security", response_model=UserSecurityInfo, response_model_exclude_none=True)
async def get_user_security_info(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Security information for a user - Uses UserService"""
    try:
        security_info = UserService.get_user_security_info(db, user_id)
        
        return UserSecurityInfo(
            user_id=uuid.UUID(security_info["user_id"]),
            failed_login_attempts=security_info["failed_login_attempts"],
            locked_until=datetime.fromisoformat(security_info["locked_until"]) if security_info["locked_until"] else None,
            last_login_at=datetime.fromisoformat(security_info["last_login_at"]) if security_info["last_login_at"] else None,
            last_password_change=None,  # Would track this
            active_sessions_count=security_info["active_sessions_count"],
            two_factor_enabled=security_info["two_factor_enabled"],
            recent_security_events=security_info["recent_security_events"]
        )
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get security info")

# ================================
# PASSWORD MANAGEMENT FOR USERS
# ================================

@router.post("/me/change-password/")
async def change_current_user_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for current user - Uses UserService"""
    try:
        result = UserService.change_user_password(
            db, current_user.id, password_data.current_password, password_data.new_password
        )
        db.commit()
        return SuccessResponse(message=result["message"])
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Password change failed")

# ================================
# USER EXPORT & REPORTS
# ================================

@router.get("/export/")
async def export_users(
    format: str = Query(default="csv", description="Export format: csv, xlsx, json"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """Export user list - Uses UserService"""
    try:
        tenant_id = current_user.tenant_id if not current_user.is_super_admin else None
        result = UserService.export_users(db, tenant_id, format)
        
        if format == "json":
            from fastapi.responses import JSONResponse
            return JSONResponse(content=result)
        else:
            return SuccessResponse(
                message=result["message"],
                data={"download_url": result["download_url"], "total_users": result["total_users"]}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Export failed")

# ================================
# USER ROLE MANAGEMENT
# ================================

@router.get("/{user_id}/roles")
async def get_user_roles(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Get roles assigned to a user - Uses UserService"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        tenant_id = user.tenant_id if user.tenant_id else current_user.tenant_id
        result = UserService.get_user_roles(db, user_id, tenant_id)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user roles")

@router.post("/{user_id}/roles/{role_id}")
async def assign_role_to_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    role_id: uuid.UUID = Path(..., description="Role ID"),
    expires_in_days: Optional[int] = Query(None, description="Role expiration in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "assign"))
):
    """Assign a role to a user - Uses UserService"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        tenant_id = user.tenant_id if user.tenant_id else current_user.tenant_id
        result = UserService.assign_role_to_user(
            db, user_id, role_id, tenant_id, expires_in_days, current_user
        )
        db.commit()
        
        return SuccessResponse(
            message=f"Role '{result['role_name']}' assigned to user",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign role")

@router.delete("/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    role_id: uuid.UUID = Path(..., description="Role ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("roles", "assign"))
):
    """Remove a role from a user - Uses UserService"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        tenant_id = user.tenant_id if user.tenant_id else current_user.tenant_id
        result = UserService.remove_role_from_user(db, user_id, role_id, tenant_id, current_user)
        db.commit()
        
        return SuccessResponse(message=f"Role '{result['role_name']}' removed from user")
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove role")