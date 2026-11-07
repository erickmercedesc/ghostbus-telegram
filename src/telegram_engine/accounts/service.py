from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from telegram_engine.accounts.models import Account, AccountStatus, ConnectionReport, SentMessage
from telegram_engine.accounts.ports import AccountStore, SessionVault, TelegramGateway
from telegram_engine.core.exceptions import (
    AccountNotFoundError,
    AccountUnavailableError,
    AuthenticationInProgressError,
    DuplicatePhoneError,
    ExpiredOtpError,
    InvalidOtpError,
    SessionUnavailableError,
    TwoFactorRequiredError,
)


class AccountService:
    def __init__(
        self,
        store: AccountStore,
        telegram: TelegramGateway,
        sessions: SessionVault,
    ) -> None:
        self._store = store
        self._telegram = telegram
        self._sessions = sessions
        self._auth_locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, phone_number: str) -> asyncio.Lock:
        if phone_number not in self._auth_locks:
            self._auth_locks[phone_number] = asyncio.Lock()
        return self._auth_locks[phone_number]

    async def login(self, phone_number: str) -> Account:
        lock = self._lock_for(phone_number)
        if lock.locked():
            raise AuthenticationInProgressError("Authentication already in progress")

        async with lock:
            existing = await self._store.get_by_phone(phone_number)
            if existing is not None and existing.status != AccountStatus.ERROR:
                raise DuplicatePhoneError("Phone number already registered")

            if existing is None:
                account = Account(
                    id=uuid4(),
                    phone_number=phone_number,
                    status=AccountStatus.PENDING_OTP,
                    created_at=datetime.now(UTC),
                )
                account = await self._store.add(account)
            else:
                account = existing
                account.status = AccountStatus.PENDING_OTP
                account = await self._store.update(account)
            try:
                await self._telegram.request_otp(account.id, phone_number)
            except Exception:
                account.status = AccountStatus.ERROR
                await self._store.update(account)
                raise
            return account

    async def verify_otp(self, account_id: UUID, otp: str) -> Account:
        account = await self._require_account(account_id)
        lock = self._lock_for(account.phone_number)
        async with lock:
            try:
                profile = await self._telegram.verify_otp(account.id, account.phone_number, otp)
            except TwoFactorRequiredError:
                account.status = AccountStatus.PENDING_2FA
                await self._store.update(account)
                raise
            except (InvalidOtpError, ExpiredOtpError):
                raise
            except Exception:
                account.status = AccountStatus.ERROR
                await self._store.update(account)
                raise
            return await self._complete_sign_in(account, profile)

    async def verify_2fa(self, account_id: UUID, password: str) -> Account:
        account = await self._require_account(account_id)
        lock = self._lock_for(account.phone_number)
        async with lock:
            try:
                profile = await self._telegram.verify_password(account.id, password)
            except Exception:
                account.status = AccountStatus.ERROR
                await self._store.update(account)
                raise
            return await self._complete_sign_in(account, profile)

    async def check(self, account_id: UUID) -> ConnectionReport:
        account = await self._require_account(account_id)
        session_exists = bool(account.session_ref) and await self._sessions.exists(account.session_ref)
        try:
            report = await self._telegram.inspect(account.id)
        except SessionUnavailableError:
            account.status = AccountStatus.ERROR
            await self._store.update(account)
            return ConnectionReport(
                account_id=account.id,
                status=AccountStatus.ERROR,
                session_exists=session_exists,
                connected=False,
                authorized=False,
                available=False,
            )
        if report.authorized and report.connected:
            account.status = AccountStatus.CONNECTED
            account.last_connected_at = datetime.now(UTC)
            if report.telegram_id is not None:
                account.telegram_id = report.telegram_id
                account.username = report.username
                account.first_name = report.first_name
            await self._store.update(account)
            report.status = AccountStatus.CONNECTED
        elif account.status not in {AccountStatus.PENDING_OTP, AccountStatus.PENDING_2FA}:
            account.status = AccountStatus.ERROR
            await self._store.update(account)
            report.status = AccountStatus.ERROR
        else:
            report.status = account.status
        report.session_exists = session_exists
        return report

    async def list_accounts(self) -> list[Account]:
        return await self._store.list_all()

    async def delete_account(self, account_id: UUID) -> None:
        account = await self._require_account(account_id)
        lock = self._lock_for(account.phone_number)
        async with lock:
            await self._telegram.drop_client(account.id)
            if account.session_ref:
                await self._sessions.delete(account.session_ref)
            await self._store.delete(account.id)

    async def send_message(self, account_id: UUID, chat: str, text: str) -> SentMessage:
        account = await self._require_account(account_id)
        if account.status != AccountStatus.CONNECTED:
            raise AccountUnavailableError("Account is not connected")
        return await self._telegram.send_message(account.id, chat, text)

    async def restore_sessions(self) -> None:
        accounts = await self._store.list_all()
        for account in accounts:
            if not account.session_ref:
                continue
            payload = await self._sessions.load(account.session_ref)
            if payload is None:
                account.status = AccountStatus.ERROR
                await self._store.update(account)
                continue
            restored = await self._telegram.restore(account.id, payload)
            if restored:
                account.status = AccountStatus.CONNECTED
                account.last_connected_at = datetime.now(UTC)
            else:
                account.status = AccountStatus.ERROR
            await self._store.update(account)

    async def _complete_sign_in(self, account: Account, profile) -> Account:
        session_payload = await self._telegram.export_session(account.id)
        account.session_ref = await self._sessions.save(account.id, session_payload)
        if profile is None:
            account.status = AccountStatus.ERROR
            await self._store.update(account)
            return account
        account.status = AccountStatus.CONNECTED
        account.telegram_id = profile.telegram_id
        account.username = profile.username
        account.first_name = profile.first_name
        account.last_connected_at = datetime.now(UTC)
        return await self._store.update(account)

    async def _require_account(self, account_id: UUID) -> Account:
        account = await self._store.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        return account
