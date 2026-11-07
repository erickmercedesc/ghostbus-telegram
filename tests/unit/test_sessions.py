from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from telegram_engine.sessions.encrypted_store import EncryptedSessionStore


@pytest.mark.asyncio
async def test_encrypted_session_roundtrip(tmp_path: Path):
    key = Fernet.generate_key().decode()
    store = EncryptedSessionStore(tmp_path, key)
    account_id = uuid4()

    ref = await store.save(account_id, "session-string")

    assert (tmp_path / ref).exists()
    raw = (tmp_path / ref).read_bytes()
    assert b"session-string" not in raw
    assert await store.load(ref) == "session-string"
    assert await store.exists(ref) is True
    await store.delete(ref)
    assert await store.exists(ref) is False
