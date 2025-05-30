# ================================
# AUDIT & MONITORING MODELS (models/audit.py)
# ================================

from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, INET
from app.models.base import Base
from datetime import datetime

class AuditLog(Base):
    """Audit Log für alle wichtigen Aktionen"""
    __tablename__ = "audit_logs"
    
    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    impersonating_super_admin_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Action Information
    action = Column(String(100), nullable=False)  # 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', etc.
    resource_type = Column(String(100), nullable=True)  # 'user', 'project', 'document'
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Change Details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", foreign_keys=[user_id], back_populates="audit_logs")
    impersonating_admin = relationship("User", foreign_keys=[impersonating_super_admin_id])
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user='{self.user_id}', tenant='{self.tenant_id}')>"

class SuperAdminSession(Base):
    """Super Admin Session Tracking für Impersonation"""
    __tablename__ = "super_admin_sessions"
    
    # Foreign Keys
    super_admin_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    impersonated_tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Session Information
    session_token = Column(String(255), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    super_admin = relationship("User", foreign_keys=[super_admin_id])
    impersonated_tenant = relationship("Tenant", foreign_keys=[impersonated_tenant_id])
    
    def __repr__(self):
        return f"<SuperAdminSession(admin='{self.super_admin_id}', tenant='{self.impersonated_tenant_id}')>"