# Examples

Run:

```bash
python -m llm_route_meter.cli mock-lab --output-dir examples
```

Open `examples/mock_report.html` to inspect the generated route ledger.

## Ingest Adapters

Run a fixture through the Langfuse adapter:

```bash
python -m llm_route_meter.cli ingest --source langfuse --input examples/ingest/langfuse_observations.json --output /tmp/langfuse-events.jsonl
python -m llm_route_meter.cli summarize --input /tmp/langfuse-events.jsonl --output /tmp/langfuse-ledger.json
```
