"""
Fee Configuration API Endpoints

Handles tenant fee configuration and fee calculations.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import (
    get_db, 
    get_current_active_user, 
    get_current_tenant_id,
    require_permission
)
from app.models.user import User
from app.schemas.business import (
    TenantFeeConfigCreate,
    TenantFeeConfigUpdate,
    TenantFeeConfigResponse,
    FeeCalculationRequest,
    FeeCalculationResponse
)
from app.services.fee_calculation_service import FeeCalculationService
from app.core.exceptions import AppException, ValidationError
from app.utils.audit import AuditLogger

router = APIRouter(prefix="/fees", tags=["fees"])
audit_logger = AuditLogger()


@router.get("/config", response_model=TenantFeeConfigResponse)
async def get_fee_configuration(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("fees", "read"))
):
    """Get fee configuration for the current tenant"""
    config = FeeCalculationService.get_tenant_fee_config(db, tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fee configuration not found for this tenant"
        )
    
    return TenantFeeConfigResponse.model_validate(config)


@router.post("/config", response_model=TenantFeeConfigResponse)
async def create_fee_configuration(
    data: TenantFeeConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("fees", "create"))
):
    """Create fee configuration for the current tenant"""
    try:
        config = FeeCalculationService.create_tenant_fee_config(
            db=db,
            tenant_id=tenant_id,
            data=data,
            created_by=current_user.id
        )
        
        # Log the action
        audit_logger.log_business_event(
            db=db,
            action="FEE_CONFIG_CREATED",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="tenant_fee_config",
            resource_id=config.id,
            new_values={
                "notary_kaufvertrag_rate": float(config.notary_kaufvertrag_rate),
                "notary_grundschuld_rate": float(config.notary_grundschuld_rate),
                "notary_vollzug_rate": float(config.notary_vollzug_rate),
                "grundbuch_auflassung_rate": float(config.grundbuch_auflassung_rate),
                "grundbuch_eigentum_rate": float(config.grundbuch_eigentum_rate),
                "grundbuch_grundschuld_rate": float(config.grundbuch_grundschuld_rate),
                "notary_override_percentage": float(config.notary_override_percentage) if config.notary_override_percentage else None
            }
        )
        
        return TenantFeeConfigResponse.model_validate(config)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/config", response_model=TenantFeeConfigResponse)
async def update_fee_configuration(
    data: TenantFeeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("fees", "update"))
):
    """Update fee configuration for the current tenant"""
    try:
        # Get existing config for old values
        existing_config = FeeCalculationService.get_tenant_fee_config(db, tenant_id)
        if existing_config:
            old_values = {
                "notary_kaufvertrag_rate": float(existing_config.notary_kaufvertrag_rate),
                "notary_grundschuld_rate": float(existing_config.notary_grundschuld_rate),
                "notary_vollzug_rate": float(existing_config.notary_vollzug_rate),
                "grundbuch_auflassung_rate": float(existing_config.grundbuch_auflassung_rate),
                "grundbuch_eigentum_rate": float(existing_config.grundbuch_eigentum_rate),
                "grundbuch_grundschuld_rate": float(existing_config.grundbuch_grundschuld_rate),
                "notary_override_percentage": float(existing_config.notary_override_percentage) if existing_config.notary_override_percentage else None
            }
        else:
            old_values = {}
        
        config = FeeCalculationService.update_tenant_fee_config(
            db=db,
            tenant_id=tenant_id,
            data=data,
            updated_by=current_user.id
        )
        
        # Log the action
        new_values = {}
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                new_values[field] = float(value)
        
        audit_logger.log_business_event(
            db=db,
            action="FEE_CONFIG_UPDATED",
            user_id=current_user.id,
            tenant_id=tenant_id,
            resource_type="tenant_fee_config",
            resource_id=config.id,
            old_values=old_values,
            new_values=new_values
        )
        
        return TenantFeeConfigResponse.model_validate(config)
        
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculate", response_model=FeeCalculationResponse)
async def calculate_fees(
    request: FeeCalculationRequest,
    property_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("fees", "read"))
):
    """Calculate notary and Grundbuch fees based on configuration"""
    try:
        result = FeeCalculationService.calculate_fees(
            db=db,
            tenant_id=tenant_id,
            request=request,
            property_id=property_id
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))