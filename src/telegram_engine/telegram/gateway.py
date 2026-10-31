from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from telethon import TelegramClient
from telethon.errors import PhoneCodeExpiredError, PhoneCodeInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession

from telegram_engine.accounts.models import AccountStatus, ConnectionReport, SentMessage, TelegramProfile
from telegram_engine.core.exceptions import (
    ExpiredOtpError,
    InvalidOtpError,
    SessionUnavailableError,
    TelegramOperationError,
    TwoFactorRequiredError,
)

ClientFactory = Callable[[str | None], TelegramClient]


class TelethonGateway:
    def __init__(self, api_id: int, api_hash: str, client_factory: ClientFactory | None = None) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._clients: dict[UUID, TelegramClient] = {}
        self._factory = client_factory or self._default_factory

    def _default_factory(self, session_payload: str | None) -> TelegramClient:
        session = StringSession(session_payload) if session_payload else StringSession()
        return TelegramClient(session, self._api_id, self._api_hash)

    async def request_otp(self, account_id: UUID, phone_number: str) -> None:
        client = self._factory(None)
        try:
            await client.connect()
            await client.send_code_request(phone_number)
        except Exception as exc:
            await client.disconnect()
            raise TelegramOperationError(str(exc)) from exc
        self._clients[account_id] = client

    async def verify_otp(
        self, account_id: UUID, phone_number: str, otp: str
    ) -> TelegramProfile | None:
        client = self._require_client(account_id)
        try:
            await client.sign_in(phone=phone_number, code=otp)
        except SessionPasswordNeededError as exc:
            raise TwoFactorRequiredError("2FA required") from exc
        except PhoneCodeInvalidError as exc:
            raise InvalidOtpError("Invalid OTP") from exc
        except PhoneCodeExpiredError as exc:
            raise ExpiredOtpError("OTP expired") from exc
        except Exception as exc:
            raise TelegramOperationError(str(exc)) from exc
        return await self._profile(client)

    async def verify_password(self, account_id: UUID, password: str) -> TelegramProfile:
        client = self._require_client(account_id)
        try:
            await client.sign_in(password=password)
        except Exception as exc:
            raise TelegramOperationError(str(exc)) from exc
        return await self._profile(client)

    async def export_session(self, account_id: UUID) -> str:
        client = self._require_client(account_id)
        return client.session.save()

    async def restore(self, account_id: UUID, session_payload: str) -> bool:
        client = self._factory(session_payload)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return False
        except Exception:
            await client.disconnect()
            return False
        self._clients[account_id] = client
        return True

    async def inspect(self, account_id: UUID) -> ConnectionReport:
        client = self._clients.get(account_id)
        if client is None:
            raise SessionUnavailableError("No live session")
        connected = client.is_connected()
        if not connected:
            try:
                await client.connect()
                connected = client.is_connected()
            except Exception as exc:
                raise SessionUnavailableError(str(exc)) from exc
        try:
            authorized = await client.is_user_authorized()
        except Exception as exc:
            raise SessionUnavailableError(str(exc)) from exc
        profile = await self._profile(client) if authorized else None
        available = bool(connected and authorized)
        return ConnectionReport(
            account_id=account_id,
            status=AccountStatus.CONNECTED if available else AccountStatus.ERROR,
            session_exists=True,
            connected=bool(connected),
            authorized=authorized,
            available=available,
            telegram_id=profile.telegram_id if profile else None,
            username=profile.username if profile else None,
            first_name=profile.first_name if profile else None,
        )

    async def send_message(self, account_id: UUID, chat: str, text: str) -> SentMessage:
        client = self._require_client(account_id)
        try:
            message = await client.send_message(chat, text)
        except Exception as exc:
            raise TelegramOperationError(str(exc)) from exc
        return SentMessage(outbound_id=str(getattr(message, "id", "sent")), chat=chat)

    async def has_pending_auth(self, account_id: UUID) -> bool:
        return account_id in self._clients

    def _require_client(self, account_id: UUID) -> TelegramClient:
        client = self._clients.get(account_id)
        if client is None:
            raise SessionUnavailableError("Authentication process is not available")
        return client

    async def _profile(self, client: TelegramClient) -> TelegramProfile:
        me = await client.get_me()
        return TelegramProfile(
            telegram_id=me.id,
            username=me.username,
            first_name=me.first_name,
        )
