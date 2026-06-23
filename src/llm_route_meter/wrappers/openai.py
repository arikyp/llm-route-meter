from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ..fingerprint import hash_identifier
from ..writer import LocalMeterWriter


def _usage_value(response: Any, *names: str) -> int:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    current = usage
    for name in names:
        if current is None:
            return 0
        if isinstance(current, dict):
            current = current.get(name)
        else:
            current = getattr(current, name, None)
    return int(current or 0)


class MeteredOpenAI:
    """Minimal wrapper for OpenAI-compatible Python clients.

    The wrapper forwards kwargs to `client.chat.completions.create`. It does not
    write kwargs, messages, or response text. Only response usage and timing
    metadata are written.
    """

    def __init__(self, client: Any, writer: LocalMeterWriter, *, route_id: str, provider: str = "openai", environment: str = "production", salt: str = ""):
        self.client = client
        self.writer = writer
        self.route_id = route_id
        self.provider = provider
        self.environment = environment
        self.salt = salt

    def chat_completion_create(self, *, batchable: bool = False, quality_signal: str = "unknown", template_fingerprint: str | None = None, tool_schema_fingerprint: str | None = None, tenant_id: str | None = None, **kwargs: Any) -> Any:
        model = str(kwargs.get("model", "unknown"))
        started = time.perf_counter()
        observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        status = "success"
        error_type = None
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response
        except TimeoutError:
            status = "timeout"
            error_type = "timeout"
            raise
        except Exception as exc:
            status = "error"
            error_type = exc.__class__.__name__
            raise
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            response_obj = locals().get("response")
            event = {
                "schema_version": "meter_event_v1",
                "observed_at": observed,
                "route_id": self.route_id,
                "provider": self.provider,
                "model": model,
                "request_id_hash": hash_identifier(f"{observed}:{self.route_id}:{model}:{latency_ms}", salt=self.salt),
                "tenant_hash": hash_identifier(tenant_id, salt=self.salt) if tenant_id else None,
                "environment": self.environment,
                "input_tokens": _usage_value(response_obj, "prompt_tokens") or _usage_value(response_obj, "input_tokens"),
                "cached_input_tokens": _usage_value(response_obj, "prompt_tokens_details", "cached_tokens") or _usage_value(response_obj, "input_tokens_details", "cached_tokens"),
                "output_tokens": _usage_value(response_obj, "completion_tokens") or _usage_value(response_obj, "output_tokens"),
                "estimated_cost_usd": 0,
                "latency_ms": round(latency_ms, 3),
                "status": status,
                "error_type": error_type,
                "retry_count": 0,
                "fallback_used": False,
                "streaming": bool(kwargs.get("stream", False)),
                "batchable": batchable,
                "quality_signal": quality_signal,
                "template_fingerprint": template_fingerprint,
                "tool_schema_fingerprint": tool_schema_fingerprint,
                "payload_policy": "metadata_only",
            }
            self.writer.write_event({k: v for k, v in event.items() if v is not None})
