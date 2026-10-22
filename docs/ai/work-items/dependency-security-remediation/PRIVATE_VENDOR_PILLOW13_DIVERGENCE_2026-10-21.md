# Private vendor divergence — Pillow 13.0.0 on pinned Frappe v16 (2026-10-21)

**Work item:** `dependency-security-remediation` (G10 sub-scope)
**Date:** 2026-10-21
**Status:** private, versioned candidate under owner authorization — **NOT** an upstream-supported release,
**NOT** a release gate closure, **NOT** published, **NOT** bound to any site or runtime.

---

## 1. What this record is

This is the dated provenance and compatibility record for an **owner-authorized, explicitly private and
versioned** vendor divergence: the pinned Frappe v16 base used by this project
(`2871914b69b6e14a4b023d9b7cc52dc3e269cc1b`, Frappe `16.51.1`) declares `Pillow~=12.3.0`, and no upstream
Frappe v16 release inspected on 2026-10-21 declares `Pillow~=13.0.0`. The Pillow 13 advisories that block
the `Vulnerable Dependency Check` job are only fixed in Pillow `13.0.0` (released 2026-10-16); the Pillow
`12.x` line ends at `12.3.0`.

The divergence is therefore a **private vendor patch carried by this repository's dependency pins**, not a
framework release. It is recorded here so that any later reader can tell exactly which vendor commit, which
base commit, and which upstream support status the candidate rests on.

## 2. Exact identities

| Item | Value |
|---|---|
| Vendor (Frappe) base commit | `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` (16.51.1), tree `e06a13c1ef184c816802418a6928dffc6c7a285b` |
| Vendor (Frappe) divergence commit | `af44091716ed4e9be32720483a27d3f1937ad7fd`, tree `231f1d8b87171dfc6fcedb1ae320195953539c34` |
| Vendor divergence diff | `pyproject.toml`: one line, `"Pillow~=12.3.0",` → `"Pillow~=13.0.0",` |
| Vendor branch (owned clone only) | `private/pillow13-v16-divergence-20261021` |
| Application base commit | `0185a2969a8c28796d588981ccf004cf4399d637`, tree `057c1912ec14506ed6f5b0298e66ac485b8a41bb` |
| Application branch (owned clone only) | `private/pillow13-v16-candidate-20261021` |
| ERPNext (unchanged) | `7474d9e786277383de1242ab882f16856d17a9c9` (16.50.0) — no Pillow pin, no direct PIL usage |
| Application commit that adds this record | recorded in the round-1 evidence bundle (`REPORT.md` §3.2) |

None of these commits exists in a public `frappe/frappe` repository. The vendor commit is **not remotely
fetchable**; it can only be reconstructed by applying the recorded one-line patch to the recorded base.

## 3. Files changed in the application tree

| File | Change |
|---|---|
| `pyproject.toml` | dependency `Pillow~=12.3.0` → `Pillow~=13.0.0`; comment block extended with the divergence provenance |
| `requirements.txt` | `Pillow~=12.3.0` → `Pillow~=13.0.0`; Pillow-specific provenance comment added |
| `docs/ai/work-items/dependency-security-remediation/PRIVATE_VENDOR_PILLOW13_DIVERGENCE_2026-10-21.md` | this record |

No other application file is touched. The CT native contract, Timesheet project-scope, native BOQ and
stage-2 protocol work present in the application base tree are preserved unchanged.

## 4. What is deliberately NOT changed, and NOT claimed

* `[tool.bench.frappe-dependencies] frappe = ">=16.36.1,<17.0.0"` is **unchanged**. No framework floor bump
  is performed or implied by this record.
* **G10 is not closed by this change.** The ledger entry in
  `docs/ai/work-items/customer-release-gap-fixes/STATUS.md` still reads `SATISFIED` for the *previous*
  Frappe v16.36.1 alignment; re-opening and re-qualifying G10 against the Pillow 13 combination is a
  release-gate decision that this record does not take and does not pre-empt. Any statement that G10 is
  satisfied **for this candidate** would be false.
