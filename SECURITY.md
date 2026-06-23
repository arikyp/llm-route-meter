# Security Policy

Payload leakage is a high-severity bug.

LLM Route Meter is designed to emit metadata-only events. Reports of prompt text, response text, transcripts, documents, API keys, authorization headers, or other customer payload data appearing in meter events, summaries, or reports should be treated as security issues.

## Reporting

Open a private security advisory on GitHub when available, or contact the repository owner directly.

Please include:

- affected version or commit,
- reproduction steps,
- example of leaked field name or output location,
- whether network egress was involved.

Do not include real customer payloads in the report. Use synthetic sentinels.
