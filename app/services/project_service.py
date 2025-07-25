# ================================
# PROJECT SERVICE (services/project_service.py)
# ================================

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, select, desc
from sqlalchemy.exc import IntegrityError
import logging

from app.models.business import Project, ProjectImage, Property, City
from app.models.user import User
from app.schemas.business import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectOverview,
    ProjectFilter, ProjectListResponse,
    ProjectImageCreate, ProjectImageUpdate,
    ProjectAggregateStats, RangeStats
)
from app.core.exceptions import AppException
from app.mappers.project_mapper import map_project_to_overview, map_project_to_response
from app.services.s3_service import get_s3_service
from app.services.google_maps_service import GoogleMapsService
from app.services.city_service import CityService
from app.utils.audit import AuditLogger

audit_logger = AuditLogger()
logger = logging.getLogger(__name__)

class ProjectService:
    """Service für Project-Management"""
    
    @staticmethod
    def create_project(db: Session, project_data: ProjectCreate, created_by: UUID, tenant_id: UUID) -> Project:
        """Create a new project and automatically fetch micro location data"""
        try:
            # Check if project with same name already exists
            existing = db.query(Project).filter(
                and_(
                    Project.tenant_id == tenant_id,
                    Project.name == project_data.name
                )
            ).first()
            
            if existing:
                raise AppException(
                    status_code=409,
                    detail=f"Project with name '{project_data.name}' already exists"
                )
            
            # Try to find matching city if city_id not provided
            city_id = project_data.city_id
            logger.info(f"Creating project with city_id: {city_id}, city: {project_data.city}, state: {project_data.state}")
            
            if not city_id and project_data.city and project_data.state:
                logger.info(f"No city_id provided, attempting to match city '{project_data.city}' in state '{project_data.state}'")
                
                # Create a temporary user object with tenant_id for city lookup
                temp_user = User()
                temp_user.tenant_id = tenant_id
                temp_user.is_super_admin = False
                
                # Try to find city by name and state
                matching_city = CityService.get_city_by_name(
                    db=db,
                    city_name=project_data.city,
                    state=project_data.state,
                    current_user=temp_user
                )
                
                if matching_city:
                    city_id = matching_city.id
                    logger.info(f"Successfully matched city '{project_data.city}, {project_data.state}' to city_id {city_id}")
                else:
                    logger.warning(f"Could not find city '{project_data.city}' in state '{project_data.state}' for tenant {tenant_id}")
            else:
                if not city_id:
                    logger.warning(f"No city_id and missing city or state: city='{project_data.city}', state='{project_data.state}'")
            
            # Create project
            project = Project(
                **project_data.model_dump(exclude={'city_id'}),
                city_id=city_id,
                tenant_id=tenant_id,
                created_by=created_by,
                updated_by=created_by
            )
            
            db.add(project)
            db.commit()
            db.refresh(project)
            
            # Try to geocode the address to get district and coordinates
            try:
                google_maps_service = GoogleMapsService()
                address = f"{project.street} {project.house_number}, {project.zip_code} {project.city}, {project.state}"
                
                # Run async geocoding in sync context
                import asyncio
                import concurrent.futures
                
                def run_async_geocode():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            google_maps_service.geocode_address(db, address)
                        )
                    finally:
                        new_loop.close()
                
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_geocode)
                        geocode_result = future.result(timeout=10)
                except Exception as e:
                    logger.error(f"Error during geocoding in create_project: {e}")
                    geocode_result = None
                
                geocoded_data = None
                if geocode_result:
                    # We need to extract district from the Google Maps response
                    # For now, use the formatted address
                    geocoded_data = {
                        "latitude": geocode_result["lat"],
                        "longitude": geocode_result["lng"],
                        "district": None  # Google Maps doesn't provide district directly in our current implementation
                    }
                
                if geocoded_data:
                    # Update project with geocoded coordinates only (not district)
                    update_data = {}
                    
                    if geocoded_data.get("latitude") and not project.latitude:
                        update_data["latitude"] = geocoded_data["latitude"]
                        
                    if geocoded_data.get("longitude") and not project.longitude:
                        update_data["longitude"] = geocoded_data["longitude"]
                    
                    if update_data:
                        for key, value in update_data.items():
                            setattr(project, key, value)
                        db.commit()
                        db.refresh(project)
                        logger.info(f"Updated project {project.id} with geocoded data: {update_data}")
                else:
                    logger.warning(f"Could not geocode address for project {project.id}")
            except Exception as e:
                logger.error(f"Error geocoding address for project {project.id}: {str(e)}")
                # Continue without geocoding data
            
            # Try to fetch micro location data from Google Maps
            try:
                google_maps_service = GoogleMapsService()
                address = f"{project.street} {project.house_number}, {project.zip_code} {project.city}, {project.state}"
                
                # Run async function in sync context
                import asyncio
                import concurrent.futures
                
                def run_async_micro_location():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            google_maps_service.get_micro_location_data(db, address)
                        )
                    finally:
                        new_loop.close()
                
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_micro_location)
                        micro_location_data = future.result(timeout=30)  # Give more time for ChatGPT
                except Exception as e:
                    logger.error(f"Error fetching micro location data: {e}")
                    micro_location_data = None
                
                # Update project with micro location data
                if micro_location_data:
                    project.micro_location_v2 = micro_location_data
                    db.commit()
                    db.refresh(project)
                    logger.info(f"Successfully fetched micro location data for project {project.id}")
                else:
                    logger.warning(f"No micro location data returned for project {project.id}")
                    
            except Exception as e:
                # Log error but don't fail the project creation
                logger.error(f"Failed to fetch micro location data for project {project.id}: {str(e)}")
                # Continue without micro location data
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="CREATE",
                resource_type="project",
                resource_id=project.id,
                new_values={"project_name": project.name}
            )
            
            # Load relationships before returning
            db.refresh(project)
            # Explicitly load images and city_ref for the response
            from sqlalchemy.orm import selectinload
            project = db.query(Project).options(
                selectinload(Project.images),
                selectinload(Project.city_ref),
                selectinload(Project.properties)
            ).filter(Project.id == project.id).first()
            
            return project
            
        except IntegrityError as e:
            db.rollback()
            raise AppException(
                status_code=422,
                detail=f"Database integrity error: {str(e)}"
            )
    
    @staticmethod
    def get_project(db: Session, project_id: UUID, tenant_id: UUID) -> Project:
        """Get project by ID with all relationships"""
        project = db.query(Project).options(
            selectinload(Project.images),
            selectinload(Project.properties).selectinload(Property.images),
            selectinload(Project.city_ref)
        ).filter(
            and_(
                Project.id == project_id,
                Project.tenant_id == tenant_id
            )
        ).first()
        
        if not project:
            raise AppException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
            
        return project
    
    @staticmethod
    def list_projects(
        db: Session,
        tenant_id: UUID,
        filters: ProjectFilter,
        current_user: User
    ) -> ProjectListResponse:
        """List projects with filtering and pagination"""
        query = db.query(Project).filter(Project.tenant_id == tenant_id)
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Project.name.ilike(search_term),
                    Project.street.ilike(search_term),
                    Project.city.ilike(search_term),
                    Project.state.ilike(search_term),
                    Project.zip_code.ilike(search_term)
                )
            )
        
        # Apply filters
        if filters.city:
            query = query.filter(Project.city.ilike(f"%{filters.city}%"))
        if filters.state:
            query = query.filter(Project.state.ilike(f"%{filters.state}%"))
        if filters.status:
            query = query.filter(Project.status == filters.status)
        if filters.building_type:
            query = query.filter(Project.building_type == filters.building_type)
        if filters.has_elevator is not None:
            query = query.filter(Project.has_elevator == filters.has_elevator)
        if filters.has_parking is not None:
            query = query.filter(Project.has_parking == filters.has_parking)
        if filters.min_construction_year is not None:
            query = query.filter(Project.construction_year >= filters.min_construction_year)
        if filters.max_construction_year is not None:
            query = query.filter(Project.construction_year <= filters.max_construction_year)
        
        # Price range filters
        if filters.min_price is not None:
            query = query.filter(Project.min_price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(Project.max_price <= filters.max_price)
        
        # Rental yield filters
        if filters.min_rental_yield is not None:
            query = query.filter(Project.min_rental_yield >= filters.min_rental_yield)
        if filters.max_rental_yield is not None:
            query = query.filter(Project.max_rental_yield <= filters.max_rental_yield)
        
        # Check user permissions for visibility filtering
        is_admin_or_manager = current_user.is_super_admin
        if not is_admin_or_manager:
            # Check if user has can_see_all_properties flag
            if current_user.can_see_all_properties:
                # User can see all projects - no filter needed
                is_admin_or_manager = True
            else:
                from app.services.rbac_service import RBACService
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                permission_names = [p["name"] for p in permissions.get("permissions", [])]
                is_admin_or_manager = "properties:update" in permission_names
        
        # For non-admin users who can't see all properties, filter projects based on property assignments
        if not is_admin_or_manager:
            from app.models.business import Property, PropertyAssignment
            
            # Get properties assigned to this user
            assigned_property_ids = db.query(PropertyAssignment.property_id).filter(
                PropertyAssignment.user_id == current_user.id,
                PropertyAssignment.tenant_id == tenant_id
            ).subquery()
            
            # Get project IDs that have at least one property assigned to this user
            visible_project_ids = db.query(Project.id).join(Project.properties).filter(
                and_(
                    Project.tenant_id == tenant_id,
                    Property.id.in_(assigned_property_ids)
                )
            ).distinct().subquery()
            
            # Filter main query by these IDs
            query = query.filter(Project.id.in_(select(visible_project_ids.c.id)))
        
        # Get total count after visibility filtering
        total = query.count()
        
        # Apply sorting with secondary sort by ID for stable pagination
        sort_column = getattr(Project, filters.sort_by, Project.created_at)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column), desc(Project.id))
        else:
            query = query.order_by(sort_column, Project.id)
        
        # Apply pagination
        query = query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        
        # Load relationships for property count and images
        projects = query.options(
            selectinload(Project.properties),
            selectinload(Project.images)
        ).all()
        
        # Convert to overview schema using mapper
        items = []
        for project in projects:
            overview_data = map_project_to_overview(project)
            overview = ProjectOverview(**overview_data)
            items.append(overview)
        
        return ProjectListResponse(
            items=items,
            total=total,
            page=filters.page,
            size=filters.page_size,
            pages=(total + filters.page_size - 1) // filters.page_size
        )
    
    @staticmethod
    def update_project(
        db: Session,
        project_id: UUID,
        project_update: ProjectUpdate,
        updated_by: UUID,
        tenant_id: UUID
    ) -> Project:
        """Update project"""
        project = ProjectService.get_project(db, project_id, tenant_id)
        
        # Update fields
        update_data = project_update.model_dump(exclude_unset=True)
        
        # Store old values before update
        old_values = {}
        for field in update_data.keys():
            old_values[field] = getattr(project, field, None)
        
        # Check if address fields are being updated
        address_fields = {'street', 'house_number', 'city', 'state', 'country', 'zip_code'}
        address_changed = any(field in update_data for field in address_fields)
        
        # Special handling for renovations field - convert Pydantic models to dict
        if 'renovations' in update_data and update_data['renovations'] is not None:
            renovations_list = []
            for renovation in update_data['renovations']:
                if hasattr(renovation, 'model_dump'):
                    # It's a Pydantic model, convert to dict
                    renovations_list.append(renovation.model_dump())
                elif isinstance(renovation, dict):
                    # It's already a dict
                    renovations_list.append(renovation)
            update_data['renovations'] = renovations_list
        
        for field, value in update_data.items():
            setattr(project, field, value)
        
        project.updated_by = updated_by
        
        try:
            db.commit()
            db.refresh(project)
            
            # If address changed, try to re-geocode
            if address_changed:
                try:
                    google_maps_service = GoogleMapsService()
                    address = f"{project.street} {project.house_number}, {project.zip_code} {project.city}, {project.state}"
                    
                    # Run async geocoding in sync context
                    # Since we're in a sync method but FastAPI runs in async context,
                    # we need to handle this carefully
                    import asyncio
                    geocode_result = None
                    
                    try:
                        # Create a new event loop in a thread to run the async function
                        import concurrent.futures
                        
                        def run_async_geocode():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(
                                    google_maps_service.geocode_address(db, address)
                                )
                            finally:
                                new_loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_async_geocode)
                            geocode_result = future.result(timeout=10)
                            
                    except Exception as e:
                        logger.error(f"Error during geocoding: {e}")
                        geocode_result = None
                    
                    geocoded_data = None
                    if geocode_result:
                        geocoded_data = {
                            "latitude": geocode_result["lat"],
                            "longitude": geocode_result["lng"],
                            "district": None  # Google Maps doesn't provide district directly yet
                        }
                    
                    if geocoded_data:
                        # Update geocoded coordinates only (not district)
                        geocode_updates = {}
                        
                        # Don't auto-generate district - user should control this field
                        
                        if geocoded_data.get("latitude"):
                            project.latitude = geocoded_data["latitude"]
                            geocode_updates["latitude"] = geocoded_data["latitude"]
                            
                        if geocoded_data.get("longitude"):
                            project.longitude = geocoded_data["longitude"]
                            geocode_updates["longitude"] = geocoded_data["longitude"]
                        
                        if geocode_updates:
                            db.commit()
                            db.refresh(project)
                            logger.info(f"Updated project {project.id} with new geocoded data: {geocode_updates}")
                    else:
                        logger.warning(f"Could not geocode new address for project {project.id}")
                except Exception as e:
                    logger.error(f"Error geocoding updated address for project {project.id}: {str(e)}")
                    # Continue without geocoding data
            
            # Log activity with old and new values
            audit_logger.log_business_event(
                db=db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="PROJECT_UPDATED",
                resource_type="project",
                resource_id=project.id,
                old_values=old_values,
                new_values=update_data
            )
            
            # Reload with relationships for response
            return ProjectService.get_project(db, project_id, tenant_id)
            
        except IntegrityError as e:
            db.rollback()
            raise AppException(
                status_code=422,
                detail=f"Database integrity error: {str(e)}"
            )
    
    @staticmethod
    def delete_project(
        db: Session,
        project_id: UUID,
        deleted_by: UUID,
        tenant_id: UUID
    ) -> None:
        """Delete project and all associated data"""
        project = ProjectService.get_project(db, project_id, tenant_id)
        
        # Check if project has properties
        if project.properties:
            raise AppException(
                status_code=409,
                detail=f"Cannot delete project with {len(project.properties)} properties. "
                       "Delete all properties first."
            )
        
        # Delete all project images from S3
        s3_service = get_s3_service()
        if s3_service and s3_service.is_configured():
            for image in project.images:
                s3_service.delete_image(image.s3_key if hasattr(image, 's3_key') else image.image_url)
        
        # Delete project
        db.delete(project)
        db.commit()
        
        # Log activity
        audit_logger.log_business_event(
            db=db,
            user_id=deleted_by,
            tenant_id=tenant_id,
            action="DELETE",
            resource_type="project",
            resource_id=project_id,
            old_values={"project_name": project.name}
        )
    
    @staticmethod
    def add_project_image(
        db: Session,
        project_id: UUID,
        image_data: ProjectImageCreate,
        created_by: UUID,
        tenant_id: UUID
    ) -> ProjectImage:
        """Add image to project"""
        # Verify project exists
        project = ProjectService.get_project(db, project_id, tenant_id)
        
        # Create image record
        image = ProjectImage(
            project_id=project_id,
            **image_data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(image)
        db.commit()
        db.refresh(image)
        
        return image
    
    @staticmethod
    def update_project_image(
        db: Session,
        project_id: UUID,
        image_id: UUID,
        image_update: ProjectImageUpdate,
        updated_by: UUID,
        tenant_id: UUID
    ) -> ProjectImage:
        """Update project image metadata"""
        # Get image
        image = db.query(ProjectImage).filter(
            and_(
                ProjectImage.id == image_id,
                ProjectImage.project_id == project_id,
                ProjectImage.tenant_id == tenant_id
            )
        ).first()
        
        if not image:
            raise AppException(
                status_code=404,
                detail=f"Image with ID {image_id} not found"
            )
        
        # Update fields
        update_data = image_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(image, field, value)
        
        image.updated_by = updated_by
        
        db.commit()
        db.refresh(image)
        
        return image
    
    @staticmethod
    def delete_project_image(
        db: Session,
        project_id: UUID,
        image_id: UUID,
        deleted_by: UUID,
        tenant_id: UUID
    ) -> None:
        """Delete project image"""
        # Get image
        image = db.query(ProjectImage).filter(
            and_(
                ProjectImage.id == image_id,
                ProjectImage.project_id == project_id,
                ProjectImage.tenant_id == tenant_id
            )
        ).first()
        
        if not image:
            raise AppException(
                status_code=404,
                detail=f"Image with ID {image_id} not found"
            )
        
        # Delete from S3
        s3_service = get_s3_service()
        if s3_service and s3_service.is_configured():
            s3_service.delete_image(image.s3_key if hasattr(image, 's3_key') else image.image_url)
        
        # Delete from database
        db.delete(image)
        db.commit()
        
        # Log activity
        audit_logger.log_business_event(
            db=db,
            user_id=deleted_by,
            tenant_id=tenant_id,
            action="DELETE_IMAGE",
            resource_type="project",
            resource_id=project_id,
            old_values={"image_id": str(image_id), "image_type": image.image_type}
        )
    
    @staticmethod
    async def get_project_statistics(
        db: Session,
        project_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get project statistics"""
        project = await ProjectService.get_project(db, project_id, tenant_id)
        
        # Calculate statistics
        total_properties = len(project.properties)
        total_units_value = sum(p.purchase_price for p in project.properties if p.purchase_price)
        total_monthly_rent = sum(p.monthly_rent for p in project.properties if p.monthly_rent)
        total_size_sqm = sum(p.size_sqm for p in project.properties if p.size_sqm)
        
        available_units = sum(1 for p in project.properties if p.status == 'available')
        reserved_units = sum(1 for p in project.properties if p.status == 'reserved')
        sold_units = sum(1 for p in project.properties if p.status == 'sold')
        
        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "total_properties": total_properties,
            "total_value": float(total_units_value) if total_units_value else 0,
            "total_monthly_rent": float(total_monthly_rent) if total_monthly_rent else 0,
            "total_size_sqm": float(total_size_sqm) if total_size_sqm else 0,
            "average_unit_price": float(total_units_value / total_properties) if total_properties > 0 else 0,
            "average_rent_per_sqm": float(total_monthly_rent / total_size_sqm) if total_size_sqm > 0 else 0,
            "units_by_status": {
                "available": available_units,
                "reserved": reserved_units,
                "sold": sold_units
            },
            "occupancy_rate": (reserved_units + sold_units) / total_properties * 100 if total_properties > 0 else 0
        }
    
    @staticmethod
    async def refresh_project_micro_location(
        db: Session,
        project_id: UUID,
        tenant_id: UUID,
        user_id: UUID = None,
        force_refresh: bool = False
    ) -> bool:
        """Refresh micro location data for a project
        
        Args:
            db: Database session
            project_id: Project ID
            tenant_id: Tenant ID
            user_id: User ID
            force_refresh: If True, refresh even if data already exists
        
        Returns:
            bool: True if refreshed, False otherwise
        """
        try:
            # Get the project
            project = db.query(Project).filter(
                and_(
                    Project.id == project_id,
                    Project.tenant_id == tenant_id
                )
            ).first()
            
            if not project:
                logger.warning(f"Project {project_id} not found for tenant {tenant_id}")
                return False
            
            # Check if micro location already exists (unless force refresh)
            if project.micro_location_v2 and not force_refresh:
                logger.info(f"Project {project_id} already has micro location data, skipping refresh")
                return False
            
            # Only refresh if project has required address data
            if not all([project.street, project.house_number, project.city, project.state]):
                logger.warning(f"Project {project_id} missing required address data for micro location")
                return False
            
            # Try to generate micro location data
            try:
                google_maps_service = GoogleMapsService()
                address = f"{project.street} {project.house_number}, {project.zip_code} {project.city}, {project.state}"
                
                # Now we can call async function directly since this method is async
                micro_location_data = await google_maps_service.get_micro_location_data(db, address, force_refresh=force_refresh)
                
                # Update project with micro location data
                if micro_location_data:
                    project.micro_location_v2 = micro_location_data
                    db.commit()
                    logger.info(f"Successfully refreshed micro location data for project {project_id}")
                    return True
                else:
                    logger.warning(f"No micro location data returned for project {project_id}")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to refresh micro location for project {project_id}: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in refresh_project_micro_location: {str(e)}")
            return False
    
    @staticmethod
    def update_project_status_from_properties(
        db: Session,
        project_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Update project status based on its properties' statuses"""
        # Get the project with its properties
        project = db.query(Project).filter(
            and_(
                Project.id == project_id,
                Project.tenant_id == tenant_id
            )
        ).first()
        
        if not project:
            return
        
        # Count properties by active status
        from app.models.business import Property
        property_active_statuses = db.query(
            Property.active,
            func.count(Property.id)
        ).filter(
            Property.project_id == project_id
        ).group_by(Property.active).all()
        
        active_counts = {active: count for active, count in property_active_statuses}
        total_properties = sum(active_counts.values())
        
        if total_properties == 0:
            # No properties, keep current project status
            return
        
        # Determine new project status based on property active values
        # Active values: 0=Verkauft, 1=Frei, 5=Angefragt, 6=Reserviert, 7=Notartermin, 9=Notarvorbereitung
        available_count = active_counts.get(1, 0)  # Frei
        reserved_count = active_counts.get(5, 0) + active_counts.get(6, 0)  # Angefragt + Reserviert
        sold_count = active_counts.get(0, 0) + active_counts.get(7, 0) + active_counts.get(9, 0)  # Verkauft + Notartermin + Notarvorbereitung
        
        new_status = None
        
        if available_count > 0:
            # If any property is available (Frei), project is available
            new_status = 'available'
        elif sold_count == total_properties:
            # If all properties are sold/in sale process, project is sold
            new_status = 'sold'
        elif reserved_count == total_properties:
            # If all properties are reserved/inquired, project is reserved
            new_status = 'reserved'
        else:
            # Mixed status, default to reserved if there are any reserved properties
            new_status = 'reserved' if reserved_count > 0 else 'sold'
        
        # Update project status if changed
        if project.status != new_status:
            old_status = project.status
            project.status = new_status
            db.commit()
            
            # Log the status change
            audit_logger.log_business_event(
                db=db,
                user_id=project.updated_by or project.created_by,
                tenant_id=tenant_id,
                action="AUTO_STATUS_UPDATE",
                resource_type="project",
                resource_id=project.id,
                old_values={"status": old_status},
                new_values={"status": new_status},
                additional_context={"property_active_counts": active_counts}
            )
    
    @staticmethod
    def update_project_aggregates(
        db: Session,
        project_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Update project price and rental yield aggregates based on its properties"""
        try:
            # Get the project
            project = db.query(Project).filter(
                and_(
                    Project.id == project_id,
                    Project.tenant_id == tenant_id
                )
            ).first()
            
            if not project:
                logger.warning(f"Project {project_id} not found for tenant {tenant_id}")
                return
            
            # Calculate aggregates from properties
            from sqlalchemy import case
            
            # Price aggregates query
            price_aggregates = db.query(
                func.min(
                    Property.purchase_price + 
                    func.coalesce(Property.purchase_price_parking, 0) + 
                    func.coalesce(Property.purchase_price_furniture, 0)
                ).label('min_price'),
                func.max(
                    Property.purchase_price + 
                    func.coalesce(Property.purchase_price_parking, 0) + 
                    func.coalesce(Property.purchase_price_furniture, 0)
                ).label('max_price')
            ).filter(
                and_(
                    Property.project_id == project_id,
                    Property.tenant_id == tenant_id,
                    Property.purchase_price.isnot(None)
                )
            ).first()
            
            # Rental yield aggregates query
            yield_aggregates = db.query(
                func.min(
                    case(
                        (Property.purchase_price > 0,
                         ((Property.monthly_rent + func.coalesce(Property.rent_parking_month, 0)) * 12 * 100.0) / 
                         (Property.purchase_price + func.coalesce(Property.purchase_price_parking, 0) + func.coalesce(Property.purchase_price_furniture, 0))
                        ),
                        else_=None
                    )
                ).label('min_rental_yield'),
                func.max(
                    case(
                        (Property.purchase_price > 0,
                         ((Property.monthly_rent + func.coalesce(Property.rent_parking_month, 0)) * 12 * 100.0) / 
                         (Property.purchase_price + func.coalesce(Property.purchase_price_parking, 0) + func.coalesce(Property.purchase_price_furniture, 0))
                        ),
                        else_=None
                    )
                ).label('max_rental_yield')
            ).filter(
                and_(
                    Property.project_id == project_id,
                    Property.tenant_id == tenant_id
                )
            ).first()
            
            # Initial maintenance expenses aggregates query
            maintenance_aggregates = db.query(
                func.min(Property.initial_maintenance_expenses).label('min_initial_maintenance_expenses'),
                func.max(Property.initial_maintenance_expenses).label('max_initial_maintenance_expenses')
            ).filter(
                and_(
                    Property.project_id == project_id,
                    Property.tenant_id == tenant_id,
                    Property.initial_maintenance_expenses.isnot(None),
                    Property.initial_maintenance_expenses > 0
                )
            ).first()
            
            # Update project with new aggregates
            project.min_price = price_aggregates.min_price if price_aggregates else None
            project.max_price = price_aggregates.max_price if price_aggregates else None
            project.min_rental_yield = yield_aggregates.min_rental_yield if yield_aggregates else None
            project.max_rental_yield = yield_aggregates.max_rental_yield if yield_aggregates else None
            project.min_initial_maintenance_expenses = maintenance_aggregates.min_initial_maintenance_expenses if maintenance_aggregates else None
            project.max_initial_maintenance_expenses = maintenance_aggregates.max_initial_maintenance_expenses if maintenance_aggregates else None
            
            db.commit()
            
            logger.info(f"Updated aggregates for project {project_id}: price range={project.min_price}-{project.max_price}, yield range={project.min_rental_yield}-{project.max_rental_yield}, maintenance range={project.min_initial_maintenance_expenses}-{project.max_initial_maintenance_expenses}")
            
        except Exception as e:
            logger.error(f"Error updating project aggregates: {str(e)}")
            db.rollback()
    
    @staticmethod
    def get_aggregate_stats(
        db: Session,
        tenant_id: UUID,
        current_user: User
    ) -> ProjectAggregateStats:
        """Get aggregate statistics for all projects in the tenant"""
        try:
            # Base query for projects
            query = db.query(Project).filter(Project.tenant_id == tenant_id)
            
            # Check user permissions for visibility filtering
            is_admin_or_manager = current_user.is_super_admin
            if not is_admin_or_manager:
                from app.services.rbac_service import RBACService
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                permission_names = [p["name"] for p in permissions.get("permissions", [])]
                is_admin_or_manager = "properties:update" in permission_names
            
            # For non-admin users, filter projects to only those with visible properties
            if not is_admin_or_manager:
                from app.models.business import Property
                # Use a subquery to get project IDs that have visible properties
                visible_project_ids = db.query(Project.id).join(Project.properties).filter(
                    and_(
                        Project.tenant_id == tenant_id,
                        Property.visibility == 1
                    )
                ).distinct().subquery()
                
                # Filter main query by these IDs
                query = query.filter(Project.id.in_(select(visible_project_ids.c.id)))
            
            # Get aggregate statistics
            stats = db.query(
                func.min(Project.min_price).label('min_price'),
                func.max(Project.max_price).label('max_price'),
                func.min(Project.min_rental_yield).label('min_rental_yield'),
                func.max(Project.max_rental_yield).label('max_rental_yield'),
                func.min(Project.construction_year).label('min_construction_year'),
                func.max(Project.construction_year).label('max_construction_year')
            ).filter(
                Project.id.in_(query.with_entities(Project.id))
            ).first()
            
            # Convert to response format
            return ProjectAggregateStats(
                price_range=RangeStats(
                    min=float(stats.min_price) if stats.min_price else 0,
                    max=float(stats.max_price) if stats.max_price else 1000000
                ),
                rental_yield_range=RangeStats(
                    min=float(stats.min_rental_yield) if stats.min_rental_yield else 0,
                    max=float(stats.max_rental_yield) if stats.max_rental_yield else 10
                ),
                construction_year_range=RangeStats(
                    min=float(stats.min_construction_year) if stats.min_construction_year else 1900,
                    max=float(stats.max_construction_year) if stats.max_construction_year else 2024
                )
            )
            
        except Exception as e:
            logger.error(f"Error getting project aggregate stats: {str(e)}")
            # Return default values on error
            return ProjectAggregateStats(
                price_range=RangeStats(min=0, max=1000000),
                rental_yield_range=RangeStats(min=0, max=10),
                construction_year_range=RangeStats(min=1900, max=2024)
            )