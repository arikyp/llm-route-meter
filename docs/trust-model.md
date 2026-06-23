# Trust Model

LLM Route Meter is designed for local-first, metadata-only use.

- No hosted collector is configured by default.
- The local writer appends JSONL to disk.
- The schema has no fields for prompt text, response text, messages, documents, API keys, or authorization headers.
- Customers inspect the JSONL before sharing anything.
- Payload leakage is a security issue.

## What Makes It Trustworthy

- Open-source implementation.
- Small event schema.
- Sentinel tests.
- Local-only default.
- Explicit limitations.
