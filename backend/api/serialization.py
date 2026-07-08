"""Serialization helpers for API-facing simulation payloads."""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from fastapi.encoders import jsonable_encoder


class SnapshotTable(Protocol):
    """Structural snapshot shape accepted by the API serializer."""

    @property
    def tick_count(self) -> int: ...

    @property
    def state(self) -> str | Enum: ...

    @property
    def config(self) -> dict[str, Any]: ...

    @property
    def grid(self) -> dict[str, Any]: ...

    @property
    def vehicles(self) -> list[dict[str, Any]]: ...

    @property
    def traffic_lights(self) -> list[dict[str, Any]]: ...

    @property
    def metrics(self) -> dict[str, Any]: ...


def serialize_snapshot(snapshot: SnapshotTable) -> dict[str, Any]:
    """Convert a simulation snapshot into a JSON-ready dictionary."""
    encoded = jsonable_encoder(snapshot)
    if not isinstance(encoded, dict):
        raise TypeError("Simulation snapshot must serialize to a JSON object.")
    return encoded
