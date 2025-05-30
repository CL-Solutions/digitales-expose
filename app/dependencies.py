# ================================
# DEPENDENCIES (dependencies.py)
# ================================

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from typing import Optional, Callable
import uuid

security = HTTPBearer()

# ================================
# BASIC DEPENDENCIES
# ================================

def get_db(request: Request) -> Session:
    """Dependency für Database Session aus Middleware"""
    return request.state.db

def get_current_tenant_id(request: Request) -> Optional[uuid.UUID]:
    """Dependency für aktuelle Tenant-ID"""
    return getattr(request.state, 'tenant_id', None)

def get_request_id(request: Request) -> str:
    """Dependency für Request-ID"""
    return getattr(request.state, 'request_id', 'unknown')

# ================================
# USER AUTHENTICATION DEPENDENCIES
# ================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency für aktuellen User"""
    payload = verify_token(credentials.credentials)
    if not payload:
        raise AuthenticationError("Invalid authentication credentials")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency für aktiven User (zusätzliche Checks)"""
    if not current_user.is_active:
        raise AuthenticationError("User account is deactivated")
    
    if not current_user.is_verified:
        raise AuthenticationError("Email address not verified")
    
    # Check for account lockout
    from datetime import datetime
    if current_user.locked_until and current_user.locked_until > datetime.utcnow():
        raise AuthenticationError("Account is temporarily locked")
    
    return current_user

async def get_super_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependency für Super-Admin User"""
    if not current_user.is_super_admin:
        raise AuthorizationError("Super admin access required")
    return current_user

async def get_tenant_admin_user(
    current_user: User = Depends(get_current_active_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> User:
    """Dependency für Tenant-Admin User"""
    if current_user.is_super_admin:
        return current_user  # Super-Admins sind automatisch Tenant-Admins
    
    # Check if user is tenant admin
    is_tenant_admin = check_user_has_role(db, current_user.id, tenant_id, "tenant_admin")
    if not is_tenant_admin:
        raise AuthorizationError("Tenant admin access required")
    
    return current_user

# ================================
# PERMISSION-BASED DEPENDENCIES
# ================================

def require_permission(resource: str, action: str):
    """Factory für Permission-basierte Dependencies"""
    
    def permission_dependency(
        current_user: User = Depends(get_current_active_user),
        tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
        db: Session = Depends(get_db)
    ) -> bool:
        # Super-Admins haben alle Rechte
        if current_user.is_super_admin:
            return True
        
        # Prüfe User-Berechtigung im aktuellen Tenant
        if not tenant_id:
            raise AuthorizationError("No tenant context available")
        
        has_permission = check_user_permission(
            db, current_user.id, tenant_id, resource, action
        )
        
        if not has_permission:
            raise AuthorizationError(
                f"Permission denied: {action} on {resource}"
            )
        
        return True
    
    return permission_dependency

def require_role(role_name: str):
    """Factory für Role-basierte Dependencies"""
    
    def role_dependency(
        current_user: User = Depends(get_current_active_user),
        tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
        db: Session = Depends(get_db)
    ) -> bool:
        # Super-Admins haben alle Rollen
        if current_user.is_super_admin:
            return True
        
        if not tenant_id:
            raise AuthorizationError("No tenant context available")
        
        has_role = check_user_has_role(db, current_user.id, tenant_id, role_name)
        if not has_role:
            raise AuthorizationError(f"Role required: {role_name}")
        
        return True
    
    return role_dependency

def require_tenant_access(allow_super_admin: bool = True):
    """Dependency für Tenant-Zugriff"""
    
    def tenant_access_dependency(
        current_user: User = Depends(get_current_active_user),
        tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id)
    ) -> bool:
        # Super-Admin Check
        if allow_super_admin and current_user.is_super_admin:
            return True
        
        # User muss zum Tenant gehören
        if not tenant_id or current_user.tenant_id != tenant_id:
            raise AuthorizationError("Access denied for this tenant")
        
        return True
    
    return tenant_access_dependency

# ================================
# HELPER FUNCTIONS
# ================================

def check_user_permission(
    db: Session, 
    user_id: uuid.UUID, 
    tenant_id: uuid.UUID, 
    resource: str, 
    action: str
) -> bool:
    """Prüft ob User eine spezifische Berechtigung hat"""
    from sqlalchemy import and_
    from app.models.rbac import UserRole, RolePermission, Permission
    
    # Query: user_roles -> role_permissions -> permissions
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

def check_user_has_role(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role_name: str
) -> bool:
    """Prüft ob User eine spezifische Rolle hat"""
    from sqlalchemy import and_
    from app.models.rbac import UserRole, Role
    
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

def get_user_permissions(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> List[str]:
    """Holt alle Berechtigungen eines Users"""
    from sqlalchemy import and_
    from app.models.rbac import UserRole, RolePermission, Permission
    
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

def get_user_roles(
    db: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID
) -> List[str]:
    """Holt alle Rollen eines Users"""
    from sqlalchemy import and_
    from app.models.rbac import UserRole, Role
    
    roles = db.query(Role).join(
        UserRole, Role.id == UserRole.role_id
    ).filter(
        and_(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id
        )
    ).all()
    
    return [role.name for role in roles]

# ================================
# SPECIALIZED DEPENDENCIES
# ================================

def require_own_resource_or_permission(resource: str, action: str):
    """Dependency für Zugriff auf eigene Ressourcen oder mit Permission"""
    
    def resource_access_dependency(
        resource_id: uuid.UUID,
        current_user: User = Depends(get_current_active_user),
        tenant_id: Optional[uuid.UUID] = Depends(get_current_tenant_id),
        db: Session = Depends(get_db)
    ) -> bool:
        # Super-Admin hat immer Zugriff
        if current_user.is_super_admin:
            return True
        
        # Prüfe ob Ressource dem User gehört
        # (Diese Logik müsste je nach Ressource angepasst werden)
        from app.models.base import get_resource_owner
        
        try:
            owner_id = get_resource_owner(db, resource, resource_id)
            if owner_id == current_user.id:
                return True
        except:
            pass  # Ressource existiert nicht oder hat keinen Owner
        
        # Fallback: Prüfe Permission
        if not tenant_id:
            raise AuthorizationError("No tenant context available")
        
        has_permission = check_user_permission(
            db, current_user.id, tenant_id, resource, action
        )
        
        if not has_permission:
            raise AuthorizationError(
                f"Access denied: cannot {action} {resource}"
            )
        
        return True
    
    return resource_access_dependency

def require_same_tenant_or_super_admin():
    """Dependency für Same-Tenant Zugriff oder Super-Admin"""
    
    def same_tenant_dependency(
        target_user_id: uuid.UUID,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> bool:
        # Super-Admin hat immer Zugriff
        if current_user.is_super_admin:
            return True
        
        # Prüfe ob Target-User im gleichen Tenant ist
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if target_user.tenant_id != current_user.tenant_id:
            raise AuthorizationError("Access denied: different tenant")
        
        return True
    
    return same_tenant_dependency

# ================================
# PAGINATION DEPENDENCIES
# ================================

def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> tuple[int, int]:
    """Dependency für Pagination Parameter"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    
    return page, page_size

def get_sort_params(
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> tuple[str, str]:
    """Dependency für Sort Parameter"""
    valid_orders = ["asc", "desc"]
    if sort_order not in valid_orders:
        sort_order = "desc"
    
    return sort_by, sort_order