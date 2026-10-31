from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from telegram_engine.accounts.models import IncomingMessage
from telegram_engine.telegram.gateway import TelethonGateway
from telegram_engine.webhooks.incoming import IncomingWebhook
from tests.unit.test_telegram_gateway import FakeClient


class RecordingSink:
    def __init__(self) -> None:
        self.messages: list[IncomingMessage] = []

    async def publish(self, incoming: IncomingMessage) -> None:
        self.messages.append(incoming)


@pytest.mark.asyncio
async def test_incoming_webhook_posts_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = httpx.Response(200).json if False else None
        captured["body"] = request.content
        captured["url"] = str(request.url)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    webhook = IncomingWebhook("https://example.com/incoming", client=client)
    account_id = uuid4()
    await webhook.publish(IncomingMessage(account_id=account_id, message="hola", sender="bob"))
    assert captured["url"] == "https://example.com/incoming"
    assert b'"from":"bob"' in captured["body"]
    assert str(account_id).encode() in captured["body"]
    assert b'"message":"hola"' in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
async def test_empty_webhook_url_is_noop():
    webhook = IncomingWebhook("")
    await webhook.publish(IncomingMessage(account_id=uuid4(), message="hola", sender="bob"))


@pytest.mark.asyncio
async def test_gateway_forwards_incoming_message_to_sink():
    client = FakeClient()
    gateway = TelethonGateway(1, "hash", client_factory=lambda payload: client)
    sink = RecordingSink()
    gateway.set_incoming_sink(sink)
    account_id = uuid4()
    await gateway.request_otp(account_id, "+1555")

    async def get_sender():
        return SimpleNamespace(username="bob", id=99)

    event = SimpleNamespace(out=False, raw_text="hola", chat_id=10, id=1, get_sender=get_sender)
    await client.handlers[0](event)
    assert sink.messages[0].account_id == account_id
    assert sink.messages[0].message == "hola"
    assert sink.messages[0].sender == "bob"
