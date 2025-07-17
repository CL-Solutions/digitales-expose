from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_active_user, get_current_tenant_id, require_permission
from app.models.user import User
from app.models.business import DocumentType, ProjectDocument
from app.schemas.document import (
    ProjectDocumentResponse, 
    PropertyDocumentResponse,
    ProjectDocumentListResponse,
    PropertyDocumentListResponse,
    DocumentUploadResponse
)
from app.services.document_service import DocumentService
from app.mappers.document_mapper import map_document_to_response

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

# Project Document Endpoints

@router.post("/projects/{project_id}/upload", response_model=DocumentUploadResponse)
async def upload_project_document(
    project_id: UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "upload"))
):
    """Upload a document for a project"""
    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: PDF, PNG, JPG"
        )
    
    # Max file size: 50MB
    max_size = 50 * 1024 * 1024
    if file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of 50MB"
        )
    
    try:
        document = await DocumentService.upload_project_document(
            db=db,
            project_id=project_id,
            document_type=document_type,
            file=file,
            title=title,
            description=description,
            display_order=display_order,
            uploaded_by=current_user.id,
            tenant_id=tenant_id
        )
        
        return DocumentUploadResponse(
            document=map_document_to_response(document),
            message="Document uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectDocumentListResponse)
async def list_project_documents(
    project_id: UUID,
    document_type: Optional[DocumentType] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "read"))
):
    """List all documents for a project"""
    documents = DocumentService.list_project_documents(
        db=db,
        project_id=project_id,
        tenant_id=tenant_id,
        document_type=document_type
    )
    
    return ProjectDocumentListResponse(
        items=[map_document_to_response(doc) for doc in documents],
        total=len(documents)
    )


@router.delete("/projects/{document_id}", response_model=dict)
async def delete_project_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "delete"))
):
    """Delete a project document"""
    try:
        await DocumentService.delete_project_document(
            db=db,
            document_id=document_id,
            tenant_id=tenant_id,
            deleted_by=current_user.id
        )
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# Property Document Endpoints

@router.post("/properties/{property_id}/upload", response_model=DocumentUploadResponse)
async def upload_property_document(
    property_id: UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "upload"))
):
    """Upload a document for a property"""
    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: PDF, PNG, JPG"
        )
    
    # Max file size: 50MB
    max_size = 50 * 1024 * 1024
    if file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of 50MB"
        )
    
    try:
        document = await DocumentService.upload_property_document(
            db=db,
            property_id=property_id,
            document_type=document_type,
            file=file,
            title=title,
            description=description,
            display_order=display_order,
            uploaded_by=current_user.id,
            tenant_id=tenant_id
        )
        
        return DocumentUploadResponse(
            document=map_document_to_response(document),
            message="Document uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/properties/{property_id}", response_model=PropertyDocumentListResponse)
async def list_property_documents(
    property_id: UUID,
    document_type: Optional[DocumentType] = Query(None),
    include_project_documents: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "read"))
):
    """List all documents for a property, optionally including inherited project documents"""
    documents = DocumentService.list_property_documents(
        db=db,
        property_id=property_id,
        tenant_id=tenant_id,
        document_type=document_type,
        include_project_documents=include_project_documents
    )
    
    # Map documents to response schemas
    response_items = []
    for doc in documents:
        mapped_doc = map_document_to_response(doc)
        # Check if this is a project document (inherited)
        if isinstance(doc, ProjectDocument):
            # Create a PropertyDocumentResponse with is_inherited flag
            response_item = PropertyDocumentResponse(
                id=mapped_doc.id,
                document_type=mapped_doc.document_type,
                title=mapped_doc.title,
                description=mapped_doc.description,
                display_order=mapped_doc.display_order,
                file_name=mapped_doc.file_name,
                file_path=mapped_doc.file_path,
                file_size=mapped_doc.file_size,
                mime_type=mapped_doc.mime_type,
                s3_key=mapped_doc.s3_key,
                s3_bucket=mapped_doc.s3_bucket,
                uploaded_by=mapped_doc.uploaded_by,
                uploaded_at=mapped_doc.uploaded_at,
                created_at=mapped_doc.created_at,
                updated_at=mapped_doc.updated_at,
                property_id=property_id,  # Associate with the property
                is_inherited=True
            )
            response_items.append(response_item)
        else:
            # Regular property document
            response_items.append(mapped_doc)
    
    return PropertyDocumentListResponse(
        items=response_items,
        total=len(response_items)
    )


@router.delete("/properties/{document_id}", response_model=dict)
async def delete_property_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "delete"))
):
    """Delete a property document"""
    try:
        await DocumentService.delete_property_document(
            db=db,
            document_id=document_id,
            tenant_id=tenant_id,
            deleted_by=current_user.id
        )
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# Tenant-wide Document Endpoints

@router.get("/tenant/all", response_model=List[dict])
async def list_all_tenant_documents(
    document_type: Optional[DocumentType] = Query(None),
    include_property_documents: bool = Query(True),
    include_project_documents: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("documents", "read"))
):
    """
    List all documents for the current tenant.
    
    Returns document metadata including:
    - Document type (expose, floor_plan, etc.)
    - Access URL (presigned S3 URL for secure access)
    - Associated project or property ID
    - File metadata (name, size, mime type)
    """
    documents = DocumentService.list_tenant_documents(
        db=db,
        tenant_id=tenant_id,
        document_type=document_type,
        include_property_documents=include_property_documents,
        include_project_documents=include_project_documents
    )
    
    return documents