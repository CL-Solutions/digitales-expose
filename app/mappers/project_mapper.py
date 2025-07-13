"""
Project Mapper Module
Handles conversion of Project ORM objects to response dictionaries
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from app.models.business import Project


def map_project_to_overview(proj: Project) -> Dict[str, Any]:
    """
    Map a Project ORM object to ProjectOverview response format
    
    Args:
        proj: Project ORM object with loaded relationships
        
    Returns:
        Dictionary matching ProjectOverview schema
    """
    # Calculate visibility status based on contained properties
    visibility_status = None
    if hasattr(proj, 'properties') and proj.properties:
        visibility_values = [p.visibility for p in proj.properties if p.visibility is not None]
        if visibility_values:
            if any(v == 1 for v in visibility_values):
                visibility_status = 'active'
            elif all(v in [-1, 0] for v in visibility_values):
                visibility_status = 'inactive'
            else:
                visibility_status = 'mixed'
    
    # Get thumbnail from first image
    thumbnail_url = None
    if proj.images:
        sorted_images = sorted(
            proj.images,
            key=lambda x: (x.display_order, x.created_at if x.created_at else datetime.min.replace(tzinfo=timezone.utc))
        )
        if sorted_images:
            thumbnail_url = sorted_images[0].image_url
    
    overview_data = {
        "id": proj.id,
        "name": proj.name,
        "street": proj.street,
        "house_number": proj.house_number,
        "city": proj.city,
        "district": proj.district,
        "state": proj.state,
        "zip_code": proj.zip_code,
        "status": proj.status,
        "building_type": proj.building_type,
        "total_floors": proj.total_floors,
        "total_units": proj.total_units,
        "construction_year": proj.construction_year,
        "has_elevator": proj.has_elevator,
        "has_parking": proj.has_parking,
        "min_price": proj.min_price,
        "max_price": proj.max_price,
        "min_rental_yield": proj.min_rental_yield,
        "max_rental_yield": proj.max_rental_yield,
        "min_initial_maintenance_expenses": proj.min_initial_maintenance_expenses,
        "max_initial_maintenance_expenses": proj.max_initial_maintenance_expenses,
        "thumbnail_url": thumbnail_url,
        "property_count": len(proj.properties) if hasattr(proj, 'properties') else 0,
        "visibility_status": visibility_status,
        "investagon_id": proj.investagon_id,
        "provision_percentage": proj.provision_percentage
    }
    
    return overview_data


def map_project_to_response(proj: Project) -> Dict[str, Any]:
    """
    Map a Project ORM object to full ProjectResponse format
    
    Args:
        proj: Project ORM object with loaded relationships
        
    Returns:
        Dictionary matching ProjectResponse schema
    """
    # Get thumbnail from first image
    thumbnail_url = None
    if proj.images:
        sorted_images = sorted(
            proj.images,
            key=lambda x: (x.display_order, x.created_at if x.created_at else datetime.min.replace(tzinfo=timezone.utc))
        )
        if sorted_images:
            thumbnail_url = sorted_images[0].image_url
    
    # Build response data
    response_data = {
        "id": proj.id,
        "name": proj.name,
        "street": proj.street,
        "house_number": proj.house_number,
        "city": proj.city,
        "district": proj.district,
        "state": proj.state,
        "country": proj.country,
        "zip_code": proj.zip_code,
        "latitude": proj.latitude,
        "longitude": proj.longitude,
        "construction_year": proj.construction_year,
        "renovation_year": proj.renovation_year,
        "total_floors": proj.total_floors,
        "total_units": proj.total_units,
        "building_type": proj.building_type,
        "has_elevator": proj.has_elevator,
        "has_parking": proj.has_parking,
        "has_basement": proj.has_basement,
        "has_garden": proj.has_garden,
        "energy_certificate_type": proj.energy_certificate_type,
        "energy_consumption": proj.energy_consumption,
        "energy_class": proj.energy_class,
        "heating_type": proj.heating_type,
        "primary_energy_consumption": proj.primary_energy_consumption,
        "heating_building_year": proj.heating_building_year,
        # New fields from Issue #51
        "backyard_development": proj.backyard_development,
        "sev_takeover_one_year": proj.sev_takeover_one_year,
        "renovations": proj.renovations,  # This will be JSON serialized automatically
        # Additional fields
        "description": proj.description,
        "amenities": proj.amenities,
        "micro_location_v2": proj.micro_location_v2,
        "status": proj.status,
        "provision_percentage": proj.provision_percentage,
        "min_price": proj.min_price,
        "max_price": proj.max_price,
        "min_rental_yield": proj.min_rental_yield,
        "max_rental_yield": proj.max_rental_yield,
        "min_initial_maintenance_expenses": proj.min_initial_maintenance_expenses,
        "max_initial_maintenance_expenses": proj.max_initial_maintenance_expenses,
        "city_id": proj.city_id,
        "investagon_id": proj.investagon_id,
        "investagon_data": proj.investagon_data,
        "tenant_id": proj.tenant_id,
        "created_by": proj.created_by,
        "updated_by": proj.updated_by,
        "created_at": proj.created_at,
        "updated_at": proj.updated_at,
        "thumbnail_url": thumbnail_url,
        "property_count": len(proj.properties) if hasattr(proj, 'properties') else 0
    }
    
    # Add city reference if loaded
    if hasattr(proj, 'city_ref') and proj.city_ref:
        response_data["city_ref"] = {
            "id": proj.city_ref.id,
            "name": proj.city_ref.name,
            "state": proj.city_ref.state,
            "country": proj.city_ref.country,
            "population": proj.city_ref.population,
            "population_growth": proj.city_ref.population_growth,
            "unemployment_rate": proj.city_ref.unemployment_rate,
            "average_income": proj.city_ref.average_income,
            "universities": proj.city_ref.universities,
            "major_employers": proj.city_ref.major_employers,
            "description": proj.city_ref.description,
            "highlights": proj.city_ref.highlights,
            "created_at": proj.city_ref.created_at,
            "updated_at": proj.city_ref.updated_at,
            "images": []
        }
    else:
        response_data["city_ref"] = None
    
    # Add properties if loaded
    if hasattr(proj, 'properties'):
        response_data["properties"] = proj.properties
    else:
        response_data["properties"] = []
    
    # Add images if loaded
    if hasattr(proj, 'images'):
        response_data["images"] = proj.images
    else:
        response_data["images"] = []
    
    return response_data


def map_renovation_to_dict(renovation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure renovation item matches the expected schema
    
    Args:
        renovation: Renovation dictionary from JSON field
        
    Returns:
        Validated renovation dictionary
    """
    return {
        "type": renovation.get("type"),
        "year": renovation.get("year"),
        "description": renovation.get("description")
    }