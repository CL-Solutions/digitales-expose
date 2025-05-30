# ================================
# MODEL UTILITIES (models/utils.py)
# ================================

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.rbac import UserRole, Role, Permission, RolePermission
from app.models.user import User
from app.models.business import Project, Document
from typing import List, Optional
import uuid

def get_user_permissions(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[str]:
    """Holt alle Berechtigungen eines Users in einem Tenant"""
    
    permissions = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(
        and_(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        )
    ).all()
    
    return [f"{p.resource}:{p.action}" for p in permissions]

def get_user_roles(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[str]:
    """Holt alle Rollen eines Users in einem Tenant"""
    
    roles = db.query(Role).join(
        UserRole, Role.id == UserRole.role_id
    ).filter(
        and_(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        )
    ).all()
    
    return [role.name for role in roles]

def has_permission(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID, resource: str, action: str) -> bool:
    """Prüft ob User eine spezifische Berechtigung hat"""
    
    permission_exists = db.query(Permission).join(
        RolePermission, Permission.id == RolePermission.permission_id
    ).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(
        and_(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            Permission.resource == resource,
            Permission.action == action
        )
    ).first()
    
    return permission_exists is not None

def has_role(db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID, role_name: str) -> bool:
    """Prüft ob User eine spezifische Rolle hat"""
    
    role_exists = db.query(UserRole).join(
        Role, UserRole.role_id == Role.id
    ).filter(
        and_(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            Role.name == role_name
        )
    ).first()
    
    return role_exists is not None

def get_resource_owner(db: Session, resource_type: str, resource_id: uuid.UUID) -> Optional[uuid.UUID]:
    """Ermittelt den Owner einer Ressource"""
    
    if resource_type == "project":
        project = db.query(Project).filter(Project.id == resource_id).first()
        return project.created_by if project else None
    elif resource_type == "document":
        document = db.query(Document).filter(Document.id == resource_id).first()
        return document.created_by if document else None
    
    return None

def create_default_permissions(db: Session) -> List[Permission]:
    """Erstellt Standard-Berechtigungen für das System"""
    
    default_permissions = [
        # User Management
        ("users", "create", "Create new users"),
        ("users", "read", "View user information"),
        ("users", "update", "Update user information"),
        ("users", "delete", "Delete users"),
        ("users", "invite", "Invite new users"),
        
        # Project Management
        ("projects", "create", "Create new projects"),
        ("projects", "read", "View projects"),
        ("projects", "update", "Update projects"),
        ("projects", "delete", "Delete projects"),
        
        # Document Management
        ("documents", "create", "Create/upload documents"),
        ("documents", "read", "View documents"),
        ("documents", "update", "Update documents"),
        ("documents", "delete", "Delete documents"),
        ("documents", "download", "Download documents"),
        
        # Tenant Administration
        ("tenant", "manage", "Manage tenant settings"),
        ("tenant", "billing", "Access billing information"),
        
        # Role Management
        ("roles", "create", "Create custom roles"),
        ("roles", "read", "View roles"),
        ("roles", "update", "Update roles"),
        ("roles", "delete", "Delete roles"),
        ("roles", "assign", "Assign roles to users"),
    ]
    
    permissions = []
    for resource, action, description in default_permissions:
        # Check if permission already exists
        existing = db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action
        ).first()
        
        if not existing:
            permission = Permission(
                resource=resource,
                action=action,
                description=description
            )
            db.add(permission)
            permissions.append(permission)
    
    db.flush()  # Get IDs without committing
    return permissions

def create_default_roles_for_tenant(db: Session, tenant_id: uuid.UUID) -> List[Role]:
    """Erstellt Standard-Rollen für einen neuen Tenant"""
    
    # Get all permissions
    all_permissions = db.query(Permission).all()
    permission_map = {f"{p.resource}:{p.action}": p for p in all_permissions}
    
    # Define default roles with their permissions
    default_roles = {
        "tenant_admin": {
            "description": "Full access to tenant administration",
            "permissions": [
                "users:create", "users:read", "users:update", "users:delete", "users:invite",
                "projects:create", "projects:read", "projects:update", "projects:delete",
                "documents:create", "documents:read", "documents:update", "documents:delete", "documents:download",
                "tenant:manage", "tenant:billing",
                "roles:create", "roles:read", "roles:update", "roles:delete", "roles:assign"
            ]
        },
        "project_manager": {
            "description": "Manage projects and documents",
            "permissions": [
                "users:read",
                "projects:create", "projects:read", "projects:update", "projects:delete",
                "documents:create", "documents:read", "documents:update", "documents:delete", "documents:download",
                "roles:read"
            ]
        },
        "user": {
            "description": "Basic user permissions",
            "permissions": [
                "users:read",
                "projects:read",
                "documents:create", "documents:read", "documents:update", "documents:download"
            ]
        },
        "viewer": {
            "description": "Read-only access",
            "permissions": [
                "users:read",
                "projects:read",
                "documents:read", "documents:download"
            ]
        }
    }
    
    created_roles = []
    
    for role_name, role_config in default_roles.items():
        # Create role
        role = Role(
            tenant_id=tenant_id,
            name=role_name,
            description=role_config["description"],
            is_system_role=True
        )
        db.add(role)
        db.flush()  # Get role.id
        
        # Assign permissions to role
        for perm_name in role_config["permissions"]:
            if perm_name in permission_map:
                role_permission = RolePermission(
                    role_id=role.id,
                    permission_id=permission_map[perm_name].id
                )
                db.add(role_permission)
        
        created_roles.append(role)
    
    return created_roles

def assign_user_to_role(
    db: Session, 
    user_id: uuid.UUID, 
    role_name: str, 
    tenant_id: uuid.UUID,
    granted_by: Optional[uuid.UUID] = None
) -> UserRole:
    """Weist einem User eine Rolle zu"""
    
    # Find role
    role = db.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.name == role_name
    ).first()
    
    if not role:
        raise ValueError(f"Role '{role_name}' not found in tenant")
    
    # Check if assignment already exists
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
        UserRole.tenant_id == tenant_id
    ).first()
    
    if existing:
        return existing
    
    # Create new assignment
    user_role = UserRole(
        user_id=user_id,
        role_id=role.id,
        tenant_id=tenant_id,
        granted_by=granted_by
    )
    db.add(user_role)
    
    return user_role

