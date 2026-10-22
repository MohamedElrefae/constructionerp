# AI-A2 Independent Peer Review — bilingual-translation-catalog-sync

**Work item:** `bilingual-translation-catalog-sync`
**Reviewer:** fresh non-author session (independent of the proposal author)
**Session / task id:** no formal task id issued; fresh non-author opencode session
(`opencode/mimo-v2.6-flash-free`), read-only research, no prior authorship of SCOPE,
audit script, log or proposal
**Date:** 2026-10-05 (UTC) / 2026-10-06 EEST
**Site:** v16.localhost (non-production test)
**Briefing base commit:** `234c024`; HEAD observed during this review `6c721b8`
(3 commits later: `3bd3d1e`, `da7c3c6`, `6c721b8` — none touch
`construction/data/`, `translation_loader.py`, `translation_service.py`,
`overrides/translation.py` or `patches/`)

> **Privacy R4:** no Arabic value is written in this committed record. Every Arabic
> string is represented only by its sha16 digest (first 16 hex chars of the SHA-256 of
> the UTF-8 value). Arabic values exist solely in the private proposal
> (`sites/v16.localhost/private/translation-catalog-sync/proposal.json`) and in the
> pre-existing app data artefacts.

**Verdict: `REVISE` (4 required changes) — proposal sha256
`a497bc418bcb7df28e794eb226cd0502da91251efc960c41ed236690e3ccd089`**

---

## 1. Header block

| field | value |
|---|---|
| Work item | `bilingual-translation-catalog-sync` |
| Reviewer | fresh non-author session (independent of the proposal author) |
| Date | 2026-10-05 (UTC) |
| Site | v16.localhost (non-production test) |
| Review artefact | `docs/ai/work-items/bilingual-translation-catalog-sync/evidence/review-ai-a2.md` |
| Round | 1 |

## 2. Binding

| item | value |
|---|---|
| Reviewed artefact | `sites/v16.localhost/private/translation-catalog-sync/proposal.json` (private, 8282 bytes, trailing newline) |
| sha256 (recomputed by me) | `a497bc418bcb7df28e794eb226cd0502da91251efc960c41ed236690e3ccd089` |
| Source of comparison | `evidence/audit-translation-catalog.log:117` |
| Recomputation | **I recomputed it myself** with `sha256sum …/proposal.json` at session start and again at session end — identical both times, and identical to the audit log. I did not trust the log's printed digest. |

Supporting digests I also recomputed myself (all match the proposal and the audit log):

- glossary `construction/data/glossary/egyptian_construction_glossary.json` =
  `aefbbf633d432fb93ac63996960bb58d0bd005e973e0e461f4480d7ae46b51b4`
- payload `construction/data/translations/approved_ar_overrides.csv` =
  `0a55f3c120cf1ac381c0564407cdc7a9ea975782d68642c6a943807cdd70b421`
- predicted glossary-after (independently re-derived, check C) =
  `7afbef1ab892f466eb14471c99a9e76dde65b4f2e9d4a40a1405e34addc6894d`

## 3. Verdict chain

| Round | Scope | Approve | Revise | Overall |
|---|---|---|---|---|
| 1 | Private proposal + audit log + audit script (digest chain, history, loader/drift safety, R4, byte hygiene, completeness vs briefing §3 Step 1 / §4) | — | X | **REVISE** |

## 4. Reviewer checks

