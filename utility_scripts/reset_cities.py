#!/usr/bin/env python3
"""
Reset Cities Script

This script deletes all cities from the database so they can be recreated
with proper state names during the next sync.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.business import City, Property, Project
from app.models.user import User

def reset_cities():
    """Delete all cities from the database"""
    db = SessionLocal()
    
    try:
        # Get all cities
        city_count = db.query(City).count()
        print(f"Found {city_count} cities in the database")
        
        if city_count == 0:
            print("No cities to delete")
            return
        
        # Auto-confirm for automation
        print(f"Proceeding to delete all {city_count} cities...")
        
        # First, set all property city_id fields to NULL
        print("Removing city references from properties...")
        properties_updated = db.query(Property).filter(
            Property.city_id.isnot(None)
        ).update({"city_id": None})
        print(f"Updated {properties_updated} properties")
        
        # Also remove city_id from projects
        print("Removing city references from projects...")
        projects_updated = db.query(Project).filter(
            Project.city_id.isnot(None)
        ).update({"city_id": None})
        print(f"Updated {projects_updated} projects")
        
        # Delete all cities
        print("Deleting all cities...")
        deleted = db.query(City).delete()
        
        # Commit the changes
        db.commit()
        print(f"Successfully deleted {deleted} cities")
        print("Cities will be recreated with proper state names during the next sync")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    exit(reset_cities())