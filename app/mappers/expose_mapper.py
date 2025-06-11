"""
Expose Mapper Module
Handles conversion of ExposeLink ORM objects to response dictionaries
"""
from typing import Dict, Any, Optional, List
from app.models.business import ExposeLink, Property
from app.mappers.property_mapper import map_property_to_overview


def map_expose_link_to_response(link: ExposeLink) -> Dict[str, Any]:
    """
    Map an ExposeLink ORM object to ExposeLinkResponse format
    
    Args:
        link: ExposeLink ORM object with loaded relationships
        
    Returns:
        Dictionary matching ExposeLinkResponse schema
    """
    response_data = {
        "id": link.id,
        "link_id": link.link_id,
        "property_id": link.property_id,
        "template_id": link.template_id,
        "name": link.name,
        "is_active": link.is_active,
        "view_count": link.view_count,
        "first_viewed_at": link.first_viewed_at,
        "last_viewed_at": link.last_viewed_at,
        "created_at": link.created_at,
        "created_by": link.created_by,
        "preset_equity_amount": link.preset_equity_amount,
        "preset_interest_rate": link.preset_interest_rate,
        "preset_loan_term_years": link.preset_loan_term_years,
        "preset_monthly_rent": link.preset_monthly_rent,
        "expiration_date": link.expiration_date,
        "password_protected": link.password_protected,
        "visible_sections": link.visible_sections,
        "custom_message": link.custom_message
    }
    
    # Add property overview if available
    if link.property:
        response_data["property"] = map_property_to_overview(link.property)
    
    # Add template if present
    if link.template:
        response_data["template"] = link.template
    
    return response_data


def map_expose_links_to_responses(links: List[ExposeLink]) -> List[Dict[str, Any]]:
    """
    Map a list of ExposeLink ORM objects to response format
    
    Args:
        links: List of ExposeLink ORM objects with loaded relationships
        
    Returns:
        List of dictionaries matching ExposeLinkResponse schema
    """
    return [map_expose_link_to_response(link) for link in links]