| check | verdict | evidence (commands + observed output) |
|---|---|---|
| A. Proposal digest recomputed | **PASS** | `sha256sum sites/v16.localhost/private/translation-catalog-sync/proposal.json` → `a497bc418bcb7df28e794eb226cd0502da91251efc960c41ed236690e3ccd089` (8282 bytes); equals audit log line 117. Re-run at end of session: unchanged. |
| B. Glossary before-sha + payload sha | **PASS** | `sha256sum construction/data/glossary/…json construction/data/translations/approved_ar_overrides.csv` → `aefbbf63…46b51b4` / `0a55f3c1…70b421`. Both equal proposal `glossary_sha256_before` and `payload_sha256_before`; payload `sha256_after` is the same digest (file untouched). Re-verified at session end. |
| C. Predicted glossary-after recomputed independently | **PASS** | (1) Serialisation pre-check: `json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")` reproduces the current file **byte-for-byte** (24380 bytes, no trailing newline — `raw.endswith(b"\n")` = False). (2) Applied exactly the specified patch (payload value for `Add Child` at `approved_ar`; proposal `after.usage_notes` / `after.references`; term `version`→`2.1`; meta `previous_checksum`→before-sha, `previous_version`→old meta version `2.0`, `version`→`2.1`, `date`→`2026-10-05`) and serialised the same way → **`7afbef1ab892f466eb14471c99a9e76dde65b4f2e9d4a40a1405e34addc6894d`** = predicted value in proposal and log line 119. Intermediate sha16s also verified: `approved_ar` `46dadab0f9e2eacf`→`f548ae03f4cdbef0`, `usage_notes` `0dfe04819391b103`→`a512254a69200243`, `references` `0a7690f5e7326f8e`→`0f76655c55120046`. |
| D. Git history: payload supersession, glossary predates | **PASS** | `git show 4fede75 -- …approved_ar_overrides.csv` → exactly one payload line changed, `release_version` `1.0`→`1.1`, value sha16 `46dadab0f9e2eacf`→`f548ae03f4cdbef0`, commit dated Thu Sep 3 14:08:18 2026, message "owner-directed, single space". Commit is an ancestor of HEAD (`git merge-base --is-ancestor` OK). Walking every blob revision of that row: only two distinct values ever existed — `46dadab0f9e2eacf`@rv1.0 (newest at `39560df`, 2026-09-02) and `f548ae03f4cdbef0`@rv1.1 (all commits `4fede75`→`eead580`); current work-tree row = `f548ae03f4cdbef0`@rv1.1. Glossary file log: `9011767` (2026-09-02) then `338baba` (2026-09-01) — glossary predates the owner change by ≥1 day. Corroboration: `construction/data/translations/release_decisions.json` decision `3f9feb39e587957d995d7a4116536d0f41b994a5918a07c9eaaf8599e04185a6` carries `release_version 1.1`, `translated_text` sha16 `f548ae03f4cdbef0`, artifact ref `legacy:docs/translation/sign-off-1.0.md` (file exists; §6.2 exists), 3 named reviewers + timestamps — matching proposal `payload_decision_ref`. |
| E. Runtime loader excludes `ct_is_catalog_entry=1` and empty values | **PASS** | `construction/translation_loader.py:25` → `filters={"language": lang, "ct_is_catalog_entry": 0}` (the exact filter); `:44-48` → loop body skips empties: comment ":45 An empty runtime value must never shadow the .mo catalog" and `:47-48` `if not t.translated_text: continue`. Fallback path `:31-38` (no catalog filter) runs only when the column is reported missing — the column exists (`audit-translation-catalog.log:13` `by_ct_is_catalog_entry {0: 7028, 1: 15733}`). Therefore the 24 inert rows (`ct_is_catalog_entry=1`) and their 20 distinct sources cannot render; inert-empty rows are double-protected (flag filter + empty skip). |
| F. Drift safety / payload byte-identity | **PASS** | `construction/translation_service.py:636-676` `_compute_drift()`: builds `payload_map` from the payload CSV (`release_status == "Released"` only, :647), reads live rows `filters={"ct_origin": "Packaged Release", "language": "ar"}` (:651-656), then compares `translated_text` / `ct_app` / `ct_release_version` plus missing/orphan keys. **The glossary JSON is never read by `_compute_drift()`**, so a glossary edit cannot create drift. Payload CSV: `git status` clean for `construction/data/`, and `payload_sha256_before == payload_sha256_after == 0a55f3c1…70b421` → byte-identical. Extra safety observed: `hooks.py:403` (`after_install`) and `hooks.py:426` (`after_migrate`) both run `construction.translation_service.import_released_overrides_hook`, which force-syncs live rows to the payload on the next migrate (`import_released_overrides` sets `needs_update=True` whenever `existing_val != val`). |
| G. Audit script R4 + write lint | **PASS** (note N1) | Scan of `evidence/scripts/audit_translation_catalog.py` (471 lines): zero Arabic **values**; Arabic-block codepoints found = exactly one, `U+0640` (tatweel) inside the byte-hygiene sentinel at line 102, plus the regex range endpoints `\u0600`/`\u06FF` at line 130 (scanner ranges, not values); no `U+06xx` value escapes. The target Arabic is derived at runtime from the payload CSV (`build_patch`, lines 146-197), never literalised. `python3 scripts/lint_translation_writes.py` → `Translation write lint PASSED`, exit 0. Script is read-only by construction: a single `frappe.get_all` (:134) + `clear_cache()` + one file write to the private dir; no `set_value`/`get_doc(...).save`/`db.sql` writes. |
| H. Byte hygiene of the target value | **PASS** | I re-ran the proposal's `byte_scan_after` logic on the target myself: `[]`. Facts observed: `len=15`; sha16 `f548ae03f4cdbef0`; codepoints = 13 Arabic letters (`U+0625, U+0636, U+0627, U+0641, U+0629, U+062D, U+0633, U+0627, U+0628, U+0641, U+0631, U+0639, U+064A`) + **two** `U+0020` normal single spaces (legitimate word separators); no double space, no leading/trailing whitespace, no bidi/zero-width, no C0/C1 controls, no tatweel, no Arabic-Indic digits, no `Cf/Co/Cs`. |
| I. Forbidden terms for `Add Child` | **PASS** | Glossary `forbidden_ar` sha16s = `7585be92d87ca83b`, `632978bfde63531d`; proposal `before` and `after` lists hash identically (list unaltered by the patch). Substring containment test of each token against the target value → **no hits** (and the script enforces the same test at `build_patch` line 166, aborting on violation). |
| J. Completeness vs briefing Step 1 / §3 (and §4 deliverables) | **FAIL** | 4 gaps — see "Amendments" below. Positive coverage that I did confirm: Step 1 extraction (`ar` rows = 22761, PASS A), glossary conflict flagging (PASS B/C/D/E, `stored exact=76 divergent=4 empty=21`, `rendered match=46 divergent=1 absent=0`, forbidden violations 0, context contradictions 0), inert report-only inventory (PASS H: 3 divergent + 21 empty = 24 rows over 20 distinct sources — I recount-verified 17 empty-source names + 3 divergent sources = 20), private proposal output (check A), read-only script (check G). Missing: `SCOPE.md`; base-commit pinning; ratified baseline for master labels; app-source carriers of the superseded value. |

