"""Брокер событий: FastStream поверх Kafka-совместимого API Redpanda."""

from __future__ import annotations

from faststream.kafka import KafkaBroker


def create_broker(bootstrap_servers: str) -> KafkaBroker:
    return KafkaBroker(bootstrap_servers)
