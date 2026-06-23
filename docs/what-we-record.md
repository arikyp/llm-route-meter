# What We Record

Metadata only:

- route ID
- provider/model
- request ID hash
- token counts
- cached-token counts
- latency
- status/error type
- retry/fallback counters
- batchable flag
- quality signal
- local template/tool-schema fingerprints

We do not record prompts, responses, transcripts, documents, files, API keys, or auth headers.
