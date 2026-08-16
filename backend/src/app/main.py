from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Assemble an isolated application that supports dependency overrides in tests."""
    application_settings = settings or get_settings()
    application = FastAPI(title="Codex Hackathon API", version="0.1.0")
    application.state.settings = application_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(application_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
