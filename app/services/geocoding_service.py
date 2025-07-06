"""
OpenStreetMap Geocoding Service
Provides address validation and geocoding using Nominatim API
"""

import httpx
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import quote
import time

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for geocoding addresses and retrieving location details using OpenStreetMap Nominatim"""
    
    # Nominatim API endpoint
    NOMINATIM_API_URL = "https://nominatim.openstreetmap.org"
    
    # User agent for API requests (required by Nominatim)
    USER_AGENT = "DigitalesExpose/1.0"
    
    # Rate limiting (1 request per second as per Nominatim policy)
    MIN_REQUEST_INTERVAL = 1.0
    
    def __init__(self):
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting to respect Nominatim's usage policy"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - time_since_last_request)
        
        self.last_request_time = time.time()
    
    def geocode_address(
        self,
        street: str,
        house_number: str,
        city: str,
        state: str,
        country: str = "Deutschland",
        zip_code: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Geocode an address and return location details including district
        
        Args:
            street: Street name
            house_number: House number
            city: City name
            state: State/province name
            country: Country name (default: Deutschland)
            zip_code: Postal code (optional)
            
        Returns:
            Dict containing location details or None if not found
        """
        try:
            # Enforce rate limiting
            self._rate_limit()
            
            # Build the query string
            query_parts = []
            
            # Add street and house number
            if street and house_number:
                query_parts.append(f"{street} {house_number}")
            elif street:
                query_parts.append(street)
                
            # Add postal code if provided
            if zip_code:
                query_parts.append(zip_code)
                
            # Add city
            if city:
                query_parts.append(city)
                
            # Add state
            if state:
                query_parts.append(state)
                
            # Add country
            if country:
                query_parts.append(country)
                
            query = ", ".join(query_parts)
            
            # Make the API request
            with httpx.Client() as client:
                response = client.get(
                    f"{self.NOMINATIM_API_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "addressdetails": 1,
                        "limit": 1,
                        "accept-language": "de"  # Get results in German
                    },
                    headers={
                        "User-Agent": self.USER_AGENT
                    },
                    timeout=10.0
                )
                
                response.raise_for_status()
                results = response.json()
                
                if not results:
                    logger.warning(f"No geocoding results found for: {query}")
                    return None
                
                # Take the first (best) result
                result = results[0]
                
                # Extract address details
                address = result.get("address", {})
                
                # Extract district (can be in various fields)
                district = (
                    address.get("suburb") or 
                    address.get("neighbourhood") or
                    address.get("quarter") or
                    address.get("district") or
                    address.get("borough") or
                    address.get("city_district")
                )
                
                # Build return data
                geocoded_data = {
                    "latitude": float(result.get("lat")),
                    "longitude": float(result.get("lon")),
                    "display_name": result.get("display_name"),
                    "district": district,
                    "city": address.get("city") or address.get("town") or address.get("village"),
                    "state": address.get("state"),
                    "country": address.get("country"),
                    "postcode": address.get("postcode"),
                    "house_number": address.get("house_number"),
                    "road": address.get("road"),
                    "osm_id": result.get("osm_id"),
                    "osm_type": result.get("osm_type"),
                    "place_id": result.get("place_id"),
                    "boundingbox": result.get("boundingbox"),
                    "raw_address": address
                }
                
                logger.info(f"Successfully geocoded address: {query} -> District: {district}")
                return geocoded_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during geocoding: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {str(e)}")
            return None
    
    def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Reverse geocode coordinates to get address details
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dict containing location details or None if not found
        """
        try:
            # Enforce rate limiting
            self._rate_limit()
            
            # Make the API request
            with httpx.Client() as client:
                response = client.get(
                    f"{self.NOMINATIM_API_URL}/reverse",
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "json",
                        "addressdetails": 1,
                        "accept-language": "de"  # Get results in German
                    },
                    headers={
                        "User-Agent": self.USER_AGENT
                    },
                    timeout=10.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if not result:
                    logger.warning(f"No reverse geocoding results found for: {latitude}, {longitude}")
                    return None
                
                # Extract address details
                address = result.get("address", {})
                
                # Extract district
                district = (
                    address.get("suburb") or 
                    address.get("neighbourhood") or
                    address.get("quarter") or
                    address.get("district") or
                    address.get("borough") or
                    address.get("city_district")
                )
                
                # Build return data
                geocoded_data = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "display_name": result.get("display_name"),
                    "district": district,
                    "city": address.get("city") or address.get("town") or address.get("village"),
                    "state": address.get("state"),
                    "country": address.get("country"),
                    "postcode": address.get("postcode"),
                    "house_number": address.get("house_number"),
                    "road": address.get("road"),
                    "osm_id": result.get("osm_id"),
                    "osm_type": result.get("osm_type"),
                    "place_id": result.get("place_id"),
                    "boundingbox": result.get("boundingbox"),
                    "raw_address": address
                }
                
                logger.info(f"Successfully reverse geocoded: {latitude}, {longitude} -> District: {district}")
                return geocoded_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during reverse geocoding: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during reverse geocoding: {str(e)}")
            return None
    
    def validate_and_enrich_address(
        self,
        street: str,
        house_number: str,
        city: str,
        state: str,
        country: str = "Deutschland",
        zip_code: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an address and enrich it with additional data like district and coordinates
        
        Args:
            street: Street name
            house_number: House number
            city: City name
            state: State/province name
            country: Country name (default: Deutschland)
            zip_code: Postal code (optional)
            
        Returns:
            Tuple of (is_valid, enriched_data)
        """
        geocoded = self.geocode_address(
            street=street,
            house_number=house_number,
            city=city,
            state=state,
            country=country,
            zip_code=zip_code
        )
        
        if not geocoded:
            return False, None
        
        # Validate that the geocoded result matches the input
        # This is a basic validation - you might want to make it more sophisticated
        is_valid = True
        
        # Check if city matches (accounting for variations)
        geocoded_city = geocoded.get("city", "").lower()
        if city and geocoded_city and city.lower() not in geocoded_city:
            logger.warning(f"City mismatch: input='{city}', geocoded='{geocoded_city}'")
            # Don't fail validation for city mismatch as OSM might use different city boundaries
        
        return is_valid, geocoded


# Create a singleton instance
geocoding_service = GeocodingService()