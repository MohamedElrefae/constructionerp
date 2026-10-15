# Acceptance dataset + non-reproduction proofs (lab fresh site `f31fresh-clean.localhost)

Date: 2026-10-15. All data below is ACCEPTANCE data with documented expectations, kept
separate from legacy records (which live on `f31upgrade.localhost` and are preserved
unchanged except the approved D004 deletion). No legacy quantity, approval or total was
invented or altered.

## Documented expectations

| Entity | Key data | Expected |
|---|---|---|
| Company | ACC Acceptance Co, EGP, Egypt | exists |
| Project | ACC-001 (name PROJ-0001) | exists |
| BOQ Header | ACC BOQ 01, Draft → Locked | total 6,200.00 |
| Item 1 | ACC Excavation, 100 × 50 | line 5,000.00 |
| Item 2 | ACC Backfill, 40 × 30 | line 1,200.00 |
| Personas | f31-pm (PM), f31-maintainer (Cost DB), acc-eng (Site Engineer), all scoped to ACC company/project | valid scopes |

Lab-seeding note: the fresh lab site shipped zero Warehouse Types / UOM Nos / Item Group
"All Item Groups" (rehearsal has all three). Seeded standard masters (Transit, Nos/M3/Meter/Kg,
All Item Groups) as lab setup — not product behavior. One leaf yields one auto-item; the
second item needed a second leaf (script corrected mid-run, recorded here).

## Non-reproduction proofs (current workflows, ordinary personas)

1. **Wrong-total lock (D001 mechanism):** PM set `total_contract_value = 1.00`, walked
   Draft → Pricing → Frozen → Locked. The controller **recomputed 6,200.00 on save** —
   totals are system-derived, not user-writable. D001-style wrong totals cannot be produced
   through this path. Header now Locked at the correct total.
2. **Double approval (D003 mechanism):** PM approved analysis A (rate 100) → Approved;
   second analysis B (rate 110) submitted → **ACCEPTED with proper supersession**
   (B supersedes A; A → Superseded; exactly one active approval). The legacy multi-Approved
   state cannot be produced here — it predates supersession enforcement. Both proof analyses
   cancelled and deleted afterwards; item manual costs intact (50.0/30.0), zero analyses remain.
3. **Revision-delete guard:** no baseline revisions exist on the clean header to attempt
   against; the guard stands proven by product tests plus the F24-D002 teardown refusals
   observed live. No undeletable residue was manufactured on the clean site.
4. **Engineer certification (SoD):** acc-eng setting `certified_qty` → **REFUSED**
   ("Only Project Manager, Construction Owner, or System Manager can certify");
   the same session recording `measured_executed_qty = 5` → **ACCEPTED**. Both halves verified.
