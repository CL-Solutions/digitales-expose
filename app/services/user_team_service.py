from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.audit_logger import audit_logger
from app.core.exceptions import AppException
from app.models.user import User
from app.models.user_team import UserRequest, UserTeamAssignment
from app.models.rbac import Role, UserRole
from app.schemas.user_team import (
    UserRequestCreate,
    UserRequestUpdate,
    UserTeamAssignmentCreate,
)
from app.services.auth_service import AuthService


class UserTeamService:
    """Service for managing user teams and requests"""
    
    @staticmethod
    def create_team_assignment(
        db: Session,
        assignment_data: UserTeamAssignmentCreate,
        assigned_by: UUID,
        tenant_id: UUID
    ) -> UserTeamAssignment:
        """Create a new team assignment"""
        
        # Validate users exist and belong to tenant
        manager = db.query(User).filter(
            User.id == assignment_data.manager_id,
            User.tenant_id == tenant_id
        ).first()
        if not manager:
            raise AppException(
                status_code=404,
                detail="Manager not found"
            )
            
        member = db.query(User).filter(
            User.id == assignment_data.member_id,
            User.tenant_id == tenant_id
        ).first()
        if not member:
            raise AppException(
                status_code=404,
                detail="Team member not found"
            )
            
        # Check if assignment already exists
        existing = db.query(UserTeamAssignment).filter(
            UserTeamAssignment.manager_id == assignment_data.manager_id,
            UserTeamAssignment.member_id == assignment_data.member_id,
            UserTeamAssignment.tenant_id == tenant_id
        ).first()
        
        if existing:
            raise AppException(
                status_code=400,
                detail="Team assignment already exists"
            )
            
        # Create assignment
        assignment = UserTeamAssignment(
            manager_id=assignment_data.manager_id,
            member_id=assignment_data.member_id,
            tenant_id=tenant_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow()
        )
        
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        
        audit_logger.log_business_event(
            db=db,
            action="TEAM_ASSIGNMENT_CREATED",
            user_id=assigned_by,
            tenant_id=tenant_id,
            resource_type="team_assignment",
            resource_id=assignment.id,
            new_values={
                "manager_id": str(assignment.manager_id),
                "member_id": str(assignment.member_id)
            }
        )
        
        return assignment
    
    @staticmethod
    def delete_team_assignment(
        db: Session,
        assignment_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Delete a team assignment"""
        
        assignment = db.query(UserTeamAssignment).filter(
            UserTeamAssignment.id == assignment_id,
            UserTeamAssignment.tenant_id == tenant_id
        ).first()
        
        if not assignment:
            raise AppException(
                status_code=404,
                detail="Team assignment not found"
            )
            
        db.delete(assignment)
        db.commit()
        
        audit_logger.log_business_event(
            db=db,
            action="TEAM_ASSIGNMENT_DELETED",
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type="team_assignment",
            resource_id=assignment_id
        )
    
    @staticmethod
    def get_team_members(
        db: Session,
        manager_id: UUID,
        tenant_id: UUID
    ) -> List[User]:
        """Get all team members for a manager"""
        
        assignments = db.query(UserTeamAssignment).filter(
            UserTeamAssignment.manager_id == manager_id,
            UserTeamAssignment.tenant_id == tenant_id
        ).options(
            joinedload(UserTeamAssignment.member).joinedload(User.user_roles).joinedload(UserRole.role)
        ).all()
        
        return [assignment.member for assignment in assignments]
    
    @staticmethod
    def get_user_managers(
        db: Session,
        member_id: UUID,
        tenant_id: UUID
    ) -> List[User]:
        """Get all managers for a user"""
        
        assignments = db.query(UserTeamAssignment).filter(
            UserTeamAssignment.member_id == member_id,
            UserTeamAssignment.tenant_id == tenant_id
        ).options(
            joinedload(UserTeamAssignment.manager)
        ).all()
        
        return [assignment.manager for assignment in assignments]
    
    @staticmethod
    def create_user_request(
        db: Session,
        request_data: UserRequestCreate,
        requested_by: UUID,
        tenant_id: UUID
    ) -> UserRequest:
        """Create a new user request"""
        
        # Check if user with email already exists
        existing_user = db.query(User).filter(
            User.email == request_data.email,
            User.tenant_id == tenant_id
        ).first()
        
        if existing_user:
            raise AppException(
                status_code=400,
                detail="User with this email already exists"
            )
            
        # Validate role if provided
        if request_data.role_id:
            role = db.query(Role).filter(
                Role.id == request_data.role_id,
                or_(Role.tenant_id == tenant_id, Role.tenant_id.is_(None))
            ).first()
            
            if not role:
                raise AppException(
                    status_code=404,
                    detail="Role not found"
                )
        
        # Create request
        request = UserRequest(
            email=request_data.email,
            name=request_data.name,
            role_id=request_data.role_id,
            notes=request_data.notes,
            requested_by=requested_by,
            tenant_id=tenant_id,
            status="pending"
        )
        
        db.add(request)
        db.commit()
        db.refresh(request)
        
        audit_logger.log_business_event(
            db=db,
            action="USER_REQUEST_CREATED",
            user_id=requested_by,
            tenant_id=tenant_id,
            resource_type="user_request",
            resource_id=request.id,
            new_values={
                "email": request.email,
                "name": request.name
            }
        )
        
        return request
    
    @staticmethod
    def update_user_request(
        db: Session,
        request_id: UUID,
        update_data: UserRequestUpdate,
        reviewed_by: UUID,
        tenant_id: UUID
    ) -> UserRequest:
        """Update a user request (approve/reject)"""
        
        request = db.query(UserRequest).filter(
            UserRequest.id == request_id,
            UserRequest.tenant_id == tenant_id
        ).first()
        
        if not request:
            raise AppException(
                status_code=404,
                detail="User request not found"
            )
            
        if request.status != "pending":
            raise AppException(
                status_code=400,
                detail="Request has already been processed"
            )
        
        # Update request
        if update_data.status:
            request.status = update_data.status
            request.reviewed_by = reviewed_by
            request.reviewed_at = datetime.utcnow()
            
        if update_data.notes is not None:
            request.notes = update_data.notes
            
        db.commit()
        db.refresh(request)
        
        # If approved, create the user
        if request.status == "approved":
            try:
                # Create user using AuthService
                role_ids = [request.role_id] if request.role_id else []
                
                AuthService.create_user_by_admin(
                    db=db,
                    email=request.email,
                    name=request.name,
                    tenant_id=tenant_id,
                    created_by=reviewed_by,
                    role_ids=role_ids,
                    send_invite=True
                )
                
            except Exception as e:
                # Revert status on error
                request.status = "pending"
                request.reviewed_by = None
                request.reviewed_at = None
                db.commit()
                raise AppException(
                    status_code=400,
                    detail=f"Failed to create user: {str(e)}"
                )
        
        audit_logger.log_business_event(
            db=db,
            action="USER_REQUEST_UPDATED",
            user_id=reviewed_by,
            tenant_id=tenant_id,
            resource_type="user_request",
            resource_id=request.id,
            old_values={"status": "pending"},
            new_values={"status": request.status}
        )
        
        return request
    
    @staticmethod
    def get_user_requests(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None,
        requested_by: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[UserRequest], int]:
        """Get user requests with filtering"""
        
        query = db.query(UserRequest).filter(
            UserRequest.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(UserRequest.status == status)
            
        if requested_by:
            query = query.filter(UserRequest.requested_by == requested_by)
            
        # Get total count
        total = query.count()
        
        # Get paginated results
        requests = query.options(
            joinedload(UserRequest.requested_by_user),
            joinedload(UserRequest.reviewed_by_user),
            joinedload(UserRequest.role)
        ).order_by(UserRequest.created_at.desc()).limit(limit).offset(offset).all()
        
        return requests, total
    
    @staticmethod
    def get_team_requests(
        db: Session,
        manager_id: UUID,
        tenant_id: UUID,
        status: Optional[str] = None
    ) -> List[UserRequest]:
        """Get user requests from team members"""
        
        # Get team member IDs
        team_members = UserTeamService.get_team_members(db, manager_id, tenant_id)
        member_ids = [member.id for member in team_members]
        
        if not member_ids:
            return []
            
        query = db.query(UserRequest).filter(
            UserRequest.tenant_id == tenant_id,
            UserRequest.requested_by.in_(member_ids)
        )
        
        if status:
            query = query.filter(UserRequest.status == status)
            
        return query.options(
            joinedload(UserRequest.requested_by_user),
            joinedload(UserRequest.role)
        ).order_by(UserRequest.created_at.desc()).all()