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