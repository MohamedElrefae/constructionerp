# F28 — Delivery artifact hygiene review (wheel/sdist and checkout paths)

**Compliant rebuild verification — 12 October 2026:** Retained Flit3.12 archives independently match the recorded SHA-256s and all member names. Wheel metadata changes are METADATA/RECORD/WHEEL; sdist metadata change is PKG-INFO; app bytes are unchanged. F28-D005 is closed for the backend-range action. Source/input binding, customer-delivery decision and installation/replay remain separate open F28 work. The earlier diagnostic-build observations below are retained.

**F29 verification follow-up:** [Documentation/preservation review](construction_foundation_documentation_organization_review_2026-10-12.md) and [per-member verification JSON](construction_foundation_delivery_artifact_verification_2026-10-12.json) independently confirm archive hashes and contents. The build used Flit 4.1.0 outside the declared <4 range, and 706 app members are untracked build/runtime outputs. Compliant rebuild and input binding are additional F28 prerequisites.

**Date:** 12 October 2026
**Candidate:** develop `c9e6803c5ac63073aeb0b166c779844d29051d8d`
**Program:** [Foundation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md) · [F25 review](construction_foundation_runtime_asset_consistency_review_2026-10-12.md)
**Status:** Artifact inspection complete at source level; F28 **In progress** pending installation-behavior and deployment-export checks on the F02 target.
**Classification:** Confidential — internal

## 1. What was actually built and inspected

`flit_core` 4.1.0 was installed **only** into the isolated directory `/tmp/opencode/f28-tools` (bench venv and site untouched; no dependency resolution, no install into any environment). Both artifacts were built from the repo root into `/tmp/opencode/f28-artifacts` and fully listed; hashes and complete file lists are in [the evidence JSON](construction_foundation_delivery_artifact_evidence_2026-10-12.json).

| Artifact | Build backend | SHA-256 (first 16) | Files |
|---|---|---|---|
| `construction-0.0.5-py3-none-any.whl` | flit_core 4.1.0 (**out of declared range** — diagnostic only) | `2b6ff4bfab0e9f85…` | 1229 = 1225 app + 4 dist-info |
| `construction-0.0.5.tar.gz` | flit_core 4.1.0 (**out of declared range** — diagnostic only) | `279ae91b8f1cceeb…` | 1229 = 1225 app + 4 metadata files |
| `construction-0.0.5-py3-none-any.whl` | **flit_core 3.12.0 (compliant)** | `fc8bd4d7c4343c2d…` | 1229 = 1225 app + 4 dist-info |
| `construction-0.0.5.tar.gz` | **flit_core 3.12.0 (compliant)** | `a263c960a5559fb9…` | 1229 = 1225 app + 4 metadata files |

**Compliant rebuild (F28-D005 closure action):** flit_core 3.12.0 installed into a separate isolated directory only. It produces **identical member sets** to the diagnostic build (1,229/1,229); only `dist-info/{METADATA,RECORD,WHEEL}` differ in bytes — **zero app-member bytes differ**. The declared sdist exclusions therefore still exclude nothing inside the package — now verified on the in-range backend rather than inferred from the out-of-range build. The compliant artifacts supersede the diagnostic pair for qualification; both are retained as evidence.

**F28-D006 confirmed by direct member-vs-git comparison:** of the 1,225 app members, **706 are absent from git tracking** — 704 generated `theme_*.css` outputs plus the 2 `public/dist/` bundle outputs. All 6 tracked `theme_*` files do ship. HEAD alone cannot bind the untracked delivered bytes; a reviewed input/build manifest or deterministic isolated rebuild is required before package qualification. A blanket `theme_*` exclusion would remove legitimate runtime theme assets — distinguish runtime output from test residue first.

**F29 verification:** the wheel and sdist contain identical sets of 1,225 app files with identical bytes; their four non-app metadata/source-root files differ. The two declared packaging exclusions (`[tool.flit.sdist] exclude = ["orchestrator/", "tests_offline/"]` in pyproject; `find_packages(exclude=("orchestrator", …, "tests_offline", …))` in setup.py) target **root-level directories outside the `construction` package** — they do not remove the observed in-package residue, confirmed for both backends above.

