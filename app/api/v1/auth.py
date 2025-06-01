# ================================
# AUTH API ROUTES (api/v1/auth.py) - UPDATED TO USE SERVICES
# ================================

import secrets
from fastapi import APIRouter, Depends, HTTPException, Path, status, Request, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user, get_super_admin_user
from app.schemas.auth import (
    LoginRequest, CreateUserRequest, TokenResponse, 
    ImpersonateRequest, PasswordResetRequest, 
    PasswordResetConfirm, EmailVerificationRequest,
    ChangePasswordRequest, OAuthCallbackRequest,
    OAuthUrlResponse, AuthStatusResponse,
    LoginHistoryResponse, SecurityEventResponse,
    RefreshTokenRequest
)
from app.services.auth_service import AuthService
from app.services.oauth_service import EnterpriseOAuthService
from app.services.user_service import UserService
from app.models.user import User
from app.models.tenant import Tenant
from app.core.exceptions import AppException
from app.config import settings
from typing import List
import uuid

router = APIRouter()

# ================================
# LOCAL AUTHENTICATION
# ================================

@router.post("/create-user", response_model=dict)
async def create_user_by_admin(
    user_data: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new user (admin only) - Uses AuthService"""
    try:
        # Tenant-ID from current user context (or from request for Super-Admin)
        tenant_id = user_data.tenant_id if current_user.is_super_admin else current_user.tenant_id
        
        user = await AuthService.create_user_by_admin(db, user_data, tenant_id, current_user)
        db.commit()
        
        return {
            "message": "User created successfully",
            "user_id": str(user.id),
            "email": user.email,
            "welcome_email_sent": user_data.send_welcome_email
        }
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.post("/login", response_model=TokenResponse)
async def login_local_user(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Local user login - Uses AuthService"""
    try:
        ip_address = request.client.host if request.client else None
        
        user, tokens = await AuthService.authenticate_local_user(
            db, login_data.email, login_data.password, ip_address
        )
        db.commit()
        
        return TokenResponse(**tokens, user_id=str(user.id))
    
    except AppException as e:
        db.rollback()
        # All auth errors returned as 401 with generic message
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User logout - Uses AuthService"""
    try:
        # Extract session token from header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            session_token_suffix = token[-32:]
            
            success = await AuthService.logout_user(db, current_user, session_token_suffix)
            db.commit()
            
            return {"message": "Successfully logged out", "success": success}
        
        return {"message": "No active session found"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Logout failed")

# ================================
# PASSWORD MANAGEMENT
# ================================

@router.post("/password-reset/request")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Password reset request - Uses AuthService"""
    try:
        success = await AuthService.request_password_reset(db, reset_data.email)
        db.commit()
        
        # Always return success (security)
        return {"message": "If the email exists, a reset link has been sent"}
    
    except Exception as e:
        db.rollback()
        return {"message": "If the email exists, a reset link has been sent"}

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Execute password reset - Uses AuthService"""
    try:
        user = await AuthService.reset_password(db, reset_data.token, reset_data.new_password)
        db.commit()
        
        return {"message": "Password reset successful", "user_id": str(user.id)}
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Password reset failed")

@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Email verification - Uses AuthService"""
    try:
        user = await AuthService.verify_email(db, verification_data.token)
        db.commit()
        
        return {"message": "Email verified successfully", "user_id": str(user.id)}
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email verification failed")

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for logged in users - Uses UserService"""
    try:
        result = UserService.change_user_password(
            db, current_user.id, password_data.current_password, password_data.new_password
        )
        db.commit()
        
        return result
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Password change failed")

# ================================
# OAUTH AUTHENTICATION
# ================================

@router.get("/oauth/{provider}/login/{tenant_slug}")
async def oauth_login_url(
    provider: str,
    tenant_slug: str,
    db: Session = Depends(get_db)
):
    """Generate OAuth login URL for specific tenant - Uses EnterpriseOAuthService"""
    # Find tenant by slug
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        redirect_uri = f"{settings.BASE_URL}/api/v1/auth/oauth/{provider}/callback/{tenant_slug}"
        auth_url = await EnterpriseOAuthService.get_oauth_authorization_url(
            db, tenant.id, provider, redirect_uri
        )
        
        return OAuthUrlResponse(
            auth_url=auth_url, 
            provider=provider, 
            tenant=tenant_slug,
            state="secure_state_token"  # Should be generated securely
        )
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate OAuth URL")

@router.post("/oauth/{provider}/callback/{tenant_slug}")
async def oauth_callback(
    provider: str,
    tenant_slug: str,
    callback_data: OAuthCallbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """OAuth callback for tenant-specific authentication - Uses EnterpriseOAuthService"""
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        ip_address = request.client.host if request.client else None
        
        if provider == "microsoft":
            user, tokens = await EnterpriseOAuthService.authenticate_microsoft_enterprise_user(
                db, callback_data.code, tenant.id, ip_address
            )
        elif provider == "google":
            user, tokens = await EnterpriseOAuthService.authenticate_google_enterprise_user(
                db, callback_data.code, tenant.id, ip_address
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        
        db.commit()
        return TokenResponse(**tokens, user_id=str(user.id))
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="OAuth authentication failed")

# ================================
# SUPER ADMIN IMPERSONATION
# ================================

@router.post("/impersonate", response_model=TokenResponse)
async def super_admin_impersonate(
    impersonate_data: ImpersonateRequest,
    request: Request,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Super admin impersonation - Uses AuthService"""
    try:
        ip_address = request.client.host if request.client else None
        tokens = await AuthService.super_admin_impersonate(
            db, super_admin, impersonate_data.tenant_id, ip_address
        )
        
        db.commit()
        return TokenResponse(**tokens, user_id=str(super_admin.id))
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Impersonation failed")

@router.post("/end-impersonation")
async def end_impersonation(
    request: Request,
    super_admin: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """End super admin impersonation - Uses AuthService"""
    try:
        # Create new session without impersonation
        ip_address = request.client.host if request.client else None
        tokens = await AuthService._create_user_session(db, super_admin, ip_address)
        
        db.commit()
        return TokenResponse(**tokens, user_id=str(super_admin.id))
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to end impersonation")

# ================================
# AUTHENTICATION STATUS & HISTORY
# ================================

@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Current authentication status"""
    try:
        # Extract impersonation info from token
        auth_header = request.headers.get("Authorization", "")
        is_impersonating = False
        impersonated_tenant_id = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            from app.core.security import verify_token
            payload = verify_token(token)
            if payload:
                is_impersonating = "impersonated_tenant_id" in payload
                impersonated_tenant_id = payload.get("impersonated_tenant_id")
        
        # Get user permissions using RBACService
        from app.services.rbac_service import RBACService
        tenant_id = uuid.UUID(impersonated_tenant_id) if impersonated_tenant_id else current_user.tenant_id
        
        if tenant_id:
            permissions_data = RBACService.get_user_permissions(db, current_user.id, tenant_id)
            permissions = [perm["name"] for perm in permissions_data.get("permissions", [])]
        else:
            permissions = []
        
        return AuthStatusResponse(
            is_authenticated=True,
            user_id=current_user.id,
            tenant_id=tenant_id,
            is_super_admin=current_user.is_super_admin,
            is_impersonating=is_impersonating,
            impersonated_tenant_id=uuid.UUID(impersonated_tenant_id) if impersonated_tenant_id else None,
            permissions=permissions,
            session_expires_at=None  # Would need to get from session
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get auth status")

@router.get("/history", response_model=List[LoginHistoryResponse])
async def get_login_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Login history for current user"""
    try:
        from app.models.audit import AuditLog
        from sqlalchemy import and_, desc
        
        # Get login audit logs
        login_logs = db.query(AuditLog).filter(
            and_(
                AuditLog.user_id == current_user.id,
                AuditLog.action.in_(["LOGIN_SUCCESS", "LOGIN_FAILED"])
            )
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        history = []
        for log in login_logs:
            history.append(LoginHistoryResponse(
                login_timestamp=log.created_at.isoformat(),
                ip_address=str(log.ip_address) if log.ip_address else None,
                user_agent=log.user_agent,
                auth_method="local",  # Would need to extract from log details
                success=log.action == "LOGIN_SUCCESS",
                failure_reason=log.new_values.get("reason") if log.action == "LOGIN_FAILED" else None
            ))
        
        return history
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get login history")

@router.get("/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Security events for current user"""
    try:
        from app.models.audit import AuditLog
        from sqlalchemy import and_, desc
        
        # Get security-related audit logs
        security_events = db.query(AuditLog).filter(
            and_(
                AuditLog.user_id == current_user.id,
                AuditLog.action.in_([
                    "LOGIN_FAILED", "ACCOUNT_LOCKED", "PASSWORD_RESET_REQUESTED",
                    "PASSWORD_CHANGED", "EMAIL_VERIFIED", "OAUTH_LOGIN_FAILED"
                ])
            )
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        events = []
        for event in security_events:
            severity = "critical" if event.action == "ACCOUNT_LOCKED" else "warning"
            if event.action in ["EMAIL_VERIFIED", "PASSWORD_CHANGED"]:
                severity = "info"
            
            events.append(SecurityEventResponse(
                event_type=event.action,
                timestamp=event.created_at.isoformat(),
                ip_address=str(event.ip_address) if event.ip_address else None,
                user_agent=event.user_agent,
                details=event.new_values or {},
                severity=severity
            ))
        
        return events
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get security events")

# ================================
# TOKEN REFRESH
# ================================

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token with refresh token"""
    try:
        from app.core.security import verify_token, create_access_token
        from datetime import datetime
        
        # Verify refresh token
        payload = verify_token(refresh_data.refresh_token, "refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        # Verify session exists
        from app.models.user import UserSession
        session = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.refresh_token == refresh_data.refresh_token[-32:]
        ).first()
        
        if not session or session.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Session expired")
        
        # Create new access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_super_admin": user.is_super_admin
        }
        
        # Preserve impersonation if exists
        if payload.get("impersonated_tenant_id"):
            token_data["impersonated_tenant_id"] = payload["impersonated_tenant_id"]
        
        new_access_token = create_access_token(token_data)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_data.refresh_token,  # Keep same refresh token
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user_id=user.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Token refresh failed")

# ================================
# SESSION MANAGEMENT
# ================================

@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active sessions for current user - Uses UserService"""
    try:
        sessions = UserService.get_user_sessions(db, current_user.id)
        return {
            "sessions": sessions,
            "total_active": len(sessions)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: uuid.UUID = Path(..., description="Session ID to terminate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate a specific session - Uses UserService"""
    try:
        result = UserService.terminate_user_sessions(
            db, current_user.id, session_id, False, current_user
        )
        db.commit()
        
        if result["terminated_count"] == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session terminated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to terminate session")

@router.delete("/sessions")
async def terminate_all_sessions(
    request: Request,
    keep_current: bool = Query(default=True, description="Keep current session active"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate all sessions for current user - Uses UserService"""
    try:
        # For simplicity, terminate all sessions (UserService would handle keep_current logic)
        result = UserService.terminate_user_sessions(
            db, current_user.id, None, True, current_user
        )
        db.commit()
        
        return {
            "message": f"Terminated {result['terminated_count']} session(s)",
            "terminated_count": result["terminated_count"]
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to terminate sessions")

# ================================
# ACCOUNT SECURITY SETTINGS
# ================================

@router.get("/security/settings")
async def get_security_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's security settings - Uses UserService"""
    try:
        security_info = UserService.get_user_security_info(db, current_user.id)
        
        return {
            "email_verified": current_user.is_verified,
            "two_factor_enabled": security_info.get("two_factor_enabled", False),
            "active_sessions_count": security_info.get("active_sessions_count", 0),
            "failed_login_attempts": security_info.get("failed_login_attempts", 0),
            "account_locked": security_info.get("locked_until") is not None,
            "last_password_change": security_info.get("last_password_change"),
            "last_login": security_info.get("last_login_at"),
            "auth_method": current_user.auth_method,
            "backup_codes_remaining": 0  # Would implement
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get security settings")

@router.post("/security/email/resend-verification")
async def resend_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend email verification"""
    try:
        if current_user.is_verified:
            return {"message": "Email is already verified"}
        
        # Generate new verification token
        from app.core.security import generate_verification_token
        from datetime import datetime, timedelta
        
        verification_token = generate_verification_token()
        current_user.email_verification_token = verification_token
        current_user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        # Send verification email
        from app.utils.email import email_service
        await email_service.send_email_verification(
            current_user.email,
            current_user.full_name,
            verification_token
        )
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "EMAIL_VERIFICATION_RESENT", current_user.id, current_user.tenant_id,
            {"email": current_user.email}
        )
        
        db.commit()
        
        return {"message": "Verification email sent successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to resend verification email")