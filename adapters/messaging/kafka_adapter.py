"""Kafka adapter for the Arca Platform events contract.

This is a reference adapter; products may use it or provide their own adapter
that satisfies the events contract.
"""

from __future__ import annotations

import json
from typing import Callable

from pydantic import BaseModel


class PlatformEvent(BaseModel):
    event_id: str
    event_type: str
    source: str
    timestamp: str
    correlation_id: str
    tenant_id: str
    payload: dict


class KafkaMessagingAdapter:
    """Reference adapter for producing and consuming platform events via Kafka."""

    def __init__(self, bootstrap_servers: str, topic_prefix: str = "arca") -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self._producer = None
        self._consumers: list = []

    def _topic(self, event_type: str) -> str:
        return f"{self.topic_prefix}.{event_type}"

    def connect(self) -> None:
        try:
            from kafka import KafkaProducer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("kafka-python-ng is required for Kafka adapter") from exc
        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def publish(self, event: PlatformEvent) -> None:
        if self._producer is None:
            raise RuntimeError("Adapter not connected")
        self._producer.send(self._topic(event.event_type), event.model_dump())

    def subscribe(
        self, event_type: str, handler: Callable[[PlatformEvent], None]
    ) -> None:
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("kafka-python-ng is required for Kafka adapter") from exc
        consumer = KafkaConsumer(
            self._topic(event_type),
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id=f"arca-{event_type}",
        )
        self._consumers.append(consumer)
        # In production, consumption runs in a dedicated worker.
        for message in consumer:
            handler(PlatformEvent.model_validate(message.value))
