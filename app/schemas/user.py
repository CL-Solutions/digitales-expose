# ================================
# USER SCHEMAS (schemas/user.py) - COMPLETED
# ================================

from pydantic import Field, EmailStr, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema, BaseResponseSchema, TimestampMixin, PaginationParams, SortParams, SearchParams
from app.schemas.rbac import RoleResponse

class UserBase(BaseSchema):
    """Base User Schema"""
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    is_active: bool = Field(default=True, description="User active status")

class UserCreate(UserBase):
    """Schema für User-Erstellung durch Admin"""
    password: Optional[str] = Field(default=None, min_length=8, description="User password (optional, will generate if not provided)")
    role_ids: List[UUID] = Field(default_factory=list, description="Role IDs to assign")
    send_welcome_email: bool = Field(default=True, description="Send welcome email to user")
    require_email_verification: bool = Field(default=False, description="Require email verification before login")
    tenant_id: UUID = Field(..., description="Tenant ID for the user")
    provision_percentage: Optional[int] = Field(default=0, ge=0, le=100, description="User's provision percentage (0-100)")
    can_see_all_properties: bool = Field(default=False, description="User can see all properties regardless of assignments")

class UserUpdate(BaseSchema):
    """Schema für User-Updates"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    settings: Optional[dict] = Field(None, description="User settings")
    provision_percentage: Optional[int] = Field(None, ge=0, le=100, description="User's provision percentage (0-100)")
    can_see_all_properties: Optional[bool] = Field(None, description="User can see all properties regardless of assignments")
    
    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore"  # Ignore extra fields not defined in the schema
    )

class UserBasicInfo(UserBase):
    """Basic user info with ID - used for manager references"""
    id: UUID

class UserResponse(UserBase, TimestampMixin):
    """Schema für User-Responses"""
    id: UUID
    tenant_id: Optional[UUID]
    auth_method: Literal["local", "microsoft", "google"]
    is_super_admin: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    avatar_url: Optional[str]
    settings: Optional[dict] = Field(default_factory=dict, description="User settings")
    provision_percentage: int = Field(default=0, description="User's provision percentage (0-100)")
    can_see_all_properties: bool = Field(default=False, description="User can see all properties regardless of assignments")
    
    # Role Information
    roles: List['RoleResponse'] = Field(default_factory=list)
    
    # Team Information (optional - only included in list views)
    manager: Optional['UserBasicInfo'] = Field(None, description="The location manager this user belongs to")
    team_provision_percentage: Optional[int] = Field(None, description="Provision percentage from team assignment (0-100)")

class UserListResponse(BaseSchema):
    """Schema für User-Listen"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int

class UserProfileResponse(UserResponse):
    """Extended User Profile Response"""
    failed_login_attempts: int
    locked_until: Optional[datetime]
    permissions: List[str] = Field(default_factory=list, description="List of user permissions")
    settings: dict = Field(default_factory=dict, description="User settings")

class UserFilterParams(PaginationParams, SortParams, SearchParams):
    """Schema für User-Filtering"""
    auth_method: Optional[Literal["local", "microsoft", "google"]] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None  # Nur für Super-Admin

class UserStatsResponse(BaseSchema):
    """Schema für User-Statistiken"""
    total_users: int
    active_users: int
    verified_users: int
    users_by_auth_method: dict[str, int]
    recent_logins: int

# ================================
# USER SESSION SCHEMAS
# ================================

class UserSessionResponse(BaseSchema, TimestampMixin):
    """Schema für User Session Response"""
    id: UUID
    user_id: UUID
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime
    last_accessed_at: datetime
    is_impersonation: bool = Field(default=False, description="Is this an impersonation session")
    impersonated_tenant_id: Optional[UUID]

class ActiveSessionsResponse(BaseSchema):
    """Schema für aktive Sessions"""
    sessions: List[UserSessionResponse]
    total_active: int

class SessionTerminateRequest(BaseSchema):
    """Schema für Session-Terminierung"""
    session_id: Optional[UUID] = Field(description="Specific session to terminate (if not provided, terminates current session)")
    terminate_all: bool = Field(default=False, description="Terminate all sessions for user")

# ================================
# USER INVITATION SCHEMAS
# ================================

class UserInviteRequest(BaseSchema):
    """Schema für User-Einladung"""
    email: EmailStr = Field(..., description="Email address to invite")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role_ids: List[UUID] = Field(..., min_items=1, description="Role IDs to assign")
    welcome_message: Optional[str] = Field(description="Custom welcome message")
    expires_in_days: int = Field(default=7, ge=1, le=30, description="Invitation expiry in days")

