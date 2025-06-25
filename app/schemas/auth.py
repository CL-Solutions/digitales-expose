# ================================
# AUTHENTICATION SCHEMAS (schemas/auth.py)
# ================================

from pydantic import Field, EmailStr, field_validator
from typing import Optional, Literal
from uuid import UUID
from app.schemas.base import BaseSchema, PasswordFieldMixin

class LoginRequest(BaseSchema):
    """Schema für Login-Requests"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password")
    remember_me: bool = Field(default=False, description="Extended session duration")

class TokenResponse(BaseSchema):
    """Schema für Token-Responses"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user_id: UUID = Field(..., description="User ID")

class RefreshTokenRequest(BaseSchema):
    """Schema für Token-Refresh"""
    refresh_token: str = Field(..., description="Valid refresh token")

class ImpersonateRequest(BaseSchema):
    """Schema für Super-Admin Impersonation"""
    tenant_id: UUID = Field(..., description="Tenant ID to impersonate")
    reason: Optional[str] = Field(description="Reason for impersonation")

class PasswordResetRequest(BaseSchema):
    """Schema für Password-Reset Anfrage"""
    email: EmailStr = Field(..., description="User email address")

class PasswordResetConfirm(BaseSchema, PasswordFieldMixin):
    """Schema für Password-Reset Bestätigung"""
    token: str = Field(..., description="Password reset token")
    password: str = Field(..., min_length=8, description="New password")

class EmailVerificationRequest(BaseSchema):
    """Schema für Email-Verifizierung"""
    token: str = Field(..., description="Email verification token")

class ChangePasswordRequest(BaseSchema, PasswordFieldMixin):
    """Schema für Passwort-Änderung"""
    current_password: str = Field(..., description="Current password")
    password: str = Field(..., min_length=8, description="New password")

class CreateUserRequest(BaseSchema, PasswordFieldMixin):
    """Schema für User-Erstellung durch Admin"""
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    password: Optional[str] = Field(min_length=8, description="User password (optional)")
    role_ids: list[UUID] = Field(default_factory=list, description="Role IDs to assign")
    send_welcome_email: bool = Field(default=True, description="Send welcome email")
    require_email_verification: bool = Field(default=False, description="Require email verification")
    tenant_id: Optional[UUID] = Field(description="Tenant ID (only for super admin)")

# ================================
# OAUTH SCHEMAS (schemas/oauth.py)
# ================================

class OAuthCallbackRequest(BaseSchema):
    """Schema für OAuth Callback"""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: Optional[str] = Field(description="State parameter for CSRF protection")

class OAuthUrlResponse(BaseSchema):
    """Schema für OAuth Authorization URL"""
    auth_url: str = Field(..., description="OAuth authorization URL")
    provider: str = Field(..., description="OAuth provider name")
    tenant: str = Field(..., description="Tenant slug")
    state: str = Field(..., description="CSRF protection state")

class OAuthErrorResponse(BaseSchema):
    """Schema für OAuth Error Response"""
    error: str = Field(..., description="OAuth error code")
    error_description: Optional[str] = Field(description="Human-readable error description")
    error_uri: Optional[str] = Field(description="URI for more information about the error")

class OAuthTokenRefreshRequest(BaseSchema):
    """Schema für OAuth Token Refresh"""
    provider: Literal["microsoft", "google"] = Field(..., description="OAuth provider")

class OAuthRevokeRequest(BaseSchema):
    """Schema für OAuth Access Revocation"""
    provider: Literal["microsoft", "google"] = Field(..., description="OAuth provider")

# ================================
# AUTHENTICATION STATUS SCHEMAS
# ================================

class AuthStatusResponse(BaseSchema):
    """Schema für Authentication Status"""
    is_authenticated: bool = Field(..., description="User authentication status")
    user_id: Optional[UUID] = Field(description="User ID if authenticated")
    tenant_id: Optional[UUID] = Field(description="Current tenant ID")
    is_super_admin: bool = Field(default=False, description="Super admin status")
    is_impersonating: bool = Field(default=False, description="Currently impersonating another tenant")
    impersonated_tenant_id: Optional[UUID] = Field(description="Impersonated tenant ID")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    session_expires_at: Optional[str] = Field(description="Session expiration time")

class LoginHistoryResponse(BaseSchema):
    """Schema für Login History"""
    login_timestamp: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    auth_method: Literal["local", "microsoft", "google"]
    success: bool
    failure_reason: Optional[str]
    location: Optional[str]

class SecurityEventResponse(BaseSchema):
    """Schema für Security Events"""
    event_type: str = Field(..., description="Type of security event")
    timestamp: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: dict = Field(default_factory=dict, description="Additional event details")
    severity: Literal["info", "warning", "error", "critical"]

# ================================
# TWO-FACTOR AUTHENTICATION SCHEMAS (Future Extension)
# ================================

class TwoFactorSetupRequest(BaseSchema):
    """Schema für 2FA Setup (Future)"""
    method: Literal["totp", "sms", "email"] = Field(..., description="2FA method")
    phone_number: Optional[str] = Field(description="Phone number for SMS")

class TwoFactorVerifyRequest(BaseSchema):
    """Schema für 2FA Verification (Future)"""
    code: str = Field(..., min_length=6, max_length=8, description="2FA verification code")
    remember_device: bool = Field(default=False, description="Remember this device")

class TwoFactorBackupCodesResponse(BaseSchema):
    """Schema für 2FA Backup Codes (Future)"""
    backup_codes: list[str] = Field(..., description="Backup codes for 2FA recovery")
    
# ================================
# API KEY AUTHENTICATION SCHEMAS (Future Extension)
# ================================

class ApiKeyCreateRequest(BaseSchema):
    """Schema für API Key Creation (Future)"""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: list[str] = Field(..., description="Permissions for this API key")
    expires_in_days: Optional[int] = Field(ge=1, le=365, description="Expiration in days")

class ApiKeyResponse(BaseSchema):
    """Schema für API Key Response (Future)"""
    id: UUID
    name: str
    key_prefix: str = Field(..., description="First 8 characters of the API key")
    permissions: list[str]
    expires_at: Optional[str]
    last_used_at: Optional[str]
    created_at: str

# ================================
# AUTHENTICATION AUDIT SCHEMAS
# ================================

class AuthAuditResponse(BaseSchema):
    """Schema für Authentication Audit"""
    user_id: UUID
    action: str = Field(..., description="Authentication action performed")
    timestamp: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    tenant_id: Optional[UUID]
    success: bool
    details: dict = Field(default_factory=dict)

class AuthAuditFilterParams(BaseSchema):
    """Schema für Auth Audit Filtering"""
    user_id: Optional[UUID]
    tenant_id: Optional[UUID]
    action: Optional[str]
    success: Optional[bool]
    start_date: Optional[str]
    end_date: Optional[str]
    ip_address: Optional[str]

class AuthStatsResponse(BaseSchema):
    """Schema für Authentication Statistics"""
    total_logins: int
    successful_logins: int
    failed_logins: int
    unique_users: int
    logins_by_method: dict[str, int]
    failed_logins_by_reason: dict[str, int]
    recent_activity: list[AuthAuditResponse]