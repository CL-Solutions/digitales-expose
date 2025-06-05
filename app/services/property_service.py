# ================================
# PROPERTY SERVICE (services/property_service.py)
# ================================

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.models.business import Property, PropertyImage, City
from app.models.user import User
from app.schemas.business import (
    PropertyCreate, PropertyUpdate, PropertyFilter,
    PropertyImageCreate, PropertyImageUpdate
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from app.services.rbac_service import RBACService
from decimal import Decimal

audit_logger = AuditLogger()

class PropertyService:
    """Service for managing properties"""
    
    @staticmethod
    def create_property(
        db: Session,
        property_data: PropertyCreate,
        current_user: User
    ) -> Property:
        """Create a new property"""
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "properties:create" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to create properties"
                    )
            
            
            # Create property
            property_dict = property_data.model_dump()
            property = Property(
                **property_dict,
                tenant_id=current_user.tenant_id,
                created_by=current_user.id
            )
            
            db.add(property)
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action="CREATE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                details={
                    "street": property.street,
                    "house_number": property.house_number,
                    "apartment_number": property.apartment_number,
                    "city": property.city
                }
            )
            
            return property
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to create property: {str(e)}"
            )
    
    @staticmethod
    def get_property(
        db: Session,
        property_id: UUID,
        current_user: User
    ) -> Property:
        """Get a single property by ID"""
        try:
            query = db.query(Property).options(
                joinedload(Property.images),
                joinedload(Property.city_ref)
            )
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(Property.tenant_id == current_user.tenant_id)
            
            property = query.filter(Property.id == property_id).first()
            
            if not property:
                raise AppException(
                    status_code=404,
                    detail="Property not found"
                )
            
            return property
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to retrieve property: {str(e)}"
            )
    
    @staticmethod
    def list_properties(
        db: Session,
        current_user: User,
        filter_params: PropertyFilter
    ) -> Dict[str, Any]:
        """List properties with filtering and pagination"""
        try:
            query = db.query(Property)
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(Property.tenant_id == current_user.tenant_id)
            
            # Apply filters
            if filter_params.city:
                query = query.filter(Property.city.ilike(f"%{filter_params.city}%"))
            
            if filter_params.state:
                query = query.filter(Property.state.ilike(f"%{filter_params.state}%"))
            
            if filter_params.property_type:
                query = query.filter(Property.property_type == filter_params.property_type)
            
            if filter_params.status:
                query = query.filter(Property.status == filter_params.status)
            
            if filter_params.min_price:
                query = query.filter(Property.purchase_price >= filter_params.min_price)
            
            if filter_params.max_price:
                query = query.filter(Property.purchase_price <= filter_params.max_price)
            
            if filter_params.min_size:
                query = query.filter(Property.size_sqm >= filter_params.min_size)
            
            if filter_params.max_size:
                query = query.filter(Property.size_sqm <= filter_params.max_size)
            
            if filter_params.min_rooms:
                query = query.filter(Property.rooms >= filter_params.min_rooms)
            
            if filter_params.max_rooms:
                query = query.filter(Property.rooms <= filter_params.max_rooms)
            
            if filter_params.energy_class:
                query = query.filter(Property.energy_class == filter_params.energy_class)
            
            # Apply Investagon status filters
            if filter_params.active is not None:
                query = query.filter(Property.active == filter_params.active)
            
            if filter_params.pre_sale is not None:
                query = query.filter(Property.pre_sale == filter_params.pre_sale)
            
            if filter_params.draft is not None:
                query = query.filter(Property.draft == filter_params.draft)
            
            # Get total count
            total = query.count()
            
            # Apply sorting
            sort_field = getattr(Property, filter_params.sort_by, Property.created_at)
            if filter_params.sort_order == "desc":
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
            
            # Apply pagination
            offset = (filter_params.page - 1) * filter_params.page_size
            properties = query.offset(offset).limit(filter_params.page_size).all()
            
            return {
                "items": properties,
                "total": total,
                "page": filter_params.page,
                "size": filter_params.page_size,
                "pages": (total + filter_params.page_size - 1) // filter_params.page_size
            }
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to list properties: {str(e)}"
            )
    
    @staticmethod
    def update_property(
        db: Session,
        property_id: UUID,
        property_data: PropertyUpdate,
        current_user: User
    ) -> Property:
        """Update a property"""
        try:
            property = PropertyService.get_property(db, property_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "properties:update" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to update properties"
                    )
            
            # Update fields
            update_data = property_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(property, field, value)
            
            property.updated_by = current_user.id
            property.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action="UPDATE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                details={"updated_fields": list(update_data.keys())}
            )
            
            return property
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to update property: {str(e)}"
            )
    
    @staticmethod
    def delete_property(
        db: Session,
        property_id: UUID,
        current_user: User
    ) -> None:
        """Delete a property"""
        try:
            property = PropertyService.get_property(db, property_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "properties:delete" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to delete properties"
                    )
            
            # Log activity before deletion
            audit_logger.log_event(
                db=db,
                action="DELETE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                details={
                    "street": property.street,
                    "house_number": property.house_number,
                    "apartment_number": property.apartment_number,
                    "city": property.city
                }
            )
            
            db.delete(property)
            db.flush()
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to delete property: {str(e)}"
            )
    
    @staticmethod
    def add_property_image(
        db: Session,
        property_id: UUID,
        image_data: PropertyImageCreate,
        current_user: User
    ) -> PropertyImage:
        """Add an image to a property"""
        try:
            property = PropertyService.get_property(db, property_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "images:upload" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to upload images"
                    )
            
            # Create image record
            image = PropertyImage(
                property_id=property.id,
                tenant_id=property.tenant_id,
                created_by=current_user.id,
                **image_data.model_dump()
            )
            
            db.add(image)
            db.flush()
            
            return image
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to add property image: {str(e)}"
            )
    
    @staticmethod
    def update_property_image(
        db: Session,
        property_id: UUID,
        image_id: UUID,
        image_data: PropertyImageUpdate,
        current_user: User
    ) -> PropertyImage:
        """Update a property image"""
        try:
            # Get property to ensure access
            property = PropertyService.get_property(db, property_id, current_user)
            
            # Get image
            image = db.query(PropertyImage).filter(
                and_(
                    PropertyImage.id == image_id,
                    PropertyImage.property_id == property.id
                )
            ).first()
            
            if not image:
                raise AppException(
                    status_code=404,
                    detail="Image not found"
                )
            
            # Update fields
            update_data = image_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(image, field, value)
            
            image.updated_by = current_user.id
            image.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            return image
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to update property image: {str(e)}"
            )
    
    @staticmethod
    def delete_property_image(
        db: Session,
        property_id: UUID,
        image_id: UUID,
        current_user: User
    ) -> None:
        """Delete a property image"""
        try:
            # Get property to ensure access
            property = PropertyService.get_property(db, property_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "images:delete" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to delete images"
                    )
            
            # Get image
            image = db.query(PropertyImage).filter(
                and_(
                    PropertyImage.id == image_id,
                    PropertyImage.property_id == property.id
                )
            ).first()
            
            if not image:
                raise AppException(
                    status_code=404,
                    detail="Image not found"
                )
            
            # TODO: Delete from S3 when implemented
            
            db.delete(image)
            db.flush()
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to delete property image: {str(e)}"
            )
    
    @staticmethod
    def get_property_stats(
        db: Session,
        current_user: User
    ) -> Dict[str, Any]:
        """Get property statistics for the tenant"""
        try:
            query = db.query(Property)
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(Property.tenant_id == current_user.tenant_id)
            
            total_properties = query.count()
            available_properties = query.filter(Property.status == "available").count()
            reserved_properties = query.filter(Property.status == "reserved").count()
            sold_properties = query.filter(Property.status == "sold").count()
            
            # Get value statistics
            total_value = db.query(func.sum(Property.purchase_price)).filter(
                Property.tenant_id == current_user.tenant_id
            ).scalar() or Decimal('0')
            
            avg_price = db.query(func.avg(Property.purchase_price)).filter(
                Property.tenant_id == current_user.tenant_id
            ).scalar() or Decimal('0')
            
            return {
                "total_properties": total_properties,
                "available_properties": available_properties,
                "reserved_properties": reserved_properties,
                "sold_properties": sold_properties,
                "total_portfolio_value": float(total_value),
                "average_property_price": float(avg_price),
                "properties_by_type": PropertyService._get_properties_by_type(db, query),
                "properties_by_city": PropertyService._get_properties_by_city(db, query)
            }
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to get property statistics: {str(e)}"
            )
    
    @staticmethod
    def _get_properties_by_type(db: Session, base_query) -> List[Dict[str, Any]]:
        """Get property count by type"""
        results = base_query.with_entities(
            Property.property_type,
            func.count(Property.id).label('count')
        ).group_by(Property.property_type).all()
        
        return [{"type": r[0], "count": r[1]} for r in results]
    
    @staticmethod
    def _get_properties_by_city(db: Session, base_query) -> List[Dict[str, Any]]:
        """Get property count by city"""
        results = base_query.with_entities(
            Property.city,
            func.count(Property.id).label('count')
        ).group_by(Property.city).order_by(func.count(Property.id).desc()).limit(10).all()
        
        return [{"city": r[0], "count": r[1]} for r in results]