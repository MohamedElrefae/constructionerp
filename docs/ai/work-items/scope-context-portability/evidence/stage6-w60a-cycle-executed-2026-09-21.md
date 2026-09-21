# Stage 6 W6-0a — governed cycle executed (test site, 2026-09-21)

Owner approval chain: desk-shell batch cut (362 rows) → reclassification to
348 candidates + placeholders kept eligible → owner approved the
candidate-only quorum cycle (2026-09-21) with the last adjustments
(workspace-guidance row moved to candidates; unmatched-location exceptions
became DEFERRED, not suppressible).

## Cycle gates — executed on the test site only

1. **Scope**: 349 quorum-eligible candidate rows (the workspace row moved
   back by owner instruction); 3 REAL-HTML/blob exceptions decided as
   suppressible WITH hash-pinned location + rationale + AI-R reference;
   10 rows `DEFERRED-unresolved-location` (not suppressible, out of the
   payload until their source contexts are mapped for AI-R).
2. **AI proposals**: every candidate row authored (glossary v2.0 grounded;
   duplicate linkage rows dropped upfront; placeholder parity enforced
   programmatically across all rows; the 4 rows carrying escaped `\"...\\"`
   sources matched exactly).
3. **Payload**: 347 released rows appended (all `ct_app: frappe`,
   `release_version 1.2`; `Add Child` row from the W6-0a draft was dropped
   at DRY time because it would supersede the already-released legacy row
   with the glossary-v2 term — the change is recorded as a future
   terminology-escalation candidate, not silently applied).
4. **Governed importer runs**: DRY first `total=451/created=347/updated=0/
   skipped=104/drift=0`; final idempotent state
   `total=450/created=0/updated=0/skipped=450/drift=0`; zero-drift across
   the cycle; IMPORT executed test-site only (`created=347`, drift 0).
5. **Dispositions recorded**: release_decisions.json — 450 decisions
   (34 legacy batch + 347 W6-0a rows + 69 W6-1 rows), AI-R
   dataset binding intact after all payload changes; decision_root +
   decisions_sha re-recorded in the manifest.
6. **Runtime verification**: live readback of samples (`Add {0}` →
   `إضافة {0}`, `Cancel All` → `إلغاء الكل`, `Duplicate Entry` →
   `مدخل مكرر`, `Invalid Filter` → `عامل تصفية غير صالح`, `Copy Link` →
   `نسخ الرابط`); server ar-dictionary contains the new entries
   (`get_all_translations("ar")` totals 10,752 with the W6-0a rows).
7. **Freshness + manifest + PO catalog**: freshness re-collected (450
   packaged rows, critical_pass), construction/locale/ar.po got the two
   new API strings (catalog 807), construction_po_sha re-recorded; the
   Site-Override friction row ("Edit Sidebar" duplicate) dropped in favor
   of the legacy 1.1 value; the 10 deferred rows stayed out of the
   payload by the owner rule.
8. **Evidence re-pin**: ten durable envelopes + index regenerated as one
   atomic set for the current pre-commit HEAD; contracts updated
   (`EXPECTED_GATE` catalog 807 / files 261 / wrapped 666;
   `EXPECTED_DRYRUN` 450/0/450/0; the round-3 binding test asserts the
   450-row payload); standalone suite 91/91 OK; evidence-inclusive gate
   **exit 0** on the pre-commit HEAD (the documented each-commit HEAD-pin
   staleness applies after this commit until the next catalog event).

## Honest evidence limitation (browser)

The Stage-7 evidence for W6-0a is recorded at *server resolution* level:
the browser `__()` probes in the ar-directed headless session returned
English this time (the v16 desk loads the client translation map through
a path that did not include the new packaged rows in this headless run —
the raw `frappe._dict` came up empty even in an ar session). The same
browser probe did work for W6-1 (after a cache clear) so this is a
test-environment/dictionary-wiring quirk rather than a data defect; the
server-side resolution of these exact strings (console probes + ar
dictionary presence) is verified. Live DOM evidence for W6-0a rows is a
follow-up browser probe (same status as the CoA-tree manual paste — a
devtools check).

## Boundaries honored

- No candidate rows beyond the approved 349+1 (reclassified).
- 14→3 real exceptions only; 10 deferred rows protected (not suppressed).
- No production mutation; temp admin password revoked after the run and
  Administrator language restored to en.
