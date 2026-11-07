from uuid import uuid4

import pytest

from telegram_engine.accounts.models import AccountStatus
from telegram_engine.accounts.service import AccountService
from telegram_engine.core.exceptions import (
    AccountUnavailableError,
    DuplicatePhoneError,
    ExpiredOtpError,
    InvalidOtpError,
    TwoFactorRequiredError,
)
from tests.fakes import FakeAccountStore, FakeSessionVault, FakeTelegramGateway


def make_service() -> tuple[AccountService, FakeAccountStore, FakeTelegramGateway, FakeSessionVault]:
    store = FakeAccountStore()
    telegram = FakeTelegramGateway()
    sessions = FakeSessionVault()
    return AccountService(store, telegram, sessions), store, telegram, sessions


@pytest.mark.asyncio
async def test_login_registers_pending_otp_account():
    service, store, telegram, _ = make_service()

    account = await service.login("+15551234567")

    assert account.status == AccountStatus.PENDING_OTP
    assert account.phone_number == "+15551234567"
    assert account.id in telegram.otp_requested
    assert await store.get_by_id(account.id) is not None


@pytest.mark.asyncio
async def test_login_rejects_duplicate_phone():
    service, _, _, _ = make_service()
    await service.login("+15551234567")

    with pytest.raises(DuplicatePhoneError):
        await service.login("+15551234567")


@pytest.mark.asyncio
async def test_verify_otp_connects_and_persists_session():
    service, _, telegram, sessions = make_service()
    account = await service.login("+15551234567")

    connected = await service.verify_otp(account.id, "12345")

    assert connected.status == AccountStatus.CONNECTED
    assert connected.telegram_id == 1
    assert connected.session_ref is not None
    assert await sessions.exists(connected.session_ref)
    assert connected.id not in telegram.otp_requested


@pytest.mark.asyncio
async def test_verify_otp_rejects_invalid_code():
    service, _, _, _ = make_service()
    account = await service.login("+15551234567")

    with pytest.raises(InvalidOtpError):
        await service.verify_otp(account.id, "00000")

    stored = (await service.list_accounts())[0]
    assert stored.status == AccountStatus.PENDING_OTP


@pytest.mark.asyncio
async def test_verify_otp_rejects_expired_code():
    service, _, telegram, _ = make_service()
    telegram.fail_otp = ExpiredOtpError("expired")
    account = await service.login("+15551234567")

    with pytest.raises(ExpiredOtpError):
        await service.verify_otp(account.id, "12345")


@pytest.mark.asyncio
async def test_verify_otp_signals_2fa():
    service, _, telegram, _ = make_service()
    telegram.require_2fa = True
    account = await service.login("+15551234567")

    with pytest.raises(TwoFactorRequiredError):
        await service.verify_otp(account.id, "12345")

    stored = (await service.list_accounts())[0]
    assert stored.status == AccountStatus.PENDING_2FA


@pytest.mark.asyncio
async def test_verify_2fa_completes_login():
    service, _, telegram, sessions = make_service()
    telegram.require_2fa = True
    account = await service.login("+15551234567")
    with pytest.raises(TwoFactorRequiredError):
        await service.verify_otp(account.id, "12345")

    connected = await service.verify_2fa(account.id, "secret")

    assert connected.status == AccountStatus.CONNECTED
    assert await sessions.exists(connected.session_ref)


@pytest.mark.asyncio
async def test_check_reads_live_connection_not_only_stored_status():
    service, _, telegram, _ = make_service()
    account = await service.login("+15550001111")
    await service.verify_otp(account.id, "12345")
    telegram.connected[account.id] = False
    telegram.authorized[account.id] = False

    report = await service.check(account.id)

    assert report.connected is False
    assert report.authorized is False
    assert report.status == AccountStatus.ERROR


@pytest.mark.asyncio
async def test_list_accounts_omits_session_payload():
    service, _, _, sessions = make_service()
    account = await service.login("+15550002222")
    connected = await service.verify_otp(account.id, "12345")

    listed = await service.list_accounts()

    assert listed[0].id == connected.id
    assert listed[0].phone_number == connected.phone_number
    assert connected.session_ref in sessions.files
    assert not hasattr(listed[0], "otp")


@pytest.mark.asyncio
async def test_restore_sessions_reconnects_without_otp():
    service, store, telegram, sessions = make_service()
    account = await service.login("+15550003333")
    connected = await service.verify_otp(account.id, "12345")
    telegram.authorized.clear()
    telegram.connected.clear()

    restored_service = AccountService(store, telegram, sessions)
    await restored_service.restore_sessions()

    stored = await store.get_by_id(connected.id)
    assert stored is not None
    assert stored.status == AccountStatus.CONNECTED
    assert telegram.authorized[connected.id] is True


@pytest.mark.asyncio
async def test_restore_marks_error_when_session_revoked():
    service, store, telegram, sessions = make_service()
    account = await service.login("+15550004444")
    await service.verify_otp(account.id, "12345")
    telegram.restore_ok = False

    await AccountService(store, telegram, sessions).restore_sessions()

    stored = (await store.list_all())[0]
    assert stored.status == AccountStatus.ERROR


@pytest.mark.asyncio
async def test_send_message_uses_connected_account():
    service, _, telegram, _ = make_service()
    account = await service.login("+15550005555")
    with pytest.raises(AccountUnavailableError):
        await service.send_message(account.id, "someone", "hello")
    connected = await service.verify_otp(account.id, "12345")
    sent = await service.send_message(connected.id, "someone", "hello")
    assert sent.chat == "someone"
    assert telegram.sent == [(connected.id, "someone", "hello")]


@pytest.mark.asyncio
async def test_delete_account_removes_session_and_record():
    service, store, telegram, sessions = make_service()
    account = await service.login("+15550006666")
    connected = await service.verify_otp(account.id, "12345")
    assert connected.session_ref is not None
    assert await sessions.exists(connected.session_ref)

    await service.delete_account(connected.id)

    assert await store.get_by_id(connected.id) is None
    assert await sessions.exists(connected.session_ref) is False
    assert connected.id not in telegram.sessions
