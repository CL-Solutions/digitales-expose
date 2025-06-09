# ================================
# USER PREFERENCES SERVICE (services/user_preferences_service.py)
# ================================

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.user import User
from app.models.user_preferences import UserFilterPreference
from app.schemas.user_preferences import (
    UserFilterPreferenceCreate,
    UserFilterPreferenceUpdate,
    UserFilterPreferenceResponse
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()


class UserPreferencesService:
    """Service for managing user filter preferences"""
    
    @staticmethod
    def get_user_filters(
        db: Session,
        user_id: UUID,
        view_name: str,
        tenant_id: UUID
    ) -> List[UserFilterPreferenceResponse]:
        """Get all filter preferences for a user and view"""
        try:
            filters = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.view_name == view_name,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).order_by(UserFilterPreference.display_order).all()
            
            return [UserFilterPreferenceResponse.model_validate(f) for f in filters]
        
        except Exception as e:
            logger.error(f"Failed to get user filters: {str(e)}")
            raise AppException(
                status_code=500,
                detail="Failed to retrieve filter preferences"
            )
    
    @staticmethod
    def get_default_filter(
        db: Session,
        user_id: UUID,
        view_name: str,
        tenant_id: UUID
    ) -> Optional[UserFilterPreferenceResponse]:
        """Get the default filter for a user and view"""
        try:
            default_filter = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.view_name == view_name,
                    UserFilterPreference.is_default == True,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).first()
            
            return UserFilterPreferenceResponse.model_validate(default_filter) if default_filter else None
        
        except Exception as e:
            logger.error(f"Failed to get default filter: {str(e)}")
            return None
    
    @staticmethod
    def create_filter(
        db: Session,
        user_id: UUID,
        filter_data: UserFilterPreferenceCreate,
        tenant_id: UUID
    ) -> UserFilterPreferenceResponse:
        """Create a new filter preference"""
        try:
            # Check if filter name already exists for this user and view
            existing = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.view_name == filter_data.view_name,
                    UserFilterPreference.filter_name == filter_data.filter_name,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).first()
            
            if existing:
                raise AppException(
                    status_code=409,
                    detail=f"Filter '{filter_data.filter_name}' already exists for this view"
                )
            
            # If this is set as default, unset other defaults
            if filter_data.is_default:
                db.query(UserFilterPreference).filter(
                    and_(
                        UserFilterPreference.user_id == user_id,
                        UserFilterPreference.view_name == filter_data.view_name,
                        UserFilterPreference.tenant_id == tenant_id
                    )
                ).update({UserFilterPreference.is_default: False})
            
            # Create new filter
            new_filter = UserFilterPreference(
                user_id=user_id,
                tenant_id=tenant_id,
                created_by=user_id,
                **filter_data.model_dump()
            )
            
            db.add(new_filter)
            db.commit()
            db.refresh(new_filter)
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="FILTER_CREATE",
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type="user_filter_preference",
                resource_id=new_filter.id,
                new_values=filter_data.model_dump()
            )
            
            return UserFilterPreferenceResponse.model_validate(new_filter)
        
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to create filter: {str(e)}")
            db.rollback()
            raise AppException(
                status_code=500,
                detail="Failed to create filter preference"
            )
    
    @staticmethod
    def update_filter(
        db: Session,
        filter_id: UUID,
        user_id: UUID,
        filter_data: UserFilterPreferenceUpdate,
        tenant_id: UUID
    ) -> UserFilterPreferenceResponse:
        """Update an existing filter preference"""
        try:
            # Get existing filter
            filter_obj = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.id == filter_id,
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).first()
            
            if not filter_obj:
                raise AppException(
                    status_code=404,
                    detail="Filter preference not found"
                )
            
            # Store old values for audit
            old_values = {
                "filter_name": filter_obj.filter_name,
                "filters": filter_obj.filters,
                "is_default": filter_obj.is_default
            }
            
            # If updating to default, unset other defaults
            if filter_data.is_default and not filter_obj.is_default:
                db.query(UserFilterPreference).filter(
                    and_(
                        UserFilterPreference.user_id == user_id,
                        UserFilterPreference.view_name == filter_obj.view_name,
                        UserFilterPreference.tenant_id == tenant_id,
                        UserFilterPreference.id != filter_id
                    )
                ).update({UserFilterPreference.is_default: False})
            
            # Update filter
            update_data = filter_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(filter_obj, key, value)
            
            filter_obj.updated_by = user_id
            
            db.commit()
            db.refresh(filter_obj)
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="FILTER_UPDATE",
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type="user_filter_preference",
                resource_id=filter_obj.id,
                old_values=old_values,
                new_values=update_data
            )
            
            return UserFilterPreferenceResponse.model_validate(filter_obj)
        
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to update filter: {str(e)}")
            db.rollback()
            raise AppException(
                status_code=500,
                detail="Failed to update filter preference"
            )
    
    @staticmethod
    def delete_filter(
        db: Session,
        filter_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Delete a filter preference"""
        try:
            # Get filter
            filter_obj = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.id == filter_id,
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).first()
            
            if not filter_obj:
                raise AppException(
                    status_code=404,
                    detail="Filter preference not found"
                )
            
            # Log activity before deletion
            audit_logger.log_business_event(
                db=db,
                action="FILTER_DELETE",
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type="user_filter_preference",
                resource_id=filter_obj.id,
                old_values={
                    "view_name": filter_obj.view_name,
                    "filter_name": filter_obj.filter_name,
                    "filters": filter_obj.filters
                }
            )
            
            db.delete(filter_obj)
            db.commit()
        
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete filter: {str(e)}")
            db.rollback()
            raise AppException(
                status_code=500,
                detail="Failed to delete filter preference"
            )
    
    @staticmethod
    def set_default_filter(
        db: Session,
        filter_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> UserFilterPreferenceResponse:
        """Set a filter as the default for its view"""
        try:
            # Get filter
            filter_obj = db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.id == filter_id,
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).first()
            
            if not filter_obj:
                raise AppException(
                    status_code=404,
                    detail="Filter preference not found"
                )
            
            # Unset other defaults for this view
            db.query(UserFilterPreference).filter(
                and_(
                    UserFilterPreference.user_id == user_id,
                    UserFilterPreference.view_name == filter_obj.view_name,
                    UserFilterPreference.tenant_id == tenant_id
                )
            ).update({UserFilterPreference.is_default: False})
            
            # Set this filter as default
            filter_obj.is_default = True
            filter_obj.updated_by = user_id
            
            db.commit()
            db.refresh(filter_obj)
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="FILTER_SET_DEFAULT",
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type="user_filter_preference",
                resource_id=filter_obj.id,
                new_values={"is_default": True}
            )
            
            return UserFilterPreferenceResponse.model_validate(filter_obj)
        
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to set default filter: {str(e)}")
            db.rollback()
            raise AppException(
                status_code=500,
                detail="Failed to set default filter"
            )