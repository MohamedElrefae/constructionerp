# Stage 2 Remediation — Builder Evidence (2026-09-05)

Addresses AI-R technical review + AI-A3 A3-01…A3-08. Stage 1C untouched and intact.

## Checker rewrite (`scripts/check_localization_gates.py`)

- Standards-aware PO parser: msgctxt, msgid_plural, msgstr[n], fuzzy flags, obsolete
  `#~`, escape decoding, malformed-line rejection. Duplicate identity is
  (context, msgid). Arabic nplurals=6 enforced from header; translated plurals need
  all six forms.
- Placeholders: full printf grammar (positional, width, precision, conversions) +
  brace format with `{{`/`}}` escape handling.
- HTML: tag-name + entity parity per target; `<script`/`<iframe`/event-handler
  attributes rejected.
- Unicode/bidi/NUL on decoded values; affix-mirroring (source trailing space is
  mirrored, not flagged).
- Source-equal allowlist `allowlisted_source_equal.txt` (8 technical tokens with
  rationale/provenance); missing file fails closed. AI-A1's 3 natural-language rows
  are NOT allowlisted — filed as `ct_proposed_translation` proposals on test site
  only (Produced→تم الإنتاج, Prevdoc DocType→نوع المستند السابق, Fw: {0}→إعادة توجيه: {0});
  no runtime rows created.
- CSV: exact header, unique (language, source, context, app), full quorum incl
  `a2_approved_at` + timestamp format + version regex + references + reviewer sanity.
- Extraction: 232 source files (dist/tests excluded), 588 wrapped literals; every
  literal must be in Construction catalog or reviewed `vendor_covered.txt`
  (47 entries, audited via `--audit-vendor-coverage`, exit 0).
- 497 genuinely-new + 1 BOQ-Locked strings bulk-cataloged to Construction ar.po
  (empty msgstr) and synced: 498 Pending rows created on test site, 0 drift.
  Catalog is now 706 entries; extraction missing=0.
- JS raw-sink gate found 1 real defect (`boq_header.js:424` unwrapped msgprint) —
  FIXED (wrapped + cataloged). Python `frappe.throw` stays a documented skip
  (backend-error convention).
- Vendor baseline + localization manifest with `--update-baselines` (reviewed op);
  vendor deltas fail until re-triaged and re-recorded.
- `--files`: traversal rejected, unhandled relevant paths fail, empty set fails,
  deletions reported as SKIP, non-localizable suffixes reported as SKIP.
- Per-call error state (no module-global leakage).
- CI: `linter.yml` step added; `workflow_dispatch` no longer skips the linter job.

## Adversarial tests (`construction/tests/test_localization_gates.py`)

15 tests, pass standalone (`python3 construction/tests/...`) and via bench
(15/15 OK): parser fixtures (multiline escapes, msgctxt identity, plurals,
fuzzy, obsolete, malformed), printf variants, unsafe HTML, bidi, allowlist
fail-closed, traversal rejection, empty-set, per-call state.

## Durable inventory

`construction/data/localization/stage2_inventory_manifest.json`: exact SQL
predicates, per-app categories, PO hashes, site/commit envelope, UTC timestamp,
reconciliation note (Pending 7321 vs empty 7322 = one legacy-status empty row;
17850 vs 17848 = 2 Deprecated grouped separately).

## Raw logs

`evidence/raw-logs/stage2/`: full gate, scoped gate, vendor audit, 15 gate tests,
sync output — each with command, UTC stamps, exit code.

## Round 2 (2026-09-05) — AI-R rerun findings closed

1. **CI reproducibility**: `linter.yml` checks out pinned Frappe/ERPNext siblings
   (`81aadb9…`, `2807c9f…`, sparse locale-only) into bench layout; checker pins vendor
   commits and fails on any HEAD drift with triage instructions. Absent trees fail
   (no green skip). `workflow_dispatch` fixed.
2. **Extraction**: wrapped-call scan extended to `.html`/`.vue` + multiline calls;
   JSON UI-label scan (workspace/sidebar/print labels; fixtures/CSS/markup/code
   excluded with explicit SKIP notices); 3 dynamic `_(f"…")` calls refactored to
   static templates; remaining dynamics fail closed. 591 wrapped + JSON labels,
   0 missing; catalog 720 entries.
