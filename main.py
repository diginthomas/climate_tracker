from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from controllers import home_controller, auth_controller, user_controller, category_controller, \
    event_controller, user_mangement_controller, geocoding_controller, climate_controller,contact_controller
from fastapi.middleware.cors import CORSMiddleware
from database import create_indexes
from middleware.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded as SlowAPIRateLimitExceeded
from utils.logger import setup_logging, get_logger
from utils.exceptions import (
    APIException,
    api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from bson.errors import InvalidId
from utils.exceptions import invalid_id_handler
import os

# Setup logging
logger = setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database indexes on application startup"""
    logger.info("Starting application...")
    await create_indexes()
    logger.info("Application started successfully")
    yield
    logger.info("Shutting down application...")
    # Cleanup code can go here if needed


app = FastAPI(
    lifespan=lifespan,
    title="Climate Tracker API",
    description="API for climate event tracking and management",
    version="1.0.0"
)

# Add rate limiter to app state (will be used by all route limiters)
from middleware.rate_limiter import limiter
app.state.limiter = limiter

# Register exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(InvalidId, invalid_id_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Rate limit exception handler
@app.exception_handler(SlowAPIRateLimitExceeded)
async def rate_limit_handler(request: Request, exc: SlowAPIRateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.
    Returns a JSON response with 429 status code.
    """
    logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
    response = JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}. Please try again later.",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "status_code": 429
        }
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response

prefix = "/api/climate"

# Allow your React dev server origin
origins = [
    "http://localhost:5173",  # React Vite dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],    # GET, POST, PUT, DELETE
    allow_headers=["*"],    # Allow all headers
)

# Include routers with prefix
app.include_router(home_controller.router, prefix=prefix)
app.include_router(auth_controller.router, prefix=prefix)
app.include_router(user_controller.router, prefix=prefix)
app.include_router(category_controller.router, prefix=prefix)
app.include_router(event_controller.router, prefix=prefix)
app.include_router(geocoding_controller.router, prefix=prefix)
app.include_router(climate_controller.router, prefix=prefix)
app.include_router(contact_controller.router, prefix=prefix)
app.include_router(user_mangement_controller.router, prefix=prefix)

# Mount static files for uploaded images (only if directory exists - for backward compatibility with existing local images)
if os.path.exists("uploads") and os.path.isdir("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")