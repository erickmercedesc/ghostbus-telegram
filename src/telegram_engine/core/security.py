import secrets

from fastapi import Header

from telegram_engine.core.config import Settings
from telegram_engine.core.exceptions import UnauthorizedError


def require_internal_api_key(
    settings: Settings,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.internal_api_key):
        raise UnauthorizedError("Invalid API key")
