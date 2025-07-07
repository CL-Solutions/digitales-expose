"""
Google Maps Service
Handles all interactions with Google Maps APIs including geocoding, places search, and distance calculations
"""

import hashlib
import json
import logging
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
        self.cache_duration = timedelta(days=30)  # Cache for 30 days
        
        # Category mappings for Places API
        self.category_types = {
            "shopping": ["supermarket", "grocery_or_supermarket", "shopping_mall", "department_store"],
            "transit": ["transit_station", "subway_station", "train_station", "bus_station"],
            "leisure": ["park", "gym", "movie_theater", "restaurant", "cafe", "museum"]
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
        radius: int = 1500,  # 1.5km default
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Find nearby places of a specific category
        Returns list of places with name, address, location, and place_id
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
        
        # Check cache
        cache_id = self._generate_cache_id("places", lat, lng, category, radius)
        
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
        
        # Make API requests for each place type in category
        all_places = []
        
        for place_type in self.category_types[category]:
            url = f"{self.base_url}/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "key": self.api_key,
                "language": "de"
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data["status"] == "OK":
                        for place in data.get("results", []):
                            all_places.append({
                                "name": place["name"],
                                "address": place.get("vicinity", ""),
                                "lat": place["geometry"]["location"]["lat"],
                                "lng": place["geometry"]["location"]["lng"],
                                "place_id": place["place_id"],
                                "types": place.get("types", []),
                                "rating": place.get("rating", 0),
                                "user_ratings_total": place.get("user_ratings_total", 0)
                            })
                            
            except Exception as e:
                logger.error(f"Error fetching places for type {place_type}: {e}")
                continue
        
        # Deduplicate places by place_id
        seen_place_ids = set()
        unique_places = []
        for place in all_places:
            if place["place_id"] not in seen_place_ids:
                seen_place_ids.add(place["place_id"])
                unique_places.append(place)
        
        # Sort by rating and number of reviews
        unique_places.sort(
            key=lambda x: ((x.get("rating") or 0) * (x.get("user_ratings_total") or 0)),
            reverse=True
        )
        
        # Take top 4 places
        top_places = unique_places[:4]
        
        # Store in cache
        cache_entry = GooglePlacesCache(
            id=cache_id,
            latitude=lat,
            longitude=lng,
            category=category,
            radius=radius,
            places=top_places
        )
        
        # Update or insert
        existing = db.query(GooglePlacesCache).filter(
            GooglePlacesCache.id == cache_id
        ).first()
        
        if existing:
            existing.places = top_places
            existing.updated_at = datetime.utcnow()
        else:
            db.add(cache_entry)
        
        db.commit()
        
        return top_places
    
    async def calculate_distances(
        self,
        db: Session,
        origin: Tuple[float, float],
        destinations: List[Tuple[float, float]],
        modes: List[str] = ["driving", "walking", "transit"],
        force_refresh: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        Calculate distances and durations from origin to multiple destinations
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
        
        for mode in modes:
            mode_results = []
            
            # Check cache for each destination
            for dest in destinations:
                cache_id = self._generate_cache_id(
                    "distance", 
                    origin[0], origin[1],
                    dest[0], dest[1],
                    mode
                )
                
                if not force_refresh:
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
                        mode_results.append({
                            "distance_meters": cached.distance_meters,
                            "duration_seconds": cached.duration_seconds
                        })
                        continue
                
                # Make API request for uncached routes
                url = f"{self.base_url}/distancematrix/json"
                params = {
                    "origins": f"{origin[0]},{origin[1]}",
                    "destinations": f"{dest[0]},{dest[1]}",
                    "mode": mode,
                    "key": self.api_key,
                    "language": "de",
                    "units": "metric"
                }
                
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                        
                        if data["status"] == "OK":
                            element = data["rows"][0]["elements"][0]
                            
                            if element["status"] == "OK":
                                distance_meters = element["distance"]["value"]
                                duration_seconds = element["duration"]["value"]
                                
                                # Store in cache
                                cache_entry = GoogleDistanceCache(
                                    id=cache_id,
                                    origin_lat=origin[0],
                                    origin_lng=origin[1],
                                    destination_lat=dest[0],
                                    destination_lng=dest[1],
                                    mode=mode,
                                    distance_meters=distance_meters,
                                    duration_seconds=duration_seconds,
                                    raw_response=data
                                )
                                
                                existing = db.query(GoogleDistanceCache).filter(
                                    GoogleDistanceCache.id == cache_id
                                ).first()
                                
                                if existing:
                                    existing.distance_meters = distance_meters
                                    existing.duration_seconds = duration_seconds
                                    existing.raw_response = data
                                    existing.updated_at = datetime.utcnow()
                                else:
                                    db.add(cache_entry)
                                
                                db.commit()
                                
                                mode_results.append({
                                    "distance_meters": distance_meters,
                                    "duration_seconds": duration_seconds
                                })
                            else:
                                mode_results.append({
                                    "distance_meters": None,
                                    "duration_seconds": None
                                })
                        
                except Exception as e:
                    logger.error(f"Error calculating distance for mode {mode}: {e}")
                    mode_results.append({
                        "distance_meters": None,
                        "duration_seconds": None
                    })
            
            results[mode] = mode_results
        
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
            "categories": {}
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
        
        return micro_location_data