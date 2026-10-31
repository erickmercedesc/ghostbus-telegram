from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AccountStatus(StrEnum):
    PENDING_OTP = "pending_otp"
    PENDING_2FA = "pending_2fa"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(slots=True)
class SentMessage:
    outbound_id: str
    chat: str


@dataclass(slots=True)
class TelegramProfile:
    telegram_id: int
    username: str | None
    first_name: str | None


@dataclass(slots=True)
class Account:
    id: UUID
    phone_number: str
    status: AccountStatus
    created_at: datetime
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_connected_at: datetime | None = None
    session_ref: str | None = None


@dataclass(slots=True)
class ConnectionReport:
    account_id: UUID
    status: AccountStatus
    session_exists: bool
    connected: bool
    authorized: bool
    available: bool
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
