from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from telegram_engine.database.models import Base


def _prepare_sqlite(database_url: str) -> None:
    url = make_url(database_url)
    if not url.get_backend_name().startswith("sqlite"):
        return
    database = url.database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(
    database_url: str,
) -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    _prepare_sqlite(database_url)
    engine = create_async_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def init_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
