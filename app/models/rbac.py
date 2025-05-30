# ================================
# RBAC MODELS (models/rbac.py)
# ================================

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
from datetime import datetime

class Permission(Base):
    """Permission Model"""
    __tablename__ = "permissions"
    
    # Permission Definition
    resource = Column(String(100), nullable=False)  # 'users', 'projects', 'documents'
    action = Column(String(50), nullable=False)     # 'create', 'read', 'update', 'delete'
    description = Column(Text, nullable=True)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )
    
    @property
    def name(self) -> str:
        """Permission name as resource:action"""
        return f"{self.resource}:{self.action}"
    
    def __repr__(self):
        return f"<Permission(resource='{self.resource}', action='{self.action}')>"

class Role(Base):
    """Role Model"""
    __tablename__ = "roles"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)  # NULL für System-Rollen
    
    # Role Definition
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)  # System-definierte Rollen
    
    # Relationships
    tenant = relationship("Tenant", back_populates="roles")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_role_tenant_name'),
    )
    
    def __repr__(self):
        return f"<Role(name='{self.name}', tenant='{self.tenant_id}')>"

class RolePermission(Base):
    """Role-Permission Association"""
    __tablename__ = "role_permissions"
    
    # Foreign Keys
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    
    def __repr__(self):
        return f"<RolePermission(role='{self.role_id}', permission='{self.permission_id}')>"

class UserRole(Base):
    """User-Role Association"""
    __tablename__ = "user_roles"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Assignment Information
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Für temporäre Rollen
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    granter = relationship("User", foreign_keys=[granted_by])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'tenant_id', name='uq_user_role_tenant'),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if role assignment is expired"""
        return self.expires_at and self.expires_at < datetime.utcnow()
    
    def __repr__(self):
        return f"<UserRole(user='{self.user_id}', role='{self.role_id}', tenant='{self.tenant_id}')>"