"""
Script to backfill coordinates for events that are missing lat/lng.
Uses the fixed geocoding logic to add coordinates to existing events.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import events_collection
from bson import ObjectId
from utils.geocoding_helper import geocode_location_with_region
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Region ID to name mapping
REGION_ID_TO_NAME = {
    "100": "Northern BC",
    "101": "Thompson-Okanagan",
    "102": "Lower Mainland",
    "103": "Vancouver Island & Coast",
    "104": "Kootenay/Columbia"
}

async def backfill_coordinates():
    """Backfill coordinates for events missing lat/lng."""
    print("=" * 100)
    print("BACKFILLING EVENT COORDINATES")
    print("=" * 100)
    
    # Find all events missing coordinates
    query = {
        "$or": [
            {"lat": {"$exists": False}},
            {"lat": None},
            {"lng": {"$exists": False}},
            {"lng": None}
        ]
    }
    
    events_to_update = await events_collection.find(query).to_list(length=None)
    total_events = len(events_to_update)
    
    print(f"\nFound {total_events} events missing coordinates\n")
    
    if total_events == 0:
        print("✅ All events already have coordinates!")
        return
    
    # Statistics
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Process each event
    for idx, event in enumerate(events_to_update, 1):
        event_id = event.get("_id")
        title = event.get("title", "Untitled")[:50]
        location = event.get("location", "N/A")
        region = event.get("region", "N/A")
        
        # Map region ID to name for display
        region_display = REGION_ID_TO_NAME.get(region, region) if region != "N/A" else "N/A"
        
        print(f"\n[{idx}/{total_events}] Processing: {title}")
        print(f"   Location: {location}")
        print(f"   Region: {region_display} {'(ID: ' + region + ')' if region in REGION_ID_TO_NAME else ''}")
        
        # Skip if no location or region
        if not location or location == "N/A":
            print(f"   ⚠️  SKIPPED: Missing location")
            skipped_count += 1
            continue
        
        if not region or region == "N/A":
            print(f"   ⚠️  SKIPPED: Missing region")
            skipped_count += 1
            continue
        
        try:
            # Geocode the location
            lat, lng, was_adjusted = await geocode_location_with_region(location, region)
            
            if lat and lng:
                # Update the event in database
                update_result = await events_collection.update_one(
                    {"_id": event_id},
                    {"$set": {"lat": lat, "lng": lng}}
                )
                
                if update_result.modified_count > 0:
                    print(f"   ✅ SUCCESS: Added coordinates ({lat:.6f}, {lng:.6f})")
                    if was_adjusted:
                        print(f"      Note: Coordinates adjusted to match region")
                    success_count += 1
                else:
                    print(f"   ⚠️  WARNING: Coordinates calculated but update failed")
                    failed_count += 1
            else:
                print(f"   ❌ FAILED: Could not geocode location")
                failed_count += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            logger.error(f"Error geocoding event {event_id}: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 100)
    print("BACKFILL SUMMARY")
    print("=" * 100)
    print(f"\nTotal events processed: {total_events}")
    print(f"✅ Successfully added coordinates: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    
    if success_count > 0:
        print(f"\n🎉 Successfully added coordinates to {success_count} event(s)!")
    
    if failed_count > 0 or skipped_count > 0:
        print(f"\n⚠️  {failed_count + skipped_count} event(s) still need manual attention.")
    
    print("\n" + "=" * 100)
    print("\nNext steps:")
    print("- Check the map to see if events are displaying correctly")
    print("- Verify coordinates are in the correct regions")
    print("- If needed, manually adjust any events with incorrect coordinates")
    print("\n" + "=" * 100)

if __name__ == "__main__":
    try:
        asyncio.run(backfill_coordinates())
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        logger.exception("Fatal error in backfill script")

