from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from telegram_engine.accounts.service import AccountService
from telegram_engine.core.config import Settings
from telegram_engine.main import build_for_tests
from tests.fakes import FakeAccountStore, FakeSessionVault, FakeTelegramGateway

API_KEY = "test-key"


def make_client() -> tuple[TestClient, FakeTelegramGateway, AccountService]:
    store = FakeAccountStore()
    telegram = FakeTelegramGateway()
    sessions = FakeSessionVault()
    service = AccountService(store, telegram, sessions)
    settings = Settings(
        internal_api_key=API_KEY,
        session_encryption_key=Fernet.generate_key().decode(),
        telegram_api_id=1,
        telegram_api_hash="hash",
    )
    app = build_for_tests(service, settings)
    return TestClient(app), telegram, service



def auth_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def test_login_and_list_requires_api_key():
    client, _, _ = make_client()
    response = client.post("/accounts/login", json={"phone_number": "+15550001111"})
    assert response.status_code == 401


def test_login_verify_and_list():
    client, _, _ = make_client()
    login = client.post(
        "/accounts/login",
        json={"phone_number": "+15550001111"},
        headers=auth_headers(),
    )
    assert login.status_code == 201
    body = login.json()
    assert body["status"] == "pending_otp"
    account_id = body["account_id"]

    verify = client.post(
        "/accounts/verify-otp",
        json={"account_id": account_id, "otp": "12345"},
        headers=auth_headers(),
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "connected"
    assert "session_ref" not in verify.json()

    listed = client.get("/accounts", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json()[0]["phone_number"] == "+15550001111"
    assert "session_ref" not in listed.json()[0]


def test_duplicate_phone_conflict():
    client, _, _ = make_client()
    client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    again = client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    assert again.status_code == 409


def test_invalid_otp():
    client, _, _ = make_client()
    login = client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    verify = client.post(
        "/accounts/verify-otp",
        json={"account_id": login.json()["account_id"], "otp": "00000"},
        headers=auth_headers(),
    )
    assert verify.status_code == 400


def test_2fa_flow():
    client, telegram, _ = make_client()
    telegram.require_2fa = True
    login = client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    verify = client.post(
        "/accounts/verify-otp",
        json={"account_id": login.json()["account_id"], "otp": "12345"},
        headers=auth_headers(),
    )
    assert verify.status_code == 401
    assert verify.json()["detail"]["status"] == "pending_2fa"

    done = client.post(
        "/accounts/verify-2fa",
        json={"account_id": login.json()["account_id"], "password": "secret"},
        headers=auth_headers(),
    )
    assert done.status_code == 200
    assert done.json()["status"] == "connected"


def test_check_account():
    client, _, _ = make_client()
    login = client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    account_id = login.json()["account_id"]
    client.post(
        "/accounts/verify-otp",
        json={"account_id": account_id, "otp": "12345"},
        headers=auth_headers(),
    )
    check = client.get(f"/accounts/{account_id}/check", headers=auth_headers())
    assert check.status_code == 200
    body = check.json()
    assert body["authorized"] is True
    assert body["connected"] is True
    assert body["available"] is True


def test_send_message():
    client, telegram, _ = make_client()
    login = client.post("/accounts/login", json={"phone_number": "+15550001111"}, headers=auth_headers())
    account_id = login.json()["account_id"]
    denied = client.post(
        "/send",
        json={"account": account_id, "to": "someone", "message": "hello"},
        headers=auth_headers(),
    )
    assert denied.status_code == 409
    client.post(
        "/accounts/verify-otp",
        json={"account_id": account_id, "otp": "12345"},
        headers=auth_headers(),
    )
    sent = client.post(
        "/send",
        json={"account": account_id, "to": "someone", "message": "hello"},
        headers=auth_headers(),
    )
    assert sent.status_code == 200
    assert sent.json()["to"] == "someone"
    assert telegram.sent[0][2] == "hello"
