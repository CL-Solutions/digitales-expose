# ================================
# BASE MODEL (models/base.py)
# ================================

from sqlalchemy import Column, DateTime, func, ForeignKey
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.dialects.postgresql import UUID
import uuid

@as_declarative()
class Base:
    """Base Model mit gemeinsamen Feldern und Funktionalität"""
    
    # Automatische Tabellennamen basierend auf Klassennamen
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"
    
    # Gemeinsame Spalten
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class TenantMixin:
    """Mixin für Tenant-isolierte Tabellen"""
    
    @declared_attr
    def tenant_id(cls):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        return Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)

class AuditMixin:
    """Mixin für Audit-Felder (created_by, updated_by)"""
    
    @declared_attr
    def created_by(cls):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        return Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    @declared_attr
    def updated_by(cls):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        return Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

class SoftDeleteMixin:
    """Mixin für Soft Delete Funktionalität"""
    
    @declared_attr
    def is_deleted(cls):
        from sqlalchemy import Column, Boolean
        return Column(Boolean, default=False, nullable=False)
    
    @declared_attr
    def deleted_at(cls):
        from sqlalchemy import Column, DateTime
        return Column(DateTime(timezone=True), nullable=True)
    
    @declared_attr
    def deleted_by(cls):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import UUID
        return Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)