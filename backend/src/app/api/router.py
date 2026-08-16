from fastapi import APIRouter

from app.api import health, item_vision, locations, missions, parent_snapshot, road_vision

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(missions.router)
api_router.include_router(locations.router)
api_router.include_router(road_vision.router)
api_router.include_router(item_vision.router)
api_router.include_router(parent_snapshot.router)
