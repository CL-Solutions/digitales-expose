# ================================
# CITIES API (api/v1/cities.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.dependencies import get_db, get_current_active_user, require_permission, get_current_tenant_id
from app.models.user import User
from app.schemas.business import (
    CityCreate,
    CityUpdate,
    CityResponse,
    CityImageCreate,
    CityImageUpdate,
    CityImageSchema
)
from app.schemas.base import SuccessResponse
from app.services.city_service import CityService
from app.services.s3_service import get_s3_service
from app.core.exceptions import AppException
from app.config import settings

router = APIRouter()

@router.get("/", response_model=List[CityResponse], response_model_exclude_none=True)
async def list_cities(
    state: Optional[str] = Query(None, description="Filter by state"),
    search: Optional[str] = Query(None, description="Search by city name"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "read"))
):
    """List all cities"""
    try:
        cities = CityService.list_cities(db, current_user, state, search)
        return [CityResponse.model_validate(c) for c in cities]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/with-properties/", response_model=List[Dict[str, Any]], response_model_exclude_none=True)
async def get_cities_with_properties(
    current_user: User = Depends(get_current_active_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "read"))
):
    """Get cities that have properties available"""
    try:
        cities = CityService.get_cities_with_properties(db, current_user, tenant_id)
        return cities
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CityResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_city(
    city_data: CityCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "create"))
):
    """Create a new city"""
    try:
        city = CityService.create_city(db, city_data, current_user)
        db.commit()
        
        return CityResponse.model_validate(city)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{city_id}", response_model=CityResponse, response_model_exclude_none=True)
async def get_city(
    city_id: UUID = Path(..., description="City ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "read"))
):
    """Get city details"""
    try:
        city = CityService.get_city(db, city_id, current_user)
        return CityResponse.model_validate(city)
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{city_id}", response_model=CityResponse, response_model_exclude_none=True)
async def update_city(
    city_id: UUID = Path(..., description="City ID"),
    city_data: CityUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "update"))
):
    """Update city details"""
    try:
        city = CityService.update_city(db, city_id, city_data, current_user)
        db.commit()
        
        return CityResponse.model_validate(city)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city(
    city_id: UUID = Path(..., description="City ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "delete"))
):
    """Delete a city"""
    try:
        CityService.delete_city(db, city_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# City Images Endpoints

@router.post("/{city_id}/images/upload", response_model=CityImageSchema, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def upload_city_image(
    city_id: UUID = Path(..., description="City ID"),
    image: UploadFile = File(..., description="Image file to upload"),
    image_type: str = Form(..., description="Image type (header, location, lifestyle, other)"),
    title: Optional[str] = Form(None, description="Image title"),
    description: Optional[str] = Form(None, description="Image description"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "update"))
):
    """Upload an image file for a city"""
    try:
        # Validate image type
        valid_types = ['header', 'location', 'lifestyle', 'other']
        if image_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Get city to ensure access and get tenant_id
        city = CityService.get_city(db, city_id, current_user)
        
        # Upload to S3
        s3_service = get_s3_service()
        
        # Set resize options based on image type
        resize_options = None
        if image_type == 'header':
            # Header images should be wide for hero sections
            resize_options = {'width': 1920, 'quality': 85}
        else:
            # Other images can be slightly smaller
            resize_options = {'width': 1600, 'quality': 85}
        
        upload_result = await s3_service.upload_image(
            file=image,
            folder=f"cities/{city_id}",
            tenant_id=str(city.tenant_id),
            resize_options=resize_options
        )
        
        # Create image record with S3 data
        image_data = CityImageCreate(
            image_url=upload_result['url'],
            image_type=image_type,
            title=title,
            description=description,
            file_size=upload_result['file_size'],
            mime_type=upload_result['mime_type'],
            width=upload_result.get('width'),
            height=upload_result.get('height')
        )
        
        # Save to database using the existing service method
        image_record = CityService.add_city_image(
            db, city_id, image_data.image_url, image_data.image_type,
            image_data.title, image_data.description, current_user
        )
        
        db.commit()
        
        return CityImageSchema.model_validate(image_record)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{city_id}/images", response_model=CityImageSchema, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def add_city_image(
    city_id: UUID = Path(..., description="City ID"),
    image_url: str = ...,
    image_type: str = ...,
    title: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("images", "upload"))
):
    """Add an image to a city"""
    try:
        image = CityService.add_city_image(
            db, city_id, image_url, image_type, 
            title, description, current_user
        )
        db.commit()
        
        return CityImageSchema.model_validate(image)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{city_id}/images/{image_id}", response_model=CityImageSchema, response_model_exclude_none=True)
async def update_city_image(
    image_data: CityImageUpdate,
    city_id: UUID = Path(..., description="City ID"),
    image_id: UUID = Path(..., description="Image ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("images", "upload"))
):
    """Update a city image metadata"""
    try:
        # Get city to ensure access
        city = CityService.get_city(db, city_id, current_user)
        
        # Get and update image
        from app.models.business import CityImage
        image = db.query(CityImage).filter(
            CityImage.id == image_id,
            CityImage.city_id == city.id
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=404,
                detail="Image not found"
            )
        
        # Update fields
        update_data = image_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(image, field, value)
        
        image.updated_by = current_user.id
        image.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return CityImageSchema.model_validate(image)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{city_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city_image(
    city_id: UUID = Path(..., description="City ID"),
    image_id: UUID = Path(..., description="Image ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("cities", "update"))
):
    """Delete a city image"""
    try:
        # Get image to extract S3 key from URL if needed
        from app.models.business import CityImage
        image = db.query(CityImage).filter(CityImage.id == image_id).first()
        
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
        CityService.delete_city_image(db, city_id, image_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))