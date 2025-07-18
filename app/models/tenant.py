# ================================
# TENANT MODELS (models/tenant.py)
# ================================

from sqlalchemy import Column, String, Integer, Boolean, JSON, Text, ARRAY, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid

class Tenant(Base):
    """Tenant/Organization Model"""
    __tablename__ = "tenants"
    
    # Basic Information
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=True, index=True)
    
    # Configuration
    settings = Column(JSON, default=dict, nullable=False)
    subscription_plan = Column(String(50), default="basic", nullable=False)
    max_users = Column(Integer, default=10, nullable=False)
    
    # Contact Information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(100), nullable=True)
    contact_street = Column(String(255), nullable=True)
    contact_house_number = Column(String(50), nullable=True)
    contact_city = Column(String(100), nullable=True)
    contact_state = Column(String(100), nullable=True)
    contact_zip_code = Column(String(20), nullable=True)
    contact_country = Column(String(100), nullable=True)
    
    # Company Branding
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color e.g. #FF5733
    secondary_color = Column(String(7), nullable=True)  # Hex color
    accent_color = Column(String(7), nullable=True)  # Hex color
    
    # Investagon Integration
    investagon_organization_id = Column(String(255), nullable=True)
    investagon_api_key = Column(String(255), nullable=True)  # Should be encrypted in production
    investagon_sync_enabled = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    identity_providers = relationship("TenantIdentityProvider", back_populates="tenant", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="tenant", cascade="all, delete-orphan")
    # Removed properties relationship to prevent circular loading when accessing Property.tenant
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant(name='{self.name}', slug='{self.slug}')>"

class TenantIdentityProvider(Base):
    """Tenant-spezifische OAuth/SAML Identity Provider Konfiguration"""
    __tablename__ = "tenant_identity_providers"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Provider Configuration
    provider = Column(String(50), nullable=False)  # 'microsoft', 'google', etc.
    provider_type = Column(String(50), default="oauth2", nullable=False)  # 'oauth2', 'saml', 'oidc'
    
    # OAuth2/OIDC Configuration
    client_id = Column(String(255), nullable=False)
    client_secret_hash = Column(String(255), nullable=False)  # Encrypted
    azure_tenant_id = Column(String(255), nullable=True)  # Microsoft specific
    
    # Endpoints
    discovery_endpoint = Column(Text, nullable=True)
    authorization_endpoint = Column(Text, nullable=True)
    token_endpoint = Column(Text, nullable=True)
    userinfo_endpoint = Column(Text, nullable=True)
    jwks_uri = Column(Text, nullable=True)
    
    # SAML Configuration (future)
    sso_url = Column(Text, nullable=True)
    slo_url = Column(Text, nullable=True)
    certificate = Column(Text, nullable=True)
    
    # User/Role Mapping
    user_attribute_mapping = Column(JSON, default=dict, nullable=False)
    role_attribute_mapping = Column(JSON, default=dict, nullable=False)
    
    # Settings
    auto_provision_users = Column(Boolean, default=True, nullable=False)
    require_verified_email = Column(Boolean, default=True, nullable=False)
    allowed_domains = Column(ARRAY(String), default=list, nullable=False)
    default_role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="identity_providers")
    default_role = relationship("Role", foreign_keys=[default_role_id])
    
    def __repr__(self):
        return f"<TenantIdentityProvider(tenant='{self.tenant_id}', provider='{self.provider}')>"