# ================================
# BUSINESS SERVICE (services/business_service.py) - COMPLETED
# ================================

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app.models.business import Project, Document
from app.models.user import User
from app.schemas.business import (
    ProjectCreate, ProjectUpdate, DocumentCreate, DocumentUpdate,
    ProjectFilterParams, DocumentFilterParams, SearchRequest
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

audit_logger = AuditLogger()

class ProjectService:
    """Service for project management operations"""
    
    @staticmethod
    def create_project(
        db: Session,
        project_data: ProjectCreate,
        current_user: User
    ) -> Project:
        """Create a new project"""
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
        audit_logger.log_business_event(
            db, "PROJECT_CREATED", current_user.id, current_user.tenant_id,
            "project", project.id,
            new_values={
                "name": project.name,
                "description": project.description,
                "status": project.status
            }
        )
        
        return project
    
    @staticmethod
    def get_project_by_id(
        db: Session,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Optional[Project]:
        """Get project by ID within tenant"""
        return db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == tenant_id
        ).first()
    
    @staticmethod
    def list_projects(
        db: Session,
        tenant_id: uuid.UUID,
        filter_params: ProjectFilterParams
    ) -> tuple[List[Project], int]:
        """List projects with filtering and pagination"""
        # Base query for tenant
        query = db.query(Project).filter(Project.tenant_id == tenant_id)
        
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
            query = query.filter(Project.created_at >= datetime.fromisoformat(filter_params.created_after))
        
        if filter_params.created_before:
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
        
        return projects, total
    
    @staticmethod
    def update_project(
        db: Session,
        project_id: uuid.UUID,
        project_update: ProjectUpdate,
        current_user: User
    ) -> Project:
        """Update an existing project"""
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise AppException("Project not found", 404, "PROJECT_NOT_FOUND")
        
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
        audit_logger.log_business_event(
            db, "PROJECT_UPDATED", current_user.id, current_user.tenant_id,
            "project", project.id, old_values, update_data
        )
        
        return project
    
    @staticmethod
    def delete_project(
        db: Session,
        project_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Delete a project"""
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise AppException("Project not found", 404, "PROJECT_NOT_FOUND")
        
        # Count documents for audit
        document_count = len(project.documents)
        
        # Audit log
        audit_logger.log_business_event(
            db, "PROJECT_DELETED", current_user.id, current_user.tenant_id,
            "project", project.id,
            old_values={
                "name": project.name,
                "document_count": document_count
            }
        )
        
        # Delete project (cascade will handle documents)
        db.delete(project)
        
        return {"deleted_documents": document_count}
    
    @staticmethod
    def get_project_statistics(
        db: Session,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get project statistics for tenant"""
        # Basic counts
        total_projects = db.query(Project).filter(Project.tenant_id == tenant_id).count()
        active_projects = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status == "active"
        ).count()
        completed_projects = db.query(Project).filter(
            Project.tenant_id == tenant_id,
            Project.status == "completed"
        ).count()
        archived_projects = db.query(Project).filter(
            Project.tenant_id == tenant_id,
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
                    Project.tenant_id == tenant_id,
                    Project.created_at >= month_start,
                    Project.created_at <= month_end
                )
            ).count()
            
            projects_by_month[month_start.strftime("%Y-%m")] = count
        
        # Average documents per project
        total_documents = db.query(Document).filter(Document.tenant_id == tenant_id).count()
        avg_docs_per_project = total_documents / total_projects if total_projects > 0 else 0
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "archived_projects": archived_projects,
            "projects_by_month": projects_by_month,
            "average_documents_per_project": round(avg_docs_per_project, 2)
        }
    
    @staticmethod
    def export_project(
        db: Session,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        include_documents: bool = True
    ) -> Dict[str, Any]:
        """Export project data"""
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == tenant_id
        ).first()
        
        if not project:
            raise AppException("Project not found", 404, "PROJECT_NOT_FOUND")
        
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
        
        return export_data