* No upstream support is claimed. The divergence is a local patch, not a Frappe release.
* No CVE waiver, audit ignore list, `--ignore-vuln` flag, security-exclusion file, dropped required CI job,
  or fabricated "fixed" package is introduced anywhere.
* The dependency-security work item scope file, the customer-release gap report and the dated
  `DEPENDENCY_VALIDATION.md` / `DEPENDENCY_REVIEW.md` / `ADVISORY_INVENTORY.json` narrative are **not**
  rewritten here; they remain valid as the record of the 2026-10-06 alignment.
* The shared bench, the shared `apps/frappe`, the shared `apps/erpnext`, the protected `apps/construction`
  checkout, the frozen application source and the accepted runtime are **not** modified by this record.

## 5. CI transport — proposal only, not applied

The private vendor commit is not fetchable from `github.com/frappe/frappe`, so the existing CI steps that
assert `git rev-parse HEAD = 2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` for `apps/frappe` cannot simply be
repointed at a remote SHA.

The round-1 **evidence bundle** therefore contains a **source-only, reviewable CI integration proposal**
(not applied to `.github/workflows/ci.yml` in this round, not committed to this repository, and not dispatched
to any CI destination). The proposal transports the exact one-line vendor patch as a file that would be
committed in this repository and asserts, fail-closed:

1. the vendor checkout base commit equals `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b`;
2. the transport patch file's SHA-256 equals the recorded digest;
3. `git apply --check` succeeds against that base;
4. the resulting tree equals the recorded expected result tree `231f1d8b87171dfc6fcedb1ae320195953539c34`;
5. the patched `pyproject.toml` byte digest equals the recorded digest.

The proposal also names the CI fixture pins that are affected and the ones that are **not**: the
`construction/data/localization/vendor_ci_inputs.json` digests cover `frappe/locale/ar.po` and
`frappe/public/js/frappe/form/script_manager.js`, neither of which the one-line `pyproject.toml` change
touches, so those recorded hashes and the pinned vendor commits stay as they are.

Because the divergence is applied as an **uncommitted working-tree change**, `git rev-parse HEAD` for
`apps/frappe` stays `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` and the existing vendor-HEAD assertions in
`.github/workflows/ci.yml` remain valid unchanged; the proposal **adds** an assertion of the effective
vendor tree and patched-file digest so that a missing or reverted divergence fails the job instead of
silently running the un-diverged vendor. Review of that proposal is required before any CI dispatch.

## 6. Verification performed in round 1

Round-1 evidence (raw logs, exact commands, exit codes, digests) is written to
`/home/mohamed/frappe-bench/backups/f44-qualification-resume-2026-10-20/pillow13-v16-candidate-round1/`.

Performed: a clean, fully owned Python 3.14 environment built from the owned Frappe divergence commit, the
pinned ERPNext commit and the owned application tree, including both `git+https` framework dependencies
(`PyPika`, `gunicorn`); `pip check` (exit 0); the CI audit command `pip-audit==2.10.1 --desc on .` (exit 0 on
the candidate, exit 1 with the identical eight advisories on the baseline control); the real upstream Frappe
image and identicon test bodies executed against the upstream Frappe fixtures; the real `frappe.utils.image`
16-bit and RGB PNG paths compared byte-for-byte between Pillow 12.3.0 and 13.0.0; PDF rendering dependency
compatibility through the Frappe-pinned WeasyPrint; the application startup checkers, scope and translation
lints, offline suite, stage-2 protocol suites, JS property tests and customer-distribution verification.

**One known outstanding item, measured and attributed.** The application's localization **vendor-delta** pin
records the upstream Frappe commit, so `construction/tests/test_localization_gates.py` fails with
`vendor-delta: frappe HEAD af44091716ed4e9be32720483a27d3f1937ad7fd != pinned
2871914b69b6e14a4b023d9b7cc52dc3e269cc1b`. With the base vendor the same suite passes in the same owned
environment, so the failure is attributable to this private divergence alone. The repository's documented
remedy is `scripts/vendor_upgrade_delta.py --app frappe --old 2871914b… --new af44091… --write`, followed by
human triage of the generated `triage_status: pending` delta and a **reviewed** re-record. That reviewed
evidence change is **not** made here and is not part of this record.