## 2. What a customer would actually receive (Python package path)

Recorded scan result: no matching secrets/credentials/config/dump/backup classes were reported by the pattern scan over the 1,229-file inventories (the only SQL file identified was DDL-only setup text). This is a scoped scan finding, not a blanket absence-of-sensitive-content certification. No `docs/` work-item evidence, SESSION_MEMORY or AI-orchestration content is included in the package.

However, both artifacts ship substantial dev residue **inside** the package, because nothing excludes it:

| Category | Count | Examples |
|---|---|---|
| Theme CSS pattern (704 untracked outputs + 6 tracked theme files; intended runtime assets need separate review) | 710 | `public/css/theme___dict__.css`, `theme_null.css`, `theme_FALSE.css`, `theme_TestLoginTitle30Chars.css` |
| Deprecated React `.jsx` components | 8 | `public/js/components/UltimateButton.jsx`, `UnifiedCRUDForm.jsx`, … (ADR-008 retained; shipped to customers) |
| Screenshot PNGs | 12 | `construction/tests/02_construction_module.png` … `19_print_format.png` |
| Test-suite + session fixtures | ~90 | 80+ `test_*.py`/`test_*.js`, `tests/tools/sessions/*.session` (4), `tests/package-lock.json` |
| Diagnostic/scratch code | 4 | `remove_important.py`, `public/js/dropdown_diagnostic.js`, `quick_diagnostic.js`, `scratch/survival_test.py` |
| Built bundle + **source map** | 2 | `public/dist/js/construction.bundle.RGKW7W7V.js` + `.js.map` (source map exposes original sources) |
| Test-lab pages | 2 | `public/theme_test_lab.html`, `public/vite_preview.html` |
| Misc hygiene | 3 | `construction/.gitignore` (leaks ignore policy), setup SQL script, `public/.gitkeep` |

## 3. The real customer delivery path (checkout) delivers far more

`bench get-app` obtains a **git checkout**: all **2,134** tracked files, not the wheel. That path includes:

| Top-level | Files | Note |
|---|---|---|
| `docs/` | 1450 | Mixed guides and internal work-item evidence/data; requires audience/content selection before customer delivery |
| `construction/` | 519 | The app package (see §2 residue) |
| `orchestrator/` | 49 | AI orchestration tooling (devtools) |
| `scripts/` | 44 | Includes engineering/setup scripts |
| `dashboard/` | 31 | Dev dashboard |
| `tests_offline/`, `.github/`, `construction-erp-coder/` | 12 | Offline tests, CI workflows, coder tooling |
| `backups/` | 4 | **Git stash patches** (`backups/stashes/stash-*.patch`) — working-tree history, not app content |

So the two delivery paths have opposite problems: the **package** is mostly clean but carries dev junk; the **checkout** carries the working tree's private evidence and tooling. Neither currently matches a reviewed customer-delivery definition. F28's completion criteria require an explicit artifact inventory decision per delivery path — this review supplies the facts; the decision and enforcement remain.

## 4. Issues logged

