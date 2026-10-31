from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from telegram_engine.accounts.service import AccountService
from telegram_engine.api.accounts import router as accounts_router
from telegram_engine.api.deps import create_api_key_dependency
from telegram_engine.core.config import Settings, get_settings
from telegram_engine.database.engine import create_session_factory, init_schema
from telegram_engine.database.repository import SqlAccountStore
from telegram_engine.sessions.encrypted_store import EncryptedSessionStore
from telegram_engine.telegram.gateway import TelethonGateway


def create_app(
    settings: Settings | None = None,
    service: AccountService | None = None,
    restore_on_startup: bool = True,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is None:
            factory, engine = create_session_factory(settings.database_url)
            await init_schema(engine)
            store = SqlAccountStore(factory)
            telegram = TelethonGateway(settings.telegram_api_id, settings.telegram_api_hash)
            sessions = EncryptedSessionStore(settings.session_store_path, settings.session_encryption_key)
            app.state.account_service = AccountService(store, telegram, sessions)
            if restore_on_startup:
                await app.state.account_service.restore_sessions()
        else:
            app.state.account_service = service
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    if service is not None:
        app.state.account_service = service
    app.include_router(
        accounts_router,
        dependencies=[Depends(create_api_key_dependency(settings))],
    )
    return app


def build_for_tests(service: AccountService, settings: Settings) -> FastAPI:
    return create_app(settings=settings, service=service, restore_on_startup=False)
