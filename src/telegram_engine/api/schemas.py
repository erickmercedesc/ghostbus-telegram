from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    phone_number: str = Field(min_length=5, max_length=32)


class LoginResponse(BaseModel):
    account_id: UUID
    status: str
    message: str


class VerifyOtpRequest(BaseModel):
    account_id: UUID
    otp: str = Field(min_length=1, max_length=16)


class Verify2faRequest(BaseModel):
    account_id: UUID
    password: str = Field(min_length=1)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_number: str
    telegram_id: int | None
    username: str | None
    first_name: str | None
    status: str
    created_at: datetime
    last_connected_at: datetime | None


class CheckResponse(BaseModel):
    id: UUID
    status: str
    session_exists: bool
    connected: bool
    authorized: bool
    available: bool
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
