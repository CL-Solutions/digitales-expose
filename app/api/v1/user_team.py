from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import (
    get_current_active_user,
    get_current_tenant_id,
    get_db,
    require_permission,
)
from app.models.user import User
from app.schemas.user_team import (
    TeamMemberResponse,
    TeamOverviewResponse,
    UserRequestCreate,
    UserRequestListResponse,
    UserRequestResponse,
    UserRequestUpdate,
    UserTeamAssignmentCreate,
    UserTeamAssignmentListResponse,
    UserTeamAssignmentResponse,
)
from app.services.user_team_service import UserTeamService

router = APIRouter()


# Team Assignment Endpoints
@router.post("/assignments", response_model=UserTeamAssignmentResponse)
async def create_team_assignment(
    assignment_data: UserTeamAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "update"))
):
    """Create a new team assignment (admin only)"""
    assignment = UserTeamService.create_team_assignment(
        db=db,
        assignment_data=assignment_data,
        assigned_by=current_user.id,
        tenant_id=tenant_id
    )
    
    return UserTeamAssignmentResponse(
        id=assignment.id,
        manager_id=assignment.manager_id,
        member_id=assignment.member_id,
        tenant_id=assignment.tenant_id,
        assigned_by=assignment.assigned_by,
        assigned_at=assignment.assigned_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        manager_name=assignment.manager.full_name if assignment.manager else None,
        member_name=assignment.member.full_name if assignment.member else None
    )


@router.delete("/assignments/{assignment_id}")
async def delete_team_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "update"))
):
    """Delete a team assignment (admin only)"""
    UserTeamService.delete_team_assignment(
        db=db,
        assignment_id=assignment_id,
        user_id=current_user.id,
        tenant_id=tenant_id
    )
    
    return {"detail": "Team assignment deleted successfully"}


@router.put("/assignments/member/{member_id}")
async def update_member_assignment(
    member_id: UUID,
    manager_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "update"))
):
    """Update team assignment for a member - reassign or remove from team"""
    from app.models.user_team import UserTeamAssignment
    from app.models.rbac import UserRole, Role
    
    # If manager_id provided, verify they have location_manager role
    if manager_id:
        has_manager_role = db.query(UserRole).join(Role).filter(
            UserRole.user_id == manager_id,
            UserRole.tenant_id == tenant_id,
            Role.name == "location_manager"
        ).first()
        
        if not has_manager_role:
            raise HTTPException(
                status_code=400,
                detail="Selected user does not have location_manager role"
            )
    
    # First, remove any existing assignments for this member
    existing_assignments = db.query(UserTeamAssignment).filter(
        UserTeamAssignment.member_id == member_id,
        UserTeamAssignment.tenant_id == tenant_id
    ).all()
    
    for assignment in existing_assignments:
        db.delete(assignment)
    
    # If manager_id provided, create new assignment
    if manager_id:
        assignment_data = UserTeamAssignmentCreate(
            manager_id=manager_id,
            member_id=member_id
        )
        
        new_assignment = UserTeamService.create_team_assignment(
            db=db,
            assignment_data=assignment_data,
            assigned_by=current_user.id,
            tenant_id=tenant_id
        )
        
        db.commit()
        
        return UserTeamAssignmentResponse(
            id=new_assignment.id,
            manager_id=new_assignment.manager_id,
            member_id=new_assignment.member_id,
            tenant_id=new_assignment.tenant_id,
            assigned_by=new_assignment.assigned_by,
            assigned_at=new_assignment.assigned_at,
            created_at=new_assignment.created_at,
            updated_at=new_assignment.updated_at,
            manager_name=new_assignment.manager.full_name if new_assignment.manager else None,
            member_name=new_assignment.member.full_name if new_assignment.member else None
        )
    else:
        # Just remove from team
        db.commit()
        # Return a consistent structure
        return {
            "detail": "Member removed from all teams",
            "member_id": str(member_id),
            "manager_id": None
        }


@router.get("/members", response_model=List[TeamMemberResponse])
async def get_my_team_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "read_team"))
):
    """Get team members for current user (location manager)"""
    members = UserTeamService.get_team_members(
        db=db,
        manager_id=current_user.id,
        tenant_id=tenant_id
    )
    
    response = []
    for member in members:
        response.append(TeamMemberResponse(
            id=member.id,
            email=member.email,
            first_name=member.first_name,
            last_name=member.last_name,
            full_name=member.full_name,
            is_active=member.is_active,
            roles=[role.role.name for role in member.user_roles if role.tenant_id == tenant_id],
            created_at=member.created_at,
            updated_at=member.updated_at
        ))
    
    return response


