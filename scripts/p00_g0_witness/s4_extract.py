"""P00/G0 S4 extraction/redaction component (revision 2, design-bound).

Implements the extraction contract of the Gate G8 study
(P00_G0_MECHANISM_DESIGN_SELECTION_STUDY_2026-11-02.md,
SHA-256 641bf0d0e93816d4d03ae382a0be9ad65ba330931b7229a75daf4c20f8122501),
plus revision 2 (2026-11-02):
  - conflicting-evidence detection across two observations in one assessment
    => INCOMPLETE, reason "conflicting_evidence", no class emitted;
  - unevaluable/ambiguous input => INCOMPLETE, reason "evaluation_ambiguous"
    (distinct from out-of-enum values, which stay C3/UNKNOWN).

Properties enforced: reads only permitted columns for the caller's own session
(trx_mysql_thread_id = CONNECTION_ID() in WHERE only); never selects, returns,
logs or stores the connection id or excluded fields; emits only C1-C6 codes,
statuses (UNKNOWN/INCOMPLETE/FAIL) and fixed reasons; freshness rule >= 150 ms
idle before a read; immutable-append record with a SHA-256 digest chain.

No target access, no configuration change, no writes, no qualification.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from typing import Callable, Iterable, Mapping, Optional, Sequence

SURFACE = "S4"
ALLOWED_COLUMNS: Sequence[str] = (
    "trx_is_read_only",
    "trx_autocommit_non_locking",
    "trx_state",
)

QUERY = (
    "SELECT trx_is_read_only, trx_autocommit_non_locking FROM "
    "information_schema.innodb_trx "
    "WHERE trx_mysql_thread_id = CONNECTION_ID()"
)

C1 = "C1"  # MODE_READONLY
C2 = "C2"  # MODE_READWRITE
C3 = "C3"  # MODE_INDETERMINATE
C4 = "C4"  # MODE_ABSENT
C5 = "C5"  # MODE_WITHHELD
C6 = "C6"  # MODE_ERROR

UNKNOWN = "UNKNOWN"
INCOMPLETE = "INCOMPLETE"
FAIL = "FAIL"

STATUSES = (UNKNOWN, INCOMPLETE, FAIL)
CODES = (C1, C2, C3, C4, C5, C6)

MIN_IDLE_MS = 150
REASONS = (
    "declared_readonly",
    "declared_readwrite",
    "absence_not_evidence",
    "autocommit_non_locking",
    "global_mode_confound",
    "multiple_rows",
    "unexpected_column",
    "unexpected_value",
    "evaluation_ambiguous",
    "evaluation_aborted",
    "conflicting_evidence",
    "freshness_unproven",
    "query_error",
    "integrity_failure",
)

Row = Mapping[str, object]


class Outcome:
    """A single classification outcome (code may be None when no class is emitted)."""

    __slots__ = ("code", "status", "reason")

    def __init__(self, code: Optional[str], status: str, reason: str) -> None:
        if code is not None and code not in CODES:
            raise ValueError(f"code outside closed vocabulary: {code!r}")
        if status not in STATUSES:
            raise ValueError(f"status outside closed vocabulary: {status!r}")
        if reason not in REASONS:
            raise ValueError(f"reason outside fixed set: {reason!r}")
        self.code = code
        self.status = status
        self.reason = reason

    def as_dict(self) -> dict:
        return {"code": self.code, "status": self.status, "reason": self.reason}


def classify(
    row: Optional[Row],
    *,
    innodb_read_only: bool,
    multiple: bool = False,
) -> Outcome:
    """Classify one own-session row per the Gate G8 decision logic."""
    if multiple:
        return Outcome(C3, UNKNOWN, "multiple_rows")
    if row is None:
        return Outcome(C4, UNKNOWN, "absence_not_evidence")

    unexpected = [k for k in row.keys() if k not in ALLOWED_COLUMNS]
    if unexpected:
        return Outcome(C5, INCOMPLETE, "unexpected_column")

    raw_read_only = row.get("trx_is_read_only")
    raw_auto = row.get("trx_autocommit_non_locking", 0)
    try:
        read_only = int(raw_read_only)
        autocommit_non_locking = int(raw_auto)
    except (TypeError, ValueError):
        # Value missing or non-numeric: evaluation is ambiguous, not out-of-enum.
        return Outcome(None, INCOMPLETE, "evaluation_ambiguous")

    if read_only not in (0, 1) or autocommit_non_locking not in (0, 1):
        return Outcome(C3, UNKNOWN, "unexpected_value")

    if autocommit_non_locking == 1:
        return Outcome(C3, UNKNOWN, "autocommit_non_locking")
    if innodb_read_only:
        return Outcome(C3, UNKNOWN, "global_mode_confound")
    if read_only == 1:
        return Outcome(C1, UNKNOWN, "declared_readonly")
    return Outcome(C2, UNKNOWN, "declared_readwrite")


class S4Extractor:
    """Reading/recording wrapper; the query runner is injected for testability."""

    def __init__(
        self,
        run_query: Callable[[str], Iterable[Row]],
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        min_idle_ms: int = MIN_IDLE_MS,
        genesis_digest: str = "0" * 64,
    ) -> None:
        self._run_query = run_query
        self._clock = clock
        self._sleep = sleeper
        self._min_idle_ms = min_idle_ms
        self._last_read_at: Optional[float] = None
        self._prev_digest = genesis_digest

    # -- internals ---------------------------------------------------------
    def _enforce_freshness(self) -> tuple[float, bool]:
        now = self._clock()
        if self._last_read_at is None:  # first read in this assessment
            self._last_read_at = now
            return 0.0, True
        gap_ms = (now - self._last_read_at) * 1000.0
        if gap_ms < self._min_idle_ms:
            self._sleep((self._min_idle_ms - gap_ms) / 1000.0)
            now = self._clock()
            gap_ms = (now - self._last_read_at) * 1000.0
        self._last_read_at = now
        return gap_ms, gap_ms >= self._min_idle_ms

    def _read_once(self) -> tuple[Optional[list], float, bool, bool]:
        """Return (rows, gap_ms, freshness_ok, errored)."""
        gap_ms, fresh = self._enforce_freshness()
        if not fresh:
            return [], gap_ms, False, False
        try:
            return list(self._run_query(QUERY)), gap_ms, True, False
        except Exception:
            return [], gap_ms, True, True

    def _record(
        self,
        *,
        attempt_id: str,
        case_id: str,
        handle: str,
        gap_ms: float,
        outcome: Outcome,
        fresh: bool = True,
    ) -> dict:
        record = {
            "attempt_id": attempt_id,
            "case_id": case_id,
            "surface": SURFACE,
            "correlation": {"handle": handle, "predicate": "own_session", "continuity": True},
            "freshness": {
                "idle_gap_ms": round(gap_ms, 1),
                "cache_class": "fresh" if fresh else "unproven",
            },
            "class_outcome": outcome.as_dict(),
            "redaction_decision": "emitted_label" if outcome.code else "withheld",
            "timestamp_class": "coarse",
        }
        body = json.dumps(record, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256((self._prev_digest + body).encode("utf-8")).hexdigest()
        record["integrity"] = {"prev_digest": self._prev_digest, "this_digest": digest}
        self._prev_digest = digest
        return record

    # -- public API --------------------------------------------------------
    def extract(
        self,
        *,
        case_id: str = "smoke",
        innodb_read_only: bool = False,
        integrity_failed: bool = False,
    ) -> dict:
        rows, gap_ms, fresh, errored = self._read_once()
        if integrity_failed:
            outcome = Outcome(None, FAIL, "integrity_failure")
        elif errored:
            outcome = Outcome(None, INCOMPLETE, "evaluation_aborted")
        elif not fresh:
            outcome = Outcome(None, INCOMPLETE, "freshness_unproven")
        elif len(rows) > 1:
            outcome = classify(None, innodb_read_only=innodb_read_only, multiple=True)
        elif len(rows) == 1:
            outcome = classify(rows[0], innodb_read_only=innodb_read_only)
        else:
            outcome = classify(None, innodb_read_only=innodb_read_only)
        return self._record(
            attempt_id=secrets.token_hex(16),
            case_id=case_id,
            handle=secrets.token_hex(16),
            gap_ms=gap_ms,
            outcome=outcome,
            fresh=fresh,
        )

    def assess(
        self,
        *,
        case_id: str = "assessment",
        innodb_read_only: bool = False,
        integrity_failed: bool = False,
    ) -> dict:
        """Two observations in one assessment; conflicting evidence => INCOMPLETE."""
        rows_a, gap_a, fresh_a, err_a = self._read_once()
        rows_b, gap_b, fresh_b, err_b = self._read_once()
        if integrity_failed:
            outcome = Outcome(None, FAIL, "integrity_failure")
        elif err_a or err_b:
            outcome = Outcome(None, INCOMPLETE, "evaluation_aborted")
        elif not (fresh_a and fresh_b):
            outcome = Outcome(None, INCOMPLETE, "freshness_unproven")
        else:
            key_a = _row_key(rows_a)
            key_b = _row_key(rows_b)
            if key_a is None or key_b is None:
                outcome = Outcome(None, INCOMPLETE, "evaluation_ambiguous")
            elif key_a != key_b:
                outcome = Outcome(None, INCOMPLETE, "conflicting_evidence")
            elif len(rows_a) > 1:
                outcome = classify(None, innodb_read_only=innodb_read_only, multiple=True)
            elif len(rows_a) == 1:
                outcome = classify(rows_a[0], innodb_read_only=innodb_read_only)
            else:
                outcome = classify(None, innodb_read_only=innodb_read_only)
        return self._record(
            attempt_id=secrets.token_hex(16),
            case_id=case_id,
            handle=secrets.token_hex(16),
            gap_ms=max(gap_a, gap_b),
            outcome=outcome,
            fresh=(fresh_a and fresh_b),
        )


def _row_key(rows: Sequence[Row]) -> Optional[tuple]:
    """Canonical comparable key for one-or-zero-row observation lists."""
    if len(rows) > 1:
        # Multiple rows already mean indeterminate; represent as a distinct key.
        return ("multi", len(rows))
    if not rows:
        return ("absent",)
    row = rows[0]
    try:
        return ("row", int(row.get("trx_is_read_only")), int(row.get("trx_autocommit_non_locking", 0)))
    except (TypeError, ValueError):
        return None
