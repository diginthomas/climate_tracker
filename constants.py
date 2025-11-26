"""
Application-wide constants.
Centralizes magic numbers and status codes for better maintainability.
"""

# Event Status Codes
EVENT_STATUS_PENDING = 3
EVENT_STATUS_APPROVED = 1
EVENT_STATUS_DELETED = 2

# Category Status Codes
CATEGORY_STATUS_ACTIVE = 1
CATEGORY_STATUS_DEACTIVATED = 2

# Default pagination
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Image upload limits
MAX_IMAGES_PER_EVENT = 5

# Cache timeouts (in seconds)
CACHE_STALE_TIME_DEFAULT = 300  # 5 minutes
CACHE_STALE_TIME_CATEGORIES = 600  # 10 minutes (categories change rarely)
CACHE_STALE_TIME_EVENTS = 120  # 2 minutes (events change more frequently)


