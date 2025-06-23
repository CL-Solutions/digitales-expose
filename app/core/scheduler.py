# ================================
# BACKGROUND SCHEDULER (core/scheduler.py)
# ================================

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager
import traceback

from app.core.database import SessionLocal
from app.config import settings

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Simple background task scheduler for periodic tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self._task_handles: Dict[str, asyncio.Task] = {}
    
    def add_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        initial_delay: int = 0,
        enabled: bool = True
    ):
        """Add a periodic task to the scheduler"""
        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
            "initial_delay": initial_delay,
            "enabled": enabled,
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "error_count": 0,
            "last_error": None
        }
        logger.info(f"Scheduled task '{name}' with interval {interval_seconds}s")
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info("Starting background scheduler")
        
        # Start all enabled tasks
        for task_name, task_config in self.tasks.items():
            if task_config["enabled"]:
                self._task_handles[task_name] = asyncio.create_task(
                    self._run_task_loop(task_name)
                )
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Stopping background scheduler")
        
        # Cancel all running tasks
        for task_name, task_handle in self._task_handles.items():
            task_handle.cancel()
            try:
                await task_handle
            except asyncio.CancelledError:
                pass
        
        self._task_handles.clear()
        logger.info("Background scheduler stopped")
    
    async def _run_task_loop(self, task_name: str):
        """Run a task in a loop"""
        task_config = self.tasks[task_name]
        
        # Initial delay
        if task_config["initial_delay"] > 0:
            logger.info(f"Task '{task_name}' waiting {task_config['initial_delay']}s before first run")
            await asyncio.sleep(task_config["initial_delay"])
        
        while self.running and task_config["enabled"]:
            try:
                # Update next run time
                task_config["next_run"] = datetime.now(timezone.utc) + timedelta(
                    seconds=task_config["interval"]
                )
                
                # Run the task
                logger.info(f"Running scheduled task '{task_name}'")
                start_time = datetime.now(timezone.utc)
                
                await task_config["func"]()
                
                # Update task stats
                task_config["last_run"] = start_time
                task_config["run_count"] += 1
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"Task '{task_name}' completed in {duration:.2f}s")
                
            except Exception as e:
                task_config["error_count"] += 1
                task_config["last_error"] = {
                    "time": datetime.now(timezone.utc),
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                logger.error(f"Error in scheduled task '{task_name}': {e}")
                logger.debug(traceback.format_exc())
            
            # Wait for next run
            await asyncio.sleep(task_config["interval"])
    
    def get_task_status(self, task_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of scheduled tasks"""
        if task_name:
            if task_name not in self.tasks:
                return {"error": f"Task '{task_name}' not found"}
            
            task = self.tasks[task_name]
            return {
                "name": task_name,
                "enabled": task["enabled"],
                "interval": task["interval"],
                "last_run": task["last_run"].isoformat() if task["last_run"] else None,
                "next_run": task["next_run"].isoformat() if task["next_run"] else None,
                "run_count": task["run_count"],
                "error_count": task["error_count"],
                "last_error": task["last_error"]
            }
        
        # Return all tasks
        return {
            name: self.get_task_status(name)
            for name in self.tasks
        }
    
    def enable_task(self, task_name: str):
        """Enable a task"""
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.tasks[task_name]["enabled"] = True
        logger.info(f"Enabled task '{task_name}'")
    
    def disable_task(self, task_name: str):
        """Disable a task"""
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")
        
        self.tasks[task_name]["enabled"] = False
        logger.info(f"Disabled task '{task_name}'")

# Global scheduler instance
scheduler = BackgroundScheduler()

# ================================
# SCHEDULED TASKS
# ================================

async def sync_investagon_properties():
    """Scheduled task to sync properties from Investagon"""
    # Use a new database session for the background task
    db = SessionLocal()
    try:
        from app.services.investagon_service import InvestagonSyncService
        from app.models.user import User
        from app.models.tenant import Tenant
        from app.models.business import InvestagonSync
        from types import SimpleNamespace
        
        # Get all tenants that have Investagon sync enabled
        tenants_to_sync = db.query(Tenant).filter(
            Tenant.is_active.is_(True),
            Tenant.investagon_sync_enabled.is_(True),
            Tenant.investagon_organization_id.is_not(None),
            Tenant.investagon_api_key.is_not(None)
        ).all()
        
        if not tenants_to_sync:
            logger.info("No tenants have Investagon sync enabled")
            return
        
        logger.info(f"Found {len(tenants_to_sync)} tenants with Investagon sync enabled")
        
        # Process each tenant
        for tenant in tenants_to_sync:
            try:
                # Get a user from this tenant for the sync (prefer admin)
                sync_user = db.query(User).filter(
                    User.tenant_id == tenant.id,
                    User.is_active.is_(True)
                ).first()
                
                if not sync_user:
                    logger.warning(f"No active user found for tenant {tenant.id}")
                    continue
                
                # Create a user-like object with tenant context
                effective_user = SimpleNamespace(
                    id=sync_user.id,
                    tenant_id=tenant.id,
                    is_super_admin=False,
                    is_active=True
                )
                
                # Check if we can sync (respects rate limits)
                can_sync_status = InvestagonSyncService.can_sync(db, effective_user)
                
                if not can_sync_status["can_sync"]:
                    logger.info(f"Investagon sync skipped for tenant {tenant.id}: {can_sync_status['reason']}")
                    continue
                
                # Get tenant-specific API client
                api_client = InvestagonSyncService.get_tenant_api_client(db, tenant.id)
                if not api_client:
                    logger.warning(f"Failed to create API client for tenant {tenant.id}")
                    continue
                
                # Create sync service with tenant client
                sync_service = InvestagonSyncService(api_client)
                
                # Get last successful sync to do incremental sync
                last_sync = db.query(InvestagonSync).filter(
                    InvestagonSync.tenant_id == tenant.id,
                    InvestagonSync.status.in_(["completed", "partial"]),
                    InvestagonSync.sync_type.in_(["full", "incremental"])
                ).order_by(InvestagonSync.completed_at.desc()).first()
                
                modified_since = last_sync.completed_at if last_sync else None
                
                # Perform the sync
                logger.info(f"Starting scheduled Investagon sync for tenant {tenant.name} (incremental: {modified_since is not None})")
                
                sync_record = await sync_service.sync_all_properties(
                    db, 
                    effective_user, 
                    modified_since
                )
                
                db.commit()
                
                logger.info(
                    f"Investagon sync completed for tenant {tenant.name}: "
                    f"{sync_record.properties_created} created, "
                    f"{sync_record.properties_updated} updated, "
                    f"{sync_record.properties_failed} failed"
                )
                
            except Exception as e:
                logger.error(f"Error syncing tenant {tenant.id}: {e}")
                db.rollback()
                # Continue with next tenant
        
    except Exception as e:
        logger.error(f"Error in scheduled Investagon sync: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def cleanup_expired_sessions():
    """Clean up expired sessions and tokens"""
    db = SessionLocal()
    try:
        from app.models.user import RefreshToken
        
        # Delete expired refresh tokens
        expired_tokens = db.query(RefreshToken).filter(
            RefreshToken.expires_at < datetime.now(timezone.utc)
        ).count()
        
        if expired_tokens > 0:
            db.query(RefreshToken).filter(
                RefreshToken.expires_at < datetime.now(timezone.utc)
            ).delete()
            db.commit()
            logger.info(f"Cleaned up {expired_tokens} expired refresh tokens")
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        db.rollback()
    finally:
        db.close()

async def generate_daily_reports():
    """Generate daily usage reports"""
    # This is a placeholder for future reporting functionality
    logger.info("Daily reports generation (not implemented)")

# ================================
# SCHEDULER INITIALIZATION
# ================================

def initialize_scheduler():
    """Initialize the scheduler with default tasks"""
    
    # Investagon sync - every hour
    scheduler.add_task(
        name="investagon_sync",
        func=sync_investagon_properties,
        interval_seconds=3600,  # 1 hour
        initial_delay=300,  # Wait 5 minutes after startup
        enabled=settings.ENABLE_AUTO_SYNC
    )
    
    # Session cleanup - every 6 hours
    scheduler.add_task(
        name="session_cleanup",
        func=cleanup_expired_sessions,
        interval_seconds=21600,  # 6 hours
        initial_delay=600,  # Wait 10 minutes after startup
        enabled=True
    )
    
    # Daily reports - once per day at midnight
    scheduler.add_task(
        name="daily_reports",
        func=generate_daily_reports,
        interval_seconds=86400,  # 24 hours
        initial_delay=3600,  # Wait 1 hour after startup
        enabled=False  # Disabled by default
    )
    
    logger.info("Scheduler initialized with default tasks")