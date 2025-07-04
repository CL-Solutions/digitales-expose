# ================================
# RESERVATION SERVICE (services/reservation_service.py)
# ================================

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
import uuid

from app.models.business import Reservation, ReservationStatusHistory, Property
from app.models.user import User
from app.schemas.reservation import (
    ReservationCreate, ReservationUpdate, ReservationStatusUpdate,
    ReservationResponse, ReservationListResponse, ReservationStatusHistoryResponse,
    ReservationPromote, ReservationCancel, WaitlistReorder
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger

audit_logger = AuditLogger()

class ReservationService:
    """Service for managing property reservations"""
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        1: [5],  # Frei → Angefragt
        5: [6, 1],  # Angefragt → Reserviert or back to Frei
        6: [9, 1],  # Reserviert → Notarvorbereitung or back to Frei
        9: [7, 1],  # Notarvorbereitung → Notartermin or back to Frei
        7: [0, 1],  # Notartermin → Verkauft or back to Frei
        0: []  # Verkauft is final
    }
    
    @staticmethod
    def create_reservation(
        db: Session,
        property_id: uuid.UUID,
        data: ReservationCreate,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Reservation:
        """Create a new reservation or add to waitlist"""
        
        # Get property
        property = db.query(Property).filter(
            Property.id == property_id,
            Property.tenant_id == tenant_id
        ).first()
        
        if not property:
            raise AppException("Property not found", 404)
        
        # Check if property is available for reservation
        if property.active not in [1, 5, 6, 7, 9]:  # Not Verkauft
            # Check for active reservations
            active_reservation = db.query(Reservation).filter(
                Reservation.property_id == property_id,
                Reservation.is_active == True,
                Reservation.tenant_id == tenant_id
            ).first()
            
            # Determine if this will be active or waitlist
            is_active = active_reservation is None
            waitlist_position = None
            
            if not is_active:
                # Get next waitlist position
                max_position = db.query(func.max(Reservation.waitlist_position)).filter(
                    Reservation.property_id == property_id,
                    Reservation.is_active == False,
                    Reservation.tenant_id == tenant_id
                ).scalar() or 0
                waitlist_position = max_position + 1
            
            # Create reservation
            reservation = Reservation(
                **data.model_dump(),
                property_id=property_id,
                user_id=user_id,
                tenant_id=tenant_id,
                status=5,  # Angefragt
                is_active=is_active,
                waitlist_position=waitlist_position,
                created_by=user_id
            )
            
            db.add(reservation)
            
            # Update property status if this is the active reservation
            if is_active:
                property.active = 5  # Angefragt
                
                # Create initial status history
                history = ReservationStatusHistory(
                    reservation_id=reservation.id,
                    from_status=None,
                    to_status=5,
                    changed_by=user_id,
                    tenant_id=tenant_id,
                    notes="Reservation created"
                )
                db.add(history)
            
            # Log the event
            audit_logger.log_business_event(
                db=db,
                action="RESERVATION_CREATED",
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type="reservation",
                resource_id=reservation.id,
                new_values={
                    "property_id": str(property_id),
                    "customer_name": data.customer_name,
                    "is_active": is_active,
                    "waitlist_position": waitlist_position
                }
            )
            
            db.commit()
            db.refresh(reservation)
            
            return reservation
        else:
            raise AppException("Property is already sold", 400)
    
    @staticmethod
    def get_reservation(
        db: Session,
        reservation_id: uuid.UUID,
        user: User,
        tenant_id: uuid.UUID
    ) -> Reservation:
        """Get reservation by ID with permission check"""
        
        query = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id
        ).options(
            selectinload(Reservation.user),
            selectinload(Reservation.property),
            selectinload(Reservation.status_history).selectinload(ReservationStatusHistory.changed_by_user)
        )
        
        # Check permissions
        if not user.is_super_admin:
            # Check if user has reservation management permission
            user_permissions = {f"{rp.permission.resource}:{rp.permission.action}" 
                               for ur in user.user_roles 
                               for rp in ur.role.role_permissions}
            
            if "reservations:manage" not in user_permissions:
                # Sales people can only see their own reservations
                query = query.filter(Reservation.user_id == user.id)
        
        reservation = query.first()
        
        if not reservation:
            raise AppException("Reservation not found", 404)
        
        return reservation
    
    @staticmethod
    def list_reservations(
        db: Session,
        user: User,
        tenant_id: uuid.UUID,
        property_id: Optional[uuid.UUID] = None,
        status: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Reservation], int]:
        """List reservations with role-based filtering"""
        
        query = db.query(Reservation).filter(
            Reservation.tenant_id == tenant_id
        ).options(
            selectinload(Reservation.user),
            selectinload(Reservation.property)
        )
        
        # Apply filters
        if property_id:
            query = query.filter(Reservation.property_id == property_id)
        if status is not None:
            query = query.filter(Reservation.status == status)
        if is_active is not None:
            query = query.filter(Reservation.is_active == is_active)
        
        # Check permissions for visibility
        if not user.is_super_admin:
            user_permissions = {f"{rp.permission.resource}:{rp.permission.action}" 
                               for ur in user.user_roles 
                               for rp in ur.role.role_permissions}
            
            if "reservations:manage" not in user_permissions:
                # Check if user is a location manager
                team_member_ids = []
                for assignment in user.managed_team_members:
                    team_member_ids.append(assignment.member_id)
                
                if team_member_ids:
                    # Location managers see their team's reservations
                    query = query.filter(
                        or_(
                            Reservation.user_id == user.id,
                            Reservation.user_id.in_(team_member_ids)
                        )
                    )
                else:
                    # Sales people only see their own
                    query = query.filter(Reservation.user_id == user.id)
        
        # Order by active status first, then waitlist position
        query = query.order_by(
            Reservation.is_active.desc(),
            Reservation.waitlist_position.asc().nullsfirst(),
            Reservation.created_at.desc()
        )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        reservations = query.offset(skip).limit(limit).all()
        
        return reservations, total
    
    @staticmethod
    def update_reservation(
        db: Session,
        reservation_id: uuid.UUID,
        data: ReservationUpdate,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Reservation:
        """Update reservation details"""
        
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id
        ).first()
        
        if not reservation:
            raise AppException("Reservation not found", 404)
        
        # Store old values for audit
        old_values = {}
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(reservation, field):
                old_values[field] = getattr(reservation, field)
                setattr(reservation, field, value)
        
        reservation.updated_by = user_id
        reservation.updated_at = datetime.now(timezone.utc)
        
        # Log the update
        audit_logger.log_business_event(
            db=db,
            action="RESERVATION_UPDATED",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="reservation",
            resource_id=reservation_id,
            old_values=old_values,
            new_values=update_data
        )
        
        db.commit()
        db.refresh(reservation)
        
        return reservation
    
    @staticmethod
    def update_reservation_status(
        db: Session,
        reservation_id: uuid.UUID,
        data: ReservationStatusUpdate,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Reservation:
        """Update reservation status with validation"""
        
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id,
            Reservation.is_active == True  # Only active reservations can change status
        ).options(
            selectinload(Reservation.property)
        ).first()
        
        if not reservation:
            raise AppException(404, "Active reservation not found")
        
        # Validate transition
        if data.status not in ReservationService.VALID_TRANSITIONS.get(reservation.status, []):
            raise AppException(f"Invalid status transition from {reservation.status} to {data.status}", 400)
        
        # Store old status
        old_status = reservation.status
        
        # Update status
        reservation.status = data.status
        
        # Handle status-specific requirements
        if data.status == 6:  # Reserviert
            reservation.reservation_fee_paid = data.reservation_fee_paid
            reservation.reservation_fee_paid_date = data.reservation_fee_paid_date or datetime.now(timezone.utc)
        
        elif data.status == 7:  # Notartermin
            reservation.notary_appointment_date = data.notary_appointment_date
            reservation.notary_appointment_time = data.notary_appointment_time
            if data.notary_location:
                reservation.notary_location = data.notary_location
        
        # Update property status
        reservation.property.active = data.status
        
        # Create status history
        history = ReservationStatusHistory(
            reservation_id=reservation_id,
            from_status=old_status,
            to_status=data.status,
            changed_by=user_id,
            tenant_id=tenant_id,
            notes=data.notes
        )
        db.add(history)
        
        reservation.updated_by = user_id
        reservation.updated_at = datetime.now(timezone.utc)
        
        # Log the status change
        audit_logger.log_business_event(
            db=db,
            action="RESERVATION_STATUS_CHANGED",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="reservation",
            resource_id=reservation_id,
            old_values={"status": old_status},
            new_values={"status": data.status}
        )
        
        db.commit()
        db.refresh(reservation)
        
        return reservation
    
    @staticmethod
    def promote_reservation(
        db: Session,
        reservation_id: uuid.UUID,
        data: ReservationPromote,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> Reservation:
        """Promote a waitlist reservation to active"""
        
        # Get the reservation to promote
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id,
            Reservation.is_active == False  # Must be on waitlist
        ).options(
            selectinload(Reservation.property)
        ).first()
        
        if not reservation:
            raise AppException("Waitlist reservation not found", 404)
        
        # Get current active reservation
        active_reservation = db.query(Reservation).filter(
            Reservation.property_id == reservation.property_id,
            Reservation.tenant_id == tenant_id,
            Reservation.is_active == True
        ).first()
        
        if active_reservation:
            # Move active to waitlist position 1
            active_reservation.is_active = False
            active_reservation.waitlist_position = 1
            active_reservation.status = 5  # Reset to Angefragt
            
            # Shift other waitlist positions
            db.query(Reservation).filter(
                Reservation.property_id == reservation.property_id,
                Reservation.tenant_id == tenant_id,
                Reservation.is_active == False,
                Reservation.waitlist_position < reservation.waitlist_position,
                Reservation.id != reservation_id
            ).update({
                Reservation.waitlist_position: Reservation.waitlist_position + 1
            })
        
        # Promote the reservation
        reservation.is_active = True
        reservation.waitlist_position = None
        
        # Update property status
        reservation.property.active = reservation.status
        
        # Create status history
        history = ReservationStatusHistory(
            reservation_id=reservation_id,
            from_status=None,
            to_status=reservation.status,
            changed_by=user_id,
            tenant_id=tenant_id,
            notes=f"Promoted from waitlist. {data.notes or ''}"
        )
        db.add(history)
        
        # Log the promotion
        audit_logger.log_business_event(
            db=db,
            action="RESERVATION_PROMOTED",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="reservation",
            resource_id=reservation_id,
            new_values={"promoted_to_active": True}
        )
        
        db.commit()
        db.refresh(reservation)
        
        return reservation
    
    @staticmethod
    def cancel_reservation(
        db: Session,
        reservation_id: uuid.UUID,
        data: ReservationCancel,
        user: User,
        tenant_id: uuid.UUID
    ) -> None:
        """Cancel a reservation"""
        
        reservation = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.tenant_id == tenant_id
        ).options(
            selectinload(Reservation.property)
        ).first()
        
        if not reservation:
            raise AppException("Reservation not found", 404)
        
        # Check permissions
        user_permissions = {f"{rp.permission.resource}:{rp.permission.action}" 
                           for ur in user.user_roles 
                           for rp in ur.role.role_permissions}
        
        # Sales people can only cancel their own reservations
        if "reservations:manage" not in user_permissions and reservation.user_id != user.id:
            raise AppException("You can only cancel your own reservations", 403)
        
        # Don't allow cancelling sold properties
        if reservation.status == 0:
            raise AppException("Cannot cancel a sold property", 400)
        
        # Store cancellation reason
        reservation.cancellation_reason = data.cancellation_reason
        
        # If this was the active reservation, activate next in waitlist
        if reservation.is_active:
            # Get next waitlist reservation
            next_reservation = db.query(Reservation).filter(
                Reservation.property_id == reservation.property_id,
                Reservation.tenant_id == tenant_id,
                Reservation.is_active == False,
                Reservation.waitlist_position == 1
            ).first()
            
            if next_reservation:
                # Promote next reservation
                next_reservation.is_active = True
                next_reservation.waitlist_position = None
                
                # Update property status
                reservation.property.active = next_reservation.status
                
                # Shift remaining waitlist positions
                db.query(Reservation).filter(
                    Reservation.property_id == reservation.property_id,
                    Reservation.tenant_id == tenant_id,
                    Reservation.is_active == False,
                    Reservation.waitlist_position > 1
                ).update({
                    Reservation.waitlist_position: Reservation.waitlist_position - 1
                })
            else:
                # No waitlist, property becomes available
                reservation.property.active = 1  # Frei
        else:
            # Just shift waitlist positions
            db.query(Reservation).filter(
                Reservation.property_id == reservation.property_id,
                Reservation.tenant_id == tenant_id,
                Reservation.is_active == False,
                Reservation.waitlist_position > reservation.waitlist_position
            ).update({
                Reservation.waitlist_position: Reservation.waitlist_position - 1
            })
        
        # Create final status history
        history = ReservationStatusHistory(
            reservation_id=reservation_id,
            from_status=reservation.status,
            to_status=1,  # Cancelled = Frei
            changed_by=user.id,
            tenant_id=tenant_id,
            notes=f"Cancelled. {data.cancellation_reason or ''}"
        )
        db.add(history)
        
        # Log the cancellation
        audit_logger.log_business_event(
            db=db,
            action="RESERVATION_CANCELLED",
            user_id=user.id,
            tenant_id=tenant_id,
            resource_type="reservation",
            resource_id=reservation_id,
            new_values={"cancellation_reason": data.cancellation_reason}
        )
        
        # Delete the reservation
        db.delete(reservation)
        db.commit()
    
    @staticmethod
    def reorder_waitlist(
        db: Session,
        property_id: uuid.UUID,
        data: WaitlistReorder,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> List[Reservation]:
        """Reorder waitlist for a property"""
        
        # Verify all reservations exist and are on waitlist
        reservations = db.query(Reservation).filter(
            Reservation.id.in_(data.reservation_ids),
            Reservation.property_id == property_id,
            Reservation.tenant_id == tenant_id,
            Reservation.is_active == False
        ).all()
        
        if len(reservations) != len(data.reservation_ids):
            raise AppException("Invalid reservation IDs", 400)
        
        # Update positions based on order in list
        for position, reservation_id in enumerate(data.reservation_ids, 1):
            reservation = next(r for r in reservations if r.id == reservation_id)
            reservation.waitlist_position = position
        
        # Log the reorder
        audit_logger.log_business_event(
            db=db,
            action="WAITLIST_REORDERED",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="property",
            resource_id=property_id,
            new_values={"new_order": [str(id) for id in data.reservation_ids]}
        )
        
        db.commit()
        
        # Return updated reservations
        return db.query(Reservation).filter(
            Reservation.property_id == property_id,
            Reservation.tenant_id == tenant_id,
            Reservation.is_active == False
        ).order_by(Reservation.waitlist_position).all()
    
    @staticmethod
    def get_reservation_history(
        db: Session,
        reservation_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> List[ReservationStatusHistory]:
        """Get status history for a reservation"""
        
        return db.query(ReservationStatusHistory).filter(
            ReservationStatusHistory.reservation_id == reservation_id,
            ReservationStatusHistory.tenant_id == tenant_id
        ).options(
            selectinload(ReservationStatusHistory.changed_by_user)
        ).order_by(
            ReservationStatusHistory.changed_at.desc()
        ).all()