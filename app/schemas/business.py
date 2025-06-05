# ================================
# DIGITALES EXPOSE SCHEMAS (schemas/business.py)
# ================================

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginationParams

# ================================
# Property Schemas
# ================================

class PropertyBase(BaseModel):
    """Base schema for Property"""
    street: Optional[str] = Field(None, max_length=255)
    house_number: Optional[str] = Field(None, max_length=50)
    apartment_number: Optional[str] = Field(None, max_length=100)
    city: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    zip_code: str = Field(..., max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    property_type: str = Field(..., max_length=100)
    
    size_sqm: float = Field(..., ge=0)
    rooms: float = Field(..., ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = Field(None)
    total_floors: Optional[int] = Field(None, gt=0)
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    renovation_year: Optional[int] = Field(None, ge=1800, le=2100)
    
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
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    status: str = Field(default="available", pattern="^(available|reserved|sold)$")
    
    # Investagon Status Flags
    active: Optional[int] = Field(None, ge=0)
    pre_sale: Optional[int] = Field(None, ge=0, le=1)
    draft: Optional[int] = Field(None, ge=0, le=1)

    model_config = ConfigDict(from_attributes=True)

class PropertyCreate(PropertyBase):
    """Schema for creating a Property"""
    city_id: Optional[UUID] = None
    investagon_id: Optional[str] = None

class PropertyUpdate(BaseModel):
    """Schema for updating a Property"""
    street: Optional[str] = Field(None, max_length=255)
    house_number: Optional[str] = Field(None, max_length=50)
    apartment_number: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=255)
    city_id: Optional[UUID] = None
    state: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    property_type: Optional[str] = Field(None, max_length=100)
    
    size_sqm: Optional[float] = Field(None, ge=0)
    rooms: Optional[float] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = None
    total_floors: Optional[int] = Field(None, gt=0)
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    renovation_year: Optional[int] = Field(None, ge=1800, le=2100)
    
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
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    status: Optional[str] = Field(None, pattern="^(available|reserved|sold)$")
    
    # Investagon Status Flags
    active: Optional[int] = Field(None, ge=0)
    pre_sale: Optional[int] = Field(None, ge=0, le=1)
    draft: Optional[int] = Field(None, ge=0, le=1)

    model_config = ConfigDict(from_attributes=True)

class PropertyImageSchema(BaseSchema):
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

class PropertyResponse(PropertyBase, BaseSchema):
    """Schema for Property response"""
    city_id: Optional[UUID] = None
    investagon_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    
    # Include related data
    images: List[PropertyImageSchema] = []
    city_ref: Optional["CityResponse"] = None
    
    # Computed fields
    total_investment: Optional[Decimal] = None
    gross_rental_yield: Optional[float] = None
    net_rental_yield: Optional[float] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )

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

class PropertyImageCreate(BaseModel):
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

class PropertyImageUpdate(BaseModel):
    """Schema for updating a PropertyImage"""
    image_url: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None

# ================================
# City Schemas
# ================================

class CityBase(BaseModel):
    """Base schema for City"""
    name: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    country: str = Field(default="Germany", max_length=100)
    
    population: Optional[int] = Field(None, gt=0)
    population_growth: Optional[float] = None
    unemployment_rate: Optional[float] = Field(None, ge=0, le=100)
    average_income: Optional[int] = Field(None, gt=0)
    
    universities: Optional[List[str]] = None
    major_employers: Optional[List[str]] = None
    public_transport: Optional[Dict[str, Any]] = None
    
    description: Optional[str] = None
    highlights: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

class CityCreate(CityBase):
    """Schema for creating a City"""
    pass

class CityUpdate(BaseModel):
    """Schema for updating a City"""
    population: Optional[int] = Field(None, gt=0)
    population_growth: Optional[float] = None
    unemployment_rate: Optional[float] = Field(None, ge=0, le=100)
    average_income: Optional[int] = Field(None, gt=0)
    
    universities: Optional[List[str]] = None
    major_employers: Optional[List[str]] = None
    public_transport: Optional[Dict[str, Any]] = None
    
    description: Optional[str] = None
    highlights: Optional[List[str]] = None

# ================================
# City Image Schemas
# ================================

class CityImageCreate(BaseModel):
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

class CityImageUpdate(BaseModel):
    """Schema for updating a CityImage"""
    image_url: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None

class CityImageSchema(BaseSchema):
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

class CityResponse(CityBase, BaseSchema):
    """Schema for City response"""
    images: List[CityImageSchema] = []

# ================================
# Expose Template Schemas
# ================================

class ExposeTemplateBase(BaseModel):
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

class ExposeTemplateUpdate(BaseModel):
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

class ExposeTemplateResponse(ExposeTemplateBase, BaseSchema):
    """Schema for ExposeTemplate response"""
    pass

# ================================
# Expose Link Schemas
# ================================

class ExposeLinkBase(BaseModel):
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

class ExposeLinkUpdate(BaseModel):
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

class ExposeLinkResponse(ExposeLinkBase, BaseSchema):
    """Schema for ExposeLink response"""
    link_id: str
    is_active: bool = True
    view_count: int = 0
    first_viewed_at: Optional[datetime] = None
    last_viewed_at: Optional[datetime] = None
    
    # Include property basic info - use forward reference to avoid circular imports
    property: Optional["PropertyOverview"] = None
    template: Optional[ExposeTemplateResponse] = None

class ExposeLinkPublicResponse(BaseModel):
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

class InvestagonSyncSchema(BaseSchema):
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

class PropertyFilter(PaginationParams):
    """Schema for property filtering"""
    city: Optional[str] = None
    state: Optional[str] = None
    property_type: Optional[str] = None
    status: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    energy_class: Optional[str] = None
    # Investagon status filters
    active: Optional[int] = None
    pre_sale: Optional[int] = None
    draft: Optional[int] = None
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

class PropertyOverview(BaseModel):
    """Schema for Property overview (list view)"""
    id: UUID
    street: Optional[str] = None
    house_number: Optional[str] = None
    apartment_number: Optional[str] = None
    city: str
    state: str
    property_type: str
    status: str
    purchase_price: Decimal
    monthly_rent: Decimal
    size_sqm: float
    rooms: float
    investagon_id: Optional[str] = None
    # Investagon status fields
    active: Optional[int] = None
    pre_sale: Optional[int] = None
    draft: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class PropertyListResponse(BaseModel):
    """Schema for paginated property list"""
    items: List[PropertyOverview]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)