@router.get("/overview", response_model=TeamOverviewResponse)
async def get_team_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "read_team"))
):
    """Get team overview for location manager"""
    # Get team members
    members = UserTeamService.get_team_members(
        db=db,
        manager_id=current_user.id,
        tenant_id=tenant_id
    )
    
    # Get pending requests from team
    pending_requests = UserTeamService.get_team_requests(
        db=db,
        manager_id=current_user.id,
        tenant_id=tenant_id,
        status="pending"
    )
    
    # Build response
    manager_response = TeamMemberResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=[role.role.name for role in current_user.user_roles if role.tenant_id == tenant_id],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
    
    member_responses = []
    for member in members:
        member_responses.append(TeamMemberResponse(
            id=member.id,
            email=member.email,
            first_name=member.first_name,
            last_name=member.last_name,
            full_name=member.full_name,
            is_active=member.is_active,
            roles=[role.role.name for role in member.user_roles if role.tenant_id == tenant_id],
            created_at=member.created_at,
            updated_at=member.updated_at
        ))
    
    request_responses = []
    for request in pending_requests:
        request_responses.append(UserRequestResponse(
            id=request.id,
            email=request.email,
            name=request.name,
            role_id=request.role_id,
            notes=request.notes,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            status=request.status,
            requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
            role_name=request.role.name if request.role else None,
            created_at=request.created_at,
            updated_at=request.updated_at
        ))
    
    return TeamOverviewResponse(
        manager=manager_response,
        team_members=member_responses,
        pending_requests=request_responses,
        active_members=len([m for m in members if m.is_active])
    )


# User Request Endpoints
@router.post("/requests", response_model=UserRequestResponse)
async def create_user_request(
    request_data: UserRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "request_create"))
):
    """Create a user creation request"""
    request = UserTeamService.create_user_request(
        db=db,
        request_data=request_data,
        requested_by=current_user.id,
        tenant_id=tenant_id
    )
    
    return UserRequestResponse(
        id=request.id,
        email=request.email,
        name=request.name,
        role_id=request.role_id,
        notes=request.notes,
        tenant_id=request.tenant_id,
        requested_by=request.requested_by,
        status=request.status,
        requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
        role_name=request.role.name if request.role else None,
        created_at=request.created_at,
        updated_at=request.updated_at
    )


@router.get("/requests", response_model=UserRequestListResponse)
async def get_user_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "create"))
):
    """Get user requests (admin only)"""
    offset = (page - 1) * limit
    
    requests, total = UserTeamService.get_user_requests(
        db=db,
        tenant_id=tenant_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    items = []
    for request in requests:
        items.append(UserRequestResponse(
            id=request.id,
            email=request.email,
            name=request.name,
            role_id=request.role_id,
            notes=request.notes,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            status=request.status,
            reviewed_by=request.reviewed_by,
            reviewed_at=request.reviewed_at,
            requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
            reviewed_by_name=request.reviewed_by_user.full_name if request.reviewed_by_user else None,
            role_name=request.role.name if request.role else None,
            created_at=request.created_at,
            updated_at=request.updated_at
        ))
    
    return UserRequestListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/requests/my-team", response_model=List[UserRequestResponse])
async def get_my_team_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "read_team"))
):
    """Get user requests from my team members"""
    requests = UserTeamService.get_team_requests(
        db=db,
        manager_id=current_user.id,
        tenant_id=tenant_id,
        status=status
    )
    
    response = []
    for request in requests:
        response.append(UserRequestResponse(
            id=request.id,
            email=request.email,
            name=request.name,
            role_id=request.role_id,
            notes=request.notes,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
            status=request.status,
            requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
            role_name=request.role.name if request.role else None,
            created_at=request.created_at,
            updated_at=request.updated_at
        ))
    
    return response


@router.patch("/requests/{request_id}", response_model=UserRequestResponse)
async def update_user_request(
    request_id: UUID,
    update_data: UserRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "create"))
):
    """Update user request (approve/reject) - admin only"""
    request = await UserTeamService.update_user_request(
        db=db,
        request_id=request_id,
        update_data=update_data,
        reviewed_by=current_user.id,
        tenant_id=tenant_id
    )
    
    return UserRequestResponse(
        id=request.id,
        email=request.email,
        name=request.name,
        role_id=request.role_id,
        notes=request.notes,
        tenant_id=request.tenant_id,
        requested_by=request.requested_by,
        status=request.status,
        reviewed_by=request.reviewed_by,
        reviewed_at=request.reviewed_at,
        requested_by_name=request.requested_by_user.full_name if request.requested_by_user else None,
        reviewed_by_name=request.reviewed_by_user.full_name if request.reviewed_by_user else None,
        role_name=request.role.name if request.role else None,
        created_at=request.created_at,
        updated_at=request.updated_at
    )


@router.delete("/requests/{request_id}")
async def delete_user_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    _: bool = Depends(require_permission("users", "request_create"))
):
    """Delete a user request (only by creator)"""
    from app.models.user_team import UserRequest
    
    # Get the request first to check ownership
    request = db.query(UserRequest).filter(
        UserRequest.id == request_id,
        UserRequest.tenant_id == tenant_id
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="User request not found")
    
    # Only the creator can delete their own request
    if request.requested_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own requests")
    
    # Only allow deletion of pending requests
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be deleted")
    
    db.delete(request)
    db.commit()
    
    return {"message": "User request deleted successfully"}
