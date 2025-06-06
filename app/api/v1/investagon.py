# ================================
# INVESTAGON API (api/v1/investagon.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from types import SimpleNamespace
import logging

from app.dependencies import get_db, get_current_active_user, require_permission, get_current_tenant_id
from app.models.user import User
from app.models.business import InvestagonSync
from app.schemas.business import InvestagonSyncSchema
from app.services.investagon_service import InvestagonSyncService
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sync/status", response_model=Dict[str, Any])
async def check_sync_status(
    current_user: User = Depends(get_current_active_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Check if sync is allowed and get current sync status"""
    try:
        # Check tenant context
        if not tenant_id:
            return {
                "can_sync": False,
                "reason": "No tenant context. Super admins must impersonate a tenant to sync properties."
            }
        
        # Create a user-like object with effective tenant ID for service
        from types import SimpleNamespace
        effective_user = SimpleNamespace(
            id=current_user.id,
            tenant_id=tenant_id if tenant_id else current_user.tenant_id,
            is_super_admin=current_user.is_super_admin,
            is_active=current_user.is_active
        )
        
        status = InvestagonSyncService.can_sync(db, effective_user)
        return status
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/history", response_model=List[InvestagonSyncSchema])
async def get_sync_history(
    limit: int = Query(default=10, ge=1, le=50, description="Number of sync records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Get sync history for the tenant"""
    try:
        # Check tenant context  
        if not current_user.tenant_id:
            return []
        
        syncs = InvestagonSyncService.get_sync_history(db, current_user, limit)
        return [InvestagonSyncSchema.model_validate(sync) for sync in syncs]
    
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/property/{investagon_id}", response_model=Dict[str, Any])
async def sync_single_property(
    investagon_id: str = Path(..., description="Investagon property ID"),
    current_user: User = Depends(get_current_active_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Sync a single property from Investagon"""
    try:
        # Check tenant context
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="No tenant context. Super admins must impersonate a tenant to sync properties."
            )
        
        # Create effective user with tenant context
        effective_user = SimpleNamespace(
            id=current_user.id,
            tenant_id=tenant_id,
            is_super_admin=current_user.is_super_admin
        )
        
        sync_service = InvestagonSyncService()
        property = await sync_service.sync_single_property(db, investagon_id, effective_user)
        db.commit()
        
        return {
            "success": True,
            "property_id": str(property.id),
            "investagon_id": property.investagon_id,
            "action": "created" if property.created_at == property.updated_at else "updated"
        }
    
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/all", response_model=InvestagonSyncSchema, status_code=status.HTTP_202_ACCEPTED)
async def sync_all_properties(
    background_tasks: BackgroundTasks,
    incremental: bool = Query(
        default=False, 
        description="If true, only sync properties modified since last sync"
    ),
    current_user: User = Depends(get_current_active_user),
    tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Start a full or incremental sync of all properties from Investagon"""
    try:
        # Check tenant context
        if not tenant_id:
            raise HTTPException(
                status_code=400,
                detail="No tenant context. Super admins must impersonate a tenant to sync properties."
            )
        
        # Create effective user with tenant context
        effective_user = SimpleNamespace(
            id=current_user.id,
            tenant_id=tenant_id,
            is_super_admin=current_user.is_super_admin
        )
        
        # Check if sync is allowed
        can_sync_status = InvestagonSyncService.can_sync(db, effective_user)
        if not can_sync_status["can_sync"]:
            raise HTTPException(
                status_code=429,
                detail=can_sync_status["reason"]
            )
        
        # Get last sync date for incremental sync
        modified_since = None
        if incremental:
            last_sync = db.query(InvestagonSync).filter(
                InvestagonSync.tenant_id == tenant_id,
                InvestagonSync.status.in_(["completed", "partial"])
            ).order_by(InvestagonSync.completed_at.desc()).first()
            
            if last_sync:
                modified_since = last_sync.completed_at
        
        # Start sync in background
        async def run_sync():
            try:
                # Create new database session for background task
                from app.core.database import SessionLocal
                bg_db = SessionLocal()
                
                try:
                    # Create effective user with tenant context for background task
                    bg_user = SimpleNamespace(
                        id=current_user.id,
                        tenant_id=tenant_id,
                        is_super_admin=current_user.is_super_admin
                    )
                    sync_service = InvestagonSyncService()
                    await sync_service.sync_all_properties(bg_db, bg_user, modified_since)
                    bg_db.commit()
                finally:
                    bg_db.close()
            except Exception as e:
                logger.error(f"Background sync failed: {str(e)}")
        
        # Add to background tasks
        background_tasks.add_task(run_sync)
        
        # Create initial sync record
        sync_record = InvestagonSync(
            tenant_id=tenant_id,
            sync_type="incremental" if incremental else "full",
            status="pending",
            started_at=datetime.now(timezone.utc),
            created_by=current_user.id
        )
        db.add(sync_record)
        db.commit()
        
        return InvestagonSyncSchema.model_validate(sync_record)
    
    except HTTPException:
        raise
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/all-sync", response_model=InvestagonSyncSchema)
async def sync_all_properties_sync(
    incremental: bool = Query(
        default=False, 
        description="If true, only sync properties modified since last sync"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Synchronously sync all properties from Investagon (blocks until complete)"""
    try:
        # Check tenant context
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=400,
                detail="No tenant context. Super admins must impersonate a tenant to sync properties."
            )
        
        # Check if sync is allowed
        can_sync_status = InvestagonSyncService.can_sync(db, current_user)
        if not can_sync_status["can_sync"]:
            raise HTTPException(
                status_code=429,
                detail=can_sync_status["reason"]
            )
        
        # Get last sync date for incremental sync
        modified_since = None
        if incremental:
            last_sync = db.query(InvestagonSync).filter(
                InvestagonSync.tenant_id == tenant_id,
                InvestagonSync.status.in_(["completed", "partial"])
            ).order_by(InvestagonSync.completed_at.desc()).first()
            
            if last_sync:
                modified_since = last_sync.completed_at
        
        # Run sync synchronously
        sync_service = InvestagonSyncService()
        sync_record = await sync_service.sync_all_properties(db, current_user, modified_since)
        db.commit()
        
        return InvestagonSyncSchema.model_validate(sync_record)
    
    except HTTPException:
        raise
    except AppException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-connection", response_model=Dict[str, Any])
async def test_investagon_connection(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Test connection to Investagon API"""
    try:
        from app.services.investagon_service import InvestagonSyncService
        
        # Get tenant-specific API client
        api_client = InvestagonSyncService.get_tenant_api_client(db, current_user.tenant_id)
        if not api_client:
            return {
                "connected": False,
                "message": "API credentials not configured for this tenant",
                "error": "Missing Investagon credentials"
            }
        
        # Try to fetch projects to test connection
        projects = await api_client.get_projects()
        
        # Count total properties across all projects
        total_properties = 0
        if projects:
            # Get details for first project to verify property fetching works
            first_project = projects[0]
            project_details = await api_client.get_project_by_id(first_project.get("id"))
            property_urls = project_details.get("properties", [])
            total_properties = len(property_urls)
        
        return {
            "connected": True,
            "message": "Successfully connected to Investagon API",
            "projects_found": len(projects),
            "properties_in_first_project": total_properties
        }
    
    except AppException as e:
        if e.status_code == 503:
            return {
                "connected": False,
                "message": "API credentials not configured",
                "error": e.detail
            }
        elif e.status_code == 401:
            return {
                "connected": False,
                "message": "Invalid API credentials",
                "error": e.detail
            }
        else:
            return {
                "connected": False,
                "message": "Connection failed",
                "error": e.detail
            }
    except Exception as e:
        return {
            "connected": False,
            "message": "Unexpected error",
            "error": str(e)
        }