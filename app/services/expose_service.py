# ================================
# EXPOSE SERVICE (services/expose_service.py)
# ================================

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import secrets
import string

from app.models.business import (
    ExposeTemplate, ExposeLink, ExposeLinkView,
    Property, Project, City
)
from app.models.user import User
from app.schemas.business import (
    ExposeTemplateCreate, ExposeTemplateUpdate,
    ExposeLinkCreate, ExposeLinkUpdate
)
from app.core.exceptions import AppException
from app.core.security import get_password_hash, verify_password
from app.utils.audit import AuditLogger
from app.services.rbac_service import RBACService
from app.services.property_service import PropertyService
from app.mappers.expose_mapper import map_expose_links_to_responses

audit_logger = AuditLogger()

class ExposeService:
    """Service for managing expose templates and links"""
    
    @staticmethod
    def create_template(
        db: Session,
        template_data: ExposeTemplateCreate,
        current_user: User
    ) -> ExposeTemplate:
        """Create a new expose template"""
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "expose:manage_templates" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to manage templates"
                    )
            
            # Check if tenant already has a template
            existing_template = db.query(ExposeTemplate).filter(
                ExposeTemplate.tenant_id == current_user.tenant_id
            ).first()
            
            if existing_template:
                raise AppException(
                    status_code=400,
                    detail="Tenant already has a template. Please update the existing template instead."
                )
            
            # Create template
            template_dict = template_data.model_dump()
            
            # Ensure enabled_sections has defaults if not provided
            if "enabled_sections" not in template_dict or template_dict["enabled_sections"] is None:
                from app.schemas.expose_template_types import EnabledSections
                template_dict["enabled_sections"] = EnabledSections().model_dump()
            
            # Apply default content for any missing fields
            from app.utils.default_template_content import get_default_template_content
            default_content = get_default_template_content()
            
            for field, default_value in default_content.items():
                if field not in template_dict or template_dict[field] is None:
                    template_dict[field] = default_value
            
            template = ExposeTemplate(
                **template_dict,
                tenant_id=current_user.tenant_id,
                created_by=current_user.id
            )
            
            db.add(template)
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="TEMPLATE_CREATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="template",
                resource_id=template.id,
                new_values={"tenant_id": str(template.tenant_id)}
            )
            
            return template
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to create template: {str(e)}"
            )
    
    @staticmethod
    def get_template(
        db: Session,
        template_id: UUID,
        current_user: User
    ) -> ExposeTemplate:
        """Get a single template by ID"""
        try:
            query = db.query(ExposeTemplate)
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(ExposeTemplate.tenant_id == current_user.tenant_id)
            
            template = query.filter(ExposeTemplate.id == template_id).first()
            
            if not template:
                raise AppException(
                    status_code=404,
                    detail="Template not found"
                )
            
            return template
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to retrieve template: {str(e)}"
            )
    
    @staticmethod
    def list_templates(
        db: Session,
        current_user: User
    ) -> List[ExposeTemplate]:
        """List expose templates"""
        try:
            query = db.query(ExposeTemplate)
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(ExposeTemplate.tenant_id == current_user.tenant_id)
            
            # Get all templates (each tenant has only one)
            templates = query.all()
            
            return templates
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to list templates: {str(e)}"
            )
    
    @staticmethod
    def update_template(
        db: Session,
        template_id: UUID,
        template_data: ExposeTemplateUpdate,
        current_user: User
    ) -> ExposeTemplate:
        """Update an expose template"""
        try:
            template = ExposeService.get_template(db, template_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "expose:manage_templates" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to manage templates"
                    )
            
            # Update fields
            update_data = template_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(template, field, value)
            
            template.updated_by = current_user.id
            template.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="TEMPLATE_UPDATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="template",
                resource_id=template.id,
                new_values={"updated_fields": list(update_data.keys())}
            )
            
            return template
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to update template: {str(e)}"
            )
    
    @staticmethod
    def delete_template(
        db: Session,
        template_id: UUID,
        current_user: User
    ) -> None:
        """Delete an expose template"""
        try:
            template = ExposeService.get_template(db, template_id, current_user)
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "expose:manage_templates" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to manage templates"
                    )
            
            # Cannot delete a tenant's only template
            raise AppException(
                status_code=400,
                detail="Cannot delete the tenant's template. Each tenant must have exactly one template."
            )
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to delete template: {str(e)}"
            )
    
    @staticmethod
    def get_or_create_tenant_template(
        db: Session,
        tenant_id: UUID,
        created_by: UUID
    ) -> ExposeTemplate:
        """Get the tenant's template or create a default one if none exists"""
        try:
            # Check if tenant has a template
            template = db.query(ExposeTemplate).filter(
                ExposeTemplate.tenant_id == tenant_id
            ).first()
            
            if template:
                return template
            
            # Create default template with all sections enabled
            from app.schemas.expose_template_types import EnabledSections
            from app.utils.default_template_content import get_default_template_content
            
            default_content = get_default_template_content()
            
            default_template = ExposeTemplate(
                tenant_id=tenant_id,
                created_by=created_by,
                enabled_sections=EnabledSections().model_dump(),  # All sections enabled by default
                **default_content  # Unpack all default content fields
            )
            
            db.add(default_template)
            db.flush()
            
            return default_template
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to get or create tenant template: {str(e)}"
            )
    
    @staticmethod
    def create_expose_link(
        db: Session,
        link_data: ExposeLinkCreate,
        current_user: User
    ) -> ExposeLink:
        """Create a new expose link"""
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "expose:create" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to create expose links"
                    )
            
            # Verify property exists and user has access
            property = PropertyService.get_property(
                db, link_data.property_id, current_user
            )
            
            # Generate unique link ID
            link_id = ExposeService._generate_link_id(db)
            
            # Get password from link_data if password_protected
            password = link_data.password if hasattr(link_data, 'password') else None
            
            # Create link
            link_dict = link_data.model_dump(exclude={'password'})
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Creating expose link with data: {link_dict}")
            logger.info(f"preset_data value: {link_dict.get('preset_data')}")
            
            # Extract preset_data separately to ensure it's properly set
            preset_data = link_dict.pop('preset_data', {})
            
            link = ExposeLink(
                **link_dict,
                link_id=link_id,
                tenant_id=property.tenant_id,
                created_by=current_user.id
            )
            
            # Explicitly set preset_data after creation
            link.preset_data = preset_data or {}
            
            # Log the actual preset_data being set
            logger.info(f"Setting link.preset_data to: {link.preset_data}")
            
            # Hash password if provided
            if link_data.password_protected and password:
                link.password_hash = get_password_hash(password)
            
            db.add(link)
            db.flush()
            
            # Debug - check if preset_data was saved
            logger.info(f"After flush - link.preset_data: {link.preset_data}")
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="EXPOSE_LINK_CREATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="expose_link",
                resource_id=link.id,
                new_values={
                    "property_id": str(property.id),
                    "link_id": link_id
                }
            )
            
            # Load relationships for response
            db.refresh(link)
            
            # Eagerly load property with project for response mapping
            link = db.query(ExposeLink).options(
                joinedload(ExposeLink.property).joinedload(Property.project),
                joinedload(ExposeLink.template)
            ).filter(ExposeLink.id == link.id).first()
            
            # Final debug check
            logger.info(f"Final link.preset_data before return: {link.preset_data}")
            
            return link
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to create expose link: {str(e)}"
            )
    
    @staticmethod
    def get_expose_link(
        db: Session,
        link_id: str,
        password: Optional[str] = None,
        track_view: bool = False,
        viewer_info: Optional[Dict[str, Any]] = None
    ) -> ExposeLink:
        """Get an expose link by link ID (public access)"""
        try:
            link = db.query(ExposeLink).options(
                joinedload(ExposeLink.property).joinedload(Property.images),
                joinedload(ExposeLink.property).joinedload(Property.project).joinedload(Project.city_ref),
                joinedload(ExposeLink.property).joinedload(Property.project).joinedload(Project.images),
                joinedload(ExposeLink.template)
            ).filter(
                ExposeLink.link_id == link_id
            ).first()
            
            if not link:
                raise AppException(
                    status_code=404,
                    detail="Expose link not found"
                )
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Retrieved expose link {link_id}: preset_data = {link.preset_data}")
            
            # Check if link is active
            if not link.is_active:
                raise AppException(
                    status_code=403,
                    detail="This expose link is no longer active"
                )
            
            # Check expiration
            if link.expiration_date:
                # Ensure both datetimes are timezone-aware for comparison
                current_time = datetime.now(timezone.utc)
                expiration_time = link.expiration_date
                if expiration_time.tzinfo is None:
                    # If expiration_date is naive, assume it's UTC
                    expiration_time = expiration_time.replace(tzinfo=timezone.utc)
                
                if expiration_time < current_time:
                    raise AppException(
                        status_code=403,
                        detail="This expose link has expired"
                    )
            
            # Check password
            if link.password_protected:
                if not password:
                    raise AppException(
                        status_code=401,
                        detail="Password required"
                    )
                if not verify_password(password, link.password_hash):
                    raise AppException(
                        status_code=401,
                        detail="Invalid password"
                    )
            
            # Track view if requested
            if track_view:
                ExposeService._track_view(db, link, viewer_info)
            
            return link
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to retrieve expose link: {str(e)}"
            )
    
    @staticmethod
    def list_expose_links(
        db: Session,
        current_user: User,
        property_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[ExposeLink]:
        """List expose links - users only see links they created"""
        try:
            query = db.query(ExposeLink).options(
                joinedload(ExposeLink.property).joinedload(Property.project)
            )
            
            # Always filter by current tenant (even for super admins)
            query = query.filter(ExposeLink.tenant_id == current_user.tenant_id)
            
            # Filter by created_by to ensure users only see their own links
            query = query.filter(ExposeLink.created_by == current_user.id)
            
            if property_id:
                query = query.filter(ExposeLink.property_id == property_id)
            
            if is_active is not None:
                query = query.filter(ExposeLink.is_active == is_active)
            
            # Order by creation date (newest first)
            links = query.order_by(ExposeLink.created_at.desc()).all()
            
            return links
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to list expose links: {str(e)}"
            )
    
    @staticmethod
    def list_expose_links_with_details(
        db: Session,
        current_user: User,
        property_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List expose links and return formatted response data with property details"""
        try:
            # Get the expose links with all relationships loaded
            links = ExposeService.list_expose_links(db, current_user, property_id, is_active)
            
            # Use mapper to convert to response format
            return map_expose_links_to_responses(links)
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to list expose links with details: {str(e)}"
            )
    
    @staticmethod
    def update_expose_link(
        db: Session,
        link_id: UUID,
        link_data: ExposeLinkUpdate,
        current_user: User
    ) -> ExposeLink:
        """Update an expose link"""
        try:
            # Get link by UUID (not link_id string)
            query = db.query(ExposeLink)
            
            # Always filter by current tenant (even for super admins)
            query = query.filter(ExposeLink.tenant_id == current_user.tenant_id)
            
            link = query.filter(ExposeLink.id == link_id).first()
            
            if not link:
                raise AppException(
                    status_code=404,
                    detail="Expose link not found"
                )
            
            # Check permissions
            is_owner = link.created_by == current_user.id
            if not current_user.is_super_admin and not is_owner:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "expose:edit_content" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to edit expose links"
                    )
            
            # Update fields
            update_data = link_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(link, field, value)
            
            link.updated_by = current_user.id
            link.updated_at = datetime.now(timezone.utc)
            
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="EXPOSE_LINK_UPDATED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="expose_link",
                resource_id=link.id,
                new_values={"updated_fields": list(update_data.keys())}
            )
            
            # Load relationships for response
            db.refresh(link)
            
            # Eagerly load property with project for response mapping
            link = db.query(ExposeLink).options(
                joinedload(ExposeLink.property).joinedload(Property.project),
                joinedload(ExposeLink.template)
            ).filter(ExposeLink.id == link.id).first()
            
            return link
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to update expose link: {str(e)}"
            )
    
    @staticmethod
    def delete_expose_link(
        db: Session,
        link_id: UUID,
        current_user: User
    ) -> None:
        """Delete an expose link"""
        try:
            # Get link by UUID (not link_id string)
            query = db.query(ExposeLink)
            
            # Always filter by current tenant (even for super admins)
            query = query.filter(ExposeLink.tenant_id == current_user.tenant_id)
            
            link = query.filter(ExposeLink.id == link_id).first()
            
            if not link:
                raise AppException(
                    status_code=404,
                    detail="Expose link not found"
                )
            
            # Check permissions - only creator or admin can delete
            if not current_user.is_super_admin and link.created_by != current_user.id:
                raise AppException(
                    status_code=403,
                    detail="You can only delete your own expose links"
                )
            
            # Log activity before deletion
            audit_logger.log_business_event(
                db=db,
                action="EXPOSE_LINK_DELETED",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="expose_link",
                resource_id=link.id,
                old_values={"link_id": link.link_id}
            )
            
            db.delete(link)
            db.flush()
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to delete expose link: {str(e)}"
            )
    
    @staticmethod
    def _generate_link_id(db: Session) -> str:
        """Generate a unique link ID"""
        while True:
            # Generate 8 character alphanumeric ID
            link_id = ''.join(
                secrets.choice(string.ascii_letters + string.digits)
                for _ in range(8)
            )
            
            # Check if it already exists
            existing = db.query(ExposeLink).filter(
                ExposeLink.link_id == link_id
            ).first()
            
            if not existing:
                return link_id
    
    @staticmethod
    def _track_view(
        db: Session,
        link: ExposeLink,
        viewer_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track a view of an expose link"""
        try:
            # Create view record
            view = ExposeLinkView(
                expose_link_id=link.id,
                tenant_id=link.tenant_id,
                viewed_at=datetime.now(timezone.utc),
                ip_address=viewer_info.get("ip_address") if viewer_info else None,
                user_agent=viewer_info.get("user_agent") if viewer_info else None,
                referrer=viewer_info.get("referrer") if viewer_info else None
            )
            
            db.add(view)
            
            # Update link view count and timestamps
            link.view_count += 1
            link.last_viewed_at = datetime.now(timezone.utc)
            if not link.first_viewed_at:
                link.first_viewed_at = datetime.now(timezone.utc)
            
            db.flush()
            
        except Exception:
            # Don't fail the request if tracking fails
            pass
    
    @staticmethod
    def get_expose_link_stats(
        db: Session,
        link_id: UUID,
        current_user: User
    ) -> Dict[str, Any]:
        """Get statistics for an expose link"""
        try:
            # Get link by UUID
            query = db.query(ExposeLink)
            
            # Always filter by current tenant (even for super admins)
            query = query.filter(ExposeLink.tenant_id == current_user.tenant_id)
            
            link = query.filter(ExposeLink.id == link_id).first()
            
            if not link:
                raise AppException(
                    status_code=404,
                    detail="Expose link not found"
                )
            
            # Get view details
            views = db.query(ExposeLinkView).filter(
                ExposeLinkView.expose_link_id == link.id
            ).order_by(ExposeLinkView.viewed_at.desc()).all()
            
            # Get unique viewers
            unique_ips = set(v.ip_address for v in views if v.ip_address)
            
            # Get views by date
            views_by_date = {}
            for view in views:
                date_key = view.viewed_at.date().isoformat()
                views_by_date[date_key] = views_by_date.get(date_key, 0) + 1
            
            return {
                "link_id": link.link_id,
                "created_at": link.created_at,
                "total_views": link.view_count,
                "unique_viewers": len(unique_ips),
                "first_viewed_at": link.first_viewed_at,
                "last_viewed_at": link.last_viewed_at,
                "views_by_date": views_by_date,
                "recent_views": [
                    {
                        "viewed_at": v.viewed_at,
                        "ip_address": v.ip_address,
                        "user_agent": v.user_agent,
                        "referrer": v.referrer
                    }
                    for v in views[:10]  # Last 10 views
                ]
            }
            
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to get expose link statistics: {str(e)}"
            )