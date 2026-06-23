from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..constants import FORBIDDEN_FIELD_NAMES
from ..fingerprint import hash_identifier
from ..guard import assert_metadata_only

SOURCE_FORBIDDEN_FIELD_NAMES = FORBIDDEN_FIELD_NAMES | {
    "input",
    "output",
    "raw_input",
    "raw_output",
    "prompt_text",
    "response_text",
    "input_text",
    "output_text",
    "request_body",
    "response_body",
}


def load_source(path: str | Path) -> Any:
    source_path = Path(path)
    if source_path.suffix.lower() == ".csv":
        with source_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    text = source_path.read_text(encoding="utf-8")
    if source_path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def assert_source_metadata_only(value: object, path: str = "") -> None:
    forbidden = find_forbidden_source_keys(value, path)
    if forbidden:
        raise ValueError(f"forbidden payload fields in source export: {', '.join(forbidden)}")


def find_forbidden_source_keys(value: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower()
            child_path = f"{path}.{key}" if path else str(key)
            if normalized in SOURCE_FORBIDDEN_FIELD_NAMES and not is_metric_leaf(child_path, normalized):
                found.append(child_path)
            found.extend(find_forbidden_source_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_source_keys(child, f"{path}[{index}]"))
    return found


def is_metric_leaf(path: str, normalized_key: str) -> bool:
    if normalized_key not in {"input", "output"}:
        return False
    normalized_path = path.lower()
    return "usage" in normalized_path or "cost" in normalized_path or "token" in normalized_path


def records_from_source(source: Any, preferred_keys: Iterable[str] = ("data", "results", "rows", "records", "observations", "traces")) -> list[dict[str, Any]]:
    if isinstance(source, list):
        return [as_record(item) for item in source]
    if not isinstance(source, Mapping):
        raise ValueError("source export must be a JSON object, JSON array, JSONL records, or CSV rows")
    for key in preferred_keys:
        value = source.get(key)
        if isinstance(value, list):
            return [as_record(item) for item in value]
    return [dict(source)]


def as_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"source record must be an object, got {type(value).__name__}")
    return dict(value)


def first_value(record: Mapping[str, Any], *paths: str) -> Any:
    for path in paths:
        value = nested_get(record, path)
        if value not in (None, ""):
            return value
    return None


def nested_get(record: Mapping[str, Any], path: str) -> Any:
    current: Any = record
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def to_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return int(value)
    return int(float(value))


def to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def to_bool(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return default


def to_iso_time(value: Any) -> str:
    if value in (None, ""):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if text.isdigit():
        return datetime.fromtimestamp(float(text), timezone.utc).isoformat().replace("+00:00", "Z")
    if text.endswith("Z"):
        return text
    return text


def parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc)
    text = str(value).strip()
    if text.isdigit():
        return datetime.fromtimestamp(float(text), timezone.utc)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_ms(record: Mapping[str, Any]) -> float:
    direct = first_value(record, "latency_ms", "latencyMs", "duration_ms", "durationMs", "time_to_first_token_ms")
    if direct not in (None, ""):
        return to_float(direct)

    seconds = first_value(record, "latency", "duration", "response_time")
    if seconds not in (None, ""):
        value = to_float(seconds)
        return value * 1000 if value < 100 else value

    started = parse_time(first_value(record, "start_time", "startTime", "started_at", "createdAt", "timestamp"))
    ended = parse_time(first_value(record, "end_time", "endTime", "ended_at", "completionStartTime"))
    if started and ended:
        return max(0.0, (ended - started).total_seconds() * 1000)
    return 0.0


def hashed_route(prefix: str, value: Any, fallback: str) -> str:
    if value in (None, ""):
        return fallback
    return f"{prefix}_{hash_identifier(str(value))}"


def event_hash(adapter: str, record: Mapping[str, Any], observed_at: str, route_id: str) -> str:
    stable_id = first_value(record, "request_id", "requestId", "id", "trace_id", "traceId", "generation_id", "generationId")
    if stable_id in (None, ""):
        stable_id = json.dumps(record, sort_keys=True, default=str)
    return hash_identifier(f"{adapter}:{observed_at}:{route_id}:{stable_id}")


def clean_event(event: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = {key: value for key, value in event.items() if value is not None}
    assert_metadata_only(cleaned)
    return cleaned

