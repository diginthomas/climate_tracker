"""
Rate limiting middleware for FastAPI using slowapi.
Protects against brute force attacks and API abuse.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the shared limiter (will be attached to app.state in main.py)
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations for different endpoints
RATE_LIMIT_LOGIN = "5/minute"  # 5 login attempts per minute per IP
RATE_LIMIT_REGISTER = "3/hour"  # 3 registrations per hour per IP
RATE_LIMIT_CONTACT = "10/hour"  # 10 contact submissions per hour per IP
RATE_LIMIT_PASSWORD_RESET = "5/hour"  # 5 password reset requests per hour per IP
RATE_LIMIT_GENERAL = "100/minute"  # General API rate limit

