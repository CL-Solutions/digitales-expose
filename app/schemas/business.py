# ================================
# DIGITALES EXPOSE SCHEMAS (schemas/business.py)
# ================================

from pydantic import Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.schemas.base import BaseSchema, BaseResponseSchema, PaginationParams

# ================================
# Project Schemas
# ================================

class ProjectBase(BaseSchema):
    """Base schema for Project"""
    name: str = Field(..., max_length=255)
    street: str = Field(..., max_length=255)
    house_number: str = Field(..., max_length=50)
    city: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    country: Optional[str] = Field(default="Deutschland", max_length=100)
    zip_code: str = Field(..., max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Building Details
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    renovation_year: Optional[int] = Field(None, ge=1800, le=2100)
    total_floors: Optional[int] = Field(None, gt=0)
    building_type: Optional[str] = Field(None, max_length=100)
    
    # Building Features
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_basement: Optional[bool] = None
    has_garden: Optional[bool] = None
    
    # Energy Data
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    primary_energy_consumption: Optional[float] = Field(None, ge=0)
    heating_building_year: Optional[int] = Field(None, ge=1800, le=2100)
    
    # Additional Information
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    
    status: str = Field(default="available", pattern="^(available|reserved|sold)$")

    model_config = ConfigDict(from_attributes=True)

class ProjectCreate(ProjectBase):
    """Schema for creating a Project"""
    city_id: Optional[UUID] = None

class ProjectUpdate(BaseSchema):
    """Schema for updating a Project"""
    name: Optional[str] = Field(None, max_length=255)
    street: Optional[str] = Field(None, max_length=255)
    house_number: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=255)
    city_id: Optional[UUID] = None
    state: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    renovation_year: Optional[int] = Field(None, ge=1800, le=2100)
    total_floors: Optional[int] = Field(None, gt=0)
    building_type: Optional[str] = Field(None, max_length=100)
    
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_basement: Optional[bool] = None
    has_garden: Optional[bool] = None
    
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    primary_energy_consumption: Optional[float] = Field(None, ge=0)
    heating_building_year: Optional[int] = Field(None, ge=1800, le=2100)
    
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    
    status: Optional[str] = Field(None, pattern="^(available|reserved|sold)$")

    model_config = ConfigDict(from_attributes=True)

class ProjectImageSchema(BaseResponseSchema):
    """Schema for ProjectImage"""
    project_id: UUID
    image_url: str
    image_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class ProjectResponse(ProjectBase, BaseResponseSchema):
    """Schema for Project response"""
    city_id: Optional[UUID] = None
    investagon_id: Optional[str] = None
    
    # Include related data
    images: List[ProjectImageSchema] = []
    city_ref: Optional["CityResponse"] = None
    properties: List["PropertyOverview"] = []
    
    # Computed fields
    property_count: int = 0
    thumbnail_url: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    
    @model_validator(mode='before')
    @classmethod
    def calculate_counts(cls, values):
        """Calculate property count and thumbnail before validation"""
        if isinstance(values, dict):
            # Calculate property count
            if 'properties' in values:
                values['property_count'] = len(values['properties'])
            
            # Set thumbnail_url from first image
            if 'images' in values and values['images']:
                # Sort images by display_order and get the first one
                sorted_images = sorted(values['images'], key=lambda x: x.display_order if hasattr(x, 'display_order') else 0)
                if sorted_images:
                    first_image = sorted_images[0]
                    values['thumbnail_url'] = first_image.image_url if hasattr(first_image, 'image_url') else None
        
        return values

# ================================
# Project Image Schemas
# ================================

class ProjectImageCreate(BaseSchema):
    """Schema for creating a ProjectImage"""
    image_url: str
    image_type: str = Field(..., pattern="^(exterior|common_area|amenity|floor_plan)$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0)
    file_size: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = Field(None, max_length=100)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)

class ProjectImageUpdate(BaseSchema):
    """Schema for updating a ProjectImage"""
    image_url: Optional[str] = None
    image_type: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None

# ================================
# Property Schemas
# ================================

