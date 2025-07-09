# ================================
# EXPOSES API (api/v1/exposes.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Request, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.dependencies import get_db, get_current_active_user, get_current_tenant_id, require_permission
from app.models.user import User
from app.schemas.business import (
    ExposeTemplateCreate,
    ExposeTemplateUpdate,
    ExposeTemplateResponse,
    ExposeTemplateImageSchema,
    ExposeLinkCreate,
    ExposeLinkUpdate,
    ExposeLinkResponse,
    ExposeLinkPublicResponse
)
from app.schemas.base import SuccessResponse
from app.services.expose_service import ExposeService
from app.services.city_service import CityService
from app.core.exceptions import AppException
from app.models.business import ExposeLink

router = APIRouter()

# Template Management Endpoints

@router.get("/templates/", response_model=List[ExposeTemplateResponse], response_model_exclude_none=True)
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """List all expose templates"""
    try:
        templates = ExposeService.list_templates(db, current_user)
        return [ExposeTemplateResponse.model_validate(t) for t in templates]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/", response_model=ExposeTemplateResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ExposeTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "manage_templates"))
):
    """Create a new expose template"""
    try:
        template = ExposeService.create_template(db, template_data, current_user)
        db.commit()
        
        return ExposeTemplateResponse.model_validate(template)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}", response_model=ExposeTemplateResponse, response_model_exclude_none=True)
