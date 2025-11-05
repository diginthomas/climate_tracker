from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import httpx
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user
from database import events_collection

router = APIRouter(prefix="/climate", tags=["climate"])

# BC Regions data with major city coordinates for climate data
BC_REGIONS_DATA = {
    "Northern BC": {
        "cities": ["Prince George", "Fort St. John", "Terrace"],
        "coordinates": {"lat": 57.0, "lng": -125.0}
    },
    "Thompson-Okanagan": {
        "cities": ["Kamloops", "Kelowna", "Vernon"],
        "coordinates": {"lat": 50.5, "lng": -119.0}
    },
    "Lower Mainland": {
        "cities": ["Vancouver", "Surrey", "Burnaby"],
        "coordinates": {"lat": 49.2, "lng": -123.0}
    },
    "Vancouver Island & Coast": {
        "cities": ["Victoria", "Nanaimo", "Courtenay"],
        "coordinates": {"lat": 49.6, "lng": -125.0}
    },
    "Kootenay/Columbia": {
        "cities": ["Cranbrook", "Nelson", "Castlegar"],
        "coordinates": {"lat": 49.5, "lng": -116.0}
    }
}

@router.get("/region")
async def get_region_climate_data(
    region: str = Query(..., description="Region name in British Columbia"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch historical climate data for a specific BC region.
    Uses Open-Meteo API (free, no API key required).
    """
    if region not in BC_REGIONS_DATA:
        raise HTTPException(
            status_code=404, 
            detail=f"Region '{region}' not found. Available regions: {', '.join(BC_REGIONS_DATA.keys())}"
        )
    
    region_data = BC_REGIONS_DATA[region]
    coords = region_data["coordinates"]
    
    try:
        # Calculate date range (last 10 years)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 10)
        
        # Fetch historical climate data from Open-Meteo API
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Historical weather API
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lng"],
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "America/Vancouver"
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                daily_data = data.get("daily", {})
                
                # Process and aggregate data
                historical = []
                temps = daily_data.get("temperature_2m_max", [])
                temps_min = daily_data.get("temperature_2m_min", [])
                precip = daily_data.get("precipitation_sum", [])
                dates = daily_data.get("time", [])
                
                # Group by year for yearly statistics
                yearly_stats = {}
                for i in range(len(dates)):
                    if i < len(temps) and i < len(precip):
                        date_str = dates[i]
                        year = datetime.fromisoformat(date_str).year
                        
                        if year not in yearly_stats:
                            yearly_stats[year] = {
                                "year": year,
                                "temperatures": [],
                                "precipitations": []
                            }
                        
                        if temps[i] is not None:
                            yearly_stats[year]["temperatures"].append(temps[i])
                        if precip[i] is not None:
                            yearly_stats[year]["precipitations"].append(precip[i])
                
                # Calculate yearly averages
                for year, stats in yearly_stats.items():
                    avg_temp = sum(stats["temperatures"]) / len(stats["temperatures"]) if stats["temperatures"] else None
                    total_precip = sum(stats["precipitations"]) if stats["precipitations"] else None
                    
                    historical.append({
                        "year": year,
                        "temperature": round(avg_temp, 2) if avg_temp else None,
                        "precipitation": round(total_precip, 2) if total_precip else None
                    })
                
                # Calculate overall statistics
                all_temps = [h["temperature"] for h in historical if h["temperature"] is not None]
                all_precip = [h["precipitation"] for h in historical if h["precipitation"] is not None]
                
                avg_temperature = round(sum(all_temps) / len(all_temps), 2) if all_temps else None
                total_precipitation = round(sum(all_precip), 2) if all_precip else None
                
                # Generate insights
                insights = generate_climate_insights(historical, avg_temperature, total_precipitation)
                
                # Count events in this region
                event_count = await count_events_in_region(region)
                
                return {
                    "region": region,
                    "coordinates": coords,
                    "cities": region_data["cities"],
                    "historical": sorted(historical, key=lambda x: x["year"]),
                    "avg_temperature": avg_temperature,
                    "total_precipitation": total_precipitation,
                    "event_count": event_count,
                    "data_range": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d")
                    },
                    "insights": insights,
                    "source": "open_meteo_api"
                }
            else:
                # Return mock data if API fails
                mock_data = get_mock_climate_data(region, region_data)
                mock_data["event_count"] = await count_events_in_region(region)
                return mock_data
                
    except Exception as e:
        print(f"Climate API error: {e}")
        # Return mock data on error
        mock_data = get_mock_climate_data(region, region_data)
        mock_data["event_count"] = await count_events_in_region(region)
        return mock_data


async def count_events_in_region(region: str) -> int:
    """Count climate events in a specific region"""
    try:
        # Search for events that might be in this region
        # Check if location contains any city from the region
        region_cities = BC_REGIONS_DATA[region]["cities"]
        query = {
            "$or": [
                {"location": {"$regex": city, "$options": "i"}}
                for city in region_cities
            ] + [{"location": {"$regex": region, "$options": "i"}}],
            "status": {"$ne": 2}  # Exclude deleted events
        }
        count = await events_collection.count_documents(query)
        return count
    except Exception as e:
        print(f"Error counting events: {e}")
        return 0


def get_mock_climate_data(region: str, region_data: dict):
    """Generate mock climate data when API is unavailable"""
    import random
    
    current_year = datetime.now().year
    historical = []
    
    for year in range(current_year - 10, current_year):
        historical.append({
            "year": year,
            "temperature": round(random.uniform(8, 15), 2),
            "precipitation": round(random.uniform(400, 800), 2)
        })
    
    return {
        "region": region,
        "coordinates": region_data["coordinates"],
        "cities": region_data["cities"],
        "historical": historical,
        "avg_temperature": round(sum(h["temperature"] for h in historical) / len(historical), 2),
        "total_precipitation": round(sum(h["precipitation"] for h in historical), 2),
        "event_count": 0,
        "data_range": {
            "start": f"{current_year - 10}-01-01",
            "end": f"{current_year - 1}-12-31"
        },
        "insights": [
            f"{region} shows typical temperate climate patterns.",
            "Temperature variations are consistent with regional averages.",
            "Precipitation levels align with historical norms for the area."
        ],
        "source": "mock_data",
        "note": "Using mock data - API may be unavailable"
    }


def generate_climate_insights(historical: list, avg_temp: float, total_precip: float) -> list:
    """Generate climate insights based on historical data"""
    insights = []
    
    if not historical:
        return ["Insufficient data for climate analysis."]
    
    # Temperature trend analysis
    if len(historical) >= 5:
        recent_temps = [h["temperature"] for h in historical[-5:] if h["temperature"]]
        older_temps = [h["temperature"] for h in historical[:5] if h["temperature"]]
        
        if recent_temps and older_temps:
            recent_avg = sum(recent_temps) / len(recent_temps)
            older_avg = sum(older_temps) / len(older_temps)
            
            if recent_avg > older_avg + 0.5:
                insights.append("Average temperatures have increased over the past decade.")
            elif recent_avg < older_avg - 0.5:
                insights.append("Average temperatures have decreased slightly over the past decade.")
            else:
                insights.append("Temperature trends remain relatively stable.")
    
    # Precipitation analysis
    if avg_temp:
        insights.append(f"Average annual temperature: {avg_temp}°C")
    
    if total_precip:
        insights.append(f"Total precipitation over period: {total_precip:.0f} mm")
    
    return insights


@router.get("/city")
async def get_city_climate_data(
    city: str = Query(..., description="City name in British Columbia"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch climate data for a specific city in BC.
    """
    # Find which region the city belongs to
    region = None
    for reg_name, reg_data in BC_REGIONS_DATA.items():
        if city in [c.lower() for c in reg_data["cities"]]:
            region = reg_name
            break
    
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found in BC regions database."
        )
    
    # Use the region endpoint logic but filter for city
    return await get_region_climate_data(region=region, current_user=current_user)
