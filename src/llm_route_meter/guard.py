from __future__ import annotations

import json
from collections.abc import Mapping

from .constants import FORBIDDEN_FIELD_NAMES


def find_forbidden_keys(value: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower()
            child_path = f"{path}.{key}" if path else str(key)
            if normalized in FORBIDDEN_FIELD_NAMES:
                found.append(child_path)
            found.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return found


def assert_metadata_only(event: Mapping[str, object]) -> None:
    if event.get("payload_policy") != "metadata_only":
        raise ValueError("meter events must set payload_policy=metadata_only")
    forbidden = find_forbidden_keys(event)
    if forbidden:
        raise ValueError(f"forbidden payload fields in meter event: {', '.join(forbidden)}")


def assert_no_sentinels(serialized: str, sentinels: list[str]) -> None:
    leaked = [sentinel for sentinel in sentinels if sentinel and sentinel in serialized]
    if leaked:
        raise ValueError(f"sentinel values leaked into meter output: {leaked}")


def event_to_json(event: Mapping[str, object]) -> str:
    assert_metadata_only(event)
    return json.dumps(event, sort_keys=True, separators=(",", ":"))
