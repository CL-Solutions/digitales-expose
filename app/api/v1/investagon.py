# ================================
# INVESTAGON API (api/v1/investagon.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging

from app.dependencies import get_db, get_current_active_user, require_permission
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
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Check if sync is allowed and get current sync status"""
    try:
        status = InvestagonSyncService.can_sync(db, current_user)
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
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Sync a single property from Investagon"""
    try:
        sync_service = InvestagonSyncService()
        property = await sync_service.sync_single_property(db, investagon_id, current_user)
        db.commit()
        
        return {
            "success": True,
            "property_id": str(property.id),
            "address": property.address,
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
    db: Session = Depends(get_db),
    _: bool = Depends(require_permission("investagon", "sync"))
):
    """Start a full or incremental sync of all properties from Investagon"""
    try:
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
                InvestagonSync.tenant_id == current_user.tenant_id,
                InvestagonSync.sync_status.in_(["success", "partial"])
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
                    sync_service = InvestagonSyncService()
                    await sync_service.sync_all_properties(bg_db, current_user, modified_since)
                    bg_db.commit()
                finally:
                    bg_db.close()
            except Exception as e:
                logger.error(f"Background sync failed: {str(e)}")
        
        # Add to background tasks
        background_tasks.add_task(run_sync)
        
        # Create initial sync record
        sync_record = InvestagonSync(
            tenant_id=current_user.tenant_id,
            sync_type="incremental" if incremental else "full",
            sync_status="queued",
            started_at=datetime.now(timezone.utc),
            initiated_by=current_user.id
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
                InvestagonSync.tenant_id == current_user.tenant_id,
                InvestagonSync.sync_status.in_(["success", "partial"])
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
        from app.services.investagon_service import InvestagonAPIClient
        
        client = InvestagonAPIClient()
        
        # Try to fetch first page with 1 item to test connection
        result = await client.list_properties(page=1, per_page=1)
        
        return {
            "connected": True,
            "message": "Successfully connected to Investagon API",
            "properties_found": len(result.get("items", []))
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