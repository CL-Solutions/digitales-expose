#!/usr/bin/env python3
"""
Update tenant_admin role permissions to include team management permissions.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.rbac import Role, Permission, RolePermission
from sqlalchemy.orm import Session
import uuid


def update_tenant_admin_permissions():
    """Add team permissions to all tenant_admin roles"""
    
    db = SessionLocal()
    
    try:
        # Get the permissions we need to add
        team_permissions = db.query(Permission).filter(
            Permission.resource == "users",
            Permission.action.in_(["read_team", "request_create"])
        ).all()
        
        report_permission = db.query(Permission).filter(
            Permission.resource == "reports",
            Permission.action == "team"
        ).first()
        
        if not team_permissions:
            print("Team permissions not found in database!")
            return
            
        all_permissions = team_permissions
        if report_permission:
            all_permissions.append(report_permission)
        
        # Get all tenant_admin roles
        tenant_admin_roles = db.query(Role).filter(
            Role.name == "tenant_admin"
        ).all()
        
        print(f"Found {len(tenant_admin_roles)} tenant_admin roles to update")
        
        for role in tenant_admin_roles:
            print(f"\nUpdating role for tenant: {role.tenant_id}")
            
            # Check which permissions already exist
            existing_permissions = db.query(RolePermission).filter(
                RolePermission.role_id == role.id
            ).all()
            existing_permission_ids = {rp.permission_id for rp in existing_permissions}
            
            # Add missing permissions
            added_count = 0
            for permission in all_permissions:
                if permission.id not in existing_permission_ids:
                    role_permission = RolePermission(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    db.add(role_permission)
                    added_count += 1
                    print(f"  Added permission: {permission.resource}:{permission.action}")
            
            if added_count == 0:
                print("  All permissions already present")
            else:
                print(f"  Added {added_count} new permissions")
        
        db.commit()
        print("\nSuccessfully updated all tenant_admin roles!")
        
    except Exception as e:
        db.rollback()
        print(f"Error updating permissions: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_tenant_admin_permissions()