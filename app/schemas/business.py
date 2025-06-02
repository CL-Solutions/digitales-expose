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
    address: str = Field(..., max_length=500)
    city: str = Field(..., max_length=255)
    state: str = Field(..., max_length=255)
    zip_code: str = Field(..., max_length=20)
    property_type: str = Field(..., max_length=100)
    
    size_sqm: float = Field(..., gt=0)
    rooms: float = Field(..., gt=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = Field(None)
    total_floors: Optional[int] = Field(None, gt=0)
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    
    purchase_price: Decimal = Field(..., decimal_places=2, ge=0)
    monthly_rent: Decimal = Field(..., decimal_places=2, ge=0)
    additional_costs: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    management_fee: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    status: str = Field(default="available", pattern="^(available|reserved|sold)$")

    model_config = ConfigDict(from_attributes=True)

class PropertyCreate(PropertyBase):
    """Schema for creating a Property"""
    investagon_id: Optional[str] = None

class PropertyUpdate(BaseModel):
    """Schema for updating a Property"""
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=255)
    zip_code: Optional[str] = Field(None, max_length=20)
    property_type: Optional[str] = Field(None, max_length=100)
    
    size_sqm: Optional[float] = Field(None, gt=0)
    rooms: Optional[float] = Field(None, gt=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = None
    total_floors: Optional[int] = Field(None, gt=0)
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    
    purchase_price: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    monthly_rent: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    additional_costs: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    management_fee: Optional[Decimal] = Field(None, decimal_places=2, ge=0)
    
    energy_certificate_type: Optional[str] = Field(None, max_length=50)
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_class: Optional[str] = Field(None, max_length=10)
    heating_type: Optional[str] = Field(None, max_length=100)
    
    status: Optional[str] = Field(None, pattern="^(available|reserved|sold)$")

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
    investagon_id: Optional[str] = None
    investagon_data: Optional[Dict[str, Any]] = None
    last_sync: Optional[datetime] = None
    images: List[PropertyImageSchema] = []
    
    # Computed fields
    total_investment: Optional[Decimal] = None
    gross_rental_yield: Optional[float] = None
    net_rental_yield: Optional[float] = None

    @model_validator(mode='after')
    def calculate_yields(self):
        if self.purchase_price and self.monthly_rent:
            annual_rent = self.monthly_rent * 12
            self.total_investment = self.purchase_price
            self.gross_rental_yield = float((annual_rent / self.purchase_price) * 100)
            
            if self.additional_costs and self.management_fee:
                annual_costs = (self.additional_costs + self.management_fee) * 12
                net_annual_rent = annual_rent - annual_costs
                self.net_rental_yield = float((net_annual_rent / self.purchase_price) * 100)
        return self

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
    
    # Include property basic info
    property: Optional[PropertyResponse] = None
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
    property_id: Optional[UUID] = None
    sync_type: str  # manual, full, incremental
    sync_status: str  # queued, in_progress, success, partial, failed
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_synced: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    sync_details: Optional[Dict[str, Any]] = None
    initiated_by: UUID

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

class PropertyListResponse(BaseModel):
    """Schema for paginated property list"""
    items: List[PropertyResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)