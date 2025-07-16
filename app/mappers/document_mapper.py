from typing import Union
from app.models.business import ProjectDocument, PropertyDocument
from app.schemas.document import ProjectDocumentResponse, PropertyDocumentResponse, DocumentResponse


def map_document_to_response(
    document: Union[ProjectDocument, PropertyDocument]
) -> Union[ProjectDocumentResponse, PropertyDocumentResponse]:
    """Map a document model to its response schema"""
    
    # Common fields
    base_data = {
        "id": document.id,
        "document_type": document.document_type,
        "title": document.title,
        "description": document.description,
        "display_order": document.display_order,
        "file_name": document.file_name,
        "file_path": document.file_path,
        "file_size": document.file_size,
        "mime_type": document.mime_type,
        "s3_key": document.s3_key,
        "s3_bucket": document.s3_bucket,
        "uploaded_by": document.uploaded_by,
        "uploaded_at": document.uploaded_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at
    }
    
    # Return appropriate response type
    if isinstance(document, ProjectDocument):
        return ProjectDocumentResponse(
            **base_data,
            project_id=document.project_id
        )
    else:  # PropertyDocument
        return PropertyDocumentResponse(
            **base_data,
            property_id=document.property_id
        )