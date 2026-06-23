import json
import tempfile
import unittest
from pathlib import Path

from llm_route_meter import LocalMeterWriter
from llm_route_meter.guard import assert_metadata_only
from llm_route_meter.mock_lab import run_mock_lab
from llm_route_meter.wrappers.openai import MeteredOpenAI


class FakeUsage:
    prompt_tokens = 123
    completion_tokens = 45
    prompt_tokens_details = {"cached_tokens": 67}


class FakeResponse:
    usage = FakeUsage()
    text = "RESPONSE_SECRET_SENTINEL"


class FakeCompletions:
    def create(self, **kwargs):
        assert "PROMPT_SECRET_SENTINEL" in str(kwargs)
        return FakeResponse()


class FakeChat:
    completions = FakeCompletions()


class FakeClient:
    chat = FakeChat()


class NoPayloadLeakTests(unittest.TestCase):
    def test_writer_rejects_forbidden_fields(self):
        with self.assertRaises(ValueError):
            assert_metadata_only({"payload_policy": "metadata_only", "messages": [{"content": "secret"}]})

    def test_openai_wrapper_does_not_persist_prompt_or_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            writer = LocalMeterWriter(path)
            metered = MeteredOpenAI(FakeClient(), writer, route_id="ticket_summary")
            response = metered.chat_completion_create(
                model="managed-small",
                messages=[{"role": "user", "content": "PROMPT_SECRET_SENTINEL"}],
                quality_signal="schema_valid",
            )
            self.assertEqual(response.text, "RESPONSE_SECRET_SENTINEL")
            output = path.read_text()
            self.assertNotIn("PROMPT_SECRET_SENTINEL", output)
            self.assertNotIn("RESPONSE_SECRET_SENTINEL", output)
            event = json.loads(output)
            self.assertEqual(event["payload_policy"], "metadata_only")
            self.assertEqual(event["input_tokens"], 123)

    def test_mock_lab_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_mock_lab(tmp)
            self.assertEqual(result["decision"], "support")
            self.assertEqual(result["passed"], result["total"])


if __name__ == "__main__":
    unittest.main()
