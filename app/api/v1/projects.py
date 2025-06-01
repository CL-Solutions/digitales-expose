# ================================
# PROJECTS & BUSINESS LOGIC API ROUTES (api/v1/projects.py) - COMPLETED USING SERVICES
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.orm import Session
from app.dependencies import (
    get_db, get_current_user, require_permission, 
    require_tenant_access, require_own_resource_or_permission
)
from app.schemas.business import (
    ProjectCreate, ProjectUpdate, ProjectResponse, 
    ProjectDetailResponse, ProjectListResponse, ProjectFilterParams,
    ProjectStatsResponse, DocumentCreate, DocumentUpdate,
    DocumentResponse, DocumentDetailResponse, DocumentListResponse,
    DocumentFilterParams, DocumentUploadRequest, DocumentUploadResponse,
    ActivityFeedResponse, SearchRequest, SearchResponse, ActivityResponse
)
from app.schemas.base import SuccessResponse
from app.services.business_service import ProjectService, DocumentService, BusinessSearchService
from app.models.user import User
from app.core.exceptions import AppException
from app.config import settings
from typing import List, Optional
import uuid

router = APIRouter()

# ================================
# PROJECT MANAGEMENT
# ================================

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "create")),
    __: bool = Depends(require_tenant_access())
):
    """Create new project - Uses ProjectService"""
    try:
        project = ProjectService.create_project(db, project_data, current_user)
        db.commit()
        
        project_response = ProjectResponse.model_validate(project)
        project_response.document_count = 0  # New project has no documents
        
        return project_response
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Project update failed")

@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_own_resource_or_permission("projects", "delete"))
):
    """Delete project - Uses ProjectService"""
    try:
        result = ProjectService.delete_project(db, project_id, current_user)
        db.commit()
        
        return SuccessResponse(
            message="Project deleted successfully",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Project deletion failed")

# ================================
# DOCUMENT MANAGEMENT
# ================================

@router.post("/{project_id}/documents", response_model=DocumentResponse)
async def create_document(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    document_data: DocumentCreate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("documents", "create")),
    __: bool = Depends(require_tenant_access())
):
    """Create new document in project - Uses DocumentService"""
    try:
        document = DocumentService.create_document(db, project_id, document_data, current_user)
        db.commit()
        return DocumentResponse.model_validate(document)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create document")

@router.get("/documents", response_model=DocumentListResponse)
async def list_all_documents(
    filter_params: DocumentFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("documents", "read")),
    __: bool = Depends(require_tenant_access())
):
    """List all documents in tenant - Uses DocumentService"""
    try:
        documents, total = DocumentService.list_documents(db, current_user.tenant_id, filter_params)
        
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")

@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_by_id(
    document_id: uuid.UUID = Path(..., description="Document ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("documents", "read")),
    __: bool = Depends(require_tenant_access())
):
    """Get specific document - Uses DocumentService"""
    try:
        document = DocumentService.get_document_by_id(db, document_id, current_user.tenant_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Build detailed response
        document_detail = DocumentDetailResponse.model_validate(document)
        document_detail.creator_name = document.creator.full_name if document.creator else None
        document_detail.updater_name = document.updater.full_name if document.updater else None
        document_detail.project_name = document.project.name if document.project else None
        
        # Generate download URL if file exists
        if document.file_path:
            document_detail.download_url = f"/api/v1/files/download/{document.id}"
            document_detail.preview_url = f"/api/v1/files/preview/{document.id}"
        
        return document_detail
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get document")

@router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID = Path(..., description="Document ID"),
    document_update: DocumentUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_own_resource_or_permission("documents", "update"))
):
    """Update document - Uses DocumentService"""
    try:
        document = DocumentService.update_document(db, document_id, document_update, current_user)
        db.commit()
        return DocumentResponse.model_validate(document)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Document update failed")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID = Path(..., description="Document ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_own_resource_or_permission("documents", "delete"))
):
    """Delete document - Uses DocumentService"""
    try:
        result = DocumentService.delete_document(db, document_id, current_user)
        db.commit()
        
        return SuccessResponse(message="Document deleted successfully")
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Document deletion failed")

