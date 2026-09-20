# Stage 2 — Independent AI-R Rerun

## Verification identity and boundary

| Field | Value |
|---|---|
| Role | AI-R — independent Stage 2 rerun verifier |
| Agent/session | `/root/stage2_ai_r_rerun` |
| Model | OpenAI Codex, GPT-5 family (exact serving build not exposed) |
| Verified at (UTC) | `2026-09-04T21:33:34Z` |
| Candidate | `feature/erp-arabic-bilingual-data`; `HEAD e7be48855bde540464ea302e53c9bfca62b7c462`; changes remain uncommitted |
| Vendor commits | Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`; ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5` |
| Independence | This agent was not the Builder or either earlier Stage 2 reviewer. It did not modify code, catalogs, payload, database/runtime, Git index/history, or existing evidence. This report is its only write. |

## Exact reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4 | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Implementation record | `ac0369be972c0f5d40d40e20bdb37ffec200871f6d043868213b4b1215499f0a` |
| Stage 2 inventory narrative | `7f2f4e0a048f438f82f792ea652593eece19c0aaa417e848ed9a87302050b3e4` |
| Stage 2 remediation record | `d0f8288ce521e8b66de336680f86e5cf77ccad02dda53c5f4b230a2ffae7dcfe` |
| Prior AI-A3 review | `aab4cb35af0bc627f91ad1900067ff149275ed680b048805fae4a3535ea8d5ca` |
| Prior AI-R review | `5117c94838fd234f1bdc321d0afa93481921ecc55534081e18f9dfccd6a961ba` |
| Stage 1C final closure | `54ed9554fb2b8f82834598e5213a7aa6c954694497d0c5569754ed1a80dd42d8` |
| Localization checker | `ecd500a19057fc5b4773c5f641eeb8a8c44933897d4af7445f5bf73eda2b9d2b` |
| Adversarial tests | `9fa2b68dff2380e652aeff2cfbab00a1e29b532a3b125cbe01938eba23f856e1` |
| CI workflow | `59152947ac8e13aeb1cd557eefa4f734df02b894c465a3929abbac8128e4b461` |
| Construction PO | `3aeb7203711b2ac80b5ab1d71137f04e4f0b9056aad09ea049087097fb8fefe2` |
| Released payload | `7ba7902c201e4010ffc30cad068490917b1cea1452faf859eb3020ff101badc0` |
| Vendor baseline | `642914004eff0c154f274ce205297e7b4d563fd37e54a7d9267f544f8378d60a` |
| Localization manifest | `1a197a8bf0fba3ff1433aacfae5ca53590155e070acf7cea86cf8bd6f47b526a` |
| Stage 2 inventory manifest | `88bce566f2dba6a9d4c517c4650d12145b03f6e3a0bcb176fa3a3b81015479c4` |
| Source-equal allowlist | `a2569b8cc66edef651b160dfb1293d66103169550103fc0eae104df91218bb63` |
| Vendor-covered list | `b23d31aafb7c341b422dfaf8c72cc36a496afc061b7bf97ca4cbc6d996f7591b` |
| BOQ raw-sink fix | `113193ffda62922b373a6de94806786a23e7e5dba05192ac3808794653908cec` |

The four durable Stage 2 logs were also verified by hash: full gate `5156f6cf…`, scoped gate `c52b541e…`, vendor audit `ac0a00bd…`, and gate tests `bd053fea…`.

## Independent execution

- Full checker: exit `0`; Construction PO identities `706`; payload rows checked `34`; extraction `232` files / `588` wrapped literals / `0` missing; `0` errors.
- Vendor-covered audit: exit `0`; `0` errors.
- Exact standalone test command (`python3 construction/tests/test_localization_gates.py`): 15 tests, exit `0`.
- Bench test module on `v16.localhost`: 15 tests, exit `0`.
- Scoped run over `construction/api/translation_tools.py README.md docs/random.csv`: exit `0`; one source file, zero wrapped literals; the absent CSV and Markdown file were skipped.
- Empty checkable set (`--files README.md`): exit `1`, as intended.
- `git diff --check`: exit `0` before this report.
- Frappe and ERPNext Arabic PO paths had no local diff. Construction remains a disclosed dirty feature worktree; no clean-worktree claim is made.

## Prior finding closure matrix

