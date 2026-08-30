import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import pytest

from app.services.mq import rabbitmq_service


class DummyExchange:
    def __init__(self):
        self.published = []

    async def publish(self, message, routing_key):
        self.published.append((message, routing_key))


class DummyChannel:
    def __init__(self, exchange):
        self.exchange = exchange

    async def get_exchange(self, name):
        return self.exchange


@pytest.mark.asyncio
async def test_publish_timeout_check_uses_millisecond_ttl_string(monkeypatch):
    exchange = DummyExchange()
    channel = DummyChannel(exchange)

    async def fake_get_channel():
        return channel

    monkeypatch.setattr(rabbitmq_service, "_get_channel", fake_get_channel)

    await rabbitmq_service.publish_timeout_check("TKTEST", delay_minutes=10)

    assert len(exchange.published) == 1
    message, routing_key = exchange.published[0]
    assert routing_key == rabbitmq_service.QUEUE_DISPATCH_TIMEOUT_DELAY
    assert message.expiration == "600000"
    assert json.loads(message.body.decode()) == {
        "ticket_id": "TKTEST",
        "action": "timeout_check",
    }

