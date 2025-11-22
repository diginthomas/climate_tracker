# database.py
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["climate_db"]

#tables
users_collection = db["users"]
profiles_collection = db["user_profiles"]
categories_collection = db["categories"]
events_collection = db["events"]
contacts_collection = db["contacts"]


async def create_indexes():
    """
    Create database indexes for optimal query performance.
    This should be called once at application startup.
    """
    try:
        # Users collection indexes
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("role")
        await users_collection.create_index("created_at")
        
        # Events collection indexes
        await events_collection.create_index("category_id")
        await events_collection.create_index("status")
        await events_collection.create_index("region")
        await events_collection.create_index("year")
        await events_collection.create_index("is_featured")
        await events_collection.create_index("uploaded_at")
        await events_collection.create_index("date")
        # Compound index for common query patterns
        await events_collection.create_index([("status", 1), ("is_featured", -1)])
        await events_collection.create_index([("region", 1), ("year", -1)])
        await events_collection.create_index([("category_id", 1), ("status", 1)])
        
        # Categories collection indexes
        await categories_collection.create_index("title", unique=True)
        await categories_collection.create_index("status")
        
        # Contacts collection indexes
        await contacts_collection.create_index("status")
        await contacts_collection.create_index("is_deleted")
        await contacts_collection.create_index("created_at")
        await contacts_collection.create_index([("is_deleted", 1), ("status", 1)])
        
        # User profiles collection indexes
        await profiles_collection.create_index("user_id", unique=True)
        
        print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Warning: Error creating indexes: {e}")
        # Don't raise - allow app to continue if indexes already exist