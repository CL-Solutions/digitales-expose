# ================================
# USER MANAGEMENT API ROUTES (api/v1/users.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.dependencies import (
    get_db, get_current_user, require_permission, 
    get_pagination_params, get_sort_params,
    require_same_tenant_or_super_admin
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
from app.models.user import User, UserSession
from app.core.exceptions import AppException
from typing import List, Optional
import uuid

router = APIRouter()

# ================================
# USER PROFILE MANAGEMENT
# ================================

@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Aktuelles User-Profil abrufen"""
    try:
        # Get user permissions
        from app.models.utils import get_user_permissions
        permissions = []
        if current_user.tenant_id:
            permissions = get_user_permissions(db, current_user.id, current_user.tenant_id)
        
        # Create profile response
        profile_data = UserProfileResponse.model_validate(current_user)
        profile_data.permissions = permissions
        
        return profile_data
    
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
    """Beendet User Sessions"""
    try:
        # Users können nur ihre eigenen Sessions beenden (außer Admins)
        if not current_user.is_super_admin and user_id != current_user.id:
            from app.dependencies import check_user_permission
            if not check_user_permission(db, current_user.id, current_user.tenant_id, "users", "update"):
                raise HTTPException(status_code=403, detail="Access denied")
        
        if session_data.terminate_all:
            # Terminate all sessions for user
            deleted_count = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).delete()
        elif session_data.session_id:
            # Terminate specific session
            deleted_count = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.id == session_data.session_id
            ).delete()
        else:
            raise HTTPException(status_code=400, detail="Must specify session_id or terminate_all")
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "SESSIONS_TERMINATED", current_user.id, current_user.tenant_id,
            {
                "target_user_id": str(user_id), 
                "terminated_sessions": deleted_count,
                "terminate_all": session_data.terminate_all
            }
        )
        
        db.commit()
        return SuccessResponse(
            message=f"Terminated {deleted_count} session(s)",
            data={"terminated_count": deleted_count}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to terminate sessions")

# ================================
# USER INVITATIONS
# ================================

@router.post("/invite", response_model=UserInviteResponse)
async def invite_user(
    invite_data: UserInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "invite"))
):
    """Lädt einen neuen User ein"""
    try:
        from app.models.user import User
        from datetime import datetime, timedelta
        import secrets
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == invite_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")
        
        # Create invitation record (would need InviteToken model)
        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=invite_data.expires_in_days)
        
        # Send invitation email
        from app.utils.email import email_service
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        
        invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={invite_token}"
        
        # Would implement invitation email template
        await email_service.send_email(
            to_emails=[invite_data.email],
            subject=f"Invitation to join {tenant.name}",
            template_name="user_invitation",
            template_data={
                "invited_by": current_user.full_name,
                "organization": tenant.name,
                "invitation_link": invitation_link,
                "expires_days": invite_data.expires_in_days,
                "custom_message": invite_data.welcome_message
            }
        )
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "USER_INVITED", current_user.id, current_user.tenant_id,
            {"invited_email": invite_data.email, "expires_at": expires_at.isoformat()}
        )
        
        db.commit()
        
        # Return invitation response (would use actual InviteToken model)
        return UserInviteResponse(
            id=uuid.uuid4(),  # Would be actual invite ID
            email=invite_data.email,
            invited_by=current_user.id,
            expires_at=expires_at,
            is_accepted=False,
            accepted_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send invitation")

# ================================
# BULK OPERATIONS
# ================================

@router.post("/bulk/create", response_model=UserBulkCreateResponse)
async def bulk_create_users(
    bulk_data: UserBulkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "create"))
):
    """Erstellt mehrere User auf einmal"""
    try:
        from app.services.auth_service import AuthService
        
        created_users = []
        failed_users = []
        
        for user_data in bulk_data.users:
            try:
                # Use default role if not specified
                if not user_data.role_ids and bulk_data.default_role_id:
                    user_data.role_ids = [bulk_data.default_role_id]
                
                user_data.send_welcome_email = bulk_data.send_welcome_emails
                
                user = await AuthService.create_user_by_admin(
                    db, user_data, current_user.tenant_id, current_user
                )
                created_users.append(UserResponse.model_validate(user))
                
            except Exception as e:
                failed_users.append({
                    "email": user_data.email,
                    "error": str(e)
                })
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "BULK_USER_CREATE", current_user.id, current_user.tenant_id,
            {
                "total_users": len(bulk_data.users),
                "created_count": len(created_users),
                "failed_count": len(failed_users)
            }
        )
        
        db.commit()
        
        return UserBulkCreateResponse(
            created_users=created_users,
            failed_users=failed_users,
            total_created=len(created_users),
            total_failed=len(failed_users)
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Bulk user creation failed")

@router.post("/bulk/action", response_model=UserBulkActionResponse)
async def bulk_user_action(
    action_data: UserBulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "update"))
):
    """Führt Bulk-Aktionen auf Users aus"""
    try:
        successful_user_ids = []
        failed_user_ids = []
        errors = {}
        
        for user_id in action_data.user_ids:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    failed_user_ids.append(user_id)
                    errors[str(user_id)] = "User not found"
                    continue
                
                # Prevent action on self for certain operations
                if user_id == current_user.id and action_data.action in ["deactivate", "delete", "lock"]:
                    failed_user_ids.append(user_id)
                    errors[str(user_id)] = "Cannot perform this action on yourself"
                    continue
                
                # Apply action
                if action_data.action == "activate":
                    user.is_active = True
                elif action_data.action == "deactivate":
                    user.is_active = False
                elif action_data.action == "verify":
                    user.is_verified = True
                elif action_data.action == "lock":
                    user.locked_until = datetime.utcnow() + timedelta(hours=24)
                elif action_data.action == "unlock":
                    user.locked_until = None
                    user.failed_login_attempts = 0
                elif action_data.action == "delete":
                    user.is_active = False
                    user.email = f"deleted_{user.id}@deleted.local"
                
                successful_user_ids.append(user_id)
                
            except Exception as e:
                failed_user_ids.append(user_id)
                errors[str(user_id)] = str(e)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "BULK_USER_ACTION", current_user.id, current_user.tenant_id,
            {
                "action": action_data.action,
                "total_users": len(action_data.user_ids),
                "successful_count": len(successful_user_ids),
                "failed_count": len(failed_user_ids),
                "reason": action_data.reason
            }
        )
        
        db.commit()
        
        return UserBulkActionResponse(
            successful_user_ids=successful_user_ids,
            failed_user_ids=failed_user_ids,
            errors=errors,
            total_processed=len(action_data.user_ids),
            total_successful=len(successful_user_ids)
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Bulk action failed")

# ================================
# USER STATISTICS & ANALYTICS
# ================================

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """User-Statistiken für den aktuellen Tenant"""
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Base query for tenant users
        base_query = db.query(User)
        if not current_user.is_super_admin:
            base_query = base_query.filter(User.tenant_id == current_user.tenant_id)
        
        # Count totals
        total_users = base_query.count()
        active_users = base_query.filter(User.is_active == True).count()
        verified_users = base_query.filter(User.is_verified == True).count()
        
        # Users by auth method
        auth_method_stats = db.query(
            User.auth_method,
            func.count(User.id).label('count')
        ).filter(
            User.tenant_id == current_user.tenant_id if not current_user.is_super_admin else True
        ).group_by(User.auth_method).all()
        
        users_by_auth_method = {stat.auth_method: stat.count for stat in auth_method_stats}
        
        # Recent logins (last 7 days)
        recent_date = datetime.utcnow() - timedelta(days=7)
        recent_logins = base_query.filter(
            User.last_login_at >= recent_date
        ).count()
        
        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            users_by_auth_method=users_by_auth_method,
            recent_logins=recent_logins
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user statistics")

# ================================
# USER SECURITY INFO
# ================================

@router.get("/{user_id}/security", response_model=UserSecurityInfo)
async def get_user_security_info(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Security-Informationen für einen User"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Count active sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        # Get recent security events
        from app.models.audit import AuditLog
        recent_events = db.query(AuditLog).filter(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.action.in_([
                    "LOGIN_SUCCESS", "LOGIN_FAILED", "PASSWORD_CHANGED",
                    "ACCOUNT_LOCKED", "EMAIL_VERIFIED"
                ]),
                AuditLog.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).order_by(desc(AuditLog.created_at)).limit(10).all()
        
        security_events = []
        for event in recent_events:
            security_events.append({
                "event_type": event.action,
                "timestamp": event.created_at.isoformat(),
                "ip_address": str(event.ip_address) if event.ip_address else None,
                "details": event.new_values or {}
            })
        
        return UserSecurityInfo(
            user_id=user.id,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            last_login_at=user.last_login_at,
            last_password_change=None,  # Would need to track this
            active_sessions_count=active_sessions,
            two_factor_enabled=False,  # Future feature
            recent_security_events=security_events
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get security info")

# ================================
# PASSWORD MANAGEMENT FOR USERS
# ================================

@router.post("/me/change-password")
async def change_current_user_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Passwort des aktuellen Users ändern"""
    try:
        from app.core.security import verify_password, get_password_hash
        
        # Only for local auth users
        if current_user.auth_method != "local":
            raise HTTPException(
                status_code=400, 
                detail="Password change not available for OAuth users"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        current_user.password_hash = get_password_hash(password_data.new_password)
        
        # Invalidate all other sessions except current one
        from app.models.user import UserSession
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id
        ).delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PASSWORD_CHANGED", current_user.id, current_user.tenant_id,
            {"self_service": True}
        )
        
        db.commit()
        return SuccessResponse(message="Password changed successfully. Please log in again.")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Password change failed")

