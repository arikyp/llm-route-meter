from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from .constants import ACCEPTED_QUALITY_SIGNALS, UNKNOWN_QUALITY_SIGNALS
from .guard import assert_metadata_only


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100) * (len(ordered) - 1))))
    return float(ordered[index])


def load_events(path: str | Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        assert_metadata_only(event)
        events.append(event)
    return events


def event_weight(event: dict[str, Any]) -> int:
    return max(1, int(event.get("aggregation_count", 1)))


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_route[str(event["route_id"])].append(event)

    ledgers = []
    for route_id, route_events in sorted(by_route.items()):
        ledgers.append(summarize_route(route_id, route_events))
    return {"schema_version": "route_meter_summary_v1", "routes": ledgers}


def summarize_route(route_id: str, route_events: list[dict[str, Any]]) -> dict[str, Any]:
    request_count = sum(event_weight(e) for e in route_events)
    total_cost = sum(float(e.get("estimated_cost_usd", 0)) for e in route_events)
    input_tokens = sum(int(e.get("input_tokens", 0)) for e in route_events)
    cached_tokens = sum(int(e.get("cached_input_tokens", 0)) for e in route_events)
    output_tokens = sum(int(e.get("output_tokens", 0)) for e in route_events)
    retries = sum(int(e.get("retry_count", 0)) for e in route_events)
    fallbacks = sum(event_weight(e) for e in route_events if e.get("fallback_used"))
    errors = sum(event_weight(e) for e in route_events if e.get("status") != "success")
    batchable = sum(event_weight(e) for e in route_events if e.get("batchable"))
    quality_known_count = sum(event_weight(e) for e in route_events if e.get("quality_signal") not in UNKNOWN_QUALITY_SIGNALS)
    accepted = sum(event_weight(e) for e in route_events if e.get("quality_signal") in ACCEPTED_QUALITY_SIGNALS)
    latencies = [float(e.get("latency_ms", 0)) for e in route_events]
    template_counts: Counter[str] = Counter()
    for event in route_events:
        template = event.get("template_fingerprint")
        if template:
            template_counts[str(template)] += event_weight(event)
    top_template_share = max(template_counts.values()) * 100 / request_count if request_count and template_counts else 0.0
    cached_share = cached_tokens * 100 / input_tokens if input_tokens else 0.0
    batchable_share = batchable * 100 / request_count if request_count else 0.0
    accepted_rate = accepted * 100 / quality_known_count if quality_known_count else None

    ranked_waste = []
    if top_template_share >= 45 and cached_share < 40:
        ranked_waste.append({
            "category": "cache_miss",
            "signal": f"Top template is {top_template_share:.1f}% of calls but cached input share is {cached_share:.1f}%.",
            "first_fix": "Stabilize and front-load static system/tool/schema prefix before dynamic content.",
            "confidence": "medium",
        })
    if batchable_share >= 20:
        ranked_waste.append({
            "category": "batchable_work",
            "signal": f"{batchable_share:.1f}% of requests are marked batchable.",
            "first_fix": "Test managed batch/async processing before private inference.",
            "confidence": "high",
        })
    if retries or fallbacks:
        ranked_waste.append({
            "category": "retry_fallback_spend",
            "signal": f"Observed {retries} retries and {fallbacks} fallback calls in {request_count} requests.",
            "first_fix": "Add idempotency, timeout classes, and a single fallback policy to prevent duplicate spend.",
            "confidence": "medium",
        })
    error_rate = errors * 100 / request_count if request_count else 0.0
    if error_rate >= 2:
        ranked_waste.append({
            "category": "reliability",
            "signal": f"Non-success rate is {error_rate:.1f}%.",
            "first_fix": "Fix reliability before model or provider migration.",
            "confidence": "medium",
        })

    decision = "NO_ACTION"
    reason = "No dominant waste source found in the supplied metadata."
    if ranked_waste:
        decision = "MANAGED_OPTIMIZE"
        reason = "Fix the ranked managed-API waste before private inference benchmarking."
    elif total_cost >= 100 and top_template_share >= 50:
        if accepted_rate is None:
            decision = "NO_GO"
            reason = "Spend and route stability are interesting, but there is no quality oracle for a benchmark decision."
        elif accepted_rate >= 95:
            decision = "PRIVATE_BENCHMARK"
            reason = "Spend, template stability, and quality signal are strong enough for private inference benchmarking."
        else:
            decision = "NO_GO"
            reason = "Quality signal is below the threshold for private inference benchmarking."

    return {
        "schema_version": "route_ledger_v1",
        "route_id": route_id,
        "summary": {
            "request_count": request_count,
            "estimated_cost_usd": round(total_cost, 6),
            "input_tokens": input_tokens,
            "cached_input_tokens": cached_tokens,
            "cached_input_share_pct": round(cached_share, 2),
            "output_tokens": output_tokens,
            "p50_latency_ms": round(median(latencies), 2) if latencies else 0,
            "p95_latency_ms": round(percentile(latencies, 95), 2),
            "retry_count": retries,
            "fallback_count": fallbacks,
            "error_count": errors,
            "batchable_request_share_pct": round(batchable_share, 2),
            "top_template_share_pct": round(top_template_share, 2),
            "accepted_output_rate_pct": round(accepted_rate, 2) if accepted_rate is not None else None,
        },
        "ranked_waste": [{"rank": i + 1, **item} for i, item in enumerate(ranked_waste[:3])],
        "decision": decision,
        "private_benchmark_readiness": "candidate" if decision == "PRIVATE_BENCHMARK" else "not_yet",
        "reason": reason,
        "payload_policy": "metadata_only",
    }