class PropertyBase(BaseSchema):
    """Base schema for Property"""
    project_id: UUID  # Required - property must belong to a project
    unit_number: str = Field(..., max_length=100)  # e.g., "WE1", "WE2", "WHG 103"
    
    # Location data (denormalized from project for search/filter)
    city: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    zip_code: str = Field(..., max_length=20)
    
    property_type: str = Field(..., max_length=100)  # 'apartment', 'studio', 'penthouse'
    
    # Property Details
    size_sqm: float = Field(..., ge=0)
    rooms: float = Field(..., ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[str] = Field(None, max_length=50)  # e.g., "1. OG", "2. OG Mitte", "EG"
    balcony: Optional[bool] = None
    
    purchase_price: Decimal = Field(..., decimal_places=2, ge=0)
    purchase_price_parking: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    purchase_price_furniture: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    monthly_rent: Decimal = Field(..., decimal_places=2, ge=0)
    rent_parking_month: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    additional_costs: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    management_fee: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Transaction Costs (as percentages)
    transaction_broker_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_tax_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_notary_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_register_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Operating Costs
    operation_cost_landlord: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    operation_cost_tenant: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    operation_cost_reserve: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Additional Property Data
    object_share_owner: Optional[float] = Field(None, ge=0)  # Can be percentage value from Investagon
    share_land: Optional[float] = Field(None, ge=0)
    property_usage: Optional[str] = Field(None, max_length=100)
    initial_maintenance_expenses: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Depreciation Settings
    degressive_depreciation_building_onoff: Optional[int] = Field(None, ge=-1, le=1)
    depreciation_rate_building_manual: Optional[float] = Field(None, ge=0, le=100)
    
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)  # Endenergieverbrauch
    primary_energy_consumption: Optional[float] = Field(None, ge=0)  # Primärenergieverbrauch
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    # Investagon Status Flags
    active: Optional[int] = Field(None, ge=0)
    pre_sale: Optional[int] = Field(None, ge=0, le=1)
    draft: Optional[int] = Field(None, ge=0, le=1)

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float
        }
    )

class PropertyCreate(PropertyBase):
    """Schema for creating a Property"""
    city_id: Optional[UUID] = None
    investagon_id: Optional[str] = None

class PropertyUpdate(BaseSchema):
    """Schema for updating a Property"""
    project_id: Optional[UUID] = None  # Allow changing project
    unit_number: Optional[str] = Field(None, max_length=100)
    
    # Location updates (denormalized)
    city: Optional[str] = Field(None, max_length=255)
    city_id: Optional[UUID] = None
    state: Optional[str] = Field(None, max_length=255)
    zip_code: Optional[str] = Field(None, max_length=20)
    
    property_type: Optional[str] = Field(None, max_length=100)
    
    # Property Details
    size_sqm: Optional[float] = Field(None, ge=0)
    rooms: Optional[float] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[str] = Field(None, max_length=50)
    balcony: Optional[bool] = None
    
    purchase_price: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    purchase_price_parking: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    purchase_price_furniture: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    monthly_rent: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    rent_parking_month: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    additional_costs: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    management_fee: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Transaction Costs
    transaction_broker_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_tax_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_notary_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    transaction_register_rate: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Operating Costs
    operation_cost_landlord: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    operation_cost_tenant: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    operation_cost_reserve: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Additional Property Data
    object_share_owner: Optional[float] = Field(None, ge=0, le=1)
    share_land: Optional[float] = Field(None, ge=0)
    property_usage: Optional[str] = Field(None, max_length=100)
    initial_maintenance_expenses: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    # Depreciation Settings
    degressive_depreciation_building_onoff: Optional[int] = Field(None, ge=-1, le=1)
    depreciation_rate_building_manual: Optional[float] = Field(None, ge=0, le=100)
    
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)
    primary_energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    # Investagon Status Flags
    active: Optional[int] = Field(None, ge=0)
    pre_sale: Optional[int] = Field(None, ge=0, le=1)
    draft: Optional[int] = Field(None, ge=0, le=1)

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float
        }
    )