# ================================
# USER EXPORT & REPORTS
# ================================

@router.get("/export")
async def export_users(
    format: str = Query(default="csv", description="Export format: csv, xlsx, json"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """Export User-Liste"""
    try:
        # Get all users in tenant
        query = db.query(User)
        if not current_user.is_super_admin:
            query = query.filter(User.tenant_id == current_user.tenant_id)
        
        users = query.all()
        
        if format == "json":
            user_data = []
            for user in users:
                user_data.append({
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "auth_method": user.auth_method,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
                })
            
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"users": user_data, "total": len(user_data)})
        
        elif format in ["csv", "xlsx"]:
            # Would implement CSV/Excel export
            return SuccessResponse(
                message=f"Export initiated in {format} format",
                data={"download_url": f"/api/v1/exports/users-{uuid.uuid4().hex}.{format}"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Export failed") profile")

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Aktuelles User-Profil aktualisieren"""
    try:
        # Update allowed fields
        if user_update.first_name is not None:
            current_user.first_name = user_update.first_name
        if user_update.last_name is not None:
            current_user.last_name = user_update.last_name
        if user_update.avatar_url is not None:
            current_user.avatar_url = user_update.avatar_url
        
        # Log the change
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PROFILE_UPDATED", current_user.id, current_user.tenant_id,
            {"updated_fields": user_update.model_dump(exclude_unset=True)}
        )
        
        db.commit()
        return UserResponse.model_validate(current_user)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Profile update failed")

# ================================
# USER MANAGEMENT (ADMIN)
# ================================

@router.get("/", response_model=UserListResponse)
async def list_users(
    filter_params: UserFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read"))
):
    """Liste aller User im Tenant (mit Filtering/Pagination)"""
    try:
        # Base query - nur User im gleichen Tenant (außer Super-Admin)
        query = db.query(User)
        
        if not current_user.is_super_admin:
            query = query.filter(User.tenant_id == current_user.tenant_id)
        elif filter_params.tenant_id:
            query = query.filter(User.tenant_id == filter_params.tenant_id)
        
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
        
        # Apply pagination
        offset = (filter_params.page - 1) * filter_params.page_size
        users = query.offset(offset).limit(filter_params.page_size).all()
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Spezifischen User abrufen"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user permissions
        from app.models.utils import get_user_permissions
        permissions = []
        if user.tenant_id:
            permissions = get_user_permissions(db, user.id, user.tenant_id)
        
        profile_data = UserProfileResponse.model_validate(user)
        profile_data.permissions = permissions
        
        return profile_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID = Path(..., description="User ID"),
    user_update: UserUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "update")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """User aktualisieren"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        update_data = {}
        if user_update.first_name is not None:
            user.first_name = user_update.first_name
            update_data["first_name"] = user_update.first_name
        if user_update.last_name is not None:
            user.last_name = user_update.last_name
            update_data["last_name"] = user_update.last_name
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
            update_data["is_active"] = user_update.is_active
        if user_update.avatar_url is not None:
            user.avatar_url = user_update.avatar_url
            update_data["avatar_url"] = user_update.avatar_url
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "USER_UPDATED", current_user.id, user.tenant_id,
            {"target_user_id": str(user.id), "updates": update_data}
        )
        
        db.commit()
        return UserResponse.model_validate(user)
    
    except HTTPException:
        raise
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
    """User deaktivieren (Soft Delete)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
        # Soft delete (deactivate) instead of hard delete
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.local"  # Prevent email conflicts
        
        # Invalidate all user sessions
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "USER_DEACTIVATED", current_user.id, user.tenant_id,
            {"target_user_id": str(user.id)}
        )
        
        db.commit()
        return SuccessResponse(message="User deactivated successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="User deletion failed")

# ================================
# USER SESSIONS MANAGEMENT
# ================================

@router.get("/{user_id}/sessions", response_model=ActiveSessionsResponse)
async def get_user_sessions(
    user_id: uuid.UUID = Path(..., description="User ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("users", "read")),
    __: bool = Depends(require_same_tenant_or_super_admin())
):
    """Aktive Sessions eines Users abrufen"""
    try:
        # Users können nur ihre eigenen Sessions sehen (außer Admins)
        if not current_user.is_super_admin and user_id != current_user.id:
            from app.dependencies import check_user_permission
            if not check_user_permission(db, current_user.id, current_user.tenant_id, "users", "read"):
                raise HTTPException(status_code=403, detail="Access denied")
        
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        ).order_by(desc(UserSession.last_accessed_at)).all()
        
        session_responses = []
        for session in sessions:
            session_responses.append(UserSessionResponse(
                id=session.id,
                user_id=session.user_id,
                ip_address=str(session.ip_address) if session.ip_address else None,
                user_agent=session.user_agent,
                expires_at=session.expires_at,
                last_accessed_at=session.last_accessed_at,
                is_impersonation=session.impersonated_tenant_id is not None,
                impersonated_tenant_id=session.impersonated_tenant_id,
                **session.__dict__
            ))
        
        return ActiveSessionsResponse(
            sessions=session_responses,
            total_active=len(session_responses)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get user