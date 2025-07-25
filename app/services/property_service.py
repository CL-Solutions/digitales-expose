# ================================
# PROPERTY SERVICE (services/property_service.py)
# ================================

from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from app.models.business import Property, PropertyImage, City, Project
from app.models.user import User
from app.schemas.business import (
    PropertyCreate, PropertyUpdate, PropertyFilter,
    PropertyImageCreate, PropertyImageUpdate,
    PropertyAggregateStats, RangeStats
)
from app.core.exceptions import AppException
from app.utils.audit import AuditLogger
from app.services.rbac_service import RBACService
from decimal import Decimal
from app.mappers.property_mapper import map_property_to_overview
import logging

logger = logging.getLogger(__name__)
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
            
            
            # Verify project exists
            from app.models.business import Project
            project = db.query(Project).filter(
                and_(
                    Project.id == property_data.project_id,
                    Project.tenant_id == current_user.tenant_id
                )
            ).first()
            
            if not project:
                raise AppException(
                    status_code=404,
                    detail="Project not found"
                )
            
            # Create property with denormalized location data from project
            property_dict = property_data.model_dump()
            # Remove location fields that will come from project to avoid duplicate arguments
            property_dict.pop('city', None)
            property_dict.pop('state', None)
            property_dict.pop('zip_code', None)
            property_dict.pop('city_id', None)
            
            property = Property(
                **property_dict,
                # Denormalize location data from project
                city=project.city,
                state=project.state,
                zip_code=project.zip_code,
                city_id=project.city_id,
                tenant_id=current_user.tenant_id,
                created_by=current_user.id
            )
            
            db.add(property)
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="PROPERTY_CREATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                new_values={
                    "project_id": str(property.project_id),
                    "unit_number": property.unit_number,
                    "city": property.city
                }
            )
            
            # Update project status based on properties
            from app.services.project_service import ProjectService
            ProjectService.update_project_status_from_properties(
                db=db,
                project_id=property.project_id,
                tenant_id=current_user.tenant_id
            )
            
            # Update project aggregates (price and rental yield ranges)
            ProjectService.update_project_aggregates(
                db=db,
                project_id=property.project_id,
                tenant_id=current_user.tenant_id
            )
            
            # Commit and refresh with relationships
            db.commit()
            db.refresh(property)
            
            # Load relationships for proper response
            from sqlalchemy.orm import joinedload
            property = db.query(Property).options(
                joinedload(Property.images),
                joinedload(Property.city_ref).joinedload(City.images),
                joinedload(Property.project).joinedload(Project.images),
                joinedload(Property.project).joinedload(Project.city_ref)
            ).filter(Property.id == property.id).first()
            
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
                joinedload(Property.city_ref).joinedload(City.images),
                joinedload(Property.project).joinedload(Project.images),
                joinedload(Property.project).joinedload(Project.city_ref)
            )
            
            # Apply tenant filter
            # Always filter by tenant_id (which is set to impersonated tenant when impersonating)
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
        filter_params: PropertyFilter,
        tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """List properties with filtering and pagination"""
        try:
            # Query with images and project eagerly loaded for thumbnail and name
            # Using subqueryload to avoid pagination issues with joins
            query = db.query(Property).options(
                subqueryload(Property.images),
                subqueryload(Property.project).subqueryload(Project.images)
            )
            
            # Apply tenant filter
            # Use the tenant_id from request context (handles impersonation)
            effective_tenant_id = tenant_id if tenant_id else current_user.tenant_id
            query = query.filter(Property.tenant_id == effective_tenant_id)
            
            # Apply visibility filter based on user role and assignments
            # Visibility levels:
            # -1: Hidden/Deactivated (visible to admins and property managers)
            #  0: In progress/Draft (visible to admins and property managers)
            #  1: Active/Published (visible to all users including sales people)
            if not current_user.is_super_admin:
                # Check if user has can_see_all_properties flag
                if current_user.can_see_all_properties:
                    # User can see all properties - no filter needed
                    pass
                else:
                    # Get user permissions to check role
                    permissions = RBACService.get_user_permissions(
                        db, current_user.id, current_user.tenant_id
                    )
                    permission_names = [p["name"] for p in permissions.get("permissions", [])]
                    
                    # Check if user is tenant_admin or property_manager
                    # These roles typically have properties:update permission
                    is_admin_or_manager = "properties:update" in permission_names
                    
                    if not is_admin_or_manager:
                        # Sales people need to check assignments
                        from app.models.business import PropertyAssignment
                        
                        # Get properties assigned to this user
                        assigned_property_ids = db.query(PropertyAssignment.property_id).filter(
                            PropertyAssignment.user_id == current_user.id,
                            PropertyAssignment.tenant_id == effective_tenant_id
                        ).subquery()
                        
                        # User can ONLY see properties explicitly assigned to them
                        query = query.filter(
                            Property.id.in_(assigned_property_ids)
                        )
                    # Tenant admins and property managers see all properties (no visibility filter)
            
            # Apply search filter
            if filter_params.search:
                search_term = f"%{filter_params.search}%"
                # Join with Project to search in project name
                query = query.join(Property.project)
                query = query.filter(
                    or_(
                        Property.unit_number.ilike(search_term),
                        Property.city.ilike(search_term),
                        Property.state.ilike(search_term),
                        Property.zip_code.ilike(search_term),
                        Project.name.ilike(search_term),
                        Project.street.ilike(search_term)
                    )
                )
            
            # Apply filters
            if filter_params.project_id:
                query = query.filter(Property.project_id == filter_params.project_id)
            
            if filter_params.city:
                query = query.filter(Property.city.ilike(f"%{filter_params.city}%"))
            
            if filter_params.state:
                query = query.filter(Property.state.ilike(f"%{filter_params.state}%"))
            
            if filter_params.property_type:
                query = query.filter(Property.property_type == filter_params.property_type)
            
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
            if filter_params.active is not None and len(filter_params.active) > 0:
                query = query.filter(Property.active.in_(filter_params.active))
            
            if filter_params.pre_sale is not None:
                query = query.filter(Property.pre_sale == filter_params.pre_sale)
            
            if filter_params.draft is not None:
                query = query.filter(Property.draft == filter_params.draft)
            
            # Apply rental yield filters if specified
            # Note: We'll need to filter after fetching since yield is calculated
            # This is not optimal for large datasets but necessary for computed fields
            needs_yield_filter = filter_params.min_rental_yield is not None or filter_params.max_rental_yield is not None
            
            # Get total count
            total = query.count()
            
            # Apply sorting with secondary sort by ID for stable pagination
            sort_field = getattr(Property, filter_params.sort_by, Property.created_at)
            if filter_params.sort_order == "desc":
                query = query.order_by(sort_field.desc(), Property.id.desc())
            else:
                query = query.order_by(sort_field.asc(), Property.id.asc())
            
            # Apply pagination
            offset = (filter_params.page - 1) * filter_params.page_size
            properties = query.offset(offset).limit(filter_params.page_size).all()
            
            # Convert to PropertyOverview format with computed fields
            from app.schemas.business import PropertyOverview
            items = []
            for prop in properties:
                # Use mapper to convert property to overview format
                overview_data = map_property_to_overview(prop)
                
                # Apply rental yield filter if needed
                if needs_yield_filter:
                    gross_rental_yield = overview_data.get("gross_rental_yield")
                    if filter_params.min_rental_yield is not None and gross_rental_yield is not None:
                        if gross_rental_yield < filter_params.min_rental_yield:
                            continue
                    if filter_params.max_rental_yield is not None and gross_rental_yield is not None:
                        if gross_rental_yield > filter_params.max_rental_yield:
                            continue
                
                items.append(PropertyOverview(**overview_data))
            
            # If we filtered by yield, we need to adjust total count
            if needs_yield_filter:
                # This is not ideal but necessary for computed fields
                # In production, consider adding a database column for rental yield
                total = len(items)
            
            return {
                "items": items,
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
            
            # Store old values before update
            old_values = {}
            update_data = property_data.model_dump(exclude_unset=True)
            
            # Capture old values for fields being updated
            for field in update_data.keys():
                old_values[field] = getattr(property, field, None)
            
            # Update fields
            for field, value in update_data.items():
                setattr(property, field, value)
            
            property.updated_by = current_user.id
            property.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            # Log activity with old and new values
            audit_logger.log_business_event(
                db=db,
                action="PROPERTY_UPDATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                old_values=old_values,
                new_values=update_data
            )
            
            # If status was updated, update project status
            if 'status' in update_data:
                from app.services.project_service import ProjectService
                ProjectService.update_project_status_from_properties(
                    db=db,
                    project_id=property.project_id,
                    tenant_id=current_user.tenant_id
                )
            
            # If price or rent fields were updated, update project aggregates
            price_fields = {'purchase_price', 'purchase_price_parking', 'purchase_price_furniture', 
                           'monthly_rent', 'rent_parking_month'}
            if any(field in update_data for field in price_fields):
                from app.services.project_service import ProjectService
                ProjectService.update_project_aggregates(
                    db=db,
                    project_id=property.project_id,
                    tenant_id=current_user.tenant_id
                )
            
            # Commit and reload with relationships
            db.commit()
            
            # Load relationships for proper response
            from sqlalchemy.orm import joinedload
            property = db.query(Property).options(
                joinedload(Property.images),
                joinedload(Property.city_ref).joinedload(City.images),
                joinedload(Property.project).joinedload(Project.images),
                joinedload(Property.project).joinedload(Project.city_ref)
            ).filter(Property.id == property.id).first()
            
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
            audit_logger.log_business_event(
                db=db,
                action="PROPERTY_DELETED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property.id,
                old_values={
                    "project_id": str(property.project_id),
                    "unit_number": property.unit_number,
                    "city": property.city
                }
            )
            
            # Store project_id before deletion
            project_id = property.project_id
            
            db.delete(property)
            db.flush()
            
            # Update project status after property deletion
            from app.services.project_service import ProjectService
            ProjectService.update_project_status_from_properties(
                db=db,
                project_id=project_id,
                tenant_id=current_user.tenant_id
            )
            
            # Update project aggregates after property deletion
            ProjectService.update_project_aggregates(
                db=db,
                project_id=project_id,
                tenant_id=current_user.tenant_id
            )
            
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
            # Count by active status values - handle nullable active field
            available_properties = query.filter(
                and_(Property.active.is_not(None), Property.active == 1)
            ).count()  # Frei
            reserved_properties = query.filter(
                and_(Property.active.is_not(None), Property.active.in_([5, 6]))
            ).count()  # Angefragt + Reserviert
            sold_properties = query.filter(
                and_(Property.active.is_not(None), Property.active.in_([0, 7, 9]))
            ).count()  # Verkauft + Notartermin + Notarvorbereitung
            
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
    
    @staticmethod
    def get_aggregate_stats(
        db: Session,
        tenant_id: UUID,
        current_user: User
    ) -> PropertyAggregateStats:
        """Get aggregate statistics for all properties in the tenant"""
        try:
            # Base query for properties
            query = db.query(Property).filter(Property.tenant_id == tenant_id)
            
            # Check user permissions
            is_admin_or_manager = current_user.is_super_admin
            if not is_admin_or_manager:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                permission_names = [p["name"] for p in permissions.get("permissions", [])]
                is_admin_or_manager = "properties:update" in permission_names
            
            # Apply visibility filter for non-admin users
            if not is_admin_or_manager:
                query = query.filter(Property.visibility == 1)
            
            # Get aggregate statistics
            stats = db.query(
                func.min(Property.purchase_price).label('min_price'),
                func.max(Property.purchase_price).label('max_price'),
                func.min(Property.size_sqm).label('min_size'),
                func.max(Property.size_sqm).label('max_size'),
                func.min(Property.rooms).label('min_rooms'),
                func.max(Property.rooms).label('max_rooms')
            ).filter(
                Property.id.in_(query.with_entities(Property.id))
            ).first()
            
            # Get rental yield range from properties with valid data
            yield_subquery = query.filter(
                and_(
                    Property.purchase_price > 0,
                    Property.monthly_rent > 0
                )
            ).with_entities(
                (
                    ((Property.monthly_rent + func.coalesce(Property.rent_parking_month, 0)) * 12 * 100.0) / 
                    (Property.purchase_price + func.coalesce(Property.purchase_price_parking, 0) + func.coalesce(Property.purchase_price_furniture, 0))
                ).label('rental_yield')
            ).subquery()
            
            yield_stats = db.query(
                func.min(yield_subquery.c.rental_yield).label('min_yield'),
                func.max(yield_subquery.c.rental_yield).label('max_yield')
            ).first()
            
            # Convert to response format
            return PropertyAggregateStats(
                price_range=RangeStats(
                    min=float(stats.min_price) if stats.min_price else 0,
                    max=float(stats.max_price) if stats.max_price else 1000000
                ),
                size_range=RangeStats(
                    min=float(stats.min_size) if stats.min_size else 0,
                    max=float(stats.max_size) if stats.max_size else 200
                ),
                rooms_range=RangeStats(
                    min=float(stats.min_rooms) if stats.min_rooms else 1,
                    max=float(stats.max_rooms) if stats.max_rooms else 5
                ),
                rental_yield_range=RangeStats(
                    min=float(yield_stats.min_yield) if yield_stats.min_yield else 0,
                    max=float(yield_stats.max_yield) if yield_stats.max_yield else 10
                )
            )
            
        except Exception as e:
            logger.error(f"Error getting property aggregate stats: {str(e)}")
            # Return default values on error
            return PropertyAggregateStats(
                price_range=RangeStats(min=0, max=1000000),
                size_range=RangeStats(min=0, max=200),
                rooms_range=RangeStats(min=1, max=5),
                rental_yield_range=RangeStats(min=0, max=10)
            )