class PropertyImageSchema(BaseResponseSchema):
    """Schema for PropertyImage"""
    property_id: UUID
    image_url: str
    image_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class PropertyResponse(PropertyBase, BaseResponseSchema):
    """Schema for Property response"""
    city_id: Optional[UUID] = None
    investagon_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    
    # Include related data
    project: Optional["ProjectResponse"] = None
    images: List[PropertyImageSchema] = []  # Property-specific images only
    city_ref: Optional["CityResponse"] = None
    
    # Computed fields
    total_investment: Optional[Decimal] = None
    gross_rental_yield: Optional[float] = None
    net_rental_yield: Optional[float] = None
    all_images: List[PropertyImageSchema] = []  # Combined project + property images
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={
            Decimal: float
        }
    )
    
    @model_validator(mode='before')
    @classmethod
    def combine_project_and_property_images(cls, values):
        """Always combine project images with property images"""
        if isinstance(values, dict):
            property_images = values.get('images', [])
            project = values.get('project')
            
            # Start with project images if available
            all_images = []
            if project and hasattr(project, 'images') and project.images:
                # Add project images first (they're usually exterior/building shots)
                all_images.extend(project.images)
            
            # Then add property-specific images
            if property_images:
                all_images.extend(property_images)
            
            # Set the combined images
            values['all_images'] = all_images
                
        return values

    @model_validator(mode='before')
    @classmethod
    def calculate_yields(cls, values):
        """Calculate yield metrics before validation"""
        if isinstance(values, dict):
            purchase_price = values.get('purchase_price')
            monthly_rent = values.get('monthly_rent')
            additional_costs = values.get('additional_costs')
            management_fee = values.get('management_fee')
            
            if purchase_price and monthly_rent:
                try:
                    annual_rent = monthly_rent * 12
                    values['total_investment'] = purchase_price
                    values['gross_rental_yield'] = float((annual_rent / purchase_price) * 100)
                    
                    if additional_costs and management_fee:
                        annual_costs = (additional_costs + management_fee) * 12
                        net_annual_rent = annual_rent - annual_costs
                        values['net_rental_yield'] = float((net_annual_rent / purchase_price) * 100)
                except (TypeError, ZeroDivisionError, ValueError):
                    # Skip calculation if there are type/calculation errors
                    pass
        return values

# ================================
# Property Image Schemas
# ================================

class PropertyImageCreate(BaseSchema):
    """Schema for creating a PropertyImage"""
    image_url: str
    image_type: str = Field(..., pattern="^(exterior|interior|floor_plan|energy_certificate|bathroom|kitchen|bedroom|living_room|balcony|garden|parking|basement|roof)$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0)
    file_size: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = Field(None, max_length=100)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)

class PropertyImageUpdate(BaseSchema):
    """Schema for updating a PropertyImage"""
    image_url: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None

# ================================
# City Schemas
# ================================

class CityBase(BaseSchema):
    """Base schema for City"""
    name: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    country: str = Field(default="Germany", max_length=100)
    
    population: Optional[int] = Field(None, gt=0)
    population_growth: Optional[float] = None
    unemployment_rate: Optional[float] = Field(None, ge=0, le=100)
    average_income: Optional[int] = Field(None, gt=0)
    
    universities: Optional[List[str]] = None
    major_employers: Optional[List[Dict[str, str]]] = None
    public_transport: Optional[Dict[str, Any]] = None
    
    description: Optional[str] = None
    highlights: Optional[List[Dict[str, str]]] = None

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('major_employers', 'highlights', mode='before')
    @classmethod
    def clean_list_items(cls, v):
        """Clean up list items - remove None values and ensure proper format"""
        if v is None:
            return None
        if isinstance(v, list):
            # Filter out None values and ensure all items are dicts
            cleaned = []
            for item in v:
                if item is not None:
                    if isinstance(item, dict):
                        cleaned.append(item)
                    elif isinstance(item, str):
                        # Convert old string format to new dict format
                        cleaned.append({"title": item, "description": ""})
            return cleaned if cleaned else None
        return v

class CityCreate(CityBase):
    """Schema for creating a City"""
    pass

class CityUpdate(BaseSchema):
    """Schema for updating a City"""
    population: Optional[int] = Field(None, gt=0)
    population_growth: Optional[float] = None
    unemployment_rate: Optional[float] = Field(None, ge=0, le=100)
    average_income: Optional[int] = Field(None, gt=0)
    
    universities: Optional[List[str]] = None
    major_employers: Optional[List[Dict[str, str]]] = None
    public_transport: Optional[Dict[str, Any]] = None
    
    description: Optional[str] = None
    highlights: Optional[List[Dict[str, str]]] = None
    
    @field_validator('major_employers', 'highlights', mode='before')
    @classmethod
    def clean_list_items_update(cls, v):
        """Clean up list items - remove None values and ensure proper format"""
        if v is None:
            return None
        if isinstance(v, list):
            # Filter out None values and ensure all items are dicts
            cleaned = []
            for item in v:
                if item is not None:
                    if isinstance(item, dict):
                        cleaned.append(item)
                    elif isinstance(item, str):
                        # Convert old string format to new dict format
                        cleaned.append({"title": item, "description": ""})
            return cleaned if cleaned else None
        return v

# ================================
# City Image Schemas
# ================================

class CityImageCreate(BaseSchema):
    """Schema for creating a CityImage"""
    image_url: str
    image_type: str = Field(..., pattern="^(skyline|landmark|downtown|residential|commercial|nature|transport|culture|nightlife|education|recreation|overview)$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0)
    file_size: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = Field(None, max_length=100)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)

