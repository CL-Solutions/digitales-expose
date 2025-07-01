from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseResponseSchema, BaseSchema


# User Team Assignment Schemas
class UserTeamAssignmentBase(BaseSchema):
    """Base schema for user team assignments"""
    manager_id: UUID = Field(..., description="Manager user ID")
    member_id: UUID = Field(..., description="Team member user ID")


class UserTeamAssignmentCreate(UserTeamAssignmentBase):
    """Schema for creating team assignments"""
    pass


class UserTeamAssignmentUpdate(BaseSchema):
    """Schema for updating team assignments"""
    manager_id: Optional[UUID] = None


class UserTeamAssignmentResponse(UserTeamAssignmentBase, BaseResponseSchema):
    """Response schema for team assignments"""
    tenant_id: UUID
    assigned_by: Optional[UUID] = None
    assigned_at: datetime
    
    # Related user info
    manager_name: Optional[str] = None
    member_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserTeamAssignmentListResponse(BaseSchema):
    """List response for team assignments"""
    items: List[UserTeamAssignmentResponse]
    total: int
    page: int
    limit: int


# User Request Schemas
class UserRequestBase(BaseSchema):
    """Base schema for user creation requests"""
    email: EmailStr = Field(..., description="Email for the new user")
    name: str = Field(..., min_length=1, max_length=255, description="Name for the new user")
    role_id: Optional[UUID] = Field(None, description="Requested role ID")
    notes: Optional[str] = Field(None, description="Additional notes for the request")


class UserRequestCreate(UserRequestBase):
    """Schema for creating user requests"""
    pass


class UserRequestUpdate(BaseSchema):
    """Schema for updating user requests (for admins)"""
    status: Optional[str] = Field(None, description="Request status: pending, approved, rejected")
    notes: Optional[str] = None


class UserRequestResponse(UserRequestBase, BaseResponseSchema):
    """Response schema for user requests"""
    tenant_id: UUID
    requested_by: UUID
    status: str = Field(..., description="Request status: pending, approved, rejected")
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    
    # Related info
    requested_by_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    role_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserRequestListResponse(BaseSchema):
    """List response for user requests"""
    items: List[UserRequestResponse]
    total: int
    page: int
    limit: int


# Team Member Schemas
class TeamMemberResponse(BaseResponseSchema):
    """Response schema for team member info"""
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    is_active: bool
    roles: List[str] = Field(default_factory=list)
    
    # Performance metrics (to be extended)
    properties_created: int = 0
    exposes_created: int = 0
    
    class Config:
        from_attributes = True


class TeamOverviewResponse(BaseSchema):
    """Team overview for location managers"""
    manager: TeamMemberResponse
    team_members: List[TeamMemberResponse]
    pending_requests: List[UserRequestResponse]
    
    # Aggregated metrics
    total_properties: int = 0
    total_exposes: int = 0
    active_members: int = 0