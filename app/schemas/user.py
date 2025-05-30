# ================================
# USER SCHEMAS (schemas/user.py)
# ================================

from pydantic import Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema, TimestampMixin, PaginationParams, SortParams, SearchParams

class UserBase(BaseSchema):
    """Base User Schema"""
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    is_active: bool = Field(default=True, description="User active status")

class UserCreate(UserBase):
    """Schema für User-Erstellung durch Admin"""
    password: Optional[str] = Field(None, min_length=8, description="User password (optional, will generate if not provided)")
    role_ids: List[UUID] = Field(default_factory=list, description="Role IDs to assign")
    send_welcome_email: bool = Field(default=True, description="Send welcome email to user")
    require_email_verification: bool = Field(default=False, description="Require email verification before login")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID (only for super admin)")

class UserUpdate(BaseSchema):
    """Schema für User-Updates"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")

class UserResponse(UserBase, TimestampMixin):
    """Schema für User-Responses"""
    id: UUID
    tenant_id: Optional[UUID]
    auth_method: Literal["local", "microsoft", "google"]
    is_super_admin: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    avatar_url: Optional[str] = None
    
    # Role Information
    roles: List['RoleResponse'] = Field(default_factory=list)

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
    impersonated_tenant_id: Optional[UUID] = None

class ActiveSessionsResponse(BaseSchema):
    """Schema für aktive Sessions"""
    sessions: List[UserSessionResponse]
    total_active: int

class SessionTerminateRequest(BaseSchema):
    """Schema für Session-Terminierung"""
    session_id: Optional[UUID] = Field(None, description="Specific session to terminate (if not provided, terminates current session)")
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
    welcome_message: Optional[str] = Field(None, description="Custom welcome message")
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
    first_name: Optional[str] = Field(None, description="Update first name")
    last_name: Optional[str] = Field(None, description="Update last name")

# ================================
# USER BULK OPERATIONS
# ================================

class UserBulkCreateRequest(BaseSchema):
    """Schema für Bulk User Creation"""
    users: List[UserCreate] = Field(..., min_items=1, max_items=100)
    send_welcome_emails: bool = Field(default=True)
    default_