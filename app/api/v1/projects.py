# ================================
# PROJECT ROUTES (api/v1/projects.py)
# ================================

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_active_user, get_current_tenant_id, require_permission
from app.schemas.business import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectFilter, ProjectImageCreate, ProjectImageUpdate, ProjectImageSchema
)
from app.models.user import User
from app.services.project_service import ProjectService
from app.core.exceptions import AppException
from app.services.s3_service import get_s3_service

router = APIRouter()

# ================================
# Project CRUD Endpoints
# ================================

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "create"))
):
    """Create a new project"""
    try:
        new_project = ProjectService.create_project(
            db=db,
            project_data=project,
            created_by=current_user.id,
            tenant_id=tenant_id
        )
        return ProjectResponse.model_validate(new_project)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    filters: ProjectFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "read"))
):
    """List all projects with filtering and pagination"""
    return ProjectService.list_projects(
        db=db,
        tenant_id=tenant_id,
        filters=filters,
        current_user=current_user
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "read"))
):
    """Get project by ID"""
    try:
        import re
        from app.schemas.business import PropertyOverview
        from app.mappers.property_mapper import map_property_to_overview
        
        project = ProjectService.get_project(db, project_id, tenant_id)
        
        # Convert properties to PropertyOverview using mapper
        property_overviews = []
        if project.properties:
            for prop in project.properties:
                # Use mapper to convert property to overview dict
                overview_data = map_property_to_overview(prop)
                # Create PropertyOverview from the mapped data
                overview = PropertyOverview(**overview_data)
                property_overviews.append(overview)
            
            # Sort properties by unit number
            def get_unit_number_sort_key(prop):
                # Extract all numbers from the unit_number
                numbers = re.findall(r'\d+', prop.unit_number)
                # Return the first number as an integer, or 0 if no numbers found
                return int(numbers[0]) if numbers else 0
            
            property_overviews.sort(key=get_unit_number_sort_key)
        
        # Create response with property overviews
        response_data = project.__dict__.copy()
        response_data['properties'] = property_overviews
        
        return ProjectResponse.model_validate(response_data)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "update"))
):
    """Update project"""
    try:
        updated_project = ProjectService.update_project(
            db=db,
            project_id=project_id,
            project_update=project_update,
            updated_by=current_user.id,
            tenant_id=tenant_id
        )
        return ProjectResponse.model_validate(updated_project)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "delete"))
):
    """Delete project"""
    try:
        ProjectService.delete_project(
            db=db,
            project_id=project_id,
            deleted_by=current_user.id,
            tenant_id=tenant_id
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

# ================================
# Project Statistics
# ================================

@router.get("/{project_id}/statistics", response_model=Dict[str, Any])
async def get_project_statistics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "read"))
):
    """Get project statistics"""
    try:
        project = ProjectService.get_project(db, project_id, tenant_id)
        # Calculate statistics
        return {
            "total_properties": len(project.properties),
            "total_size_sqm": sum(p.size_sqm for p in project.properties if p.size_sqm),
            "active_properties": sum(1 for p in project.properties if p.active and p.active > 0),
            "pre_sale_properties": sum(1 for p in project.properties if p.pre_sale == 1),
            "draft_properties": sum(1 for p in project.properties if p.draft == 1)
        }
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

# ================================
# Project Image Management
# ================================

@router.post("/{project_id}/images/upload", response_model=ProjectImageSchema)
async def upload_project_image(
    project_id: UUID,
    file: UploadFile = File(...),
    image_type: str = Form(..., regex="^(exterior|common_area|amenity|floor_plan)$"),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "update"))
):
    """Upload an image for a project"""
    try:
        # Verify project exists
        ProjectService.get_project(db, project_id, tenant_id)
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed"
            )
        
        # Upload to S3
        s3_service = get_s3_service()
        if not s3_service or not s3_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image storage service is not available"
            )
            
        upload_result = await s3_service.upload_image(
            file=file,
            folder="projects",
            tenant_id=str(tenant_id),
            resize_options={'width': 1920, 'quality': 85}
        )
        
        # Create database record
        image_data = ProjectImageCreate(
            image_url=upload_result['url'],
            image_type=image_type,
            title=title or f"{image_type.replace('_', ' ').title()} Image",
            description=description,
            display_order=display_order,
            file_size=upload_result.get('file_size', 0),
            mime_type=upload_result.get('mime_type', file.content_type),
            width=upload_result.get('width'),
            height=upload_result.get('height')
        )
        
        image = ProjectService.add_project_image(
            db=db,
            project_id=project_id,
            image_data=image_data,
            created_by=current_user.id,
            tenant_id=tenant_id
        )
        
        return ProjectImageSchema.model_validate(image)
        
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/{project_id}/images/{image_id}", response_model=ProjectImageSchema)
async def update_project_image(
    project_id: UUID,
    image_id: UUID,
    image_update: ProjectImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "update"))
):
    """Update project image metadata"""
    try:
        updated_image = ProjectService.update_project_image(
            db=db,
            project_id=project_id,
            image_id=image_id,
            image_update=image_update,
            updated_by=current_user.id,
            tenant_id=tenant_id
        )
        return ProjectImageSchema.model_validate(updated_image)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.delete("/{project_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_image(
    project_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "update"))
):
    """Delete project image"""
    try:
        ProjectService.delete_project_image(
            db=db,
            project_id=project_id,
            image_id=image_id,
            deleted_by=current_user.id,
            tenant_id=tenant_id
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

# ================================
# Micro Location Management
# ================================

@router.post("/{project_id}/refresh-micro-location", response_model=ProjectResponse)
async def refresh_micro_location(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("projects", "update"))
):
    """Manually refresh micro location data for a project"""
    try:
        # Use the service method with force_refresh=True for manual refresh
        success = ProjectService.refresh_project_micro_location(
            db=db,
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=current_user.id,
            force_refresh=True  # Always refresh when manually triggered
        )
        
        if not success:
            raise AppException(
                status_code=400,
                detail="Failed to refresh micro location data"
            )
        
        # Get the updated project
        project = ProjectService.get_project(db, project_id, tenant_id)
        
        return ProjectResponse.model_validate(project)
        
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh micro location data: {str(e)}"
        )