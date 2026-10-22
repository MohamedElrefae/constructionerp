# Stage 5 — Wave 1 masters readiness inventory (2026-09-20, data-only read)

## Purpose

Prepare Wave 1 (Item, Customer, Supplier, Cost Center, Warehouse, Project) of the
ERP Arabic bilingual data program per the end-to-end plan §11 row 5. This is a
**read-only inventory and readiness record**: no Arabic masters data was
proposed, reviewed, dry-run, or imported in this pass, and no live row was
modified.

## Registry state (merged `develop` @ `4457de2`, test site `v16.localhost`)

| Doctype | Registry Arabic field | Registry state | Custom field installed on site | Arabic values populated |
|---|---|---|---|---|
| Item | `item_name_ar` | `schema_installed` | yes | **0 of 43** |
| Customer | `customer_name_in_arabic` | `schema_installed` | yes | **0 of 12** |
| Supplier | `supplier_name_in_arabic` | `schema_installed` | yes | **0 of 10** |
| Cost Center | — | not mapped | (registry) | — |
| Warehouse | — | not mapped | (registry) | — |
| Project | — | not mapped | (registry) | — |

`Cost Center`, `Warehouse`, `Project` remain outside
`bilingual_registry.json` (no `planned` mapping yet).

## Inventory (live, read-only)

- **Item (43):** mostly ERPNext vendor test fixtures (`_Test*`, and prior test
  scaffolding `TEST-CONC-<hex>` ×10). Candidate non-fixture masters:
  `OH-SITE-ADMIN-001`, `SUBCONCRETE-001`, `PLANT-MIXER-001`, `LAB-MASON-001`,
  `Consulting`, `Macbook Pro`, `Photocopier`, `138-CMS Shoe` — data quality is
  mixed (`LAB-MASON-001` contains a stray backtick; `Test Esstimate` is a
  misspelled test item).
- **Customer (12):** vendor `_Test*` fixtures except `Prestiga-Biz`.
- **Supplier (10):** ERPNext vendor `_Test*` fixtures only.
- **Project (11):** `PROJ-0001..PROJ-0011` — genuine master records.
- **Cost Center (46):** Elrefae chart (`Elrefae - E`, `Main - E`) plus
  multi-company vendor test fixtures (`_TC*`).

## Search readiness (verified live)

`search_bilingual` resolves all three `schema_installed` Wave-1 doctypes with
0 Arabic values populated: English/code queries match (`Prestiga-Biz`,
`PLANT-MIXER-001`, `SUBCONCRETE-001`); Arabic-only queries (`مباشر`) return an
empty result cleanly (`label_mode: english`) — no crash, no silent `[]`
SQL failure path (Stage 1A contract).

## Governance findings and recommendation

1. **ERPNext vendor `_Test*` fixtures are excluded from any future Wave-1
   Arabic migration** by governance: they belong to the vendor test corpus and
   are reset/relaundered by vendor test runs; translating them would corrupt
   both suites and evidence.
2. **Real master data on this non-production test site is minimal** (a handful
   of candidate items, one customer, 11 projects). A full Stage 5
   proposal/panel/dry-run/IMPORT cycle is only meaningful once production
   master data exists — i.e., the Wave-1 data migration naturally attaches to
   Stage 8 production rollout or to real data entry on the target site.
3. **Remaining registry gaps for Wave 1** (`Cost Center`, `Warehouse`,
   `Project` mappings, and per-DocType `identity_section`/tree UI flags) are
   config-only and can be enacted once a decision on their scope fields is
   made (Project already has scope-context usage; Warehouse/Cost Center carry
   hierarchy semantics similar to Account).

## Owner decision requested

Choose the Wave-1 data path:
- **(a) Defer data migration** to Stage 8 production rollout with real masters (recommended), or
- **(b) Pilot now** on the candidate non-fixture masters listed above, following the full D4/D5 proposal/panel/dry-run/IMPORT cycle.

Until then, Stage 5 status remains: readiness recorded, data migration not started.
