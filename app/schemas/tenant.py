# ================================
# TENANT SCHEMAS (schemas/tenant.py)
# ================================

from pydantic import Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from app.schemas.base import BaseSchema, TimestampMixin, SlugFieldMixin, DomainFieldMixin

class TenantBase(BaseSchema, DomainFieldMixin):
    """Base Tenant Schema"""
    name: str = Field(..., min_length=2, max_length=255, description="Organization name")
    domain: Optional[str] = Field(max_length=255, description="Organization domain")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Tenant-specific settings")
    subscription_plan: str = Field(default="basic", description="Subscription plan")
    max_users: int = Field(default=10, ge=1, le=10000, description="Maximum number of users")
    is_active: bool = Field(default=True, description="Tenant active status")
    
    # Investagon Integration
    investagon_organization_id: Optional[str] = Field(max_length=255, description="Investagon organization ID")
    investagon_api_key: Optional[str] = Field(max_length=255, description="Investagon API key")
    investagon_sync_enabled: bool = Field(default=False, description="Enable automatic Investagon sync")
    
    # Contact Information
    contact_email: Optional[str] = Field(max_length=255, description="Contact email")
    contact_phone: Optional[str] = Field(max_length=100, description="Contact phone")
    contact_street: Optional[str] = Field(max_length=255, description="Contact street")
    contact_house_number: Optional[str] = Field(max_length=50, description="Contact house number")
    contact_city: Optional[str] = Field(max_length=100, description="Contact city")
    contact_state: Optional[str] = Field(max_length=100, description="Contact state")
    contact_zip_code: Optional[str] = Field(max_length=20, description="Contact ZIP code")
    contact_country: Optional[str] = Field(max_length=100, description="Contact country")

class TenantCreate(TenantBase, SlugFieldMixin):
    """Schema für Tenant-Erstellung (nur Super-Admin)"""
    slug: str = Field(..., min_length=2, max_length=100, description="URL-friendly identifier")
    
    # Super-Admin der diesen Tenant erstellt
    admin_email: EmailStr = Field(..., description="Email of the first tenant admin")
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_password: Optional[str] = Field(min_length=8, description="Admin password (optional, will generate if not provided)")

class TenantUpdate(BaseSchema, DomainFieldMixin):
    """Schema für Tenant-Updates"""
    name: Optional[str] = Field(min_length=2, max_length=255)
    domain: Optional[str] = Field(max_length=255)
    settings: Optional[Dict[str, Any]] = None
    subscription_plan: Optional[str]
    max_users: Optional[int] = Field(ge=1, le=10000)
    is_active: Optional[bool]
    
    # Investagon Integration
    investagon_organization_id: Optional[str] = Field(max_length=255)
    investagon_api_key: Optional[str] = Field(max_length=255)
    investagon_sync_enabled: Optional[bool]
    
    # Contact Information
    contact_email: Optional[str] = Field(max_length=255)
    contact_phone: Optional[str] = Field(max_length=100)
    contact_street: Optional[str] = Field(max_length=255)
    contact_house_number: Optional[str] = Field(max_length=50)
    contact_city: Optional[str] = Field(max_length=100)
    contact_state: Optional[str] = Field(max_length=100)
    contact_zip_code: Optional[str] = Field(max_length=20)
    contact_country: Optional[str] = Field(max_length=100)

class TenantResponse(TenantBase, TimestampMixin):
    """Schema für Tenant-Responses"""
    id: UUID
    slug: str
    user_count: Optional[int] = Field(description="Current number of users")

class TenantListResponse(BaseSchema):
    """Schema für Tenant-Listen"""
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int

# ================================
# IDENTITY PROVIDER SCHEMAS (schemas/identity_provider.py)
# ================================

class TenantIdentityProviderBase(BaseSchema):
    """Base Schema für Identity Provider Konfiguration"""
    provider: Literal["microsoft", "google", "azuread", "okta", "auth0"] = Field(..., description="OAuth provider type")
    provider_type: Literal["saml", "oidc", "oauth2"] = Field(default="oauth2", description="Protocol type")
    
    # OAuth2/OIDC Configuration
    client_id: str = Field(..., min_length=1, description="OAuth client ID")
    discovery_endpoint: Optional[str] = Field(description="OIDC discovery endpoint")
    authorization_endpoint: Optional[str]
    token_endpoint: Optional[str]
    userinfo_endpoint: Optional[str]
    jwks_uri: Optional[str]
    
    # User Mapping
    user_attribute_mapping: Dict[str, str] = Field(default_factory=dict, description="Map provider attributes to user fields")
    role_attribute_mapping: Dict[str, str] = Field(default_factory=dict, description="Map provider roles to system roles")
    
    # Settings
    auto_provision_users: bool = Field(default=True, description="Auto-create users on first login")
    require_verified_email: bool = Field(default=True, description="Require verified email from provider")
    allowed_domains: List[str] = Field(default_factory=list, description="Restrict to specific email domains")
    is_active: bool = Field(default=True, description="Provider is active")

class MicrosoftIdentityProviderCreate(TenantIdentityProviderBase):
    """Schema für Microsoft Entra ID Konfiguration"""
    provider: Literal["microsoft"] = "microsoft"
    azure_tenant_id: str = Field(..., description="Microsoft Entra Tenant ID")
    client_secret: str = Field(..., min_length=1, description="OAuth client secret")
    default_role_name: Optional[str] = Field("user", description="Default role for new users")

class GoogleIdentityProviderCreate(TenantIdentityProviderBase):
    """Schema für Google Workspace Konfiguration"""
    provider: Literal["google"] = "google"
    client_secret: str = Field(..., min_length=1, description="OAuth client secret")
    default_role_name: Optional[str] = Field("user", description="Default role for new users")

class IdentityProviderResponse(TenantIdentityProviderBase, TimestampMixin):
    """Schema für Identity Provider Response"""
    id: UUID
    tenant_id: UUID
    # client_secret wird nicht zurückgegeben
    azure_tenant_id: Optional[str]

class IdentityProviderUpdate(BaseSchema):
    """Schema für Identity Provider Updates"""
    client_id: Optional[str] = Field(min_length=1)
    client_secret: Optional[str] = Field(min_length=1)
    azure_tenant_id: Optional[str]
    discovery_endpoint: Optional[str]
    user_attribute_mapping: Optional[Dict[str, str]] = None
    role_attribute_mapping: Optional[Dict[str, str]] = None
    auto_provision_users: Optional[bool]
    require_verified_email: Optional[bool]
    allowed_domains: Optional[List[str]] = None
    is_active: Optional[bool]

class IdentityProviderListResponse(BaseSchema):
    """Schema für Identity Provider Listen"""
    providers: List[IdentityProviderResponse]
    total: int

# ================================
# TENANT FILTERING SCHEMAS
# ================================

from app.schemas.base import PaginationParams, SortParams, SearchParams

class TenantFilterParams(PaginationParams, SortParams, SearchParams):
    """Schema für Tenant-Filtering"""
    subscription_plan: Optional[str] = None
    is_active: Optional[bool] = None
    has_domain: Optional[bool] = None

class TenantStatsResponse(BaseSchema):
    """Schema für Tenant-Statistiken"""
    total_tenants: int
    active_tenants: int
    total_users: int
    tenants_by_plan: Dict[str, int]
    recent_signups: int