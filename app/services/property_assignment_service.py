# ================================
# PROPERTY ASSIGNMENT SERVICE
# ================================

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.business import PropertyAssignment, Property
from app.models.user import User
from app.schemas.business import (
    PropertyAssignmentCreate, 
    PropertyAssignmentUpdate,
    PropertyAssignmentResponse,
    PropertyAssignmentBulkCreate
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger

audit_logger = AuditLogger()


class PropertyAssignmentService:
    """Service for managing property assignments to users"""
    
    @staticmethod
    def create_assignment(
        db: Session,
        assignment_data: PropertyAssignmentCreate,
        assigned_by: UUID,
        tenant_id: UUID
    ) -> PropertyAssignment:
        """Create a new property assignment"""
        
        # Verify property exists and belongs to tenant
        property = db.query(Property).filter(
            Property.id == assignment_data.property_id,
            Property.tenant_id == tenant_id
        ).first()
        
        if not property:
            raise AppException("Property not found", 404, "PROPERTY_NOT_FOUND")
        
        # Verify user exists and belongs to tenant
        user = db.query(User).filter(
            User.id == assignment_data.user_id,
            User.tenant_id == tenant_id
        ).first()
        
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        # Check if assignment already exists
        existing = db.query(PropertyAssignment).filter(
            PropertyAssignment.property_id == assignment_data.property_id,
            PropertyAssignment.user_id == assignment_data.user_id,
            PropertyAssignment.tenant_id == tenant_id
        ).first()
        
        if existing:
            raise AppException("Assignment already exists", 400, "ASSIGNMENT_EXISTS")
        
        # Create new assignment
        assignment = PropertyAssignment(
            property_id=assignment_data.property_id,
            user_id=assignment_data.user_id,
            assigned_by=assigned_by,
            tenant_id=tenant_id,
            notes=assignment_data.notes,
            assigned_at=datetime.now(timezone.utc),
            created_by=assigned_by,
            updated_by=assigned_by
        )
        
        db.add(assignment)
        db.flush()
        
        # Audit log
        audit_logger.log_business_event(
            db=db,
            action="PROPERTY_ASSIGNMENT_CREATED",
            user_id=assigned_by,
            tenant_id=tenant_id,
            resource_type="property_assignment",
            resource_id=assignment.id,
            new_values={
                "property_id": str(assignment_data.property_id),
                "user_id": str(assignment_data.user_id),
                "notes": assignment_data.notes
            }
        )
        
        return assignment
    
    @staticmethod
    def bulk_assign_properties(
        db: Session,
        bulk_data: PropertyAssignmentBulkCreate,
        assigned_by: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Bulk assign properties to users"""
        
        created_assignments = []
        failed_assignments = []
        
        # Verify all properties exist and belong to tenant
        properties = db.query(Property).filter(
            Property.id.in_(bulk_data.property_ids),
            Property.tenant_id == tenant_id
        ).all()
        
        property_ids = {str(p.id) for p in properties}
        invalid_properties = [str(pid) for pid in bulk_data.property_ids if str(pid) not in property_ids]
        
        if invalid_properties:
            failed_assignments.extend([
                {"property_id": pid, "reason": "Property not found"} 
                for pid in invalid_properties
            ])
        
        # Verify all users exist and belong to tenant
        users = db.query(User).filter(
            User.id.in_(bulk_data.user_ids),
            User.tenant_id == tenant_id
        ).all()
        
        user_ids = {str(u.id) for u in users}
        invalid_users = [str(uid) for uid in bulk_data.user_ids if str(uid) not in user_ids]
        
        if invalid_users:
            failed_assignments.extend([
                {"user_id": uid, "reason": "User not found"} 
                for uid in invalid_users
            ])
        
        # Create assignments for valid combinations
        for property_id in bulk_data.property_ids:
            if str(property_id) not in property_ids:
                continue
                
            for user_id in bulk_data.user_ids:
                if str(user_id) not in user_ids:
                    continue
                
                # Check if assignment already exists
                existing = db.query(PropertyAssignment).filter(
                    PropertyAssignment.property_id == property_id,
                    PropertyAssignment.user_id == user_id,
                    PropertyAssignment.tenant_id == tenant_id
                ).first()
                
                if existing:
                    failed_assignments.append({
                        "property_id": str(property_id),
                        "user_id": str(user_id),
                        "reason": "Assignment already exists"
                    })
                    continue
                
                # Create assignment
                assignment = PropertyAssignment(
                    property_id=property_id,
                    user_id=user_id,
                    assigned_by=assigned_by,
                    tenant_id=tenant_id,
                    notes=bulk_data.notes,
                    assigned_at=datetime.now(timezone.utc),
                    created_by=assigned_by,
                    updated_by=assigned_by
                )
                
                db.add(assignment)
                created_assignments.append(assignment)
        
        db.flush()
        
        # Audit log for bulk operation
        if created_assignments:
            audit_logger.log_business_event(
                db=db,
                action="PROPERTY_BULK_ASSIGNMENT_CREATED",
                user_id=assigned_by,
                tenant_id=tenant_id,
                resource_type="property_assignment",
                resource_id=None,
                new_values={
                    "total_created": len(created_assignments),
                    "property_ids": [str(pid) for pid in bulk_data.property_ids],
                    "user_ids": [str(uid) for uid in bulk_data.user_ids]
                }
            )
        
        return {
            "created": len(created_assignments),
            "failed": len(failed_assignments),
            "failed_details": failed_assignments
        }
    
    @staticmethod
    def delete_assignment(
        db: Session,
        property_id: UUID,
        user_id: UUID,
        current_user_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete a property assignment"""
        
        assignment = db.query(PropertyAssignment).filter(
            PropertyAssignment.property_id == property_id,
            PropertyAssignment.user_id == user_id,
            PropertyAssignment.tenant_id == tenant_id
        ).first()
        
        if not assignment:
            raise AppException("Assignment not found", 404, "ASSIGNMENT_NOT_FOUND")
        
        # Audit log
        audit_logger.log_business_event(
            db=db,
            action="PROPERTY_ASSIGNMENT_DELETED",
            user_id=current_user_id,
            tenant_id=tenant_id,
            resource_type="property_assignment",
            resource_id=assignment.id,
            old_values={
                "property_id": str(property_id),
                "user_id": str(user_id)
            }
        )
        
        db.delete(assignment)
        db.flush()
        
        return True
    
    @staticmethod
    def get_property_assignments(
        db: Session,
        property_id: UUID,
        tenant_id: UUID
    ) -> List[PropertyAssignment]:
        """Get all assignments for a property"""
        
        # Verify property exists and belongs to tenant
        property = db.query(Property).filter(
            Property.id == property_id,
            Property.tenant_id == tenant_id
        ).first()
        
        if not property:
            raise AppException("Property not found", 404, "PROPERTY_NOT_FOUND")
        
        assignments = db.query(PropertyAssignment).options(
            joinedload(PropertyAssignment.user),
            joinedload(PropertyAssignment.property)
        ).filter(
            PropertyAssignment.property_id == property_id,
            PropertyAssignment.tenant_id == tenant_id
        ).all()
        
        return assignments
    
    @staticmethod
    def get_user_assignments(
        db: Session,
        user_id: UUID,
        tenant_id: UUID,
        include_expired: bool = False
    ) -> List[PropertyAssignment]:
        """Get all property assignments for a user"""
        
        # Verify user exists and belongs to tenant
        user = db.query(User).filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()
        
        if not user:
            raise AppException("User not found", 404, "USER_NOT_FOUND")
        
        query = db.query(PropertyAssignment).options(
            joinedload(PropertyAssignment.property).joinedload(Property.project),
            joinedload(PropertyAssignment.user)
        ).filter(
            PropertyAssignment.user_id == user_id,
            PropertyAssignment.tenant_id == tenant_id
        )
        
        if not include_expired:
            query = query.filter(
                or_(
                    PropertyAssignment.expires_at.is_(None),
                    PropertyAssignment.expires_at > datetime.now(timezone.utc)
                )
            )
        
        assignments = query.all()
        
        return assignments
    
    @staticmethod
    def update_assignment(
        db: Session,
        property_id: UUID,
        user_id: UUID,
        update_data: PropertyAssignmentUpdate,
        current_user_id: UUID,
        tenant_id: UUID
    ) -> PropertyAssignment:
        """Update a property assignment"""
        
        assignment = db.query(PropertyAssignment).filter(
            PropertyAssignment.property_id == property_id,
            PropertyAssignment.user_id == user_id,
            PropertyAssignment.tenant_id == tenant_id
        ).first()
        
        if not assignment:
            raise AppException("Assignment not found", 404, "ASSIGNMENT_NOT_FOUND")
        
        # Store old values for audit
        old_values = {
            "notes": assignment.notes,
            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None
        }
        
        # Update fields
        new_values = {}
        if update_data.notes is not None:
            assignment.notes = update_data.notes
            new_values["notes"] = update_data.notes
            
        if update_data.expires_at is not None:
            assignment.expires_at = update_data.expires_at
            new_values["expires_at"] = update_data.expires_at.isoformat()
        
        assignment.updated_at = datetime.now(timezone.utc)
        assignment.updated_by = current_user_id
        
        db.flush()
        
        # Audit log
        if new_values:
            audit_logger.log_business_event(
                db=db,
                action="PROPERTY_ASSIGNMENT_UPDATED",
                user_id=current_user_id,
                tenant_id=tenant_id,
                resource_type="property_assignment",
                resource_id=assignment.id,
                old_values=old_values,
                new_values=new_values
            )
        
        return assignment