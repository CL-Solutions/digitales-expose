"""Add document permissions

Revision ID: add_document_permissions
Revises: 2accccc44905
Create Date: 2025-01-15 22:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_document_permissions'
down_revision = '2accccc44905'
branch_labels = None
depends_on = None


def upgrade():
    # Add document permissions
    now = datetime.now()
    
    # Insert new permissions
    op.execute(f"""
        INSERT INTO permissions (id, resource, action, description, created_at, updated_at)
        VALUES 
            ('{uuid.uuid4()}', 'documents', 'upload', 'Upload documents', '{now}', '{now}'),
            ('{uuid.uuid4()}', 'documents', 'read', 'View documents', '{now}', '{now}'),
            ('{uuid.uuid4()}', 'documents', 'delete', 'Delete documents', '{now}', '{now}')
        ON CONFLICT (resource, action) DO NOTHING
    """)
    
    # Add document permissions to existing roles
    
    # Get connection to execute queries that return results
    connection = op.get_bind()
    
    # Get document permissions
    doc_permissions = connection.execute(sa.text(
        "SELECT id, action FROM permissions WHERE resource = 'documents'"
    )).fetchall()
    
    # Get roles
    roles = connection.execute(sa.text(
        "SELECT id, name FROM roles WHERE name IN ('tenant_admin', 'property_manager', 'sales_person')"
    )).fetchall()
    
    # Create role permission mappings
    for role in roles:
        role_id, role_name = role
        
        # Determine which permissions this role should have
        if role_name in ['tenant_admin', 'property_manager']:
            # These roles get all document permissions
            actions = ['upload', 'read', 'delete']
        elif role_name == 'sales_person':
            # Sales person only gets read permission
            actions = ['read']
        else:
            continue
            
        # Add permissions for this role
        for perm in doc_permissions:
            perm_id, perm_action = perm
            if perm_action in actions:
                # Check if permission already exists
                existing = connection.execute(sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ), {"role_id": role_id, "perm_id": perm_id}).fetchone()
                
                if not existing:
                    op.execute(f"""
                        INSERT INTO role_permissions (id, role_id, permission_id)
                        VALUES ('{uuid.uuid4()}', '{role_id}', '{perm_id}')
                    """)


def downgrade():
    # Remove document permissions from roles
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions 
            WHERE resource = 'documents'
        )
    """)
    
    # Remove document permissions
    op.execute("""
        DELETE FROM permissions
        WHERE resource = 'documents'
    """)