class CityImageUpdate(BaseSchema):
    """Schema for updating a CityImage"""
    image_url: Optional[str] = None
    image_type: Optional[str] = Field(None, pattern="^(skyline|landmark|downtown|residential|commercial|nature|transport|culture|nightlife|education|recreation|overview)$")
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None

class CityImageSchema(BaseResponseSchema):
    """Schema for CityImage"""
    city_id: UUID
    image_url: str
    image_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class CityResponse(CityBase, BaseResponseSchema):
    """Schema for City response"""
    images: List[CityImageSchema] = []
    
    # Override the validators from CityBase to ensure they're applied
    @field_validator('major_employers', 'highlights', mode='before')
    @classmethod
    def clean_list_items_response(cls, v):
        """Clean up list items - remove None values and ensure proper format"""
        if v is None:
            return None
        if isinstance(v, list):
            # Filter out None values and ensure all items are dicts
            cleaned = []
            for item in v:
                if item is not None:
                    if isinstance(item, dict):
                        cleaned.append(item)
                    elif isinstance(item, str):
                        # Convert old string format to new dict format
                        cleaned.append({"title": item, "description": ""})
            return cleaned if cleaned else None
        return v

# ================================
# Expose Template Schemas
# ================================

class ExposeTemplateBase(BaseSchema):
    """Base schema for ExposeTemplate"""
    name: str = Field(..., max_length=255)
    property_type: Optional[str] = Field(None, max_length=100)
    
    investment_benefits: Optional[str] = None
    location_description: Optional[str] = None
    property_description: Optional[str] = None
    financing_info: Optional[str] = None
    tax_benefits: Optional[str] = None
    risks_disclaimer: Optional[str] = None
    company_info: Optional[str] = None
    process_steps: Optional[str] = None
    
    default_equity_percentage: float = Field(default=20.0, ge=0, le=100)
    default_interest_rate: float = Field(default=3.5, ge=0, le=20)
    default_loan_term_years: int = Field(default=20, ge=1, le=50)
    default_tax_rate: float = Field(default=42.0, ge=0, le=100)
    
    is_active: bool = True
    is_default: bool = False

    model_config = ConfigDict(from_attributes=True)

class ExposeTemplateCreate(ExposeTemplateBase):
    """Schema for creating an ExposeTemplate"""
    pass

class ExposeTemplateUpdate(BaseSchema):
    """Schema for updating an ExposeTemplate"""
    name: Optional[str] = Field(None, max_length=255)
    property_type: Optional[str] = Field(None, max_length=100)
    
    investment_benefits: Optional[str] = None
    location_description: Optional[str] = None
    property_description: Optional[str] = None
    financing_info: Optional[str] = None
    tax_benefits: Optional[str] = None
    risks_disclaimer: Optional[str] = None
    company_info: Optional[str] = None
    process_steps: Optional[str] = None
    
    default_equity_percentage: Optional[float] = Field(None, ge=0, le=100)
    default_interest_rate: Optional[float] = Field(None, ge=0, le=20)
    default_loan_term_years: Optional[int] = Field(None, ge=1, le=50)
    default_tax_rate: Optional[float] = Field(None, ge=0, le=100)
    
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

class ExposeTemplateResponse(ExposeTemplateBase, BaseResponseSchema):
    """Schema for ExposeTemplate response"""
    pass

# ================================
# Expose Link Schemas
# ================================

class ExposeLinkBase(BaseSchema):
    """Base schema for ExposeLink"""
    property_id: UUID
    template_id: Optional[UUID] = None
    name: Optional[str] = Field(None, max_length=255)
    
    preset_equity_amount: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    preset_interest_rate: Optional[float] = Field(None, ge=0, le=20)
    preset_loan_term_years: Optional[int] = Field(None, ge=1, le=50)
    preset_monthly_rent: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    expiration_date: Optional[datetime] = None
    password_protected: bool = False
    password: Optional[str] = Field(None, exclude=True)  # Only for creation
    
    visible_sections: Optional[Dict[str, bool]] = None
    custom_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExposeLinkCreate(ExposeLinkBase):
    """Schema for creating an ExposeLink"""
    @field_validator('password')
    def validate_password(cls, v, values):
        if values.data.get('password_protected') and not v:
            raise ValueError('Password is required when password_protected is True')
        return v

class ExposeLinkUpdate(BaseSchema):
    """Schema for updating an ExposeLink"""
    name: Optional[str] = Field(None, max_length=255)
    
    preset_equity_amount: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    preset_interest_rate: Optional[float] = Field(None, ge=0, le=20)
    preset_loan_term_years: Optional[int] = Field(None, ge=1, le=50)
    preset_monthly_rent: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    
    visible_sections: Optional[Dict[str, bool]] = None
    custom_message: Optional[str] = None

