# ================================
# AUTH SERVICE (services/auth_service.py)
# ================================

from sqlalchemy.orm import Session
from app.models.user import User, UserSession, PasswordResetToken
from app.models.tenant import Tenant
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, generate_reset_token
from app.schemas.user import UserCreate
from app.core.exceptions import AppException, AuthenticationError, AuthorizationError
from app.utils.audit import AuditLogger
from datetime import datetime, timedelta
import uuid
import logging
import secrets
import string

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

class AuthService:
    
    @staticmethod
    async def create_user_by_admin(
        db: Session, 
        user_data: UserCreate, 
        tenant_id: uuid.UUID, 
        created_by_user: User
    ) -> User:
        """Erstellt einen neuen User (nur durch Tenant-Admin oder Super-Admin)"""
        
        # Permission Check: Tenant-Admin oder Super-Admin
        if not (created_by_user.is_super_admin or 
                AuthService._is_tenant_admin(db, created_by_user.id, tenant_id)):
            raise AuthorizationError("Insufficient permissions to create users")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            audit_logger.log_auth_event(
                db, "USER_CREATE_FAILED", created_by_user.id, tenant_id,
                {"reason": "email_exists", "email": user_data.email}
            )
            raise AppException("Email already registered", 400, "EMAIL_EXISTS")
        
        # Generate temporary password if not provided
        temp_password = user_data.password or AuthService._generate_temp_password()
        hashed_password = get_password_hash(temp_password)
        
        user = User(
            email=user_data.email,
            tenant_id=tenant_id,
            auth_method="local",
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_verified=user_data.send_welcome_email,  # Verified if welcome email sent
            email_verification_token=generate_reset_token() if user_data.require_email_verification else None,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24) if user_data.require_email_verification else None
        )
        
        db.add(user)
        db.flush()  # Get user.id without committing
        
        # Assign specified roles or default role
        if user_data.role_ids:
            await AuthService._assign_roles_to_user(db, user.id, user_data.role_ids, tenant_id)
        else:
            await AuthService._assign_default_role(db, user.id, tenant_id)
        
        # Send welcome email with temp password or verification link
        if user_data.send_welcome_email:
            from app.utils.email import email_service
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            
            await email_service.send_welcome_email(
                to_email=user.email,
                user_name=f"{user.first_name} {user.last_name}".strip(),
                temp_password=temp_password if not user_data.require_email_verification else None,
                verification_token=user.email_verification_token if user_data.require_email_verification else None,
                tenant_name=tenant.name if tenant else None
            )
        
        audit_logger.log_auth_event(
            db, "USER_CREATED", created_by_user.id, tenant_id,
            {"new_user_id": str(user.id), "email": user.email}
        )
        
        return user
    
    @staticmethod
    async def authenticate_local_user(
        db: Session, 
        email: str, 
        password: str, 
        ip_address: str = None,
        user_agent: str = None
    ) -> tuple[User, dict]:
        """Authentifiziert einen lokalen User - Einheitliche Fehlermeldung für Security"""
        
        logger.debug(f"Attempting login for email: {email}")
        
        GENERIC_ERROR_MESSAGE = "Invalid email or password"
        
        try:
            user = db.query(User).filter(
                User.email == email,
                User.auth_method == "local"
            ).first()
        except Exception as e:
            logger.error(f"Database query error during login: {str(e)}", exc_info=True)
            raise AuthenticationError(GENERIC_ERROR_MESSAGE)
        
        # User not found
        if not user:
            audit_logger.log_auth_event(
                db, "LOGIN_FAILED", None, None,
                {"reason": "user_not_found", "email": email},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError(GENERIC_ERROR_MESSAGE)
        
        # Account locked check
        if user.locked_until and user.locked_until > datetime.utcnow():
            audit_logger.log_auth_event(
                db, "LOGIN_FAILED", user.id, user.tenant_id,
                {"reason": "account_locked", "locked_until": user.locked_until.isoformat()},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError(GENERIC_ERROR_MESSAGE)
        
        # Account deactivated check
        if not user.is_active:
            audit_logger.log_auth_event(
                db, "LOGIN_FAILED", user.id, user.tenant_id,
                {"reason": "account_deactivated"},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError(GENERIC_ERROR_MESSAGE)
        
        # Password verification
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                audit_logger.log_auth_event(
                    db, "ACCOUNT_LOCKED", user.id, user.tenant_id,
                    {"failed_attempts": user.failed_login_attempts},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:
                audit_logger.log_auth_event(
                    db, "LOGIN_FAILED", user.id, user.tenant_id,
                    {"reason": "invalid_password", "failed_attempts": user.failed_login_attempts},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            db.commit()  # Save failed attempt count
            raise AuthenticationError(GENERIC_ERROR_MESSAGE)
        
        # Email verification check (if required)
        if not user.is_verified:
            audit_logger.log_auth_event(
                db, "LOGIN_FAILED", user.id, user.tenant_id,
                {"reason": "email_not_verified"},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError("Please verify your email address first")
        
        # Successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        
        tokens = await AuthService._create_user_session(db, user, ip_address)
        
        audit_logger.log_auth_event(
            db, "LOGIN_SUCCESS", user.id, user.tenant_id,
            {},  # No need for IP in details since it's now a parameter
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return user, tokens
    
    @staticmethod
    async def super_admin_impersonate(
        db: Session, 
        super_admin: User, 
        tenant_id: uuid.UUID,
        ip_address: str = None
    ) -> dict:
        """Super-Admin Impersonation eines Tenants"""
        
        if not super_admin.is_super_admin:
            raise AuthorizationError("Super admin access required")
        
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise AppException("Tenant not found", 404, "TENANT_NOT_FOUND")
        
        # Create impersonated session
        tokens = await AuthService._create_user_session(db, super_admin, ip_address, tenant_id)
        
        audit_logger.log_auth_event(
            db, "SUPER_ADMIN_IMPERSONATE", super_admin.id, tenant_id,
            {"impersonated_tenant_id": str(tenant_id)},
            ip_address=ip_address
        )
        
        return tokens
    
    @staticmethod
    async def logout_user(
        db: Session,
        user: User,
        session_token_suffix: str
    ) -> bool:
        """Logout User - invalidiert Session"""
        try:
            session = db.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.session_token == session_token_suffix
            ).first()
            
            if session:
                db.delete(session)
                
                audit_logger.log_auth_event(
                    db, "USER_LOGOUT", user.id, user.tenant_id,
                    {"session_id": str(session.id)}
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    @staticmethod
    async def verify_email(db: Session, token: str) -> User:
        """Email-Verifizierung"""
        user = db.query(User).filter(
            User.email_verification_token == token,
            User.email_verification_expires > datetime.utcnow()
        ).first()
        
        if not user:
            raise AppException("Invalid or expired verification token", 400, "INVALID_TOKEN")
        
        user.is_verified = True
        user.email_verification_token = None
        user.email_verification_expires = None
        
        audit_logger.log_auth_event(
            db, "EMAIL_VERIFIED", user.id, user.tenant_id,
            {"email": user.email}
        )
        
        return user
    
    @staticmethod
    async def request_password_reset(db: Session, email: str) -> bool:
        """Password-Reset Anfrage"""
        user = db.query(User).filter(
            User.email == email,
            User.auth_method == "local"
        ).first()
        
        # Auch wenn User nicht existiert, keine Fehlermeldung (Security)
        if not user:
            return True
        
        # Generate reset token
        reset_token = generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store reset token
        password_reset = PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at
        )
        db.add(password_reset)
        
        # Send reset email
        from app.utils.email import email_service
        await email_service.send_password_reset_email(
            to_email=user.email,
            user_name=f"{user.first_name} {user.last_name}".strip(),
            reset_token=reset_token
        )
        
        audit_logger.log_auth_event(
            db, "PASSWORD_RESET_REQUESTED", user.id, user.tenant_id,
            {"email": user.email}
        )
        
        return True
    
    @staticmethod
    async def reset_password(db: Session, token: str, new_password: str) -> User:
        """Password-Reset durchführen"""
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.expires_at > datetime.utcnow(),
            PasswordResetToken.used_at.is_(None)
        ).first()
        
        if not reset_token:
            raise AppException("Invalid or expired reset token", 400, "INVALID_TOKEN")
        
        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Update password
        user.password_hash = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Mark token as used
        reset_token.used_at = datetime.utcnow()
        
        # Invalidate all existing sessions
        db.query(UserSession).filter(UserSession.user_id == user.id).delete()
        
        audit_logger.log_auth_event(
            db, "PASSWORD_RESET_COMPLETED", user.id, user.tenant_id,
            {"email": user.email}
        )
        
        return user
    
    # ================================
    # HELPER METHODS
    # ================================
    
    @staticmethod
    def _is_tenant_admin(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Prüft ob User Tenant-Admin ist"""
        from app.models.rbac import UserRole, Role
        from sqlalchemy import and_
        
        admin_role = db.query(UserRole).join(Role).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Role.name == "tenant_admin"
            )
        ).first()
        
        return admin_role is not None
    
    @staticmethod
    def _generate_temp_password() -> str:
        """Generiert ein sicheres temporäres Passwort"""
        # 12 Zeichen: Buchstaben, Zahlen, Sonderzeichen
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(12))
    
    @staticmethod
    async def _create_user_session(
        db: Session, 
        user: User, 
        ip_address: str = None, 
        impersonated_tenant_id: uuid.UUID = None
    ) -> dict:
        """Erstellt eine neue User-Session mit Tokens"""
        
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_super_admin": user.is_super_admin
        }
        
        # Super-Admin Impersonation
        if impersonated_tenant_id and user.is_super_admin:
            token_data["impersonated_tenant_id"] = str(impersonated_tenant_id)
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store session in database
        session = UserSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            session_token=access_token[-32:],  # Store last 32 chars for lookup
            refresh_token=refresh_token[-32:],
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            impersonated_tenant_id=impersonated_tenant_id,
            ip_address=ip_address
        )
        
        db.add(session)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 30 * 60  # 30 minutes in seconds
        }
    
    @staticmethod
    async def _assign_roles_to_user(
        db: Session,
        user_id: uuid.UUID,
        role_ids: list[uuid.UUID],
        tenant_id: uuid.UUID
    ):
        """Weist einem User spezifische Rollen zu"""
        from app.models.rbac import UserRole, Role
        
        # Verify roles exist and belong to tenant
        roles = db.query(Role).filter(
            Role.id.in_(role_ids),
            Role.tenant_id == tenant_id
        ).all()
        
        if len(roles) != len(role_ids):
            raise AppException("One or more roles not found", 400, "ROLES_NOT_FOUND")
        
        # Create user-role assignments
        for role in roles:
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                tenant_id=tenant_id
            )
            db.add(user_role)
    
    @staticmethod
    async def _assign_default_role(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID):
        """Weist die Standard-Rolle 'user' zu"""
        from app.models.rbac import Role, UserRole
        
        default_role = db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == "user",
            Role.is_system_role == True
        ).first()
        
        if default_role:
            user_role = UserRole(
                user_id=user_id,
                role_id=default_role.id,
                tenant_id=tenant_id
            )
            db.add(user_role)