"""Engine/session factory. Lazy so importing the package never needs DATABASE_URL."""

import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

_SQLALCHEMY_SCHEME = "postgresql+psycopg://"


def database_url() -> str:
    """DATABASE_URL in SQLAlchemy form (`postgresql+psycopg://`).

    Managed Postgres providers hand out `postgresql://` / `postgres://`; a bare
    `postgresql://` makes SQLAlchemy load psycopg2, which isn't installed.
    """
    url = os.environ["DATABASE_URL"]
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return _SQLALCHEMY_SCHEME + url[len(prefix) :]
    return url


def psycopg_dsn() -> str:
    """DATABASE_URL as a plain libpq DSN, for raw psycopg connections (LISTEN)."""
    url = database_url()
    return "postgresql://" + url[len(_SQLALCHEMY_SCHEME) :]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Yield a session bound to the shared engine (FastAPI dependency / context use)."""
    with Session(get_engine()) as session:
        yield session