class ExposeLinkResponse(ExposeLinkBase, BaseResponseSchema):
    """Schema for ExposeLink response"""
    link_id: str
    is_active: bool = True
    view_count: int = 0
    first_viewed_at: Optional[datetime] = None
    last_viewed_at: Optional[datetime] = None
    created_at: datetime
    created_by: UUID
    
    # Include property basic info - use forward reference to avoid circular imports
    property: Optional["PropertyOverview"] = None
    template: Optional[ExposeTemplateResponse] = None

class ExposeLinkPublicResponse(BaseSchema):
    """Schema for public ExposeLink response (for viewers)"""
    link_id: str
    property: PropertyResponse
    template: Optional[ExposeTemplateResponse] = None
    
    preset_equity_amount: Optional[Decimal] = None
    preset_interest_rate: Optional[float] = None
    preset_loan_term_years: Optional[int] = None
    preset_monthly_rent: Optional[Decimal] = None
    
    visible_sections: Optional[Dict[str, bool]] = None
    custom_message: Optional[str] = None
    
    # City information if available
    city_info: Optional[CityResponse] = None

    model_config = ConfigDict(from_attributes=True)

# ================================
# Investagon Sync Schemas
# ================================

class InvestagonSyncSchema(BaseResponseSchema):
    """Schema for InvestagonSync"""
    sync_type: str  # single_property, full, incremental
    status: str  # pending, in_progress, completed, partial, failed
    started_at: datetime
    completed_at: Optional[datetime] = None
    properties_created: int = 0
    properties_updated: int = 0
    properties_failed: int = 0
    error_details: Optional[Dict[str, Any]] = None
    created_by: UUID

# ================================
# Search and Filter Schemas
# ================================

class ProjectFilter(PaginationParams):
    """Schema for project filtering"""
    city: Optional[str] = None
    state: Optional[str] = None
    status: Optional[str] = None
    building_type: Optional[str] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    min_construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    max_construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

class ProjectOverview(BaseSchema):
    """Schema for Project overview (list view)"""
    id: UUID
    name: str
    street: str
    house_number: str
    city: str
    state: str
    zip_code: str
    status: str
    building_type: Optional[str] = None
    total_floors: Optional[int] = None
    construction_year: Optional[int] = None
    property_count: int = 0
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None
    thumbnail_url: Optional[str] = None
    investagon_id: Optional[str] = None
    visibility_status: Optional[str] = None  # 'active', 'in_progress', 'deactivated', 'mixed'
    min_rental_yield: Optional[float] = None  # Minimum Bruttomietrendite of properties
    max_rental_yield: Optional[float] = None  # Maximum Bruttomietrendite of properties
    
    model_config = ConfigDict(from_attributes=True)

class ProjectListResponse(BaseSchema):
    """Schema for paginated project list"""
    items: List[ProjectOverview]
    total: int
    page: int
    size: int
    pages: int
    
    model_config = ConfigDict(from_attributes=True)

class PropertyFilter(PaginationParams):
    """Schema for property filtering"""
    project_id: Optional[UUID] = None  # Filter by project
    city: Optional[str] = None
    state: Optional[str] = None
    property_type: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    min_rental_yield: Optional[float] = None  # Filter by minimum Bruttomietrendite
    max_rental_yield: Optional[float] = None  # Filter by maximum Bruttomietrendite
    energy_class: Optional[str] = None
    # Investagon status filters
    active: Optional[List[int]] = None  # Multiple statuses
    pre_sale: Optional[int] = None
    draft: Optional[int] = None
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

class PropertyOverview(BaseSchema):
    """Schema for Property overview (list view)"""
    id: UUID
    project_id: UUID
    project_name: Optional[str] = None  # Denormalized for performance
    project_street: Optional[str] = None
    project_house_number: Optional[str] = None
    unit_number: str
    city: str
    state: str
    property_type: str
    purchase_price: Decimal
    monthly_rent: Decimal
    size_sqm: float
    rooms: float
    floor: Optional[str] = None
    investagon_id: Optional[str] = None
    # Investagon status fields
    active: Optional[int] = None
    pre_sale: Optional[int] = None
    draft: Optional[int] = None
    visibility: Optional[int] = None
    
    # Calculated fields
    gross_rental_yield: Optional[float] = None  # Bruttomietrendite in percent
    
    # Thumbnail URL from S3 for list view
    thumbnail_url: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: float
        }
    )

class PropertyListResponse(BaseSchema):
    """Schema for paginated property list"""
    items: List[PropertyOverview]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)