from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import httpx
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user
from database import events_collection
from config.region_mapping import (
    REGIONAL_DISTRICT_TO_REGION,
    REGION_CENTERS,
    REGION_CITIES, REGION_ID
)
from utils.geospatial import GeoJSONRegionMapper
import os

router = APIRouter(prefix="/climate", tags=["climate"])

# BC Regions data with major city coordinates for climate data
BC_REGIONS_DATA = {
    "Northern BC": {
        "cities": REGION_CITIES["Northern BC"],
        "coordinates": REGION_CENTERS["Northern BC"]
    },
    "Thompson-Okanagan": {
        "cities": REGION_CITIES["Thompson-Okanagan"],
        "coordinates": REGION_CENTERS["Thompson-Okanagan"]
    },
    "Lower Mainland": {
        "cities": REGION_CITIES["Lower Mainland"],
        "coordinates": REGION_CENTERS["Lower Mainland"]
    },
    "Vancouver Island & Coast": {
        "cities": REGION_CITIES["Vancouver Island & Coast"],
        "coordinates": REGION_CENTERS["Vancouver Island & Coast"]
    },
    "Kootenay/Columbia": {
        "cities": REGION_CITIES["Kootenay/Columbia"],
        "coordinates": REGION_CENTERS["Kootenay/Columbia"]
    }
}

# Initialize GeoJSON mapper
# Path to GeoJSON file (relative to project root or absolute)
GEOJSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "climate_tracker_frontend",
    "public",
    "ABMS_REGIONAL_DISTRICTS_SP.geojson"
)

# Try to initialize the mapper
try:
    region_mapper = GeoJSONRegionMapper(GEOJSON_PATH, REGIONAL_DISTRICT_TO_REGION)
except Exception as e:
    print(f"Warning: Could not initialize GeoJSON mapper: {e}")
    region_mapper = None

