#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "verify-output"
SENTINELS = ["PROMPT_SECRET_SENTINEL", "RESPONSE_SECRET_SENTINEL", "AUTH_SECRET_SENTINEL"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "llm_route_meter.cli", "mock-lab", "--output-dir", str(OUT)], cwd=ROOT, check=True)
    events = OUT / "mock_events.jsonl"
    report = OUT / "mock_report.html"
    subprocess.run([sys.executable, "-m", "llm_route_meter.cli", "validate", "--input", str(events), *sum((["--sentinel", s] for s in SENTINELS), [])], cwd=ROOT, check=True)
    combined = events.read_text() + report.read_text()
    leaked = [sentinel for sentinel in SENTINELS if sentinel in combined]
    if leaked:
        raise SystemExit(f"payload sentinel leak detected: {leaked}")
    for line in events.read_text().splitlines():
        event = json.loads(line)
        if event.get("payload_policy") != "metadata_only":
            raise SystemExit("non metadata-only event detected")
    print("no payload leak verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
