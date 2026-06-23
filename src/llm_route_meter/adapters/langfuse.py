from __future__ import annotations

from typing import Any

from .common import (
    assert_source_metadata_only,
    clean_event,
    duration_ms,
    event_hash,
    first_value,
    records_from_source,
    to_bool,
    to_float,
    to_int,
    to_iso_time,
)


def convert_langfuse(source: Any) -> list[dict[str, Any]]:
    events = []
    for record in records_from_source(source, preferred_keys=("data", "observations", "traces", "results", "rows")):
        assert_source_metadata_only(record)
        observed_at = to_iso_time(first_value(record, "startTime", "start_time", "createdAt", "timestamp"))
        route_id = str(first_value(record, "metadata.route_id", "metadata.routeId", "route_id", "routeId", "name", "traceName", "trace_id", "traceId") or "langfuse_import")
        model = str(first_value(record, "model", "modelName", "metadata.model", "metadata.model_name") or "unknown")
        status_text = str(first_value(record, "status", "level") or "success").lower()
        status = "error" if "error" in status_text else "success"

        event = {
            "schema_version": "meter_event_v1",
            "observed_at": observed_at,
            "route_id": route_id,
            "feature": first_value(record, "metadata.feature", "metadata.route_group"),
            "provider": str(first_value(record, "metadata.provider", "provider") or "langfuse"),
            "model": model,
            "request_id_hash": event_hash("langfuse", record, observed_at, route_id),
            "tenant_hash": first_value(record, "metadata.tenant_hash", "metadata.tenantHash"),
            "environment": str(first_value(record, "environment", "metadata.environment") or "imported"),
            "input_tokens": to_int(first_value(record, "usageDetails.input", "usageDetails.input_tokens", "usageDetails.promptTokens", "usage_details.input", "usage_details.input_tokens", "usage.input", "usage.prompt_tokens", "usage.promptTokens")),
            "cached_input_tokens": to_int(first_value(record, "usageDetails.cachedInput", "usageDetails.cached_input_tokens", "usageDetails.cache_read_input_tokens", "usage_details.cached_input", "usage_details.cached_input_tokens", "usage.cache_read_input_tokens")),
            "output_tokens": to_int(first_value(record, "usageDetails.output", "usageDetails.output_tokens", "usageDetails.completionTokens", "usage_details.output", "usage_details.output_tokens", "usage.output", "usage.completion_tokens", "usage.completionTokens")),
            "estimated_cost_usd": to_float(first_value(record, "costDetails.total", "cost_details.total", "totalCost", "calculatedTotalCost", "cost", "metadata.estimated_cost_usd")),
            "latency_ms": round(duration_ms(record), 3),
            "status": status,
            "error_type": first_value(record, "statusMessage", "metadata.error_type") if status == "error" else None,
            "retry_count": to_int(first_value(record, "metadata.retry_count", "metadata.retryCount")),
            "fallback_used": to_bool(first_value(record, "metadata.fallback_used", "metadata.fallbackUsed")),
            "streaming": to_bool(first_value(record, "metadata.streaming")),
            "batchable": to_bool(first_value(record, "metadata.batchable")),
            "quality_signal": str(first_value(record, "metadata.quality_signal", "metadata.qualitySignal") or "unknown"),
            "template_fingerprint": first_value(record, "metadata.template_fingerprint", "metadata.templateFingerprint"),
            "tool_schema_fingerprint": first_value(record, "metadata.tool_schema_fingerprint", "metadata.toolSchemaFingerprint"),
            "payload_policy": "metadata_only",
        }
        events.append(clean_event(event))
    return events

