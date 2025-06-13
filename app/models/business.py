# ================================
# DIGITALES EXPOSE MODELS (models/business.py)
# ================================

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Numeric, and_
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TenantMixin, AuditMixin
import uuid
from datetime import datetime, timezone

class Project(Base, TenantMixin, AuditMixin):
    """Project Model for grouping related properties in the same building"""
    __tablename__ = "projects"
    
    # Basic Information
    name = Column(String(255), nullable=False)  # e.g., "Abcstreet 123"
    street = Column(String(255), nullable=False)
    house_number = Column(String(50), nullable=False)
    city = Column(String(255), nullable=False)
    city_id = Column(UUID(as_uuid=True), ForeignKey('cities.id'), nullable=True)
    state = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True, default="Deutschland")
    zip_code = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Building Details
    construction_year = Column(Integer, nullable=True)
    renovation_year = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    building_type = Column(String(100), nullable=True)  # 'apartment_building', 'mixed_use', etc.
    
    # Building Features
    has_elevator = Column(Boolean, nullable=True)
    has_parking = Column(Boolean, nullable=True)
    has_basement = Column(Boolean, nullable=True)
    has_garden = Column(Boolean, nullable=True)
    
    # Energy Data (Building Level)
    energy_certificate_type = Column(String(50), nullable=True)  # 'consumption', 'demand'
    energy_consumption = Column(Float, nullable=True)
    primary_energy_consumption = Column(Float, nullable=True)
    energy_class = Column(String(10), nullable=True)  # 'A+', 'A', 'B', etc.
    heating_type = Column(String(100), nullable=True)
    heating_building_year = Column(Integer, nullable=True)
    
    # Additional Information
    description = Column(Text, nullable=True)
    amenities = Column(JSON, nullable=True)  # List of building amenities
    micro_location = Column(JSON, nullable=True)  # Micro location data from ChatGPT
    
    # Status
    status = Column(String(50), default="available", nullable=False)  # 'available', 'reserved', 'sold'
    
    # External Reference
    investagon_id = Column(String(255), nullable=True, unique=True)  # Investagon project ID
    investagon_data = Column(JSON, nullable=True)  # Store full API response
    
    # Relationships
    tenant = relationship("Tenant")
    creator = relationship("User", foreign_keys="Project.created_by")
    updater = relationship("User", foreign_keys="Project.updated_by")
    properties = relationship("Property", back_populates="project", cascade="all, delete-orphan")
    images = relationship("ProjectImage", back_populates="project", cascade="all, delete-orphan", order_by="ProjectImage.display_order")
    city_ref = relationship("City", foreign_keys="Project.city_id")

    def __repr__(self):
        return f"<Project(name='{self.name}', city='{self.city}', status='{self.status}')>"

class ProjectImage(Base, TenantMixin, AuditMixin):
    """Project Image Model"""
    __tablename__ = "project_images"
    
    # Foreign Keys
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # Image Information
    image_url = Column(Text, nullable=False)  # S3 URL
    image_type = Column(String(50), nullable=False)  # 'exterior', 'interior', 'common_area', 'floor_plan', 'energy_certificate'
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="images")
    tenant = relationship("Tenant", foreign_keys="ProjectImage.tenant_id")
    creator = relationship("User", foreign_keys="ProjectImage.created_by")
    updater = relationship("User", foreign_keys="ProjectImage.updated_by")

    def __repr__(self):
        return f"<ProjectImage(project='{self.project_id}', type='{self.image_type}')>"

