# Contributing

Contributions are welcome if they keep the project metadata-only by default.

## Local Checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 scripts/verify_no_payload_leak.py
cd packages/typescript && npm test
```

## Privacy Boundary

Do not add fields or examples that include prompts, responses, transcripts, documents, files, headers, API keys, request bodies, or payload text. New collection paths should include sentinel leak tests.

## Scope

This repository is for the open-source meter: local event collection, schemas, wrappers, summarization, reports, examples, and tests. Commercial benchmark packs, customer-specific interpretation, and partner workflows should not be added here.
