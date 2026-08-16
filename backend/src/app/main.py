from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import item_vision, locations, missions, parent_snapshot, road_vision
from app.api.dependencies import get_role_token_verifier
from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import create_neon_engine, create_session_factory
from app.integrations.openai.client import OpenAIVisionClient
from app.integrations.tmap.client import TmapClient
from app.repositories.missions import MissionRepository
from app.security.roles import MissionRoleTokenVerifier
from app.services.item_vision import ItemVisionService
from app.services.mission import MissionService
from app.services.navigation import LocationService
from app.services.parent_snapshot import ParentSnapshotService
from app.services.road_vision import RoadVisionService


@dataclass(frozen=True, slots=True)
class ApplicationComponents:
    """One shared production graph for an application's complete lifetime."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    repository: MissionRepository
    token_verifier: MissionRoleTokenVerifier
    tmap_client: Any
    vision_client: Any
    mission_service: MissionService
    location_service: LocationService
    road_vision_service: RoadVisionService
    item_vision_service: ItemVisionService
    parent_snapshot_service: ParentSnapshotService


def assemble_components(
    *,
    settings: Settings,
    engine: Engine,
    tmap_client: Any,
    vision_client: Any,
) -> ApplicationComponents:
    """Compose concrete services once; tests may supply SQLite and typed adapter doubles."""
    session_factory = create_session_factory(engine)
    repository = MissionRepository(session_factory)
    mission_service = MissionService(
        repository=repository,
        tmap_client=tmap_client,
        join_code_ttl_minutes=settings.mission_join_code_ttl_minutes,
    )
    return ApplicationComponents(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        repository=repository,
        token_verifier=MissionRoleTokenVerifier(repository),
        tmap_client=tmap_client,
        vision_client=vision_client,
        mission_service=mission_service,
        location_service=LocationService(repository),
        road_vision_service=RoadVisionService(repository=repository, vision_client=vision_client),
        item_vision_service=ItemVisionService(repository, vision_client, mission_service),
        parent_snapshot_service=ParentSnapshotService(repository),
    )


def _build_production_components(settings: Settings) -> ApplicationComponents:
    """Build runtime adapters lazily so imports and health checks never require secrets or a DB."""
    settings.require()
    database_url = settings.database_url
    openai_api_key = settings.openai_api_key
    if database_url is None or openai_api_key is None:
        raise AssertionError("validated required settings are missing")

    engine = create_neon_engine(database_url.get_secret_value())
    components = assemble_components(
        settings=settings,
        engine=engine,
        tmap_client=TmapClient.from_settings(settings),
        vision_client=OpenAIVisionClient(
            model=settings.openai_vision_model,
            api_key=openai_api_key.get_secret_value(),
        ),
    )
    # Lambda disables ASGI lifespan.  The controlled demo opts in explicitly, while production
    # schema ownership remains outside request handling and therefore has no hidden side effect.
    if settings.app_env == "demo":
        Base.metadata.create_all(engine)
    return components


def create_app(
    settings: Settings | None = None,
    *,
    components: ApplicationComponents | None = None,
) -> FastAPI:
    """Assemble an isolated application that supports dependency overrides in tests."""
    application_settings = settings or get_settings()
    application = FastAPI(title="Codex Hackathon API", version="0.1.0")
    application.state.settings = application_settings
    application.state.components = components
    application.state.components_lock = Lock()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(application_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(application)
    application.include_router(api_router)

    def resolve_components() -> ApplicationComponents:
        configured = application.state.components
        if configured is not None:
            return configured
        with application.state.components_lock:
            configured = application.state.components
            if configured is None:
                configured = _build_production_components(application_settings)
                application.state.components = configured
            return configured

    application.dependency_overrides[get_role_token_verifier] = lambda: (
        resolve_components().token_verifier
    )
    application.dependency_overrides[missions.get_mission_service] = lambda: (
        resolve_components().mission_service
    )
    application.dependency_overrides[locations.get_location_service] = lambda: (
        resolve_components().location_service
    )
    application.dependency_overrides[road_vision.get_road_vision_service] = lambda: (
        resolve_components().road_vision_service
    )
    application.dependency_overrides[item_vision.get_item_vision_service] = lambda: (
        resolve_components().item_vision_service
    )
    application.dependency_overrides[parent_snapshot.get_parent_snapshot_service] = lambda: (
        resolve_components().parent_snapshot_service
    )
    return application


app = create_app()
