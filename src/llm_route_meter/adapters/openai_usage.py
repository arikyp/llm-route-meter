from __future__ import annotations

from typing import Any

from .common import (
    assert_source_metadata_only,
    clean_event,
    event_hash,
    first_value,
    hashed_route,
    records_from_source,
    to_float,
    to_int,
    to_iso_time,
)


def convert_openai_usage(source: Any) -> list[dict[str, Any]]:
    events = []
    for record in iter_openai_records(source):
        assert_source_metadata_only(record)
        observed_at = to_iso_time(first_value(record, "_bucket_start_time", "start_time", "startTime", "created_at", "createdAt"))
        model = str(first_value(record, "model", "line_item") or "unknown")
        route_id = str(first_value(record, "route_id", "metadata.route_id") or "")
        if not route_id:
            route_id = hashed_route("openai_project", first_value(record, "project_id"), "")
        if not route_id:
            route_id = hashed_route("openai_key", first_value(record, "api_key_id"), "")
        if not route_id:
            route_id = f"openai_{model}" if model != "unknown" else "openai_usage"

        amount = first_value(record, "amount.value", "estimated_cost_usd", "cost_usd", "cost")
        event = {
            "schema_version": "meter_event_v1",
            "observed_at": observed_at,
            "route_id": route_id,
            "feature": first_value(record, "feature", "metadata.feature"),
            "provider": "openai",
            "model": model,
            "request_id_hash": event_hash("openai_usage", record, observed_at, route_id),
            "tenant_hash": None,
            "environment": str(first_value(record, "environment", "metadata.environment") or "imported"),
            "input_tokens": to_int(first_value(record, "input_tokens", "inputTokens")),
            "cached_input_tokens": to_int(first_value(record, "input_cached_tokens", "cached_input_tokens", "cached_tokens", "input_token_details.cached_tokens")),
            "output_tokens": to_int(first_value(record, "output_tokens", "outputTokens")),
            "estimated_cost_usd": to_float(amount),
            "latency_ms": 0,
            "status": "success",
            "retry_count": 0,
            "fallback_used": False,
            "streaming": False,
            "batchable": False,
            "quality_signal": "unknown",
            "aggregation_count": max(1, to_int(first_value(record, "num_model_requests", "request_count", "num_requests"), 1)),
            "payload_policy": "metadata_only",
        }
        events.append(clean_event(event))
    return events


def iter_openai_records(source: Any) -> list[dict[str, Any]]:
    records = []
    for item in records_from_source(source, preferred_keys=("data", "results", "rows", "records")):
        results = item.get("results")
        if isinstance(results, list):
            for result in results:
                if not isinstance(result, dict):
                    raise ValueError("OpenAI usage result must be an object")
                merged = dict(result)
                merged["_bucket_start_time"] = item.get("start_time") or item.get("startTime")
                merged["_bucket_end_time"] = item.get("end_time") or item.get("endTime")
                records.append(merged)
        else:
            records.append(item)
    return records