@router.get("/region")
async def get_region_climate_data(
    region: str = Query(..., description="Region name in British Columbia"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch historical climate data for a specific BC region.
    Uses Open-Meteo Historical Weather API with ERA5-Land model for climate change accuracy.
    Provides temperature, precipitation, and snowfall trends from 1940 to present.
    """
    if region not in BC_REGIONS_DATA:
        raise HTTPException(
            status_code=404, 
            detail=f"Region '{region}' not found. Available regions: {', '.join(BC_REGIONS_DATA.keys())}"
        )
    
    region_data = BC_REGIONS_DATA[region]
    coords = region_data["coordinates"]
    
    try:
        # Calculate date range (extend to show more historical data - up to 10 years or available)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 10)
        
        # Fetch historical climate data from Open-Meteo Historical Weather API
        # Using ERA5-Land model for best climate-change accuracy
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lng"],
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_mean,precipitation_sum,snowfall_sum",
                "models": "era5_land",  # Best for climate change analysis
                "timezone": "America/Vancouver"
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                daily_data = data.get("daily", {})
                
                # Process and aggregate data
                historical = []
                temps = daily_data.get("temperature_2m_mean", [])
                precip = daily_data.get("precipitation_sum", [])
                snowfall = daily_data.get("snowfall_sum", [])
                dates = daily_data.get("time", [])
                
                # Filter out invalid values (-9999.9 or similar)
                def is_valid_value(val):
                    if val is None:
                        return False
                    try:
                        val_float = float(val)
                        return -9999.0 < val_float < 9999.0
                    except (ValueError, TypeError):
                        return False
                
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
                                "precipitations": [],
                                "snowfalls": []
                            }
                        
                        if is_valid_value(temps[i]):
                            yearly_stats[year]["temperatures"].append(temps[i])
                        if is_valid_value(precip[i]):
                            yearly_stats[year]["precipitations"].append(precip[i])
                        if i < len(snowfall) and is_valid_value(snowfall[i]):
                            yearly_stats[year]["snowfalls"].append(snowfall[i])
                
                # Calculate yearly averages
                for year, stats in yearly_stats.items():
                    avg_temp = sum(stats["temperatures"]) / len(stats["temperatures"]) if stats["temperatures"] else None
                    total_precip = sum(stats["precipitations"]) if stats["precipitations"] else None
                    total_snowfall = sum(stats["snowfalls"]) if stats["snowfalls"] else None
                    
                    historical.append({
                        "year": year,
                        "temperature": round(avg_temp, 2) if avg_temp is not None else None,
                        "precipitation": round(total_precip, 2) if total_precip is not None else None,
                        "snowfall": round(total_snowfall, 2) if total_snowfall is not None else None
                    })
                
                # Calculate overall statistics
                all_temps = [h["temperature"] for h in historical if h["temperature"] is not None]
                all_precip = [h["precipitation"] for h in historical if h["precipitation"] is not None]
                all_snowfall = [h["snowfall"] for h in historical if h["snowfall"] is not None]
                
                avg_temperature = round(sum(all_temps) / len(all_temps), 2) if all_temps else None
                total_precipitation = round(sum(all_precip), 2) if all_precip else None
                avg_snowfall = round(sum(all_snowfall) / len(all_snowfall), 2) if all_snowfall else None
                
                # Generate insights
                insights = generate_climate_insights(historical, avg_temperature, total_precipitation, avg_snowfall)
                
                # Count events in this region
                event_count = await count_events_in_region(region)
                
                return {
                    "region": region,
                    "coordinates": coords,
                    "cities": region_data["cities"],
                    "historical": sorted(historical, key=lambda x: x["year"]),
                    "avg_temperature": avg_temperature,
                    "total_precipitation": total_precipitation,
                    "avg_snowfall": avg_snowfall,
                    "event_count": event_count,
                    "data_range": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d")
                    },
                    "insights": insights,
                    "source": "open_meteo_api",
                    "model": "era5_land"
                }
            else:
                # Return mock data if API fails
                print(f"Open-Meteo API error: {response.status_code}")
                mock_data = get_mock_climate_data(region, region_data)
                mock_data["event_count"] = await count_events_in_region(region)
                return mock_data
                
    except Exception as e:
        print(f"Climate API error: {e}")
        import traceback
        traceback.print_exc()
        # Return mock data on error
        mock_data = get_mock_climate_data(region, region_data)
        mock_data["event_count"] = await count_events_in_region(region)
        return mock_data


async def count_events_in_region(region: str) -> int:
    """Count climate events in a specific region using geographic coordinates"""
    try:
        # If GeoJSON mapper is available, use geographic matching
        if region_mapper and region_mapper.has_geojson_data():
            # Get all events with coordinates
            query = {
                "lat": {"$exists": True, "$ne": None},
                "lng": {"$exists": True, "$ne": None},
                "status": {"$ne": 2}  # Exclude deleted events
            }
            
            count = 0
            async for event in events_collection.find(query):
                lat = event.get("lat")
                lng = event.get("lng")
                
                if lat is not None and lng is not None:
                    event_region = region_mapper.get_region_for_point(lat, lng)
                    if event_region == region:
                        count += 1
            
            return count
        else:
            # Fallback to text-based matching if GeoJSON not available
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
        # Fallback to text matching on error
        try:
            region_cities = BC_REGIONS_DATA[region]["cities"]
            query = {
                "$or": [
                    {"location": {"$regex": city, "$options": "i"}}
                    for city in region_cities
                ] + [{"location": {"$regex": region, "$options": "i"}}],
                "status": {"$ne": 2}
            }
            return await events_collection.count_documents(query)
        except:
            return 0


def get_mock_climate_data(region: str, region_data: dict):
    """Generate mock climate data when Open-Meteo API is unavailable"""
    import random
    
    current_year = datetime.now().year
    historical = []
    
    # Generate realistic mock data based on region
    # Different regions have different climate characteristics
    region_climates = {
        "Northern BC": {"temp_range": (0, 12), "precip_range": (300, 600)},
        "Thompson-Okanagan": {"temp_range": (5, 15), "precip_range": (200, 400)},
        "Lower Mainland": {"temp_range": (8, 14), "precip_range": (800, 1200)},
        "Vancouver Island & Coast": {"temp_range": (7, 13), "precip_range": (600, 1000)},
        "Kootenay/Columbia": {"temp_range": (3, 12), "precip_range": (400, 700)},
    }
    
    climate_params = region_climates.get(region, {"temp_range": (5, 12), "precip_range": (400, 800)})
    
    for year in range(current_year - 10, current_year):
        historical.append({
            "year": year,
            "temperature": round(random.uniform(*climate_params["temp_range"]), 2),
            "precipitation": round(random.uniform(*climate_params["precip_range"]), 2)
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
            "Precipitation levels align with historical norms for the area.",
            "Note: Using fallback data - Open-Meteo API may be unavailable."
        ],
        "source": "fallback_data",
        "note": "Using fallback data - Open-Meteo API may be unavailable",
        "avg_snowfall": None
    }


def generate_climate_insights(historical: list, avg_temp: float, total_precip: float, avg_snowfall: Optional[float] = None) -> list:
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
    
    # Snowfall insights (important for BC)
    if avg_snowfall is not None:
        insights.append(f"Average annual snowfall: {avg_snowfall:.0f} mm")
    
    return insights


@router.get("/projections")
async def get_region_climate_projections(
    region: str = Query(..., description="Region name in British Columbia"),
    model: str = Query("CMCC_CM2_VHR4", description="Climate model (e.g., CMCC_CM2_VHR4, EC_Earth3P_HR)"),
    scenario: str = Query("ssp585", description="Emission scenario (ssp126=low, ssp585=high)"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch future climate projections for a specific BC region.
    Uses Open-Meteo Climate API with IPCC CMIP6 models.
    Shows projected changes in temperature and precipitation.
    """
    if region not in BC_REGIONS_DATA:
        raise HTTPException(
            status_code=404, 
            detail=f"Region '{region}' not found. Available regions: {', '.join(BC_REGIONS_DATA.keys())}"
        )
    
    region_data = BC_REGIONS_DATA[region]
    coords = region_data["coordinates"]
    
    try:
        # Future projections - Climate API works with specific date ranges
        # Try 2020-2040 first (shorter range to avoid "Invalid date" error)
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2040, 12, 31)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://climate-api.open-meteo.com/v1/climate"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lng"],
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "models": model,
                "scenario": scenario,
                "timezone": "America/Vancouver"
            }
            
            print(f"Fetching projections: {url} with params: {params}")
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "No error message"
                print(f"Climate API error response: {error_text}")
                # Try with a shorter date range if first attempt fails
                if "Invalid date" in error_text or response.status_code == 400:
                    print("Trying with shorter date range (2020-2030)...")
                    end_date = datetime(2030, 12, 31)
                    params["end_date"] = end_date.strftime("%Y-%m-%d")
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Climate API error: {response.text[:500] if response.text else 'Unknown error'}"
                        )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Climate API error: {error_text}"
                    )
            
            if response.status_code == 200:
                data = response.json()
                daily_data = data.get("daily", {})
                
                # Process projection data
                projections = []
                temps_max = daily_data.get("temperature_2m_max", [])
                temps_min = daily_data.get("temperature_2m_min", [])
                precip = daily_data.get("precipitation_sum", [])
                dates = daily_data.get("time", [])
                
                # Filter invalid values
                def is_valid_value(val):
                    if val is None:
                        return False
                    try:
                        val_float = float(val)
                        return -9999.0 < val_float < 9999.0
                    except (ValueError, TypeError):
                        return False
                
                # Group by year
                yearly_stats = {}
                for i in range(len(dates)):
                    if i < len(temps_max) and i < len(temps_min) and i < len(precip):
                        date_str = dates[i]
                        year = datetime.fromisoformat(date_str).year
                        
                        if year not in yearly_stats:
                            yearly_stats[year] = {
                                "year": year,
                                "temps_max": [],
                                "temps_min": [],
                                "precipitations": []
                            }
                        
                        if is_valid_value(temps_max[i]):
                            yearly_stats[year]["temps_max"].append(temps_max[i])
                        if is_valid_value(temps_min[i]):
                            yearly_stats[year]["temps_min"].append(temps_min[i])
                        if is_valid_value(precip[i]):
                            yearly_stats[year]["precipitations"].append(precip[i])
                
                # Calculate yearly averages
                for year, stats in yearly_stats.items():
                    avg_temp_max = sum(stats["temps_max"]) / len(stats["temps_max"]) if stats["temps_max"] else None
                    avg_temp_min = sum(stats["temps_min"]) / len(stats["temps_min"]) if stats["temps_min"] else None
                    avg_temp = (avg_temp_max + avg_temp_min) / 2 if (avg_temp_max and avg_temp_min) else None
                    total_precip = sum(stats["precipitations"]) if stats["precipitations"] else None
                    
                    # Count days above 30°C (heat days)
                    days_above_30 = sum(1 for t in stats["temps_max"] if t and t > 30.0)
                    
                    projections.append({
                        "year": year,
                        "temperature": round(avg_temp, 2) if avg_temp is not None else None,
                        "temperature_max": round(avg_temp_max, 2) if avg_temp_max is not None else None,
                        "temperature_min": round(avg_temp_min, 2) if avg_temp_min is not None else None,
                        "precipitation": round(total_precip, 2) if total_precip is not None else None,
                        "days_above_30c": days_above_30
                    })
                
                return {
                    "region": region,
                    "coordinates": coords,
                    "model": model,
                    "scenario": scenario,
                    "scenario_name": "High Emissions" if scenario == "ssp585" else "Low Emissions" if scenario == "ssp126" else scenario,
                    "projections": sorted(projections, key=lambda x: x["year"]),
                    "data_range": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d")
                    },
                    "source": "open_meteo_climate_api"
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Climate API error: {response.text}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Climate projections API error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching climate projections: {str(e)}"
        )


