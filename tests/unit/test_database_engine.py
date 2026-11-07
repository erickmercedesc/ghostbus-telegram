import pytest

from telegram_engine.core.exceptions import UnsupportedDatabaseError
from telegram_engine.database.engine import normalize_database_url


def test_normalize_keeps_sqlite():
    url = "sqlite+aiosqlite:///./data/telegram_engine.db"
    assert normalize_database_url(url) == url


def test_normalize_adds_aiomysql_driver():
    assert (
        normalize_database_url("mysql://user:pass@db.example:3306/telegram")
        == "mysql+aiomysql://user:pass@db.example:3306/telegram"
    )


def test_normalize_keeps_aiomysql():
    url = "mysql+aiomysql://user:pass@127.0.0.1:3306/telegram_engine"
    assert normalize_database_url(url) == url


def test_normalize_rejects_other_dialects():
    with pytest.raises(UnsupportedDatabaseError):
        normalize_database_url("postgresql+asyncpg://user:pass@localhost/db")