3. **Vendor delta**: `scripts/vendor_upgrade_delta.py` emits add/remove/changed
   (self-delta 0/0/0 verified); baseline pins commits; any move fails until delta
   triaged and re-recorded.
4. **Freshness contract**: `construction/localization_freshness.py` collects
   authenticated evidence (input hashes, packaged rows=34, runtime_digest,
   critical 6/6, health) on the authorized site; manifest v2 binds inputs and
   fails on stale/missing/critical-fail/drift. Saved artifact + raw log.
5. **Quorum binding**: `decision_ref` column (legacy→sign-off-1.0.md, six new→AI
   review files); checker verifies existence; timestamps must parse (parallel-review
   chronology carries no semantics — ordering rule removed with rationale).
   Payload hash now `5b5da75f…`; dry-run 34 skipped/0 drift (new column runtime-inert).
6. **Routing**: absent/deleted paths fail unless in `retired_sources.txt`;
   unhandled relevant paths fail; JSON coverage runs in scoped mode too.
7. **Inventory**: manifest carries merkle root `8d3701f7…` (18,361 rows) + exact
   query; narrative refreshed (construction 742 = 729 catalog + 13 runtime).
8. **Tests**: 30 adversarial tests (full `check_po`, plurals, HTML attrs, CSV
   quorum/dup/timestamps/decision-ref/header, extraction, dynamic, vendor-absent,
   JSON-invalid, traversal, absent-file, per-call state) pass standalone + bench.

## Round 3 (2026-09-05) — AI-R round-2 items closed

1. **Routing overwrite removed** (`SOURCE_SUFFIXES` single definition incl html/vue);
   `.json` UI sources get their own `json_sources` bucket with label-coverage in
   both full and scoped modes; counts now report `wrapped=591, json_labels=21`
   separately for exact reconciliation.
