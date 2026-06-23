# LLM Route Meter

Local, metadata-only observability for OpenAI-compatible LLM routes.

LLM Route Meter helps teams find managed-side waste before they benchmark private inference. It records route-level metadata such as token counts, cached-token counts, latency, retries, fallbacks, batchability, quality signals, and template fingerprints. It does **not** record prompts or responses.

## Why

Before moving an LLM workload to Baseten, Fireworks, Together, self-hosted vLLM, or another inference platform, teams should first answer simpler questions:

- Are we missing provider-side prompt caching?
- Is this route batchable?
- Are retries and fallback loops inflating spend?
- Is the model tier too expensive for the task?
- Do we have a quality signal strong enough for a benchmark?

The meter produces a route ledger and a first-action decision: optimize managed API usage, fix prompt shape, right-size models, control retries, run a private benchmark, do nothing, or stop because the evidence is missing.

## Trust Model

By default, this tool writes JSONL to local disk and performs no network egress.

The emitted event schema has no fields for:

- prompt text
- response text
- chat messages
- transcripts
- documents
- files
- API keys
- authorization headers
- PHI/PII payloads

Run it locally, inspect the JSONL, then decide whether to share the metadata.

## Install For Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

No runtime third-party dependency is required for the Python core.

## Quick Start

Run the mock lab:

```bash
python -m llm_route_meter.cli mock-lab --output-dir examples
```

Summarize events:

```bash
python -m llm_route_meter.cli summarize \
  --input examples/mock_events.jsonl \
  --output examples/generated_route_ledger.json
```

Build a readable report:

```bash
python -m llm_route_meter.cli report \
  --input examples/generated_route_ledger.json \
  --output examples/mock_report.html
```

Validate no forbidden payload fields appear:

```bash
python -m llm_route_meter.cli validate --input examples/mock_events.jsonl
```

## Python Wrapper Example

```python
from llm_route_meter import LocalMeterWriter
from llm_route_meter.wrappers.openai import MeteredOpenAI

writer = LocalMeterWriter("meter-events.jsonl")
metered = MeteredOpenAI(openai_client, writer, route_id="ticket_summary_v2")

response = metered.chat_completion_create(
    batchable=True,
    quality_signal="schema_valid",
    template_fingerprint="tpl_ticket_summary_v2",
    messages=[{"role": "user", "content": "..."}],
    model="managed-small",
)
```

The wrapper forwards `messages` to your existing client but never writes them to meter events.

## JavaScript Wrapper Example

```js
import { LocalMeterWriter, meteredCall } from "./packages/typescript/src/index.js";

const writer = new LocalMeterWriter("meter-events.jsonl");
const response = await meteredCall({
  routeId: "ticket_summary_v2",
  model: "managed-small",
  writer,
  batchable: true,
  qualitySignal: "schema_valid",
  call: () => client.chat.completions.create({ model, messages }),
});
```

## Decisions

- `NO_ACTION`: metadata shows no dominant waste source.
- `MANAGED_OPTIMIZE`: fix cache, batch, retry, fallback, or reliability waste before benchmarking private inference.
- `PRIVATE_BENCHMARK`: spend, route stability, and quality signal are strong enough for a private inference benchmark.
- `NO_GO`: quality evidence or route attribution is missing, or quality is below threshold.

## License

Apache-2.0.