### Recorded notes (non-blocking)

- **N1** — script line 56 comment says "no Arabic literals in this file" while line 102
  contains `U+0640` as a raw character; write it as the escape `"\u0640"` for literal
  truth. Zero value entropy either way.
- **N2** — briefing §2 invariant 5 (format specifiers `{0}`/`%s`/HTML) has no audit
  pass; the target value contains no format tokens (verified), so defer the format-
  corruption assertion to post-sync verification (§3 Step 3).
- **N3** — proposal authority note says "superseded the glossary v1.0 value"; the
  glossary term's own `version` field is `2.0` (meta `2.0`) — "v1.0" is the payload
  `release_version` / the term's `references` string. Wording only; no digest impact.
- **N4** — commit hygiene: exclude `evidence/scripts/__pycache__/` from `git add`;
  never commit the untracked root `dump.rdb`; keep `git add` scoped to this work-item
  directory (currently wholly untracked).
- **N5** — briefing §4 deliverables `dry-run.log`, `apply.log`,
  `post-sync-verification.log`, `gates.log`, `MANIFEST.json` are later-stage artefacts
  (Steps 2-3) and are not defects at Round 1.

## 5. Redaction statement (privacy R4)

No Arabic value is committed in this file. Every Arabic string referenced here — the
target value, the superseded value, the third UI literal, the two `forbidden_ar`
tokens — appears only as a sha16 digest (`f548ae03f4cdbef0`, `46dadab0f9e2eacf`,
`0bed7b4494c94ee6`, `7585be92d87ca83b`, `632978bfde63531d`). Arabic values remain
only in the private proposal under `sites/v16.localhost/private/translation-catalog-sync/`
and in pre-existing app data artefacts. I created no file under `docs/` other than this
review record, and this record was scanned after writing to confirm it contains zero
Arabic-block codepoints.

