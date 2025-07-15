# ================================
# DIGITALES EXPOSE MODELS (models/business.py)
# ================================

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Numeric, and_, Index
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
    district = Column(String(255), nullable=True)  # City district/neighborhood
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
    total_units = Column(Integer, nullable=True)
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
    
    # New fields from Issue #51
    backyard_development = Column(Boolean, nullable=True)  # Hinterlandsbebauung
    sev_takeover_one_year = Column(Boolean, nullable=True)  # Übernahme SEV für 1 Jahr
    
    # HOA renovations (WEG Gewerke) - JSON array of renovation objects
    # Format: [{"type": "roof", "year": 2023}, {"type": "windows", "year": 2025}, ...]
    renovations = Column(JSON, nullable=True)
    
    # Additional Information
    description = Column(Text, nullable=True)
    amenities = Column(JSON, nullable=True)  # List of building amenities
    micro_location_v2 = Column(JSON, nullable=True)  # Enhanced micro location data from Google Maps API
    
    # Status
    status = Column(String(50), default="available", nullable=False)  # 'available', 'reserved', 'sold'
    
    # Base provision percentage for this project (0.0 - 100.0)
    provision_percentage = Column(Float, default=0.0, nullable=False)
    
    # Aggregated Property Data (for efficient sorting/filtering)
    min_price = Column(Numeric(12, 2), nullable=True)  # Minimum property price in project
    max_price = Column(Numeric(12, 2), nullable=True)  # Maximum property price in project
    min_rental_yield = Column(Numeric(5, 2), nullable=True)  # Minimum rental yield in project
    max_rental_yield = Column(Numeric(5, 2), nullable=True)  # Maximum rental yield in project
    min_initial_maintenance_expenses = Column(Numeric(12, 2), nullable=True)  # Minimum initial maintenance expenses
    max_initial_maintenance_expenses = Column(Numeric(12, 2), nullable=True)  # Maximum initial maintenance expenses
    
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

    # Table indexes
    __table_args__ = (
        Index('idx_projects_city', 'city'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_min_price', 'min_price'),
        Index('idx_projects_min_rental_yield', 'min_rental_yield'),
    )

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
    balcony = Column(String(50), nullable=True)  # 'none' or orientation: 'north', 'south', 'east', 'west', etc.
    
    # Financial Data
    purchase_price = Column(Numeric(12, 2), nullable=False)
    purchase_price_parking = Column(Numeric(10, 2), nullable=True)
    purchase_price_furniture = Column(Numeric(10, 2), nullable=True)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    rent_parking_month = Column(Numeric(10, 2), nullable=True)
    additional_costs = Column(Numeric(10, 2), nullable=True)
    management_fee = Column(Numeric(10, 2), nullable=True)
    
    # Transaction Costs (as percentages)
    notary_override_percentage = Column(Numeric(5, 2), nullable=True)  # Override for new fee calculation
    
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
    
    # New fields from Issue #50
    reserves = Column(Numeric(10, 2), nullable=True)  # Rücklagen
    takeover_special_charges_years = Column(Integer, nullable=True)  # Übernahme Sonderlagen bis zu x Jahre
    takeover_special_charges_amount = Column(Numeric(10, 2), nullable=True)  # Übernahme Sonderlagen bis zu x €
    has_cellar = Column(Boolean, nullable=True)  # Keller vorhanden
    parking_type = Column(String(50), nullable=True)  # Stellplatz/Garage/Duplexgarage/Tiefgarage
    
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
    reservations = relationship("Reservation", back_populates="property", cascade="all, delete-orphan")

    # Table indexes
    __table_args__ = (
        Index('idx_properties_active', 'active'),
        Index('idx_properties_project_id', 'project_id'),
        Index('idx_properties_city', 'city'),
        Index('idx_properties_purchase_price', 'purchase_price'),
        Index('idx_properties_visibility', 'visibility'),
    )

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
    
    # Additional Data
    description = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # Key selling points
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="City.tenant_id")
    creator = relationship("User", foreign_keys="City.created_by")
    updater = relationship("User", foreign_keys="City.updated_by")
    images = relationship("CityImage", back_populates="city", cascade="all, delete-orphan")
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
    image_type = Column(String(50), nullable=False)  # 'header', 'location', 'lifestyle', 'other'
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
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
    
    # Section visibility controls
    enabled_sections = Column(JSON, nullable=False, default={})  # {section_key: boolean}
    
    # JSON fields for customizable content sections
    floor_plan_content = Column(Text, nullable=True)  # Content for Grundriss section
    modernization_items = Column(JSON, nullable=True)  # List of modernization items [{title, description?}]
    insurance_plans = Column(JSON, nullable=True)  # Insurance plan data [{name, price, period, features, recommended}]
    process_steps_list = Column(JSON, nullable=True)  # Process steps [{number, title, description, color_scheme}]
    opportunities_risks_sections = Column(JSON, nullable=True)  # List of opportunities/risks sections [{headline, content, is_expanded_by_default}]
    
    # New sections (January 2025)
    liability_disclaimer_content = Column(Text, nullable=True)  # Content for Haftungsausschluss section
    onsite_management_services = Column(JSON, nullable=True)  # On-site management services [{service, description}]
    onsite_management_package = Column(JSON, nullable=True)  # Management package details {name, price, unit}
    coliving_content = Column(Text, nullable=True)  # Co-Living description text
    special_features_items = Column(JSON, nullable=True)  # Special features [{title, description}]
    
    # Highlights configuration
    highlights = Column(JSON, nullable=True)  # List of highlight keys to display [{key: string, enabled: boolean}]
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="ExposeTemplate.tenant_id")
    creator = relationship("User", foreign_keys="ExposeTemplate.created_by")
    updater = relationship("User", foreign_keys="ExposeTemplate.updated_by")
    images = relationship("ExposeTemplateImage", back_populates="template", cascade="all, delete-orphan", order_by="ExposeTemplateImage.display_order")

    def __repr__(self):
        return f"<ExposeTemplate(tenant_id='{self.tenant_id}')>"