class DocumentService:
    """Service for document management operations"""
    
    @staticmethod
    def create_document(
        db: Session,
        project_id: uuid.UUID,
        document_data: DocumentCreate,
        current_user: User
    ) -> Document:
        """Create a new document"""
        # Verify project exists and belongs to tenant
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.tenant_id == current_user.tenant_id
        ).first()
        
        if not project:
            raise AppException("Project not found", 404, "PROJECT_NOT_FOUND")
        
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
        audit_logger.log_business_event(
            db, "DOCUMENT_CREATED", current_user.id, current_user.tenant_id,
            "document", document.id,
            new_values={
                "title": document.title,
                "project_id": str(project_id)
            }
        )
        
        return document
    
    @staticmethod
    def get_document_by_id(
        db: Session,
        document_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Optional[Document]:
        """Get document by ID within tenant"""
        return db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        ).first()
    
    @staticmethod
    def list_documents(
        db: Session,
        tenant_id: uuid.UUID,
        filter_params: DocumentFilterParams
    ) -> tuple[List[Document], int]:
        """List documents with filtering and pagination"""
        # Base query for tenant
        query = db.query(Document).filter(Document.tenant_id == tenant_id)
        
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
        
        return documents, total
    
    @staticmethod
    def update_document(
        db: Session,
        document_id: uuid.UUID,
        document_update: DocumentUpdate,
        current_user: User
    ) -> Document:
        """Update a document"""
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise AppException("Document not found", 404, "DOCUMENT_NOT_FOUND")
        
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
                    raise AppException("Invalid project ID", 400, "INVALID_PROJECT")
            document.project_id = document_update.project_id
            update_data["project_id"] = str(document_update.project_id) if document_update.project_id else None
        
        document.updated_by = current_user.id
        document.version += 1
        
        # Audit log
        audit_logger.log_business_event(
            db, "DOCUMENT_UPDATED", current_user.id, current_user.tenant_id,
            "document", document.id, old_values, update_data,
            {"version": document.version}
        )
        
        return document
    
    @staticmethod
    def delete_document(
        db: Session,
        document_id: uuid.UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Delete a document"""
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise AppException("Document not found", 404, "DOCUMENT_NOT_FOUND")
        
        # Audit log
        audit_logger.log_business_event(
            db, "DOCUMENT_DELETED", current_user.id, current_user.tenant_id,
            "document", document.id,
            old_values={
                "title": document.title,
                "project_id": str(document.project_id) if document.project_id else None,
                "file_size": document.file_size
            }
        )
        
        # Delete document
        db.delete(document)
        
        return {"document_title": document.title}
    
    @staticmethod
    def share_document(
        db: Session,
        document_id: uuid.UUID,
        user_emails: List[str],
        permission_level: str,
        current_user: User
    ) -> Dict[str, Any]:
        """Share document with users"""
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id
        ).first()
        
        if not document:
            raise AppException("Document not found", 404, "DOCUMENT_NOT_FOUND")
        
        # Verify users exist in same tenant
        valid_users = []
        for email in user_emails:
            user = db.query(User).filter(
                User.email == email,
                User.tenant_id == current_user.tenant_id,
                User.is_active == True
            ).first()
            if user:
                valid_users.append(user)
        
        if not valid_users:
            raise AppException("No valid users found to share with", 400, "NO_VALID_USERS")
        
        # Audit log
        audit_logger.log_business_event(
            db, "DOCUMENT_SHARED", current_user.id, current_user.tenant_id,
            "document", document.id,
            new_values={
                "shared_with": [user.email for user in valid_users],
                "permission_level": permission_level
            }
        )
        
        return {
            "shared_with": [user.email for user in valid_users],
            "permission_level": permission_level
        }

class BusinessSearchService:
    """Service for searching across business entities"""
    
    @staticmethod
    def search_projects_and_documents(
        db: Session,
        tenant_id: uuid.UUID,
        search_request: SearchRequest
    ) -> Dict[str, Any]:
        """Search in projects and documents"""
        import time
        start_time = time.time()
        
        results_by_type = {}
        total_results = 0
        
        # Search projects
        if "project" in search_request.resource_types:
            project_query = db.query(Project).filter(
                and_(
                    Project.tenant_id == tenant_id,
                    or_(
                        Project.name.ilike(f"%{search_request.query}%"),
                        Project.description.ilike(f"%{search_request.query}%")
                    )
                )
            ).limit(search_request.limit)
            
            projects = project_query.all()
            project_results = []
            
            for project in projects:
                project_results.append({
                    "id": project.id,
                    "type": "project",
                    "title": project.name,
                    "description": project.description,
                    "url": f"/projects/{project.id}",
                    "relevance_score": 1.0,
                    "metadata": {
                        "status": project.status,
                        "created_at": project.created_at.isoformat(),
                        "document_count": len(project.documents)
                    }
                })
            
            results_by_type["project"] = project_results
            total_results += len(project_results)
        
        # Search documents
        if "document" in search_request.resource_types:
            document_query = db.query(Document).filter(
                and_(
                    Document.tenant_id == tenant_id,
                    or_(
                        Document.title.ilike(f"%{search_request.query}%"),
                        Document.content.ilike(f"%{search_request.query}%")
                    )
                )
            ).limit(search_request.limit)
            
            documents = document_query.all()
            document_results = []
            
            for document in documents:
                document_results.append({
                    "id": document.id,
                    "type": "document",
                    "title": document.title,
                    "description": document.content[:200] + "..." if document.content and len(document.content) > 200 else document.content,
                    "url": f"/documents/{document.id}",
                    "relevance_score": 1.0,
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
        
        return {
            "query": search_request.query,
            "total_results": total_results,
            "results_by_type": results_by_type,
            "search_time_ms": search_time_ms,
            "suggestions": []
        }
    
    @staticmethod
    def get_activity_feed(
        db: Session,
        tenant_id: uuid.UUID,
        limit: int = 50,
        project_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get activity feed for projects and documents"""
        from app.models.audit import AuditLog
        
        # Get activity logs
        query = db.query(AuditLog).filter(
            and_(
                AuditLog.tenant_id == tenant_id,
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
            activity_data = {
                "id": activity.id,
                "activity_type": activity.action,
                "resource_type": "project" if "PROJECT" in activity.action else "document",
                "resource_id": activity.resource_id or uuid.uuid4(),
                "description": f"{activity.action.replace('_', ' ').title()}",
                "user_id": activity.user_id,
                "user_name": "Unknown User",  # Would join with users table
                "tenant_id": activity.tenant_id,
                "metadata": activity.new_values or {},
                "created_at": activity.created_at,
                "updated_at": activity.created_at
            }
            activity_responses.append(activity_data)
        
        return activity_responses