# ================================
# FILE UPLOAD & MANAGEMENT
# ================================

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    upload_data: DocumentUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("documents", "create")),
    __: bool = Depends(require_tenant_access())
):
    """Initiate document upload (Pre-signed URL)"""
    try:
        # Verify project if specified
        if upload_data.project_id:
            project = ProjectService.get_project_by_id(db, upload_data.project_id, current_user.tenant_id)
            if not project:
                raise HTTPException(status_code=400, detail="Invalid project ID")
        
        # Check for existing document if replace_existing is False
        if not upload_data.replace_existing:
            from app.models.business import Document
            existing = db.query(Document).filter(
                Document.title == upload_data.title,
                Document.tenant_id == current_user.tenant_id,
                Document.project_id == upload_data.project_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Document with this title already exists")
        
        # Generate upload URL (would implement file service)
        document_id = uuid.uuid4()
        upload_url = f"https://your-storage-bucket.s3.amazonaws.com/documents/{document_id}"
        
        # Create document record
        from app.models.business import Document
        document = Document(
            id=document_id,
            tenant_id=current_user.tenant_id,
            project_id=upload_data.project_id,
            title=upload_data.title,
            created_by=current_user.id,
            file_path=f"documents/{document_id}"
        )
        
        db.add(document)
        db.commit()
        
        return DocumentUploadResponse(
            document_id=document_id,
            upload_url=upload_url,
            fields={
                "key": f"documents/{document_id}",
                "Content-Type": "application/octet-stream"
            },
            expires_at="2024-01-01T12:00:00Z"  # Would be actual expiration
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to initiate upload")

@router.post("/documents/{document_id}/upload-complete")
async def complete_document_upload(
    document_id: uuid.UUID = Path(..., description="Document ID"),
    file_size: int = Query(..., description="Uploaded file size"),
    mime_type: str = Query(..., description="File MIME type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete document upload after file is uploaded"""
    try:
        document = DocumentService.get_document_by_id(db, document_id, current_user.tenant_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update document with file info
        document.file_size = file_size
        document.mime_type = mime_type
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_business_event(
            db, "DOCUMENT_UPLOADED", current_user.id, current_user.tenant_id,
            "document", document.id,
            new_values={
                "file_size": file_size,
                "mime_type": mime_type
            }
        )
        
        db.commit()
        return SuccessResponse(message="Upload completed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to complete upload")

# ================================
# STATISTICS
# ================================

@router.get("/stats", response_model=ProjectStatsResponse)
async def get_project_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read"))
):
    """Project statistics for current tenant - Uses ProjectService"""
    try:
        stats = ProjectService.get_project_statistics(db, current_user.tenant_id)
        
        return ProjectStatsResponse(
            total_projects=stats["total_projects"],
            active_projects=stats["active_projects"],
            completed_projects=stats["completed_projects"],
            archived_projects=stats["archived_projects"],
            projects_by_month=stats["projects_by_month"],
            average_documents_per_project=stats["average_documents_per_project"],
            most_active_projects=[]  # Would implement most active projects query
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get project statistics")

# ================================
# SEARCH & ACTIVITY
# ================================

@router.get("/activity", response_model=ActivityFeedResponse)
async def get_project_activity(
    limit: int = Query(default=50, ge=1, le=100),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read"))
):
    """Activity feed for projects and documents - Uses BusinessSearchService"""
    try:
        activities = BusinessSearchService.get_activity_feed(
            db, current_user.tenant_id, limit, project_id
        )
        
        activity_responses = []
        for activity in activities:
            activity_responses.append(ActivityResponse(**activity))
        
        return ActivityFeedResponse(
            activities=activity_responses,
            total=len(activity_responses),
            has_more=len(activity_responses) == limit
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get activity feed")

@router.post("/search", response_model=SearchResponse)
async def search_projects_and_documents(
    search_data: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_tenant_access())
):
    """Search in projects and documents - Uses BusinessSearchService"""
    try:
        search_results = BusinessSearchService.search_projects_and_documents(
            db, current_user.tenant_id, search_data
        )
        
        return SearchResponse(**search_results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Search failed")

# ================================
# DOCUMENT SHARING & COLLABORATION
# ================================

@router.post("/documents/{document_id}/share")
async def share_document(
    document_id: uuid.UUID = Path(..., description="Document ID"),
    share_with_emails: List[str] = Query(..., description="Emails to share with"),
    permission_level: str = Query(default="read", description="Permission level: read, write"),
    message: Optional[str] = Query(None, description="Optional message"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("documents", "update"))
):
    """Share document with other users - Uses DocumentService"""
    try:
        result = DocumentService.share_document(
            db, document_id, share_with_emails, permission_level, current_user
        )
        
        # Send sharing notifications
        from app.utils.email import email_service
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        document = DocumentService.get_document_by_id(db, document_id, current_user.tenant_id)
        
        for email in result["shared_with"]:
            await email_service.send_email(
                to_emails=[email],
                subject=f"Document shared: {document.title}",
                template_name="document_shared",
                template_data={
                    "document_title": document.title,
                    "shared_by": current_user.full_name,
                    "permission_level": permission_level,
                    "message": message,
                    "document_url": f"{settings.FRONTEND_URL}/documents/{document.id}",
                    "tenant_name": tenant.name if tenant else "Your Organization"
                }
            )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Document shared with {len(result['shared_with'])} users",
            data=result
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to share document")

# ================================
# PROJECT EXPORT & BACKUP
# ================================

@router.post("/{project_id}/export")
async def export_project(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    format: str = Query(default="json", description="Export format: json, zip"),
    include_documents: bool = Query(default=True, description="Include document content"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read")),
    __: bool = Depends(require_tenant_access())
):
    """Export project with all documents - Uses ProjectService"""
    try:
        export_data = ProjectService.export_project(
            db, project_id, current_user.tenant_id, include_documents
        )
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_business_event(
            db, "PROJECT_EXPORTED", current_user.id, current_user.tenant_id,
            "project", project_id,
            new_values={
                "format": format,
                "include_documents": include_documents,
                "document_count": len(export_data["documents"])
            }
        )
        
        db.commit()
        
        if format == "json":
            from fastapi.responses import JSONResponse
            return JSONResponse(content=export_data)
        else:
            # Would implement ZIP export
            return SuccessResponse(
                message="Export initiated",
                data={"download_url": f"/api/v1/exports/project-{project_id}.zip"}
            )
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Export failed")
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create project")

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    filter_params: ProjectFilterParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read")),
    __: bool = Depends(require_tenant_access())
):
    """List all projects in tenant - Uses ProjectService"""
    try:
        projects, total = ProjectService.list_projects(db, current_user.tenant_id, filter_params)
        
        # Add document count to each project
        project_responses = []
        for project in projects:
            project_response = ProjectResponse.model_validate(project)
            project_response.document_count = len(project.documents)
            project_responses.append(project_response)
        
        return ProjectListResponse(
            projects=project_responses,
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_by_id(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read")),
    __: bool = Depends(require_tenant_access())
):
    """Get specific project - Uses ProjectService"""
    try:
        project = ProjectService.get_project_by_id(db, project_id, current_user.tenant_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build detailed response
        project_detail = ProjectDetailResponse.model_validate(project)
        project_detail.creator_name = project.creator.full_name if project.creator else None
        project_detail.updater_name = project.updater.full_name if project.updater else None
        project_detail.document_count = len(project.documents)
        
        # Add recent documents
        from sqlalchemy import desc
        recent_documents = db.query(DocumentService.get_document_by_id.__annotations__['return'].__args__[0]).filter(
            db.query(DocumentService.get_document_by_id.__annotations__['return'].__args__[0]).project_id == project_id
        ).order_by(desc(db.query(DocumentService.get_document_by_id.__annotations__['return'].__args__[0]).updated_at)).limit(5).all()
        
        # Fix: Get recent documents properly
        from app.models.business import Document
        recent_documents = db.query(Document).filter(
            Document.project_id == project_id
        ).order_by(desc(Document.updated_at)).limit(5).all()
        
        project_detail.documents = [DocumentResponse.model_validate(doc) for doc in recent_documents]
        
        return project_detail
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get project")

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    project_update: ProjectUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_own_resource_or_permission("projects", "update"))
):
    """Update project - Uses ProjectService"""
    try:
        project = ProjectService.update_project(db, project_id, project_update, current_user)
        db.commit()
        
        project_response = ProjectResponse.model_validate(project)
        project_response.document_count = len(project.documents)
        
        return project_response
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Project update failed")