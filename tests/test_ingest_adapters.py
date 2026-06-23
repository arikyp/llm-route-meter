import json
import tempfile
import unittest
from pathlib import Path

from llm_route_meter.adapters import convert_source
from llm_route_meter.adapters.common import load_source
from llm_route_meter.cli import main
from llm_route_meter.guard import event_to_json
from llm_route_meter.summarize import summarize_events

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "ingest"


class IngestAdapterTests(unittest.TestCase):
    def test_openai_usage_export_counts_aggregate_requests(self):
        events = convert_source("openai_usage", load_source(FIXTURES / "openai_usage_export.json"))
        self.assertEqual(len(events), 2)
        self.assertEqual(sum(event["aggregation_count"] for event in events), 120)
        summary = summarize_events(events)
        request_count = sum(route["summary"]["request_count"] for route in summary["routes"])
        self.assertEqual(request_count, 120)
        self.assertNotIn("proj_support_summary", "\n".join(event_to_json(event) for event in events))

    def test_langfuse_export_maps_usage_and_metadata(self):
        events = convert_source("langfuse", load_source(FIXTURES / "langfuse_observations.json"))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["route_id"], "support_summary")
        self.assertEqual(events[0]["input_tokens"], 1800)
        self.assertEqual(events[0]["cached_input_tokens"], 120)
        self.assertEqual(events[1]["retry_count"], 1)
        serialized = "\n".join(event_to_json(event) for event in events)
        self.assertNotIn("messages", serialized)
        self.assertNotIn("content", serialized)

    def test_litellm_jsonl_export_ingests(self):
        events = convert_source("litellm", load_source(FIXTURES / "litellm_spend_logs.jsonl"))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["provider"], "openai")
        self.assertEqual(events[0]["route_id"], "support_summary")
        self.assertEqual(events[0]["latency_ms"], 2600)

    def test_cli_ingest_writes_metadata_only_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            rc = main([
                "ingest",
                "--source",
                "langfuse",
                "--input",
                str(FIXTURES / "langfuse_observations.json"),
                "--output",
                str(output),
                "--sentinel",
                "PROMPT_SECRET_SENTINEL",
            ])
            self.assertEqual(rc, 0)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["payload_policy"] == "metadata_only" for row in rows))

    def test_payload_bearing_source_is_rejected(self):
        with self.assertRaises(ValueError):
            convert_source("langfuse", load_source(FIXTURES / "source_with_payload.json"))


if __name__ == "__main__":
    unittest.main()
