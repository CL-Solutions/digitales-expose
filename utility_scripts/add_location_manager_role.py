#!/usr/bin/env python3
"""
Script to add location_manager role to all existing tenants with proper role_permissions mapping
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.rbac import Role, Permission, RolePermission
from app.models.utils import create_default_permissions


def add_location_manager_role_to_tenants():
    """Add location_manager role to all existing tenants with permissions"""
    db: Session = SessionLocal()
    
    try:
        # First ensure all permissions exist
        print("Ensuring all permissions exist...")
        create_default_permissions(db)
        db.commit()
        
        # Define permissions for location_manager role
        permission_specs = [
            ("users", "read"),
            ("users", "read_team"),
            ("users", "request_create"),
            ("projects", "read"),
            ("properties", "read"),
            ("expose", "create"),
            ("expose", "read"),
            ("cities", "read"),
            ("reports", "team"),
            ("roles", "read")
        ]
        
        # Get permission IDs
        permission_ids = []
        for resource, action in permission_specs:
            perm = db.query(Permission).filter(
                Permission.resource == resource,
                Permission.action == action
            ).first()
            if perm:
                permission_ids.append(perm.id)
                print(f"Found permission: {resource}:{action} (ID: {perm.id})")
            else:
                print(f"ERROR: Permission {resource}:{action} not found!")
                # Try to create it
                new_perm = Permission(
                    resource=resource,
                    action=action,
                    description=f"{action.replace('_', ' ').title()} {resource}"
                )
                db.add(new_perm)
                db.flush()
                permission_ids.append(new_perm.id)
                print(f"Created permission: {resource}:{action} (ID: {new_perm.id})")
        
        # Get all tenants
        tenants = db.query(Tenant).all()
        print(f"\nProcessing {len(tenants)} tenants...")
        
        created_count = 0
        
        for tenant in tenants:
            # Check if location_manager role already exists for this tenant
            existing_role = db.query(Role).filter(
                Role.name == "location_manager",
                Role.tenant_id == tenant.id
            ).first()
            
            if existing_role:
                print(f"✓ Role 'location_manager' already exists for tenant '{tenant.name}'")
                # Ensure it has all permissions
                existing_perms = db.query(RolePermission.permission_id).filter(
                    RolePermission.role_id == existing_role.id
                ).all()
                existing_perm_ids = {p[0] for p in existing_perms}
                
                # Add missing permissions
                for perm_id in permission_ids:
                    if perm_id not in existing_perm_ids:
                        role_perm = RolePermission(
                            role_id=existing_role.id,
                            permission_id=perm_id
                        )
                        db.add(role_perm)
                        print(f"  Added missing permission ID {perm_id}")
                
                continue
            
            # Create location_manager role
            role = Role(
                tenant_id=tenant.id,
                name="location_manager",
                description="Sales manager with team oversight and reporting capabilities",
                is_system_role=True
            )
            db.add(role)
            db.flush()  # Get role.id
            
            # Create role_permissions entries
            for perm_id in permission_ids:
                role_perm = RolePermission(
                    role_id=role.id,
                    permission_id=perm_id
                )
                db.add(role_perm)
            
            print(f"✓ Created 'location_manager' role for tenant '{tenant.name}' with {len(permission_ids)} permissions")
            created_count += 1
        
        db.commit()
        print(f"\nSuccess! Created location_manager role for {created_count} tenants")
        
        # Show summary
        print("\nSummary:")
        print(f"- Total tenants: {len(tenants)}")
        print(f"- New roles created: {created_count}")
        print(f"- Roles already existed: {len(tenants) - created_count}")
        print(f"- Permissions per role: {len(permission_ids)}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_location_manager_role_to_tenants()