class Property(Base, TenantMixin, AuditMixin):
    """Property Model for real estate investments"""
    __tablename__ = "properties"
    
    # Foreign Keys
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    # Basic Information
    unit_number = Column(String(100), nullable=False)  # e.g., "WE1", "WE2", "WHG 103", etc.
    floor = Column(String(50), nullable=True)  # e.g., "1. OG", "2. OG Mitte", "EG"
    
    # Location references (denormalized for search/filter, but project is source of truth)
    city = Column(String(255), nullable=False)
    city_id = Column(UUID(as_uuid=True), ForeignKey('cities.id'), nullable=True)
    state = Column(String(255), nullable=False)
    zip_code = Column(String(20), nullable=False)
    property_type = Column(String(100), nullable=False)  # 'apartment', 'studio', 'penthouse', etc.
    
    # Property Details
    size_sqm = Column(Float, nullable=False)
    rooms = Column(Float, nullable=False)
    bathrooms = Column(Integer, nullable=True)
    balcony = Column(Boolean, nullable=True)  # Has balcony or not
    
    # Financial Data
    purchase_price = Column(Numeric(12, 2), nullable=False)
    purchase_price_parking = Column(Numeric(10, 2), nullable=True)
    purchase_price_furniture = Column(Numeric(10, 2), nullable=True)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    rent_parking_month = Column(Numeric(10, 2), nullable=True)
    additional_costs = Column(Numeric(10, 2), nullable=True)
    management_fee = Column(Numeric(10, 2), nullable=True)
    
    # Transaction Costs (as percentages)
    transaction_broker_rate = Column(Numeric(5, 2), nullable=True)
    transaction_tax_rate = Column(Numeric(5, 2), nullable=True)
    transaction_notary_rate = Column(Numeric(5, 2), nullable=True)
    transaction_register_rate = Column(Numeric(5, 2), nullable=True)
    
    # Operating Costs
    operation_cost_landlord = Column(Numeric(10, 2), nullable=True)
    operation_cost_tenant = Column(Numeric(10, 2), nullable=True)
    operation_cost_reserve = Column(Numeric(10, 2), nullable=True)
    
    # Additional Property Data
    object_share_owner = Column(Float, nullable=True)  # Ownership share (e.g., 0.5 for 50%)
    share_land = Column(Float, nullable=True)  # Land share in sqm
    property_usage = Column(String(100), nullable=True)  # e.g., 'WG-Wohnung', 'Single-Apartment'
    initial_maintenance_expenses = Column(Numeric(10, 2), nullable=True)  # Initial investment for maintenance
    
    # Depreciation Settings
    degressive_depreciation_building_onoff = Column(Integer, nullable=True)  # -1 (off), 0, 1 (on)
    depreciation_rate_building_manual = Column(Float, nullable=True)  # Manual depreciation rate percentage
    
    # Energy Data
    energy_certificate_type = Column(String(50), nullable=True)  # 'consumption', 'demand'
    energy_consumption = Column(Float, nullable=True)  # Endenergieverbrauch
    primary_energy_consumption = Column(Float, nullable=True)  # Primärenergieverbrauch
    energy_class = Column(String(10), nullable=True)  # 'A+', 'A', 'B', etc.
    heating_type = Column(String(100), nullable=True)
    
    # Investagon Status Flags
    active = Column(Integer, nullable=True)  # Can be more than 1
    pre_sale = Column(Integer, nullable=True)  # 0 or 1 from Investagon
    draft = Column(Integer, nullable=True)  # 0 or 1 from Investagon
    visibility = Column(Integer, nullable=True)  # Visibility value from Investagon (-1 to 1)
    
    # Investagon Integration
    investagon_id = Column(String(255), nullable=True, unique=True)
    investagon_data = Column(JSON, nullable=True)  # Cache for additional API data
    last_sync = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="properties")
    tenant = relationship("Tenant")
    creator = relationship("User", foreign_keys="Property.created_by", back_populates="created_properties")
    updater = relationship("User", foreign_keys="Property.updated_by", back_populates="updated_properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.display_order")
    expose_links = relationship("ExposeLink", back_populates="property", cascade="all, delete-orphan")
    city_ref = relationship("City", foreign_keys="Property.city_id")

    @property
    def thumbnail_url(self):
        """Get the first image URL from S3 as thumbnail"""
        if self.images:
            # Sort by display_order first, then by created_at to get the primary image
            sorted_images = sorted(
                self.images, 
                key=lambda x: (x.display_order, x.created_at if x.created_at else datetime.min.replace(tzinfo=timezone.utc))
            )
            return sorted_images[0].image_url if sorted_images else None
        return None

    def __repr__(self):
        return f"<Property(unit='{self.unit_number}', project='{self.project.name if self.project else 'N/A'}')>"

