# Stage 2 — Independent AI-R Technical Review

## Verification identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — independent Stage 2 technical verifier |
| Agent/model | OpenAI Codex, GPT-5 family (no more-specific model identifier exposed to this session) |
| Canonical task/session | `/root/stage2_ai_r` |
| Verified at (UTC) | `2026-09-04T21:22:06Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; disclosed changes remain uncommitted |
| Authority | Read-only verification plus creation of this review record only. No code, catalog, payload, database/runtime, existing evidence, Git index/history, commit, push, deployment, or production state was modified. |

## Exact reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Builder implementation record | `c0283cabfb961dd6f726296b0d6160269a271d958225f9038ec153abe7a790d4` |
| Stage 2 inventory | `7f2f4e0a048f438f82f792ea652593eece19c0aaa417e848ed9a87302050b3e4` |
| Stage 1C durability closure | `54ed9554fb2b8f82834598e5213a7aa6c954694497d0c5569754ed1a80dd42d8` |
| Localization checker | `da40bc8b47fb5958d9b59a43d62004286f240cdb74e053337915a069f5c5b697` |
| CI workflow | `adea11bd9f27b27fd9977a3c4a4f96a7313f034da61fe1fcf0013b3bc2b5c0d8` |
| Construction `ar.po` | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |
| Approved override payload | `7ba7902c201e4010ffc30cad068490917b1cea1452faf859eb3020ff101badc0` |
| Egyptian construction glossary JSON | `aefbbf633d432fb93ac63996960bb58d0bd005e973e0e461f4480d7ae46b51b4` |
| Translation QA report JSON | `abd85f3eeef6ebd0d769a754f395949f037864234365e35eba326d0cc027bda2` |

## Independent checks performed

- Read the repository instructions, canonical plan v4, handoff, implementation record, Stage 2 inventory, Stage 1C final closure, checker source, CI workflow, Construction PO, payload headers/content, and data JSON inventory.
- Ran `python3 scripts/check_localization_gates.py`: exit 0, `checked=4`, `errors=0`.
- Ran `python3 -m py_compile scripts/check_localization_gates.py`: exit 0.
- Ran `git diff --check`: exit 0 before this evidence file was created.
- Verified the Frappe and ERPNext vendor Arabic PO paths are clean in their respective repositories (`git diff --quiet`, exit 0 for each). The only PO change in the Construction repository is the Construction-owned `Typography Settings` entry.
- Queried `tabTranslation` read-only on `v16.localhost`. The live database independently reproduces: 15,172 app-attributed catalog rows (5,927 Frappe, 9,014 ERPNext, 231 Construction), 2,678 unattributed legacy rows, 7,322 rows whose PO/display value is empty, 7,780 non-empty legacy-`Approved` rows, 11 source-equal rows, 49 `Released` rows, and 2 `Deprecated` rows. The inventory's 7,321 `Pending` count is also consistent: one of the 7,322 empty rows has a legacy state other than `Pending`.
- Confirmed the current full scan discovers four owned inputs: Construction PO, approved payload CSV, glossary JSON, and QA-report JSON.
- Exercised changed-file mode. `--files docs/random.csv` checked the canonical approved payload rather than the named file; `--files README.md` checked zero files and returned success.
- Probed placeholder parsing directly. `%1$s`, `%2$d`, and `%.2f` were not recognized, while brace placeholders were recognized. Inspected PO parsing and CI control flow for plural/context/multiline/path behavior.

## Findings

### Critical — Stage 2 gate is not implemented by the CI checker

The canonical Stage 2 release gate says new Construction visible strings and vendor upgrade deltas cannot bypass triage; plan F2 explicitly requires hardcoded visible-string checks and rejection of Construction msgids without Arabic or a filed proposal. The checker scans only `construction/locale/ar.po`, the released payload CSV, and JSON under `construction/data`. It does not extract or scan Python, JavaScript, templates, workspaces, reports, print/email sources, or compare extracted msgids to catalog/proposal state. A new unwrapped visible string—or a wrapped but untranslated Construction string—therefore passes CI. It also never analyzes Frappe/ERPNext upgrade deltas. The Stage 2 release gate is materially false-negative and cannot be marked complete.

### High — Multiple mandatory F2/handoff checks are absent

The implementation does not check:

- HTML/tag parity or unsafe translated markup;
- plural-form presence/parity;
- missing context for the maintained ambiguity list;
- `.mo` or equivalent runtime-artifact/source-hash freshness;
- released payload versus live/package drift and duplicate identity;
- upgrade additions, removals, or context shifts;
- active bilingual-registry fields against schema, or registered form language/search tests (when the registry exists).

The script docstring and Stage 2 evidence describe a narrower set, but the canonical plan and handoff are authoritative. Deferring these without an explicit, reviewed plan amendment does not satisfy Stage 2.

### High — Changed-file mode does not check the files supplied

Any supplied `.csv` causes the fixed canonical payload to be checked, and any supplied PO under a matching-looking path causes the fixed canonical Construction PO to be checked. Unsupported changed files are silently discarded; a run over only `README.md` reports `checked=0 ... errors=0`. Consequently the mode can produce a green result while the named changed artifact was never read. It also has no changed-source-to-extraction/catalog routing, so it is not a safe changed-file-aware localization gate. Inputs should be normalized, constrained to repository paths, classified explicitly, and either checked as named or rejected/declared skipped under a documented policy; a relevant changed source must trigger extraction/delta validation.

### High — PO parsing is not standards-compliant and creates future false results

`parse_po` is an ad-hoc line parser. It does not parse `msgctxt`, `msgid_plural`, `msgstr[n]`, flags/fuzzy/obsolete state, or escaped PO strings according to gettext syntax. Context-distinct equal msgids would be reported as duplicates, plural translations are ignored, and malformed PO syntax is not rejected. The repository declares six Arabic plural forms, making plural handling a required gate rather than an optional enhancement. Use a proven gettext parser/tool (or rigorously tested equivalent) and define duplicate identity as context plus msgid, with plural semantics.

### High — Placeholder coverage is incomplete

`PLACEHOLDER_RE` misses common printf forms including positional (`%1$s`), precision/width (`%.2f`, `%02d`), and other conversion types; it also treats every `{...}` as a placeholder without validating Python/JS format grammar. This yields both false negatives and false positives. Placeholder parity must support the formats emitted by the three applications and be backed by adversarial fixtures.

### Medium — CSV structural, uniqueness, and quorum validation is incomplete

The CSV reader does not require an exact schema or reject duplicate `(language, source_text, context, ct_app)` identities. A malformed/empty-header CSV can pass if it contains no qualifying rows. Released quorum checks omit `a2_approved_at`, do not validate timestamps, release version, decision values, references/evidence, reviewer/session identity, or placeholder identities. This is weaker than plan B2/B3 and permits structurally unreviewed release metadata to pass.

### Medium — JSON validation is only a raw-text control-character scan

`check_json` never parses JSON, validates schema, traverses translated values, checks source/target placeholders or affixes, or enforces registry rules. Invalid JSON without a banned bidi/NUL character passes this localization gate (although another general linter might fail independently). Bidi rejection is conservative and useful, but it is not the full JSON gate claimed by the plan.

### Medium — Affix and Unicode checks are too coarse

Affix matching uses Python whitespace stripping on decoded CSV values but undecoded PO lexical fragments. It cannot reliably distinguish intentional layout whitespace/escapes from corruption. Unicode checks ban selected bidi controls and literal NUL only; they do not validate normalization, unpaired-surrogate/escape behavior, malformed encoding beyond the decoder, or unsafe invisible characters described by the broader plan. Tests should define the accepted Unicode policy and check parsed values consistently.

### Medium — Inventory evidence is not durable/reproducible enough

The headline counts are independently reproducible now, but `stage-2-inventory.md` records neither the exact query/script, target-site identity/commit envelope, UTC start/finish, exit code, raw output, nor current PO/catalog hashes. It also says “counts + PO hashes in stage-0,” although Stage 0 hashes describe older catalogs and different totals. No Stage 2 raw logs or automated checker tests were filed. This weakens later auditability and makes category definitions (notably Pending versus empty and Approved versus populated-unreviewed) implicit.

### Low — CI trigger semantics are confusing but not presently bypassing pull requests

The localization check is correctly placed in the pull-request linter job and will run as a full scan for PRs. However, the job-level `if: github.event_name == 'pull_request'` means the declared `workflow_dispatch` event skips the entire linter job. Either remove the dispatch trigger or allow a manual full-scan run. CI also currently calls only full-scan mode, so the advertised changed-file mode is not exercised there.

### Low — Module-global error state impairs reusable/test invocation

`ERRORS` is module-global and is not reset by `main`. A future unit test or in-process caller invoking `main` more than once inherits prior failures. Return a result object or initialize state per invocation.

## Positive findings

- The live inventory's principal counts and classifications are arithmetically reproducible once their implicit predicates are reconstructed.
- The checker is deterministic in target ordering for the current full scan, stdlib-only, syntax-valid on Python 3.10-compatible syntax, and fail-closes on missing full-scan owned files.
- Literal NUL and the selected bidi controls are rejected in scanned values/text.
- Basic `{...}`, named-percent, and simple `%s/%d/%f` placeholder parity works for non-empty PO/CSV targets.
- Construction-owned vendor override policy is respected: no Frappe or ERPNext PO edit was found.
- The localization check is wired into the pull-request linter job with read-only repository permissions.
- Stage 1C's durable evidence chain remains intact and is not invalidated by these Stage 2 findings.

## Decision

**BLOCKED — Stage 2 is not technically verified.**

The inventory is substantially correct, and the current checker passes its own narrow implementation. However, a green result does not establish the authoritative Stage 2 gate: new visible Construction strings, missing translations/proposals, and vendor upgrade deltas can bypass triage, while several explicitly required structural and freshness checks are absent. Changed-file and parser behavior add material false-negative risk.

This decision does not invalidate completed Stages 0–1C and does not assess the linguistic waves, which properly remain separate review work.

## Exact next gate

Before Stage 3 begins or Stage 2 is marked complete:

1. Implement source extraction/delta enforcement for Construction-visible Python/JS/JSON/template/workspace/report/print/email strings, including hardcoded-visible-string policy and “Arabic present or proposal filed”; implement a reproducible Frappe/ERPNext upgrade-delta input/report.
2. Implement or explicitly amend the canonical plan for every F2 gate currently absent: HTML, plurals, ambiguity context, runtime artifact/source freshness, packaged/live drift/identity, and later-registry/schema/form gates.
3. Replace the PO parser with standards-compliant gettext parsing and expand placeholder handling to positional, width/precision, brace-format, and application-observed forms.
4. Make `--files` validate the exact normalized repository-relative targets, fail or explicitly report relevant unsupported inputs, and trigger extraction/delta checks for changed visible-source files. Remove repository path traversal capability.
5. Require and validate CSV schema, unique governed identity, complete AI-A1/AI-A2/AI-A3 decision/session/timestamp/evidence fields for Released rows, and parse JSON with schema-aware checks.
6. Add adversarial unit/fixture tests proving each gate fails closed, including malformed PO/JSON/CSV, context duplicates, Arabic plurals, HTML mismatch, placeholder variants, source-equal allowlist, bidi/NUL, missing proposal, changed-file routing, deleted/renamed files, stale artifacts, and upgrade deltas.
7. Save a durable Stage 2 command/query script and `.txt` raw evidence with candidate/hash envelope, target-site declaration, UTC timestamps, exit codes, exact predicates, catalog hashes, inventory output, checker tests, full scan, representative changed-file scan, and CI/YAML validation.
8. Run a fresh independent AI-R review against the exact remediated hashes. Only `VERIFIED` from that rerun opens Stage 3; no commit, push, merge, deployment, or production mutation is authorized by this record.
