from __future__ import annotations

from typing import Any

from .common import (
    assert_source_metadata_only,
    clean_event,
    duration_ms,
    event_hash,
    first_value,
    hashed_route,
    records_from_source,
    to_bool,
    to_float,
    to_int,
    to_iso_time,
)


def convert_litellm(source: Any) -> list[dict[str, Any]]:
    events = []
    for record in records_from_source(source, preferred_keys=("data", "results", "rows", "records", "spend")):
        assert_source_metadata_only(record)
        observed_at = to_iso_time(first_value(record, "startTime", "start_time", "created_at", "createdAt", "timestamp", "endTime"))
        model = str(first_value(record, "model", "model_name", "modelName") or "unknown")
        route_id = str(first_value(record, "metadata.route_id", "metadata.routeId", "route_id", "routeId", "key_alias", "team_alias") or "")
        if not route_id:
            route_id = hashed_route("litellm_team", first_value(record, "team_id"), "")
        if not route_id:
            route_id = hashed_route("litellm_user", first_value(record, "user_id", "end_user"), "")
        if not route_id:
            route_id = f"litellm_{model}" if model != "unknown" else "litellm_import"

        status_value = str(first_value(record, "status", "response_status") or "success").lower()
        status = "error" if "error" in status_value or status_value.startswith("5") else "success"
        event = {
            "schema_version": "meter_event_v1",
            "observed_at": observed_at,
            "route_id": route_id,
            "feature": first_value(record, "metadata.feature"),
            "provider": str(first_value(record, "custom_llm_provider", "litellm_provider", "provider") or "litellm"),
            "model": model,
            "request_id_hash": event_hash("litellm", record, observed_at, route_id),
            "tenant_hash": first_value(record, "metadata.tenant_hash", "tenant_hash"),
            "environment": str(first_value(record, "environment", "metadata.environment") or "imported"),
            "input_tokens": to_int(first_value(record, "prompt_tokens", "input_tokens", "inputTokens")),
            "cached_input_tokens": to_int(first_value(record, "cache_read_input_tokens", "cached_input_tokens", "input_cached_tokens")),
            "output_tokens": to_int(first_value(record, "completion_tokens", "output_tokens", "outputTokens")),
            "estimated_cost_usd": to_float(first_value(record, "response_cost", "spend", "cost", "cost_usd", "estimated_cost_usd")),
            "latency_ms": round(duration_ms(record), 3),
            "status": status,
            "retry_count": to_int(first_value(record, "retry_count", "metadata.retry_count")),
            "fallback_used": to_bool(first_value(record, "fallback_used", "metadata.fallback_used")),
            "streaming": to_bool(first_value(record, "streaming", "metadata.streaming")),
            "batchable": to_bool(first_value(record, "metadata.batchable", "batchable")),
            "quality_signal": str(first_value(record, "metadata.quality_signal", "quality_signal") or "unknown"),
            "template_fingerprint": first_value(record, "metadata.template_fingerprint", "template_fingerprint"),
            "tool_schema_fingerprint": first_value(record, "metadata.tool_schema_fingerprint", "tool_schema_fingerprint"),
            "aggregation_count": max(1, to_int(first_value(record, "request_count", "num_requests"), 1)),
            "payload_policy": "metadata_only",
        }
        events.append(clean_event(event))
    return events

