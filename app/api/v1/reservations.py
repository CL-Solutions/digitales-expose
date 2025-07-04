# ================================
# RESERVATION API ROUTES (api/v1/reservations.py)
# ================================

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import uuid

from app.dependencies import (
    get_db,
    get_current_active_user,
    get_current_tenant_id,
    require_permission
)
from app.models.user import User
from app.services.reservation_service import ReservationService
from app.schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    ReservationStatusUpdate,
    ReservationResponse,
    ReservationListResponse,
    ReservationStatusHistoryResponse,
    ReservationPromote,
    ReservationCancel,
    WaitlistReorder
)
from app.core.exceptions import AppException

router = APIRouter(
    prefix="/api/v1",
    tags=["reservations"]
)

@router.post("/properties/{property_id}/reservations", response_model=ReservationResponse)
async def create_reservation(
    property_id: uuid.UUID,
    reservation_data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "create"))
):
    """Create a new reservation for a property"""
    try:
        reservation = ReservationService.create_reservation(
            db=db,
            property_id=property_id,
            data=reservation_data,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return ReservationResponse.model_validate(reservation)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.get("/reservations", response_model=List[ReservationListResponse])
async def list_reservations(
    property_id: Optional[uuid.UUID] = Query(None),
    status: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "read"))
):
    """List reservations with role-based filtering"""
    reservations, total = ReservationService.list_reservations(
        db=db,
        user=current_user,
        tenant_id=tenant_id,
        property_id=property_id,
        status=status,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    # Return with total count header
    return [ReservationListResponse.model_validate(r) for r in reservations]

@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "read"))
):
    """Get reservation details"""
    try:
        reservation = ReservationService.get_reservation(
            db=db,
            reservation_id=reservation_id,
            user=current_user,
            tenant_id=tenant_id
        )
        
        # Map the response with additional fields
        response_data = {
            **reservation.__dict__,
            "unit_number": reservation.property.unit_number if reservation.property else None,
            "project_name": reservation.property.project.name if reservation.property and reservation.property.project else None,
        }
        
        return ReservationResponse.model_validate(response_data)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.put("/reservations/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: uuid.UUID,
    update_data: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "update"))
):
    """Update reservation details"""
    try:
        reservation = ReservationService.update_reservation(
            db=db,
            reservation_id=reservation_id,
            data=update_data,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return ReservationResponse.model_validate(reservation)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.post("/reservations/{reservation_id}/status", response_model=ReservationResponse)
async def update_reservation_status(
    reservation_id: uuid.UUID,
    status_data: ReservationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "manage"))
):
    """Update reservation status (Property Manager/Tenant Admin only)"""
    try:
        reservation = ReservationService.update_reservation_status(
            db=db,
            reservation_id=reservation_id,
            data=status_data,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return ReservationResponse.model_validate(reservation)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.post("/reservations/{reservation_id}/promote", response_model=ReservationResponse)
async def promote_reservation(
    reservation_id: uuid.UUID,
    promote_data: ReservationPromote,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "manage"))
):
    """Promote a waitlist reservation to active (Property Manager/Tenant Admin only)"""
    try:
        reservation = ReservationService.promote_reservation(
            db=db,
            reservation_id=reservation_id,
            data=promote_data,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return ReservationResponse.model_validate(reservation)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    cancel_data: ReservationCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "delete"))
):
    """Cancel a reservation"""
    try:
        ReservationService.cancel_reservation(
            db=db,
            reservation_id=reservation_id,
            data=cancel_data,
            user=current_user,
            tenant_id=tenant_id
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.put("/properties/{property_id}/waitlist", response_model=List[ReservationListResponse])
async def reorder_waitlist(
    property_id: uuid.UUID,
    reorder_data: WaitlistReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "manage"))
):
    """Reorder waitlist for a property (Property Manager/Tenant Admin only)"""
    try:
        reservations = ReservationService.reorder_waitlist(
            db=db,
            property_id=property_id,
            data=reorder_data,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return [ReservationListResponse.model_validate(r) for r in reservations]
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

@router.get("/reservations/{reservation_id}/history", response_model=List[ReservationStatusHistoryResponse])
async def get_reservation_history(
    reservation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("reservations", "read"))
):
    """Get status history for a reservation"""
    history = ReservationService.get_reservation_history(
        db=db,
        reservation_id=reservation_id,
        tenant_id=tenant_id
    )
    return [ReservationStatusHistoryResponse.model_validate(h) for h in history]

@router.get("/properties/{property_id}/reservation", response_model=Optional[ReservationResponse])
async def get_property_reservation(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("properties", "read"))
):
    """Get active reservation for a property"""
    reservations, _ = ReservationService.list_reservations(
        db=db,
        user=current_user,
        tenant_id=tenant_id,
        property_id=property_id,
        is_active=True,
        limit=1
    )
    
    if reservations:
        return ReservationResponse.model_validate(reservations[0])
    return None