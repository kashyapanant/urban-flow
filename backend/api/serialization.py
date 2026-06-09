"""Serialization helpers for API-facing simulation payloads."""

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder


def serialize_snapshot(snapshot: Any) -> dict[str, Any]:
    """Convert a simulation snapshot into a JSON-ready dictionary."""
    encoded = jsonable_encoder(snapshot)
    if not isinstance(encoded, dict):
        raise TypeError("Simulation snapshot must serialize to a JSON object.")
    return encoded