| Finding | Rerun result | Independent assessment |
|---|---|---|
| A3-01 — structural PO/HTML/plural/placeholder gate | **Partially closed** | Context identity, plural indexing, fuzzy/obsolete handling, multiline values, printf variants, tag/entity parity, unsafe markup, Unicode, and affixes are now implemented and current data pass. However, the parser remains a custom subset rather than a standards parser; plural target checks compare every form only with singular `msgid`, not `msgid_plural`; HTML checks compare tag names/entities but not structural nesting/attribute parity. The 15 tests do not invoke the actual plural completeness or full `check_po` path. |
| A3-02 — extraction and vendor upgrade bypass | **Not closed** | The reported `232/588/0` is accurate for `.py` and `.js` literal calls matched by one regex. The authoritative plan requires Python, JavaScript, JSON, workspace, report, print, email, and client-template extraction plus hardcoded visible-string detection. `PO_SCAN_SUFFIXES` is only `{.py,.js}`; multiline/dynamic wrapper calls and general DOM/UI sinks can bypass it; raw-sink detection covers only a few JS calls. Vendor files are reduced to snapshot hashes, without a durable add/change/remove/context-shift delta or reviewed deferral/orphan disposition. |
| A3-03 — runtime freshness | **Not closed** | The v16 decision not to require an inapplicable `.mo` age check is reasonable. The offered equivalent is not implemented: `localization_manifest.json` binds only the Construction PO hash and payload CSV hash. It contains no compiled/boot/runtime dictionary hash, current live packaged hash, critical-key result, test-site dry-run hash, or authenticated runtime result. No Stage 2 dry-run/runtime log exists under `evidence/raw-logs/stage2/`. The Stage 1C runtime proof remains valid for its six keys, but it cannot prove freshness for the Stage 2 candidate. |
| A3-04 — full Released quorum | **Partially closed** | Exact CSV header, governed identity uniqueness, A1/A2/A3 names, all three timestamps (including A2), timestamp shape, version shape, and references are checked. The checker still does not validate decision values, reviewer role/session provenance, timestamp parseability/temporal validity, approval-to-proposal/content-hash binding, or approval invalidation after edits. The payload schema has no fields enabling several of those checks. |
| A3-05 — changed-file routing | **Partially closed** | Traversal and an empty checkable set fail, and an existing Construction `.py`/`.js` file triggers scoped extraction. Nevertheless, absent paths—including `docs/random.csv`—are reported `SKIP` and exit green, deleted/moved localizable source files are also intentionally skipped, JSON is classified as non-localizable outside `construction/data`, and the extraction limitations from A3-02 remain. A relevant deleted/renamed source or unsupported visible artifact can therefore bypass triage. |
| A3-06 — source-equal governance | **Closed for current Construction PO** | The allowlist exists, is fail-closed, keys on app/context/source, and contains the eight stated technical tokens with comments/provenance. The three natural-language values are not allowlisted and have a separate AI-A1 proposal record. Current gate is green. |
| A3-07 — reproducible inventory | **Partially closed** | A private-data-safe aggregate manifest now records site, base commit, app/category counts, hashes, UTC time, predicates, and reconciliation. Its current Construction count `729` correctly reflects the additional 498 Pending rows. It does not contain the claimed exact SQL/query or command/exit record, row-level digest/identity manifest, catalog sync raw log, or versioned vendor delta rows. The older `stage-2-inventory.md` remains stale at Construction `231` and says the gate is complete under the superseded narrow implementation. |
| A3-08 — adversarial tests and durable evidence | **Partially closed** | Fifteen tests pass both standalone and through Bench, and four durable command logs carry UTC/exit metadata. Coverage is materially improved but not “every gate”: the CSV header test only asserts a temporary file exists and never calls `check_csv`; there are no actual fail fixtures for plural completeness, CSV quorum/duplicate identity/timestamps, extraction missing/raw sinks, vendor/manifest staleness, JSON parsing/schema, source-equal success, deleted/renamed routing, or CI-without-vendor-trees behavior. The remediation text claims a sync log, but only four Stage 2 `.txt` logs exist and none is a sync/dry-run log. |

## CI reproducibility blocker

`.github/workflows/linter.yml` uses a normal single-repository `actions/checkout`. The checker resolves vendor catalogs as sibling application trees (`ROOT.parent/frappe/...` and `ROOT.parent/erpnext/...`). In a standard GitHub runner those siblings are not checked out. `check_vendor_baseline` records each absent tree as an error (`vendor-skip`) and exits nonzero. Therefore the new mandatory CI step cannot pass in the workflow as committed. The docstring says vendor checks are “skipped where vendors absent,” but the implementation fails them; either behavior still requires an explicit CI architecture that supplies and verifies the intended vendor commits.

## Runtime-freshness disposition

The architectural substitution—manifest-hash contract plus authenticated test-site dry-run instead of `.mo` mtime—is acceptable in principle for this v16 runtime. It is **not yet evidenced or enforced by this candidate**. The manifest must bind all runtime-producing inputs to a durable, current runtime/boot dictionary or packaged/live digest result, and the authenticated test-site command/output must be saved with target classification, hashes, UTC timestamps, and exit code. CI may validate the source-side contract without a DB, while a separately required integration gate validates the live side. Merely hashing PO and payload files is not runtime freshness.

## Decision

**BLOCKED — Stage 2 is not verified.**

The remediation closes important parts of A3-01 and fully closes the current source-equal gate, and its local green counts are reproducible. It does not yet prove the locked Stage 2 acceptance statement that new visible Construction strings and vendor upgrade deltas cannot bypass triage. A3-02 and A3-03 remain open, the checked-in CI topology is non-reproducible, and A3-04/A3-05/A3-07/A3-08 remain incomplete. This does not invalidate Stage 1C.

## Exact next gate

1. Make CI reproducible: check out/pin the Frappe and ERPNext catalog inputs or store a reviewed vendor delta artifact that standalone CI can validate without sibling repositories.
2. Extend deterministic extraction to every plan-listed visible source class and add tested detection/allowlisting for unwrapped UI output; explicitly cover multiline calls and relevant templates/JSON/workspace/report/print/email sources.
3. Produce and govern an add/change/remove/context-shift vendor delta with dispositions, rather than only replacing snapshot hashes.
4. Implement the v16 freshness contract end to end: bind all declared inputs and durable authenticated test-site dry-run/runtime/critical-key evidence. No compiled `.mo` age check is required if it is not part of this runtime architecture.
5. Complete approval binding and adversarial tests for every claimed gate; make deleted/renamed and unsupported relevant paths fail closed or require an explicit reviewed disposition.
6. Save the exact inventory generator/query, catalog sync log, runtime dry-run log, and refreshed internally consistent narrative/manifest.
7. Run a new independent AI-R rerun against the exact remediated hashes. Only `VERIFIED` opens Stage 3.

