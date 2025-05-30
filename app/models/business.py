# ================================
# BUSINESS LOGIC MODELS (models/business.py)
# ================================

from sqlalchemy import Column, String, Text, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TenantMixin, AuditMixin

class Project(Base, TenantMixin, AuditMixin):
    """Project Model (Beispiel für Business Logic)"""
    __tablename__ = "projects"
    
    # Project Information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # 'active', 'completed', 'archived'
    
    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    creator = relationship("User", foreign_keys=[AuditMixin.created_by], back_populates="created_projects")
    updater = relationship("User", foreign_keys=[AuditMixin.updated_by], back_populates="updated_projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(name='{self.name}', tenant='{self.tenant_id}')>"

class Document(Base, TenantMixin, AuditMixin):
    """Document Model (Beispiel für Business Logic)"""
    __tablename__ = "documents"
    
    # Foreign Keys
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    
    # Document Information
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    
    # File Information
    file_path = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[TenantMixin.tenant_id])
    project = relationship("Project", back_populates="documents")
    creator = relationship("User", foreign_keys=[AuditMixin.created_by], back_populates="created_documents")
    updater = relationship("User", foreign_keys=[AuditMixin.updated_by])
    
    def __repr__(self):
        return f"<Document(title='{self.title}', project='{self.project_id}')>"