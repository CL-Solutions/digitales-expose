from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Index, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class GoogleGeocodingCache(Base):
    __tablename__ = "google_geocoding_cache"

    id = Column(String, primary_key=True)
    address = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    formatted_address = Column(String, nullable=True)
    place_id = Column(String, nullable=True)
    raw_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class GooglePlacesCache(Base):
    __tablename__ = "google_places_cache"

    id = Column(String, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # shopping, transit, leisure
    radius = Column(Integer, nullable=False)
    places = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_places_location_category', 'latitude', 'longitude', 'category'),
    )


class GoogleDistanceCache(Base):
    __tablename__ = "google_distance_cache"

    id = Column(String, primary_key=True)
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    mode = Column(String, nullable=False)  # driving, walking, transit
    distance_meters = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    raw_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_distance_route', 'origin_lat', 'origin_lng', 'destination_lat', 'destination_lng', 'mode'),
    )