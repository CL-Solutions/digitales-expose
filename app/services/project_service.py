# ================================
# PROJECT SERVICE (services/project_service.py)
# ================================

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, func, select, desc
from sqlalchemy.exc import IntegrityError

from app.models.business import Project, ProjectImage, Property
from app.schemas.business import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectOverview,
    ProjectFilter, ProjectListResponse,
    ProjectImageCreate, ProjectImageUpdate
)
from app.core.exceptions import AppException
from app.services.s3_service import get_s3_service
from app.utils.audit import AuditLogger

audit_logger = AuditLogger()

class ProjectService:
    """Service für Project-Management"""
    
    @staticmethod
    def create_project(db: Session, project_data: ProjectCreate, created_by: UUID, tenant_id: UUID) -> Project:
        """Create a new project"""
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
            
            # Create project
            project = Project(
                **project_data.model_dump(exclude={'city_id'}),
                city_id=project_data.city_id,
                tenant_id=tenant_id,
                created_by=created_by,
                updated_by=created_by
            )
            
            db.add(project)
            db.commit()
            db.refresh(project)
            
            # Log activity
            audit_logger.log_event(
                db=db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="CREATE",
                resource_type="project",
                resource_id=project.id,
                details={"project_name": project.name}
            )
            
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
        filters: ProjectFilter
    ) -> ProjectListResponse:
        """List projects with filtering and pagination"""
        query = db.query(Project).filter(Project.tenant_id == tenant_id)
        
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
        
        # Get total count
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
        
        # Convert to overview schema
        items = []
        for project in projects:
            # Get thumbnail from first image
            thumbnail_url = None
            if project.images:
                # Sort by display_order and get first
                sorted_images = sorted(project.images, key=lambda x: x.display_order)
                if sorted_images:
                    thumbnail_url = sorted_images[0].image_url
            
            overview = ProjectOverview(
                id=project.id,
                name=project.name,
                street=project.street,
                house_number=project.house_number,
                city=project.city,
                state=project.state,
                zip_code=project.zip_code,
                status=project.status,
                building_type=project.building_type,
                total_floors=project.total_floors,
                property_count=len(project.properties),
                has_elevator=project.has_elevator,
                has_parking=project.has_parking,
                thumbnail_url=thumbnail_url,
                investagon_id=project.investagon_id
            )
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
        for field, value in update_data.items():
            setattr(project, field, value)
        
        project.updated_by = updated_by
        
        try:
            db.commit()
            db.refresh(project)
            
            # Log activity
            audit_logger.log_event(
                db=db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="UPDATE",
                resource_type="project",
                resource_id=project.id,
                details={"updated_fields": list(update_data.keys())}
            )
            
            return project
            
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
        audit_logger.log_event(
            db=db,
            user_id=deleted_by,
            tenant_id=tenant_id,
            action="DELETE",
            resource_type="project",
            resource_id=project_id,
            details={"project_name": project.name}
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
        audit_logger.log_event(
            db=db,
            user_id=deleted_by,
            tenant_id=tenant_id,
            action="DELETE_IMAGE",
            resource_type="project",
            resource_id=str(project_id),
            details={"image_id": str(image_id), "image_type": image.image_type}
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