# ================================
# USER MODELS (models/user.py)
# ================================

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from app.models.base import Base
from datetime import datetime, timezone

class User(Base):
    """User Model"""
    __tablename__ = "users"
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)  # NULL für Super-Admins
    
    # Authentication
    auth_method = Column(String(20), default="local", nullable=False)  # 'local', 'microsoft', 'google'
    is_super_admin = Column(Boolean, default=False, nullable=False)
    
    # Local Authentication
    password_hash = Column(String(255), nullable=True)
    password_salt = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # OAuth Authentication
    oauth_provider_id = Column(String(255), nullable=True)  # Provider-specific user ID
    
    # Profile Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # User Settings (JSON)
    settings = Column(JSONB, default={}, nullable=False)
    
    # Provision percentage (0-100)
    provision_percentage = Column(Integer, default=0, nullable=False)
    
    # Property access control
    can_see_all_properties = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")
    filter_preferences = relationship("UserFilterPreference", foreign_keys="UserFilterPreference.user_id", back_populates="user", cascade="all, delete-orphan")
    oauth_tokens = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    # Audit trails
    created_properties = relationship("Property", foreign_keys="Property.created_by", back_populates="creator")
    updated_properties = relationship("Property", foreign_keys="Property.updated_by", back_populates="updater")
    created_expose_links = relationship("ExposeLink", foreign_keys="ExposeLink.created_by", back_populates="creator")
    created_reservations = relationship("Reservation", foreign_keys="Reservation.user_id", back_populates="user")
    audit_logs = relationship("AuditLog", foreign_keys="AuditLog.user_id", back_populates="user")
    
    # Property assignments
    property_assignments = relationship("PropertyAssignment", foreign_keys="PropertyAssignment.user_id", back_populates="user", cascade="all, delete-orphan")
    
    # Team relationships
    managed_team_members = relationship(
        "UserTeamAssignment", 
        foreign_keys="UserTeamAssignment.manager_id", 
        back_populates="manager",
        cascade="all, delete-orphan"
    )
    team_managers = relationship(
        "UserTeamAssignment", 
        foreign_keys="UserTeamAssignment.member_id", 
        back_populates="member",
        cascade="all, delete-orphan"
    )
    user_requests_created = relationship(
        "UserRequest",
        foreign_keys="UserRequest.requested_by",
        back_populates="requested_by_user",
        cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Full name property"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        return self.locked_until and self.locked_until > datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<User(email='{self.email}', tenant='{self.tenant_id}')>"

class UserSession(Base):
    """User Session Management"""
    __tablename__ = "user_sessions"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Session Information
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Session Context
    ip_address = Column(INET, nullable=True)  # IPv4/IPv6 support
    user_agent = Column(Text, nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Super-Admin Impersonation
    impersonated_tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=True)
    original_session_id = Column(UUID(as_uuid=True), ForeignKey('user_sessions.id'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    impersonated_tenant = relationship("Tenant", foreign_keys=[impersonated_tenant_id])
    original_session = relationship("UserSession", remote_side="UserSession.id")
    
    def __repr__(self):
        return f"<UserSession(user='{self.user_id}', expires='{self.expires_at}')>"

class OAuthToken(Base):
    """OAuth Token Storage"""
    __tablename__ = "oauth_tokens"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Token Information
    provider = Column(String(50), nullable=False)  # 'microsoft', 'google'
    access_token_hash = Column(String(255), nullable=True)  # Hashed for security
    refresh_token_hash = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="oauth_tokens")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    
    def __repr__(self):
        return f"<OAuthToken(user='{self.user_id}', provider='{self.provider}')>"

class PasswordResetToken(Base):
    """Password Reset Token Management"""
    __tablename__ = "password_reset_tokens"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Token Information
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")
    
    def __repr__(self):
        return f"<PasswordResetToken(user='{self.user_id}', expires='{self.expires_at}')>"