2. **Vendor delta**: `classify_delta` split add/remove/changed/**context_shift**
   (same msgid, moved contexts); `--update-baselines` refuses vendor-commit moves
   without `--delta-reviewed <file>` carrying `triage_status=reviewed` + disposition
   for the exact old→new transition.
3. **Manifest binding**: manifest pins `freshness_sha`, `runtime_digest`,
   `packaged_rows`, exact `critical` mappings, `site`; checker validates all +
   30-day evidence age. Freshness re-collected per CSV change; runtime digest
   stable (`ce8e729f…`) proving metadata-only evolution.
4. **Decision binding**: `decision_ref` schemes `content:` (file must contain the
   exact source+Arabic — edits auto-invalidate) and `legacy:` (historical batch,
   explicitly weaker). Six new rows bind to the three AI review files; 23 legacy
   rows grandfathered as `legacy:` + sign-off doc.
5. **Retired paths**: `retired_sources.txt` requires `path|reason|reviewer|date|evidence`
   with existing evidence; absent/unknown paths fail closed.
6. **Tests**: 40 adversarial (html/vue routing, workspace JSON routing, delta
   classifier incl shift, content binding, retired schema, manifest fields,
   dynamic detection, vendor-absent); mid-file `unittest.main()` moved to EOF so
   all collect; unclosed-file warning fixed.
7. **Envelopes**: `final-dryrun.txt` records current payload `037e79c2…`
   (34/0/0/0); sync/merkle/freshness logs carry command/UTC/exit; inventory
   manifest regenerated by one deterministic command (merkle `8d3701f7…`, 18,361).

## Round 4 (2026-09-05) — AI-R round-3 items closed

1. **Raw visible-text gate**: Jinja/HTML text-node extraction over
   `construction/templates/**` (+ `{{ _( ) }}` wrapping in 5 files incl the
   JSON-embedded BOQ print HTML: 21 print labels); demo/marketing pages
   (theme_test_lab, vite_preview, www/) excluded with documented rationale.
   Python `frappe.throw/msgprint` literals must be wrapped or dispositioned;
   ~40 backend messages wrapped (f-strings → static templates + `.format`),
   service/migration diagnostics dispositioned with rationale (translation-service
   internals untouched per plan §0.3). New `no-underscore-import` rule caught and
   fixed 7 latent missing imports (incl a real stabilization-test failure from
   `overrides/translation.py`). Current: `raw_text 7/0/2`, py-sinks 0.
2. **Vendor governance**: `classify_delta` split; `--update-baselines` refuses
   commit moves without `--delta-reviewed` (triage_status=reviewed + disposition
   for the exact transition); same-commit content changes also gated via manifest
   staleness. Sensitive-file wraps reverted (service/patches keep dispositions).
3. **Decision binding**: `content:` refs require exact source+Arabic presence
   (edits auto-invalidate); `legacy:` migrated to hash-pinned
   `legacy_batch_decisions.json` (doc sha + 28-row roll). Freshness binds
   classified site (`site_classification.json`: v16.localhost non-production test),
   future-date rejection, full health invariants, and critical-vs-policy map
   (`critical_labels.json`).
4. **Retired**: `path|reason|reviewer|date|evidence` schema + evidence existence
   enforced; absent/unknown paths fail closed.
5. **Tests/envelopes**: 51 adversarial green standalone + bench; positive scoped
   run (exit 0); 86-test aggregate log; dry-run/freshness/merkle/sync/lint logs
   all carry command/UTC/exit (+ hashes); inventory manifest regenerated by one
   command (merkle `f10945e1…`, 18,408 rows, construction 789).

## Round 5 (2026-09-05) — AI-R round-4 items closed

1. **Raw sinks**: Jinja text-node gate over `construction/templates/**` (5 files
   wrapped incl JSON-embedded BOQ HTML; demo/marketing excluded with rationale);
   Python throw/msgprint literals wrapped (f-strings → static templates) or
   dispositioned; variable sinks (`message`, `error_message`) verified at
   construction or dispositioned with provenance; service/migration internals
   untouched per plan §0.3 (dispositions, not translation); new
   `no-underscore-import` rule fixed 7 latent missing imports incl a real
   stabilization failure. Multiline calls, `frappe.confirm`, f-string dynamics
   covered. Current: raw 7/0/2, py-sinks 0.
2. **Vendor governance**: `classify_delta` incl `context_shift`; baseline writes
   require `--delta-reviewed` with recomputed-set equality + per-item dispositions
   + delta hash binding; same-commit content moves equally gated (reproduced
   bypass now refused).
3. **Decision binding**: `release_decisions.json` pins canonical row identities
   (language|app|context|source|arabic|reviewers|timestamps|version|artifact shas);
   any row/artifact edit invalidates. Legacy 28 rows migrated to hash-pinned batch
   record (recount corrected: 34 − 6 = 28). `content:` refs require exact
   source+Arabic presence.
4. **Freshness**: classified site (non-production test), future-date rejection,
   full health invariants, critical-vs-policy map; runtime digest stable.
5. **Retired**: 7-field lifecycle schema (event/old/new/reason/reviewer/date/
   evidence#sha) with date/evidence/rename/uniqueness validation.
6. **Tests/envelopes**: 54 adversarial green both ways (incl invalidation, rename
   lifecycle, delta refusal, routing); positive scoped run; 89-test aggregate
   green; 10 enveloped logs (command/UTC/exit/hashes); inventory regenerated
   (merkle `7f15e19e…`, 18,455 rows, construction 792).

Current live counts (2026-09-05): catalog 770 identities; wrapped 630 + JSON
labels 21, 0 missing; raw templates 7 files / 2 texts (brand-dispositioned), 0
missing; Python sinks 0 open; CSV 34 rows; payload `037e79c2…`; PO `eec4078f…`;
manifest `9bd8af82…`; decisions `b1e0c46a…`; checker `d821af10…`.

## Round 6 (2026-09-05) — AI-R round-5 items closed

1. **Vendor inventory binding**: committed `vendor_msgids_{frappe,erpnext}.txt`
   (context/msgid/translation-hash16, ~750KB generated versioned data). Baseline
   compares live candidate bytes against the committed inventory: any add/remove/
   translation change fails until a reviewed delta exactly matching the recomputed
   diff (with per-item dispositions, hash-bound) is supplied. Same-commit/dirty
   trees fully covered; `update_baselines` refuses without it (reproduced bypass
   now refused; negative test uses an isolated tmp root and never touches the
   checkout — the prior stateful test was replaced).
2. **AST sink analysis**: `ast_sink_findings` classifies throw/msgprint args
   (static/dynamic), resolves `_()`/`__()`/`frappe._()`/import-alias chains and
   `.format()` wrappers, detects aliases, multiline literals (AI-R repro caught),
   f-strings, concatenation, variables, subscripts. Variable sinks require
   `path :: var` dispositions with verified provenance; `str(e)` rethrow is a
   documented sink-shape rule. All service/migration internals untouched.
3. **Retired lifecycle**: 7-field schema with delete (`-`)/rename (must exist)
   semantics, date/future validation, mandatory evidence `#sha256` pin option,
   uniqueness; valid/invalid/rename flows tested.
4. **Decision/freshness**: row-identity pins enforced; legacy recount fixed
   (34 − 6 = 28); site classification + future rejection + full health + critical
   policy all enforced and passing.
5. **Tests/envelopes**: 61 adversarial green both ways; positive scoped run;
   96-test aggregate green (13+6+5+3+8+61); 10 enveloped logs with command/UTC/
   exit/hashes; inventory regenerated (merkle `b4cda993…`, 18,412 rows,
   construction 793).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; manifest/freshness current.

## Round 7 (2026-09-05) — AI-R round-6 items closed

1. **Hermetic tests**: all vendor/baseline functions take explicit `root`
   (no def-time ROOT defaults); same-commit fixture rebuilt at the true bench
   topology (`tmp/bench/apps/{construction,frappe,erpnext}`); refusal reasons
   flow into the errors list; the stateful live-writer test was replaced with a
   tmp-root refusal test asserting exact reason + byte-identical baseline.
2. **Canonical delta**: producer and consumer share `canonical_delta_sets`
   (list-pair add/remove/changed + dict context_shift); consumer recomputes from
   committed inventory vs candidate bytes; per-item dispositions required.
3. **AST aliases**: `import frappe as f`, `from frappe import throw/_ as x`,
   `f = frappe` chains all resolve (fixtures proven); `frappe._()` chains skip.
4. **Retired**: delete requires absence + `new_path -`; rename requires old
   absent + new exists/retired; evidence `#sha256` pin mandatory and verified;
   order-independent two-pass validation; rename/delete flows tested.
5. **Decisions**: `record_release_decisions.py` (committed recorder) builds v2
   records with verdicts/proposal/artifact hashes; manifest pins `decisions_sha`
   + `decision_root`; checker validates objects, verdicts, proposal, artifacts,
   and root. Legacy recount fixed (34 − 6 = 28).
6. **Freshness**: strict non-future, site-classification hash bound,
   `packaged_rows` == CSV Released count, constraint-name + drift-timestamp
   enforced, critical-vs-policy map enforced.
7. **Merkle determinism**: ORDER BY all five columns committed in
   `scripts/stage2_inventory.sql`; root `6848f2ed…` (18,412 rows) reproducible.
8. **Envelopes**: exactly 10 files, each with command/UTC/exit/hashes
   (freshness embedded with artifact hash; merkle carries full manifest hash).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 63 adversarial green both ways;
98-test aggregate green (13+6+5+3+8+63).

## Round 8 (2026-09-05) — AI-R round-7 items closed

1. **Hermetic roots**: every vendor/baseline/inventory function takes an explicit
   `root` (no def-time ROOT defaults); `--root=` flag on update path; refusal
   reasons flow into the errors list; same-commit and refusal fixtures use the
   true `tmp/bench/apps/{construction,frappe,erpnext}` topology with zero
   checkout writes (proven: governed artifacts byte-identical across suites).
2. **Canonical delta**: producer and consumer share `canonical_delta_sets`;
   consumer `want` is built from the recomputed shift (forged omission refused —
   permanent hermetic test); per-item dispositions required; delta hash bound.
3. **AST aliases**: `import frappe as f`, `from frappe import throw/_ as x`,
   `f = frappe` chains all resolve (fixtures); `frappe._()` chains skip;
   `t = f._` conservatively flagged (documented false-positive residual, not a
   bypass).
4. **Retired**: delete requires absence + `-`; rename requires old absent + new
   live/retired; evidence `#sha256` mandatory and verified; order-independent
   two-pass validation; rename/delete flows tested.
5. **Decisions**: `record_release_decisions.py` (committed recorder) builds v2
   records with verdicts/proposal/artifact hashes; manifest pins `decisions_sha`
   + object-based `decision_root`; checker validates objects, verdicts, proposal,
   artifacts, and root; mutation tests per field.
6. **Freshness**: strict non-future, site-classification hash bound,
   `production_mutation_authorized=false` enforced, `packaged_rows` reconciled to
   CSV Released count, constraint-name + drift-timestamp enforced, critical map
   enforced.
7. **Merkle determinism**: committed `localization_inventory.merkle_root`
   (str-normalize + Python full-tuple sort + JSON, never repr/DB-order);
   `scripts/stage2_inventory.sql` committed; root `973b8faccbc1…` (18,412 rows).
8. **Envelopes**: exactly 10 files, each with command/UTC/exit/result+artifact
   hashes (freshness embedded with artifact hash; merkle carries manifest hash).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 67 adversarial green both ways;
102-test aggregate green (13+6+5+3+8+67).

## Round 9 (2026-09-05) — AI-R round-8 items closed

1. **Root isolation**: explicit `root` through `check_vendor_baseline`,
   `update_baselines`, `live_msgid_inventory`, `audit_vendor_coverage`, and
   `vendor_upgrade_delta.blob`; delta provenance (`old/new/old_po_sha/new_po_sha`)
   validated against recorded→live before any set comparison; forged-provenance
   fixture refused with reason; no-write assertions on tmp roots.
2. **Canonical delta**: producer and consumer share `canonical_delta_sets`;
   consumer `want` built from recomputed shift only; permanent forged-omission
   and forged-provenance hermetic tests.
3. **AST aliases**: `import frappe as f`, `from frappe import throw/_ as x`,
   `f = frappe` chains proven by fixture; `frappe._()` skips; `t = f._`
   conservatively flagged (documented, not a bypass).
4. **Retired**: versioned `retired-lifecycle/v3` marker enforced; delete requires
   absence + `-`; rename requires old absent + new live/retired; evidence
   `#sha256` mandatory and verified; order-independent two-pass; replacement
   explicitly out of scope (model as delete+rename pair).
5. **Decisions**: `record_release_decisions.py` builds v2 records with
   verdicts/proposal/artifact hashes; manifest pins `decisions_sha` + object
   `decision_root`; checker validates objects, verdicts, proposal, artifacts,
   root; per-field mutation tests.
6. **Freshness**: strict non-future, site-classification hash bound,
   `production_mutation_authorized=false` enforced, `packaged_rows` reconciled to
   CSV Released count, constraint-name + all three audit timestamps enforced,
   critical-vs-policy map enforced.
7. **Merkle**: committed serializer (str-normalize + Python full-tuple sort +
   JSON) with committed SQL; root `973b8faccbc1…` (18,412 rows) independently
   reproducible; manifest binds inventory SHA + root.
8. **Envelopes**: exactly 10 files, each with command/UTC/exit/result+artifact
   hashes; governed set enumerated here.

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 68 adversarial green both ways;
103-test aggregate green (13+6+5+3+8+68).

## Round 10 (2026-09-05) — AI-R round-9 items closed

1. **Root isolation**: explicit `root` through every vendor function
   (baseline reads, candidate PO reads/hashes, inventories, commits, audit,
   delta CLI `--root`, temp parse files via TMPDIR); `audit_vendor_coverage`
   reads the candidate allowlist under root (cross-root leak proven fixed by
   fixture); full/scoped scans thread root end to end.
2. **Provenance**: delta `old/new/old_po_sha/new_po_sha` validated against
   recorded→live before set comparison; forged-provenance fixture refused;
   schema requires all provenance fields.
3. **Retired**: versioned `retired-lifecycle/v3` marker enforced; future dates
   strictly rejected (tomorrow fixture refused); evidence `#sha256` mandatory
   and verified; delete/rename absence semantics tested.
4. **Freshness**: audit timestamps get age/future/consistency bounds plus
   agreement with the audit map; end-to-end manifest-gate tests on mutated
   disposable artifacts (future + critical tamper refused); `ResourceWarning`
   closed via context-managed CSV read; collector emits single health call +
   DB NOW anchor (multi-hour DB/app skew documented with budget).
5. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding all
   ten SHAs and 8 artifact SHAs; merkle carries full manifest hash; SQL
   `repr(rows)` comment corrected to the JSON serializer.

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 70 adversarial green both ways;
105-test aggregate green (13+6+5+3+8+70).

## Round 11 (2026-09-05) — AI-R round-10 items closed

1. **Root isolation**: explicit `root` through `audit_vendor_coverage`,
   `update_baselines`, all vendor/inventory/commit/hash helpers, scans, loaders,
   and `vendor_upgrade_delta` (blob hashes, po-sha loop, `--write` path, temp
   files via TMPDIR); `main()` accepts `--root=`; cross-root CLI fixture asserts
   isolated hashes/output plus checkout byte-identity.
2. **Evidence index validator**: `check_evidence_index` enforces the exact 10-file
   set (missing/extra/duplicate/traversal rejected), per-file command/UTC/exit +
   full-SHA + length envelopes, merkle root/manifest binding, and index↔file hash
   agreement; wired into the full scan.
3. **Redis**: cache/queue instances restarted; 105-test aggregate green.
4. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding all
   ten SHAs and 8 artifact SHAs (freshness embedded with artifact hash; merkle
   carries manifest hash + root + row count).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 71 adversarial green both ways;
105-test aggregate green (13+6+5+3+8+71).

## Round 12 (2026-09-05) — AI-R round-11 items closed

1. **Root isolation completed**: explicit `root` through audit covered-file reads,
   delta CLI (blob hashes, po-sha loop, `--write` path, root-owned temp dirs via
   TMPDIR-safe mkdtemp under root), all scan/load helpers, and manifest paths;
   cross-root CLI fixture asserts isolated hashes/output plus checkout
   byte-identity.
2. **Evidence index validator**: exact 10-file set, per-file command/UTC/exit +
   full-SHA + length envelopes, merkle root/manifest binding, index↔file hash
   agreement, traversal/duplicate detection; wired into the full scan.
3. **Rebuilt checker**: after a destructive edit clobbered the script, it was
   rebuilt cleanly in parts and re-validated against the full 71-test contract
   (all green) plus the live gate.
4. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding all
   SHAs; aggregate corrected to 106 (13+6+5+3+8+71).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 71 adversarial green both ways;
106-test aggregate green (13+6+5+3+8+71).

## Round 13 (2026-09-05) — AI-R round-12 items closed

1. **Root isolation completed**: explicit `root` through audit covered-file reads,
   delta CLI (blob hashes, po-sha loop, `--write` path, root-owned temp dirs),
   all scan/load helpers, and manifest paths; cross-root CLI fixture asserts
   isolated hashes/output plus checkout byte-identity.
2. **Evidence index validator**: exact 10-file set, per-file command/UTC/exit +
   full-SHA + length envelopes, merkle root/manifest binding, index↔file hash
   agreement, traversal/duplicate detection; two-phase bootstrap (`--skip-evidence`
   for envelope generation only, documented in the envelope; CI/verification
   never skip) resolves the index/gate circularity.
3. **Rebuilt checker**: after a destructive edit clobbered the script, it was
   rebuilt cleanly and re-validated against the full 79-test contract (all
   green) plus the live gate.
4. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding all
   SHAs; aggregate corrected to 114 (13+6+5+3+8+79).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 79 adversarial green both ways;
114-test aggregate green (13+6+5+3+8+79).

## Round 14 (2026-09-05) — AI-R round-13 items closed

1. **Strict evidence contract**: exact index grammar (hash rows, CANDIDATE_HEAD,
   envelope markers, artifact SHAs; everything else rejected); exact per-file
   COMMAND identity; ordered markers with single EXIT_CODE: 0; strict UTC parse
   and order; ENVELOPE_LINES agreement; failure-text rejection; per-envelope
   semantic schemas (module identities/counts/arithmetic, gate result object,
   dry-run arithmetic, merkle bindings, zero-create sync); index/file hash
   agreement with duplicate/traversal detection; CANDIDATE_HEAD bound to live
   git HEAD.
2. **Adversarial evidence tests**: coherent totals forgery, hidden failure text,
   arbitrary command, junk index line, length marker, duplicate index/content,
   traversal, nonzero exit, bad UTC, arithmetic — all refused; valid set passes.
3. **Two-phase bootstrap documented**: `--skip-evidence` envelope generation
   only (recorded in the envelope); CI/verification run full validation.
4. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding ten
   SHAs, 8 artifact SHAs, and candidate HEAD.

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 87 adversarial green both ways;
122-test aggregate green (13+6+5+3+8+87).

## Round 15 (2026-09-05) — AI-R round-14 items closed

1. **Exact evidence contract**: index grammar accepts only hash rows,
   CANDIDATE_HEAD, envelope markers, and artifact SHAs (everything else
   rejected); exact per-file COMMAND identity; ordered single markers;
   EXIT_CODE 0; strict UTC parse/order/recency; ENVELOPE_LINES agreement;
   general failure-text rejection; per-envelope semantic schemas (module
   identities/counts/arithmetic, gate result object, dry-run arithmetic,
   merkle bindings, zero-create sync); index↔file hash agreement with
   duplicate/traversal detection; CANDIDATE_HEAD bound to live git HEAD
   (fail closed when unresolvable).
2. **Artifact recomputation**: every `*_SHA256` marker in index and envelopes
   is recomputed from the candidate and must agree everywhere it appears;
   disambiguated manifest markers (`MANIFEST_SHA256` = localization manifest,
   `INVENTORY_MANIFEST_SHA256` = inventory manifest).
3. **Adversarial evidence tests**: coherent totals forgery, hidden failure text,
   arbitrary command, junk index line, length marker, duplicate index/content,
   traversal, nonzero exit, bad UTC/order, arithmetic — all refused; valid set
   passes (fixtures use contract commands and real artifact SHAs).
4. **Envelopes**: 10 content-hash envelopes + governed `index.txt` binding ten
   SHAs, 8 artifact SHAs, and candidate HEAD.

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 87 adversarial green both ways;
122-test aggregate green (13+6+5+3+8+87).

## Round 16 (2026-09-05) — AI-R round-15 items closed

1. **Exact versioned index**: `INDEX_VERSION: 1` first line enforced; every other
   line must be a hash row, CANDIDATE_HEAD, envelope marker, or artifact SHA
   (all else rejected); exactly one HEAD required and bound to live git HEAD
   (fail closed when unresolvable); candidate root must be an
   `apps/construction` layout containing the governed artifacts.
2. **Artifact recomputation everywhere**: 14 canonical markers
   (checker/tests/PO/payload/manifests/baseline/decisions/inventory/freshness/
   SQL/both lints/both vendor POs) recomputed from the candidate wherever they
   appear (envelopes and index); manifest-marker collision fixed by exact
   anchored matching.
3. **Ten semantic schemas**: module identities/counts/arithmetic, gate result
   object, dry-run arithmetic, standalone count+OK, scoped/vendor errors=0,
   lint marks, freshness critical pass, sync zero creates/updates, merkle
   root/rows/manifest with live cross-check.
4. **Failure-text/UTC/order**: general failure spellings rejected (with
   failed=0/errors=0 carve-outs); strict UTC parse, start≤finish, 30-day
   recency, non-future; duplicate content/index rows and traversal rejected.
5. **Adversarial tests**: coherent totals forgery, hidden failure, arbitrary
   command, junk index, length marker, duplicate index/content, traversal,
   nonzero exit, bad UTC/order, arithmetic — all refused; valid set passes
   (fixtures use contract commands and real artifact SHAs).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 87 adversarial green both ways;
122-test aggregate green (13+6+5+3+8+87).

## Round 17 (2026-09-05) — AI-R round-16 items closed

1. **Exact ordered index schema**: `INDEX_VERSION: 1` first line; canonical line
   order (own COMMAND/STARTED_UTC, ten envelope hash rows in `EVIDENCE_FILES`
   order, EXIT_CODE/FINISHED_UTC, one CANDIDATE_HEAD, one CANDIDATE_ROOT bound
   to the invocation root, `ARTIFACTS:`, fourteen artifact rows in
   `ARTIFACT_PATHS` order, ENVELOPE_LINES) — any other grammar rejected.
2. **Marker disambiguation**: `MANIFEST_SHA256` = localization manifest,
   `INVENTORY_MANIFEST_SHA256` = stage2 inventory manifest, `TESTS_SHA256`
   replaces the inconsistent `TESTFILE_SHA256`; all fourteen markers recomputed
   from the candidate wherever they appear; every marker must be bound in at
   least one envelope and agree everywhere.
3. **Per-envelope ordered templates**: every result line consumed exactly once
   against an ordered per-envelope schema (module identities/counts +
   aggregate arithmetic, gate result object + file count, dry-run arithmetic,
   standalone count + OK, scoped/vendor errors=0, lint marks, freshness
   critical pass with embedded JSON parse, zero-create sync, merkle
   root/rows/manifest live cross-check with SQL binding); embedded JSON blocks
   skipped by markers, not consumed as result lines.
4. **Failure/UTC/order enforcement**: failure spellings rejected (with
   `failed=0`/`errors=0` carve-outs); strict UTC parse, start<=finish,
   non-future, 30-day recency, atomic-window check (all envelopes within one
   day), index generated after the latest envelope finish.
5. **Bootstrap gating**: `--skip-evidence` requires `STAGE2_EVIDENCE_BOOTSTRAP=1`
   (builder may not self-approve; CI and verification never pass this flag).
6. **Hermetic fixtures on the live contract**: adversarial tests build evidence
   trees from the contract commands and real artifact SHAs; valid set passes,
   forged totals/failures/commands/duplicates/traversal/nonzero-exit/bad
   UTC/order/arithmetic all refused (87 tests green).
7. **Evidence regenerated from live captures**: all ten envelopes + governed
   `index.txt` rebuilt from actual command runs (standalone 87 OK; 122-test
   aggregate 13+6+5+3+8+87 all OK; sync zero-create; dry-run 34/0/0/34/0;
   freshness critical_pass with runtime digest `ce8e729f…`; merkle root
   `973b8fac…` over 18,412 rows live-matching the committed inventory manifest;
   scoped gate errors=0; vendor audit errors=0; full gate errors=0; lints +
   diffcheck clean) with true UTC timestamps, true `ENVELOPE_LINES` counts,
   `--update-baselines` rebinding `freshness_sha` (`9206c227…`) before capture.

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 87 adversarial green both ways;
122-test aggregate green (13+6+5+3+8+87); full gate with evidence ON: errors=0.

## Round 18 (2026-09-05) — AI-R round-18 P0 items closed

1. **Governed-index length binding**: the single `ENVELOPE_LINES` row is parsed
   and must equal the actual nonempty index line count; missing/duplicate/bad
   values are rejected (`evidence-index-length`).
2. **Governed-index artifact-value binding**: every one of the fourteen ordered
   index artifact rows is parsed, required exactly once, and recomputed from
   the candidate — index values, envelope occurrences, and candidate bytes must
   all agree (`evidence-index-artifact-value`; unknown markers rejected via
   `evidence-index-artifact-alias`; absent rows fail closed). A good envelope
   value can no longer decoy a forged governed-index value.
3. **Permanent adversarial coverage**: two new coherent-forgery tests —
   false index `ENVELOPE_LINES: 999` and arbitrary index `CHECKER_SHA256` of
   64 zeroes — both rejected (suite now 89 tests; aggregate 124 =
   13+6+5+3+8+89); existing aggregate/coherent-total tests made contract-
   dynamic instead of hard-coded.
4. **Evidence regenerated from the fixed candidate**: all ten envelopes +
   governed index rebuilt from live captures (standalone 89 OK; aggregate 124
   OK; sync zero-create; dry-run 34/0/0/34/0; freshness `critical_pass` with
   rebinding via `--update-baselines`; merkle `973b8fac…`/18,412 live-matched;
   scoped/vendor/full gates `errors=0`; lints + diffcheck clean).

Current live counts: catalog 771; wrapped 631 + JSON 21, 0 missing; raw 7/0/2;
Python sinks 0; CSV 34; payload `037e79c2…`; 89 adversarial green both ways;
124-test aggregate green (13+6+5+3+8+89); full gate with evidence ON: errors=0.
