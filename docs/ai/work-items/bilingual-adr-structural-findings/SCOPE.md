# Scope Descriptor — bilingual-adr-structural-findings

**Work item:** `bilingual-adr-structural-findings`
**Branch:** `feature/bilingual-adr-structural-findings`
**Status:** `COMPLETE` — ADR structural findings reconciled and documented in `bilingual-performance-sla.md`; 19/19 reconciliation verified, 153/153 regression matrix (12 modules) verified, dual manifests verified
**Base commit:** `3e71dec74efdf1950d44e5db8d9bf19d67bceae0` (develop clean; `bilingual-narrative-sanitizer` closed)
**Date:** 2026-10-03
**Authority:** owner directive in session; resolves structural findings recorded in `docs/ai/work-items/bilingual-adr-evidence-correction/SCOPE.md` §3
**Scope:** documentation-only governance hardening for `docs/ai/work-items/bilingual-performance-sla.md`, evidence verification, dual manifest reconciliation

---

## 1. Background & Context

In `bilingual-adr-evidence-correction` (`baf9bea` / `87e88cd`), empirical reconciliation confirmed 19/19 active master rows in `bilingual-performance-sla.md` §4 against committed evidence artefacts. That sweep surfaced six open structural findings in §3 of its SCOPE descriptor, plus one pre-existing test assertion. Finding #7 (Item state assertion in `test_bilingual_service.py`) was subsequently resolved in `46aa201`.

This work item formally resolves the remaining six structural findings within `docs/ai/work-items/bilingual-performance-sla.md` without altering the parsed 19-row empirical baseline in §4.

---

## 2. Resolutions of the Six Structural Findings

### Finding 1: Mixed Measurement Protocols in §4
- **Reality:** 16 rows use `n=50` interleaved nearest-rank P95; 2 rows (`BOQ Header`, `BOQ Structure`) use `n=100` min-of-rounds over 5 rounds; 1 row (`Account`) uses `n=100` min-of-rounds with `txt=CT-RP3-`.
- **Resolution:** Clarified in §5 that Tier 2A strictly requires `n=100` min-of-rounds to arbitrate the tight $1.15\times$ bound against sub-millisecond scheduler noise. Tier 2B's $1.50\times$ band is a documented architectural trade-off for sub-millisecond queries, where an `n=50` nearest-rank sample width is statistically adequate to detect regressions beyond $1.50\times$.

### Findings 2 & 3: Unified Root Cause — Materially Different SQL & Additive Cost Model
- **Reality:** §2 previously modeled bilingual overhead as a constant $\sim 150\text{–}200\,\mu\text{s}$, but §4 exhibits overheads ranging from $-0.228\,\text{ms}$ to $+0.456\,\text{ms}$, with `BOQ Header` ($-0.207\,\text{ms}$, $0.7568\times$) and `BOQ Structure` ($-0.228\,\text{ms}$, $0.7685\times$) showing negative overhead.
- **Root Cause:** Baseline native `search_link` and governed `searchable_dropdown` issue materially different SQL. Baseline executes `IFNULL(1/NULLIF(LOCATE(...)))` scoring, multi-column `ORDER BY` (`_relevance DESC, idx DESC...`), and filters across additional doctype `search_fields` (e.g. `parent_structure`, `project_name`). Governed search issues a plain `LIKE` query with `ORDER BY modified DESC` and delegates multi-lingual ranking (`exact > prefix > substring`) to Python over `RANK_WINDOW`.
- **Resolution:** Reconciled in §2 by linking the additive model to standard single-table lookups and documenting that for composite/hierarchical doctypes, governed SQL avoids expensive SQL relevance evaluations, resulting in negative relative overhead ($< 1.0\times$) while easily meeting Tier 1 ($\le 1.50\,\text{ms}$) and Tier 2B ($\le 1.50\times$). Clarified in §3 that Tier 2 measures end-to-end framework execution comparison, not an isolated diff on identical SQL.

### Finding 4: Result Set Divergence on Production Queries
- **Reality:** The empirical parity claim (`match_sets_equal: true`) holds for the canonical fixture prefix (`CT-*`). Broad or unanchored production queries diverge because governed search ranks by bilingual match specificity and caps at `page_length`.
- **Resolution:** Clarified in §1/§2 that fixture equality establishes baseline parity on synthetic benchmarks, while governed production ranking intentionally refines search results to Arabic/English relevance.

### Finding 5: Account Baseline Reproduction vs. Frozen Governance Pin
- **Reality:** Current environment execution measures $\sim 2.4\,\text{ms} \to 2.2\,\text{ms}$ ($0.92\times$) for Account versus the recorded $1.322\,\text{ms} \to 1.482\,\text{ms}$ ($1.1210\times$).
- **Resolution:** Clarified in §1 and §4 that §4 records frozen calibration benchmarks tied to the immutable Stage-3 evidence artefacts in §7, serving as the governing historical pin against machine/environment jitter.

### Finding 6: UOM Tier-Boundary Sensitivity
- **Reality:** UOM baseline ($0.960\,\text{ms}$) is within 4% of the $1.0\,\text{ms}$ Tier 2A threshold.
- **Resolution:** Documented in §5 that an ad-hoc local observation under the canonical $n=100$ protocol measured $1.254\,\text{ms}$ baseline with ratio $0.668\times$, passing both Tier 2B ($\le 1.50\times$) and Tier 2A ($\le 1.15\times$). This observation is explicitly noted as non-pinned, with §4 retaining its committed $0.960\,\text{ms}$ evidence binding.

---

## 3. Governance & Parsing Constraints Respected

1. **§4 Table Invariant:** §4 table retains exactly 19 rows. No lines matching `ROW_RE` (`| <doctype> | <base> ms |`) added in §§5–7.
2. **Reconciler Integrity:** No measurement-schema JSON files emitted in this work item's evidence directory; only `MANIFEST.json` and `.log` files are created.
3. **Dual Manifest Digest Pinning:**
   - `bilingual-adr-evidence-correction/evidence/MANIFEST.json` digest for `bilingual-performance-sla.md` refreshed and re-verified.
   - `bilingual-adr-structural-findings/evidence/MANIFEST.json` authored and verified.
4. **Primary Invariants:** 0 diff lines to `bilingual_service.py`, `search.py`, `bilingual_registry.json`, or vendor repositories.

---

## 4. Invariants Preserved

- `construction/services/bilingual_service.py` — 0 modified lines
- `construction/searchable_dropdown/api/search.py` — 0 modified lines
- `construction/data/bilingual/bilingual_registry.json` — 0 modified lines
- `apps/frappe`, `apps/erpnext` — 0 modified lines
- Canonical regression matrix — 153/153 green across 12 modules
- Reconciliation — 19/19 OK