## 6. Amendments / required changes

1. **Add `SCOPE.md`** at `docs/ai/work-items/bilingual-translation-catalog-sync/SCOPE.md`
   (briefing §4 deliverable 1; every sibling work item has one). It must state the scope
   descriptor, the audit inventory, the report-only stance for the 24 inert rows / 20
   distinct sources, and the zero-`tabTranslation`-write stance of this round.
2. **Pin the base commit in the audit log.** `evidence/scripts/audit_translation_catalog.py:230`
   falls back to the literal `see git` because `frappe.utils.get_git_sha` does not exist,
   so `audit-translation-catalog.log:5` does not self-bind to the briefing base `234c024`.
   Replace the fallback with a real `git rev-parse --short HEAD` (subprocess) or the pinned
   literal, add a `git status --porcelain | wc -l` dirty-tree count plus an explicit note
   that `construction/data/`, `translation_loader.py`, `translation_service.py`,
   `overrides/translation.py` and `patches/` are clean, regenerate the log, then **verify
   the regenerated `proposal.json` sha256 is still
   `a497bc418bcb7df28e794eb226cd0502da91251efc960c41ed236690e3ccd089`** (the proposal
   content carries no timestamps and is deterministic); if it differs, re-sha and rebind
   this review.
3. **Make the master-label check actually flag conflicts (briefing Step 1 bullet 2).**
   `PASS F` (`audit_translation_catalog.py:337-348`) is presence-only (`ok = bool(got)`)
   yet is titled "ratified master-data labels … OK". Only 2 of the 12 labels
   (`Cost Center`, `Chart of Accounts`) are glossary terms / released payload rows; the
   other 10 have no ratified baseline anywhere in committed evidence (I grepped all 11
   distinct label sha16s — every hit is inside this work item's own artefacts), and the
   script reads only `tabTranslation` (single `frappe.get_all`, :134) — no master-data
   doctype. Either (a) compare each rendered label against a stated ratified baseline and
   cite the baseline artefact + sha16 per label, or (b) retitle PASS F as a presence probe
   and record explicitly in log and proposal that no ratified value comparison was
   performed. Until then the claim "flag entries conflicting with … newly populated master
   labels" must not be reported as satisfied.
4. **Disclose the other committed carriers of the superseded value** (sha16
   `46dadab0f9e2eacf`) in the proposal's `authority.glossary_supremacy_note` and in
   `SCOPE.md` — the current text implies the glossary is the *only* stale artefact. My
   repo scan found 13 files carrying that value, of which these can write or render:
   - `construction/patches/v8_4/fix_tree_view_arabic_translations.py:21` — registered in
     `construction/patches.txt:17`; `execute()` force-`set_value`s **every** `ar` row for
     the source (any origin/context) → if re-executed it reverts the Packaged Release row
     and would register as `_compute_drift()` "value mismatch" until the next migrate
     self-heals it via `import_released_overrides_hook` (hooks `after_install`/`after_migrate`);
   - `construction/insert_translations.py:42` — seed dict used by registered patches
     `v6_2`/`v6_3`/`v6_4`/`v6_5`; insert-only semantics (never overwrites, prints
     `[DRIFT]`) but it seeds the stale value on a fresh site until the payload import runs;
   - `construction/scripts/global_arabic_translation_review.py:49` — write-allowlisted
     review script still carrying the stale value;
   - `construction/public/js/components/TreeView.jsx:198` — a **third** variant, sha16
     `0bed7b4494c94ee6`, hardcoded in the component (no consumer found:
     `ModernThemeComponents.TreeView` is exported in `components/index.js:12` but nothing
     references it and it is absent from `app_include_js`) — confirm dead or reconcile.
   Evidence the mitigation (payload import on every migrate + insert-only seed) or schedule
   alignment; do not silently widen the remediation.

## 7. Resolution

**Standing: 9/10 checks passed (A-I PASS, J FAIL).** Round 1 verdict = **REVISE** with
4 required changes above. Digest chain, git history, loader/drift safety, R4 and byte
hygiene all verify independently — the defects are completeness/evidence-binding gaps, not
integrity failures.

**Owner sha-bound approval is still the hard gate:** no glossary byte may change until the
4 required changes land, the digests are re-verified against the (possibly regenerated)
proposal, and the owner approves the exact sha256 in writing. Zero `tabTranslation` /
Translation Doctype writes remain mandatory for this round.

---

# Round 2 — independent re-verification (2026-10-06, fresh non-author session)

**VERDICT: REVISE** — one outstanding literal privacy-scan nit (round-1 N1, still unfixed);
all four round-1 required changes are substantively addressed.

**Proposal sha256 (recomputed by me with `sha256sum`):**
`a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0`
(matches `audit-translation-catalog.log` PROPOSAL block; differs from the Round-1 digest
because the proposal was deterministically regenerated with the four amendments applied).

| check | result | observed evidence |
|---|---|---|
| A. Recompute proposal sha256 | **PASS** | `sha256sum sites/v16.localhost/private/translation-catalog-sync/proposal.json` → `a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0`; equals the audit log's printed digest. |
| B. Round-1 required changes addressed | **PASS** | (1) `SCOPE.md` exists, 144 lines, mission/scope/invariants/audit inventory/findings C-01..C-08/deliverables/causal order — substantive. (2) `audit-translation-catalog.log:5` now shows `base_commit : 6c721b8` (real, via `git rev-parse --short HEAD` at `audit_translation_catalog.py:134-143`); no "see git" fallback. (3) PASS F now prints `comparison=value_verified` only for labels with a committed baseline and `comparison=presence_only baseline=<none committed>` otherwise; baselines parsed at runtime from `docs/translation/smoke-test-1.0.md` (`:146`,`:153`,`:480-499`); log shows 12/12 present, 2/12 value-verified, NOTE citing finding C-05. Script contains no Arabic label literals. (4) PASS J lists `construction/patches/v8_4/fix_tree_view_arabic_translations.py` as `app_python_write_path files : 1` (finding C-06) and PASS J2 lists `construction/public/js/components/TreeView.jsx hardcoded_arabic_labels=10` (finding C-07). |
| C. Core patch unchanged and correct | **PASS** | `glossary_term_patches` has exactly ONE entry, source `Add Child`; `approved_ar` before/after sha16 `46dadab0f9e2eacf`/`f548ae03f4cdbef0`; `glossary_sha256_before = aefbbf633d432fb93ac63996960bb58d0bd005e973e0e461f4480d7ae46b51b4`. I independently re-derived the predicted `glossary_sha256_after`: serialisation pre-check byte-identical (24380 bytes, no trailing newline), applied the patch (payload `approved_ar`, `after.usage_notes`/`after.references`, term version 2.1, meta previous_checksum=before-sha, previous_version=2.0, version=2.1, date=2026-10-05) → **`7afbef1ab892f466eb14471c99a9e76dde65b4f2e9d4a40a1405e34addc6894d`** matches proposal. `site_translation_writes = []`, `counts.site_translation_writes = 0` (no top-level `site_translation_writes_count` key exists; the zero is carried in `counts`). |
| D. Privacy R4 codepoint scan (U+0600–U+06FF) | **FAIL (literal)** | `SCOPE.md`: no hits. `audit-translation-catalog.log`: no hits. `review-ai-a2.md` (Round 1 portion + this appendix): no hits. `evidence/scripts/audit_translation_catalog.py`: **1 hit at line 103, U+0640 (tatweel)** — the byte-hygiene sentinel raw character; this is round-1 note N1, still not written as the escape `"\u0640"`. It carries zero value entropy (scanner sentinel, not a translation value), but the strict "no Arabic codepoint in committed files" reading is not met until it is escaped. |
| E. Lint / compile | **PASS** | `python3 scripts/lint_translation_writes.py` → `Translation write lint PASSED`, rc=0. `python3 -m py_compile …/evidence/scripts/audit_translation_catalog.py` → OK. No bash deliverable to `-n` (skipped). |
| F. SCOPE.md C-01..C-08 consistent, no overclaim | **PASS** | C-01 (single rendered divergence, owner-adjudicated glossary-to-payload harmonisation) matches PASS I/C/D/E (1 patch, 0 forbidden violations, 0 context contradictions). C-02 inert 24 rows/20 sources matches PASS H. C-03 lint-forbidden apply path matches `lint_translation_writes.py` passing with 0 writes. C-04 schema-v1 `_load_glossary` no-op is a report. C-05 2/12 value-verified matches PASS F note. C-06/C-07 match PASS J/J2. C-08 dated-evidence stance stated. Language is report-only where appropriate; no claim of ratified baselines beyond the 2 committed ones. |

**Remaining required changes:**

1. (Carry-over N1, now the only blocker) Escape the U+0640 sentinel as `"\\u0640"` at
   `evidence/scripts/audit_translation_catalog.py:103` (or remove the raw char), regenerate
   the audit log, and re-verify the proposal sha256 is still
   `a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0` (content is
   timestamp-free and deterministic; only the log byte stream for the sentinel line should
   change if it is echoed there — it is not, so the digest should hold).

**Redaction / privacy statement.** No Arabic value was introduced into any file under
`docs/` by this round. Findings reference sha16 digests only (`46dadab0f9e2eacf`,
`f548ae03f4cdbef0`, `7afbef1a…dc6894d`). The only Arabic-block codepoint in a committed
artefact is the pre-existing U+0640 sentinel at `audit_translation_catalog.py:103`,
flagged above; Arabic values remain confined to the private proposal under
`sites/v16.localhost/private/translation-catalog-sync/` and pre-existing app data.

**Resolution:** standing = 5/6 checks passed (A, B, C, E, F PASS; D literal FAIL on the
carried-over N1 sentinel); owner sha-bound approval is the outstanding hard gate.

---

# Round 3 — re-verification of carried-over N1 fix (2026-10-06)

**ROUND 3 VERDICT: APPROVE**

- Check D (strict privacy scan, U+0600–U+06FF across `SCOPE.md`,
  `evidence/audit-translation-catalog.log`,
  `evidence/scripts/audit_translation_catalog.py`,
  `evidence/review-ai-a2.md`): **clean, zero hits.** The U+0640 sentinel at
  `audit_translation_catalog.py:103` is now the comparison `elif cp == 0x0640:`
  (line 103); no raw Arabic codepoint remains in any committed work-item file.
- Proposal sha256 recomputed with `sha256sum`:
  `a23a7dceb6cf4b794af47155317be63267fbab46a7334618bf05dfbceec9b9a0` — unchanged.
- `python3 -m py_compile …/audit_translation_catalog.py` → OK;
  `python3 scripts/lint_translation_writes.py` → `Translation write lint PASSED`, rc=0.
- Round-2 REVISE item (N1) is resolved; no Arabic values were introduced into any
  committed file (sha16 digests only, as before).

**Resolution:** standing = 6/6 checks passed; owner sha-bound approval is the outstanding hard gate.


