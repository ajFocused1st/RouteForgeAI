from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings
from backend.database.base import Base


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_database_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        connect_args=_connect_args(database_url),
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_database_engine(database_url)


@lru_cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(get_engine(database_url))


def initialize_database(database_url: str) -> None:
    import backend.models  # noqa: F401

    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    with session_factory() as session:
        yield session
