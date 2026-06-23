# Ingest Adapters

`llm-route-meter ingest` converts exported LLM metadata into `meter_event_v1` JSONL. It does not call vendor APIs and does not upload anything.

Supported sources:

- `openai_usage`: OpenAI organization usage/cost style JSON exports with bucketed `results`.
- `langfuse`: Langfuse observation/trace exports with `usageDetails`, `costDetails`, and optional route metadata.
- `litellm`: LiteLLM spend/log exports as JSON, JSONL, or CSV rows.

## Commands

```bash
python -m llm_route_meter.cli ingest \
  --source langfuse \
  --input examples/ingest/langfuse_observations.json \
  --output /tmp/langfuse-meter-events.jsonl

python -m llm_route_meter.cli summarize \
  --input /tmp/langfuse-meter-events.jsonl \
  --output /tmp/langfuse-route-ledger.json

python -m llm_route_meter.cli report \
  --input /tmp/langfuse-route-ledger.json \
  --output /tmp/langfuse-route-report.html
```

## Trust Boundary

Before converting a source record, the adapter scans it for payload-shaped fields. Ingestion fails if the export contains fields such as `messages`, `prompt`, `content`, `text`, `body`, `headers`, `payload`, `api_key`, or raw `input`/`output` outside token/cost usage containers.

Allowed source fields include token and cost counters such as `usageDetails.input`, `usageDetails.output`, `prompt_tokens`, `completion_tokens`, `input_cached_tokens`, `response_cost`, and `costDetails.total`.

## Route Mapping

Adapters prefer explicit route metadata:

- `metadata.route_id`
- `route_id`
- `routeId`

If no route is present, adapters fall back to safe source identifiers such as model name or hashed project/key/user identifiers. OpenAI aggregate exports often only identify project, API key, or model, so route attribution is weaker unless the account already maps those IDs to product routes.

## Aggregate Exports

Some exports represent many requests in one row. Those rows include `aggregation_count` in the generated meter event, and summaries use it for `request_count`.
