# ================================
# API PACKAGE INITIALIZATION (api/__init__.py)
# ================================

"""
API Package

Root package für alle API-Routen
"""

from fastapi import APIRouter

# Basis Router für die gesamte API
api_router = APIRouter()

# Version Info
API_VERSION = "1.0.0"
API_TITLE = "Enterprise Multi-Tenant API"
API_DESCRIPTION = """
Enterprise Multi-Tenant API with OAuth Support

## Features
- Multi-tenant architecture with row-level security
- OAuth integration (Microsoft Entra ID, Google Workspace)
- Role-based access control (RBAC)
- Super admin impersonation
- Comprehensive audit logging
- Business logic APIs (Projects, Documents)

## Authentication
- Local authentication (email/password)
- OAuth 2.0 (Microsoft, Google)
- JWT tokens with refresh mechanism
- Super admin impersonation

## Authorization
- Tenant-based isolation
- Role-based permissions
- Resource-level access control
"""

__all__ = ["api_router", "API_VERSION", "API_TITLE", "API_DESCRIPTION"]

# ================================
# API V1 INITIALIZATION (api/v1/__init__.py)
# ================================

"""
API Version 1

Alle V1 API Routes und Dependencies
"""

from fastapi import APIRouter, Depends
from app.dependencies import get_db, get_current_user

# Import all route modules
from app.api.v1 import auth, users, tenants, properties, cities, exposes, admin, rbac, user_team, maps

# Create V1 router
v1_router = APIRouter(prefix="/v1")

# Include all route modules
v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Access denied"}
    }
)

v1_router.include_router(
    users.router,
    prefix="/users",
    tags=["User Management"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "User not found"}
    }
)

v1_router.include_router(
    rbac.router,
    prefix="/rbac",
    tags=["Role & Permission Management"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Role or permission not found"}
    }
)

v1_router.include_router(
    user_team.router,
    prefix="/teams",
    tags=["Team Management"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

v1_router.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Tenant Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Super admin access required"},
        404: {"description": "Tenant not found"}
    }
)

