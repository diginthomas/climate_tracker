"""
Cloudinary configuration and utilities for image uploads
"""
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def upload_image_to_cloudinary(image_data: bytes, folder: str = "climate_events", public_id: str = None) -> dict:
    """
    Upload an image to Cloudinary
    
    Args:
        image_data: Image file bytes
        folder: Cloudinary folder name
        public_id: Optional public ID for the image
    
    Returns:
        dict: Cloudinary upload result with 'secure_url' and other metadata
    
    Raises:
        Exception: If upload fails or Cloudinary is not configured
    """
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        raise Exception("Cloudinary credentials not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in .env file")
    
    try:
        result = cloudinary.uploader.upload(
            image_data,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
            invalidate=True
        )
        return result
    except Exception as e:
        raise Exception(f"Failed to upload image to Cloudinary: {str(e)}")

def is_cloudinary_url(url: str) -> bool:
    """
    Check if a URL is a Cloudinary URL
    
    Args:
        url: Image URL to check
    
    Returns:
        bool: True if URL is from Cloudinary
    """
    return url.startswith("http://res.cloudinary.com/") or url.startswith("https://res.cloudinary.com/")

def is_local_url(url: str) -> bool:
    """
    Check if a URL is a local upload URL
    
    Args:
        url: Image URL to check
    
    Returns:
        bool: True if URL is a local path
    """
    return url and (url.startswith("/uploads/") or url.startswith("uploads/"))

