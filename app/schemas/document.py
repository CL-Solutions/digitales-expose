from typing import Optional, List
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema, BaseResponseSchema, TimestampMixin
from app.models.business import DocumentType
import uuid


class DocumentBase(BaseSchema):
    """Base schema for documents"""
    document_type: DocumentType
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0, ge=0)


class ProjectDocumentCreate(DocumentBase):
    """Schema for creating project documents"""
    pass


class PropertyDocumentCreate(DocumentBase):
    """Schema for creating property documents"""
    pass


class DocumentResponse(DocumentBase, BaseResponseSchema, TimestampMixin):
    """Response schema for documents"""
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    s3_key: str
    s3_bucket: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime


class ProjectDocumentResponse(DocumentResponse):
    """Response schema for project documents"""
    project_id: uuid.UUID


class PropertyDocumentResponse(DocumentResponse):
    """Response schema for property documents"""
    property_id: uuid.UUID
    is_inherited: Optional[bool] = False  # True if document is inherited from project


class ProjectDocumentListResponse(BaseSchema):
    """Response schema for listing project documents"""
    items: List[ProjectDocumentResponse]
    total: int


class PropertyDocumentListResponse(BaseSchema):
    """Response schema for listing property documents"""
    items: List[PropertyDocumentResponse]
    total: int


class DocumentUploadResponse(BaseSchema):
    """Response schema for document upload"""
    document: DocumentResponse
    message: str = "Document uploaded successfully"