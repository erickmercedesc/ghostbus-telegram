from __future__ import annotations

from uuid import UUID

from telegram_engine.accounts.models import Account, AccountStatus, ConnectionReport, SentMessage, TelegramProfile
from telegram_engine.core.exceptions import InvalidOtpError, SessionUnavailableError, TwoFactorRequiredError


class FakeAccountStore:
    def __init__(self) -> None:
        self.by_id: dict[UUID, Account] = {}

    async def get_by_phone(self, phone_number: str) -> Account | None:
        for account in self.by_id.values():
            if account.phone_number == phone_number:
                return account
        return None

    async def get_by_id(self, account_id: UUID) -> Account | None:
        return self.by_id.get(account_id)

    async def add(self, account: Account) -> Account:
        self.by_id[account.id] = account
        return account

    async def update(self, account: Account) -> Account:
        self.by_id[account.id] = account
        return account

    async def list_all(self) -> list[Account]:
        return list(self.by_id.values())


class FakeSessionVault:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    async def save(self, account_id: UUID, session_payload: str) -> str:
        ref = f"{account_id}.session"
        self.files[ref] = session_payload
        return ref

    async def load(self, session_ref: str) -> str | None:
        return self.files.get(session_ref)

    async def exists(self, session_ref: str) -> bool:
        return session_ref in self.files


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.otp_requested: set[UUID] = set()
        self.sessions: dict[UUID, str] = {}
        self.profiles: dict[UUID, TelegramProfile] = {}
        self.valid_otp = "12345"
        self.require_2fa = False
        self.fail_otp: Exception | None = None
        self.authorized: dict[UUID, bool] = {}
        self.connected: dict[UUID, bool] = {}
        self.restore_ok = True
        self.inspect_missing = False
        self.sent: list[tuple] = []

    async def request_otp(self, account_id: UUID, phone_number: str) -> None:
        self.otp_requested.add(account_id)

    async def verify_otp(
        self, account_id: UUID, phone_number: str, otp: str
    ) -> TelegramProfile | None:
        if self.fail_otp:
            raise self.fail_otp
        if otp != self.valid_otp:
            raise InvalidOtpError("Invalid OTP")
        if self.require_2fa:
            raise TwoFactorRequiredError("2FA required")
        profile = TelegramProfile(telegram_id=1, username="user", first_name="Ada")
        self.profiles[account_id] = profile
        self.sessions[account_id] = f"session-{account_id}"
        self.authorized[account_id] = True
        self.connected[account_id] = True
        self.otp_requested.discard(account_id)
        return profile

    async def verify_password(self, account_id: UUID, password: str) -> TelegramProfile:
        if password != "secret":
            raise SessionUnavailableError("Invalid password")
        profile = TelegramProfile(telegram_id=1, username="user", first_name="Ada")
        self.profiles[account_id] = profile
        self.sessions[account_id] = f"session-{account_id}"
        self.authorized[account_id] = True
        self.connected[account_id] = True
        return profile

    async def export_session(self, account_id: UUID) -> str:
        return self.sessions[account_id]

    async def restore(self, account_id: UUID, session_payload: str) -> bool:
        if not self.restore_ok:
            return False
        self.sessions[account_id] = session_payload
        self.authorized[account_id] = True
        self.connected[account_id] = True
        return True

    async def inspect(self, account_id: UUID) -> ConnectionReport:
        if self.inspect_missing:
            raise SessionUnavailableError("revoked")
        authorized = self.authorized.get(account_id, False)
        connected = self.connected.get(account_id, False)
        profile = self.profiles.get(account_id)
        status = AccountStatus.CONNECTED if authorized else AccountStatus.ERROR
        return ConnectionReport(
            account_id=account_id,
            status=status,
            session_exists=account_id in self.sessions,
            connected=connected,
            authorized=authorized,
            available=authorized and connected,
            telegram_id=profile.telegram_id if profile else None,
            username=profile.username if profile else None,
            first_name=profile.first_name if profile else None,
        )

    async def send_message(self, account_id: UUID, chat: str, text: str) -> SentMessage:
        self.sent.append((account_id, chat, text))
        return SentMessage(outbound_id=str(len(self.sent)), chat=chat)

    async def has_pending_auth(self, account_id: UUID) -> bool:
        return account_id in self.otp_requested
