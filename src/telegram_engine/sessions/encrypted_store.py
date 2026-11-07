from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken


class EncryptedSessionStore:
    def __init__(self, directory: Path, encryption_key: str) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(encryption_key.encode())

    async def save(self, account_id: UUID, session_payload: str) -> str:
        ref = f"{account_id}.session.enc"
        path = self._directory / ref
        path.write_bytes(self._fernet.encrypt(session_payload.encode()))
        return ref

    async def load(self, session_ref: str) -> str | None:
        path = self._directory / session_ref
        if not path.exists():
            return None
        try:
            return self._fernet.decrypt(path.read_bytes()).decode()
        except InvalidToken:
            return None

    async def exists(self, session_ref: str) -> bool:
        return (self._directory / session_ref).exists()

    async def delete(self, session_ref: str) -> None:
        path = self._directory / session_ref
        if path.exists():
            path.unlink()
