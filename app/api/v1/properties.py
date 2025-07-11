# ================================
# PROPERTIES API (api/v1/properties.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from app.dependencies import get_db, get_current_active_user, require_permission, get_current_tenant_id
from app.models.user import User
from app.schemas.business import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyOverview,
    PropertyFilter,
    PropertyListResponse,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyImageSchema,
    PropertyAggregateStats
)
from app.schemas.base import SuccessResponse
from app.services.property_service import PropertyService
from app.services.s3_service import get_s3_service
from app.core.exceptions import AppException
from app.config import settings
from app.mappers.property_mapper import map_property_to_response

router = APIRouter()

@router.get("/", response_model=PropertyListResponse, response_model_exclude_none=True)
async def list_properties(
    filter_params: PropertyFilter = Depends(),
    active: Optional[List[int]] = Query(None),
    current_user: User = Depends(get_current_active_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "read"))
):
    """List all properties with filtering (overview only)"""
    try:
        # Override the active filter with the list from query params
        if active is not None:
            filter_params.active = active
        result = PropertyService.list_properties(db, current_user, filter_params, tenant_id)
        db.commit()
        
        return PropertyListResponse(
            items=result["items"],  # Already PropertyOverview objects
            total=result["total"],
            page=result["page"],
            size=result["size"],
            pages=result["pages"]
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aggregate-stats", response_model=PropertyAggregateStats)
async def get_property_aggregate_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Get aggregate statistics for all properties"""
    try:
        stats = PropertyService.get_aggregate_stats(db, tenant_id, current_user)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get property aggregate stats: {str(e)}"
        )

@router.post("/", response_model=PropertyResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "create"))
):
    """Create a new property"""
    try:
        property = PropertyService.create_property(db, property_data, current_user)
        db.commit()
        
        # Use mapper to get response data with calculated fields
        response_data = map_property_to_response(property)
        return PropertyResponse(**response_data)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{property_id}", response_model=PropertyResponse, response_model_exclude_none=True)
async def get_property(
    property_id: UUID = Path(..., description="Property ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "read"))
):
    """Get property details"""
    try:
        property = PropertyService.get_property(db, property_id, current_user)
        
        # Use mapper to get response data with calculated fields
        response_data = map_property_to_response(property)
        
        # Convert related objects to dicts for proper serialization
        if property.project:
            project_dict = property.project.__dict__.copy()
            project_dict.pop('_sa_instance_state', None)
            
            # Check if user is tenant admin
            from app.dependencies import check_user_has_role
            is_tenant_admin = current_user.is_super_admin or check_user_has_role(
                db, current_user.id, current_user.tenant_id, "tenant_admin"
            )
            
            # Calculate user's effective provision percentage
            project_provision = property.project.provision_percentage or 0
            user_provision = current_user.provision_percentage or 0
            
            # Add logging for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Calculating provision for user {current_user.email} (ID: {current_user.id})")
            logger.info(f"Project provision: {project_provision}%")
            logger.info(f"User provision: {user_provision}%")
            
            # Check if user is in a team
            from app.models.user_team import UserTeamAssignment
            team_assignment = db.query(UserTeamAssignment).options(
                joinedload(UserTeamAssignment.manager)
            ).filter(
                UserTeamAssignment.member_id == current_user.id,
                UserTeamAssignment.tenant_id == current_user.tenant_id
            ).first()
            
            if team_assignment and team_assignment.manager:
                # User is in a team: project% * manager% * user_team%
                manager_provision = team_assignment.manager.provision_percentage or 0
                team_member_provision = team_assignment.provision_percentage or 0
                
                logger.info(f"User is in team - Manager: {team_assignment.manager.email}")
                logger.info(f"Manager provision: {manager_provision}%")
                logger.info(f"Team member provision: {team_member_provision}%")
                
                user_effective_provision = (project_provision * manager_provision / 100 * team_member_provision / 100)
                logger.info(f"Calculated effective provision (team): {user_effective_provision}%")
            else:
                # User is independent: project% * user%
                logger.info(f"User is independent (no team assignment)")
                user_effective_provision = (project_provision * user_provision / 100)
                logger.info(f"Calculated effective provision (independent): {user_effective_provision}%")
            
            project_dict['user_effective_provision_percentage'] = user_effective_provision
            
            # Hide project provision percentage from non-admin users
            if not is_tenant_admin:
                project_dict['provision_percentage'] = 0
            
            # Ensure all required fields are present
            project_dict['properties'] = []  # We don't need to load all properties for the property detail view
            if not project_dict.get('images'):
                project_dict['images'] = []
            
            # Convert project images if they exist
            if hasattr(property.project, 'images') and property.project.images:
                project_images = []
                for img in property.project.images:
                    img_dict = img.__dict__.copy()
                    img_dict.pop('_sa_instance_state', None)
                    # Add property_id as None for GenericImageSchema compatibility
                    img_dict['property_id'] = None
                    project_images.append(img_dict)
                project_dict['images'] = project_images
            
            # Add city_ref to project if it exists
            if hasattr(property.project, 'city_ref') and property.project.city_ref:
                city_dict = property.project.city_ref.__dict__.copy()
                city_dict.pop('_sa_instance_state', None)
                project_dict['city_ref'] = city_dict
            else:
                # Make sure city_ref is included even if None
                project_dict['city_ref'] = None
            
            response_data['project'] = project_dict
            
        if property.images:
            response_data['images'] = []
            for img in property.images:
                img_dict = img.__dict__.copy()
                img_dict.pop('_sa_instance_state', None)
                # Add project_id as None for GenericImageSchema compatibility
                img_dict['project_id'] = None
                response_data['images'].append(img_dict)
                
        
        # The PropertyResponse validator will handle combining all_images
        return PropertyResponse.model_validate(response_data)
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{property_id}", response_model=PropertyResponse, response_model_exclude_none=True)
async def update_property(
    property_id: UUID = Path(..., description="Property ID"),
    property_data: PropertyUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "update"))
):
    """Update property details"""
    try:
        property = PropertyService.update_property(db, property_id, property_data, current_user)
        db.commit()
        
        # Use mapper to get response data with calculated fields
        response_data = map_property_to_response(property)
        return PropertyResponse(**response_data)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: UUID = Path(..., description="Property ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "delete"))
):
    """Delete a property"""
    try:
        PropertyService.delete_property(db, property_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Property Images Endpoints

@router.post("/{property_id}/images/upload", response_model=PropertyImageSchema, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def upload_property_image(
    property_id: UUID = Path(..., description="Property ID"),
    image: UploadFile = File(..., description="Image file to upload"),
    image_type: str = Form(..., description="Image type (exterior, interior, floor_plan, energy_certificate, bathroom, kitchen, bedroom, living_room, balcony, garden, parking, basement, roof)"),
    title: Optional[str] = Form(None, description="Image title"),
    description: Optional[str] = Form(None, description="Image description"),
    display_order: int = Form(0, description="Display order"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "update"))
):
    """Upload an image file for a property"""
    try:
        # Validate image type
        valid_types = ['exterior', 'interior', 'floor_plan', 'energy_certificate', 'bathroom', 'kitchen', 'bedroom', 'living_room', 'balcony', 'garden', 'parking', 'basement', 'roof']
        if image_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Get property to ensure access and get tenant_id
        property = PropertyService.get_property(db, property_id, current_user)
        
        # Upload to S3
        s3_service = get_s3_service()
        
        # Set resize options based on image type
        resize_options = None
        if image_type in ['exterior', 'interior']:
            # Resize property photos to max 1920px wide
            resize_options = {'width': 1920, 'quality': 85}
        elif image_type == 'floor_plan':
            # Keep floor plans larger
            resize_options = {'width': 2400, 'quality': 90}
        
        upload_result = await s3_service.upload_image(
            file=image,
            folder=f"properties/{property_id}",
            tenant_id=str(property.tenant_id),
            max_size_mb=20,  # Allow larger files for floor plans
            resize_options=resize_options
        )
        
        # Create image record with S3 data
        image_data = PropertyImageCreate(
            image_url=upload_result['url'],
            image_type=image_type,
            title=title,
            description=description,
            display_order=display_order,
            file_size=upload_result['file_size'],
            mime_type=upload_result['mime_type'],
            width=upload_result.get('width'),
            height=upload_result.get('height')
        )
        
        # Save to database
        image_record = PropertyService.add_property_image(
            db, property_id, image_data, current_user
        )
        
        # Store S3 key in a separate field if needed for deletion
        # For now, we can extract it from the URL if needed
        
        db.commit()
        
        return PropertyImageSchema.model_validate(image_record)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{property_id}/images", response_model=PropertyImageSchema, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def add_property_image(
    property_id: UUID = Path(..., description="Property ID"),
    image_data: PropertyImageCreate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("images", "upload"))
):
    """Add an image URL to a property (for external images)"""
    try:
        image = PropertyService.add_property_image(db, property_id, image_data, current_user)
        db.commit()
        
        return PropertyImageSchema.model_validate(image)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{property_id}/images/{image_id}", response_model=PropertyImageSchema, response_model_exclude_none=True)
async def update_property_image(
    property_id: UUID = Path(..., description="Property ID"),
    image_id: UUID = Path(..., description="Image ID"),
    image_data: PropertyImageUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("images", "upload"))
):
    """Update a property image metadata"""
    try:
        image = PropertyService.update_property_image(
            db, property_id, image_id, image_data, current_user
        )
        db.commit()
        
        return PropertyImageSchema.model_validate(image)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{property_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_image(
    property_id: UUID = Path(..., description="Property ID"),
    image_id: UUID = Path(..., description="Image ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "update"))
):
    """Delete a property image"""
    try:
        # Get image to extract S3 key from URL if needed
        from app.models.business import PropertyImage
        image = db.query(PropertyImage).filter(PropertyImage.id == image_id).first()
        
        if image and image.image_url:
            # Extract S3 key from URL if it's an S3 URL
            s3_service = get_s3_service()
            if s3_service.is_configured() and settings.S3_ENDPOINT_URL in image.image_url:
                # Extract key from URL
                url_parts = image.image_url.split('/')
                # Skip protocol, domain, and reconstruct key
                key_start_index = 3  # After https://bucket.domain/
                s3_key = '/'.join(url_parts[key_start_index:])
                
                # Delete from S3
                s3_service.delete_image(s3_key)
        
        # Delete from database
        PropertyService.delete_property_image(db, property_id, image_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Property Statistics

@router.get("/stats/overview/", response_model=dict, response_model_exclude_none=True)
async def get_property_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("properties", "read"))
):
    """Get property statistics for the tenant"""
    try:
        stats = PropertyService.get_property_stats(db, current_user)
        return stats
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

