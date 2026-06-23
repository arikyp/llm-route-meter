"""Metadata-only import adapters."""

from __future__ import annotations

from typing import Any, Callable

from .langfuse import convert_langfuse
from .litellm import convert_litellm
from .openai_usage import convert_openai_usage

Adapter = Callable[[Any], list[dict[str, Any]]]

ADAPTERS: dict[str, Adapter] = {
    "langfuse": convert_langfuse,
    "litellm": convert_litellm,
    "openai_usage": convert_openai_usage,
}


def convert_source(source_name: str, source: Any) -> list[dict[str, Any]]:
    try:
        adapter = ADAPTERS[source_name]
    except KeyError as exc:
        supported = ", ".join(sorted(ADAPTERS))
        raise ValueError(f"unsupported source {source_name!r}; supported sources: {supported}") from exc
    return adapter(source)