Not performed and therefore **not claimed**: site- and database-dependent Frappe/ERPNext/application test
modules, any `bench` site command, any runtime rebind, any CI dispatch, any push, pull request or
publication, and any customer-acceptance activity. F44, business, F45 and publication remain **OPEN**.

## 7. Required next steps (owner decisions)

1. Review and approve the CI transport proposal before any dispatch to the authorized private Construction
   CI destination.
2. Decide and record the localization vendor-delta re-record for the new vendor commit, or accept it as a
   known gate failure.
3. Decide whether to re-open G10 in `docs/ai/work-items/customer-release-gap-fixes/STATUS.md`, and record
   the result of that decision.
4. Decide whether the private vendor divergence becomes a supported internal matrix entry, or whether the
   candidate waits for an upstream Frappe v16 release that carries `Pillow~=13.0.0`.
5. Re-run the site- and database-dependent qualification on a disposable site under a separate
   authorization; that scope was explicitly excluded from this round.

## 8. Files read for this record (session startup)

`AGENTS.md`; `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` (sections 3, 4, 15, 16);
`docs/ai/CONTEXT_INDEX.md`; `AGENT_WORKFLOW.md`; `docs/ai/SCHEMA_FACTS.md` (summary, verified by
`scripts/schema_drift_checker.py`); `SESSION_MEMORY.md` (sections 1, 3, 6); `pyproject.toml`;
`requirements.txt`; `docs/ai/work-items/dependency-security-remediation/SCOPE.md`;
`docs/ai/work-items/customer-release-gap-fixes/STATUS.md`; `PRIVATE_CI.md`; `.github/workflows/ci.yml`;
`.github/workflows/linter.yml`; `construction/data/localization/vendor_ci_inputs.json`; and, read-only, the
shared `apps/frappe` source of the pinned base commit.

## 8. Addendum 2026-10-21 (round 2) — CI vendor identity implemented; candidate NOT YET qualified

Independent parent review (`pillow13-v16-parent-review/REVIEW.json`) accepted the round-1 dependency work but
rejected the round-1 CI transport with two blocking findings:

* **P13-CI-001** — applying the patch as an uncommitted working-tree change kept vendor `HEAD` at the upstream
  base, so a HEAD-only vendor-delta gate could miss the divergence. §5 of this record described that
  mechanism; **that description is superseded by this addendum** and is no longer the transport in this tree.
* **P13-CI-002** — the later CI assertion validated `git write-tree` (the index only), so a tracked edit made
  after the applier still passed both the tree and `pyproject.toml` assertions.

### Implemented transport (in this tree)

`.github/ci/apply_private_vendor_divergence.py` (with the reviewed one-line patch, the raw private commit
object and the identity record under `.github/ci/vendor_patches/`) now:

1. requires the pinned base `HEAD` `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b`, base tree
   `e06a13c1ef184c816802418a6928dffc6c7a285b`, and a **clean tracked working tree and index**;
2. verifies the patch digest, applies the patch and requires that **only** `pyproject.toml` changed;
3. stages only that file and requires the index tree `231f1d8b87171dfc6fcedb1ae320195953539c34`;
4. reconstructs the **exact** reviewed private commit `af44091716ed4e9be32720483a27d3f1937ad7fd` locally from
   the recorded raw commit object (`git hash-object -t commit -w`), proving the SHA-1, tree and parent;
5. checks out that commit and requires `HEAD` = the reviewed commit, `HEAD` tree = the reviewed tree, and a
   clean tracked working tree and index.

The commit is **never fetched** — it is unpublished — and no vendor bundle, history or release is uploaded.
`--verify` re-asserts the same identity and cleanliness at execution/measurement boundaries. The applier is
fail-closed and never resets, stashes or cleans away an unexpected change.

CI wiring: the Server setup and the C2 setup run the applier **before** `bench setup requirements frappe`; the
JS execution step and the C2 measurement step run `--verify` first; the stage-2 sparse checkout job is
unchanged and continues to use the public, pinned base refs. Negative controls (wrong base, missing patch,
tampered patch, tampered commit metadata, extra unstaged/staged tracked change before and after apply,
reverted divergence) all fail closed and preserve the unexpected change; the positive control yields `HEAD`
`af44091716ed4e9be32720483a27d3f1937ad7fd`, tree `231f1d8b87171dfc6fcedb1ae320195953539c34` and a clean
tracked checkout.

