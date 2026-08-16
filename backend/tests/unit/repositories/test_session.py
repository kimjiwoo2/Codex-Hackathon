from unittest.mock import Mock

import pytest
from sqlalchemy import Engine

from app.db import session as session_module


def test_neon_engine_uses_psycopg_pre_ping_and_small_pool(monkeypatch) -> None:
    engine = Mock(spec=Engine)
    create_engine = Mock(return_value=engine)
    monkeypatch.setattr(session_module, "create_engine", create_engine)

    result = session_module.create_neon_engine(
        "postgresql://user:password@example-pooler.neon.tech/app?sslmode=require"
    )

    assert result is engine
    create_engine.assert_called_once_with(
        "postgresql+psycopg://user:password@example-pooler.neon.tech/app?sslmode=require",
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=10,
    )


def test_neon_engine_rejects_non_postgresql_urls() -> None:
    try:
        session_module.create_neon_engine("sqlite+pysqlite:///:memory:")
    except ValueError as error:
        assert "PostgreSQL" in str(error)
    else:
        raise AssertionError("non-PostgreSQL URL must be rejected")


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@example.com/app?sslmode=require",
        "postgresql://user:password@ep-demo.ap-southeast-1.aws.neon.tech/app?sslmode=require",
        "postgresql://user:password@ep-demo-pooler.ap-southeast-1.aws.neon.tech/app",
    ],
)
def test_neon_engine_rejects_non_pooled_or_non_ssl_urls(database_url: str) -> None:
    with pytest.raises(ValueError):
        session_module.create_neon_engine(database_url)
