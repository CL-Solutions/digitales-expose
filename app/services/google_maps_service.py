"""
Google Maps Service
Handles all interactions with Google Maps APIs including geocoding, places search, and distance calculations
"""

import hashlib
import json
import logging
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import settings
from app.models.google_maps_cache import (
    GoogleGeocodingCache,
    GooglePlacesCache,
    GoogleDistanceCache
)
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Service for Google Maps API interactions with caching"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not configured")
        
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.places_v1_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.routes_v2_url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        self.cache_duration = timedelta(days=30)  # Cache for 30 days
        
        # Fixed radius for all categories
        self.default_radius = 2000  # 2km for all categories
        
        # Category mappings for Places API v1
        self.category_types = {
            "shopping": {
                "includedTypes": ["supermarket", "market", "shopping_mall", "department_store", 
                                 "discount_store", "food_store", "clothing_store"],
                "excludedTypes": []
            },
            "transit": {
                "includedTypes": ["airport", "ferry_terminal", "international_airport", 
                                 "light_rail_station", "park_and_ride", "subway_station", "train_station"],
                "excludedTypes": ["car_rental", "heliport"]
            },
            "leisure": {
                "includedTypes": ["adventure_sports_center", "amusement_center", "aquarium", "botanical_garden",
                                 "bowling_alley", "casino", "comedy_club", "community_center", "concert_hall",
                                 "convention_center", "cycling_park", "dance_hall", "dog_park", "ferris_wheel",
                                 "garden", "hiking_area", "historical_landmark", "internet_cafe", "karaoke",
                                 "marina", "movie_theater", "national_park", "night_club", "observation_deck",
                                 "off_roading_area", "opera_house", "park", "philharmonic_hall", "picnic_ground",
                                 "planetarium", "plaza", "roller_coaster", "skateboard_park", "state_park",
                                 "tourist_attraction", "video_arcade", "visitor_center", "water_park",
                                 "wildlife_park", "wildlife_refuge", "zoo"],
                "excludedTypes": ["sports_coaching"]
            }
        }
        
        # German translations for categories
        self.category_translations = {
            "shopping": "Einkaufsmöglichkeiten",
            "transit": "Infrastruktur",
            "leisure": "Freizeitmöglichkeiten"
        }
        
    def _generate_cache_id(self, *args) -> str:
        """Generate a unique cache ID from input parameters"""
        combined = "|".join(str(arg) for arg in args)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _is_cache_valid(self, created_at: datetime) -> bool:
        """Check if cache entry is still valid"""
        return datetime.utcnow() - created_at < self.cache_duration
    
    async def geocode_address(
        self,
        db: Session,
        address: str,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Geocode an address to get latitude/longitude
        Returns: {'lat': float, 'lng': float, 'formatted_address': str, 'place_id': str}
        """
        if not self.api_key:
            raise AppException(
                status_code=500,
                detail="Google Maps API key not configured"
            )
        
        # Check cache first
        cache_id = self._generate_cache_id("geocode", address)
        
        if not force_refresh:
            cached = db.query(GoogleGeocodingCache).filter(
                GoogleGeocodingCache.address == address
            ).first()
            
            if cached and self._is_cache_valid(cached.created_at):
                logger.info(f"Using cached geocoding for address: {address}")
                return {
                    "lat": cached.latitude,
                    "lng": cached.longitude,
                    "formatted_address": cached.formatted_address,
                    "place_id": cached.place_id
                }
        
        # Make API request
        url = f"{self.base_url}/geocode/json"
        params = {
            "address": address,
            "key": self.api_key,
            "language": "de"  # German language results
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data["status"] != "OK" or not data.get("results"):
                    logger.warning(f"Geocoding failed for address: {address}, status: {data['status']}")
                    return None
                
                result = data["results"][0]
                location = result["geometry"]["location"]
                
                # Store in cache
                cache_entry = GoogleGeocodingCache(
                    id=cache_id,
                    address=address,
                    latitude=location["lat"],
                    longitude=location["lng"],
                    formatted_address=result["formatted_address"],
                    place_id=result["place_id"],
                    raw_response=data
                )
                
                # Update or insert
                existing = db.query(GoogleGeocodingCache).filter(
                    GoogleGeocodingCache.id == cache_id
                ).first()
                
                if existing:
                    existing.latitude = location["lat"]
                    existing.longitude = location["lng"]
                    existing.formatted_address = result["formatted_address"]
                    existing.place_id = result["place_id"]
                    existing.raw_response = data
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(cache_entry)
                
                db.commit()
                
                # Extract address components for district
                components = result.get("address_components", [])
                
                # Helper function to extract component by type
                def get_component(types_to_find):
                    for component in components:
                        for type_to_find in types_to_find:
                            if type_to_find in component.get("types", []):
                                return component["long_name"]
                    return None
                
                # Extract district (can be in various fields)
                district = (
                    get_component(["sublocality_level_1", "sublocality"]) or
                    get_component(["neighborhood"]) or
                    get_component(["administrative_area_level_3"]) or
                    get_component(["administrative_area_level_4"])
                )
                
                return {
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "formatted_address": result["formatted_address"],
                    "place_id": result["place_id"],
                    "district": district
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during geocoding: {e}")
            raise AppException(
                status_code=500,
                detail="Failed to geocode address"
            )
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            raise AppException(
                status_code=500,
                detail="Geocoding service error"
            )
    
    async def find_nearby_places(
        self,
        db: Session,
        lat: float,
        lng: float,
        category: str,
        radius: int = None,  # Will use default_radius if not provided
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Find nearby places of a specific category using Places API v1
        Returns list of places with name, location, place_id, and primary type
        """
        if not self.api_key:
            raise AppException(
                status_code=500,
                detail="Google Maps API key not configured"
            )
        
        if category not in self.category_types:
            raise AppException(
                status_code=400,
                detail=f"Invalid category: {category}"
            )
        
        # Use default radius if not provided
        if radius is None:
            radius = self.default_radius
        
        # Check cache
        cache_id = self._generate_cache_id("places_v1", lat, lng, category, radius)
        
        if not force_refresh:
            cached = db.query(GooglePlacesCache).filter(
                and_(
                    GooglePlacesCache.latitude == lat,
                    GooglePlacesCache.longitude == lng,
                    GooglePlacesCache.category == category,
                    GooglePlacesCache.radius == radius
                )
            ).first()
            
            if cached and self._is_cache_valid(cached.created_at):
                logger.info(f"Using cached places for category: {category}")
                return cached.places[:4]  # Return top 4 places
        
        # Prepare request for Places API v1
        category_config = self.category_types[category]
        request_body = {
            "maxResultCount": 4,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lng
                    },
                    "radius": radius
                }
            },
            "includedTypes": category_config["includedTypes"],
            "excludedTypes": category_config["excludedTypes"],
            "rankPreference": "DISTANCE",
            "languageCode": "de"
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.primaryTypeDisplayName,places.location"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.places_v1_url,
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                places = []
                for place in data.get("places", []):
                    place_data = {
                        "name": place["displayName"]["text"],
                        "lat": place["location"]["latitude"],
                        "lng": place["location"]["longitude"],
                        "place_id": place["id"]
                    }
                    
                    # Add primary type display name if available
                    if "primaryTypeDisplayName" in place and "text" in place["primaryTypeDisplayName"]:
                        place_data["primary_type_display_name"] = place["primaryTypeDisplayName"]["text"]
                    
                    places.append(place_data)
                
                # Store in cache
                cache_entry = GooglePlacesCache(
                    id=cache_id,
                    latitude=lat,
                    longitude=lng,
                    category=category,
                    radius=radius,
                    places=places
                )
                
                # Update or insert
                existing = db.query(GooglePlacesCache).filter(
                    GooglePlacesCache.id == cache_id
                ).first()
                
                if existing:
                    existing.places = places
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(cache_entry)
                
                db.commit()
                
                return places
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching places: {e.response.text}")
            raise AppException(
                status_code=502,
                detail=f"Places API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error fetching places: {str(e)}")
            raise AppException(
                status_code=502,
                detail="Failed to fetch nearby places"
            )
    
    async def calculate_distances(
        self,
        db: Session,
        origin: Tuple[float, float],
        destinations: List[Tuple[float, float]],
        modes: List[str] = ["driving", "walking", "transit"],
        force_refresh: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        Calculate distances and durations from origin to multiple destinations using Routes API v2
        Makes one request per mode for all destinations at once
        Returns: {
            'driving': [{'distance_meters': int, 'duration_seconds': int}, ...],
            'walking': [...],
            'transit': [...]
        }
        """
        if not self.api_key:
            raise AppException(
                status_code=500,
                detail="Google Maps API key not configured"
            )
        
        results = {}
        
        # Map our mode names to Routes API travel modes
        mode_mapping = {
            "driving": "DRIVE",
            "walking": "WALK", 
            "transit": "TRANSIT"
        }
        
        for mode in modes:
            # For caching, we'll still check individually but make batch API calls
            if not force_refresh:
                # Check cache for all destinations
                all_cached = True
                cached_results = []
                
                for dest in destinations:
                    cache_id = self._generate_cache_id(
                        "distance_v2", 
                        f"{origin[0]:.15f}", f"{origin[1]:.15f}",
                        f"{dest[0]:.15f}", f"{dest[1]:.15f}",
                        mode
                    )
                    
                    cached = db.query(GoogleDistanceCache).filter(
                        and_(
                            GoogleDistanceCache.origin_lat == origin[0],
                            GoogleDistanceCache.origin_lng == origin[1],
                            GoogleDistanceCache.destination_lat == dest[0],
                            GoogleDistanceCache.destination_lng == dest[1],
                            GoogleDistanceCache.mode == mode
                        )
                    ).first()
                    
                    if cached and self._is_cache_valid(cached.created_at):
                        cached_results.append({
                            "distance_meters": cached.distance_meters,
                            "duration_seconds": cached.duration_seconds
                        })
                    else:
                        all_cached = False
                        break
                
                # If all destinations are cached, return cached results
                if all_cached:
                    results[mode] = cached_results
                    continue
            
            # Make a single API request for all destinations for this mode
            request_body = {
                "origins": [{
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": origin[0],
                                "longitude": origin[1]
                            }
                        }
                    }
                }],
                "destinations": [
                    {
                        "waypoint": {
                            "location": {
                                "latLng": {
                                    "latitude": dest[0],
                                    "longitude": dest[1]
                                }
                            }
                        }
                    } for dest in destinations
                ],
                "travelMode": mode_mapping.get(mode, "DRIVE"),
                "languageCode": "de"
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "distanceMeters,duration"
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.routes_v2_url,
                        json=request_body,
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    mode_results = []
                    
                    # Process results and cache them
                    for idx, route in enumerate(data):
                        if idx < len(destinations):  # Safety check
                            dest = destinations[idx]
                            
                            # Check if route has distance data
                            if "distanceMeters" in route:
                                distance_meters = route.get("distanceMeters", 0)
                                # Parse duration string (e.g., "139s" -> 139)
                                duration_str = route.get("duration", "0s")
                                duration_seconds = int(duration_str.rstrip("s"))
                                
                                # Store in cache
                                cache_id = self._generate_cache_id(
                                    "distance_v2",
                                    f"{origin[0]:.15f}", f"{origin[1]:.15f}",
                                    f"{dest[0]:.15f}", f"{dest[1]:.15f}",
                                    mode
                                )
                                
                                try:
                                    existing = db.query(GoogleDistanceCache).filter(
                                        GoogleDistanceCache.id == cache_id
                                    ).first()
                                    
                                    if existing:
                                        existing.distance_meters = distance_meters
                                        existing.duration_seconds = duration_seconds
                                        existing.raw_response = route
                                        existing.updated_at = datetime.utcnow()
                                    else:
                                        cache_entry = GoogleDistanceCache(
                                            id=cache_id,
                                            origin_lat=origin[0],
                                            origin_lng=origin[1],
                                            destination_lat=dest[0],
                                            destination_lng=dest[1],
                                            mode=mode,
                                            distance_meters=distance_meters,
                                            duration_seconds=duration_seconds,
                                            raw_response=route
                                        )
                                        db.add(cache_entry)
                                    
                                    db.flush()  # Flush each entry individually
                                    
                                except Exception as e:
                                    logger.warning(f"Could not cache distance result: {e}")
                                    db.rollback()  # Rollback this specific cache attempt
                                
                                mode_results.append({
                                    "distance_meters": distance_meters,
                                    "duration_seconds": duration_seconds
                                })
                            else:
                                # No route found
                                mode_results.append({
                                    "distance_meters": None,
                                    "duration_seconds": None
                                })
                    
                    # Commit all changes for this mode
                    try:
                        db.commit()
                    except Exception as e:
                        logger.warning(f"Could not commit cache updates: {e}")
                        db.rollback()
                    
                    results[mode] = mode_results
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Error calculating distances for mode {mode}: {e.response.text}")
                # Return None results for all destinations
                results[mode] = [
                    {"distance_meters": None, "duration_seconds": None}
                    for _ in destinations
                ]
            except Exception as e:
                logger.error(f"Error calculating distances for mode {mode}: {str(e)}")
                # Return None results for all destinations
                results[mode] = [
                    {"distance_meters": None, "duration_seconds": None}
                    for _ in destinations
                ]
        
        return results
    
    async def get_micro_location_data(
        self,
        db: Session,
        address: str,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Get complete micro location data for an address
        This is the main method that orchestrates all API calls
        """
        # Step 1: Geocode the address
        geocode_result = await self.geocode_address(db, address, force_refresh)
        if not geocode_result:
            return None
        
        lat = geocode_result["lat"]
        lng = geocode_result["lng"]
        
        # Step 2: Find nearby places for each category
        micro_location_data = {
            "location": {
                "lat": lat,
                "lng": lng,
                "formatted_address": geocode_result["formatted_address"]
            },
            "categories": {},
            "street_view": {
                "lat": lat,
                "lng": lng,
                "heading": 0
            }
        }
        
        for category in self.category_types.keys():
            places = await self.find_nearby_places(
                db, lat, lng, category, force_refresh=force_refresh
            )
            
            if places:
                # Step 3: Calculate distances for each place
                destinations = [(p["lat"], p["lng"]) for p in places]
                distances = await self.calculate_distances(
                    db, (lat, lng), destinations, force_refresh=force_refresh
                )
                
                # Combine place data with distance data
                enhanced_places = []
                for i, place in enumerate(places):
                    enhanced_place = place.copy()
                    enhanced_place["distances"] = {
                        "driving": distances["driving"][i],
                        "walking": distances["walking"][i],
                        "transit": distances["transit"][i]
                    }
                    enhanced_places.append(enhanced_place)
                
                micro_location_data["categories"][self.category_translations[category]] = enhanced_places
        
        # Step 4: Calculate optimal street view position
        # Find the nearest place (likely on a street) to use as reference
        all_nearby_places = []
        for places_list in micro_location_data["categories"].values():
            all_nearby_places.extend(places_list)
        
        if all_nearby_places:
            # Sort by walking distance to find nearest
            nearest_places = sorted(
                all_nearby_places,
                key=lambda p: p["distances"]["walking"]["distance_meters"] or float('inf')
            )[:3]  # Take top 3 nearest
            
            if nearest_places:
                # Calculate average direction to nearest places
                # This gives us a good indication of where the street is
                avg_lat = sum(p["lat"] for p in nearest_places) / len(nearest_places)
                avg_lng = sum(p["lng"] for p in nearest_places) / len(nearest_places)
                
                # Calculate heading from street position to building
                dlng = lng - avg_lng
                dlat = lat - avg_lat
                heading = math.degrees(math.atan2(dlng, dlat))
                if heading < 0:
                    heading += 360
                
                # Position street view slightly toward the nearest places
                # This puts us on the street looking at the building
                offset_factor = 0.0002  # Roughly 20-30 meters
                street_lat = lat + (avg_lat - lat) * offset_factor / abs(avg_lat - lat + 0.0001)
                street_lng = lng + (avg_lng - lng) * offset_factor / abs(avg_lng - lng + 0.0001)
                
                micro_location_data["street_view"] = {
                    "lat": street_lat,
                    "lng": street_lng,
                    "heading": int(heading)
                }
        
        return micro_location_data