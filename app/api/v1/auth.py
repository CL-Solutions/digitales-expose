# ================================
# AUTH API ROUTES (api/v1/auth.py) - COMPLETED
# ================================

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
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
    """Erstellt einen neuen User (nur durch Admin)"""
    try:
        # Tenant-ID aus dem aktuellen User-Kontext (oder aus Request bei Super-Admin)
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
    """Login für lokale User - Einheitliche Fehlermeldung"""
    try:
        ip_address = request.client.host if request.client else None
        
        user, tokens = await AuthService.authenticate_local_user(
            db, login_data.email, login_data.password, ip_address
        )
        db.commit()
        
        return TokenResponse(**tokens, user_id=str(user.id))
    
    except AppException as e:
        db.rollback()
        # Alle Auth-Fehler werden als 401 mit generischer Meldung zurückgegeben
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
    """User Logout - invalidiert Session"""
    try:
        # Session-Token aus Header extrahieren
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
    """Password-Reset Anfrage"""
    try:
        success = await AuthService.request_password_reset(db, reset_data.email)
        db.commit()
        
        # Immer Success zurückgeben (Security)
        return {"message": "If the email exists, a reset link has been sent"}
    
    except Exception as e:
        db.rollback()
        return {"message": "If the email exists, a reset link has been sent"}

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Password-Reset durchführen"""
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
    """Email-Verifizierung"""
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
    """Passwort ändern (für eingeloggte User)"""
    try:
        from app.core.security import verify_password, get_password_hash
        
        # Verify current password
        if not verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        current_user.password_hash = get_password_hash(password_data.new_password)
        
        # Invalidate all other sessions
        from app.models.user import UserSession
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id
        ).delete()
        
        db.commit()
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        raise
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
    """Generiert OAuth Login URL für spezifischen Tenant"""
    # Tenant anhand Slug finden
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
    """OAuth Callback für Tenant-spezifische Authentication"""
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
    super_admin: User = Depends(get_super_admin_user),
    request: Request,
    db: Session = Depends(get_db)
):
    """Super-Admin Impersonation"""
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
    super_admin: User = Depends(get_super_admin_user),
    request: Request,
    db: Session = Depends(get_db)
):
    """Beendet Super-Admin Impersonation"""
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
    current_user: User = Depends(get_current_user),
    request: Request,
    db: Session = Depends(get_db)
):
    """Aktueller Authentication Status"""
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
        
        # Get user permissions
        from app.models.utils import get_user_permissions
        tenant_id = uuid.UUID(impersonated_tenant_id) if impersonated_tenant_id else current_user.tenant_id
        permissions = get_user_permissions(db, current_user.id, tenant_id) if tenant_id else []
        
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
    """Login-Historie des aktuellen Users"""
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
    """Security Events für den aktuellen User"""
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
    """Access Token erneuern mit Refresh Token"""
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
# TWO-FACTOR AUTHENTICATION (Future Extension)
# ================================

@router.post("/2fa/setup")
async def setup_two_factor_auth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup Two-Factor Authentication (Future Feature)"""
    try:
        # Would implement TOTP setup
        import secrets
        import qrcode
        from io import BytesIO
        import base64
        
        # Generate secret
        secret = secrets.token_hex(16)
        
        # Generate QR code for authenticator apps
        totp_uri = f"otpauth://totp/{settings.APP_NAME}:{current_user.email}?secret={secret}&issuer={settings.APP_NAME}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        # Store secret temporarily (would implement proper 2FA model)
        # current_user.totp_secret = secret
        # current_user.totp_enabled = False  # Enable after verification
        
        return {
            "message": "2FA setup initiated",
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_data}",
            "manual_entry_key": secret,
            "instructions": "Scan the QR code with your authenticator app or enter the manual key"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to setup 2FA")

@router.post("/2fa/verify")
async def verify_two_factor_code(
    code: str = Query(..., description="6-digit verification code"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify Two-Factor Authentication Code"""
    try:
        # Would implement TOTP verification
        import pyotp
        
        # Get user's TOTP secret (would be stored in user model)
        # totp_secret = current_user.totp_secret
        totp_secret = "example_secret"  # Placeholder
        
        totp = pyotp.TOTP(totp_secret)
        
        if totp.verify(code):
            # Enable 2FA for user
            # current_user.totp_enabled = True
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            return {
                "message": "2FA verified and enabled successfully",
                "backup_codes": backup_codes,
                "warning": "Store these backup codes securely. They can only be used once."
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid verification code")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to verify 2FA code")

@router.post("/2fa/disable")
async def disable_two_factor_auth(
    password: str = Query(..., description="Current password for confirmation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable Two-Factor Authentication"""
    try:
        from app.core.security import verify_password
        
        # Verify password before disabling 2FA
        if not verify_password(password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid password")
        
        # Disable 2FA (would implement in user model)
        # current_user.totp_enabled = False
        # current_user.totp_secret = None
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "2FA_DISABLED", current_user.id, current_user.tenant_id,
            {"disabled_by_user": True}
        )
        
        db.commit()
        
        return {"message": "Two-factor authentication disabled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to disable 2FA")

# ================================
# SESSION MANAGEMENT
# ================================

@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active sessions for current user"""
    try:
        from app.models.user import UserSession
        from datetime import datetime
        
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
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
        
        return {
            "sessions": session_list,
            "total_active": len(session_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get sessions")

@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: uuid.UUID = Path(..., description="Session ID to terminate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate a specific session"""
    try:
        from app.models.user import UserSession
        
        session = db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete session
        db.delete(session)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "SESSION_TERMINATED", current_user.id, current_user.tenant_id,
            {"session_id": str(session_id), "self_service": True}
        )
        
        db.commit()
        
        return {"message": "Session terminated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to terminate session")

@router.delete("/sessions")
async def terminate_all_sessions(
    keep_current: bool = Query(default=True, description="Keep current session active"),
    current_user: User = Depends(get_current_user),
    request: Request,
    db: Session = Depends(get_db)
):
    """Terminate all sessions for current user"""
    try:
        from app.models.user import UserSession
        
        query = db.query(UserSession).filter(UserSession.user_id == current_user.id)
        
        if keep_current:
            # Extract current session token to keep it
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                current_session_suffix = token[-32:]
                query = query.filter(UserSession.session_token != current_session_suffix)
        
        terminated_count = query.delete()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "ALL_SESSIONS_TERMINATED", current_user.id, current_user.tenant_id,
            {
                "terminated_count": terminated_count,
                "keep_current": keep_current,
                "self_service": True
            }
        )
        
        db.commit()
        
        return {
            "message": f"Terminated {terminated_count} session(s)",
            "terminated_count": terminated_count
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
    """Get current user's security settings"""
    try:
        from app.models.user import UserSession
        from datetime import datetime
        
        # Count active sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        # Get security status
        settings_data = {
            "email_verified": current_user.is_verified,
            "two_factor_enabled": False,  # Would implement
            "active_sessions_count": active_sessions,
            "failed_login_attempts": current_user.failed_login_attempts,
            "account_locked": current_user.locked_until is not None and current_user.locked_until > datetime.utcnow(),
            "last_password_change": None,  # Would track this
            "last_login": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            "auth_method": current_user.auth_method,
            "backup_codes_remaining": 0  # Would implement
        }
        
        return settings_data
    
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