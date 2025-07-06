# ================================
# MAPS API ROUTES (api/v1/maps.py)
# ================================

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
import urllib.parse

from app.config import settings
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.maps import MapUrlResponse, MapType

router = APIRouter()

@router.get("/map-url", response_model=MapUrlResponse)
async def get_map_url(
    latitude: float,
    longitude: float,
    map_type: MapType,
    zoom: Optional[int] = 15,
    width: Optional[int] = 600,
    height: Optional[int] = 400,
    heading: Optional[int] = 0,
    pitch: Optional[int] = 10,
    fov: Optional[int] = 90,
    current_user: User = Depends(get_current_active_user)
) -> MapUrlResponse:
    """
    Generate a secure Google Maps URL with the API key stored server-side.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        map_type: Type of map (roadmap, satellite, hybrid, terrain, streetview)
        zoom: Zoom level (1-20)
        width: Map width in pixels
        height: Map height in pixels
        heading: Street view heading (0-360)
        pitch: Street view pitch (-90 to 90)
        fov: Street view field of view (10-100)
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Google Maps API key not configured"
        )
    
    # Validate coordinates
    if not (-90 <= latitude <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude")
    if not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude")
    
    # Generate appropriate URL based on map type
    if map_type == MapType.STREETVIEW:
        # Google Street View embed URL
        url = (
            f"https://www.google.com/maps/embed/v1/streetview"
            f"?key={settings.GOOGLE_MAPS_API_KEY}"
            f"&location={latitude},{longitude}"
            f"&heading={heading}"
            f"&pitch={pitch}"
            f"&fov={fov}"
            f"&source=outdoor"
        )
    else:
        # Regular Google Maps embed URL
        map_type_value = map_type.value
        if map_type_value == "roadmap":
            # For embed API, we use "place" mode to show a marker
            url = (
                f"https://www.google.com/maps/embed/v1/place"
                f"?key={settings.GOOGLE_MAPS_API_KEY}"
                f"&q={latitude},{longitude}"
                f"&zoom={zoom}"
                f"&maptype={map_type_value}"
            )
        else:
            # For other map types, use view mode
            url = (
                f"https://www.google.com/maps/embed/v1/view"
                f"?key={settings.GOOGLE_MAPS_API_KEY}"
                f"&center={latitude},{longitude}"
                f"&zoom={zoom}"
                f"&maptype={map_type_value}"
            )
    
    return MapUrlResponse(url=url)