v1_router.include_router(
    properties.router,
    prefix="/properties",
    tags=["Properties"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

v1_router.include_router(
    cities.router,
    prefix="/cities",
    tags=["Cities"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

v1_router.include_router(
    exposes.router,
    prefix="/exposes",
    tags=["Exposes"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"}
    }
)

v1_router.include_router(
    maps.router,
    prefix="/maps",
    tags=["Maps"],
    dependencies=[Depends(get_current_user)],
    responses={
        401: {"description": "Authentication required"},
        503: {"description": "Service unavailable"}
    }
)

v1_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Super Admin"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Super admin access required"}
    }
)

# Health check endpoint für V1
@v1_router.get("/health", tags=["Health"])
async def v1_health_check():
    """V1 API Health Check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "api_version": "v1"
    }

# API Info endpoint
@v1_router.get("/info", tags=["Info"])
async def v1_api_info():
    """V1 API Information"""
    return {
        "api_version": "1.0.0",
        "title": "Enterprise Multi-Tenant API v1",
        "description": "Production-ready multi-tenant API with OAuth support",
        "endpoints": {
            "auth": "Authentication and OAuth",
            "users": "User management and profiles",
            "tenants": "Tenant administration (Super Admin)",
            "projects": "Business logic and document management",
            "admin": "System administration (Super Admin)"
        },
        "features": [
            "Multi-tenant architecture",
            "OAuth 2.0 integration",
            "Role-based access control",
            "Audit logging",
            "Super admin impersonation"
        ]
    }

__all__ = ["v1_router"]

# ================================
# ROUTE DEPENDENCIES (api/dependencies.py)
# ================================

"""
Route-spezifische Dependencies

Zusätzliche Dependencies die nur in API-Routen verwendet werden
"""

from fastapi import Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.models.user import User
from typing import Optional
import uuid

def get_tenant_from_header(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Optional[uuid.UUID]:
    """Extrahiert Tenant-ID aus Header (für Multi-Tenant APIs)"""
    if x_tenant_id:
        try:
            return uuid.UUID(x_tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant ID format")
    return None

def require_tenant_header():
    """Erfordert Tenant-ID im Header"""
    def tenant_header_dependency(
        tenant_id: Optional[uuid.UUID] = Depends(get_tenant_from_header)
    ) -> uuid.UUID:
        if not tenant_id:
            raise HTTPException(
                status_code=400, 
                detail="Tenant ID required in X-Tenant-ID header"
            )
        return tenant_id
    
    return tenant_header_dependency

def get_user_agent(
    user_agent: Optional[str] = Header(None, alias="User-Agent")
) -> Optional[str]:
    """Extrahiert User-Agent aus Header"""
    return user_agent

def get_client_ip(
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP")
) -> Optional[str]:
    """Extrahiert Client-IP aus Headers"""
    if x_forwarded_for:
        # Get first IP from X-Forwarded-For chain
        return x_forwarded_for.split(',')[0].strip()
    return x_real_ip

def validate_api_version(
    accept_version: Optional[str] = Header(None, alias="Accept-Version")
) -> str:
    """Validiert API-Version aus Header"""
    supported_versions = ["1.0", "1.0.0", "v1"]
    
    if accept_version and accept_version not in supported_versions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {accept_version}. Supported: {', '.join(supported_versions)}"
        )
    
    return accept_version or "1.0.0"

def require_content_type(content_type: str):
    """Erfordert spezifischen Content-Type"""
    def content_type_dependency(
        content_type_header: Optional[str] = Header(None, alias="Content-Type")
    ):
        if content_type_header != content_type:
            raise HTTPException(
                status_code=415,
                detail=f"Content-Type must be {content_type}"
            )
        return content_type_header
    
    return content_type_dependency

def get_request_context(
    user_agent: Optional[str] = Depends(get_user_agent),
    client_ip: Optional[str] = Depends(get_client_ip),
    api_version: str = Depends(validate_api_version)
) -> dict:
    """Sammelt Request-Kontext für Audit-Logging"""
    return {
        "user_agent": user_agent,
        "client_ip": client_ip,
        "api_version": api_version
    }

# ================================
# API RATE LIMITING DEPENDENCIES
# ================================

from datetime import datetime, timedelta
from typing import Dict
import time

# In-Memory Rate Limiting (in production: use Redis)
rate_limit_storage: Dict[str, list] = {}

def rate_limit(max_requests: int, window_minutes: int):
    """Rate Limiting Dependency"""
    def rate_limit_dependency(
        current_user: User = Depends(get_current_user),
        client_ip: Optional[str] = Depends(get_client_ip)
    ):
        # Use user ID + IP as key
        key = f"{current_user.id}:{client_ip or 'unknown'}"
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        # Initialize or clean old requests
        if key not in rate_limit_storage:
            rate_limit_storage[key] = []
        
        # Remove old requests outside window
        rate_limit_storage[key] = [
            req_time for req_time in rate_limit_storage[key] 
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(rate_limit_storage[key]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {max_requests} requests per {window_minutes} minutes",
                headers={"Retry-After": str(window_minutes * 60)}
            )
        
        # Record this request
        rate_limit_storage[key].append(current_time)
        
        return True
    
    return rate_limit_dependency

# ================================
# API RESPONSE HELPERS
# ================================

from fastapi.responses import JSONResponse
from app.schemas.base import SuccessResponse, ErrorResponse

def create_success_response(
    message: str, 
    data: Optional[dict] = None,
    status_code: int = 200
) -> JSONResponse:
    """Erstellt standardisierte Success Response"""
    response_data = SuccessResponse(message=message, data=data)
    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump()
    )

def create_error_response(
    detail: str,
    error_code: Optional[str] = None,
    status_code: int = 400
) -> JSONResponse:
    """Erstellt standardisierte Error Response"""
    response_data = ErrorResponse(detail=detail, error_code=error_code)
    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump()
    )

# ================================
# EXPORTS
# ================================

__all__ = [
    "get_tenant_from_header",
    "require_tenant_header", 
    "get_user_agent",
    "get_client_ip",
    "validate_api_version",
    "require_content_type",
    "get_request_context",
    "rate_limit",
    "create_success_response",
    "create_error_response"
]