# ================================
# RBAC SCHEMAS (schemas/rbac.py)
# ================================

from pydantic import Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema, TimestampMixin

class PermissionBase(BaseSchema):
    """Base Permission Schema"""
    resource: str = Field(..., min_length=1, max_length=100, description="Resource name (e.g., 'users', 'projects')")
    action: str = Field(..., min_length=1, max_length=50, description="Action name (e.g., 'create', 'read')")
    description: Optional[str] = Field(description="Permission description")

class PermissionCreate(PermissionBase):
    """Schema für Permission-Erstellung"""
    pass

class PermissionResponse(PermissionBase, TimestampMixin):
    """Schema für Permission-Responses"""
    id: UUID
    name: str = Field(..., description="Permission name as resource:action")

class RoleBase(BaseSchema):
    """Base Role Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(description="Role description")
    is_system_role: bool = Field(default=False, description="System-defined role")

class RoleCreate(RoleBase):
    """Schema für Role-Erstellung"""
    permission_ids: List[UUID] = Field(default_factory=list, description="Permission IDs to assign")

class RoleUpdate(BaseSchema):
    """Schema für Role-Updates"""
    name: Optional[str] = Field(min_length=1, max_length=100)
    description: Optional[str]
    permission_ids: Optional[List[UUID]] = None

class RoleResponse(RoleBase, TimestampMixin):
    """Schema für Role-Responses"""
    id: UUID
    tenant_id: Optional[UUID] = None
    permissions: List[PermissionResponse] = Field(default_factory=list)
    user_count: Optional[int] = Field(None, description="Number of users with this role")

class RoleDetailResponse(RoleBase, TimestampMixin):
    """Detailed Role Response with full information"""
    id: UUID
    tenant_id: Optional[UUID] = None
    permissions: List[PermissionResponse] = Field(default_factory=list, description="Permissions assigned to this role")
    user_count: int = Field(description="Number of users with this role")
    users: List[dict] = Field(default_factory=list, description="Users assigned to this role")
    
    # Additional metadata
    can_be_deleted: bool = Field(description="Whether this role can be deleted")
    permission_count: int = Field(description="Total number of permissions")
    recent_assignments: int = Field(default=0, description="Recent role assignments count")
    
    # Usage statistics
    last_assigned: Optional[datetime] = Field(None, description="When this role was last assigned")
    created_by_name: Optional[str] = Field(None, description="Name of user who created this role")

class RoleListResponse(BaseSchema):
    """Schema for Role List Response"""
    roles: List[RoleResponse]
    total: int
    page: int
    page_size: int

class BulkRoleAssignment(BaseSchema):
    """Schema for Bulk Role Assignment"""
    user_ids: List[UUID] = Field(..., min_items=1, description="User IDs to assign roles to")
    role_ids: List[UUID] = Field(..., min_items=1, description="Role IDs to assign")
    expires_at: Optional[datetime] = Field(description="Optional expiration for role assignments")

class UserRoleAssignment(BaseSchema):
    """Schema für User-Role Zuordnung"""
    user_id: UUID = Field(..., description="User ID")
    role_ids: List[UUID] = Field(..., min_items=1, description="Role IDs to assign")
    expires_at: Optional[datetime] = Field(description="Role expiration (optional)")

class UserRoleResponse(BaseSchema, TimestampMixin):
    """Schema für User-Role Response"""
    id: UUID
    user_id: UUID
    role_id: UUID
    tenant_id: UUID
    granted_by: Optional[UUID]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_expired: bool = Field(description="Whether the role assignment is expired")

# ================================
# ROLE MANAGEMENT SCHEMAS
# ================================

class RolePermissionUpdate(BaseSchema):
    """Schema für Role-Permission Updates"""
    add_permission_ids: List[UUID] = Field(default_factory=list, description="Permissions to add")
    remove_permission_ids: List[UUID] = Field(default_factory=list, description="Permissions to remove")

class RoleBulkAssignRequest(BaseSchema):
    """Schema für Bulk Role Assignment"""
    user_ids: List[UUID] = Field(..., min_items=1, max_items=100, description="User IDs")
    role_ids: List[UUID] = Field(..., min_items=1, description="Role IDs to assign")
    expires_at: Optional[datetime] = Field(description="Expiration for all assignments")

class RoleBulkAssignResponse(BaseSchema):
    """Schema für Bulk Role Assignment Response"""
    successful_assignments: int
    failed_assignments: int
    assignment_details: List[dict] = Field(description="Details of each assignment")

class RoleCloneRequest(BaseSchema):
    """Schema für Role Cloning"""
    source_role_id: UUID = Field(..., description="Role to clone from")
    new_role_name: str = Field(..., min_length=1, max_length=100, description="Name for the new role")
    new_role_description: Optional[str] = Field(description="Description for the new role")

# ================================
# PERMISSION MANAGEMENT SCHEMAS
# ================================

class PermissionGroupResponse(BaseSchema):
    """Schema für Permission Groups"""
    resource: str = Field(..., description="Resource name")
    permissions: List[PermissionResponse] = Field(description="Permissions for this resource")

class PermissionCheckRequest(BaseSchema):
    """Schema für Permission Check"""
    user_id: UUID = Field(..., description="User ID to check")
    resource: str = Field(..., description="Resource to check")
    action: str = Field(..., description="Action to check")

class PermissionCheckResponse(BaseSchema):
    """Schema für Permission Check Response"""
    has_permission: bool = Field(..., description="Whether user has the permission")
    granted_via_roles: List[str] = Field(default_factory=list, description="Roles that grant this permission")

class UserPermissionsResponse(BaseSchema):
    """Schema für User Permissions Response"""
    user_id: UUID
    tenant_id: UUID
    roles: List[RoleResponse] = Field(description="User's roles")
    permissions: List[PermissionResponse] = Field(description="All user permissions")
    permission_groups: List[PermissionGroupResponse] = Field(description="Permissions grouped by resource")

# ================================
# ADVANCED RBAC SCHEMAS
# ================================

class ConditionalPermissionRule(BaseSchema):
    """Schema für Conditional Permission Rules (Future Extension)"""
    condition_type: str = Field(..., description="Type of condition (time, location, etc.)")
    condition_value: dict = Field(..., description="Condition parameters")
    is_active: bool = Field(default=True)

class TemporaryRoleRequest(BaseSchema):
    """Schema für Temporary Role Assignment"""
    user_id: UUID = Field(..., description="User ID")
    role_id: UUID = Field(..., description="Role ID")
    duration_hours: int = Field(..., ge=1, le=168, description="Duration in hours (max 1 week)")
    reason: str = Field(..., min_length=1, description="Reason for temporary access")

class RoleHierarchy(BaseSchema):
    """Schema für Role Hierarchy (Future Extension)"""
    parent_role_id: UUID = Field(..., description="Parent role ID")
    child_role_id: UUID = Field(..., description="Child role ID")
    inheritance_type: str = Field(default="full", description="Type of inheritance")

class AccessRequest(BaseSchema):
    """Schema für Access Requests (Future Extension)"""
    requested_role_id: UUID = Field(..., description="Requested role ID")
    requested_permissions: List[UUID] = Field(default_factory=list, description="Specific permissions requested")
    justification: str = Field(..., min_length=10, description="Justification for access")
    duration_days: Optional[int] = Field(ge=1, le=90, description="Requested duration in days")

class AccessRequestResponse(BaseSchema, TimestampMixin):
    """Schema für Access Request Response"""
    id: UUID
    requester_id: UUID
    requested_role_id: UUID
    justification: str
    status: str = Field(description="pending, approved, rejected")
    reviewer_id: Optional[UUID]
    review_comment: Optional[str]
    reviewed_at: Optional[datetime]

# ================================
# RBAC FILTERING & REPORTING SCHEMAS
# ================================

class RoleFilterParams(BaseSchema):
    """Schema für Role Filtering"""
    search: Optional[str] = Field(None, description="Search in role name/description")
    is_system_role: Optional[bool] = None
    has_users: Optional[bool] = None
    permission_id: Optional[UUID] = None

class PermissionFilterParams(BaseSchema):
    """Schema für Permission Filtering"""
    search: Optional[str] = Field(None, description="Search in resource/action/description")
    resource: Optional[str] = None
    action: Optional[str] = None

class RBACStatsResponse(BaseSchema):
    """Schema für RBAC Statistics"""
    total_roles: int
    system_roles: int
    custom_roles: int
    total_permissions: int
    permissions_by_resource: dict[str, int]
    users_without_roles: int
    most_assigned_roles: List[dict]

class RoleUsageReport(BaseSchema):
    """Schema für Role Usage Report"""
    role_id: UUID
    role_name: str
    total_users: int
    active_users: int
    recent_assignments: int
    permission_count: int
    last_used: Optional[datetime]

class PermissionUsageReport(BaseSchema):
    """Schema für Permission Usage Report"""
    permission_id: UUID
    resource: str
    action: str
    total_roles_assigned: int
    total_users_with_permission: int
    usage_frequency: int

# ================================
# RBAC AUDIT SCHEMAS
# ================================

class RBACActivityResponse(BaseSchema, TimestampMixin):
    """Schema für RBAC Activity"""
    id: UUID
    activity_type: str = Field(description="role_assigned, role_removed, permission_granted, etc.")
    user_id: UUID
    target_user_id: Optional[UUID]
    role_id: Optional[UUID]
    permission_id: Optional[UUID]
    details: dict = Field(default_factory=dict)

class RBACComplianceReport(BaseSchema):
    """Schema für RBAC Compliance Report"""
    tenant_id: UUID
    total_users: int
    users_with_roles: int
    users_without_roles: int
    orphaned_permissions: int
    unused_roles: int
    compliance_score: float = Field(ge=0, le=100, description="Compliance score percentage")
    recommendations: List[str]