# ================================
# SCHEMAS PACKAGE INITIALIZATION (schemas/__init__.py)
# ================================

"""
Pydantic Schemas Package

Zentrale Imports für alle Schemas im System
"""

# Base Schemas
from app.schemas.base import (
    BaseSchema,
    TimestampMixin,
    AuditMixin,
    PaginationParams,
    SortParams,
    SearchParams,
    ErrorResponse,
    ValidationErrorResponse,
    SuccessResponse,
    SystemHealthResponse,
    ServiceInfo
)

# Tenant Schemas
from app.schemas.tenant import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantFilterParams,
    TenantStatsResponse,
    TenantIdentityProviderBase,
    MicrosoftIdentityProviderCreate,
    GoogleIdentityProviderCreate,
    IdentityProviderResponse,
    IdentityProviderUpdate,
    IdentityProviderListResponse
)

# User Schemas
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserProfileResponse,
    UserFilterParams,
    UserStatsResponse,
    UserSessionResponse,
    ActiveSessionsResponse,
    SessionTerminateRequest,
    UserInviteRequest,
    UserInviteResponse,
    UserInviteAcceptRequest,
    UserBulkCreateRequest,
    UserBulkCreateResponse,
    UserBulkUpdateRequest,
    UserBulkActionRequest,
    UserBulkActionResponse,
    UserSecurityInfo,
    UserSecurityEventResponse
)

# Authentication Schemas
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ImpersonateRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    OAuthCallbackRequest,
    OAuthUrlResponse,
    OAuthErrorResponse,
    OAuthTokenRefreshRequest,
    OAuthRevokeRequest,
    AuthStatusResponse,
    LoginHistoryResponse,
    SecurityEventResponse,
    AuthAuditResponse,
    AuthAuditFilterParams,
    AuthStatsResponse
)

# RBAC Schemas
from app.schemas.rbac import (
    PermissionBase,
    PermissionCreate,
    PermissionResponse,
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRoleAssignment,
    UserRoleResponse,
    RolePermissionUpdate,
    RoleBulkAssignRequest,
    RoleBulkAssignResponse,
    RoleCloneRequest,
    PermissionGroupResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    UserPermissionsResponse,
    RoleFilterParams,
    PermissionFilterParams,
    RBACStatsResponse,
    RoleUsageReport,
    PermissionUsageReport,
    RBACActivityResponse,
    RBACComplianceReport
)

# Business Logic Schemas
from app.schemas.business import (
    # Property Schemas
    PropertyBase,
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyImageSchema,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyFilter,
    PropertyListResponse,
    
    # City Schemas
    CityBase,
    CityCreate,
    CityUpdate,
    CityResponse,
    CityImageCreate,
    CityImageUpdate,
    CityImageSchema,
    
    # Expose Template Schemas
    ExposeTemplateBase,
    ExposeTemplateCreate,
    ExposeTemplateUpdate,
    ExposeTemplateResponse,
    
    # Expose Link Schemas
    ExposeLinkBase,
    ExposeLinkCreate,
    ExposeLinkUpdate,
    ExposeLinkResponse,
    ExposeLinkPublicResponse,
    
    # Sync Schemas
    InvestagonSyncSchema
)

# User Preferences Schemas
from app.schemas.user_preferences import (
    UserFilterPreferenceBase,
    UserFilterPreferenceCreate,
    UserFilterPreferenceUpdate,
    UserFilterPreferenceResponse
)

# ================================
# SCHEMA COLLECTIONS
# ================================

# Request Schemas (für API Input)
REQUEST_SCHEMAS = {
    # Authentication
    "login": LoginRequest,
    "register": CreateUserRequest,
    "password_reset": PasswordResetRequest,
    "password_change": ChangePasswordRequest,
    
    # User Management
    "user_create": UserCreate,
    "user_update": UserUpdate,
    "user_invite": UserInviteRequest,
    
    # Tenant Management
    "tenant_create": TenantCreate,
    "tenant_update": TenantUpdate,
    
    # RBAC
    "role_create": RoleCreate,
    "role_update": RoleUpdate,
    "permission_create": PermissionCreate,
    
    # Business Logic
    "property_create": PropertyCreate,
    "property_update": PropertyUpdate,
    "city_create": CityCreate,
    "city_update": CityUpdate,
    "expose_template_create": ExposeTemplateCreate,
    "expose_template_update": ExposeTemplateUpdate,
    "expose_link_create": ExposeLinkCreate,
    "expose_link_update": ExposeLinkUpdate,
    
    # User Preferences
    "user_filter_preference_create": UserFilterPreferenceCreate,
    "user_filter_preference_update": UserFilterPreferenceUpdate,
}

