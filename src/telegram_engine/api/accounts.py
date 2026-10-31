from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from telegram_engine.api.deps import get_account_service

from telegram_engine.accounts.models import Account
from telegram_engine.accounts.service import AccountService
from telegram_engine.api.schemas import (
    AccountResponse,
    CheckResponse,
    LoginRequest,
    LoginResponse,
    Verify2faRequest,
    VerifyOtpRequest,
)
from telegram_engine.core.exceptions import (
    AccountNotFoundError,
    AuthenticationInProgressError,
    DuplicatePhoneError,
    ExpiredOtpError,
    InvalidOtpError,
    SessionUnavailableError,
    TelegramOperationError,
    TwoFactorRequiredError,
    UnauthorizedError,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _to_account_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        phone_number=account.phone_number,
        telegram_id=account.telegram_id,
        username=account.username,
        first_name=account.first_name,
        status=account.status.value,
        created_at=account.created_at,
        last_connected_at=account.last_connected_at,
    )


def _map_error(exc: Exception) -> HTTPException:
    mapping: dict[type[Exception], tuple[int, str]] = {
        DuplicatePhoneError: (status.HTTP_409_CONFLICT, "Phone number already registered"),
        AccountNotFoundError: (status.HTTP_404_NOT_FOUND, "Account not found"),
        AuthenticationInProgressError: (status.HTTP_409_CONFLICT, "Authentication already in progress"),
        InvalidOtpError: (status.HTTP_400_BAD_REQUEST, "Invalid OTP"),
        ExpiredOtpError: (status.HTTP_400_BAD_REQUEST, "OTP expired"),
        SessionUnavailableError: (status.HTTP_409_CONFLICT, str(exc)),
        TelegramOperationError: (status.HTTP_502_BAD_GATEWAY, "Telegram operation failed"),
        UnauthorizedError: (status.HTTP_401_UNAUTHORIZED, "Unauthorized"),
    }
    if isinstance(exc, TwoFactorRequiredError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "pending_2fa", "message": "Two-factor authentication required"},
        )
    for error_type, (code, message) in mapping.items():
        if isinstance(exc, error_type):
            return HTTPException(status_code=code, detail=message)
    return HTTPException(status_code=500, detail="Internal error")


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def login(payload: LoginRequest, service: AccountService = Depends(get_account_service)) -> LoginResponse:
    try:
        account = await service.login(payload.phone_number)
    except Exception as exc:
        raise _map_error(exc) from exc
    return LoginResponse(
        account_id=account.id,
        status=account.status.value,
        message="OTP requested",
    )


@router.post("/verify-otp", response_model=AccountResponse)
async def verify_otp(payload: VerifyOtpRequest, service: AccountService = Depends(get_account_service)) -> AccountResponse:
    try:
        account = await service.verify_otp(payload.account_id, payload.otp)
    except Exception as exc:
        raise _map_error(exc) from exc
    return _to_account_response(account)


@router.post("/verify-2fa", response_model=AccountResponse)
async def verify_2fa(payload: Verify2faRequest, service: AccountService = Depends(get_account_service)) -> AccountResponse:
    try:
        account = await service.verify_2fa(payload.account_id, payload.password)
    except Exception as exc:
        raise _map_error(exc) from exc
    return _to_account_response(account)


@router.get("/{account_id}/check", response_model=CheckResponse)
async def check_account(account_id: UUID, service: AccountService = Depends(get_account_service)) -> CheckResponse:
    try:
        report = await service.check(account_id)
    except Exception as exc:
        raise _map_error(exc) from exc
    return CheckResponse(
        id=report.account_id,
        status=report.status.value,
        session_exists=report.session_exists,
        connected=report.connected,
        authorized=report.authorized,
        available=report.available,
        telegram_id=report.telegram_id,
        username=report.username,
        first_name=report.first_name,
    )


@router.get("", response_model=list[AccountResponse])
async def list_accounts(service: AccountService = Depends(get_account_service)) -> list[AccountResponse]:
    accounts = await service.list_accounts()
    return [_to_account_response(account) for account in accounts]
