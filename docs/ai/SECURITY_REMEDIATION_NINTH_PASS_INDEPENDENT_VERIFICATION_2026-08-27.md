# Security Remediation Ninth-Pass Independent Verification

**Review date:** 2026-08-27  
**Branch:** `release-candidate-v1`  
**Verified snapshot:** `96063c0e0da407f438a087378c51275513404198`  
**Basis:** direct diff/source review, isolated counterexample probes, live MariaDB inspection, static checks, targeted tests, two complete suite runs, and a controlled before/after residue comparison. The supplied eighth-pass summary was treated as a claim, not as evidence.  
**Code verdict:** **ONE NEW MEDIUM DEFECT REPRODUCED.**  
**QA verdict:** **PARTIALLY CLOSED; two new tests do not prove what they claim.**  
**Release verdict:** **HOLD / NO IMMUTABLE TAG.**

## Executive conclusion

The migration-survival additions are well targeted and close the previously identified index-definition and commit-failure coverage gap. The exact snapshot also reproduces 429 passing tests twice and is database/filesystem hermetic under a consistent comparison.

The eighth-pass conclusion is nevertheless too strong. A legacy theme-switch module remains directly whitelisted even though the hook uses the remediated implementation. That alternate dotted API accepts an invalid lowercase enum that the remediated endpoint rejects and writes it directly to `User.desk_theme`. This was reproduced as a permission-light website user inside a rolled-back transaction.

Two newly added security tests are also false or ineffective evidence: the fatal guard subprocess can pass because its own failed class-name assertion prints the expected text, and the theme rollback test raises during validation before any write occurs. The production guard and rollback behavior passed independent probes, so these are presently QA defects rather than evidence of failure in the remediated implementations.

The fresh/upgrade lifecycle, complete real-HTTP least-privilege matrix, and `PERF-BOQ-001` acceptance/evidence gates also remain open.

## Independent evidence

| Check | Independent result |
|---|---|
| Exact HEAD | `96063c0e0da407f438a087378c51275513404198` |
| Change scope from `8fdd296` | Only two test files and the supplied eighth-pass document changed; no production fix was added |
| New test methods | 10: security suite 19→23 and migration suite 7→13. The “11 tests” statement counts a strengthened existing path as though it were a new test |
| Tracked app source | Clean; `git diff --binary HEAD` has the empty SHA-256 `e3b0c442...b855` |
| Frappe / ERPNext | Clean |
| Untracked files | Only the independent seventh/eighth/ninth audit artifacts; they were not loaded by the suite |
| Static checks | `ruff`, Python compilation, JS syntax, and `git diff --check` passed |
| Targeted migration suite | 13/13 passed |
| Targeted adversarial suite | 23/23 passed, but two passing cases are not valid evidence as described below |
| Full run 1 | 254/254 in 74.132 s and 175/175 in 53.461 s; total 429/429 |
| Full run 2 | 429/429; command exit 0; second cohort 175/175 in 53.136 s |
| Scope baseline | `enable_scope_context = 0` after both runs |
| Business residue | `Security BOQ %` = 0; `MR Recon %` = 0; `VO-RECON-TEST-1` MR links = 0 |
| MR invariant | Exact one-column UNIQUE BTREE index on `custom_variation_order_active` |
| Controlled public-file comparison | Stable across the second full run: 127 files, manifest `85870a6b...09c0` |

## Prioritized issue matrix