### Controlled vendor-delta — still PENDING, not recorded here

The Frappe catalog is byte-identical between the base and the private commit
(`frappe/locale/ar.po` sha256 `ad0c7b27c0406257911210b5c5a354a2fa9506f8fac1b9552806c592c7038205` before and
after), so the generated vendor delta is empty (0 added / 0 removed / 0 changed / 0 context-shift). Only the
recorded vendor **commit** in `construction/data/localization/vendor_catalog_baseline.json` differs. That
one-line pin update requires reviewed approval and is **not** applied in this tree: against the divergent
vendor, `scripts/check_localization_gates.py --ci-source-only` reports exactly one error — the vendor-delta
pin — and the same run with the base vendor reports zero. The pending delta and the exact pin-update
proposal are in the round-2 evidence bundle, not in this tree.

### G10 and qualification status

**The candidate is NOT YET qualified.** This addendum does not close, re-open, re-qualify or overwrite the
G10 ledger entry in `docs/ai/work-items/customer-release-gap-fixes/STATUS.md`, which still records the
2026-10-06 alignment. The localization vendor-delta gate remains red against the private vendor until a human
owner/reviewer records the pin; coordinator review is not human approval. No CI dispatch, push, pull request,
publication, runtime rebind or site qualification was performed.

## Addendum 2026-10-21 (round 3) — every gate-consuming CI job aligned, controlled vendor pin recorded

The two earlier addenda above describe the transport and the *then-pending* vendor pin. This addendum
supersedes their CI and pin status for this tree; the history above is left intact.

### P13-CI-003 — Linters now runs the same effective vendor as Server and C2

`linter.yml` previously checked out the public base `2871914b…` and then ran
`scripts/check_localization_gates.py --ci-source-only`, so it evaluated a vendor identity the recorded
baseline no longer pins. Its Frappe catalog checkout is now the same exact-commit transport used by the Server
job and the C2 job:

1. `actions/checkout` still fetches only the **public** base ref `2871914b…` (the private commit is never
   fetched; it stays unpublished). The sparse checkout now materialises `frappe/locale` **and the root
   `pyproject.toml`**, the only file the reviewed patch edits.
2. `actions/setup-python` (3.14, `cache: pip`) runs before the transport step, and both come before
   pre-commit and the localization gate.
3. `.github/ci/apply_private_vendor_divergence.py` reconstructs the exact private commit
   `af44091716ed4e9be32720483a27d3f1937ad7fd` locally, then asserts `HEAD`, `HEAD^{tree}`
   `231f1d8b…`, parent `2871914b…` and a clean tracked working tree **and** index.
4. A `--verify` step re-asserts the same identity immediately before the localization gate (measurement
   boundary), so a reverted, missing or tampered divergence cannot reach the gate.
5. The ERPNext pin `7474d9e…`, `pre-commit`, the scope-metadata lint, Semgrep and the real
   `pip-audit==2.10.1 --desc on .` audit are unchanged. Nothing is waived, skipped or relaxed.

Sparse checkout is safe for the exact-commit proof because sparse-checkout filters the **working tree only**:
the git index still carries all 4095 entries of the base tree, so the applier's `git write-tree` reproduces the
full reviewed tree. Measured in an isolated probe: 42 materialised files, 4095 index entries, apply exit 0,
`HEAD` `af4409…`, tree `231f1d8b…`, tracked status clean, `--verify` exit 0.

The `stage2-evidence-protocol` job is also a gate consumer: its standalone suite runs the localization gate
against the live tree, so it too must see the recorded pin. It now transports the same effective commit (its
sparse checkout additionally materialises `/pyproject.toml`) and re-verifies at the fixture boundary. Its
**byte fixtures stay valid and meaningful**: `vendor_ci_inputs.json` keeps the same `frappe/locale/ar.po`
(`ad0c7b27…`) and `script_manager.js` (`e7204be9…`) digests, and only its recorded `apps.frappe.commit`
identity moves to `af4409…`, which is exactly the commit now checked out in that job. Leaving the job on the
public base would have failed its own gate suite against the recorded pin — the opposite of "not breaking the
fixture job". Measured on the same app tree: with the base vendor the 101-test standalone suite fails exactly
`test_scoped_positive_run_passes` (vendor-delta pin mismatch, exit 1); with the transported commit it passes
all 101 (exit 0).

