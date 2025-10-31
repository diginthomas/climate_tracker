from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from controllers import home_controller, auth_controller, test_controller, user_controller, category_controller, \
    event_controller, user_mangement_controller
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

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
app.include_router(test_controller.router, prefix=prefix)
app.include_router(user_controller.router, prefix=prefix)
app.include_router(category_controller.router, prefix=prefix)
app.include_router(event_controller.router, prefix=prefix)

app.include_router(user_mangement_controller.router, prefix=prefix)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")