def create_sample_data(db: Session):
    """Erstellt Beispieldaten für Development/Testing"""
    
    # Create permissions
    permissions = create_default_permissions(db)
    
    # Create sample tenant
    from app.models.tenant import Tenant
    sample_tenant = Tenant(
        name="Sample Company",
        slug="sample-company",
        domain="sample.com",
        settings={"theme": "default", "features": ["projects", "documents"]},
        subscription_plan="enterprise",
        max_users=100
    )
    db.add(sample_tenant)
    db.flush()
    
    # Create default roles for tenant
    roles = create_default_roles_for_tenant(db, sample_tenant.id)
    
    # Create sample admin user
    from app.core.security import get_password_hash
    admin_user = User(
        email="admin@sample.com",
        tenant_id=sample_tenant.id,
        auth_method="local",
        password_hash=get_password_hash("admin123"),
        first_name="Admin",
        last_name="User",
        is_verified=True,
        is_active=True
    )
    db.add(admin_user)
    db.flush()
    
    # Assign admin role
    assign_user_to_role(db, admin_user.id, "tenant_admin", sample_tenant.id)
    
    # Create sample regular user
    regular_user = User(
        email="user@sample.com",
        tenant_id=sample_tenant.id,
        auth_method="local",
        password_hash=get_password_hash("user123"),
        first_name="Regular",
        last_name="User",
        is_verified=True,
        is_active=True
    )
    db.add(regular_user)
    db.flush()
    
    # Assign user role
    assign_user_to_role(db, regular_user.id, "user", sample_tenant.id)
    
    # Create sample project
    sample_project = Project(
        tenant_id=sample_tenant.id,
        name="Sample Project",
        description="This is a sample project for demonstration",
        status="active",
        created_by=admin_user.id
    )
    db.add(sample_project)
    db.flush()
    
    # Create sample document
    sample_document = Document(
        tenant_id=sample_tenant.id,
        project_id=sample_project.id,
        title="Sample Document",
        content="This is a sample document content",
        created_by=admin_user.id
    )
    db.add(sample_document)
    
    # Microsoft OAuth configuration for sample tenant
    from app.models.tenant import TenantIdentityProvider
    microsoft_provider = TenantIdentityProvider(
        tenant_id=sample_tenant.id,
        provider="microsoft",
        provider_type="oauth2",
        client_id="sample-client-id",
        client_secret_hash="encrypted-secret-hash",
        azure_tenant_id="sample-azure-tenant-id",
        discovery_endpoint="https://login.microsoftonline.com/common/v2.0/.well-known/openid_configuration",
        auto_provision_users=True,
        require_verified_email=True,
        allowed_domains=["sample.com"],
        default_role_id=next((r.id for r in roles if r.name == "user"), None)
    )
    db.add(microsoft_provider)
    
    db.commit()
    print("Sample data created successfully!")

# ================================
# MODEL VALIDATION
# ================================

def validate_models():
    """Validiert alle Models auf Konsistenz"""
    
    from sqlalchemy import create_engine
    from sqlalchemy.schema import CreateTable
    from app.models.base import Base
    
    # Test engine
    engine = create_engine("sqlite:///:memory:")
    
    try:
        # Create all tables
        Base.metadata.create_all(engine)
        print("✅ All models are valid and can be created")
        
        # Print table creation SQL for verification
        for table_name, table in Base.metadata.tables.items():
            print(f"\n--- {table_name.upper()} ---")
            print(CreateTable(table).compile(engine))
            
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        raise

if __name__ == "__main__":
    validate_models()