| Severity | File and location | Risk in plain language | Exact fix / prompt for the coding agent |
|---|---|---|---|
| **MEDIUM – DATA INTEGRITY** | `construction/overrides/switch_theme.py:10-93`; active hook at `construction/hooks.py:213-215` | The old implementation is not dead: its decorator exposes `construction.overrides.switch_theme.switch_theme` as a second RPC endpoint. It bypasses the remediated validation and can directly store lowercase `dark` in the Select field. Two different public implementations now enforce different contracts. | **Prompt:** “Eliminate the alternate theme-switch contract. Search for external compatibility requirements. Prefer deleting/unwhitelisting `construction.overrides.switch_theme.switch_theme`; if compatibility is required, replace it with a thin deprecated shim that delegates to `switch_theme_simple.switch_theme(theme=..., theme_name=...)` and performs no independent reads/writes. Add a regression proving the legacy dotted route is unavailable or enforces exactly the strict enum, authentication, rollback, and no-interior-commit contract. Search for and remove any remaining references to the legacy module.” |
| **MEDIUM – QA FALSE POSITIVE** | `construction/tests/test_security_audit_remediation.py:1192-1238` | `str(ReportScopeEnforcementError(...))` contains the message, not the class name. The child assertion therefore fails. The parent then finds `ReportScopeEnforcementError` in that assertion traceback and accepts any nonzero exit. The test passes for the wrong reason and runs the same subprocess twice. | **Prompt:** “Rewrite the fatal guard child probe to assert `type(ex).__name__ == 'ReportScopeEnforcementError'` and `'Refusing startup' in str(ex)`, print a deliberate `EXPECTED_FATAL_GUARD` marker, then exit exactly 3. Run it once and assert `returncode == 3`, the deliberate marker is present, and the import-success marker is absent. Do not accept arbitrary nonzero codes or incidental traceback text.” |
| **MEDIUM – QA INEFFECTIVE TEST** | `construction/tests/test_security_audit_remediation.py:1424-1444`; validation at `construction/overrides/switch_theme_simple.py:88-94` | Emptying `_STANDARD_THEMES` makes `Dark` fail validation before `set_value` executes. The equality assertion merely confirms that nothing was written, not that a post-write failure rolls back. | **Prompt:** “Replace the rollback test with a true post-write failure injection. Wrap the real `frappe.db.set_value` so the first User desk-theme write succeeds and then raises a sentinel exception, call `switch_theme`, assert the exact exception is re-raised, and assert the previous database value is restored. Keep the outer test transaction rollback and verify the spy actually executed the write.” |
| **LOW – REPORT ACCURACY** | `docs/ai/SECURITY_REMEDIATION_EIGHTH_PASS_FIXES_2026-08-27.md` | The report says 11 focused tests were added. The diff contains 10 new test methods plus one strengthened existing path. This does not change runtime risk, but release evidence must distinguish tests from modified helpers/assertions. | **Prompt:** “Correct the eighth-pass evidence to say ‘10 new test methods plus one strengthened existing subprocess path’ and record the exact before/after method counts.” |
| **HIGH – RELEASE GATE** | Fresh-site and legacy-upgrade lifecycle | Unit coverage cannot prove that a blank install and a real legacy duplicate-MR database migrate successfully and idempotently. | **Prompt:** “From the exact successor SHA, create an isolated blank site and an isolated legacy-upgrade fixture containing two active MRs for one VO plus cancelled history. Capture install/migrate exit codes and logs; verify deterministic reconciliation, preserved cancelled history, exact generated column/index, idempotent second migrate, and clean framework trees.” |
| **HIGH – RELEASE GATE** | Real-HTTP authorization matrix | The recorded HTTP check covers only two scope endpoints and four role states. It does not cover the complete externally reachable security surface or provide committed raw evidence. | **Prompt:** “Run separate authenticated HTTP sessions for Guest, permission-less user, Website User, Site Engineer, Project Manager, Accounts User, and System Manager. Cover scope detail/display, both theme routes, VO create/transition/idempotency, BOQ preview/commit, MR generation, repricing, reports, and private files. Capture request method/path, status, normalized body, expected decision, and database before/after state; clean up exact probe IDs.” |
| **HIGH – RELEASE GATE** | `PERF-BOQ-001` | There is still no 1k/10k end-to-end evidence and no authorized human risk acceptance. A 100-item time-only unit test does not establish production ceilings. | **Prompt:** “Run 100/1k/10k BOQ imports through the real API, including final rollup/reload. Record elapsed time, SQL count, peak memory, lock/wait time, and correctness totals. Otherwise obtain written acceptance from a named human owner with an exact deadline, maximum supported import size, monitoring threshold, rollback trigger, and client-impact statement.” |

## Reproduced counterexamples

### Reachable legacy theme API

The probe used enabled Website User `test3@example.com`, performed no commit, and rolled back to the original value:

```text
STRICT_REJECTED True
LEGACY_WHITELISTED True
VALUES Light dark Light
```

This proves that the active strict endpoint rejects lowercase `dark` while the alternate public endpoint writes it.

### Fatal-guard test false positive

Running the embedded child logic showed:

```text
ACTUAL_EXCEPTION_TYPE ReportScopeEnforcementError
CLASS_NAME_IN_STR False
AssertionError: expected fatal class, got: ReportScopeEnforcementError(...)
```

The parent accepts that failed assertion because the traceback happens to contain the searched class-name fragment.

### Production rollback counter-probe

A separate post-write injection called the real `set_value`, then raised. The production function re-raised and restored `Dark` after temporarily writing `Light`. Therefore the implementation's rollback path works in the tested scenario; the committed test simply does not exercise it.

## Release decision

`96063c0` is **not eligible for a final GO or immutable tag**. The migration tests are useful and the 429-test suite is repeatably green, but one reachable conflicting RPC implementation must be removed or made contract-identical, the two misleading tests must be corrected, and all three external release gates must be completed. Tag only the exact clean successor SHA after repeating the static checks, focused counterexample tests, full suite, and residue comparison.
