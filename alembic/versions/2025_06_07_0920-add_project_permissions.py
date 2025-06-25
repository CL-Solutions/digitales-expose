"""Add project permissions

Revision ID: add_project_permissions
Revises: c17dc69993dc
Create Date: 2025-06-07 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Text
import uuid
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision: str = "add_project_permissions"
down_revision: Union[str, None] = "c17dc69993dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project permissions and update roles"""
    
    # Create a table reference for permissions
    permissions_table = table('permissions',
        column('id', sa.UUID),
        column('resource', String),
        column('action', String),
        column('description', Text),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )
    
    # Insert project permissions
    now = datetime.now(timezone.utc)
    project_permissions = [
        {
            'id': str(uuid.uuid4()),
            'resource': 'projects',
            'action': 'create',
            'description': 'Create new projects',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'resource': 'projects',
            'action': 'read',
            'description': 'View projects',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'resource': 'projects',
            'action': 'update',
            'description': 'Update projects',
            'created_at': now,
            'updated_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'resource': 'projects',
            'action': 'delete',
            'description': 'Delete projects',
            'created_at': now,
            'updated_at': now
        }
    ]
    
    op.bulk_insert(permissions_table, project_permissions)
    
    # Update role permissions - add project permissions to existing roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('tenant_admin', 'property_manager')
        AND p.resource = 'projects'
        AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp 
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
        )
    """)
    
    # Add read-only project permissions to sales_person and viewer roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('sales_person', 'viewer')
        AND p.resource = 'projects' AND p.action = 'read'
        AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp 
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
        )
    """)
    
    # Update role descriptions
    op.execute("""
        UPDATE roles 
        SET description = 'Manage projects, properties and expose content'
        WHERE name = 'property_manager'
    """)
    
    op.execute("""
        UPDATE roles 
        SET description = 'View projects and properties, create shareable links'
        WHERE name = 'sales_person'
    """)
    
    op.execute("""
        UPDATE roles 
        SET description = 'Read-only access to projects and properties'
        WHERE name = 'viewer'
    """)


def downgrade() -> None:
    """Remove project permissions"""
    
    # Remove project permissions from role_permissions
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'projects'
        )
    """)
    
    # Delete project permissions
    op.execute("DELETE FROM permissions WHERE resource = 'projects'")
    
    # Restore original role descriptions
    op.execute("""
        UPDATE roles 
        SET description = 'Manage properties and expose content'
        WHERE name = 'property_manager'
    """)
    
    op.execute("""
        UPDATE roles 
        SET description = 'View properties and create shareable links'
        WHERE name = 'sales_person'
    """)
    
    op.execute("""
        UPDATE roles 
        SET description = 'Read-only access to properties'
        WHERE name = 'viewer'
    """)