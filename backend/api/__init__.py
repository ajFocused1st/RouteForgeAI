from fastapi import APIRouter

from backend.api.ai import router as ai_router
from backend.api.depots import router as depots_router
from backend.api.dispatch import router as dispatch_router
from backend.api.geocoding import router as geocoding_router
from backend.api.health import router as health_router
from backend.api.routes import router as routes_router
from backend.api.stops import router as stops_router
from backend.api.vehicles import router as vehicles_router
from backend.api.vision import router as vision_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(health_router)
api_router.include_router(depots_router)
api_router.include_router(dispatch_router)
api_router.include_router(geocoding_router)
api_router.include_router(routes_router)
api_router.include_router(stops_router)
api_router.include_router(vehicles_router)
api_router.include_router(vision_router)
