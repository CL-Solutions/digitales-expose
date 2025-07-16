# ================================
# DATABASE INITIALIZATION (models/__init__.py)
# ================================

"""
Database Models Package

Importiert alle Models für Alembic Auto-Generation
"""

from app.models.base import Base

# Import all models for Alembic auto-generation
from app.models.tenant import Tenant, TenantIdentityProvider
from app.models.user import User, UserSession, OAuthToken, PasswordResetToken
from app.models.user_preferences import UserFilterPreference
from app.models.user_team import UserTeamAssignment, UserRequest
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.business import (
    Property, PropertyImage, 
    City, CityImage,
    ExposeTemplate, ExposeLink, ExposeLinkView,
    InvestagonSync, Project, ProjectImage,
    Reservation, ReservationStatusHistory,
    ProjectDocument, PropertyDocument, DocumentType
)
from app.models.audit import AuditLog, SuperAdminSession
from app.models.google_maps_cache import GoogleGeocodingCache, GooglePlacesCache, GoogleDistanceCache

# Export all models
__all__ = [
    "Base",
    "Tenant", 
    "TenantIdentityProvider",
    "User", 
    "UserSession", 
    "OAuthToken", 
    "PasswordResetToken",
    "UserFilterPreference",
    "UserTeamAssignment",
    "UserRequest",
    "Permission", 
    "Role", 
    "RolePermission", 
    "UserRole",
    "Property",
    "PropertyImage",
    "City",
    "CityImage",
    "ExposeTemplate",
    "ExposeLink",
    "ExposeLinkView",
    "InvestagonSync",
    "Project",
    "ProjectImage",
    "ProjectDocument",
    "PropertyDocument",
    "DocumentType",
    "Reservation",
    "ReservationStatusHistory",
    "AuditLog", 
    "SuperAdminSession",
    "GoogleGeocodingCache",
    "GooglePlacesCache", 
    "GoogleDistanceCache"
]

