from __future__ import annotations

import hashlib


def fingerprint_text(value: str, *, salt: str = "") -> str:
    """Return a non-reversible short fingerprint for local repetition analysis.

    The caller may provide a private salt. Do not send the source text to anyone;
    only the digest is intended for route meter events.
    """
    digest = hashlib.sha256((salt + value).encode("utf-8")).hexdigest()
    return "fp_" + digest[:16]


def hash_identifier(value: str, *, salt: str = "") -> str:
    return fingerprint_text(value, salt=salt).replace("fp_", "id_", 1)
