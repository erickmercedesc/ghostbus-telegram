from collections.abc import Callable

from fastapi import Header, HTTPException, Request, status

from telegram_engine.accounts.service import AccountService
from telegram_engine.core.config import Settings
from telegram_engine.core.exceptions import UnauthorizedError
from telegram_engine.core.security import require_internal_api_key


def create_api_key_dependency(settings: Settings) -> Callable:
    def _check(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        try:
            require_internal_api_key(settings, x_api_key)
        except UnauthorizedError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from exc

    return _check


def get_account_service(request: Request) -> AccountService:
    return request.app.state.account_service
