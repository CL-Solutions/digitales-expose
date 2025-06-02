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
        
    async def get_property(self, investagon_id: str) -> Dict[str, Any]:
        """Get a single property from Investagon API"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                response = await client.get(
                    f"{self.base_url}/properties/{investagon_id}.json",
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
    
    async def list_properties(
        self, 
        page: int = 1, 
        per_page: int = 100,
        modified_since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """List properties from Investagon API with pagination"""
        async with httpx.AsyncClient() as client:
            try:
                params = self._get_auth_params()
                params.update({
                    "page": page,
                    "per_page": per_page
                })
                
                if modified_since:
                    # Investagon might expect a specific date format
                    params["updated_since"] = modified_since.strftime("%Y-%m-%d %H:%M:%S")
                
                response = await client.get(
                    f"{self.base_url}/properties.json",
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parse response - Investagon might return array directly or wrapped
                data = response.json()
                if isinstance(data, list):
                    # Wrap in expected format
                    return {
                        "items": data,
                        "page": page,
                        "per_page": per_page,
                        "total": len(data),  # This might not be accurate for pagination
                        "has_more": len(data) == per_page  # Assume more if full page
                    }
                return data
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Investagon API error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 401:
                    raise AppException(
                        status_code=401,
                        detail="Invalid Investagon API credentials"
                    )
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
    def _map_investagon_to_property(investagon_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Investagon API data to our Property model fields"""
        # Based on the actual Investagon API fields from documentation
        return {
            # Basic Information
            "address": investagon_data.get("object_street", ""),
            "city": investagon_data.get("object_city", ""),
            "state": investagon_data.get("object_state", investagon_data.get("object_country", "")),
            "zip_code": investagon_data.get("object_postal_code", ""),
            "neighborhood": investagon_data.get("object_district", ""),
            "property_type": investagon_data.get("object_type", "apartment"),
            "year_built": investagon_data.get("object_year_built"),
            "size_m2": Decimal(str(investagon_data.get("object_size", 0) or 0)),
            "rooms": investagon_data.get("object_rooms"),
            "bedrooms": investagon_data.get("object_bedrooms"),
            "bathrooms": investagon_data.get("object_bathrooms"),
            "floor": investagon_data.get("object_floor"),
            "total_floors": investagon_data.get("object_total_floors"),
            "has_elevator": investagon_data.get("object_has_elevator", False),
            "has_parking": investagon_data.get("object_has_parking", False),
            "has_balcony": investagon_data.get("object_has_balcony", False),
            "has_garden": investagon_data.get("object_has_garden", False),
            "has_basement": investagon_data.get("object_has_basement", False),
            
            # Financial Data
            "purchase_price": Decimal(str(investagon_data.get("purchase_price_apartment", 0) or 0)),
            "additional_costs": Decimal(str(investagon_data.get("transaction_broker_rate", 0) or 0)),
            "renovation_costs": Decimal(str(investagon_data.get("renovation_costs", 0) or 0)),
            "monthly_rent": Decimal(str(investagon_data.get("rent_apartment_month", 0) or 0)),
            "management_fee": Decimal(str(investagon_data.get("property_management_costs", 0) or 0)),
            "maintenance_reserve": Decimal(str(investagon_data.get("maintenance_reserve", 0) or 0)),
            
            # Energy Data
            "energy_class": investagon_data.get("energy_efficiency_class"),
            "energy_consumption": Decimal(str(investagon_data.get("energy_consumption", 0) or 0)),
            "heating_type": investagon_data.get("heating_type"),
            
            # Location data
            "latitude": Decimal(str(investagon_data.get("lat", 0) or 0)) if investagon_data.get("lat") else None,
            "longitude": Decimal(str(investagon_data.get("lng", 0) or 0)) if investagon_data.get("lng") else None,
            
            # Status - map from Investagon status
            "status": "available" if investagon_data.get("status") == "available" else "sold",
            
            # Investagon Integration
            "investagon_id": str(investagon_data.get("id", "")),
            "investagon_url": investagon_data.get("public_url", ""),
            "investagon_last_sync": datetime.now(timezone.utc),
            "investagon_data": investagon_data  # Store full data for reference
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
            
            # Check if property already exists
            existing_property = db.query(Property).filter(
                and_(
                    Property.investagon_id == investagon_id,
                    Property.tenant_id == current_user.tenant_id
                )
            ).first()
            
            # Map data
            property_data = self._map_investagon_to_property(investagon_data)
            
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
                property_id=property_obj.id,
                tenant_id=current_user.tenant_id,
                sync_type="manual",
                sync_status="success",
                records_synced=1,
                records_created=1 if action == "CREATE" else 0,
                records_updated=1 if action == "UPDATE" else 0,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                initiated_by=current_user.id
            )
            db.add(sync_record)
            
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action=f"INVESTAGON_SYNC_{action}",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="property",
                resource_id=property_obj.id,
                details={
                    "investagon_id": investagon_id,
                    "address": property_obj.address
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
                sync_type="manual",
                sync_status="failed",
                error_message=str(e),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                initiated_by=current_user.id
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
                sync_status="in_progress",
                started_at=datetime.now(timezone.utc),
                initiated_by=current_user.id
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
            
            # Paginate through Investagon API
            page = 1
            has_more = True
            
            while has_more:
                try:
                    # Get page of properties
                    result = await self.api_client.list_properties(
                        page=page,
                        per_page=100,
                        modified_since=modified_since
                    )
                    
                    properties = result.get("items", [])
                    has_more = result.get("has_more", False)
                    
                    # Process each property
                    for investagon_data in properties:
                        try:
                            investagon_id = str(investagon_data.get("id", ""))
                            if not investagon_id:
                                continue
                                
                            property_data = self._map_investagon_to_property(investagon_data)
                            
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
                            
                            total_synced += 1
                            
                        except Exception as e:
                            total_errors += 1
                            errors.append({
                                "investagon_id": investagon_data.get("id"),
                                "error": str(e)
                            })
                            logger.error(f"Error syncing property {investagon_data.get('id')}: {str(e)}")
                    
                    # Move to next page
                    page += 1
                    
                    # Commit batch
                    db.flush()
                    
                except Exception as e:
                    logger.error(f"Error fetching page {page} from Investagon: {str(e)}")
                    errors.append({
                        "page": page,
                        "error": str(e)
                    })
                    break
            
            # Update sync record
            sync_record.sync_status = "success" if total_errors == 0 else "partial"
            sync_record.records_synced = total_synced
            sync_record.records_created = total_created
            sync_record.records_updated = total_updated
            sync_record.records_failed = total_errors
            sync_record.completed_at = datetime.now(timezone.utc)
            
            if errors:
                sync_record.error_message = f"Synced with {total_errors} errors"
                sync_record.sync_details = {"errors": errors}
            
            db.flush()
            
            # Log activity
            audit_logger.log_event(
                db=db,
                action="INVESTAGON_SYNC_BULK",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                resource_type="investagon_sync",
                resource_id=sync_record.id,
                details={
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
                sync_record.sync_status = "failed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_message = "Permission denied"
                db.flush()
            raise
        except Exception as e:
            logger.error(f"Failed to sync properties from Investagon: {str(e)}")
            
            if sync_record:
                sync_record.sync_status = "failed"
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_message = str(e)
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
                    InvestagonSync.sync_status == "in_progress"
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
                    InvestagonSync.sync_status.in_(["success", "partial"])
                )
            ).order_by(InvestagonSync.completed_at.desc()).first()
            
            if last_full_sync:
                time_since_last = datetime.now(timezone.utc) - last_full_sync.completed_at
                if time_since_last < timedelta(hours=1):
                    next_allowed = last_full_sync.completed_at + timedelta(hours=1)
                    return {
                        "can_sync": False,
                        "reason": "Rate limit: Full sync allowed once per hour",
                        "next_allowed_at": next_allowed.isoformat(),
                        "last_sync": last_full_sync.completed_at.isoformat()
                    }
            
            return {
                "can_sync": True,
                "last_sync": last_full_sync.completed_at.isoformat() if last_full_sync else None
            }
            
        except Exception as e:
            logger.error(f"Error checking sync status: {str(e)}")
            return {
                "can_sync": False,
                "reason": "Error checking sync status"
            }