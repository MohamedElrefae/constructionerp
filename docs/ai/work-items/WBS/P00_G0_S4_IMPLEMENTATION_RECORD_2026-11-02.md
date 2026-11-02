# P00/G0 — S4 component implementation record, 2026-11-02

**Status: IMPLEMENTED AND UNIT-TESTED (synthetic inputs only) — runtime/integration evidence ABSENT ⇒ INCOMPLETE.** No Q7 execution, no target access, no D2, no custody, no qualification, no closure. Gate remains BLOCKED.

## 1. Authorization basis

Corrected implementation authorization (2026-11-02), bound to `P00_G0_MECHANISM_DESIGN_SELECTION_STUDY_2026-11-02.md` (SHA-256 `641bf0d0e93816d4d03ae382a0be9ad65ba330931b7229a75daf4c20f8122501`). Scope: implement the S4 extraction/redaction component per that specification; unit-test with synthetic inputs only; no Q7 execution, no target, no D2, no custody, no qualification, no closure.

## 2. Delivered component

| File | SHA-256 |
|---|---|
| `apps/construction/scripts/p00_g0_witness/s4_extract.py` | `e9dc45866a6bbe35b30b8e8db1e5c1fc425d0b4d9d473ad0e9ed1711ebcdc8e3` |
| `apps/construction/scripts/p00_g0_witness/test_s4_extract.py` | `e5d30beee458763ceb637184fa8948664967346e02a6a1118090d128bd13f76b` |

Contract implemented exactly as specified:
- Query selects only `trx_is_read_only` and `trx_autocommit_non_locking` from `information_schema.innodb_trx` for the caller's own session (`trx_mysql_thread_id = CONNECTION_ID()` in `WHERE` only). The connection id is never projected, returned, logged, or stored.
- Classification: absence ⇒ `C4`/UNKNOWN; autocommit non-locking ⇒ `C3`/UNKNOWN; `@@innodb_read_only=1` equivalent (caller-supplied flag) ⇒ `C3`/UNKNOWN; `trx_is_read_only=1` ⇒ `C1`; `0` ⇒ `C2`; unexpected column ⇒ `C5`/INCOMPLETE; unexpected value/multiple rows ⇒ `C3`/UNKNOWN; query error ⇒ `C6`/UNKNOWN.
- Closed vocabulary enforced at construction (`C1–C6`, `UNKNOWN/INCOMPLETE/FAIL`, fixed reason set); no free text; no passthrough.
- Freshness: the extractor enforces ≥150 ms idle before each read (source cache-refetch bound 0.1 s), records the achieved gap and a freshness class; unproven freshness ⇒ `INCOMPLETE` with no class emitted.
- Immutable-append record with a SHA-256 digest chain over each record body (prev_digest → this_digest); per-attempt random ≥128-bit handle; handle and record contain no identifiers.

## 3. Unit test results (synthetic inputs only)

Command: `python3 -m unittest discover -s apps/construction/scripts/p00_g0_witness -v`
Result: **16 tests, all OK** — covering: absent row; declared read-only; declared read-write; autocommit indeterminacy; global-mode confound; unexpected-column withholding; unexpected-value; multiple rows; closed vocabulary (constructor rejection); single-observation record shape; query contains no forbidden projection; freshness sleep enforcement; digest-chain linkage; no connection id or forbidden keys in record; query error → `C6`; vocabulary in record.

## 4. Status and limitations

- **Implementation: COMPLETE** at design level, unit-tested against synthetic rows.
- **Integration/runtime: INCOMPLETE** — the component was deliberately **not** run against any database (Q7 execution is not authorized; unit tests use synthetic inputs only). The DB query path is exercised only through an injected fake runner.
- No witness is qualified; `trx_is_read_only` remains an unvalidated candidate surface; D5 freshness remains source-bounded only.
- Q7 remains `INCOMPLETE` (0/23 cases). Gate BLOCKED.

## 5. Non-actions

No target or system-database access; no configuration change; no package installation; no D2 action; no evidence placement; no custody act; no acceptance; no qualification; no closure.