# Response Schemas (für API Output)
RESPONSE_SCHEMAS = {
    # Authentication
    "token": TokenResponse,
    "auth_status": AuthStatusResponse,
    
    # User Management
    "user": UserResponse,
    "user_list": UserListResponse,
    "user_profile": UserProfileResponse,
    
    # Tenant Management
    "tenant": TenantResponse,
    "tenant_list": TenantListResponse,
    
    # RBAC
    "role": RoleResponse,
    "permission": PermissionResponse,
    "user_permissions": UserPermissionsResponse,
    
    # Business Logic
    "property": PropertyResponse,
    "property_list": PropertyListResponse,
    "city": CityResponse,
    "expose_template": ExposeTemplateResponse,
    "expose_link": ExposeLinkResponse,
    "expose_link_public": ExposeLinkPublicResponse,
    "investagon_sync": InvestagonSyncSchema,
    
    # User Preferences
    "user_filter_preference": UserFilterPreferenceResponse,
    
    # System
    "health": SystemHealthResponse,
    "error": ErrorResponse,
    "success": SuccessResponse,
}

# Filter Schemas (für Query Parameters)
FILTER_SCHEMAS = {
    "tenant_filter": TenantFilterParams,
    "user_filter": UserFilterParams,
    "property_filter": PropertyFilter,
    "role_filter": RoleFilterParams,
    "permission_filter": PermissionFilterParams,
}

# ================================
# SCHEMA VALIDATION HELPERS
# ================================

from typing import Type, Dict, Any
from pydantic import ValidationError

def validate_schema(schema_class: Type[BaseSchema], data: Dict[str, Any]) -> BaseSchema:
    """Validiert Daten gegen ein Schema"""
    try:
        return schema_class.model_validate(data)
    except ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e}")

def get_schema_by_name(schema_name: str, schema_type: str = "response") -> Type[BaseSchema]:
    """Gibt Schema-Klasse anhand des Namens zurück"""
    schema_collections = {
        "request": REQUEST_SCHEMAS,
        "response": RESPONSE_SCHEMAS,
        "filter": FILTER_SCHEMAS,
    }
    
    collection = schema_collections.get(schema_type)
    if not collection:
        raise ValueError(f"Unknown schema type: {schema_type}")
    
    schema_class = collection.get(schema_name)
    if not schema_class:
        raise ValueError(f"Unknown schema name: {schema_name}")
    
    return schema_class

def generate_openapi_schema_examples():
    """Generiert OpenAPI Schema-Beispiele für alle Schemas"""
    examples = {}
    
    for schema_name, schema_class in RESPONSE_SCHEMAS.items():
        try:
            # Generiere Beispiel-Daten für Schema
            example = schema_class.model_json_schema()
            examples[schema_name] = example
        except Exception as e:
            print(f"Failed to generate example for {schema_name}: {e}")
    
    return examples

# ================================
# SCHEMA VERSIONING (Future Extension)
# ================================

SCHEMA_VERSION = "1.0.0"

class SchemaVersion:
    """Schema-Versionierung für API Compatibility"""
    
    @staticmethod
    def get_compatible_schemas(version: str) -> Dict[str, Type[BaseSchema]]:
        """Gibt kompatible Schemas für eine API-Version zurück"""
        # Future: Implementierung für Schema-Versionierung
        if version == "1.0.0":
            return RESPONSE_SCHEMAS
        else:
            raise ValueError(f"Unsupported schema version: {version}")

# ================================
# SCHEMA DOCUMENTATION
# ================================

def get_schema_documentation() -> Dict[str, Dict[str, Any]]:
    """Generiert Dokumentation für alle Schemas"""
    docs = {}
    
    all_schemas = {**REQUEST_SCHEMAS, **RESPONSE_SCHEMAS, **FILTER_SCHEMAS}
    
    for schema_name, schema_class in all_schemas.items():
        docs[schema_name] = {
            "name": schema_name,
            "class": schema_class.__name__,
            "description": schema_class.__doc__ or "No description available",
            "fields": schema_class.model_fields,
            "json_schema": schema_class.model_json_schema()
        }
    
    return docs

# ================================
# EXPORTS
# ================================

__all__ = [
    # Base
    "BaseSchema", "TimestampMixin", "AuditMixin",
    "PaginationParams", "SortParams", "SearchParams",
    "ErrorResponse", "ValidationErrorResponse", "SuccessResponse",
    
    # Tenant
    "TenantCreate", "TenantUpdate", "TenantResponse", "TenantListResponse",
    "MicrosoftIdentityProviderCreate", "GoogleIdentityProviderCreate",
    
    # User
    "UserCreate", "UserUpdate", "UserResponse", "UserListResponse",
    "UserProfileResponse", "UserFilterParams",
    
    # Auth
    "LoginRequest", "TokenResponse", "PasswordResetRequest",
    "CreateUserRequest", "OAuthCallbackRequest", "AuthStatusResponse",
    
    # RBAC
    "RoleCreate", "RoleResponse", "PermissionResponse",
    "UserRoleAssignment", "UserPermissionsResponse",
    "RoleDetailResponse", "RoleListResponse", "BulkRoleAssignment",
    
    # Business
    "ProjectCreate", "ProjectResponse", "ProjectDetailResponse",
    "DocumentCreate", "DocumentResponse", "DocumentDetailResponse",
    
    # Collections
    "REQUEST_SCHEMAS", "RESPONSE_SCHEMAS", "FILTER_SCHEMAS",
    
    # Helpers
    "validate_schema", "get_schema_by_name", "get_schema_documentation",
    "SCHEMA_VERSION"
]