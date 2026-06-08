"""Engine/session factory. Lazy so importing the package never needs DATABASE_URL."""

import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    # DATABASE_URL must use a SQLAlchemy scheme, e.g. postgresql+psycopg://...
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Yield a session bound to the shared engine (FastAPI dependency / context use)."""
    with Session(get_engine()) as session:
        yield session
