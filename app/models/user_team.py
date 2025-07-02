from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TenantMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.rbac import Role


class UserTeamAssignment(Base, TenantMixin):
    """Represents a hierarchical relationship between users (manager-member)."""
    
    __tablename__ = "user_team_assignments"
    
    # Manager who leads the team
    manager_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # Team member assigned to the manager
    member_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # Who made this assignment
    assigned_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    
    # When the assignment was made
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    manager: Mapped["User"] = relationship(
        "User", foreign_keys=[manager_id], back_populates="managed_team_members"
    )
    member: Mapped["User"] = relationship(
        "User", foreign_keys=[member_id], back_populates="team_managers"
    )
    assigned_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_by]
    )
    tenant: Mapped["Tenant"] = relationship("Tenant")
    
    __table_args__ = (
        UniqueConstraint("manager_id", "member_id", "tenant_id", name="uq_team_assignment"),
        Index("idx_team_assignments_manager", "manager_id", "tenant_id"),
        Index("idx_team_assignments_member", "member_id", "tenant_id"),
    )


class UserRequest(Base, TenantMixin):
    """Represents a request to create a new user, pending approval."""
    
    __tablename__ = "user_requests"
    
    # User details
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Requested role
    role_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("roles.id"), nullable=True
    )
    
    # Request metadata
    requested_by: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # Status: pending, approved, rejected
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending"
    )
    
    # Review details
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Additional notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    role: Mapped[Optional["Role"]] = relationship("Role")
    requested_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[requested_by], back_populates="user_requests_created"
    )
    reviewed_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )
    tenant: Mapped["Tenant"] = relationship("Tenant")
    
    __table_args__ = (
        Index("idx_user_requests_status", "status", "tenant_id"),
    )