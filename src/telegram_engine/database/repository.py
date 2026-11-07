from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from telegram_engine.accounts.models import Account, AccountStatus
from telegram_engine.database.models import AccountRow


def _to_domain(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        phone_number=row.phone_number,
        status=AccountStatus(row.status),
        created_at=row.created_at,
        telegram_id=row.telegram_id,
        username=row.username,
        first_name=row.first_name,
        last_connected_at=row.last_connected_at,
        session_ref=row.session_ref,
    )


def _apply(row: AccountRow, account: Account) -> None:
    row.phone_number = account.phone_number
    row.status = account.status.value
    row.telegram_id = account.telegram_id
    row.username = account.username
    row.first_name = account.first_name
    row.created_at = account.created_at
    row.last_connected_at = account.last_connected_at
    row.session_ref = account.session_ref


class SqlAccountStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def get_by_phone(self, phone_number: str) -> Account | None:
        async with self._factory() as session:
            row = await self._fetch_by_phone(session, phone_number)
            return _to_domain(row) if row else None

    async def get_by_id(self, account_id: UUID) -> Account | None:
        async with self._factory() as session:
            row = await session.get(AccountRow, account_id)
            return _to_domain(row) if row else None

    async def add(self, account: Account) -> Account:
        async with self._factory() as session:
            row = AccountRow(id=account.id)
            _apply(row, account)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def update(self, account: Account) -> Account:
        async with self._factory() as session:
            row = await session.get(AccountRow, account.id)
            if row is None:
                return await self.add(account)
            _apply(row, account)
            await session.commit()
            await session.refresh(row)
            return _to_domain(row)

    async def list_all(self) -> list[Account]:
        async with self._factory() as session:
            result = await session.execute(select(AccountRow))
            return [_to_domain(row) for row in result.scalars().all()]

    async def delete(self, account_id: UUID) -> None:
        async with self._factory() as session:
            row = await session.get(AccountRow, account_id)
            if row is not None:
                await session.delete(row)
                await session.commit()

    async def _fetch_by_phone(self, session: AsyncSession, phone_number: str) -> AccountRow | None:
        result = await session.execute(
            select(AccountRow).where(AccountRow.phone_number == phone_number)
        )
        return result.scalar_one_or_none()
