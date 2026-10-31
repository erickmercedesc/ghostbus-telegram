from fastapi import HTTPException, status

from telegram_engine.core.exceptions import (
    AccountNotFoundError,
    AccountUnavailableError,
    AuthenticationInProgressError,
    DuplicatePhoneError,
    ExpiredOtpError,
    InvalidOtpError,
    SessionUnavailableError,
    TelegramOperationError,
    TwoFactorRequiredError,
    UnauthorizedError,
)


def map_domain_error(exc: Exception) -> HTTPException:
    mapping: dict[type[Exception], tuple[int, str]] = {
        DuplicatePhoneError: (status.HTTP_409_CONFLICT, "Phone number already registered"),
        AccountNotFoundError: (status.HTTP_404_NOT_FOUND, "Account not found"),
        AccountUnavailableError: (status.HTTP_409_CONFLICT, "Account is not connected"),
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
