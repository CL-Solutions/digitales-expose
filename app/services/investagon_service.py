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
from io import BytesIO
import mimetypes

from app.config import settings
from app.core.exceptions import AppException
from app.models.business import Property, InvestagonSync, PropertyImage, Project, ProjectImage
from app.models.user import User
from app.utils.audit import AuditLogger
from app.utils.location_utils import normalize_state_name
from app.services.rbac_service import RBACService
from app.services.s3_service import get_s3_service
from app.services.google_maps_service import GoogleMapsService

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()

class InvestagonAPIClient:
    """Client for interacting with Investagon API"""
    
    def __init__(self, organization_id: str, api_key: str):
        self.base_url = settings.INVESTAGON_API_URL
        self.organization_id = organization_id
        self.api_key = api_key
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
    
    async def get_project_with_photos(self, project_id: str) -> Dict[str, Any]:
        """Get project details including photos from Investagon API"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                response = await client.get(
                    f"{self.base_url}/projects/{project_id}",
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
    
    def __init__(self, api_client: Optional[InvestagonAPIClient] = None):
        self.api_client = api_client
    
    @staticmethod
    def get_tenant_api_client(db: Session, tenant_id: UUID) -> Optional[InvestagonAPIClient]:
        """Get InvestagonAPIClient configured with tenant credentials"""
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return None
            
        if not tenant.investagon_organization_id or not tenant.investagon_api_key:
            return None
            
        return InvestagonAPIClient(
            organization_id=tenant.investagon_organization_id,
            api_key=tenant.investagon_api_key
        )
    
    @staticmethod
    def _map_investagon_to_project(investagon_data: Dict[str, Any], db: Session = None, tenant_id: UUID = None, user_id: UUID = None, property_address: Dict[str, Any] = None) -> Dict[str, Any]:
        """Map Investagon API project data to our Project model fields
        
        Args:
            investagon_data: Project data from Investagon API
            db: Database session
            tenant_id: Tenant ID
            user_id: User ID
            property_address: Optional dict with address info from a property (street, house_number, city, state, zip_code)
        """
        from app.models.business import City
        
        # Get project name
        project_name = investagon_data.get("name", "")
        
        # Initialize address fields
        street = ""
        house_number = ""
        zip_code = ""
        city_name = "Unknown"
        state_name = "Unknown"  # Default for projects without state info
        
        # If property address is provided, use it (most reliable source)
        if property_address:
            street = property_address.get("street", "")
            house_number = property_address.get("house_number", "")
            city_name = property_address.get("city", "Unknown")
            state_name = normalize_state_name(property_address.get("state", state_name)) or property_address.get("state", state_name)
            zip_code = property_address.get("zip_code", "")
        else:
            # Fallback: Try to extract from project name (less reliable)
            parts = project_name.split(",")
            
            if len(parts) >= 2:
                # First part might be street and house number
                street_parts = parts[0].strip().split()
                if street_parts:
                    # Check if last part is a number
                    if street_parts[-1] and street_parts[-1][0].isdigit():
                        house_number = street_parts[-1]
                        street = " ".join(street_parts[:-1])
                    else:
                        street = " ".join(street_parts)
                
                # Second part might be zip and city
                city_parts = parts[1].strip().split()
                if city_parts:
                    # Check if first part is a zip code (5 digits)
                    if city_parts[0].isdigit() and len(city_parts[0]) == 5:
                        zip_code = city_parts[0]
                        city_name = " ".join(city_parts[1:])
                    else:
                        city_name = " ".join(city_parts)
        
        # Handle city creation/lookup
        city_id = None
        
        if db and tenant_id and user_id and city_name != "Unknown":
            # Look for existing city
            existing_city = db.query(City).filter(
                City.tenant_id == tenant_id,
                City.name.ilike(city_name)
            ).first()
            
            if existing_city:
                city_id = existing_city.id
                # Update state if we have better info from property
                if property_address and property_address.get("state"):
                    state_name = normalize_state_name(property_address.get("state")) or property_address.get("state")
            else:
                # Create new city
                try:
                    # Ensure state_name has a valid value
                    final_state = normalize_state_name(state_name) if state_name else "Unknown"
                    new_city = City(
                        tenant_id=tenant_id,
                        name=city_name,
                        state=final_state,
                        country="Deutschland",
                        created_by=user_id
                    )
                    db.add(new_city)
                    db.flush()
                    city_id = new_city.id
                except Exception as e:
                    logger.warning(f"Failed to create city {city_name}: {str(e)}")
                    city_id = None
        
        # If we have address info, update the project name to be more descriptive
        if street and house_number:
            display_name = f"{street} {house_number}, {city_name}"
        else:
            display_name = project_name
        
        result = {
            "name": display_name,
            "street": street,
            "house_number": house_number,
            "city": city_name,
            "city_id": city_id,
            "state": normalize_state_name(state_name) or state_name or "Unknown",
            "country": "Deutschland",
            "zip_code": zip_code,
            "status": "active",
            "investagon_id": str(investagon_data.get("id", "")),
            "investagon_data": investagon_data
        }
        
        # Add latitude, longitude, and construction year if provided in property_address
        if property_address:
            if property_address.get("latitude") is not None:
                result["latitude"] = property_address["latitude"]
            if property_address.get("longitude") is not None:
                result["longitude"] = property_address["longitude"]
            if property_address.get("construction_year") is not None:
                result["construction_year"] = int(property_address["construction_year"])
        
        return result
    
    @staticmethod  
    def _map_investagon_to_property(investagon_data: Dict[str, Any], db: Session = None, tenant_id: UUID = None, user_id: UUID = None, project_id: UUID = None) -> Dict[str, Any]:
        """Map Investagon API data to our Property model fields"""
        from app.models.business import City
        
        # Handle city creation/lookup
        city_id = None
        city_name = investagon_data.get("object_city") or "Unknown"
        # Get state with proper fallback - default to Unknown if no state provided
        raw_state = investagon_data.get("province")
        state_name = normalize_state_name(raw_state) if raw_state else None
        if not state_name:
            # Default to Unknown for properties without state info
            state_name = "Unknown"
        
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
        
        # Extract unit number from the full string (e.g., "Friedrich-Engels-Bogen / WHG 103" -> "WHG 103")
        raw_apartment = investagon_data.get("object_apartment_number") or ""
        if raw_apartment and "/" in raw_apartment:
            # Take the part after the last "/" and strip whitespace
            unit_number = raw_apartment.split("/")[-1].strip()
        else:
            unit_number = raw_apartment or ""
        
        # Clean up unit number - extract just the number part
        import re
        if unit_number:
            # Common patterns: "WE13", "WE 13", "WHG 103", "Whg.15", etc.
            # Extract just the numeric part
            match = re.search(r'(\d+)', unit_number)
            if match:
                unit_number = match.group(1)
            else:
                # If no number found, keep the original (might be text like "Penthouse")
                # But still try to remove common prefixes
                unit_number = re.sub(r'^(WE|WHG|Whg\.?|Apt\.?|Apartment|Wohnung)\s*', '', 
                                   unit_number, flags=re.IGNORECASE).strip() or unit_number
        
        return {
            # Basic Information
            "project_id": project_id,  # This must be set by the caller
            "unit_number": unit_number or "Unknown",
            "city": city_name,
            "city_id": city_id,
            "state": normalize_state_name(state_name) or state_name, 
            "zip_code": investagon_data.get("object_postal_code") or "00000",
            "property_type": mapped_property_type,
            
            # Property Details
            "size_sqm": safe_float(investagon_data.get("object_size", 0)),
            "rooms": safe_float(investagon_data.get("object_rooms", 0)),
            "bathrooms": safe_int(investagon_data.get("object_bathrooms")),
            "floor": investagon_data.get("object_floor"),  # Keep as string (e.g., "1. OG", "2. OG Mitte")
            "balcony": bool(investagon_data.get("balcony")) if investagon_data.get("balcony") is not None else None,
            
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
            # Convert percentage values (e.g., 3 for 3%) to decimal (0.03)
            "object_share_owner": safe_float(investagon_data.get("object_share_owner", 0)) / 100 if investagon_data.get("object_share_owner") is not None else None,
            "share_land": safe_float(investagon_data.get("share_land", 0)) / 100 if investagon_data.get("share_land") is not None else None,
            "property_usage": investagon_data.get("property_usage"),
            "initial_maintenance_expenses": safe_decimal(investagon_data.get("initial_investment_extra_1y_manual", 0)),
            
            # Depreciation Settings
            "degressive_depreciation_building_onoff": safe_int(investagon_data.get("degressive_depreciation_building_onoff", -1)),
            "depreciation_rate_building_manual": safe_float(investagon_data.get("depreciation_rate_building_manual", 0)),
            
            # Energy Data
            "energy_certificate_type": investagon_data.get("energy_certificate_type"),
            "energy_consumption": safe_float(investagon_data.get("power_consumption")) if investagon_data.get("power_consumption") is not None else None,
            "energy_class": investagon_data.get("energy_efficiency_class").upper() if investagon_data.get("energy_efficiency_class") else None,
            "heating_type": investagon_data.get("heating_type"),
            # Note: primary_energy_consumption is not provided by Investagon API
            
            # Investagon Status Flags
            "active": safe_int(investagon_data.get("active", 0)),
            "pre_sale": safe_int(investagon_data.get("pre_sale", 0)),
            "draft": safe_int(investagon_data.get("draft", 0)),
            "visibility": safe_int(investagon_data.get("visibility"), -1),  # Use -1 as default instead of None to avoid index issues
            
            # Investagon Integration
            "investagon_id": str(investagon_data.get("id", "")),
            "investagon_data": investagon_data,  # Store full data for reference
            "last_sync": datetime.now(timezone.utc)
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
            
            # Get tenant-specific API client
            if not self.api_client:
                self.api_client = self.get_tenant_api_client(db, current_user.tenant_id)
                if not self.api_client:
                    raise AppException(
                        status_code=503,
                        detail="Investagon API credentials not configured for this tenant"
                    )
            
            # Get property data from Investagon
            investagon_data = await self.api_client.get_property(investagon_id)
            
            # Extract the actual investagon_id from the API response
            actual_investagon_id = str(investagon_data.get("id", ""))
            
            # First, we need to find out which project this property belongs to
            # Get all projects to find the one containing this property
            projects = await self.api_client.get_projects()
            project_obj = None
            
            for project in projects:
                project_id = str(project.get("id", ""))
                if not project_id:
                    continue
                
                # Get project details to check if it contains our property
                project_details = await self.api_client.get_project_by_id(project_id)
                property_urls = project_details.get("properties") or []
                
                # Check if this property is in this project
                for prop_url in property_urls:
                    if not prop_url:
                        continue
                    if f"/api_properties/{investagon_id}" in prop_url or f"/api_properties/{actual_investagon_id}" in prop_url:
                        # Found the project - extract address from property data
                        property_address = {
                            "street": investagon_data.get("object_street"),
                            "house_number": investagon_data.get("object_house_number"),
                            "city": investagon_data.get("object_city"),
                            "state": investagon_data.get("province"),
                            "zip_code": investagon_data.get("object_postal_code"),
                            "latitude": investagon_data.get("latitude") or investagon_data.get("object_latitude") or investagon_data.get("lat"),
                            "longitude": investagon_data.get("longitude") or investagon_data.get("object_longitude") or investagon_data.get("lng"),
                            "construction_year": investagon_data.get("object_building_year")
                        }
                        
                        # Sync or create project with property address
                        project_data = self._map_investagon_to_project(
                            project_details, 
                            db, 
                            current_user.tenant_id, 
                            current_user.id, 
                            property_address=property_address
                        )
                        
                        # Check if project exists
                        existing_project = db.query(Project).filter(
                            and_(
                                Project.investagon_id == project_id,
                                Project.tenant_id == current_user.tenant_id
                            )
                        ).first()
                        
                        if existing_project:
                            # Update existing project
                            project_obj = existing_project
                            for key, value in project_data.items():
                                if key not in ["investagon_data", "created_at", "created_by"]:
                                    setattr(project_obj, key, value)
                            project_obj.updated_by = current_user.id
                            project_obj.updated_at = datetime.now(timezone.utc)
                        else:
                            # Create new project
                            project_obj = Project(
                                **project_data,
                                tenant_id=current_user.tenant_id,
                                created_by=current_user.id
                            )
                            db.add(project_obj)
                        
                        db.flush()
                        
                        # Import project images if available
                        project_photos = project_details.get('photos', [])
                        if project_photos and project_obj:
                            try:
                                await self.import_project_images(db, project_obj, project_photos, current_user)
                            except Exception as img_error:
                                logger.error(f"Failed to import project images: {str(img_error)}")
                        
                        break
                
                if project_obj:
                    break
            
            if not project_obj:
                raise AppException(
                    status_code=500,
                    detail="Could not find or create project for this property"
                )
            
            # Check if property already exists using the actual investagon_id
            existing_property = db.query(Property).filter(
                and_(
                    Property.investagon_id == actual_investagon_id,
                    Property.tenant_id == current_user.tenant_id
                )
            ).first()
            
            # Map data with project reference
            property_data = self._map_investagon_to_property(
                investagon_data, 
                db, 
                current_user.tenant_id, 
                current_user.id,
                project_id=project_obj.id
            )
            
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
            
            # Import images if available
            photos = investagon_data.get('photos', [])
            if photos:
                logger.info(f"Found {len(photos)} photos to import for property {property_obj.id}")
                imported_images = await self.import_property_images(
                    db, property_obj, photos, current_user
                )
                logger.info(f"Imported {len(imported_images)} images for property {property_obj.id}")
            
            # Update project status based on properties
            from app.services.project_service import ProjectService
            ProjectService.update_project_status_from_properties(
                db=db,
                project_id=property_obj.project_id,
                tenant_id=current_user.tenant_id
            )
            
            # Update project aggregates after syncing property
            ProjectService.update_project_aggregates(
                db=db,
                project_id=property_obj.project_id,
                tenant_id=current_user.tenant_id
            )
            
            # Refresh micro location for the project
            await ProjectService.refresh_project_micro_location(
                db=db,
                project_id=property_obj.project_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id
            )
            
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
                    "unit_number": property_obj.unit_number,
                    "project_id": str(project_obj.id),
                    "images_imported": len(photos) if photos else 0
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
    
    async def sync_project_properties(
        self, 
        db: Session, 
        investagon_project_id: str, 
        local_project_id: UUID,
        current_user
    ) -> Dict[str, Any]:
        """Sync all properties for a specific project"""
        try:
            # Initialize API client if not already done
            if not self.api_client:
                self.api_client = self.get_tenant_api_client(db, current_user.tenant_id)
                if not self.api_client:
                    raise AppException(
                        status_code=503,
                        detail="Investagon API credentials not configured for this tenant"
                    )
            
            # Track sync stats
            total_synced = 0
            total_created = 0
            total_updated = 0
            errors = []
            
            # Get existing property mapping for this project
            existing_properties = {}
            properties_query = db.query(Property).filter(
                Property.tenant_id == current_user.tenant_id,
                Property.project_id == local_project_id
            )
            
            for prop in properties_query.all():
                if prop.investagon_id:
                    existing_properties[prop.investagon_id] = prop
            
            # Get project details including property list
            try:
                project_details = await self.api_client.get_project_by_id(investagon_project_id)
                property_urls = project_details.get("properties") or []
                logger.info(f"Project {investagon_project_id} has {len(property_urls)} properties to sync")
                
                # Get the first property to extract address information for the project
                property_address = None
                first_property_data = None
                if property_urls:
                    try:
                        # Extract first property ID and fetch its details
                        first_property_url = property_urls[0]
                        if not first_property_url:
                            logger.warning("First property URL is None")
                            raise ValueError("First property URL is None")
                        if "/api_properties/" in first_property_url:
                            first_property_id = first_property_url.split("/api_properties/")[-1]
                            first_property_data = await self.api_client.get_property(first_property_id)
                            # Log available fields for debugging
                            logger.debug(f"Property data fields: {list(first_property_data.keys())}")
                            property_address = {
                                "street": first_property_data.get("object_street"),
                                "house_number": first_property_data.get("object_house_number"),
                                "city": first_property_data.get("object_city"),
                                "state": first_property_data.get("province"),
                                "zip_code": first_property_data.get("object_postal_code"),
                                "latitude": first_property_data.get("latitude") or first_property_data.get("object_latitude") or first_property_data.get("lat"),
                                "longitude": first_property_data.get("longitude") or first_property_data.get("object_longitude") or first_property_data.get("lng"),
                                "construction_year": first_property_data.get("object_building_year")
                            }
                            logger.info(f"Extracted address from first property: {property_address}")
                    except Exception as e:
                        logger.warning(f"Failed to extract address from first property: {str(e)}")
                
                # Update the local project with better address information if available
                if property_address:
                    from app.models.business import Project
                    local_project = db.query(Project).filter(Project.id == local_project_id).first()
                    if local_project:
                        # Update address fields if incomplete
                        if not local_project.street or not local_project.house_number:
                            updated_project_data = self._map_investagon_to_project(
                                project_details,
                                db,
                                current_user.tenant_id,
                                current_user.id,
                                property_address=property_address
                            )
                            # Update address fields
                            local_project.name = updated_project_data["name"]
                            local_project.street = updated_project_data["street"]
                            local_project.house_number = updated_project_data["house_number"]
                            local_project.city = updated_project_data["city"]
                            local_project.city_id = updated_project_data["city_id"]
                            local_project.state = updated_project_data["state"]
                            local_project.zip_code = updated_project_data["zip_code"]
                        
                        # Always update lat/lng if available from property (regardless of address completeness)
                        if property_address.get("latitude") is not None:
                            local_project.latitude = property_address["latitude"]
                            logger.info(f"Updating project {local_project_id} latitude to {property_address['latitude']}")
                        if property_address.get("longitude") is not None:
                            local_project.longitude = property_address["longitude"]
                            logger.info(f"Updating project {local_project_id} longitude to {property_address['longitude']}")
                        # Update construction year if available and not already set
                        if property_address.get("construction_year") and not local_project.construction_year:
                            local_project.construction_year = int(property_address["construction_year"])
                            logger.info(f"Updating project {local_project_id} construction year to {property_address['construction_year']}")
                        
                        # Update energy information from first property if available
                        if first_property_data:
                            # Energy class - update if available and not already set
                            if first_property_data.get("energy_efficiency_class") and not local_project.energy_class:
                                local_project.energy_class = first_property_data.get("energy_efficiency_class").upper()
                                logger.info(f"Updating project {local_project_id} energy class to {local_project.energy_class}")
                            
                            # Energy consumption - update if available and not already set
                            if first_property_data.get("power_consumption") and not local_project.energy_consumption:
                                try:
                                    local_project.energy_consumption = float(first_property_data.get("power_consumption"))
                                    logger.info(f"Updating project {local_project_id} energy consumption to {local_project.energy_consumption}")
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid power_consumption value: {first_property_data.get('power_consumption')}")
                            
                            # Heating type - update if available and not already set
                            if first_property_data.get("heating_type") and not local_project.heating_type:
                                local_project.heating_type = first_property_data.get("heating_type")
                                logger.info(f"Updating project {local_project_id} heating type to {local_project.heating_type}")
                        
                        # Check if any updates were made to the project
                        energy_updated = (
                            (first_property_data.get("energy_efficiency_class") and not local_project.energy_class) or
                            (first_property_data.get("power_consumption") and not local_project.energy_consumption) or
                            (first_property_data.get("heating_type") and not local_project.heating_type)
                        ) if first_property_data else False
                        
                        if (property_address.get("latitude") is not None or 
                            property_address.get("longitude") is not None or
                            property_address.get("construction_year") is not None or
                            not local_project.street or not local_project.house_number or
                            energy_updated):
                            local_project.updated_by = current_user.id
                            local_project.updated_at = datetime.now(timezone.utc)
                            db.flush()
                            logger.info(f"Updated project {local_project_id} with data from properties")
                            
                            # Try to geocode the address to get district if not already set
                            if not local_project.district and local_project.street and local_project.house_number:
                                try:
                                    google_maps_service = GoogleMapsService()
                                    address = f"{local_project.street} {local_project.house_number}, {local_project.zip_code} {local_project.city}, {local_project.state}"
                                    
                                    geocode_result = await google_maps_service.geocode_address(db, address)
                                    
                                    if geocode_result:
                                        # Update district if found
                                        if geocode_result.get("district") and not local_project.district:
                                            local_project.district = geocode_result["district"]
                                        
                                        # Update lat/lng if not already set
                                        if not local_project.latitude:
                                            local_project.latitude = geocode_result["lat"]
                                        if not local_project.longitude:
                                            local_project.longitude = geocode_result["lng"]
                                        
                                        db.flush()
                                        logger.info(f"Updated project {local_project_id} with geocoded data - District: {local_project.district}, Coords: {local_project.latitude}, {local_project.longitude}")
                                except Exception as e:
                                    logger.error(f"Error geocoding project {local_project_id}: {str(e)}")
                
                # Import project images - fetch from /projects endpoint which includes photos
                project_photos = []
                try:
                    logger.info(f"Fetching project photos from /projects endpoint for {investagon_project_id}")
                    project_with_photos = await self.api_client.get_project_with_photos(investagon_project_id)
                    project_photos = project_with_photos.get('photos', [])
                except Exception as e:
                    logger.warning(f"Failed to fetch project photos: {str(e)}")
                
                if project_photos:
                    logger.info(f"Found {len(project_photos)} project photos to import")
                    # Get the local project
                    from app.models.business import Project
                    local_project = db.query(Project).filter(Project.id == local_project_id).first()
                    if local_project:
                        try:
                            imported_images = await self.import_project_images(
                                db, local_project, project_photos, current_user
                            )
                            logger.info(f"Imported {len(imported_images)} project images")
                        except Exception as img_error:
                            logger.error(f"Failed to import project images: {str(img_error)}")
                            errors.append(f"Failed to import project images: {str(img_error)}")
                
                # Process each property URL
                for property_url in property_urls:
                    try:
                        # Extract property ID from URL
                        if not property_url:
                            logger.warning("Received None property URL")
                            continue
                        if "/api_properties/" in property_url:
                            property_id = property_url.split("/api_properties/")[-1]
                        else:
                            logger.warning(f"Unexpected property URL format: {property_url}")
                            continue
                        
                        # Get property details
                        investagon_data = await self.api_client.get_property(property_id)
                        
                        # Map property data with project reference
                        property_data = self._map_investagon_to_property(
                            investagon_data, 
                            db, 
                            current_user.tenant_id, 
                            current_user.id,
                            project_id=local_project_id
                        )
                        
                        # Use the investagon_id from the API response
                        investagon_id = str(investagon_data.get("id", ""))
                        
                        if investagon_id in existing_properties:
                            # Update existing
                            prop = existing_properties[investagon_id]
                            for key, value in property_data.items():
                                if key != "investagon_data":
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
                        
                        # Store full API response
                        prop.investagon_data = investagon_data
                        db.flush()
                        
                        # Import property images
                        property_photos = investagon_data.get('photos', [])
                        if property_photos:
                            try:
                                imported_images = await self.import_property_images(
                                    db, prop, property_photos, current_user
                                )
                                logger.info(f"Imported {len(imported_images)} images for property {prop.id}")
                            except Exception as img_error:
                                logger.error(f"Failed to import images for property {prop.id}: {str(img_error)}")
                        
                        total_synced += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to sync property {property_url}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                logger.info(f"Project sync completed: {total_synced} synced, {total_created} created, {total_updated} updated")
                
            except Exception as e:
                error_msg = f"Failed to get project details: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                raise AppException(
                    status_code=503,
                    detail=f"Failed to fetch project from Investagon: {str(e)}"
                )
            
            # Update project status based on its properties
            from app.services.project_service import ProjectService
            try:
                ProjectService.update_project_status_from_properties(
                    db=db,
                    project_id=local_project_id,
                    tenant_id=current_user.tenant_id
                )
                logger.info(f"Updated project status for project {local_project_id}")
            except Exception as e:
                logger.warning(f"Failed to update project status for {local_project_id}: {str(e)}")
            
            # Refresh micro location for the project (only if not already exists)
            try:
                refreshed = await ProjectService.refresh_project_micro_location(
                    db=db,
                    project_id=local_project_id,
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id
                )
                if refreshed:
                    logger.info(f"Generated micro location for project {local_project_id}")
                else:
                    logger.info(f"Project {local_project_id} already has micro location data, skipped generation")
            except Exception as e:
                logger.warning(f"Failed to refresh micro location for {local_project_id}: {str(e)}")
            
            return {
                "total_synced": total_synced,
                "created": total_created,
                "updated": total_updated,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Sync project properties failed: {str(e)}")
            raise

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
            
            # Get tenant-specific API client
            if not self.api_client:
                self.api_client = self.get_tenant_api_client(db, current_user.tenant_id)
                if not self.api_client:
                    raise AppException(
                        status_code=503,
                        detail="Investagon API credentials not configured for this tenant"
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
            projects_created = 0
            projects_updated = 0
            errors = []
            
            # Get existing project mapping
            existing_projects = {}
            projects_query = db.query(Project).filter(
                Project.tenant_id == current_user.tenant_id
            )
            for proj in projects_query.all():
                if proj.investagon_id:
                    existing_projects[proj.investagon_id] = proj
            
            # Get existing property mapping
            existing_properties = {}
            try:
                logger.info("Building query for existing properties...")
                properties_query = db.query(Property).filter(
                    Property.tenant_id == current_user.tenant_id
                )
                if modified_since:
                    properties_query = properties_query.filter(
                        Property.investagon_id.is_not(None)
                    )
                
                logger.info("Executing query for existing properties...")
                all_properties = properties_query.all()
                logger.info(f"Found {len(all_properties)} existing properties")
                
                for prop in all_properties:
                    if prop.investagon_id:
                        existing_properties[prop.investagon_id] = prop
                logger.info(f"Mapped {len(existing_properties)} properties with investagon_id")
            except Exception as e:
                logger.error(f"Error querying existing properties: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # First, get all projects
            try:
                projects = await self.api_client.get_projects()
                logger.info(f"Found {len(projects)} projects to sync")
                
                # Process each project
                for project in projects:
                    project_id = str(project.get("id", ""))
                    if not project_id:
                        continue
                    
                    try:
                        # Get project details including property list
                        project_details = await self.api_client.get_project_by_id(project_id)
                        
                        # Try to get address from first property for better project naming
                        property_address = None
                        property_urls = project_details.get("properties") or []
                        if property_urls:
                            try:
                                # Extract first property ID and fetch its details
                                first_property_url = property_urls[0]
                                if not first_property_url:
                                    logger.debug("First property URL is None")
                                    raise ValueError("First property URL is None")
                                if "/api_properties/" in first_property_url:
                                    first_property_id = first_property_url.split("/api_properties/")[-1]
                                    first_property_data = await self.api_client.get_property(first_property_id)
                                    # Log available fields for debugging
                                    logger.debug(f"Property data fields: {list(first_property_data.keys())}")
                                    property_address = {
                                        "street": first_property_data.get("object_street"),
                                        "house_number": first_property_data.get("object_house_number"),
                                        "city": first_property_data.get("object_city"),
                                        "state": first_property_data.get("province"),
                                        "zip_code": first_property_data.get("object_postal_code"),
                                        "latitude": first_property_data.get("latitude") or first_property_data.get("object_latitude") or first_property_data.get("lat"),
                                        "longitude": first_property_data.get("longitude") or first_property_data.get("object_longitude") or first_property_data.get("lng"),
                                        "construction_year": first_property_data.get("object_building_year")
                                    }
                            except Exception as e:
                                logger.debug(f"Could not extract address from first property: {str(e)}")
                        
                        # Map project data with property address if available
                        project_data = self._map_investagon_to_project(
                            project_details, 
                            db, 
                            current_user.tenant_id, 
                            current_user.id,
                            property_address=property_address
                        )
                        
                        # Check if project exists
                        project_obj = None
                        if project_id in existing_projects:
                            # Update existing project
                            project_obj = existing_projects[project_id]
                            for key, value in project_data.items():
                                if key not in ["investagon_data", "created_at", "created_by"]:
                                    setattr(project_obj, key, value)
                            # Also update lat/lng if available from property
                            if property_address and property_address.get("latitude") is not None:
                                project_obj.latitude = property_address["latitude"]
                            if property_address and property_address.get("longitude") is not None:
                                project_obj.longitude = property_address["longitude"]
                            # Update construction year if available and not already set
                            if property_address and property_address.get("construction_year") and not project_obj.construction_year:
                                project_obj.construction_year = int(property_address["construction_year"])
                            project_obj.updated_by = current_user.id
                            project_obj.updated_at = datetime.now(timezone.utc)
                            projects_updated += 1
                        else:
                            # Create new project
                            project_obj = Project(
                                **project_data,
                                tenant_id=current_user.tenant_id,
                                created_by=current_user.id
                            )
                            db.add(project_obj)
                            projects_created += 1
                        
                        db.flush()
                        
                        # Add to existing_projects for tracking
                        if project_obj and project_id not in existing_projects:
                            existing_projects[project_id] = project_obj
                        
                        # Try to geocode the project address to get district
                        if project_obj and not project_obj.district and project_obj.street and project_obj.house_number:
                            try:
                                google_maps_service = GoogleMapsService()
                                address = f"{project_obj.street} {project_obj.house_number}, {project_obj.zip_code} {project_obj.city}, {project_obj.state}"
                                
                                geocode_result = await google_maps_service.geocode_address(db, address)
                                
                                if geocode_result:
                                    # Update district if found
                                    if geocode_result.get("district") and not project_obj.district:
                                        project_obj.district = geocode_result["district"]
                                    
                                    # Also update lat/lng if not already set
                                    if not project_obj.latitude:
                                        project_obj.latitude = geocode_result["lat"]
                                    if not project_obj.longitude:
                                        project_obj.longitude = geocode_result["lng"]
                                    
                                    db.flush()
                                    logger.info(f"Geocoded project {project_obj.id} - District: {project_obj.district}, Coords: {project_obj.latitude}, {project_obj.longitude}")
                            except Exception as e:
                                logger.error(f"Error geocoding project {project_obj.id}: {str(e)}")
                        
                        # Import project images - fetch from /projects endpoint which includes photos
                        project_photos = []
                        try:
                            logger.info(f"Fetching project photos from /projects endpoint for {project_id}")
                            project_with_photos = await self.api_client.get_project_with_photos(project_id)
                            project_photos = project_with_photos.get('photos', [])
                        except Exception as e:
                            logger.warning(f"Failed to fetch project photos: {str(e)}")
                        
                        if project_photos and project_obj:
                            try:
                                imported_images = await self.import_project_images(
                                    db, project_obj, project_photos, current_user
                                )
                                logger.info(f"Imported {len(imported_images)} images for project {project_obj.id}")
                            except Exception as img_error:
                                logger.error(f"Failed to import images for project {project_obj.id}: {str(img_error)}")
                        
                        # Refresh micro location for newly created/updated project
                        if project_obj:
                            try:
                                from app.services.project_service import ProjectService
                                await ProjectService.refresh_project_micro_location(
                                    db=db,
                                    project_id=project_obj.id,
                                    tenant_id=current_user.tenant_id,
                                    user_id=current_user.id
                                )
                                logger.info(f"Refreshed micro location for project {project_obj.id}")
                            except Exception as e:
                                logger.warning(f"Failed to refresh micro location for project {project_obj.id}: {str(e)}")
                        
                        # Now process properties for this project
                        property_urls = project_details.get("properties", [])
                        logger.info(f"Project {project_id} has {len(property_urls)} properties")
                        
                        # Process each property URL
                        for property_url in property_urls:
                            # Create a savepoint for each property to allow partial rollback
                            savepoint = db.begin_nested()
                            try:
                                # Extract property ID from URL (format: /api/api_properties/{id})
                                if not property_url:
                                    logger.warning("Received None property URL")
                                    continue
                                if "/api_properties/" in property_url:
                                    property_id = property_url.split("/api_properties/")[-1]
                                else:
                                    logger.warning(f"Unexpected property URL format: {property_url}")
                                    continue
                                
                                # Get property details
                                logger.debug(f"Fetching property details for ID: {property_id}")
                                investagon_data = await self.api_client.get_property(property_id)
                                logger.debug(f"Property data fields: {list(investagon_data.keys())}")
                                
                                # Map property data with project reference
                                logger.debug(f"Mapping property data to model...")
                                property_data = self._map_investagon_to_property(
                                    investagon_data, 
                                    db, 
                                    current_user.tenant_id, 
                                    current_user.id,
                                    project_id=project_obj.id
                                )
                                logger.debug(f"Mapped property data successfully")
                                
                                # Use the investagon_id from the API response, not the URL property_id
                                investagon_id = str(investagon_data.get("id", ""))
                                logger.debug(f"Property investagon_id: {investagon_id}")
                                
                                # Check if property already exists
                                logger.debug(f"Checking if property {investagon_id} exists in {len(existing_properties)} cached properties...")
                                if investagon_id in existing_properties:
                                    # Update existing
                                    logger.debug(f"Updating existing property {investagon_id}")
                                    prop = existing_properties[investagon_id]
                                    for key, value in property_data.items():
                                        if key != "investagon_data":  # Skip JSON field for now
                                            setattr(prop, key, value)
                                    prop.updated_by = current_user.id
                                    prop.updated_at = datetime.now(timezone.utc)
                                    total_updated += 1
                                    logger.debug(f"Property {investagon_id} updated successfully")
                                else:
                                    # Create new
                                    logger.debug(f"Creating new property {investagon_id}")
                                    logger.debug(f"Property data keys: {list(property_data.keys())}")
                                    logger.debug(f"Property data balcony: {property_data.get('balcony')}")
                                    logger.debug(f"Property data active: {property_data.get('active')}")
                                    logger.debug(f"Property data visibility: {property_data.get('visibility')}")
                                    prop = Property(
                                        **property_data,
                                        tenant_id=current_user.tenant_id,
                                        created_by=current_user.id
                                    )
                                    db.add(prop)
                                    total_created += 1
                                    logger.debug(f"Property {investagon_id} added to session")
                                
                                # Flush the property to get its ID
                                logger.debug(f"Flushing property {investagon_id} to database...")
                                db.flush()
                                logger.debug(f"Property {investagon_id} flushed successfully")
                                
                                # Import images if available and property is new or we're doing a full sync
                                photos = investagon_data.get('photos', [])
                                if photos and (investagon_id not in existing_properties or modified_since is None):
                                    try:
                                        imported_images = await self.import_property_images(
                                            db, prop, photos, current_user
                                        )
                                        logger.info(f"Imported {len(imported_images)} images for property {prop.id}")
                                    except Exception as img_error:
                                        logger.error(f"Failed to import images for property {prop.id}: {str(img_error)}")
                                
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
                        # Don't rollback here - let successfully processed properties remain
                        # Individual property errors are already handled with savepoints
                        # The final commit/rollback will be handled at the API endpoint level
                
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
                sync_record.error_details = {
                    "message": f"Synced with {total_errors} errors", 
                    "errors": errors,
                    "projects_created": projects_created,
                    "projects_updated": projects_updated
                }
            
            db.flush()
            
            # Update project statuses based on their properties
            from app.services.project_service import ProjectService
            affected_project_ids = set()
            
            # Collect all affected project IDs from existing_projects (which contains all synced projects)
            for investagon_id, project in existing_projects.items():
                affected_project_ids.add(project.id)
            
            # Update status for each affected project
            for project_id in affected_project_ids:
                try:
                    ProjectService.update_project_status_from_properties(
                        db=db,
                        project_id=project_id,
                        tenant_id=current_user.tenant_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to update project status for {project_id}: {str(e)}")
                
                # Update project aggregates
                try:
                    ProjectService.update_project_aggregates(
                        db=db,
                        project_id=project_id,
                        tenant_id=current_user.tenant_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to update project aggregates for {project_id}: {str(e)}")
                
                # Refresh micro location for the project
                try:
                    await ProjectService.refresh_project_micro_location(
                        db=db,
                        project_id=project_id,
                        tenant_id=current_user.tenant_id,
                        user_id=current_user.id
                    )
                except Exception as e:
                    logger.warning(f"Failed to refresh micro location for {project_id}: {str(e)}")
            
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
                    "errors": total_errors,
                    "projects_created": projects_created,
                    "projects_updated": projects_updated
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
            # Check if API is configured for tenant
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            if not tenant or not tenant.investagon_organization_id or not tenant.investagon_api_key:
                return {
                    "can_sync": False,
                    "reason": "Investagon API not configured for this tenant"
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
    
    async def import_property_images(
        self,
        db: Session,
        property_obj: Property,
        photos: List[Dict[str, Any]],
        current_user: User
    ) -> List[PropertyImage]:
        """Import images from Investagon URLs to S3 and create PropertyImage records"""
        imported_images = []
        s3_service = get_s3_service()
        
        if not s3_service or not s3_service.is_configured():
            logger.warning("S3 service not configured. Skipping image import.")
            return imported_images
        
        # Get existing property images to check for duplicates
        existing_images = db.query(PropertyImage).filter(
            PropertyImage.property_id == property_obj.id
        ).all()
        
        # Create a set of Investagon IDs we already have
        existing_investagon_ids = set()
        for img in existing_images:
            if img.description and "Investagon (ID:" in img.description:
                # Extract ID from description like "Imported from Investagon (ID: 12345)"
                try:
                    investagon_id = img.description.split("ID: ")[1].split(")")[0]
                    existing_investagon_ids.add(investagon_id)
                except:
                    pass
        
        logger.info(f"Property {property_obj.id} has {len(existing_images)} existing images, "
                   f"{len(existing_investagon_ids)} from Investagon")
        
        # Sort photos by position to maintain order
        sorted_photos = sorted(photos, key=lambda x: x.get('position', 0))
        skipped_count = 0
        
        for idx, photo in enumerate(sorted_photos):
            try:
                # Check if we already have this image
                photo_id = str(photo.get('id', ''))
                if photo_id and photo_id in existing_investagon_ids:
                    logger.debug(f"Skipping already imported image {photo_id}")
                    skipped_count += 1
                    continue
                
                filename = photo.get('filename', '')
                if not filename or not filename.startswith('http'):
                    logger.warning(f"Invalid photo URL: {filename}")
                    continue
                
                # Download image from Investagon
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        filename,
                        timeout=30.0,
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    image_content = response.content
                
                # Determine content type
                content_type = response.headers.get('content-type', 'image/jpeg')
                if not content_type.startswith('image/'):
                    content_type = 'image/jpeg'
                
                # Generate filename with proper extension
                file_extension = mimetypes.guess_extension(content_type) or '.jpg'
                temp_filename = f"investagon_{photo.get('id', idx)}{file_extension}"
                
                # Create a file-like object for S3 upload
                file_obj = BytesIO(image_content)
                file_obj.name = temp_filename
                
                # Determine image type based on position or default to exterior
                # First images are typically exterior shots
                image_type = 'exterior' if idx < 4 else 'interior'
                
                # Upload to S3
                upload_result = await s3_service.upload_image_from_bytes(
                    file_data=image_content,
                    filename=temp_filename,
                    content_type=content_type,
                    folder='properties',
                    tenant_id=str(property_obj.tenant_id),
                    resize_options={'width': 1920, 'quality': 85}
                )
                
                # Create PropertyImage record
                property_image = PropertyImage(
                    property_id=property_obj.id,
                    tenant_id=property_obj.tenant_id,
                    image_url=upload_result['url'],
                    image_type=image_type,
                    title=f"Property Image {idx + 1}",
                    description=f"Imported from Investagon (ID: {photo.get('id')})",
                    display_order=photo.get('position', idx),
                    file_size=upload_result.get('file_size'),
                    mime_type=upload_result.get('mime_type'),
                    width=upload_result.get('width'),
                    height=upload_result.get('height'),
                    created_by=current_user.id
                )
                
                db.add(property_image)
                imported_images.append(property_image)
                
                logger.info(f"Successfully imported image {photo.get('id')} for property {property_obj.id}")
                
            except Exception as e:
                logger.error(f"Failed to import image {photo.get('id', 'unknown')}: {str(e)}")
                continue
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} already imported images for property {property_obj.id}")
        if imported_images:
            logger.info(f"Successfully imported {len(imported_images)} new images for property {property_obj.id}")
        
        return imported_images

    async def import_project_images(
        self,
        db: Session,
        project_obj: Project,
        photos: List[Dict[str, Any]],
        current_user: User
    ) -> List[ProjectImage]:
        """Import images from Investagon URLs to S3 and create ProjectImage records"""
        imported_images = []
        s3_service = get_s3_service()
        
        if not s3_service or not s3_service.is_configured():
            logger.warning("S3 service not configured. Skipping image import.")
            return imported_images
        
        # Get existing project images to check for duplicates
        existing_images = db.query(ProjectImage).filter(
            ProjectImage.project_id == project_obj.id
        ).all()
        
        # Create a set of Investagon IDs we already have
        existing_investagon_ids = set()
        for img in existing_images:
            if img.description and "Investagon (ID:" in img.description:
                # Extract ID from description like "Imported from Investagon (ID: 12345)"
                try:
                    investagon_id = img.description.split("ID: ")[1].split(")")[0]
                    existing_investagon_ids.add(investagon_id)
                except:
                    pass
        
        logger.info(f"Project {project_obj.id} has {len(existing_images)} existing images, "
                   f"{len(existing_investagon_ids)} from Investagon")
        
        # Sort photos by position to maintain order
        sorted_photos = sorted(photos, key=lambda x: x.get('position', 0))
        skipped_count = 0
        
        for idx, photo in enumerate(sorted_photos):
            try:
                # Check if we already have this image
                photo_id = str(photo.get('id', ''))
                if photo_id and photo_id in existing_investagon_ids:
                    logger.debug(f"Skipping already imported image {photo_id}")
                    skipped_count += 1
                    continue
                
                filename = photo.get('filename', '')
                if not filename or not filename.startswith('http'):
                    logger.warning(f"Invalid photo URL: {filename}")
                    continue
                
                # Download image from Investagon
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        filename,
                        timeout=30.0,
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    image_content = response.content
                
                # Determine content type
                content_type = response.headers.get('content-type', 'image/jpeg')
                if not content_type.startswith('image/'):
                    content_type = 'image/jpeg'
                
                # Generate filename with proper extension
                file_extension = mimetypes.guess_extension(content_type) or '.jpg'
                temp_filename = f"investagon_project_{photo.get('id', idx)}{file_extension}"
                
                # Determine image type based on position
                # First images are typically exterior shots
                if idx < 2:
                    image_type = 'exterior'
                elif idx < 4:
                    image_type = 'common_area'
                else:
                    image_type = 'amenity'
                
                # Upload to S3
                upload_result = await s3_service.upload_image_from_bytes(
                    file_data=image_content,
                    filename=temp_filename,
                    content_type=content_type,
                    folder='projects',
                    tenant_id=str(project_obj.tenant_id),
                    resize_options={'width': 1920, 'quality': 85}
                )
                
                # Create ProjectImage record
                project_image = ProjectImage(
                    project_id=project_obj.id,
                    tenant_id=project_obj.tenant_id,
                    image_url=upload_result['url'],
                    image_type=image_type,
                    title=f"Project Image {idx + 1}",
                    description=f"Imported from Investagon (ID: {photo.get('id')})",
                    display_order=photo.get('position', idx),
                    file_size=upload_result.get('file_size'),
                    mime_type=upload_result.get('mime_type'),
                    width=upload_result.get('width'),
                    height=upload_result.get('height'),
                    created_by=current_user.id
                )
                
                db.add(project_image)
                imported_images.append(project_image)
                
                logger.info(f"Successfully imported image {photo.get('id')} for project {project_obj.id}")
                
            except Exception as e:
                logger.error(f"Failed to import image {photo.get('id', 'unknown')}: {str(e)}")
                continue
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} already imported images for project {project_obj.id}")
        if imported_images:
            logger.info(f"Successfully imported {len(imported_images)} new images for project {project_obj.id}")
        
        return imported_images