"""Type definitions for ExposeTemplate JSON fields"""
from typing import Optional, List, Dict
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
    INSURANCE = "insurance"
    PROCESS_STEPS = "process_steps"
    OPPORTUNITIES_RISKS = "opportunities_risks"
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
    insurance: bool = Field(default=True)
    process_steps: bool = Field(default=True)
    opportunities_risks: bool = Field(default=True)
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