from fastapi import FastAPI
from controllers import home_controller, auth_controller, test_controller

app = FastAPI()

prefix = "/api/climate"

# Include routers with prefix
app.include_router(home_controller.router, prefix=prefix)
app.include_router(auth_controller.router, prefix=prefix)

app.include_router(test_controller.router, prefix=prefix)