class ExposeTemplateImage(Base, TenantMixin, AuditMixin):
    """Expose Template Image Model"""
    __tablename__ = "expose_template_images"
    
    # Foreign Keys
    template_id = Column(UUID(as_uuid=True), ForeignKey('expose_templates.id', ondelete='CASCADE'), nullable=False)
    
    # Image Information
    image_url = Column(Text, nullable=False)  # S3 URL
    image_type = Column(String(50), nullable=False)  # 'coliving', 'special_features', 'management', 'general'
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    # Metadata
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Relationships
    template = relationship("ExposeTemplate", back_populates="images")
    tenant = relationship("Tenant", foreign_keys="ExposeTemplateImage.tenant_id")
    creator = relationship("User", foreign_keys="ExposeTemplateImage.created_by")
    updater = relationship("User", foreign_keys="ExposeTemplateImage.updated_by")

    def __repr__(self):
        return f"<ExposeTemplateImage(template='{self.template_id}', type='{self.image_type}')>"

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

    # Table indexes
    __table_args__ = (
        Index('idx_expose_links_link_id', 'link_id'),
    )

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

class Reservation(Base, TenantMixin, AuditMixin):
    """Property reservation management"""
    __tablename__ = "reservations"
    
    # Foreign Keys
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)  # Sales person who created reservation
    
    # Customer Information
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    
    # Financial Details
    equity_amount = Column(Numeric(10, 2), nullable=True)  # Eigenkapital
    equity_percentage = Column(Numeric(5, 2), nullable=True)  # Eigenkapital percentage
    is_90_10_deal = Column(Boolean, default=False, nullable=False)  # 90/10 deal flag
    adjusted_purchase_price = Column(Numeric(10, 2), nullable=True)  # Modified price for 90/10
    external_commission = Column(Numeric(10, 2), nullable=True)  # Externe Maklercortage
    internal_commission = Column(Numeric(10, 2), nullable=True)  # Interne Provision
    reservation_fee_paid = Column(Boolean, default=False, nullable=False)  # Set when moving to Reserviert
    reservation_fee_paid_date = Column(DateTime, nullable=True)  # Date when reservation fee was paid
    
    # Notary Details
    preferred_notary = Column(String(255), nullable=True)  # Notarwunsch (can be empty)
    notary_appointment_date = Column(DateTime, nullable=True)  # Date of notary appointment
    notary_appointment_time = Column(DateTime, nullable=True)  # Time of notary appointment
    notary_location = Column(String(500), nullable=True)  # Location/address of notary appointment
    
    # Status Tracking
    status = Column(Integer, nullable=False, default=5)  # Current reservation status (matches property.active values)
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this is the active reservation or on waitlist
    waitlist_position = Column(Integer, nullable=True)  # Position in waitlist (NULL if active)
    
    # Notes and Documentation
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    property = relationship("Property", back_populates="reservations")
    user = relationship("User", foreign_keys=[user_id], back_populates="created_reservations")  # Sales person
    tenant = relationship("Tenant", foreign_keys="Reservation.tenant_id")
    creator = relationship("User", foreign_keys="Reservation.created_by")
    updater = relationship("User", foreign_keys="Reservation.updated_by")
    status_history = relationship("ReservationStatusHistory", back_populates="reservation", cascade="all, delete-orphan")
    
    # Table indexes
    __table_args__ = (
        Index('idx_reservations_property_id', 'property_id'),
        Index('idx_reservations_user_id', 'user_id'),
        Index('idx_reservations_status', 'status'),
        Index('idx_reservations_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Reservation(property='{self.property_id}', customer='{self.customer_name}', status='{self.status}')>"

class ReservationStatusHistory(Base, TenantMixin):
    """Track reservation status changes"""
    __tablename__ = "reservation_status_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Status Change Information
    from_status = Column(Integer, nullable=True)
    to_status = Column(Integer, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    
    # Relationships
    reservation = relationship("Reservation", back_populates="status_history")
    changed_by_user = relationship("User")
    tenant = relationship("Tenant", foreign_keys="ReservationStatusHistory.tenant_id")
    
    def __repr__(self):
        return f"<ReservationStatusHistory(reservation='{self.reservation_id}', from='{self.from_status}', to='{self.to_status}')>"


class FeeTableB(Base, AuditMixin):
    """Table B from GNotKG (Gerichts- und Notarkostengesetz) for fee calculations"""
    __tablename__ = "fee_table_b"
    
    # Business value range
    geschaeftswert_from = Column(Numeric(12, 2), nullable=False)
    geschaeftswert_to = Column(Numeric(12, 2), nullable=True)  # NULL for last entry (unbounded)
    
    # Fee amount
    gebuehr = Column(Numeric(10, 2), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_fee_table_b_geschaeftswert', 'geschaeftswert_from', 'geschaeftswert_to'),
    )
    
    def __repr__(self):
        return f"<FeeTableB(from={self.geschaeftswert_from}, to={self.geschaeftswert_to}, fee={self.gebuehr})>"


class TenantFeeConfig(Base, TenantMixin, AuditMixin):
    """Tenant-level configuration for notary and Grundbuch fees"""
    __tablename__ = "tenant_fee_configs"
    
    # Notary fee rates (Gebührensätze)
    notary_kaufvertrag_rate = Column(Numeric(3, 1), nullable=False, default=2.0)
    notary_grundschuld_rate = Column(Numeric(3, 1), nullable=False, default=1.0)
    notary_vollzug_rate = Column(Numeric(3, 1), nullable=False, default=0.5)
    
    # Grundbuch fee rates (Gebührensätze)
    grundbuch_auflassung_rate = Column(Numeric(3, 1), nullable=False, default=0.5)
    grundbuch_eigentum_rate = Column(Numeric(3, 1), nullable=False, default=1.0)
    grundbuch_grundschuld_rate = Column(Numeric(3, 1), nullable=False, default=1.0)
    
    # Override option (percentage of purchase price)
    notary_override_percentage = Column(Numeric(5, 2), nullable=True)  # e.g., 1.5 for 1.5%
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys="TenantFeeConfig.tenant_id")
    
    # Table indexes
    __table_args__ = (
        Index('idx_tenant_fee_config_tenant', 'tenant_id', unique=True),
    )
    
    def __repr__(self):
        return f"<TenantFeeConfig(tenant_id='{self.tenant_id}')>"