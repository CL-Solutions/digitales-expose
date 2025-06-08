#!/usr/bin/env python3
"""
Reset Investagon sync rate limit by updating the last sync time
"""
import sys
import os
from datetime import datetime, timedelta, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.business import InvestagonSync
from app.models.tenant import Tenant

def reset_sync_rate_limit(tenant_email=None):
    """Reset the sync rate limit by updating the last sync time to more than 1 hour ago"""
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Find the tenant
        if tenant_email:
            tenant = db.query(Tenant).filter(Tenant.primary_contact_email == tenant_email).first()
            if not tenant:
                print(f"Tenant with email {tenant_email} not found")
                return
            tenant_id = tenant.id
            print(f"Resetting rate limit for tenant: {tenant.name}")
        else:
            # Find the first tenant with Investagon credentials
            tenant = db.query(Tenant).filter(
                and_(
                    Tenant.investagon_organization_id.isnot(None),
                    Tenant.investagon_api_key.isnot(None)
                )
            ).first()
            if not tenant:
                print("No tenant with Investagon credentials found")
                return
            tenant_id = tenant.id
            print(f"Resetting rate limit for tenant: {tenant.name}")
        
        # Find the last full sync
        last_sync = db.query(InvestagonSync).filter(
            and_(
                InvestagonSync.tenant_id == tenant_id,
                InvestagonSync.sync_type == "full",
                InvestagonSync.status.in_(["completed", "partial"])
            )
        ).order_by(InvestagonSync.completed_at.desc()).first()
        
        if last_sync:
            # Update the completed_at time to more than 1 hour ago
            old_time = last_sync.completed_at
            new_time = datetime.now(timezone.utc) - timedelta(hours=2)
            last_sync.completed_at = new_time
            db.commit()
            print(f"Updated last sync time from {old_time} to {new_time}")
            print("Rate limit has been reset. You can now run a new sync.")
        else:
            print("No completed full sync found. You should be able to sync without issues.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # You can pass a tenant email as argument
    tenant_email = sys.argv[1] if len(sys.argv) > 1 else None
    reset_sync_rate_limit(tenant_email)