from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .guard import assert_metadata_only


class LocalMeterWriter:
    """Append metadata-only meter events to local JSONL.

    This writer performs no network calls. It only writes to the configured
    local path.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: Mapping[str, object]) -> None:
        assert_metadata_only(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(event), sort_keys=True) + "\n")
