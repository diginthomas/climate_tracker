from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import httpx
from auth.auth_utils import get_current_user

router = APIRouter(prefix="/geocoding", tags=["geocoding"])

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

@router.get("/")
async def geocode_location(
    location: str = Query(..., description="Location name to geocode"),
    current_user: str = Depends(get_current_user)
):
    """
    Geocode a location string to latitude and longitude coordinates.
    First tries Nominatim API (OpenStreetMap), falls back to local database.
    """
    location_lower = location.lower().strip()
    
    # Check local database first
    for city, coords in BC_CITIES_COORDS.items():
        if city in location_lower or location_lower in city:
            return {
                "location": location,
                "lat": coords["lat"],
                "lng": coords["lng"],
                "source": "local_database"
            }
    
    # Try Nominatim API (free, no key required)
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
                    "User-Agent": "ClimateTracker/1.0"  # Required by Nominatim
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        "location": location,
                        "lat": float(result["lat"]),
                        "lng": float(result["lon"]),
                        "source": "nominatim_api",
                        "display_name": result.get("display_name", "")
                    }
    except Exception as e:
        print(f"Geocoding API error: {e}")
    
    # If all else fails, return BC center coordinates
    return {
        "location": location,
        "lat": 53.7267,
        "lng": -127.6476,
        "source": "default_bc_center",
        "note": "Could not geocode location, using BC center"
    }
