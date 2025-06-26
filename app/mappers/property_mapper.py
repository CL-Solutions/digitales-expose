"""
Property Mapper Module
Handles conversion of Property ORM objects to response dictionaries
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.models.business import Property, Project


def map_property_to_overview(prop: Property) -> Dict[str, Any]:
    """
    Map a Property ORM object to PropertyOverview response format
    
    Args:
        prop: Property ORM object with loaded relationships
        
    Returns:
        Dictionary matching PropertyOverview schema
    """
    # Get thumbnail - first try property images, then fall back to project images
    thumbnail_url = prop.thumbnail_url  # This checks property images
    
    if not thumbnail_url and prop.project and prop.project.images:
        # If no property images, use first project image
        sorted_project_images = sorted(
            prop.project.images, 
            key=lambda x: (x.display_order, x.created_at if x.created_at else datetime.min.replace(tzinfo=timezone.utc))
        )
        if sorted_project_images:
            thumbnail_url = sorted_project_images[0].image_url
    
    # Calculate total purchase price including parking and furniture
    total_purchase_price = float(prop.purchase_price or 0)
    if prop.purchase_price_parking:
        total_purchase_price += float(prop.purchase_price_parking)
    if prop.purchase_price_furniture:
        total_purchase_price += float(prop.purchase_price_furniture)
    
    # Calculate total monthly rent including parking
    total_monthly_rent = float(prop.monthly_rent or 0)
    if prop.rent_parking_month:
        total_monthly_rent += float(prop.rent_parking_month)
    
    # Calculate gross rental yield (Bruttomietrendite) based on total price and total rent
    gross_rental_yield = None
    if total_purchase_price > 0 and total_monthly_rent > 0:
        annual_rent = total_monthly_rent * 12
        gross_rental_yield = (annual_rent / total_purchase_price) * 100
    
    overview_data = {
        "id": prop.id,
        "project_id": prop.project_id,
        "unit_number": prop.unit_number,
        "city": prop.city,
        "state": prop.state,
        "property_type": prop.property_type,
        "purchase_price": total_purchase_price,  # Total including parking and furniture
        "monthly_rent": total_monthly_rent,  # Total including parking rent
        "size_sqm": prop.size_sqm,
        "rooms": prop.rooms,
        "floor": prop.floor,
        "investagon_id": prop.investagon_id,
        "active": prop.active,
        "pre_sale": prop.pre_sale,
        "draft": prop.draft,
        "visibility": prop.visibility,
        "thumbnail_url": thumbnail_url,
        "gross_rental_yield": gross_rental_yield
    }
    
    # Add project information if loaded
    if prop.project:
        overview_data["project_name"] = prop.project.name
        overview_data["project_street"] = prop.project.street
        overview_data["project_house_number"] = prop.project.house_number
    else:
        overview_data["project_name"] = None
        overview_data["project_street"] = None
        overview_data["project_house_number"] = None
    
    return overview_data


def map_property_to_response(prop: Property) -> Dict[str, Any]:
    """
    Map a Property ORM object to full PropertyResponse format
    
    Args:
        prop: Property ORM object with loaded relationships
        
    Returns:
        Dictionary matching PropertyResponse schema
    """
    # Start with base property data
    response_data = {
        "id": prop.id,
        "project_id": prop.project_id,
        "unit_number": prop.unit_number,
        "city": prop.city,
        "state": prop.state,
        "zip_code": prop.zip_code,
        "property_type": prop.property_type,
        "size_sqm": prop.size_sqm,
        "rooms": prop.rooms,
        "bathrooms": prop.bathrooms,
        "floor": prop.floor,
        "balcony": prop.balcony,
        "purchase_price": prop.purchase_price,
        "purchase_price_parking": prop.purchase_price_parking,
        "purchase_price_furniture": prop.purchase_price_furniture,
        "monthly_rent": prop.monthly_rent,
        "rent_parking_month": prop.rent_parking_month,
        "additional_costs": prop.additional_costs,
        "management_fee": prop.management_fee,
        "transaction_broker_rate": prop.transaction_broker_rate,
        "transaction_tax_rate": prop.transaction_tax_rate,
        "transaction_notary_rate": prop.transaction_notary_rate,
        "transaction_register_rate": prop.transaction_register_rate,
        "operation_cost_landlord": prop.operation_cost_landlord,
        "operation_cost_tenant": prop.operation_cost_tenant,
        "operation_cost_reserve": prop.operation_cost_reserve,
        "object_share_owner": prop.object_share_owner,
        "share_land": prop.share_land,
        "property_usage": prop.property_usage,
        "initial_maintenance_expenses": prop.initial_maintenance_expenses,
        "degressive_depreciation_building_onoff": prop.degressive_depreciation_building_onoff,
        "depreciation_rate_building_manual": prop.depreciation_rate_building_manual,
        "energy_certificate_type": prop.energy_certificate_type,
        "energy_consumption": prop.energy_consumption,
        "primary_energy_consumption": prop.primary_energy_consumption,
        "energy_class": prop.energy_class,
        "heating_type": prop.heating_type,
        "active": prop.active,
        "pre_sale": prop.pre_sale,
        "draft": prop.draft,
        "visibility": prop.visibility,
        "city_id": prop.city_id,
        "investagon_id": prop.investagon_id,
        "last_sync": prop.last_sync,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,
        "created_by": prop.created_by,
        "updated_by": prop.updated_by
    }
    
    # Calculate total purchase price including parking and furniture
    total_purchase_price = float(prop.purchase_price or 0)
    if prop.purchase_price_parking:
        total_purchase_price += float(prop.purchase_price_parking)
    if prop.purchase_price_furniture:
        total_purchase_price += float(prop.purchase_price_furniture)
    
    # Calculate total monthly rent including parking
    total_monthly_rent = float(prop.monthly_rent or 0)
    if prop.rent_parking_month:
        total_monthly_rent += float(prop.rent_parking_month)
    
    # Add calculated fields - always include them so they're in the schema
    response_data["total_investment"] = None
    response_data["gross_rental_yield"] = None
    response_data["net_rental_yield"] = None
    
    if total_purchase_price > 0 and total_monthly_rent > 0:
        annual_rent = total_monthly_rent * 12
        response_data["total_investment"] = total_purchase_price
        response_data["gross_rental_yield"] = (annual_rent / total_purchase_price) * 100
        
        if prop.additional_costs and prop.management_fee:
            annual_costs = float(prop.additional_costs + prop.management_fee) * 12
            net_annual_rent = annual_rent - annual_costs
            response_data["net_rental_yield"] = (net_annual_rent / total_purchase_price) * 100
    
    # Add related data
    if hasattr(prop, 'project'):
        response_data["project"] = prop.project
    
    if hasattr(prop, 'images'):
        response_data["images"] = prop.images
    
    if hasattr(prop, 'city_ref'):
        response_data["city_ref"] = prop.city_ref
    
    # Don't set all_images here - let the PropertyResponse validator handle it
    # The validator in schemas/business.py will combine project and property images
    
    return response_data