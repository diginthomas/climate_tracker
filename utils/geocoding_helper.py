"""
Geocoding helper utilities for location validation and coordinate adjustment.
Ensures coordinates fall within selected region boundaries.
"""
import httpx
from typing import Optional, Tuple
from utils.geospatial import GeoJSONRegionMapper
from config.region_mapping import REGIONAL_DISTRICT_TO_REGION, REGION_CENTERS, REGION_ID
import os
import logging

logger = logging.getLogger(__name__)

# BC Cities coordinates database (fallback when API is unavailable)
BC_CITIES_COORDS = {
    "vancouver": {"lat": 49.2827, "lng": -123.1207},
    "kamloops": {"lat": 50.6745, "lng": -120.3273},
    "kelowna": {"lat": 49.888, "lng": -119.496},
    "victoria": {"lat": 48.4284, "lng": -123.3656},
    "abbotsford": {"lat": 49.0504, "lng": -122.3045},
    "prince george": {"lat": 53.9166, "lng": -122.7494},
    "surrey": {"lat": 49.1044, "lng": -122.8011},
    "burnaby": {"lat": 49.2488, "lng": -122.9805},
    "richmond": {"lat": 49.1666, "lng": -123.1364},
    "langley": {"lat": 49.1031, "lng": -122.6582},
    "coquitlam": {"lat": 49.2837, "lng": -122.7932},
    "north vancouver": {"lat": 49.3200, "lng": -123.0723},
    "west vancouver": {"lat": 49.3667, "lng": -123.1667},
    "nanaimo": {"lat": 49.1664, "lng": -123.9401},
    "vernon": {"lat": 50.2670, "lng": -119.2722},
    "penticton": {"lat": 49.5001, "lng": -119.5858},
    "cranbrook": {"lat": 49.5167, "lng": -115.7667},
    "nelson": {"lat": 49.4996, "lng": -117.2856},
    "castlegar": {"lat": 49.3244, "lng": -117.6620},
    "trail": {"lat": 49.0956, "lng": -117.7056},
    "terrace": {"lat": 54.5163, "lng": -128.5995},
    "smithers": {"lat": 54.7817, "lng": -127.1718},
    "fort st john": {"lat": 56.2465, "lng": -120.8476},
    "prince rupert": {"lat": 54.3139, "lng": -130.3273},
}

# Initialize GeoJSON mapper (lazy loading)
_region_mapper = None

def get_region_mapper() -> Optional[GeoJSONRegionMapper]:
    """Get or initialize the GeoJSON region mapper."""
    global _region_mapper
    if _region_mapper is None:
        geojson_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "climate_tracker_frontend",
            "public",
            "ABMS_REGIONAL_DISTRICTS_SP.geojson"
        )
        try:
            _region_mapper = GeoJSONRegionMapper(geojson_path, REGIONAL_DISTRICT_TO_REGION)
        except Exception as e:
            logger.warning(f"Could not initialize GeoJSON mapper: {e}")
            _region_mapper = None
    return _region_mapper


async def geocode_location_with_region(
    location: str, 
    region: Optional[str] = None
) -> Tuple[Optional[float], Optional[float], bool]:
    """
    Geocode a location and validate/adjust coordinates to fall within the selected region.
    
    Args:
        location: Location string to geocode
        region: Selected region (highest priority - coordinates will be adjusted to this region)
        
    Returns:
        Tuple of (lat, lng, was_adjusted) where was_adjusted indicates if coordinates were adjusted
    """
    location_lower = location.lower().strip()
    geocoded_lat = None
    geocoded_lng = None
    
    # Check local database first
    for city, coords in BC_CITIES_COORDS.items():
        if city in location_lower or location_lower in city:
            geocoded_lat = coords["lat"]
            geocoded_lng = coords["lng"]
            break
    
    # Try Nominatim API if not found in local database
    if geocoded_lat is None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": f"{location}, British Columbia, Canada",
                        "format": "json",
                        "limit": 1
                    },
                    headers={
                        "User-Agent": "ClimateTracker/1.0"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        result = data[0]
                        geocoded_lat = float(result["lat"])
                        geocoded_lng = float(result["lon"])
        except Exception as e:
            logger.warning(f"Geocoding API error: {e}")
    
    # If all else fails, use BC center coordinates
    if geocoded_lat is None:
        geocoded_lat = 53.7267
        geocoded_lng = -127.6476
    
    # Validate and adjust coordinates based on selected region
    final_lat = geocoded_lat
    final_lng = geocoded_lng
    was_adjusted = False
    
    if region:
        # Map region ID to region name if needed (region might be ID like "100" or name like "Northern BC")
        region_name = None
        if region.isdigit() and region in REGION_ID.values():
            # Region is an ID - map it to name
            region_name = next((k for k, v in REGION_ID.items() if v == region), region)
        elif region in REGION_CENTERS:
            # Region is already a name that exists in REGION_CENTERS
            region_name = region
        else:
            # Try direct lookup
            region_name = region
        
        if region_name and region_name in REGION_CENTERS:
            region_mapper = get_region_mapper()
            
            if region_mapper and region_mapper.has_geojson_data():
                # Check if coordinates fall within the selected region
                detected_region = region_mapper.get_region_for_point(geocoded_lat, geocoded_lng)
                
                if detected_region == region_name:
                    # Coordinates are already in the correct region
                    pass
                else:
                    # Coordinates don't match selected region - adjust to region center
                    # (Region selection is highest priority per user requirement)
                    region_center = REGION_CENTERS[region_name]
                    final_lat = region_center["lat"]
                    final_lng = region_center["lng"]
                    was_adjusted = True
            else:
                # Can't validate - use region center as fallback
                region_center = REGION_CENTERS[region_name]
                final_lat = region_center["lat"]
                final_lng = region_center["lng"]
                was_adjusted = True
    
    return final_lat, final_lng, was_adjusted

