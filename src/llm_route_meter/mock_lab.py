from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .summarize import summarize_events
from .report import write_html_report

BASE_TIME = datetime(2026, 6, 23, 10, 0, tzinfo=timezone.utc)


def event(*, route_id: str, index: int, model: str = "managed-small", cost: float = 0.01, input_tokens: int = 1800, cached_tokens: int = 900, output_tokens: int = 420, latency_ms: float = 1800, status: str = "success", retry_count: int = 0, fallback_used: bool = False, batchable: bool = False, quality_signal: str = "schema_valid", template_fingerprint: str = "tpl_main") -> dict[str, Any]:
    return {
        "schema_version": "meter_event_v1",
        "observed_at": (BASE_TIME + timedelta(seconds=index * 17)).isoformat().replace("+00:00", "Z"),
        "route_id": route_id,
        "feature": route_id.replace("_", "-"),
        "provider": "openai",
        "model": model,
        "request_id_hash": f"req_{route_id}_{index:04d}",
        "tenant_hash": f"tenant_{index % 7}",
        "environment": "mock",
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "latency_ms": latency_ms,
        "time_to_first_token_ms": latency_ms * 0.32,
        "status": status,
        "retry_count": retry_count,
        "fallback_used": fallback_used,
        "streaming": False,
        "batchable": batchable,
        "quality_signal": quality_signal,
        "template_fingerprint": template_fingerprint,
        "tool_schema_fingerprint": "tool_static",
        "payload_policy": "metadata_only",
    }


def build_mock_events() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    scenarios = [
        {"route_id": "support_summary_waste", "expected_decision": "MANAGED_OPTIMIZE"},
        {"route_id": "extraction_private_ready", "expected_decision": "PRIVATE_BENCHMARK"},
        {"route_id": "tiny_chat_no_action", "expected_decision": "NO_ACTION"},
        {"route_id": "summary_no_quality_no_go", "expected_decision": "NO_GO"},
    ]
    for i in range(60):
        events.append(event(route_id="support_summary_waste", index=i, cost=0.065, cached_tokens=120 if i % 5 else 650, batchable=i % 2 == 0, retry_count=1 if i % 11 == 0 else 0, fallback_used=i % 17 == 0, status="timeout" if i % 19 == 0 else "success", latency_ms=2400 + (i % 9) * 260, template_fingerprint="tpl_support_summary", quality_signal="schema_valid" if i % 23 else "schema_invalid"))
    for i in range(80):
        events.append(event(route_id="extraction_private_ready", index=1000 + i, model="managed-large", cost=1.85, input_tokens=5200, cached_tokens=3900, output_tokens=880, batchable=False, retry_count=0, fallback_used=False, latency_ms=3100 + (i % 7) * 120, template_fingerprint="tpl_claim_extraction" if i < 70 else f"tpl_variant_{i}", quality_signal="schema_valid" if i % 41 else "accepted"))
    for i in range(35):
        events.append(event(route_id="tiny_chat_no_action", index=2000 + i, cost=0.001, input_tokens=600, cached_tokens=20, output_tokens=130, latency_ms=900 + (i % 5) * 80, template_fingerprint=f"tpl_chat_{i}", quality_signal="accepted"))
    for i in range(70):
        events.append(event(route_id="summary_no_quality_no_go", index=3000 + i, model="managed-large", cost=1.6, input_tokens=4300, cached_tokens=3400, output_tokens=720, latency_ms=2700 + (i % 7) * 90, template_fingerprint="tpl_exec_summary" if i < 66 else f"tpl_summary_variant_{i}", quality_signal="unknown"))
    return events, scenarios


def evaluate_summary(summary: dict[str, Any], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    routes = {route["route_id"]: route for route in summary["routes"]}
    results = []
    for scenario in scenarios:
        route = routes.get(scenario["route_id"])
        actual = route.get("decision") if route else None
        results.append({**scenario, "actual_decision": actual, "status": "pass" if actual == scenario["expected_decision"] else "fail"})
    passed = sum(1 for result in results if result["status"] == "pass")
    return {"schema_version": "route_meter_mock_lab_eval_v1", "passed": passed, "total": len(results), "decision": "support" if passed == len(results) else "revise", "results": results}


def run_mock_lab(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    events, scenarios = build_mock_events()
    events_path = output / "mock_events.jsonl"
    summary_path = output / "generated_route_ledger.json"
    eval_path = output / "mock_eval.json"
    report_path = output / "mock_report.html"
    events_path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")
    summary = summarize_events(events)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    evaluation = evaluate_summary(summary, scenarios)
    eval_path.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    write_html_report(summary, report_path)
    if evaluation["decision"] != "support":
        raise RuntimeError(f"mock lab failed: {evaluation}")
    return evaluation