class UserInviteResponse(BaseSchema, TimestampMixin):
    """Schema für User-Einladung Response"""
    id: UUID
    email: EmailStr
    invited_by: UUID
    expires_at: datetime
    is_accepted: bool
    accepted_at: Optional[datetime]

class UserInviteAcceptRequest(BaseSchema):
    """Schema für Einladung akzeptieren"""
    token: str = Field(..., description="Invitation token")
    password: str = Field(..., min_length=8, description="User password")
    first_name: Optional[str] = Field(description="Update first name")
    last_name: Optional[str] = Field(description="Update last name")

# ================================
# USER BULK OPERATIONS
# ================================

class UserBulkCreateRequest(BaseSchema):
    """Schema für Bulk User Creation"""
    users: List[UserCreate] = Field(..., min_items=1, max_items=100)
    send_welcome_emails: bool = Field(default=True)
    default_role_id: Optional[UUID] = Field(description="Default role to assign if user has no roles")

class UserBulkCreateResponse(BaseSchema):
    """Schema für Bulk User Creation Response"""
    created_users: List[UserResponse]
    failed_users: List[dict] = Field(description="Users that failed to create with error details")
    total_created: int
    total_failed: int

class UserBulkUpdateRequest(BaseSchema):
    """Schema für Bulk User Updates"""
    user_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    updates: UserUpdate = Field(..., description="Updates to apply to all users")
    reason: Optional[str] = Field(description="Reason for bulk update")

class UserBulkActionRequest(BaseSchema):
    """Schema für Bulk User Actions"""
    user_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    action: Literal["activate", "deactivate", "verify", "lock", "unlock", "delete"] = Field(..., description="Action to perform")
    reason: Optional[str] = Field(description="Reason for the action")

class UserBulkActionResponse(BaseSchema):
    """Schema für Bulk Action Response"""
    successful_user_ids: List[UUID]
    failed_user_ids: List[UUID]
    errors: dict[str, str] = Field(description="Error messages for failed actions")
    total_processed: int
    total_successful: int

# ================================
# PASSWORD MANAGEMENT SCHEMAS
# ================================

