# ================================
# BASE SCHEMAS (schemas/base.py)
# ================================

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class BaseSchema(BaseModel):
    """Base Schema mit gemeinsamer Konfiguration"""
    model_config = ConfigDict(
        from_attributes=True,  # Pydantic v2: ermöglicht ORM integration
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        exclude_none=True,  # Exclude None values from responses
        json_schema_extra={
            "examples": []
        }
    )

class BaseResponseSchema(BaseSchema):
    """Base Schema for API responses with ID field"""
    id: UUID

class TimestampMixin(BaseModel):
    """Mixin für Timestamp-Felder"""
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class AuditMixin(BaseModel):
    """Mixin für Audit-Felder"""
    created_by: UUID = Field(..., description="User who created this resource")
    updated_by: Optional[UUID] = Field(description="User who last updated this resource")

# ================================
# PAGINATION & FILTERING SCHEMAS (schemas/common.py)
# ================================

from typing import Literal

class PaginationParams(BaseSchema):
    """Schema für Pagination Parameter"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=500, description="Items per page")

class SortParams(BaseSchema):
    """Schema für Sorting Parameter"""
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")

class SearchParams(BaseSchema):
    """Schema für Search Parameter"""
    search: Optional[str] = Field(description="Search term")

# ================================
# ERROR RESPONSE SCHEMAS (schemas/errors.py)
# ================================

from typing import Dict, Any

class ErrorResponse(BaseSchema):
    """Standard Error Response Schema"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(description="Application-specific error code")
    field_errors: Optional[Dict[str, List[str]]] = Field(None, description="Validation errors by field")

class ValidationErrorResponse(BaseSchema):
    """Pydantic Validation Error Response"""
    detail: str = "Validation error"
    errors: List[Dict[str, Any]] = Field(..., description="Detailed validation errors")

class SuccessResponse(BaseSchema):
    """Standard Success Response Schema"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

# ================================
# HEALTH & MONITORING SCHEMAS (schemas/system.py)
# ================================

class SystemHealthResponse(BaseSchema):
    """Schema für System Health Check"""
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    database: Literal["connected", "disconnected"]
    email_service: Literal["available", "unavailable"]
    oauth_providers: Dict[str, bool]

class ServiceInfo(BaseSchema):
    """Schema für Service Information"""
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    description: Optional[str] = Field(description="Service description")
    environment: str = Field(..., description="Environment (dev/staging/prod)")
    uptime: Optional[str] = Field(description="Service uptime")

# ================================
# COMMON FIELD VALIDATORS
# ================================

import re
from pydantic import field_validator

class EmailFieldMixin:
    """Mixin für Email-Validierung"""
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        # Zusätzliche Email-Validierung falls nötig
        return v.lower()

class SlugFieldMixin:
    """Mixin für Slug-Validierung"""
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        slug_pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        if not re.match(slug_pattern, v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v

class PasswordFieldMixin:
    """Mixin für Password-Validierung"""
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

class DomainFieldMixin:
    """Mixin für Domain-Validierung"""
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(domain_pattern, v):
            raise ValueError('Invalid domain format')
        return v.lower()