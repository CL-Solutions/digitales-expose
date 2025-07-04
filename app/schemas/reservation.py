# ================================
# RESERVATION SCHEMAS (schemas/reservation.py)
# ================================

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import validator, Field
import uuid

from app.schemas.base import BaseSchema, BaseResponseSchema, TimestampMixin
from app.schemas.user import UserBasicInfo

class ReservationBase(BaseSchema):
    """Base reservation schema"""
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    
    # Financial Details
    equity_amount: Optional[Decimal] = Field(None, decimal_places=2)
    equity_percentage: Optional[Decimal] = Field(None, decimal_places=2, ge=0, le=100)
    is_90_10_deal: bool = False
    adjusted_purchase_price: Optional[Decimal] = Field(None, decimal_places=2)
    external_commission: Optional[Decimal] = Field(None, decimal_places=2)
    internal_commission: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Notary Details
    preferred_notary: Optional[str] = Field(None, max_length=255)
    
    # Notes
    notes: Optional[str] = None

class ReservationCreate(ReservationBase):
    """Schema for creating a reservation"""
    pass

class ReservationUpdate(BaseSchema):
    """Schema for updating a reservation"""
    customer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    
    # Financial Details
    equity_amount: Optional[Decimal] = Field(None, decimal_places=2)
    equity_percentage: Optional[Decimal] = Field(None, decimal_places=2, ge=0, le=100)
    is_90_10_deal: Optional[bool] = None
    adjusted_purchase_price: Optional[Decimal] = Field(None, decimal_places=2)
    external_commission: Optional[Decimal] = Field(None, decimal_places=2)
    internal_commission: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Notary Details
    preferred_notary: Optional[str] = Field(None, max_length=255)
    notary_appointment_date: Optional[datetime] = None
    notary_appointment_time: Optional[datetime] = None
    notary_location: Optional[str] = Field(None, max_length=500)
    
    # Notes
    notes: Optional[str] = None

class ReservationStatusUpdate(BaseSchema):
    """Schema for updating reservation status"""
    status: int = Field(..., ge=0, le=9)
    notes: Optional[str] = None
    
    # Required for status 6 (Reserviert)
    reservation_fee_paid: Optional[bool] = None
    reservation_fee_paid_date: Optional[datetime] = None
    
    # Required for status 7 (Notartermin)
    notary_appointment_date: Optional[datetime] = None
    notary_appointment_time: Optional[datetime] = None
    notary_location: Optional[str] = Field(None, max_length=500)
    
    @validator('reservation_fee_paid', 'reservation_fee_paid_date')
    def validate_reservation_fee(cls, v, values):
        """Validate reservation fee fields when moving to Reserviert status"""
        if 'status' in values and values['status'] == 6:
            if v is None:
                raise ValueError('Reservation fee information required when setting status to Reserviert')
        return v
    
    @validator('notary_appointment_date', 'notary_appointment_time')
    def validate_notary_appointment(cls, v, values):
        """Validate notary appointment fields when moving to Notartermin status"""
        if 'status' in values and values['status'] == 7:
            if v is None:
                raise ValueError('Notary appointment date and time required when setting status to Notartermin')
        return v

class ReservationResponse(ReservationBase, BaseResponseSchema, TimestampMixin):
    """Reservation response with all details"""
    property_id: uuid.UUID
    user_id: uuid.UUID
    
    # Status fields
    status: int
    is_active: bool
    waitlist_position: Optional[int] = None
    
    # Payment tracking
    reservation_fee_paid: bool
    reservation_fee_paid_date: Optional[datetime] = None
    
    # Notary appointment
    notary_appointment_date: Optional[datetime] = None
    notary_appointment_time: Optional[datetime] = None
    notary_location: Optional[str] = None
    
    # Cancellation
    cancellation_reason: Optional[str] = None
    
    # Related data
    user: Optional[UserBasicInfo] = None
    
    class Config:
        from_attributes = True

class ReservationListResponse(BaseResponseSchema, TimestampMixin):
    """Simplified reservation for list views"""
    property_id: uuid.UUID
    user_id: uuid.UUID
    customer_name: str
    customer_email: Optional[str] = None
    status: int
    is_active: bool
    waitlist_position: Optional[int] = None
    reservation_fee_paid: bool
    user: Optional[UserBasicInfo] = None
    
    class Config:
        from_attributes = True

class ReservationStatusHistoryResponse(BaseResponseSchema):
    """Status history entry"""
    reservation_id: uuid.UUID
    from_status: Optional[int] = None
    to_status: int
    changed_by: uuid.UUID
    changed_at: datetime
    notes: Optional[str] = None
    changed_by_user: Optional[UserBasicInfo] = None
    
    class Config:
        from_attributes = True

class ReservationPromote(BaseSchema):
    """Schema for promoting a waitlist reservation"""
    notes: Optional[str] = None

class ReservationCancel(BaseSchema):
    """Schema for cancelling a reservation"""
    cancellation_reason: Optional[str] = None

class WaitlistReorder(BaseSchema):
    """Schema for reordering waitlist"""
    reservation_ids: List[uuid.UUID] = Field(..., min_items=1)
    
    @validator('reservation_ids')
    def validate_unique_ids(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate reservation IDs not allowed')
        return v