# ================================
# USER PREFERENCES MODELS (models/user_preferences.py)
# ================================

from sqlalchemy import Column, String, JSON, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TenantMixin, AuditMixin


class UserFilterPreference(Base, TenantMixin, AuditMixin):
    """User-specific filter preferences for different views"""
    __tablename__ = "user_filter_preferences"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Filter Configuration
    view_name = Column(String(50), nullable=False)  # 'projects', 'properties', etc.
    filter_name = Column(String(50), nullable=False)  # 'default', 'saved_filter_1', etc.
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Filter Data (stored as JSON)
    filters = Column(JSON, nullable=False, default={})
    # Example structure:
    # {
    #   "status": "available",
    #   "city": "München",
    #   "property_type": "apartment",
    #   "price_range": [100000, 500000],
    #   "size_range": [50, 150],
    #   "construction_year_range": [2000, 2024],
    #   "visibility": {
    #     "active": true,
    #     "in_progress": true,
    #     "deactivated": false
    #   }
    # }
    
    # Display Order
    display_order = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="filter_preferences")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'view_name', 'filter_name', 'tenant_id', name='uq_user_filter_preference'),
    )