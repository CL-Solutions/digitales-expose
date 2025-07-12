"""Type definitions for ExposeTemplate JSON fields"""
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class SectionKey(str, Enum):
    """Available sections in the expose"""
    HERO = "hero"
    CITY_INFO = "city_info"
    MICRO_LOCATION = "micro_location"
    PROPERTY_DATA = "property_data"
    FLOOR_PLAN = "floor_plan"
    MODERNIZATION = "modernization"
    FINANCIAL = "financial"
    VIRTUAL_TOUR = "virtual_tour"
    INSURANCE = "insurance"
    PROCESS_STEPS = "process_steps"
    OPPORTUNITIES_RISKS = "opportunities_risks"
    LIABILITY_DISCLAIMER = "liability_disclaimer"
    ONSITE_MANAGEMENT = "onsite_management"
    COLIVING = "coliving"
    SPECIAL_FEATURES = "special_features"
    CONTACT = "contact"


class EnabledSections(BaseModel):
    """Section visibility configuration"""
    hero: bool = Field(default=True)
    city_info: bool = Field(default=True)
    micro_location: bool = Field(default=True)
    property_data: bool = Field(default=True)
    floor_plan: bool = Field(default=True)
    modernization: bool = Field(default=True)
    financial: bool = Field(default=True)
    virtual_tour: bool = Field(default=True)
    insurance: bool = Field(default=True)
    process_steps: bool = Field(default=True)
    opportunities_risks: bool = Field(default=True)
    liability_disclaimer: bool = Field(default=True)
    onsite_management: bool = Field(default=True)
    coliving: bool = Field(default=True)
    special_features: bool = Field(default=True)
    contact: bool = Field(default=True)


class ModernizationItem(BaseModel):
    """Single modernization item"""
    title: str = Field(..., description="Title of the modernization")
    description: Optional[str] = Field(None, description="Optional description")


class InsurancePlan(BaseModel):
    """Insurance plan configuration"""
    name: str = Field(..., description="Plan name (e.g., 'Basis', 'Premium', 'Komplett')")
    price: float = Field(..., description="Annual price")
    period: str = Field(default="pro Jahr", description="Billing period")
    features: List[str] = Field(..., description="List of features")
    recommended: bool = Field(default=False, description="Whether this plan is recommended")


class ProcessStep(BaseModel):
    """Single process step"""
    number: int = Field(..., description="Step number")
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Step description")
    color_scheme: str = Field(default="amber", description="Color scheme: amber, blue, or green")


class OpportunityItem(BaseModel):
    """Opportunity/chance item"""
    title: str = Field(..., description="Opportunity title")
    description: Optional[str] = Field(None, description="Optional detailed description")


class RiskItem(BaseModel):
    """Risk item"""
    title: str = Field(..., description="Risk title")
    description: Optional[str] = Field(None, description="Optional detailed description")


class OpportunitiesRisksSection(BaseModel):
    """Single section for opportunities and risks content"""
    headline: str = Field(..., description="Section headline")
    content: str = Field(..., description="Section content (can be multi-paragraph)")
    is_expanded_by_default: bool = Field(default=False, description="Whether this section should be expanded by default")


class OnsiteManagementService(BaseModel):
    """On-site management service item"""
    service: str = Field(..., description="Service name")
    description: Optional[str] = Field(None, description="Optional service description")


class OnsiteManagementPackage(BaseModel):
    """Management package details"""
    name: str = Field(..., description="Package name (e.g., 'ANGEBOT 360°+')")
    price: float = Field(..., description="Package price")
    unit: str = Field(default="€ brutto monatlich pro Wohnung", description="Price unit")


class SpecialFeatureItem(BaseModel):
    """Special feature item"""
    title: str = Field(..., description="Feature title")
    description: Optional[str] = Field(None, description="Optional feature description")