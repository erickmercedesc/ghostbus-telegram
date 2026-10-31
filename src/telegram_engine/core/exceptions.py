class TelegramEngineError(Exception):
    """Base error for the accounts module."""


class DuplicatePhoneError(TelegramEngineError):
    """A phone number is already registered."""


class AccountNotFoundError(TelegramEngineError):
    """No account matches the given identifier."""


class AuthenticationInProgressError(TelegramEngineError):
    """Another authentication flow is already running for this account."""


class InvalidOtpError(TelegramEngineError):
    """The OTP is incorrect."""


class ExpiredOtpError(TelegramEngineError):
    """The OTP has expired."""


class TwoFactorRequiredError(TelegramEngineError):
    """Telegram requires the account password."""


class SessionUnavailableError(TelegramEngineError):
    """The stored session cannot be loaded or is no longer valid."""


class UnauthorizedError(TelegramEngineError):
    """The internal API key is missing or invalid."""


class TelegramOperationError(TelegramEngineError):
    """Telegram rejected or failed an operation."""


class AccountUnavailableError(TelegramEngineError):
    """The account exists but is not connected."""
