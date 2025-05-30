# ================================
# AUTH API ROUTES (api/v1/auth.py)
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
    LoginHistoryResponse, SecurityEventResponse
)
from app.services.auth_service import AuthService
from app.services.oauth_service import EnterpriseOAuthService
from app.models.user import User
from app.models.tenant import Tenant
from app.core.exceptions import AppException
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
        from app.config import settings
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