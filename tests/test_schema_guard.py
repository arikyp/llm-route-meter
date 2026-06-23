import json
import unittest
from pathlib import Path

from llm_route_meter.constants import FORBIDDEN_FIELD_NAMES

ROOT = Path(__file__).resolve().parents[1]


class SchemaGuardTests(unittest.TestCase):
    def test_meter_schema_has_no_forbidden_payload_fields(self):
        schema = json.loads((ROOT / "schemas" / "meter_event_schema_v1.json").read_text())
        properties = {key.lower() for key in schema["properties"].keys()}
        forbidden = properties & FORBIDDEN_FIELD_NAMES
        self.assertEqual(forbidden, set())


if __name__ == "__main__":
    unittest.main()
