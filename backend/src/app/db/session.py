from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def create_neon_engine(database_url: str) -> Engine:
    """Create the small, pre-pinged SQLAlchemy pool used by Neon at runtime."""
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must be a PostgreSQL URL")
    hostname = (url.host or "").lower()
    endpoint = hostname.split(".", 1)[0]
    if not hostname.endswith(".neon.tech") or not endpoint.endswith("-pooler"):
        raise ValueError("DATABASE_URL must use a Neon pooled endpoint")
    if url.query.get("sslmode") != "require":
        raise ValueError("DATABASE_URL must set sslmode=require")
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")

    return create_engine(
        url.render_as_string(hide_password=False),
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=10,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return short-lived sessions safe for request-scoped repository calls."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