### Controlled vendor pin — scoped one-field re-record, coordinator technical review

`construction/data/localization/vendor_catalog_baseline.json` changes exactly one functional value:
`apps.frappe.commit` `2871914b…` → `af440917…`. The catalog inventory, `count`, `msgid_sha`, `po_sha`
(`ad0c7b27…`), the ERPNext record and the top-level `recorded_utc` are unchanged. A `commit_pin_review`
block records the date, the technical basis, the empty catalog delta and the fact that this is **coordinator
technical review of an owner-approved private isolated candidate — NOT human approval and NOT an upstream
support claim**. `scripts/check_localization_gates.py` updates only its frozen-contract source digest for
that file (the contract pins the exact bytes of its inputs and fails closed otherwise). The dated
`stage2_current_measurements.json` record (and its `.md` twin) follows with the same single digest in
`frozen_contract_from_these_measurements.source_pins`, with an explicit 2026-10-21 follow-up note: no measured
count changed because the vendor catalog bytes the counts were measured from are identical; only the recorded
commit identity moved. The 2026-10-20 measurement artifacts themselves are untouched.

Governance inspection (recorded, not assumed): `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` §2 (routine
engineering choices and already authorized actions need no repeated owner confirmation; never invent approval),
`AGENT_WORKFLOW.md` (governed sequence; owner commit authorization is given for this round), the work-item
scope `docs/ai/work-items/dependency-security-remediation/SCOPE.md`, and the producers/consumers
`scripts/vendor_upgrade_delta.py` / `scripts/check_localization_gates.py`. No scoped rule requires a *human*
decision for this exact commit pin: the reviewed-delta requirement applies when the **catalog** differs from
the committed inventory (`--update-baselines` refuses otherwise), and here the catalog is byte-identical, so
the pin moves through the tool's inventory-identical path. The earlier statement that human review was
mandatory was our own interpretation, not a cited rule.

### Measured gates (isolated probes, no shared write)

| Run | Vendor `HEAD` | Baseline pin | Shape | Exit | Errors |
|---|---|---|---|---|---|
| before | `2871914b…` | `2871914b…` (old) | Linters sparse | 0 | 0 |
| before (blocker) | `af4409…` | `2871914b…` (old) | Linters sparse | **1** | 1 — `vendor-delta: frappe HEAD af4409… != pinned 2871914b…` |
| after | `af4409…` | `af4409…` | Linters sparse (42 files) | **0** | 0 |
| after | `af4409…` | `af4409…` | full checkout (4095 files) | **0** | 0 |
| after, binding control | `2871914b…` | `af4409…` | Linters sparse | **1** | 1 — base vendor rejected |
| full local mode | `af4409…` | `af4409…` | full checkout | 1 | 30 pre-existing historical evidence-binding errors; the vendor-delta error is gone (was 31) |

Vendor bytes are unchanged between the two pins: `frappe/locale/ar.po` `ad0c7b27…` and
`script_manager.js` `e7204be9…` at both commits; `git diff --name-status 2871914b af4409` is
`M pyproject.toml` only; ERPNext stays `7474d9e…` with `erpnext/locale/ar.po` `54c346cc…`.

### G10 / qualification status (2026-10-21)

**The candidate is NOT YET qualified.** This round aligns CI wiring and records a reviewed pin inside the
owner-approved private isolated candidate. It does not close, re-open or re-qualify the G10 ledger entry in
`docs/ai/work-items/customer-release-gap-fixes/STATUS.md` (still the 2026-10-06 alignment), no historical gate
is declared closed, and no CI run, push, PR, publication, runtime rebind, site or business qualification was
performed. A real GitHub-runner execution and the site/DB matrix remain unproven and separate.