| Issue | Evidence class / impact | Required action | Package |
|---|---|---|---|
| F28-D001 | 710 theme-pattern files (704 untracked outputs + 6 tracked) + 8 legacy `.jsx` + 12 PNGs + 4 diagnostics/scratch files + 2 test-lab pages ship in wheel/sdist; observed in-package residue is not removed by the declared exclusions (verified on both the out-of-range and compliant backends) | Decide customer artifact inventory; exclude generated/test residue at the packaging level (not by deleting source/history); verify hooks still resolve after any exclusion | F28/F26 |
| F28-D002 | Source map `construction.bundle.RGKW7W7V.js.map` ships with the bundle | Confirm dist bundle is the shipped asset path (F25-D003 still open); ship without `.map` or justify; record build/hash identity | F28/F25 |
| F28-D003 | Checkout path delivers 1,615 tracked files outside construction/ incl. private `docs/`, orchestrator, dashboard, stash patches | Define the actual supported delivery route (package vs curated checkout/export) with owner authority; no public publication is authorized by this review | F28/F39 |
| F28-D004 | Version metadata: Flit 0.0.5 vs legacy setup.py 0.1.0 (from F25) is now reflected in an actual built artifact | Canonical build policy decision; record which metadata ships | F25/F28 |
| F28-D005 | Diagnostic build used flit_core 4.1.0, outside declared `>=3.4,<4` | **Compliant rebuild performed 2026-10-12 with flit_core 3.12.0** (identical member sets; only dist-info bytes differ). Remaining: the compliant artifacts still require an input/build manifest (D006) and F13's runtime before install/replay qualification | F28/F13 |
| F28-D006 | 706 app members (704 generated theme CSS + 2 dist outputs) are absent from git tracking; HEAD cannot bind delivered bytes | Reviewed input/build manifest or deterministic isolated rebuild; distinguish runtime theme assets from test residue before any exclusion | F28 |

No application source was modified; no exclusion was changed by this review. Nothing was published, uploaded or installed.

## 5. Installation and upgrade behavior — not yet measured

Wheel/sdist content does not establish install behavior on a Frappe bench. Still owed (on the F02 target, after F13 resolves the runtime): install from the chosen artifact, verify `after_install` hook execution (15 steps), fixtures/roles/print-format creation, then a representative upgrade with repeated-migrate replay (F31). The wheel's `Requires-Dist` metadata also still reflects the F25-D001 conflict surface.

## 6. Input/build manifest (F28-D006 closure action)

A per-member manifest now binds every delivered byte: [build input manifest](construction_foundation_build_input_manifest_2026-10-12.json) records all 1,225 app members with artifact SHA-256 (wheel and sdist), git-tracking status, worktree presence/hash and provenance class.

| Class | Members | Finding |
|---|---|---|
| Tracked source, worktree bytes == artifact bytes | 519 | Zero mismatches — the tracked half of the package is exactly the HEAD worktree content |
| Untracked — generated theme CSS residue | 704 | **Provenance established:** the current controller (`construction_theme.py` `_write_static_css_file`/`get_theme_css_path`, lines 821–882) writes theme CSS to **site** storage (`frappe.get_site_path("public","files","css")`), never to the app package tree; no package-dir writer exists. These files (incl. test-flavored names `theme___dict__.css`, `theme_null.css`, `theme_FALSE.css`) are residue from historical runs of an older writer path — not runtime assets and not regenerable by the current code |
| Untracked — dist build outputs | 2 | `public/dist/js/construction.bundle.RGKW7W7V.js` + `.map`: **no root package.json/Vite config exists in the repo and no hook/template/HTML references them** — generator identity unrecorded; stale build output |

Determinism: two independent compliant builds (flit_core 3.12.0) from the same worktree produced identical member sets with zero app-byte differences, and the out-of-range diagnostic build also matched on app bytes. For a frozen worktree the artifact is therefore reproducible; it remains **not** identifiable from HEAD alone for the 706 untracked members — hence the manifest.

## 7. Verification

- Built both artifact pairs with the Flit backend from the declared pyproject into isolated temp directories: diagnostic build on flit_core 4.1.0 (out of range, retained), compliant build on flit_core 3.12.0. Complete file lists, SHA-256 digests, the compliant/diagnostic byte comparison, checkout inventory and top-level counts are recorded in the JSON evidence artifact.
- Untracked-member count computed with `git ls-files -z` (whitespace-safe); an earlier whitespace-split computation mis-counted two space-containing tracked theme filenames and was corrected to 706 (704 + 2).
- Pattern scan for secrets/credentials/backups/VCS/private-docs across all artifact files: none of the secret/backup classes found (SQL DDL and `.gitignore` noted). Scoped pattern-scan result, not a content certification.
- F29 independent verification re-hashed every archive member and matched all names/hashes; the app-member equivalence above incorporates that check.
- Startup checks unchanged and passing (21+1 schema owners; context 11/0). HEAD unchanged; no application file modified; no site, suite, migration, commit or push.
