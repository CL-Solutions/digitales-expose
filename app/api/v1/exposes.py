# ================================
# EXPOSES API (api/v1/exposes.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.dependencies import get_db, get_current_active_user, require_permission
from app.models.user import User
from app.schemas.business import (
    ExposeTemplateCreate,
    ExposeTemplateUpdate,
    ExposeTemplateResponse,
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

@router.get("/templates", response_model=List[ExposeTemplateResponse])
async def list_templates(
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("expose", "view"))
):
    """List all expose templates"""
    try:
        templates = ExposeService.list_templates(db, current_user, property_type, is_active)
        return [ExposeTemplateResponse.model_validate(t) for t in templates]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates", response_model=ExposeTemplateResponse, status_code=status.HTTP_201_CREATED)
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

@router.get("/templates/{template_id}", response_model=ExposeTemplateResponse)
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

@router.put("/templates/{template_id}", response_model=ExposeTemplateResponse)
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

# Expose Link Management Endpoints

@router.get("/links", response_model=List[ExposeLinkResponse])
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

@router.post("/links", response_model=ExposeLinkResponse, status_code=status.HTTP_201_CREATED)
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

@router.get("/links/{link_id}", response_model=ExposeLinkResponse)
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

@router.put("/links/{link_id}", response_model=ExposeLinkResponse)
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

@router.get("/links/{link_id}/stats", response_model=dict)
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

@router.get("/public/{link_id}", response_model=ExposeLinkPublicResponse)
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
        
        # Build response
        response = ExposeLinkPublicResponse(
            link_id=link.link_id,
            property=link.property,
            template=link.template,
            preset_equity_amount=link.preset_equity_amount,
            preset_interest_rate=link.preset_interest_rate,
            preset_loan_term_years=link.preset_loan_term_years,
            preset_monthly_rent=link.preset_monthly_rent,
            visible_sections=link.visible_sections,
            custom_message=link.custom_message,
            city_info=city_info
        )
        
        return response
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))