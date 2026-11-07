from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from telegram_engine.core.exceptions import UnsupportedDatabaseError
from telegram_engine.database.models import Base

_SQLITE = "sqlite"
_MYSQL = "mysql"


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend == _SQLITE:
        return database_url
    if backend == "mysql" and "+" not in url.drivername:
        return database_url.replace("mysql://", "mysql+aiomysql://", 1)
    if backend == _MYSQL:
        return database_url
    raise UnsupportedDatabaseError(
        "DATABASE_URL must be sqlite+aiosqlite://... or mysql+aiomysql://..."
    )


def _prepare_sqlite(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != _SQLITE:
        return
    database = url.database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(
    database_url: str,
) -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    database_url = normalize_database_url(database_url)
    url = make_url(database_url)
    kwargs: dict = {}
    if url.get_backend_name() == _SQLITE:
        _prepare_sqlite(database_url)
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 3600
    engine = create_async_engine(database_url, **kwargs)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def init_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
