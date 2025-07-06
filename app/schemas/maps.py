# ================================
# MAPS SCHEMAS (schemas/maps.py)
# ================================

from enum import Enum
from pydantic import BaseModel

class MapType(str, Enum):
    """Supported Google Maps types"""
    ROADMAP = "roadmap"
    SATELLITE = "satellite"
    HYBRID = "hybrid"
    TERRAIN = "terrain"
    STREETVIEW = "streetview"

class MapUrlResponse(BaseModel):
    """Response containing the secure map URL"""
    url: str