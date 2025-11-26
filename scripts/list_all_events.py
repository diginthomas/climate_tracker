"""
Script to list all events with region, location, and coordinates from the database.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import events_collection
from bson import ObjectId

# Region ID to name mapping
REGION_ID_TO_NAME = {
    "100": "Northern BC",
    "101": "Thompson-Okanagan",
    "102": "Lower Mainland",
    "103": "Vancouver Island & Coast",
    "104": "Kootenay/Columbia"
}

async def list_all_events():
    """List all events with region, location, and coordinates."""
    print("=" * 100)
    print("ALL EVENTS IN DATABASE - Region, Location, and Coordinates")
    print("=" * 100)
    
    # Get all events sorted by date
    events = await events_collection.find({}).sort("date", -1).to_list(length=None)
    total_events = len(events)
    
    print(f"\nTotal events in database: {total_events}\n")
    
    # Count by region
    region_counts = {}
    events_with_coords = 0
    events_without_coords = 0
    
    # Display all events
    for idx, event in enumerate(events, 1):
        event_id = str(event.get("_id"))
        title = event.get("title", "Untitled")
        region = event.get("region", "N/A")
        location = event.get("location", "N/A")
        lat = event.get("lat")
        lng = event.get("lng")
        status = event.get("status", "N/A")
        date = event.get("date", "N/A")
        
        # Map region ID to name if it's an ID
        region_display = REGION_ID_TO_NAME.get(region, region) if region != "N/A" else "N/A"
        
        # Format date
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = str(date)
        
        # Status mapping
        status_map = {1: "Approved", 2: "Deleted", 3: "Pending"}
        status_display = status_map.get(status, f"Status {status}")
        
        # Coordinates status
        has_coords = lat is not None and lng is not None
        if has_coords:
            events_with_coords += 1
            coords_display = f"✅ ({lat:.6f}, {lng:.6f})"
        else:
            events_without_coords += 1
            coords_display = "❌ Missing"
        
        # Count by region
        region_key = region_display if region_display != "N/A" else "No Region"
        if region_key not in region_counts:
            region_counts[region_key] = {"total": 0, "with_coords": 0, "without_coords": 0}
        region_counts[region_key]["total"] += 1
        if has_coords:
            region_counts[region_key]["with_coords"] += 1
        else:
            region_counts[region_key]["without_coords"] += 1
        
        # Display event
        print(f"\n{idx}. {title}")
        print(f"   ID: {event_id}")
        print(f"   Region: {region_display} {'(ID: ' + region + ')' if region in REGION_ID_TO_NAME else ''}")
        print(f"   Location: {location}")
        print(f"   Coordinates: {coords_display}")
        print(f"   Date: {date_str}")
        print(f"   Status: {status_display}")
        print("-" * 100)
    
    # Summary by region
    print("\n" + "=" * 100)
    print("SUMMARY BY REGION")
    print("=" * 100)
    print(f"\n{'Region':<35} {'Total':<10} {'With Coords':<15} {'Without Coords':<15}")
    print("-" * 100)
    
    # Sort regions by name
    sorted_regions = sorted(region_counts.keys())
    for region in sorted_regions:
        counts = region_counts[region]
        print(f"{region:<35} {counts['total']:<10} {counts['with_coords']:<15} {counts['without_coords']:<15}")
    
    print("-" * 100)
    print(f"{'TOTAL':<35} {total_events:<10} {events_with_coords:<15} {events_without_coords:<15}")
    
    # Events with coordinates detail
    print("\n" + "=" * 100)
    print("EVENTS WITH COORDINATES (Ready for Map Display)")
    print("=" * 100)
    
    events_with_coords_list = [
        e for e in events 
        if e.get("lat") is not None and e.get("lng") is not None
    ]
    
    if events_with_coords_list:
        for idx, event in enumerate(events_with_coords_list, 1):
            region = event.get("region", "N/A")
            region_display = REGION_ID_TO_NAME.get(region, region) if region != "N/A" else "N/A"
            
            print(f"\n{idx}. {event.get('title', 'Untitled')}")
            print(f"   Region: {region_display} {'(ID: ' + region + ')' if region in REGION_ID_TO_NAME else ''}")
            print(f"   Location: {event.get('location', 'N/A')}")
            print(f"   Coordinates: ({event.get('lat'):.6f}, {event.get('lng'):.6f})")
    else:
        print("\nNo events with coordinates found.")
    
    # Events without coordinates
    print("\n" + "=" * 100)
    print("EVENTS WITHOUT COORDINATES (Need Geocoding)")
    print("=" * 100)
    
    events_without_coords_list = [
        e for e in events 
        if e.get("lat") is None or e.get("lng") is None
    ]
    
    if events_without_coords_list:
        for idx, event in enumerate(events_without_coords_list, 1):
            region = event.get("region", "N/A")
            region_display = REGION_ID_TO_NAME.get(region, region) if region != "N/A" else "N/A"
            
            print(f"\n{idx}. {event.get('title', 'Untitled')}")
            print(f"   Region: {region_display} {'(ID: ' + region + ')' if region in REGION_ID_TO_NAME else ''}")
            print(f"   Location: {event.get('location', 'N/A')}")
            print(f"   Coordinates: Missing")
    else:
        print("\nAll events have coordinates!")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    asyncio.run(list_all_events())