async def get_template(
    template_id: UUID = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """Get a specific expose template"""
    try:
        template = ExposeService.get_template(db, template_id, current_user)
        return ExposeTemplateResponse.model_validate(template)
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/templates/{template_id}", response_model=ExposeTemplateResponse, response_model_exclude_none=True)
async def update_template(
    template_id: UUID = Path(..., description="Template ID"),
    template_data: ExposeTemplateUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "manage_templates"))
):
    """Update an expose template"""
    try:
        template = ExposeService.update_template(db, template_id, template_data, current_user)
        db.commit()
        
        return ExposeTemplateResponse.model_validate(template)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "manage_templates"))
):
    """Delete an expose template"""
    try:
        ExposeService.delete_template(db, template_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Template Image Management Endpoints

@router.post("/templates/{template_id}/images/upload", response_model=SuccessResponse)
async def upload_template_image(
    template_id: UUID = Path(..., description="Template ID"),
    image: UploadFile = File(..., description="Image file to upload"),
    image_type: str = Form("coliving", description="Image type (coliving, special_features, management, general)"),
    title: Optional[str] = Form(None, description="Image title"),
    description: Optional[str] = Form(None, description="Image description"),
    display_order: int = Form(0, description="Display order"),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "manage_templates"))
):
    """Upload an image for an expose template"""
    try:
        
        # Validate image type
        valid_types = ["coliving", "special_features", "management", "general"]
        if image_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid image type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Check template exists and user has access
        template = ExposeService.get_template(db, template_id, current_user)
        
        # Upload image
        from app.services.s3_service import S3Service
        s3_service = S3Service()
        
        # Upload to S3
        from app.dependencies import get_s3_service
        s3_service = get_s3_service()
        
        # Set resize options based on image type
        resize_options = None
        if image_type in ['coliving', 'special_features']:
            # Resize images to max 1920px wide
            resize_options = {'width': 1920, 'quality': 85}
        
        upload_result = await s3_service.upload_image(
            file=image,
            folder=f"expose_templates/{template_id}/{image_type}",
            tenant_id=str(tenant_id),
            max_size_mb=10,
            resize_options=resize_options
        )
        
        # Create database record
        from app.models.business import ExposeTemplateImage
        
        image = ExposeTemplateImage(
            template_id=template_id,
            tenant_id=tenant_id,
            image_url=upload_result["url"],
            image_type=image_type,
            title=title,
            description=description,
            display_order=display_order,
            file_size=upload_result.get("file_size"),
            mime_type=upload_result.get("mime_type"),
            width=upload_result.get("width"),
            height=upload_result.get("height"),
            created_by=current_user.id
        )
        
        db.add(image)
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Image uploaded successfully"
        )
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}/images", response_model=List[ExposeTemplateImageSchema])
async def list_template_images(
    template_id: UUID = Path(..., description="Template ID"),
    image_type: Optional[str] = Query(None, description="Filter by image type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """List all images for an expose template"""
    try:
        # Check template exists and user has access
        template = ExposeService.get_template(db, template_id, current_user)
        
        # Build query
        from app.models.business import ExposeTemplateImage
        query = db.query(ExposeTemplateImage).filter(
            ExposeTemplateImage.template_id == template_id
        )
        
        if image_type:
            query = query.filter(ExposeTemplateImage.image_type == image_type)
        
        # Order by display_order, then created_at
        images = query.order_by(
            ExposeTemplateImage.display_order,
            ExposeTemplateImage.created_at
        ).all()
        
        # Import at function level to avoid circular imports
        from app.schemas.business import ExposeTemplateImageSchema
        
        return [ExposeTemplateImageSchema.model_validate(img) for img in images]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_image(
    template_id: UUID = Path(..., description="Template ID"),
    image_id: UUID = Path(..., description="Image ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "manage_templates"))
):
    """Delete an expose template image"""
    try:
        # Check template exists and user has access
        template = ExposeService.get_template(db, template_id, current_user)
        
        # Find the image
        from app.models.business import ExposeTemplateImage
        image = db.query(ExposeTemplateImage).filter(
            ExposeTemplateImage.id == image_id,
            ExposeTemplateImage.template_id == template_id
        ).first()
        
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Delete from S3
        from app.services.s3_service import S3Service
        s3_service = S3Service()
        s3_service.delete_file(image.image_url)
        
        # Delete from database
        db.delete(image)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Expose Link Management Endpoints

@router.get("/links/", response_model=List[ExposeLinkResponse], response_model_exclude_none=True)
async def list_expose_links(
    property_id: Optional[UUID] = Query(None, description="Filter by property ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """List all expose links"""
    try:
        response_data = ExposeService.list_expose_links_with_details(
            db, current_user, property_id, is_active
        )
        return [ExposeLinkResponse(**data) for data in response_data]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/links/", response_model=ExposeLinkResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_expose_link(
    link_data: ExposeLinkCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "create"))
):
    """Create a new expose link"""
    try:
        link = ExposeService.create_expose_link(db, link_data, current_user)
        db.commit()
        
        return ExposeLinkResponse.model_validate(link)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/{link_id}", response_model=ExposeLinkResponse, response_model_exclude_none=True)
async def get_expose_link_details(
    link_id: UUID = Path(..., description="Expose link UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """Get details of an expose link (for management)"""
    try:
        # Get link by UUID (not public link_id)
        link = db.query(ExposeLink).filter(
            ExposeLink.id == link_id,
            ExposeLink.tenant_id == current_user.tenant_id
        ).first()
        
        if not link:
            raise HTTPException(status_code=404, detail="Expose link not found")
        
        return ExposeLinkResponse.model_validate(link)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/links/{link_id}", response_model=ExposeLinkResponse, response_model_exclude_none=True)
async def update_expose_link(
    link_id: UUID = Path(..., description="Expose link UUID"),
    link_data: ExposeLinkUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """Update an expose link"""
    try:
        link = ExposeService.update_expose_link(db, link_id, link_data, current_user)
        db.commit()
        
        return ExposeLinkResponse.model_validate(link)
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expose_link(
    link_id: UUID = Path(..., description="Expose link UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """Delete an expose link"""
    try:
        ExposeService.delete_expose_link(db, link_id, current_user)
        db.commit()
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/links/{link_id}/stats", response_model=dict, response_model_exclude_none=True)
async def get_expose_link_stats(
    link_id: UUID = Path(..., description="Expose link UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """Get statistics for an expose link"""
    try:
        stats = ExposeService.get_expose_link_stats(db, link_id, current_user)
        return stats
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Public Expose Access (No authentication required)

@router.get("/public/{link_id}", response_model=ExposeLinkPublicResponse, response_model_exclude_none=True)
async def get_public_expose(
    link_id: str = Path(..., description="Public expose link ID"),
    password: Optional[str] = Query(None, description="Password if required"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Access a public expose link"""
    try:
        # Extract viewer info from request
        viewer_info = None
        if request:
            viewer_info = {
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "referrer": request.headers.get("referer")
            }
        
        # Get expose link and track view
        link = ExposeService.get_expose_link(
            db, link_id, password, track_view=True, viewer_info=viewer_info
        )
        db.commit()
        
        # Get tenant's template if link doesn't have one
        template = link.template
        if not template:
            from app.models.business import ExposeTemplate
            template = db.query(ExposeTemplate).filter(
                ExposeTemplate.tenant_id == link.tenant_id
            ).first()
        
        # Get city information if available
        city_info = None
        if link.property and link.property.city:
            from app.models.user import User
            # Create a temporary user context for city lookup
            temp_user = User(tenant_id=link.tenant_id, is_super_admin=False)
            city = CityService.get_city_by_name(
                db, link.property.city, link.property.state, temp_user
            )
            if city:
                city_info = city
        
        # Get tenant contact information
        from app.models.tenant import Tenant
        tenant = db.query(Tenant).filter(Tenant.id == link.tenant_id).first()
        tenant_contact = None
        if tenant:
            tenant_contact = {
                "email": tenant.contact_email,
                "phone": tenant.contact_phone,
                "street": tenant.contact_street,
                "house_number": tenant.contact_house_number,
                "city": tenant.contact_city,
                "state": tenant.contact_state,
                "zip_code": tenant.contact_zip_code,
                "country": tenant.contact_country,
                "company_name": tenant.name
            }
        
        # Build response
        response = ExposeLinkPublicResponse(
            link_id=link.link_id,
            property=link.property,
            template=template,  # Use the tenant's template
            preset_equity_percentage=link.preset_equity_percentage,
            preset_interest_rate=link.preset_interest_rate,
            preset_repayment_rate=link.preset_repayment_rate,
            preset_gross_income=link.preset_gross_income,
            preset_is_married=link.preset_is_married,
            preset_monthly_rent=link.preset_monthly_rent,
            visible_sections=link.visible_sections,
            custom_message=link.custom_message,
            city_info=city_info,
            tenant_contact=tenant_contact
        )
        
        return response
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))