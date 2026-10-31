from telegram_engine.accounts.models import IncomingMessage

import httpx


class IncomingWebhook:
    def __init__(self, url: str, client: httpx.AsyncClient | None = None) -> None:
        self._url = url.strip()
        self._client = client

    async def publish(self, incoming: IncomingMessage) -> None:
        if not self._url:
            return
        payload = {
            "account_id": str(incoming.account_id),
            "message": incoming.message,
            "from": incoming.sender,
        }
        client = self._client or httpx.AsyncClient(timeout=10)
        owns_client = self._client is None
        try:
            await client.post(self._url, json=payload)
        except httpx.HTTPError:
            return
        finally:
            if owns_client:
                await client.aclose()