class ChangePasswordRequest(BaseSchema):
    """Schema für Passwort-Änderung durch User"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

class SetPasswordRequest(BaseSchema):
    """Schema für Admin-initiated Password Setting"""
    new_password: str = Field(..., min_length=8, description="New password")
    force_change_on_login: bool = Field(default=True, description="Force user to change password on next login")

# ================================
# USER SECURITY SCHEMAS
# ================================

class UserSecurityInfo(BaseSchema):
    """Schema für User Security Information"""
    user_id: UUID
    failed_login_attempts: int
    locked_until: Optional[datetime]
    last_login_at: Optional[datetime]
    last_password_change: Optional[datetime]
    active_sessions_count: int
    two_factor_enabled: bool
    recent_security_events: List[dict] = Field(default_factory=list)

class UserSecurityEventResponse(BaseSchema, TimestampMixin):
    """Schema für User Security Events"""
    id: UUID
    user_id: UUID
    event_type: str = Field(description="Type of security event")
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    details: dict = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "high", "critical"] = Field(default="low")

# ================================
# TWO-FACTOR AUTHENTICATION SCHEMAS
# ================================

class TwoFactorSetupRequest(BaseSchema):
    """Schema für 2FA Setup"""
    method: Literal["totp", "sms", "email"] = Field(..., description="2FA method")
    phone_number: Optional[str] = Field(description="Phone number for SMS (if method is SMS)")

class TwoFactorSetupResponse(BaseSchema):
    """Schema für 2FA Setup Response"""
    secret: str = Field(..., description="TOTP secret key")
    qr_code: str = Field(..., description="Base64 encoded QR code image")
    manual_entry_key: str = Field(..., description="Manual entry key for authenticator apps")
    backup_codes: List[str] = Field(..., description="Backup recovery codes")

class TwoFactorVerifyRequest(BaseSchema):
    """Schema für 2FA Verification"""
    code: str = Field(..., min_length=6, max_length=8, description="2FA verification code")
    remember_device: bool = Field(default=False, description="Remember this device for 30 days")

class TwoFactorDisableRequest(BaseSchema):
    """Schema für 2FA Deactivation"""
    password: str = Field(..., description="Current password for confirmation")
    backup_code: Optional[str] = Field(description="Backup code if password auth fails")

class TwoFactorBackupCodesResponse(BaseSchema):
    """Schema für 2FA Backup Codes"""
    backup_codes: List[str] = Field(..., description="New backup recovery codes")
    codes_remaining: int = Field(..., description="Number of unused backup codes")

# ================================
# API KEY MANAGEMENT SCHEMAS (Future Extension)
# ================================

class ApiKeyCreateRequest(BaseSchema):
    """Schema für API Key Creation"""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: List[str] = Field(..., description="Permissions for this API key")
    expires_in_days: Optional[int] = Field(ge=1, le=365, description="Expiration in days")

class ApiKeyResponse(BaseSchema, TimestampMixin):
    """Schema für API Key Response"""
    id: UUID
    name: str
    key_prefix: str = Field(..., description="First 8 characters of the API key")
    permissions: List[str]
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

class ApiKeyListResponse(BaseSchema):
    """Schema für API Key List"""
    api_keys: List[ApiKeyResponse]
    total: int

# ================================
# USER IMPORT/EXPORT SCHEMAS
# ================================

class UserExportRequest(BaseSchema):
    """Schema für User Export"""
    format: Literal["csv", "xlsx", "json"] = Field(default="csv", description="Export format")
    include_roles: bool = Field(default=True, description="Include user roles in export")
    include_permissions: bool = Field(default=False, description="Include detailed permissions")
    filter_active_only: bool = Field(default=False, description="Export only active users")

class UserImportRequest(BaseSchema):
    """Schema für User Import"""
    file_url: str = Field(..., description="URL of file to import")
    format: Literal["csv", "xlsx"] = Field(..., description="File format")
    mapping: dict[str, str] = Field(..., description="Column mapping for import")
    default_role_id: UUID = Field(..., description="Default role to assign to imported users")
    send_welcome_emails: bool = Field(default=False, description="Send welcome emails to imported users")
    skip_duplicates: bool = Field(default=True, description="Skip users with duplicate emails")

class UserImportResponse(BaseSchema):
    """Schema für User Import Response"""
    import_id: UUID
    total_rows: int
    successful_imports: int
    failed_imports: int
    skipped_duplicates: int
    errors: List[dict] = Field(description="Import errors with row numbers")

# ================================
# USER PREFERENCES SCHEMAS
# ================================

class UserPreferences(BaseSchema):
    """Schema für User Preferences"""
    language: str = Field(default="en", description="Preferred language (ISO 639-1)")
    timezone: str = Field(default="UTC", description="User timezone")
    date_format: str = Field(default="YYYY-MM-DD", description="Preferred date format")
    time_format: str = Field(default="24h", description="12h or 24h time format")
    theme: Literal["light", "dark", "auto"] = Field(default="light", description="UI theme preference")
    notifications_email: bool = Field(default=True, description="Receive email notifications")
    notifications_browser: bool = Field(default=True, description="Receive browser notifications")

class UserPreferencesUpdate(BaseSchema):
    """Schema für User Preferences Update"""
    language: Optional[str]
    timezone: Optional[str]
    date_format: Optional[str]
    time_format: Optional[Literal["12h", "24h"]] = None
    theme: Optional[Literal["light", "dark", "auto"]] = None
    notifications_email: Optional[bool]
    notifications_browser: Optional[bool]

# ================================
# USER ACTIVITY SCHEMAS
# ================================

class UserActivityResponse(BaseSchema, TimestampMixin):
    """Schema für User Activity"""
    id: UUID
    user_id: UUID
    activity_type: str
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: dict = Field(default_factory=dict)

class UserActivityListResponse(BaseSchema):
    """Schema für User Activity List"""
    activities: List[UserActivityResponse]
    total: int
    page: int
    page_size: int

class UserActivityFilterParams(PaginationParams, SortParams):
    """Schema für User Activity Filtering"""
    activity_type: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# ================================
# COMPLIANCE & GDPR SCHEMAS
# ================================

class UserDataExportRequest(BaseSchema):
    """Schema für GDPR Data Export Request"""
    user_id: UUID = Field(..., description="User ID to export data for")
    include_audit_logs: bool = Field(default=True, description="Include audit logs")
    include_business_data: bool = Field(default=True, description="Include business data (projects, documents)")
    format: Literal["json", "pdf"] = Field(default="json", description="Export format")

class UserDataDeletionRequest(BaseSchema):
    """Schema für GDPR Data Deletion Request"""
    user_id: UUID = Field(..., description="User ID to delete data for")
    reason: str = Field(..., description="Reason for data deletion")
    retain_audit_logs: bool = Field(default=True, description="Retain audit logs for compliance")
    anonymize_instead: bool = Field(default=False, description="Anonymize instead of delete")

class UserComplianceReport(BaseSchema):
    """Schema für User Compliance Report"""
    user_id: UUID
    data_collected: List[str] = Field(description="Types of data collected")
    consent_status: dict = Field(description="Consent status for various data uses")
    data_retention_policy: str
    last_login: Optional[datetime]
    account_age_days: int
    gdpr_compliant: bool

# ================================
# FORWARD REFERENCES
# ================================

# Update forward references for circular dependencies
UserResponse.model_rebuild()