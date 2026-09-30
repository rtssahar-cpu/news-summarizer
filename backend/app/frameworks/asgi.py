from fastapi import FastAPI

from app.interface_adapters.controllers.health_controller import router as health_router

app = FastAPI()
app.include_router(health_router)
