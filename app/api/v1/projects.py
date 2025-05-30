# ================================
# PROJECTS & BUSINESS LOGIC API ROUTES (api/v1/projects.py) - COMPLETED
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
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
    ActivityFeedResponse, SearchRequest, SearchResponse
)
from app.schemas.base import SuccessResponse
from app.models.business import Project, Document
from app.models.user import User
from app.models.tenant import Tenant
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
    """Neues Projekt erstellen"""
    try:
        project = Project(
            tenant_id=current_user.tenant_id,
            name=project_data.name,
            description=project_data.description,
            status=project_data.status,
            created_by=current_user.id
        )
        
        db.add(project)
        db.flush()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PROJECT_CREATED", current_user.id, current_user.tenant_id,
            {
                "project_id": str(project.id),
                "project_name": project.name
            }
        )
        
        db.commit()
        return ProjectResponse.model_validate(project)
    
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
    """Liste aller Projekte im Tenant"""
    try:
        # Base query für Tenant
        query = db.query(Project).filter(Project.tenant_id == current_user.tenant_id)
        
        # Apply filters
        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            query = query.filter(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        
        if filter_params.status:
            query = query.filter(Project.status == filter_params.status)
        
        if filter_params.created_by:
            query = query.filter(Project.created_by == filter_params.created_by)
        
        if filter_params.has_documents is not None:
            if filter_params.has_documents:
                query = query.filter(Project.documents.any())
            else:
                query = query.filter(~Project.documents.any())
        
        if filter_params.created_after:
            from datetime import datetime
            query = query.filter(Project.created_at >= datetime.fromisoformat(filter_params.created_after))
        
        if filter_params.created_before:
            from datetime import datetime
            query = query.filter(Project.created_at <= datetime.fromisoformat(filter_params.created_before))
        
        # Count total
        total = query.count()
        
        # Apply sorting
        if filter_params.sort_by == "name":
            sort_field = Project.name
        elif filter_params.sort_by == "status":
            sort_field = Project.status
        else:
            sort_field = Project.created_at
        
        if filter_params.sort_order == "desc":
            sort_field = sort_field.desc()
        
        query = query.order_by(sort_field)
        
        # Apply pagination
        offset = (filter_params.page - 1) * filter_params.page_size
        projects = query.offset(offset).limit(filter_params.page_size).all()
        
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
    """Spezifisches Projekt abrufen"""
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build detailed response
        project_detail = ProjectDetailResponse.model_validate(project)
        project_detail.creator_name = project.creator.full_name if project.creator else None
        project_detail.updater_name = project.updater.full_name if project.updater else None
        project_detail.document_count = len(project.documents)
        
        # Add recent documents
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
    """Projekt aktualisieren"""
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Store old values for audit
        old_values = {
            "name": project.name,
            "description": project.description,
            "status": project.status
        }
        
        # Update fields
        update_data = {}
        if project_update.name is not None:
            project.name = project_update.name
            update_data["name"] = project_update.name
        if project_update.description is not None:
            project.description = project_update.description
            update_data["description"] = project_update.description
        if project_update.status is not None:
            project.status = project_update.status
            update_data["status"] = project_update.status
        
        project.updated_by = current_user.id
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PROJECT_UPDATED", current_user.id, current_user.tenant_id,
            {
                "project_id": str(project.id),
                "project_name": project.name,
                "old_values": old_values,
                "new_values": update_data
            }
        )
        
        db.commit()
        
        project_response = ProjectResponse.model_validate(project)
        project_response.document_count = len(project.documents)
        
        return project_response
    
    except HTTPException:
        raise
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
    """Projekt löschen"""
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Count documents for audit
        document_count = len(project.documents)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PROJECT_DELETED", current_user.id, current_user.tenant_id,
            {
                "project_id": str(project.id),
                "project_name": project.name,
                "document_count": document_count
            }
        )
        
        # Delete project (cascade will handle documents)
        db.delete(project)
        db.commit()
        
        return SuccessResponse(
            message="Project deleted successfully",
            data={"deleted_documents": document_count}
        )
    
    except HTTPException:
        raise
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
    """Neues Dokument in Projekt erstellen"""
    try:
        # Verify project exists and belongs to tenant
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        document = Document(
            tenant_id=current_user.tenant_id,
            project_id=project_id,
            title=document_data.title,
            content=document_data.content,
            created_by=current_user.id
        )
        
        db.add(document)
        db.flush()
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "DOCUMENT_CREATED", current_user.id, current_user.tenant_id,
            {
                "document_id": str(document.id),
                "document_title": document.title,
                "project_id": str(project_id)
            }
        )
        
        db.commit()
        return DocumentResponse.model_validate(document)
    
    except HTTPException:
        raise
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
    """Liste aller Dokumente im Tenant"""
    try:
        # Base query für Tenant
        query = db.query(Document).filter(Document.tenant_id == current_user.tenant_id)
        
        # Apply filters
        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_term),
                    Document.content.ilike(search_term)
                )
            )
        
        if filter_params.project_id:
            query = query.filter(Document.project_id == filter_params.project_id)
        
        if filter_params.created_by:
            query = query.filter(Document.created_by == filter_params.created_by)
        
        if filter_params.mime_type:
            query = query.filter(Document.mime_type == filter_params.mime_type)
        
        if filter_params.has_content is not None:
            if filter_params.has_content:
                query = query.filter(Document.content.isnot(None))
            else:
                query = query.filter(Document.content.is_(None))
        
        if filter_params.file_size_min:
            query = query.filter(Document.file_size >= filter_params.file_size_min)
        
        if filter_params.file_size_max:
            query = query.filter(Document.file_size <= filter_params.file_size_max)
        
        # Count total
        total = query.count()
        
        # Apply sorting
        if filter_params.sort_by == "title":
            sort_field = Document.title
        elif filter_params.sort_by == "size":
            sort_field = Document.file_size
        else:
            sort_field = Document.updated_at
        
        if filter_params.sort_order == "desc":
            sort_field = sort_field.desc()
        
        query = query.order_by(sort_field)
        
        # Apply pagination
        offset = (filter_params.page - 1) * filter_params.page_size
        documents = query.offset(offset).limit(filter_params.page_size).all()
        
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
    """Spezifisches Dokument abrufen"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Build detailed response
        document_detail = DocumentDetailResponse.model_validate(document)
        document_detail.creator_name = document.creator.full_name if document.creator else None
        document_detail.updater_name = document.updater.full_name if document.updater else None
        document_detail.project_name = document.project.name if document.project else None
        
        # Generate download URL if file exists
        if document.file_path:
            # Would implement file service for pre-signed URLs
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
    """Dokument aktualisieren"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Store old values for audit
        old_values = {
            "title": document.title,
            "content": document.content[:100] + "..." if document.content and len(document.content) > 100 else document.content,
            "project_id": str(document.project_id) if document.project_id else None
        }
        
        # Update fields
        update_data = {}
        if document_update.title is not None:
            document.title = document_update.title
            update_data["title"] = document_update.title
        if document_update.content is not None:
            document.content = document_update.content
            update_data["content_updated"] = True
        if document_update.project_id is not None:
            # Verify project belongs to same tenant
            if document_update.project_id:
                project = db.query(Project).filter(
                    Project.id == document_update.project_id,
                    Project.tenant_id == current_user.tenant_id
                ).first()
                if not project:
                    raise HTTPException(status_code=400, detail="Invalid project ID")
            document.project_id = document_update.project_id
            update_data["project_id"] = str(document_update.project_id) if document_update.project_id else None
        
        document.updated_by = current_user.id
        document.version += 1
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "DOCUMENT_UPDATED", current_user.id, current_user.tenant_id,
            {
                "document_id": str(document.id),
                "document_title": document.title,
                "version": document.version,
                "old_values": old_values,
                "new_values": update_data
            }
        )
        
        db.commit()
        return DocumentResponse.model_validate(document)
    
    except HTTPException:
        raise
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
    """Dokument löschen"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "DOCUMENT_DELETED", current_user.id, current_user.tenant_id,
            {
                "document_id": str(document.id),
                "document_title": document.title,
                "project_id": str(document.project_id) if document.project_id else None,
                "file_size": document.file_size
            }
        )
        
        # Delete document
        db.delete(document)
        db.commit()
        
        return SuccessResponse(message="Document deleted successfully")
    
    except HTTPException:
        raise
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
    """Initiiert Document Upload (Pre-signed URL)"""
    try:
        # Verify project if specified
        if upload_data.project_id:
            project = db.query(Project).filter(
                Project.id == upload_data.project_id,
                Project.tenant_id == current_user.tenant_id
            ).first()
            if not project:
                raise HTTPException(status_code=400, detail="Invalid project ID")
        
        # Check for existing document if replace_existing is False
        if not upload_data.replace_existing:
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
    """Completes document upload after file is uploaded"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update document with file info
        document.file_size = file_size
        document.mime_type = mime_type
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "DOCUMENT_UPLOADED", current_user.id, current_user.tenant_id,
            {
                "document_id": str(document.id),
                "document_title": document.title,
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
    """Activity Feed für Projekte und Dokumente"""
    try:
        from app.models.audit import AuditLog
        from sqlalchemy import and_
        
        # Get activity logs
        query = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == current_user.tenant_id,
                AuditLog.action.in_([
                    "PROJECT_CREATED", "PROJECT_UPDATED", "PROJECT_DELETED",
                    "DOCUMENT_CREATED", "DOCUMENT_UPDATED", "DOCUMENT_DELETED", "DOCUMENT_UPLOADED"
                ])
            )
        )
        
        if project_id:
            query = query.filter(
                or_(
                    AuditLog.resource_id == project_id,
                    AuditLog.new_values.contains({"project_id": str(project_id)})
                )
            )
        
        activities = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        activity_responses = []
        for activity in activities:
            # Map audit log to activity response
            activity_data = {
                "id": activity.id,
                "activity_type": activity.action,
                "resource_type": "project" if "PROJECT" in activity.action else "document",
                "resource_id": activity.resource_id or uuid.uuid4(),  # Fallback
                "description": f"{activity.action.replace('_', ' ').title()}",
                "user_id": activity.user_id,
                "user_name": "Unknown User",  # Would join with users table
                "tenant_id": activity.tenant_id,
                "metadata": activity.new_values or {},
                "created_at": activity.created_at,
                "updated_at": activity.created_at
            }
            
            from app.schemas.business import ActivityResponse
            activity_responses.append(ActivityResponse(**activity_data))
        
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
    """Suche in Projekten und Dokumenten"""
    try:
        import time
        start_time = time.time()
        
        results_by_type = {}
        total_results = 0
        
        # Search projects
        if "project" in search_data.resource_types:
            project_query = db.query(Project).filter(
                and_(
                    Project.tenant_id == current_user.tenant_id,
                    or_(
                        Project.name.ilike(f"%{search_data.query}%"),
                        Project.description.ilike(f"%{search_data.query}%")
                    )
                )
            ).limit(search_data.limit)
            
            projects = project_query.all()
            project_results = []
            
            for project in projects:
                project_results.append({
                    "id": project.id,
                    "type": "project",
                    "title": project.name,
                    "description": project.description,
                    "url": f"/projects/{project.id}",
                    "relevance_score": 1.0,  # Would implement proper scoring
                    "metadata": {
                        "status": project.status,
                        "created_at": project.created_at.isoformat(),
                        "document_count": len(project.documents)
                    }
                })
            
            results_by_type["project"] = project_results
            total_results += len(project_results)
        
        # Search documents
        if "document" in search_data.resource_types:
            document_query = db.query(Document).filter(
                and_(
                    Document.tenant_id == current_user.tenant_id,
                    or_(
                        Document.title.ilike(f"%{search_data.query}%"),
                        Document.content.ilike(f"%{search_data.query}%")
                    )
                )
            ).limit(search_data.limit)
            
            documents = document_query.all()
            document_results = []
            
            for document in documents:
                document_results.append({
                    "id": document.id,
                    "type": "document",
                    "title": document.title,
                    "description": document.content[:200] + "..." if document.content and len(document.content) > 200 else document.content,
                    "url": f"/documents/{document.id}",
                    "relevance_score": 1.0,  # Would implement proper scoring
                    "metadata": {
                        "project_id": str(document.project_id) if document.project_id else None,
                        "file_size": document.file_size,
                        "mime_type": document.mime_type,
                        "created_at": document.created_at.isoformat()
                    }
                })
            
            results_by_type["document"] = document_results
            total_results += len(document_results)
        
        search_time_ms = int((time.time() - start_time) * 1000)
        
        return SearchResponse(
            query=search_data.query,
            total_results=total_results,
            results_by_type=results_by_type,
            search_time_ms=search_time_ms,
            suggestions=[]  # Would implement search suggestions
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Search failed")

# ================================
# STATISTICS
# ================================

@router.get("/stats", response_model=ProjectStatsResponse)
async def get_project_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("projects", "read"))
):
    """Projekt-Statistiken für den aktuellen Tenant"""
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Basic counts
        total_projects = db.query(Project).filter(Project.tenant_id == current_user.tenant_id).count()
        active_projects = db.query(Project).filter(
            Project.tenant_id == current_user.tenant_id,
            Project.status == "active"
        ).count()
        completed_projects = db.query(Project).filter(
            Project.tenant_id == current_user.tenant_id,
            Project.status == "completed"
        ).count()
        archived_projects = db.query(Project).filter(
            Project.tenant_id == current_user.tenant_id,
            Project.status == "archived"
        ).count()
        
        # Projects by month (last 12 months)
        projects_by_month = {}
        for i in range(12):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end - timedelta(days=month_end.day)
            
            count = db.query(Project).filter(
                and_(
                    Project.tenant_id == current_user.tenant_id,
                    Project.created_at >= month_start,
                    Project.created_at <= month_end
                )
            ).count()
            
            projects_by_month[month_start.strftime("%Y-%m")] = count
        
        # Average documents per project
        total_documents = db.query(Document).filter(Document.tenant_id == current_user.tenant_id).count()
        avg_docs_per_project = total_documents / total_projects if total_projects > 0 else 0
        
        return ProjectStatsResponse(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            archived_projects=archived_projects,
            projects_by_month=projects_by_month,
            average_documents_per_project=round(avg_docs_per_project, 2),
            most_active_projects=[]  # Would implement most active projects query
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get project statistics")

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
    """Dokument mit anderen Usern teilen"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify users exist in same tenant
        valid_users = []
        for email in share_with_emails:
            user = db.query(User).filter(
                User.email == email,
                User.tenant_id == current_user.tenant_id,
                User.is_active == True
            ).first()
            if user:
                valid_users.append(user)
        
        if not valid_users:
            raise HTTPException(status_code=400, detail="No valid users found to share with")
        
        # Send sharing notifications (would implement email notifications)
        from app.utils.email import email_service
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        
        for user in valid_users:
            await email_service.send_email(
                to_emails=[user.email],
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
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "DOCUMENT_SHARED", current_user.id, current_user.tenant_id,
            {
                "document_id": str(document.id),
                "document_title": document.title,
                "shared_with": [user.email for user in valid_users],
                "permission_level": permission_level
            }
        )
        
        db.commit()
        
        return SuccessResponse(
            message=f"Document shared with {len(valid_users)} users",
            data={
                "shared_with": [user.email for user in valid_users],
                "permission_level": permission_level
            }
        )
    
    except HTTPException:
        raise
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
    """Project mit allen Dokumenten exportieren"""
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build export data
        export_data = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            },
            "documents": []
        }
        
        if include_documents:
            for document in project.documents:
                doc_data = {
                    "id": str(document.id),
                    "title": document.title,
                    "content": document.content,
                    "file_size": document.file_size,
                    "mime_type": document.mime_type,
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat()
                }
                export_data["documents"].append(doc_data)
        
        # Audit log
        from app.utils.audit import AuditLogger
        audit_logger = AuditLogger()
        audit_logger.log_auth_event(
            db, "PROJECT_EXPORTED", current_user.id, current_user.tenant_id,
            {
                "project_id": str(project.id),
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
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Export failed")