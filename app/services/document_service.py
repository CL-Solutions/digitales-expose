from typing import List, Optional, BinaryIO
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import UploadFile
import os
import io

from app.models.business import ProjectDocument, PropertyDocument, DocumentType, Project, Property
from app.services.s3_service import S3Service
from app.utils.audit import AuditLogger
from app.utils.pdf_optimizer import PDFOptimizer
from app.core.exceptions import AppException

audit_logger = AuditLogger()


class DocumentService:
    """Service for managing documents"""

    @staticmethod
    async def upload_project_document(
        db: Session,
        project_id: UUID,
        document_type: DocumentType,
        file: UploadFile,
        title: str,
        description: Optional[str],
        display_order: int,
        uploaded_by: UUID,
        tenant_id: UUID
    ) -> ProjectDocument:
        """Upload a document for a project"""
        # Verify project exists and belongs to tenant
        project = db.query(Project).filter(
            and_(Project.id == project_id, Project.tenant_id == tenant_id)
        ).first()
        if not project:
            raise AppException(f"Project {project_id} not found", status_code=404)

        # Check if file is PDF and needs optimization
        file_size = file.size
        
        # For PDFs, try to optimize first
        if file.content_type == 'application/pdf':
            try:
                # Read file content
                file_content = await file.read()
                file_buffer = io.BytesIO(file_content)
                
                # Optimize PDF
                optimized_file, new_size, was_optimized = await PDFOptimizer.optimize_pdf(
                    file_buffer, 
                    file.size
                )
                
                if was_optimized:
                    # Reset file position for upload
                    await file.seek(0)
                    # Create a new file-like object with optimized content
                    optimized_file.seek(0)
                    # Replace the file's internal file object
                    file.file = optimized_file
                    file_size = new_size
                else:
                    # Reset to beginning for upload
                    await file.seek(0)
            except Exception as e:
                # Log error but continue with original file
                print(f"PDF optimization failed: {str(e)}")
                await file.seek(0)

        # Upload file to S3
        s3_service = S3Service()
        folder = f"documents/projects/{project_id}/{document_type.value}"
        
        try:
            s3_result = await s3_service.upload_file(
                file=file,
                folder=folder,
                tenant_id=str(tenant_id),
                allowed_types=['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
            )
        except Exception as e:
            raise AppException(f"Failed to upload file: {str(e)}", status_code=400)

        # Create document record
        document = ProjectDocument(
            project_id=project_id,
            document_type=document_type,
            title=title,
            description=description,
            display_order=display_order,
            file_name=file.filename,
            file_path=s3_result["url"],
            file_size=file_size,  # Use optimized size if applicable
            mime_type=file.content_type,
            s3_key=s3_result["s3_key"],
            s3_bucket=s3_result["s3_bucket"],
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
            tenant_id=tenant_id
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # Log audit event
        audit_logger.log_business_event(
            db=db,
            action="PROJECT_DOCUMENT_UPLOADED",
            user_id=uploaded_by,
            tenant_id=tenant_id,
            resource_type="project_document",
            resource_id=document.id,
            new_values={
                "project_id": str(project_id),
                "document_type": document_type.value,
                "file_name": file.filename
            }
        )

        return document

    @staticmethod
    async def upload_property_document(
        db: Session,
        property_id: UUID,
        document_type: DocumentType,
        file: UploadFile,
        title: str,
        description: Optional[str],
        display_order: int,
        uploaded_by: UUID,
        tenant_id: UUID
    ) -> PropertyDocument:
        """Upload a document for a property"""
        # Verify property exists and belongs to tenant
        property_obj = db.query(Property).filter(
            and_(Property.id == property_id, Property.tenant_id == tenant_id)
        ).first()
        if not property_obj:
            raise AppException(f"Property {property_id} not found", status_code=404)

        # Check if file is PDF and needs optimization
        file_size = file.size
        
        # For PDFs, try to optimize first
        if file.content_type == 'application/pdf':
            try:
                # Read file content
                file_content = await file.read()
                file_buffer = io.BytesIO(file_content)
                
                # Optimize PDF
                optimized_file, new_size, was_optimized = await PDFOptimizer.optimize_pdf(
                    file_buffer, 
                    file.size
                )
                
                if was_optimized:
                    # Reset file position for upload
                    await file.seek(0)
                    # Create a new file-like object with optimized content
                    optimized_file.seek(0)
                    # Replace the file's internal file object
                    file.file = optimized_file
                    file_size = new_size
                else:
                    # Reset to beginning for upload
                    await file.seek(0)
            except Exception as e:
                # Log error but continue with original file
                print(f"PDF optimization failed: {str(e)}")
                await file.seek(0)

        # Upload file to S3
        s3_service = S3Service()
        folder = f"documents/properties/{property_id}/{document_type.value}"
        
        try:
            s3_result = await s3_service.upload_file(
                file=file,
                folder=folder,
                tenant_id=str(tenant_id),
                allowed_types=['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
            )
        except Exception as e:
            raise AppException(f"Failed to upload file: {str(e)}", status_code=400)

        # Create document record
        document = PropertyDocument(
            property_id=property_id,
            document_type=document_type,
            title=title,
            description=description,
            display_order=display_order,
            file_name=file.filename,
            file_path=s3_result["url"],
            file_size=file_size,  # Use optimized size if applicable
            mime_type=file.content_type,
            s3_key=s3_result["s3_key"],
            s3_bucket=s3_result["s3_bucket"],
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
            tenant_id=tenant_id
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # Log audit event
        audit_logger.log_business_event(
            db=db,
            action="PROPERTY_DOCUMENT_UPLOADED",
            user_id=uploaded_by,
            tenant_id=tenant_id,
            resource_type="property_document",
            resource_id=document.id,
            new_values={
                "property_id": str(property_id),
                "document_type": document_type.value,
                "file_name": file.filename
            }
        )

        return document

    @staticmethod
    def list_project_documents(
        db: Session,
        project_id: UUID,
        tenant_id: UUID,
        document_type: Optional[DocumentType] = None
    ) -> List[ProjectDocument]:
        """List all documents for a project"""
        query = db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.project_id == project_id,
                ProjectDocument.tenant_id == tenant_id
            )
        )

        if document_type:
            query = query.filter(ProjectDocument.document_type == document_type)

        return query.order_by(
            ProjectDocument.document_type,
            ProjectDocument.display_order,
            ProjectDocument.uploaded_at
        ).all()

    @staticmethod
    def list_property_documents(
        db: Session,
        property_id: UUID,
        tenant_id: UUID,
        document_type: Optional[DocumentType] = None,
        include_project_documents: bool = True
    ) -> List[PropertyDocument | ProjectDocument]:
        """List all documents for a property, optionally including inherited project documents"""
        # Get property documents
        query = db.query(PropertyDocument).filter(
            and_(
                PropertyDocument.property_id == property_id,
                PropertyDocument.tenant_id == tenant_id
            )
        )

        if document_type:
            query = query.filter(PropertyDocument.document_type == document_type)

        property_docs = query.all()

        # If including project documents, get them too
        if include_project_documents:
            property_obj = db.query(Property).filter(
                and_(Property.id == property_id, Property.tenant_id == tenant_id)
            ).first()
            
            if property_obj and property_obj.project_id:
                project_query = db.query(ProjectDocument).filter(
                    and_(
                        ProjectDocument.project_id == property_obj.project_id,
                        ProjectDocument.tenant_id == tenant_id
                    )
                )

                if document_type:
                    project_query = project_query.filter(ProjectDocument.document_type == document_type)

                project_docs = project_query.all()
                
                # Combine and sort all documents
                all_docs = property_docs + project_docs
                return sorted(
                    all_docs,
                    key=lambda d: (d.document_type.value, d.display_order, d.uploaded_at)
                )

        return sorted(
            property_docs,
            key=lambda d: (d.document_type.value, d.display_order, d.uploaded_at)
        )

    @staticmethod
    async def delete_project_document(
        db: Session,
        document_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID
    ) -> bool:
        """Delete a project document"""
        document = db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.id == document_id,
                ProjectDocument.tenant_id == tenant_id
            )
        ).first()

        if not document:
            raise AppException(f"Document {document_id} not found", status_code=404)

        # Delete from S3
        s3_service = S3Service()
        try:
            await s3_service.delete_file(document.s3_key)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Failed to delete file from S3: {str(e)}")

        # Log audit event before deletion
        audit_logger.log_business_event(
            db=db,
            action="PROJECT_DOCUMENT_DELETED",
            user_id=deleted_by,
            tenant_id=tenant_id,
            resource_type="project_document",
            resource_id=document.id,
            old_values={
                "project_id": str(document.project_id),
                "document_type": document.document_type.value,
                "file_name": document.file_name
            }
        )

        # Delete from database
        db.delete(document)
        db.commit()

        return True

    @staticmethod
    async def delete_property_document(
        db: Session,
        document_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID
    ) -> bool:
        """Delete a property document"""
        document = db.query(PropertyDocument).filter(
            and_(
                PropertyDocument.id == document_id,
                PropertyDocument.tenant_id == tenant_id
            )
        ).first()

        if not document:
            raise AppException(f"Document {document_id} not found", status_code=404)

        # Delete from S3
        s3_service = S3Service()
        try:
            await s3_service.delete_file(document.s3_key)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Failed to delete file from S3: {str(e)}")

        # Log audit event before deletion
        audit_logger.log_business_event(
            db=db,
            action="PROPERTY_DOCUMENT_DELETED",
            user_id=deleted_by,
            tenant_id=tenant_id,
            resource_type="property_document",
            resource_id=document.id,
            old_values={
                "property_id": str(document.property_id),
                "document_type": document.document_type.value,
                "file_name": document.file_name
            }
        )

        # Delete from database
        db.delete(document)
        db.commit()

        return True

    @staticmethod
    def get_project_document(
        db: Session,
        document_id: UUID,
        tenant_id: UUID
    ) -> ProjectDocument:
        """Get a specific project document"""
        document = db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.id == document_id,
                ProjectDocument.tenant_id == tenant_id
            )
        ).first()

        if not document:
            raise AppException(f"Document {document_id} not found", status_code=404)

        return document

    @staticmethod
    def get_property_document(
        db: Session,
        document_id: UUID,
        tenant_id: UUID
    ) -> PropertyDocument:
        """Get a specific property document"""
        document = db.query(PropertyDocument).filter(
            and_(
                PropertyDocument.id == document_id,
                PropertyDocument.tenant_id == tenant_id
            )
        ).first()

        if not document:
            raise AppException(f"Document {document_id} not found", status_code=404)

        return document