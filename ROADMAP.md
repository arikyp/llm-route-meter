# Roadmap

LLM Route Meter is intentionally small: local collection, metadata-only events, no hosted collector, and plain files that teams can inspect before sharing anything.

## Near Term

- Add provider pricing import so `estimated_cost_usd` can be computed from current model pricing tables instead of caller-supplied values.
- Harden the OpenAI-compatible proxy path with streamed response accounting, timeout classes, and clearer deployment examples.
- Add existing-log adapters for common gateway exports where prompts and responses are already excluded.
- Add a static report export bundle that packages JSONL, route ledger, mock/eval output, and HTML into a shareable archive.

## Trust Gates

Every accepted feature must preserve these boundaries:

- No prompts, responses, transcripts, documents, files, headers, API keys, request bodies, or payload text in meter events.
- Local file output first. Network egress must be opt-in and outside the default path.
- Tests must include sentinel leak checks when code touches collection, wrappers, adapters, or reports.
- Public docs must distinguish metadata evidence from private benchmark or migration advice.

## Later

- More provider-compatible wrappers.
- Optional JSON Schema validation dependency for stricter CLI validation.
- Configurable decision thresholds.
- Redaction proof artifacts for security review.
