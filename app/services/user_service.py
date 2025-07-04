# ================================
# USER SERVICE (services/user_service.py)
# ================================

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.user import User, UserSession
from app.models.audit import AuditLog
from app.schemas.user import UserUpdate, UserInviteRequest, UserBulkCreateRequest, UserBulkActionRequest
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

audit_logger = AuditLogger()

class UserService:
    """Service for user management operations"""
    
    @staticmethod
    def update_user_profile(
        db: Session,
        user_id: uuid.UUID,
        user_update: UserUpdate,
        current_user: User
    ) -> User:
        """Update user profile information"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Store old values for audit
        old_values = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "avatar_url": user.avatar_url,
            "settings": user.settings,
            "provision_percentage": user.provision_percentage
        }
        
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
        if user_update.settings is not None:
            # Merge settings to preserve existing values
            if user.settings is None:
                user.settings = {}
            user.settings = {**user.settings, **user_update.settings}
            update_data["settings"] = user.settings
        if user_update.provision_percentage is not None:
            user.provision_percentage = user_update.provision_percentage
            update_data["provision_percentage"] = user_update.provision_percentage
        
        # Audit log
        audit_logger.log_auth_event(
            db, "USER_UPDATED", current_user.id, user.tenant_id,
            {"target_user_id": str(user.id), "updates": update_data}
        )
        
        return user
    
    @staticmethod
    def deactivate_user(
        db: Session,
        user_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Deactivate user (soft delete)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Prevent self-deletion
        if user.id == current_user.id:
            raise AppException("Cannot delete yourself", 400, "SELF_DELETE_FORBIDDEN")
        
        # Soft delete (deactivate) instead of hard delete
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.invalid"  # Prevent email conflicts
        
        # Invalidate all user sessions
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()
        
        # Audit log
        audit_logger.log_auth_event(
            db, "USER_DEACTIVATED", current_user.id, user.tenant_id,
            {"target_user_id": str(user.id)}
        )
        
        return {"user_id": str(user.id), "deactivated": True}
    
    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Get active sessions for a user"""
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        ).order_by(desc(UserSession.last_accessed_at)).all()
        
        session_list = []
        for session in sessions:
            session_list.append({
                "id": str(session.id),
                "ip_address": str(session.ip_address) if session.ip_address else None,
                "user_agent": session.user_agent,
                "created_at": session.created_at.isoformat(),
                "last_accessed_at": session.last_accessed_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_current": False,  # Would determine current session
                "is_impersonation": session.impersonated_tenant_id is not None
            })
        
        return session_list
    
    @staticmethod
    def terminate_user_sessions(
        db: Session,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID],
        terminate_all: bool,
        current_user: User
    ) -> Dict[str, Any]:
        """Terminate user sessions"""
        if terminate_all:
            # Terminate all sessions for user
            deleted_count = db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).delete()
        elif session_id:
            # Terminate specific session
            deleted_count = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.id == session_id
            ).delete()
        else:
            raise AppException("Must specify session_id or terminate_all", 400, "INVALID_REQUEST")
        
        # Audit log
        audit_logger.log_auth_event(
            db, "SESSIONS_TERMINATED", current_user.id, current_user.tenant_id,
            {
                "target_user_id": str(user_id), 
                "terminated_sessions": deleted_count,
                "terminate_all": terminate_all
            }
        )
        
        return {"terminated_count": deleted_count}
    
    @staticmethod
    async def invite_user(
        db: Session,
        invite_data: UserInviteRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """Invite a new user"""
        from app.config import settings
        from datetime import timedelta
        import secrets
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == invite_data.email).first()
        if existing_user:
            raise AppException("User with this email already exists", 400, "EMAIL_EXISTS")
        
        # Create invitation record (would need InviteToken model)
        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=invite_data.expires_in_days)
        
        # Send invitation email
        from app.utils.email import email_service
        from app.models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        
        invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={invite_token}"
        
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
        audit_logger.log_auth_event(
            db, "USER_INVITED", current_user.id, current_user.tenant_id,
            {"invited_email": invite_data.email, "expires_at": expires_at.isoformat()}
        )
        
        return {
            "email": invite_data.email,
            "expires_at": expires_at.isoformat(),
            "invitation_sent": True
        }
    
    @staticmethod
    async def bulk_create_users(
        db: Session,
        bulk_data: UserBulkCreateRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """Create multiple users at once"""
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
                created_users.append({
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.full_name
                })
                
            except Exception as e:
                failed_users.append({
                    "email": user_data.email,
                    "error": str(e)
                })
        
        # Audit log
        audit_logger.log_auth_event(
            db, "BULK_USER_CREATE", current_user.id, current_user.tenant_id,
            {
                "total_users": len(bulk_data.users),
                "created_count": len(created_users),
                "failed_count": len(failed_users)
            }
        )
        
        return {
            "created_users": created_users,
            "failed_users": failed_users,
            "total_created": len(created_users),
            "total_failed": len(failed_users)
        }
    
    @staticmethod
    def bulk_user_action(
        db: Session,
        action_data: UserBulkActionRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """Perform bulk actions on users"""
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
        
        return {
            "successful_user_ids": successful_user_ids,
            "failed_user_ids": failed_user_ids,
            "errors": errors,
            "total_processed": len(action_data.user_ids),
            "total_successful": len(successful_user_ids)
        }
    
    @staticmethod
    def get_user_statistics(
        db: Session,
        tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get user statistics for tenant or global"""
        # Base query
        base_query = db.query(User)
        if tenant_id:
            base_query = base_query.filter(User.tenant_id == tenant_id)
        else:
            base_query = base_query.filter(User.tenant_id.isnot(None))  # Exclude super admins
        
        # Count totals
        total_users = base_query.count()
        active_users = base_query.filter(User.is_active == True).count()
        verified_users = base_query.filter(User.is_verified == True).count()
        
        # Users by auth method
        auth_method_stats = db.query(
            User.auth_method,
            func.count(User.id).label('count')
        ).filter(
            User.tenant_id == tenant_id if tenant_id else User.tenant_id.isnot(None)
        ).group_by(User.auth_method).all()
        
        users_by_auth_method = {stat.auth_method: stat.count for stat in auth_method_stats}
        
        # Recent logins (last 7 days)
        recent_date = datetime.utcnow() - timedelta(days=7)
        recent_logins = base_query.filter(
            User.last_login_at >= recent_date
        ).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "users_by_auth_method": users_by_auth_method,
            "recent_logins": recent_logins
        }
    
    @staticmethod
    def get_user_security_info(
        db: Session,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get security information for a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Count active sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        # Get recent security events
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
        
        return {
            "user_id": str(user.id),
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "last_password_change": None,  # Would need to track this
            "active_sessions_count": active_sessions,
            "two_factor_enabled": False,  # Future feature
            "recent_security_events": security_events
        }
    
    @staticmethod
    def change_user_password(
        db: Session,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Change user password"""
        from app.core.security import verify_password, get_password_hash
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Only for local auth users
        if user.auth_method != "local":
            raise AppException(
                "Password change not available for OAuth users", 
                400, 
                "OAUTH_USER_PASSWORD_CHANGE"
            )
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise AppException("Current password is incorrect", 400, "INVALID_PASSWORD")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        
        # Invalidate all other sessions except current one
        db.query(UserSession).filter(
            UserSession.user_id == user.id
        ).delete()
        
        # Audit log
        audit_logger.log_auth_event(
            db, "PASSWORD_CHANGED", user.id, user.tenant_id,
            {"self_service": True}
        )
        
        return {"message": "Password changed successfully", "sessions_invalidated": True}
    
    @staticmethod
    def export_users(
        db: Session,
        tenant_id: uuid.UUID,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export user list"""
        query = db.query(User).filter(User.tenant_id == tenant_id)
        users = query.all()
        
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
        
        if format == "json":
            return {"users": user_data, "total": len(user_data)}
        else:
            # For CSV/Excel, would return download URL
            return {
                "message": f"Export initiated in {format} format",
                "download_url": f"/api/v1/exports/users-{uuid.uuid4().hex}.{format}",
                "total_users": len(user_data)
            }
    
    @staticmethod
    def get_user_roles(
        db: Session,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get roles assigned to a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        from app.models.rbac import UserRole, Role
        user_roles = db.query(Role).join(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        ).all()
        
        roles_data = []
        for role in user_roles:
            role_assignment = db.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role.id
            ).first()
            
            roles_data.append({
                "role_id": str(role.id),
                "role_name": role.name,
                "role_description": role.description,
                "granted_at": role_assignment.granted_at.isoformat() if role_assignment else None,
                "expires_at": role_assignment.expires_at.isoformat() if role_assignment and role_assignment.expires_at else None,
                "is_expired": role_assignment.is_expired if role_assignment else False
            })
        
        return {
            "user_id": str(user_id),
            "roles": roles_data,
            "total_roles": len(roles_data)
        }
    
    @staticmethod
    def assign_role_to_user(
        db: Session,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID,
        expires_in_days: Optional[int],
        current_user: User
    ) -> Dict[str, Any]:
        """Assign a role to a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        from app.models.rbac import Role, UserRole
        role = db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id
        ).first()
        if not role:
            raise AppException("Role not found", 404, "ROLE_NOT_FOUND")
        
        # Check if assignment already exists
        existing = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id
        ).first()
        if existing:
            raise AppException("Role already assigned to user", 400, "ROLE_ALREADY_ASSIGNED")
        
        # Create role assignment
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            granted_by=current_user.id,
            expires_at=expires_at
        )
        db.add(user_role)
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_ASSIGNED", current_user.id, tenant_id,
            {
                "target_user_id": str(user_id),
                "role_id": str(role_id),
                "role_name": role.name,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        )
        
        return {
            "role_name": role.name,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "assigned": True
        }
    
    @staticmethod
    def remove_role_from_user(
        db: Session,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Remove a role from a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        from app.models.rbac import UserRole, Role
        user_role = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.tenant_id == tenant_id
        ).first()
        
        if not user_role:
            raise AppException("Role assignment not found", 404, "ROLE_ASSIGNMENT_NOT_FOUND")
        
        # Get role name for audit
        role = db.query(Role).filter(Role.id == role_id).first()
        role_name = role.name if role else "Unknown"
        
        # Remove role assignment
        db.delete(user_role)
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ROLE_REMOVED", current_user.id, tenant_id,
            {
                "target_user_id": str(user_id),
                "role_id": str(role_id),
                "role_name": role_name
            }
        )
        
        return {"role_name": role_name, "removed": True}
    
    @staticmethod
    def get_problematic_users(
        db: Session,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Identify users with problems"""
        problematic_users = []
        
        # Base query
        base_filter = User.tenant_id == tenant_id if tenant_id else User.tenant_id.isnot(None)
        
        # Locked users
        locked_users = db.query(User).filter(
            and_(
                base_filter,
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
            and_(
                base_filter,
                User.failed_login_attempts >= 3
            )
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
                base_filter,
                User.is_verified == False,
                User.created_at < datetime.utcnow() - timedelta(days=7)
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
            and_(
                base_filter,
                or_(
                    User.last_login_at < datetime.utcnow() - timedelta(days=90),
                    User.last_login_at.is_(None)
                ),
                User.is_active == True
            )
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
    
    @staticmethod
    def unlock_user_account(
        db: Session,
        user_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Unlock user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Unlock account
        user.locked_until = None
        user.failed_login_attempts = 0
        
        # Audit log
        audit_logger.log_auth_event(
            db, "ACCOUNT_UNLOCKED_BY_ADMIN", current_user.id, user.tenant_id,
            {
                "target_user_id": str(user.id),
                "target_email": user.email
            }
        )
        
        return {"user_email": user.email, "unlocked": True}