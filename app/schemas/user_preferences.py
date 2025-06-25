# ================================
# USER PREFERENCES SCHEMAS (schemas/user_preferences.py)
# ================================

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UserFilterPreferenceBase(BaseModel):
    """Base schema for user filter preferences"""
    view_name: str = Field(..., description="View name (e.g., 'projects', 'properties')")
    filter_name: str = Field(..., description="Filter name (e.g., 'default', 'my_filter_1')")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter configuration as JSON")
    is_default: bool = Field(default=False, description="Whether this is the default filter for the view")
    display_order: int = Field(default=0, description="Display order for the filter")


class UserFilterPreferenceCreate(UserFilterPreferenceBase):
    """Schema for creating a user filter preference"""
    pass


class UserFilterPreferenceUpdate(BaseModel):
    """Schema for updating a user filter preference"""
    filter_name: Optional[str]
    filters: Optional[Dict[str, Any]] = None
    is_default: Optional[bool]
    display_order: Optional[int]


class UserFilterPreferenceResponse(UserFilterPreferenceBase):
    """Schema for user filter preference response"""
    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: Optional[UUID]
    
    class Config:
        from_attributes = True