@router.get("/air-quality")
async def get_region_air_quality(
    region: str = Query(..., description="Region name in British Columbia"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch real-time air quality data for a specific BC region.
    Uses Open-Meteo Air Quality API to show current impacts of climate events.
    Particularly useful for wildfire smoke (pm2_5) and other pollutants.
    """
    if region not in BC_REGIONS_DATA:
        raise HTTPException(
            status_code=404, 
            detail=f"Region '{region}' not found. Available regions: {', '.join(BC_REGIONS_DATA.keys())}"
        )
    
    region_data = BC_REGIONS_DATA[region]
    coords = region_data["coordinates"]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lng"],
                "hourly": "pm2_5,pm10,carbon_monoxide",  # Removed carbon_dioxide_2m - not available in this format
                "timezone": "America/Vancouver",
                "forecast_days": 1  # Current and next 24 hours
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "No error message"
                print(f"Air Quality API error response: {error_text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Air Quality API error: {error_text}"
                )
            
            if response.status_code == 200:
                data = response.json()
                hourly_data = data.get("hourly", {})
                
                pm25 = hourly_data.get("pm2_5", [])
                pm10 = hourly_data.get("pm10", [])
                co = hourly_data.get("carbon_monoxide", [])
                # Note: carbon_dioxide_2m is not available in hourly format
                times = hourly_data.get("time", [])
                
                # Get current values (most recent)
                current = {}
                if times and len(times) > 0:
                    current_time = times[-1]
                    current = {
                        "time": current_time,
                        "pm2_5": pm25[-1] if pm25 and len(pm25) > 0 else None,
                        "pm10": pm10[-1] if pm10 and len(pm10) > 0 else None,
                        "carbon_monoxide": co[-1] if co and len(co) > 0 else None,
                        "carbon_dioxide": None  # Not available in hourly format
                    }
                    
                    # Calculate AQI (Air Quality Index) based on PM2.5
                    # Simplified AQI calculation
                    pm25_val = current.get("pm2_5")
                    if pm25_val is not None:
                        if pm25_val <= 12:
                            aqi = "Good"
                            aqi_value = 1
                        elif pm25_val <= 35:
                            aqi = "Moderate"
                            aqi_value = 2
                        elif pm25_val <= 55:
                            aqi = "Unhealthy for Sensitive Groups"
                            aqi_value = 3
                        elif pm25_val <= 150:
                            aqi = "Unhealthy"
                            aqi_value = 4
                        else:
                            aqi = "Very Unhealthy"
                            aqi_value = 5
                        current["aqi"] = aqi
                        current["aqi_value"] = aqi_value
                
                # Calculate averages for the last 24 hours
                if len(times) > 0:
                    recent_pm25 = [v for v in pm25[-24:] if v is not None]
                    recent_pm10 = [v for v in pm10[-24:] if v is not None]
                    recent_co = [v for v in co[-24:] if v is not None]
                    
                    averages = {
                        "pm2_5_24h_avg": round(sum(recent_pm25) / len(recent_pm25), 2) if recent_pm25 else None,
                        "pm10_24h_avg": round(sum(recent_pm10) / len(recent_pm10), 2) if recent_pm10 else None,
                        "co_24h_avg": round(sum(recent_co) / len(recent_co), 2) if recent_co else None
                    }
                else:
                    averages = {}
                
                return {
                    "region": region,
                    "coordinates": coords,
                    "current": current,
                    "averages_24h": averages,
                    "source": "open_meteo_air_quality_api",
                    "note": "PM2.5 is particularly important for wildfire smoke detection"
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Air Quality API error: {response.text}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Air Quality API error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching air quality data: {str(e)}"
        )


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


@router.get("/events")
async def get_events( region: str = Query(..., description="Region name in British Columbia"),
    current_user: str = Depends(get_current_user)):
    region_id = REGION_ID.get(region,"")
    if not region_id:
        raise HTTPException(
            status_code=404,
        )
    """
     Get number of events per category in a specific region.
     Output format: { "Wildfire": 3, "Flood": 1 }
     """
    try:
        pipeline = [
            # 1️ Filter events by region
            {"$match": {"region": region_id}},

            # 2️ Convert string category_id to ObjectId
            {
                "$addFields": {
                    "category_obj_id": {"$toObjectId": "$category_id"}
                }
            },

            # 3️ Join with categories collection
            {
                "$lookup": {
                    "from": "categories",  # replace with your MongoDB category collection name
                    "localField": "category_obj_id",
                    "foreignField": "_id",
                    "as": "category"
                }
            },

            # 4️ Flatten category array
            {"$unwind": "$category"},

            # 5️ Group by category title and count events
            {
                "$group": {
                    "_id": "$category.title",
                    "count": {"$sum": 1}
                }
            }
        ]

        # Run aggregation asynchronously
        cursor = events_collection.aggregate(pipeline)
        data = [doc async for doc in cursor]

        # Convert to { "CategoryName": count } dictionary
        result = {item["_id"]: item["count"] for item in data}

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))