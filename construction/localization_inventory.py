"""Deterministic inventory serializer (Stage 2).

Single canonical normalization shared by the manifest generator, the checker,
and adversarial tests. DB-return-type safe: every value is coerced to str,
rows are sorted in Python by the full tuple (never relying on DB tie order),
and the digest uses JSON (never repr()).
"""

import hashlib
import json


def normalize_row(row):
    return tuple("" if v is None else str(v) for v in row)


def merkle_root(rows):
    norm = sorted(normalize_row(r) for r in rows)
    return len(norm), hashlib.sha256(
        json.dumps(norm, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
