from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from telegram_engine.accounts.models import Account, AccountStatus
from telegram_engine.database.models import Base
from telegram_engine.database.repository import SqlAccountStore


@pytest.fixture
async def store(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield SqlAccountStore(factory)
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_store_roundtrip(store: SqlAccountStore):
    account = Account(
        id=uuid4(),
        phone_number="+15550001111",
        status=AccountStatus.PENDING_OTP,
        created_at=datetime.now(UTC),
    )
    saved = await store.add(account)
    fetched = await store.get_by_phone("+15550001111")
    assert fetched is not None
    assert fetched.id == saved.id

    saved.status = AccountStatus.CONNECTED
    saved.session_ref = "abc.session.enc"
    updated = await store.update(saved)
    listed = await store.list_all()
    assert listed[0].status == AccountStatus.CONNECTED
    assert updated.session_ref == "abc.session.enc"
