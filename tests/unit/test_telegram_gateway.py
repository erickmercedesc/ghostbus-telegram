from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from telethon.errors import PhoneCodeExpiredError, PhoneCodeInvalidError, SessionPasswordNeededError

from telegram_engine.core.exceptions import ExpiredOtpError, InvalidOtpError, TwoFactorRequiredError
from telegram_engine.telegram.gateway import TelethonGateway


class FakeClient:
    def __init__(self, *, authorized: bool = True, fail: Exception | None = None) -> None:
        self._connected = False
        self._authorized = authorized
        self.fail = fail
        self.session = SimpleNamespace(save=lambda: "string-session")
        self.phone = None
        self.code = None
        self.password = None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def send_code_request(self, phone: str) -> None:
        self.phone = phone

    async def sign_in(self, phone=None, code=None, password=None):
        if self.fail:
            raise self.fail
        self.phone = phone
        self.code = code
        self.password = password

    async def is_user_authorized(self) -> bool:
        return self._authorized

    async def get_me(self):
        return SimpleNamespace(id=99, username="ada", first_name="Ada")

    async def send_message(self, chat: str, text: str):
        return SimpleNamespace(id=7, chat_id=chat)


@pytest.mark.asyncio
async def test_request_and_verify_otp():
    client = FakeClient()
    gateway = TelethonGateway(1, "hash", client_factory=lambda payload: client)
    account_id = uuid4()

    await gateway.request_otp(account_id, "+1555")
    profile = await gateway.verify_otp(account_id, "+1555", "12345")

    assert profile.telegram_id == 99
    assert await gateway.export_session(account_id) == "string-session"
    report = await gateway.inspect(account_id)
    assert report.authorized is True
    assert report.connected is True
    sent = await gateway.send_message(account_id, "someone", "hola")
    assert sent.outbound_id == "7"
    assert sent.chat == "someone"


@pytest.mark.asyncio
async def test_invalid_and_expired_otp():
    invalid = FakeClient(fail=PhoneCodeInvalidError(request=Mock()))
    gateway = TelethonGateway(1, "hash", client_factory=lambda payload: invalid)
    account_id = uuid4()
    await gateway.request_otp(account_id, "+1555")
    with pytest.raises(InvalidOtpError):
        await gateway.verify_otp(account_id, "+1555", "0")

    expired = FakeClient(fail=PhoneCodeExpiredError(request=Mock()))
    gateway2 = TelethonGateway(1, "hash", client_factory=lambda payload: expired)
    account_id2 = uuid4()
    await gateway2.request_otp(account_id2, "+1555")
    with pytest.raises(ExpiredOtpError):
        await gateway2.verify_otp(account_id2, "+1555", "0")


@pytest.mark.asyncio
async def test_password_needed():
    client = FakeClient(fail=SessionPasswordNeededError(request=Mock()))
    gateway = TelethonGateway(1, "hash", client_factory=lambda payload: client)
    account_id = uuid4()
    await gateway.request_otp(account_id, "+1555")
    with pytest.raises(TwoFactorRequiredError):
        await gateway.verify_otp(account_id, "+1555", "12345")


@pytest.mark.asyncio
async def test_restore_rejects_unauthorized_session():
    client = FakeClient(authorized=False)
    gateway = TelethonGateway(1, "hash", client_factory=lambda payload: client)
    ok = await gateway.restore(uuid4(), "payload")
    assert ok is False
