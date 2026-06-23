#!/usr/bin/env python3
"""Minimal metadata-only OpenAI-compatible proxy skeleton.

This proxy forwards JSON requests to an upstream OpenAI-compatible endpoint and
writes metadata-only events. It intentionally does not log request bodies,
messages, responses, or authorization headers.

It is a reference implementation, not a hardened production proxy.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from llm_route_meter.fingerprint import hash_identifier
from llm_route_meter.writer import LocalMeterWriter

UPSTREAM_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.getenv("OPENAI_API_KEY", "")
EVENT_PATH = os.getenv("LLM_ROUTE_METER_EVENTS", "meter-events.jsonl")
WRITER = LocalMeterWriter(EVENT_PATH)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length)
        started = time.perf_counter()
        observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        status = "success"
        response_body = b""
        status_code = 200
        try:
            payload = json.loads(body)
            model = str(payload.get("model", "unknown"))
            route_id = str(self.headers.get("x-llm-route", "unknown_route"))
            upstream = urllib.request.Request(
                UPSTREAM_BASE_URL + self.path,
                data=body,
                headers={"content-type": "application/json", "authorization": f"Bearer {API_KEY}"},
                method="POST",
            )
            with urllib.request.urlopen(upstream, timeout=120) as response:
                status_code = response.status
                response_body = response.read()
            parsed = json.loads(response_body)
        except Exception as exc:
            status = "error"
            status_code = 502
            response_body = json.dumps({"error": "proxy upstream error"}).encode("utf-8")
            parsed = {}
            model = "unknown"
            route_id = str(self.headers.get("x-llm-route", "unknown_route"))
        finally:
            usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
            details = usage.get("prompt_tokens_details", {}) or usage.get("input_tokens_details", {}) or {}
            WRITER.write_event({
                "schema_version": "meter_event_v1",
                "observed_at": observed,
                "route_id": route_id,
                "provider": "openai-compatible-proxy",
                "model": model,
                "request_id_hash": hash_identifier(f"{observed}:{route_id}:{model}"),
                "environment": os.getenv("LLM_ROUTE_METER_ENV", "production"),
                "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "cached_input_tokens": int(details.get("cached_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                "estimated_cost_usd": 0,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "status": status,
                "retry_count": 0,
                "fallback_used": False,
                "streaming": False,
                "batchable": self.headers.get("x-llm-batchable", "false").lower() == "true",
                "quality_signal": self.headers.get("x-llm-quality", "unknown"),
                "payload_policy": "metadata_only",
            })
        self.send_response(status_code)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(response_body)


def main() -> None:
    host = os.getenv("LLM_ROUTE_METER_HOST", "127.0.0.1")
    port = int(os.getenv("LLM_ROUTE_METER_PORT", "8787"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