class PropertyImage(Base, TenantMixin, AuditMixin):
    """Property Image Model"""
    __tablename__ = "property_images"
    
    # Foreign Keys
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    
    # Image Information
    image_url = Column(Text, nullable=False)  # S3 URL
    image_type = Column(String(50), nullable=False)  # 'exterior', 'interior', 'floor_plan', 'energy_certificate'
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Relationships
    property = relationship("Property", back_populates="images")
    tenant = relationship("Tenant", foreign_keys="PropertyImage.tenant_id")
    creator = relationship("User", foreign_keys="PropertyImage.created_by")
    updater = relationship("User", foreign_keys="PropertyImage.updated_by")

    def __repr__(self):
        return f"<PropertyImage(property='{self.property_id}', type='{self.image_type}')>"

class City(Base, TenantMixin, AuditMixin):
    """City Model for location data"""
    __tablename__ = "cities"
    
    # Basic Information
    name = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    country = Column(String(100), default="Germany", nullable=False)
    
    # Statistics
    population = Column(Integer, nullable=True)
    population_growth = Column(Float, nullable=True)  # Percentage
    unemployment_rate = Column(Float, nullable=True)  # Percentage
    average_income = Column(Integer, nullable=True)
    
    # Infrastructure
    universities = Column(JSON, nullable=True)  # List of major universities
    major_employers = Column(JSON, nullable=True)  # List of major employers
    public_transport = Column(JSON, nullable=True)  # Public transport info
    
    # Additional Data
    description = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # Key selling points
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="City.tenant_id")
    creator = relationship("User", foreign_keys="City.created_by")
    updater = relationship("User", foreign_keys="City.updated_by")
    images = relationship("CityImage", back_populates="city", cascade="all, delete-orphan", order_by="CityImage.display_order")
    # Removed properties relationship to prevent circular loading

    def __repr__(self):
        return f"<City(name='{self.name}', state='{self.state}')>"

class CityImage(Base, TenantMixin, AuditMixin):
    """City Image Model"""
    __tablename__ = "city_images"
    
    # Foreign Keys
    city_id = Column(UUID(as_uuid=True), ForeignKey('cities.id', ondelete='CASCADE'), nullable=False)
    
    # Image Information
    image_url = Column(Text, nullable=False)  # S3 URL
    image_type = Column(String(50), nullable=False)  # 'skyline', 'landmark', 'map', 'university', 'other'
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Relationships
    city = relationship("City", back_populates="images")
    tenant = relationship("Tenant", foreign_keys="CityImage.tenant_id")
    creator = relationship("User", foreign_keys="CityImage.created_by")
    updater = relationship("User", foreign_keys="CityImage.updated_by")

    def __repr__(self):
        return f"<CityImage(city='{self.city_id}', type='{self.image_type}')>"

class ExposeTemplate(Base, TenantMixin, AuditMixin):
    """Template for expose content sections"""
    __tablename__ = "expose_templates"
    
    # Template Information
    name = Column(String(255), nullable=False)
    property_type = Column(String(100), nullable=True)  # Optional: specific to property type
    
    # Content Sections (customizable text)
    investment_benefits = Column(Text, nullable=True)
    location_description = Column(Text, nullable=True)
    property_description = Column(Text, nullable=True)
    financing_info = Column(Text, nullable=True)
    tax_benefits = Column(Text, nullable=True)
    risks_disclaimer = Column(Text, nullable=True)
    company_info = Column(Text, nullable=True)
    process_steps = Column(Text, nullable=True)
    
    # Default Calculation Parameters
    default_equity_percentage = Column(Float, default=20.0)
    default_interest_rate = Column(Float, default=3.5)
    default_loan_term_years = Column(Integer, default=20)
    default_tax_rate = Column(Float, default=42.0)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="ExposeTemplate.tenant_id")
    creator = relationship("User", foreign_keys="ExposeTemplate.created_by")
    updater = relationship("User", foreign_keys="ExposeTemplate.updated_by")

    def __repr__(self):
        return f"<ExposeTemplate(name='{self.name}', is_default='{self.is_default}')>"

