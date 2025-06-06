# ================================
# CITY SERVICE (services/city_service.py)
# ================================

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.models.business import City, CityImage
from app.models.user import User
from app.schemas.business import (
    CityCreate, CityUpdate,
    CityImageSchema
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from app.services.rbac_service import RBACService

audit_logger = AuditLogger()

class CityService:
    """Service for managing city data"""
    
    @staticmethod
    def create_city(
        db: Session,
        city_data: CityCreate,
        current_user: User
    ) -> City:
        """Create a new city"""
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "cities:create" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to create cities"
                    )
            
            # Check if city already exists in tenant
            existing = db.query(City).filter(
                and_(
                    City.name == city_data.name,
                    City.state == city_data.state,
                    City.tenant_id == current_user.tenant_id
                )
            ).first()
            
            if existing:
                raise AppException(
                    status_code=400,
                    detail="City already exists in this state"
                )
            
            # Create city
            city = City(
                **city_data.model_dump(),
                tenant_id=current_user.tenant_id,
                created_by=current_user.id
            )
            
            db.add(city)
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action="CREATE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="city",
                resource_id=city.id,
                details={"city": f"{city.name}, {city.state}"}
            )
            
            return city
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to create city: {str(e)}"
            )
    
    @staticmethod
    def get_city(
        db: Session,
        city_id: UUID,
        current_user: User
    ) -> City:
        """Get a single city by ID"""
        try:
            query = db.query(City).options(
                joinedload(City.images)
            )
            
            # Apply tenant filter
            # Always filter by tenant_id (which is set to impersonated tenant when impersonating)
            query = query.filter(City.tenant_id == current_user.tenant_id)
            
            city = query.filter(City.id == city_id).first()
            
            if not city:
                raise AppException(
                    status_code=404,
                    detail="City not found"
                )
            
            return city
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to retrieve city: {str(e)}"
            )
    
    @staticmethod
    def get_city_by_name(
        db: Session,
        city_name: str,
        state: str,
        current_user: User
    ) -> Optional[City]:
        """Get a city by name and state"""
        try:
            query = db.query(City).options(
                joinedload(City.images)
            )
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(City.tenant_id == current_user.tenant_id)
            
            city = query.filter(
                and_(
                    City.name == city_name,
                    City.state == state
                )
            ).first()
            
            return city
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to retrieve city: {str(e)}"
            )
    
    @staticmethod
    def list_cities(
        db: Session,
        current_user: User,
        state: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[City]:
        """List cities with optional filtering"""
        try:
            query = db.query(City).options(
                joinedload(City.images)
            )
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(City.tenant_id == current_user.tenant_id)
            
            if state:
                query = query.filter(City.state == state)
            
            if search:
                query = query.filter(
                    City.name.ilike(f"%{search}%")
                )
            
            # Order by state and name
            cities = query.order_by(City.state, City.name).all()
            
            return cities
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to list cities: {str(e)}"
            )
    
    @staticmethod
    def update_city(
        db: Session,
        city_id: UUID,
        city_data: CityUpdate,
        current_user: User
    ) -> City:
        """Update a city"""
        try:
            city = CityService.get_city(db, city_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "cities:update" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to update cities"
                    )
            
            # Update fields
            update_data = city_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(city, field, value)
            
            city.updated_by = current_user.id
            city.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action="UPDATE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="city",
                resource_id=city.id,
                details={"updated_fields": list(update_data.keys())}
            )
            
            return city
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to update city: {str(e)}"
            )
    
    @staticmethod
    def delete_city(
        db: Session,
        city_id: UUID,
        current_user: User
    ) -> None:
        """Delete a city"""
        try:
            city = CityService.get_city(db, city_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "cities:delete" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to delete cities"
                    )
            
            # Check if any properties reference this city
            from app.models.business import Property
            property_count = db.query(Property).filter(
                and_(
                    Property.city == city.name,
                    Property.tenant_id == city.tenant_id
                )
            ).count()
            
            if property_count > 0:
                raise AppException(
                    status_code=400,
                    detail=f"Cannot delete city: {property_count} properties reference this city"
                )
            
            # Log activity before deletion
            audit_logger.log_event(
                db=db,
                action="DELETE",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="city",
                resource_id=city.id,
                details={"city": f"{city.name}, {city.state}"}
            )
            
            db.delete(city)
            db.flush()
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to delete city: {str(e)}"
            )
    
    @staticmethod
    def add_city_image(
        db: Session,
        city_id: UUID,
        image_url: str,
        image_type: str,
        title: Optional[str],
        description: Optional[str],
        display_order: int,
        current_user: User
    ) -> CityImage:
        """Add an image to a city"""
        try:
            city = CityService.get_city(db, city_id, current_user)
            
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
            image = CityImage(
                city_id=city.id,
                tenant_id=city.tenant_id,
                image_url=image_url,
                image_type=image_type,
                title=title,
                description=description,
                display_order=display_order,
                created_by=current_user.id
            )
            
            db.add(image)
            db.flush()
            
            return image
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to add city image: {str(e)}"
            )
    
    @staticmethod
    def delete_city_image(
        db: Session,
        city_id: UUID,
        image_id: UUID,
        current_user: User
    ) -> None:
        """Delete a city image"""
        try:
            # Get city to ensure access
            city = CityService.get_city(db, city_id, current_user)
            
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
            image = db.query(CityImage).filter(
                and_(
                    CityImage.id == image_id,
                    CityImage.city_id == city.id
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
                detail=f"Failed to delete city image: {str(e)}"
            )
    
    @staticmethod
    def get_cities_with_properties(
        db: Session,
        current_user: User,
        tenant_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get cities that have properties"""
        try:
            from app.models.business import Property
            
            # Base query for properties
            property_query = db.query(
                Property.city,
                Property.state,
                func.count(Property.id).label('property_count')
            ).filter(
                Property.status == 'available'
            )
            
            # Apply tenant filter
            # Use the tenant_id from request context (handles impersonation)
            effective_tenant_id = tenant_id if tenant_id else current_user.tenant_id
            property_query = property_query.filter(
                Property.tenant_id == effective_tenant_id
            )
            
            # Group by city and state
            city_property_counts = property_query.group_by(
                Property.city,
                Property.state
            ).all()
            
            # Get city details for each unique city
            result = []
            for city_name, state, property_count in city_property_counts:
                city = CityService.get_city_by_name(db, city_name, state, current_user)
                
                city_data = {
                    "city_name": city_name,
                    "state": state,
                    "property_count": property_count
                }
                
                if city:
                    city_data.update({
                        "city_id": str(city.id),
                        "population": city.population,
                        "population_growth": city.population_growth,
                        "average_income": city.average_income,
                        "has_details": True
                    })
                else:
                    city_data["has_details"] = False
                
                result.append(city_data)
            
            # Sort by property count
            result.sort(key=lambda x: x["property_count"], reverse=True)
            
            return result
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to get cities with properties: {str(e)}"
            )