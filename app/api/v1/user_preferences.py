# ================================
# USER PREFERENCES API (api/v1/user_preferences.py)
# ================================

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_active_user, get_current_tenant_id
from app.models.user import User
from app.schemas.user_preferences import (
    UserFilterPreferenceCreate,
    UserFilterPreferenceUpdate,
    UserFilterPreferenceResponse
)
from app.services.user_preferences_service import UserPreferencesService
from app.core.exceptions import AppException

router = APIRouter(prefix="/user-preferences", tags=["user-preferences"])


@router.get("/filters", response_model=List[UserFilterPreferenceResponse])
async def get_user_filters(
    view_name: str = Query(..., description="View name (e.g., 'projects', 'properties')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Get all filter preferences for the current user and specified view"""
    try:
        filters = UserPreferencesService.get_user_filters(
            db=db,
            user_id=current_user.id,
            view_name=view_name,
            tenant_id=tenant_id
        )
        return filters
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.get("/filters/default", response_model=UserFilterPreferenceResponse)
async def get_default_filter(
    view_name: str = Query(..., description="View name (e.g., 'projects', 'properties')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Get the default filter for the current user and specified view"""
    default_filter = UserPreferencesService.get_default_filter(
        db=db,
        user_id=current_user.id,
        view_name=view_name,
        tenant_id=tenant_id
    )
    
    if not default_filter:
        raise HTTPException(status_code=404, detail="No default filter found")
    
    return default_filter


@router.post("/filters", response_model=UserFilterPreferenceResponse)
async def create_filter(
    filter_data: UserFilterPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Create a new filter preference"""
    try:
        new_filter = UserPreferencesService.create_filter(
            db=db,
            user_id=current_user.id,
            filter_data=filter_data,
            tenant_id=tenant_id
        )
        return new_filter
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.patch("/filters/{filter_id}", response_model=UserFilterPreferenceResponse)
async def update_filter(
    filter_id: UUID,
    filter_data: UserFilterPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Update an existing filter preference"""
    try:
        updated_filter = UserPreferencesService.update_filter(
            db=db,
            filter_id=filter_id,
            user_id=current_user.id,
            filter_data=filter_data,
            tenant_id=tenant_id
        )
        return updated_filter
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete("/filters/{filter_id}")
async def delete_filter(
    filter_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Delete a filter preference"""
    try:
        UserPreferencesService.delete_filter(
            db=db,
            filter_id=filter_id,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return {"message": "Filter deleted successfully"}
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/filters/{filter_id}/set-default", response_model=UserFilterPreferenceResponse)
async def set_default_filter(
    filter_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """Set a filter as the default for its view"""
    try:
        updated_filter = UserPreferencesService.set_default_filter(
            db=db,
            filter_id=filter_id,
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        return updated_filter
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)