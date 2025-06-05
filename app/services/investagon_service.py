# ================================
# INVESTAGON SERVICE (services/investagon_service.py)
# ================================

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
import logging
from decimal import Decimal

from app.config import settings
from app.core.exceptions import AppException
from app.models.business import Property, InvestagonSync
from app.models.user import User
from app.utils.audit import AuditLogger
from app.services.rbac_service import RBACService

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

class InvestagonAPIClient:
    """Client for interacting with Investagon API"""
    
    def __init__(self):
        self.base_url = settings.INVESTAGON_API_URL
        self.organization_id = settings.INVESTAGON_ORGANIZATION_ID
        self.api_key = settings.INVESTAGON_API_KEY
        self.timeout = 30.0
        
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters for API requests"""
        if not self.organization_id or not self.api_key:
            raise AppException(
                status_code=503,
                detail="Investagon API credentials not configured"
            )
        return {
            "organization_id": self.organization_id,
            "api_key": self.api_key
        }
        
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects from Investagon API"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                response = await client.get(
                    f"{self.base_url}/api_projects",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AppException(
                        status_code=401,
                        detail="Invalid Investagon API credentials"
                    )
                else:
                    logger.error(f"Investagon API error: {e.response.status_code} - {e.response.text}")
                    raise AppException(
                        status_code=502,
                        detail=f"Investagon API error: {e.response.status_code}"
                    )
            except httpx.RequestError as e:
                logger.error(f"Request error to Investagon API: {str(e)}")
                raise AppException(
                    status_code=502,
                    detail="Failed to connect to Investagon API"
                )
    
    async def get_project_by_id(self, project_id: str) -> Dict[str, Any]:
        """Get a single project details from Investagon API"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                response = await client.get(
                    f"{self.base_url}/api_projects/{project_id}",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise AppException(
                        status_code=404,
                        detail=f"Project not found in Investagon: {project_id}"
                    )
                elif e.response.status_code == 401:
                    raise AppException(
                        status_code=401,
                        detail="Invalid Investagon API credentials"
                    )
                else:
                    logger.error(f"Investagon API error: {e.response.status_code} - {e.response.text}")
                    raise AppException(
                        status_code=502,
                        detail=f"Investagon API error: {e.response.status_code}"
                    )
            except httpx.RequestError as e:
                logger.error(f"Request error to Investagon API: {str(e)}")
                raise AppException(
                    status_code=502,
                    detail="Failed to connect to Investagon API"
                )
    
    async def get_property(self, investagon_id: str) -> Dict[str, Any]:
        """Get a single property from Investagon API"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                response = await client.get(
                    f"{self.base_url}/properties/{investagon_id}",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise AppException(
                        status_code=404,
                        detail=f"Property not found in Investagon: {investagon_id}"
                    )
                elif e.response.status_code == 401:
                    raise AppException(
                        status_code=401,
                        detail="Invalid Investagon API credentials"
                    )
                else:
                    logger.error(f"Investagon API error: {e.response.status_code} - {e.response.text}")
                    raise AppException(
                        status_code=502,
                        detail=f"Investagon API error: {e.response.status_code}"
                    )
            except httpx.RequestError as e:
                logger.error(f"Request error to Investagon API: {str(e)}")
                raise AppException(
                    status_code=502,
                    detail="Failed to connect to Investagon API"
                )

class InvestagonSyncService:
    """Service for syncing property data from Investagon API"""
    
    def __init__(self):
        self.api_client = InvestagonAPIClient()
    
    @staticmethod  
    def _map_investagon_to_property(investagon_data: Dict[str, Any], db: Session = None, tenant_id: UUID = None, user_id: UUID = None) -> Dict[str, Any]:
        """Map Investagon API data to our Property model fields"""
        from app.models.business import City
        
        # Handle city creation/lookup
        city_id = None
        city_name = investagon_data.get("object_city") or "Unknown"
        state_name = investagon_data.get("province") or "Unknown"
        
        if db and tenant_id and user_id and city_name != "Unknown":
            # Clean city and state names for better matching
            city_name = city_name.strip()
            state_name = state_name.strip()
            
            # Look for existing city (case-insensitive match)
            existing_city = db.query(City).filter(
                City.tenant_id == tenant_id,
                City.name.ilike(city_name),
                City.state.ilike(state_name)
            ).first()
            
            if existing_city:
                city_id = existing_city.id
            else:
                # Create new city with proper error handling
                try:
                    new_city = City(
                        tenant_id=tenant_id,
                        name=city_name,
                        state=state_name,
                        country=investagon_data.get("object_country", "Deutschland"),
                        created_by=user_id
                    )
                    db.add(new_city)
                    db.flush()  # Get the ID
                    city_id = new_city.id
                except Exception as e:
                    # If city creation fails, try to find it again (might have been created by another transaction)
                    logger.warning(f"Failed to create city {city_name}, {state_name}: {str(e)}. Trying lookup again.")
                    existing_city = db.query(City).filter(
                        City.tenant_id == tenant_id,
                        City.name.ilike(city_name),
                        City.state.ilike(state_name)
                    ).first()
                    if existing_city:
                        city_id = existing_city.id
                    else:
                        logger.error(f"Could not create or find city {city_name}, {state_name}")
                        city_id = None
        
        # Extract numeric values safely
        def safe_decimal(value, default=0):
            try:
                return Decimal(str(value or default))
            except:
                return Decimal(str(default))
        
        def safe_float(value, default=0):
            try:
                return float(value or default)
            except:
                return float(default)
        
        def safe_int(value, default=None):
            try:
                return int(value) if value is not None else default
            except:
                return default
        
        # Map property type - adjust based on actual API values
        property_type_map = {
            "apartment": "apartment",
            "house": "house",
            "co-living": "co-living",
            "multi-family": "house",
            "single-family": "house"
        }
        api_property_type = investagon_data.get("property_type", "apartment")
        mapped_property_type = property_type_map.get(str(api_property_type).lower(), "apartment")
        
        # Determine property status from active field (0 = sold, 1 = available)
        status = "available" if investagon_data.get("active") == 1 else "sold"
        
        # Extract apartment number from the full string (e.g., "Friedrich-Engels-Bogen / WHG 103" -> "WHG 103")
        raw_apartment = investagon_data.get("object_apartment_number", "")
        if "/" in raw_apartment:
            # Take the part after the last "/" and strip whitespace
            apartment_number = raw_apartment.split("/")[-1].strip()
        else:
            apartment_number = raw_apartment
        
        return {
            # Basic Information
            "street": investagon_data.get("object_street", ""),
            "house_number": investagon_data.get("object_house_number", ""),
            "apartment_number": apartment_number,
            "city": city_name,
            "city_id": city_id,
            "state": state_name, 
            "country": investagon_data.get("object_country", "Deutschland"),
            "zip_code": investagon_data.get("object_postal_code") or "00000",
            "latitude": safe_float(investagon_data.get("lat")) if investagon_data.get("lat") else None,
            "longitude": safe_float(investagon_data.get("lng")) if investagon_data.get("lng") else None,
            "property_type": mapped_property_type,
            
            # Property Details
            "size_sqm": safe_float(investagon_data.get("object_size", 0)),
            "rooms": safe_float(investagon_data.get("object_rooms", 0)),
            "bathrooms": safe_int(investagon_data.get("object_bathrooms")),
            "floor": safe_int(investagon_data.get("object_floor")),
            "total_floors": safe_int(investagon_data.get("object_total_floors")),
            "construction_year": safe_int(investagon_data.get("object_building_year")),
            "renovation_year": safe_int(investagon_data.get("object_renovation_year")),
            
            # Financial Data
            "purchase_price": safe_decimal(investagon_data.get("purchase_price_apartment", 0)),
            "purchase_price_parking": safe_decimal(investagon_data.get("purchase_price_parking", 0)),
            "purchase_price_furniture": safe_decimal(investagon_data.get("purchase_price_furniture", 0)),
            "monthly_rent": safe_decimal(investagon_data.get("rent_apartment_month", 0)),
            "rent_parking_month": safe_decimal(investagon_data.get("rent_parking_month", 0)),
            "additional_costs": safe_decimal(investagon_data.get("additional_costs", 0)),
            "management_fee": safe_decimal(investagon_data.get("property_management_fee", 0)) or safe_decimal(investagon_data.get("property_management_fee_sev", 0)),
            
            # Transaction Costs (as percentages)
            "transaction_broker_rate": safe_decimal(investagon_data.get("transaction_broker_rate", 0)),
            "transaction_tax_rate": safe_decimal(investagon_data.get("transaction_tax_rate", 0)),
            "transaction_notary_rate": safe_decimal(investagon_data.get("transaction_notary_rate", 0)),
            "transaction_register_rate": safe_decimal(investagon_data.get("transaction_register_rate", 0)),
            
            # Operating Costs
            "operation_cost_landlord": safe_decimal(investagon_data.get("operation_cost_landlord_apartment", 0)),
            "operation_cost_tenant": safe_decimal(investagon_data.get("operation_cost_tenant_apartment", 0)),
            "operation_cost_reserve": safe_decimal(investagon_data.get("operation_cost_reserve_apartment", 0)),
            
            # Additional Property Data
            "object_share_owner": safe_float(investagon_data.get("object_share_owner", 0)),
            "share_land": safe_float(investagon_data.get("share_land", 0)),
            "property_usage": investagon_data.get("property_usage"),
            "initial_maintenance_expenses": safe_decimal(investagon_data.get("initial_investment_extra_1y_manual", 0)),
            
            # Depreciation Settings
            "degressive_depreciation_building_onoff": safe_int(investagon_data.get("degressive_depreciation_building_onoff", -1)),
            "depreciation_rate_building_manual": safe_float(investagon_data.get("depreciation_rate_building_manual", 0)),
            
            # Energy Data
            "energy_certificate_type": investagon_data.get("energy_certificate_type"),
            "energy_consumption": safe_float(investagon_data.get("power_consumption")) if investagon_data.get("power_consumption") else None,
            "energy_class": investagon_data.get("energy_efficiency_class"),
            "heating_type": investagon_data.get("heating_type"),
            
            # Status
            "status": status,
            
            # Investagon Status Flags
            "active": safe_int(investagon_data.get("active", 0)),
            "pre_sale": safe_int(investagon_data.get("pre_sale", 0)),
            "draft": safe_int(investagon_data.get("draft", 0)),
            
            # Investagon Integration
            "investagon_id": str(investagon_data.get("id", "")),
            "investagon_data": investagon_data,  # Store full data for reference
            "last_sync": datetime.now(timezone.utc),
        }
    
    async def sync_single_property(
        self,
        db: Session,
        investagon_id: str,
        current_user: User
    ) -> Property:
        """Sync a single property from Investagon"""
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "investagon:sync" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to sync from Investagon"
                    )
            
            # Get property data from Investagon
            investagon_data = await self.api_client.get_property(investagon_id)
            
            # Extract the actual investagon_id from the API response
            actual_investagon_id = str(investagon_data.get("id", ""))
            
            # Check if property already exists using the actual investagon_id
            existing_property = db.query(Property).filter(
                and_(
                    Property.investagon_id == actual_investagon_id,
                    Property.tenant_id == current_user.tenant_id
                )
            ).first()
            
            # Map data
            property_data = self._map_investagon_to_property(investagon_data, db, current_user.tenant_id, current_user.id)
            
            if existing_property:
                # Update existing property
                for key, value in property_data.items():
                    if key != "investagon_data":  # Skip JSON field for now
                        setattr(existing_property, key, value)
                existing_property.updated_by = current_user.id
                existing_property.updated_at = datetime.now(timezone.utc)
                
                property_obj = existing_property
                action = "UPDATE"
            else:
                # Create new property
                property_obj = Property(
                    **property_data,
                    tenant_id=current_user.tenant_id,
                    created_by=current_user.id
                )
                db.add(property_obj)
                action = "CREATE"
            
            # Record sync
            sync_record = InvestagonSync(
                tenant_id=current_user.tenant_id,
                sync_type="single_property",
                status="completed",
                properties_created=1 if action == "CREATE" else 0,
                properties_updated=1 if action == "UPDATE" else 0,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                created_by=current_user.id
            )
            db.add(sync_record)
            
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action=f"INVESTAGON_SYNC_{action}",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property_obj.id,
                new_values={
                    "investagon_id": investagon_id,
                    "street": property_obj.street,
                    "apartment_number": property_obj.apartment_number
                }
            )
            
            return property_obj
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to sync property from Investagon: {str(e)}")
            
            # Record failed sync
            sync_record = InvestagonSync(
                tenant_id=current_user.tenant_id,
                sync_type="single_property",
                status="failed",
                error_details={"error": str(e)},
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                created_by=current_user.id
            )
            db.add(sync_record)
            db.flush()
            
            raise AppException(
                status_code=500,
                detail=f"Failed to sync property: {str(e)}"
            )
    
    async def sync_all_properties(
        self,
        db: Session,
        current_user: User,
        modified_since: Optional[datetime] = None
    ) -> InvestagonSync:
        """Sync all properties from Investagon for the tenant"""
        sync_record = None
        
        try:
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "investagon:sync" not in [p["name"] for p in permissions.get("permissions", [])]:
                    raise AppException(
                        status_code=403,
                        detail="You don't have permission to sync from Investagon"
                    )
            
            # Create sync record
            sync_record = InvestagonSync(
                tenant_id=current_user.tenant_id,
                sync_type="full" if not modified_since else "incremental",
                status="in_progress",
                started_at=datetime.now(timezone.utc),
                created_by=current_user.id
            )
            db.add(sync_record)
            db.flush()
            
            # Track sync stats
            total_synced = 0
            total_created = 0
            total_updated = 0
            total_errors = 0
            errors = []
            
            # Get existing property mapping
            existing_properties = {}
            properties_query = db.query(Property).filter(
                Property.tenant_id == current_user.tenant_id
            )
            if modified_since:
                properties_query = properties_query.filter(
                    Property.investagon_id.isnot(None)
                )
            
            for prop in properties_query.all():
                if prop.investagon_id:
                    existing_properties[prop.investagon_id] = prop
            
            # First, get all projects
            try:
                projects = await self.api_client.get_projects()
                logger.info(f"Found {len(projects)} projects to sync")
                
                # Process each project
                for project in projects:
                    project_id = project.get("id")
                    if not project_id:
                        continue
                    
                    try:
                        # Get project details including property list
                        project_details = await self.api_client.get_project_by_id(project_id)
                        property_urls = project_details.get("properties", [])
                        
                        logger.info(f"Project {project_id} has {len(property_urls)} properties")
                        
                        # Process each property URL
                        for property_url in property_urls:
                            # Create a savepoint for each property to allow partial rollback
                            savepoint = db.begin_nested()
                            try:
                                # Extract property ID from URL (format: /api/api_properties/{id})
                                if "/api_properties/" in property_url:
                                    property_id = property_url.split("/api_properties/")[-1]
                                else:
                                    logger.warning(f"Unexpected property URL format: {property_url}")
                                    continue
                                
                                # Get property details
                                investagon_data = await self.api_client.get_property(property_id)
                                
                                # Add project information to property data
                                investagon_data["project_id"] = project_id
                                investagon_data["project_name"] = project_details.get("name", "")
                                
                                # Map property data
                                property_data = self._map_investagon_to_property(investagon_data, db, current_user.tenant_id, current_user.id)
                                
                                # Use the investagon_id from the API response, not the URL property_id
                                investagon_id = str(investagon_data.get("id", ""))
                                
                                if investagon_id in existing_properties:
                                    # Update existing
                                    prop = existing_properties[investagon_id]
                                    for key, value in property_data.items():
                                        if key != "investagon_data":  # Skip JSON field for now
                                            setattr(prop, key, value)
                                    prop.updated_by = current_user.id
                                    prop.updated_at = datetime.now(timezone.utc)
                                    total_updated += 1
                                else:
                                    # Create new
                                    prop = Property(
                                        **property_data,
                                        tenant_id=current_user.tenant_id,
                                        created_by=current_user.id
                                    )
                                    db.add(prop)
                                    total_created += 1
                                
                                # Commit the savepoint
                                savepoint.commit()
                                total_synced += 1
                                
                                # Flush every 50 properties to avoid memory issues
                                if total_synced % 50 == 0:
                                    db.flush()
                                    logger.info(f"Synced {total_synced} properties so far...")
                                
                            except Exception as e:
                                # Rollback only this property's savepoint, not the entire transaction
                                savepoint.rollback()
                                total_errors += 1
                                errors.append({
                                    "property_id": property_id,
                                    "investagon_id": investagon_data.get("id") if 'investagon_data' in locals() else None,
                                    "project_id": project_id,
                                    "error": str(e)
                                })
                                logger.error(f"Error syncing property {property_id}: {str(e)}")
                        
                    except Exception as e:
                        logger.error(f"Error processing project {project_id}: {str(e)}")
                        errors.append({
                            "project_id": project_id,
                            "error": str(e)
                        })
                
                # Final flush
                db.flush()
                
            except Exception as e:
                logger.error(f"Error fetching projects from Investagon: {str(e)}")
                raise AppException(
                    status_code=502,
                    detail=f"Failed to fetch projects from Investagon: {str(e)}"
                )
            
            # Update sync record
            sync_record.status = "completed" if total_errors == 0 else "partial"
            sync_record.properties_created = total_created
            sync_record.properties_updated = total_updated
            sync_record.properties_failed = total_errors
            sync_record.completed_at = datetime.now(timezone.utc)
            
            if errors:
                sync_record.error_details = {"message": f"Synced with {total_errors} errors", "errors": errors}
            
            db.flush()
            
            # Log activity
            audit_logger.log_business_event(
                db=db,
                action="INVESTAGON_SYNC_BULK",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="investagon_sync",
                resource_id=sync_record.id,
                new_values={
                    "type": sync_record.sync_type,
                    "synced": total_synced,
                    "created": total_created,
                    "updated": total_updated,
                    "errors": total_errors
                }
            )
            
            return sync_record
            
        except AppException:
            if sync_record:
                sync_record.status = "failed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_details = {"error": "Permission denied"}
                db.flush()
            raise
        except Exception as e:
            logger.error(f"Failed to sync properties from Investagon: {str(e)}")
            
            if sync_record:
                sync_record.status = "failed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_details = {"error": str(e)}
                db.flush()
            
            raise AppException(
                status_code=500,
                detail=f"Failed to sync properties: {str(e)}"
            )
    
    @staticmethod
    def get_sync_history(
        db: Session,
        current_user: User,
        limit: int = 10
    ) -> List[InvestagonSync]:
        """Get sync history for the tenant"""
        try:
            query = db.query(InvestagonSync)
            
            # Apply tenant filter if not super admin
            if not current_user.is_super_admin:
                query = query.filter(InvestagonSync.tenant_id == current_user.tenant_id)
            
            # Order by most recent first
            syncs = query.order_by(InvestagonSync.started_at.desc()).limit(limit).all()
            
            return syncs
            
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"Failed to get sync history: {str(e)}"
            )
    
    @staticmethod
    def _calculate_duration(started_at: Optional[datetime], completed_at: Optional[datetime]) -> Optional[float]:
        """Calculate duration between two datetimes, handling timezone issues"""
        if not started_at or not completed_at:
            return None
        
        try:
            # Ensure both are timezone-aware
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            
            return (completed_at - started_at).total_seconds()
        except:
            return None
    
    @staticmethod
    def can_sync(db: Session, current_user: User) -> Dict[str, Any]:
        """Check if sync is allowed and when it can be performed"""
        try:
            # Check if API is configured
            if not settings.INVESTAGON_ORGANIZATION_ID or not settings.INVESTAGON_API_KEY:
                return {
                    "can_sync": False,
                    "reason": "Investagon API not configured"
                }
            
            # Check permissions
            if not current_user.is_super_admin:
                permissions = RBACService.get_user_permissions(
                    db, current_user.id, current_user.tenant_id
                )
                if "investagon:sync" not in [p["name"] for p in permissions.get("permissions", [])]:
                    return {
                        "can_sync": False,
                        "reason": "No permission to sync from Investagon"
                    }
            
            # Check if sync is already in progress
            in_progress = db.query(InvestagonSync).filter(
                and_(
                    InvestagonSync.tenant_id == current_user.tenant_id,
                    InvestagonSync.status == "in_progress"
                )
            ).first()
            
            if in_progress:
                return {
                    "can_sync": False,
                    "reason": "Sync already in progress",
                    "started_at": in_progress.started_at.isoformat()
                }
            
            # Check rate limiting (max 1 full sync per hour)
            last_full_sync = db.query(InvestagonSync).filter(
                and_(
                    InvestagonSync.tenant_id == current_user.tenant_id,
                    InvestagonSync.sync_type == "full",
                    InvestagonSync.status.in_(["completed", "partial"])
                )
            ).order_by(InvestagonSync.completed_at.desc()).first()
            
            if last_full_sync and last_full_sync.completed_at:
                # Ensure we have timezone-aware datetime
                completed_at = last_full_sync.completed_at
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                
                time_since_last = datetime.now(timezone.utc) - completed_at
                if time_since_last < timedelta(hours=1):
                    next_allowed = completed_at + timedelta(hours=1)
                    return {
                        "can_sync": False,
                        "reason": "Rate limit: Full sync allowed once per hour",
                        "next_allowed_at": next_allowed.isoformat(),
                        "last_sync": completed_at.isoformat()
                    }
            
            # Get the most recent sync (any status)
            recent_sync = db.query(InvestagonSync).filter(
                InvestagonSync.tenant_id == current_user.tenant_id
            ).order_by(InvestagonSync.started_at.desc()).first()
            
            return {
                "can_sync": True,
                "last_completed_sync": last_full_sync.completed_at.isoformat() if last_full_sync and last_full_sync.completed_at else None,
                "current_status": {
                    "id": str(recent_sync.id),
                    "type": recent_sync.sync_type,
                    "status": recent_sync.status,
                    "started_at": recent_sync.started_at.isoformat() if recent_sync.started_at else None,
                    "completed_at": recent_sync.completed_at.isoformat() if recent_sync.completed_at else None,
                    "properties_created": recent_sync.properties_created,
                    "properties_updated": recent_sync.properties_updated,
                    "properties_failed": recent_sync.properties_failed,
                    "error_details": recent_sync.error_details,
                    "duration_seconds": InvestagonSyncService._calculate_duration(recent_sync.started_at, recent_sync.completed_at)
                } if recent_sync else None
            }
            
        except Exception as e:
            logger.error(f"Error checking sync status: {str(e)}")
            return {
                "can_sync": False,
                "reason": "Error checking sync status"
            }