class ExposeLink(Base, TenantMixin, AuditMixin):
    """Shareable expose links with tracking"""
    __tablename__ = "expose_links"
    
    # Foreign Keys
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey('expose_templates.id', ondelete='SET NULL'), nullable=True)
    
    # Link Information
    link_id = Column(String(100), nullable=False, unique=True, default=lambda: str(uuid.uuid4())[:8])
    name = Column(String(255), nullable=True)  # Optional name for internal tracking
    
    # Predefined Calculation Parameters (can be overridden by viewer)
    preset_equity_percentage = Column(Float, nullable=True)  # Percentage-based equity
    preset_interest_rate = Column(Float, nullable=True)
    preset_repayment_rate = Column(Float, nullable=True)  # Repayment percentage
    preset_gross_income = Column(Numeric(10, 2), nullable=True)  # Annual gross income
    preset_is_married = Column(Boolean, nullable=True)  # Marital status for tax calculation
    preset_monthly_rent = Column(Numeric(10, 2), nullable=True)
    
    # Access Control
    expiration_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    password_protected = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=True)
    
    # Tracking
    view_count = Column(Integer, default=0, nullable=False)
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    
    # Custom Settings
    visible_sections = Column(JSON, nullable=True)  # Which sections to show/hide
    custom_message = Column(Text, nullable=True)  # Personal message from sales person
    
    # Relationships
    property = relationship("Property", back_populates="expose_links")
    template = relationship("ExposeTemplate")
    tenant = relationship("Tenant", foreign_keys="ExposeLink.tenant_id")
    creator = relationship("User", foreign_keys="ExposeLink.created_by", back_populates="created_expose_links")
    updater = relationship("User", foreign_keys="ExposeLink.updated_by")
    views = relationship("ExposeLinkView", back_populates="expose_link", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExposeLink(link_id='{self.link_id}', property='{self.property_id}')>"

class ExposeLinkView(Base, TenantMixin):
    """Track individual views of expose links"""
    __tablename__ = "expose_link_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    expose_link_id = Column(UUID(as_uuid=True), ForeignKey('expose_links.id', ondelete='CASCADE'), nullable=False)
    
    # View Information
    viewed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    
    # Relationships
    expose_link = relationship("ExposeLink", back_populates="views")
    tenant = relationship("Tenant", foreign_keys="ExposeLinkView.tenant_id")

    def __repr__(self):
        return f"<ExposeLinkView(link='{self.expose_link_id}', viewed_at='{self.viewed_at}')>"

class InvestagonSync(Base, TenantMixin, AuditMixin):
    """Track Investagon API synchronization"""
    __tablename__ = "investagon_syncs"
    
    # Sync Information
    sync_type = Column(String(50), nullable=False)  # 'full', 'incremental', 'single_property'
    status = Column(String(50), nullable=False)  # 'pending', 'in_progress', 'completed', 'failed'
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    properties_created = Column(Integer, default=0)
    properties_updated = Column(Integer, default=0)
    properties_failed = Column(Integer, default=0)
    error_details = Column(JSON, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="InvestagonSync.tenant_id")
    creator = relationship("User", foreign_keys="InvestagonSync.created_by")

    def __repr__(self):
        return f"<InvestagonSync(type='{self.sync_type}', status='{self.status}')>"