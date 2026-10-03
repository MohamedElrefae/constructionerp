# RFC — Transactional Link Resolution

**Status:** `APPROVED` (owner decision, 2026-10-03)
**Date:** 2026-10-03
**Prerequisite:** `bilingual-wave2b-transactions/SCOPE.md` §7
**Unblocks:** deferred ledgers `Asset`, `Brand`, `Terms and Conditions`
**Authoritative sources cited inline:** `construction/searchable_dropdown/api/search.py`,
`construction/services/bilingual_service.py`, `construction/data/bilingual/bilingual_registry.json`,
`construction/hooks.py`, `construction/public/js/searchable_dropdown/searchable_dropdown.js`

---

## 1. Context & Historical Background

### 1.1 The wave 2b deferral

`bilingual-wave2b-transactions/SCOPE.md` §7 preserved a path forward for transactional
bilingual search and bound it to three prerequisites:

1. **An RFC renegotiating the zero-service-edit invariant**, "stating plainly that the
   invariant ends and why the trade is worth it."
2. **A deliberate `RANK_WINDOW` design** covering multi-table candidate windows and the
   overflow-throw contract, with boundary tests.
3. **A matched-set equivalence proof** per doctype, as recorded in
   `bilingual-wave1-masters/evidence/wave1-p95-measurement.json`.

Transactional bilingual search is *deferred, not rejected*.

### 1.2 The transactional identity paradox

Transactional documents carry no intrinsic Arabic identity. `Sales Order.name` is a naming
series (`SO-2026-00012`); the human-meaningful identity is bound to linked masters. The
identity therefore already exists — on another table.

### 1.3 Why denormalisation is rejected

Copying `customer_name_ar` onto `tabSales Order` produces staleness against master renames,
conflicts with `docstatus` submission locking, and writes unverifiable values into financial
records. Rejected on audit grounds; not reopened by this RFC.

### 1.4 The current boundary — verified

`searchable_link_search` accepts `link_fieldname` and `reference_doctype` (search.py:21–22)
and **never reads them**. Frappe's `search_widget` already passes the cross-table context to
the server; it is discarded at the signature.

The consequence: typing an Arabic party name into a transactional Link field yields zero
results, because the query only ever matches columns physically present on the target table
(`search.py:124–136` — `or_filters` are built from `effective_fields` and `name` alone).

---

## 2. The Invariant Supersession Question

### 2.1 The invariant is a triad, not a pair

The 0-diff guarantee spans **three** files across seven reference commits:

| File | Role |
|---|---|
| `construction/services/bilingual_service.py` | normalisation, `get_mapping`, `RANK_WINDOW` |
| `construction/searchable_dropdown/api/search.py` | the governed query path |
| `construction/data/bilingual/bilingual_registry.json` | per-doctype field registry (19 doctypes) |

Any RFC section that proposes `link_resolution_fields` in the registry (§5 below) is editing
this triad and must be evaluated as an invariant question — not as an incidental schema note.

### 2.2 Three candidate positions

| | Position | Triad |
|---|---|---|
| **A** | Extend `searchable_link_search` in place with cross-table logic | **2 files breached** (`search.py`, registry) |
| **B** | Two-tier pre-resolution implemented inside `search.py` | **1 file breached** (`search.py`) |
| **C** | **Zero-diff sidecar** — new endpoint + client route | **0 diff** |

### 2.3 Recommendation: Option C

Option C is not merely the least invasive option; three verified facts make it the correct
architecture rather than a workaround:

1. **`get_mapping` does not fail closed for unregistered doctypes.**
   `bilingual_service.py:144–146` — when `doctype` is absent from `registry["doctypes"]`,
   `cfg` is `None` and the function returns `None` *silently*. It raises only when a mapping
   exists in state `active`/`schema_installed` and its configured fields are missing
   (`:159–160`). Therefore `searchable_link_search(doctype="Sales Order", …)` runs the plain
   path today, with no modification.

2. **A blank-query path already exists.** `search.py:124` guards all `or_filters`
   construction behind `if search_txt:`; `search.py:148–154` handles the empty case as
   bounded pagination with `filters` applied and `page_length` clamped to 200 (`:145`).
   Passing `txt=""` is therefore a supported, tested code path — not a hack.

3. **`filters` is applied verbatim on both paths** (`search.py:153` and `:168`). Because the
   sidecar calls `searchable_link_search` directly from Python, it can pass a native tuple
   `{"customer": ("in", ids)}` with no JSON round-trip.

**Conclusion:** transactional bilingual search can be delivered with the triad at **0 diff**.
Wave 2b §7.1 presumes the invariant must end. This RFC renegotiates that presumption and
concludes it need not end — recorded here explicitly so the conclusion is an argued
renegotiation rather than an evasion of §7.1.

### 2.4 What Option C does *not* preserve

Honesty requires stating the costs:

- **Configuration splits.** Master field configuration lives in `bilingual_registry.json`;
  link-resolution configuration cannot live there (§5) and must live beside the sidecar.
  Two configuration surfaces for one platform.
- **Client route is outside the invariant.** `searchable_dropdown.js` is editable, which is
  precisely why Option C works — and it means the routing decision is client-supplied.
- **The sidecar loses registry enrichment.** With `mapping is None`, no registry `search.fields`
  are appended (`search.py:110–114`), so the sidecar must pass `search_fields` explicitly
  and must supply any Arabic display labels itself.

---

## 3. Candidate Resolution Models

### 3.1 Option A — SQL JOIN (rejected)

```sql
SELECT so.name FROM `tabSales Order` so
JOIN tabCustomer c ON c.name = so.customer
WHERE c.customer_name_ar_norm LIKE %(norm)s
```

Rejected: per-doctype dynamic join generation, join-order/optimiser variance across MariaDB
versions, and every new transactional doctype adds a new join shape to maintain.

### 3.2 Option B — Two-tier pre-resolution (chosen mechanic)

1. Resolve the Arabic query against the **master** using the existing indexed normalised
   column (`customer_name_ar_norm`, `supplier_name_ar_norm`, …).
2. Query the **transaction** table with `<link_field> IN (resolved_ids)`.

Leverages already-built indexes, keeps the transaction-side query a single-table `get_list`,
and requires no schema change.

### 3.3 Option C — the sidecar (chosen packaging)

A new whitelisted endpoint, e.g. `construction.services.transaction_link_search.search_transactions`,
which:

- validates the requested target doctype against an **allow-list** (server-side; never trusts
  the client route — §2.4),
- performs Option B pre-resolution,
- delegates the transaction-side fetch to the **unmodified** `searchable_link_search` with
  `txt=""` and `filters={link_field: ("in", ids)}`,
- enriches display labels with the master's Arabic name where the transaction row has none.

**Client route:** `setCustomQuery()` in
`construction/public/js/searchable_dropdown/searchable_dropdown.js` (loaded via
`hooks.py:152`) branches on whether the target doctype is in the allow-list. This file is
**not** part of the invariant triad.

### 3.4 Structural exception — `Journal Entry`

Verified against live metadata: `Journal Entry` has **no parent-level party Link**. Its only
Link fields to `Account` on the parent are `stock_asset_account` and
`periodic_entry_difference_account`; the substantive account references live in the child
table `tabJournal Entry Account`.

Resolving "Arabic account name → journal entries" therefore requires a **child-table leg**:
`tabJournal Entry Account` (matches `account`) → `parent` → `tabJournal Entry`.

The parent-level sidecar cannot serve this. Either a child-table variant is scoped, or
`Journal Entry` is explicitly excluded in v1 with the exclusion recorded.

**Resolved by D2 (ratified 2026-10-03): `Journal Entry` is excluded in v1.** Scope is strictly
parent-level party links; the child-table leg is recorded as deferred work, not silently
dropped.

---

## 4. `RANK_WINDOW` & Memory Safety Bounds

### 4.1 Current contract (verified)

`RANK_WINDOW = 5000` (`bilingual_service.py:75`). The ranked path requests
`RANK_WINDOW + 1` rows (`search.py:171`) — a 5,001st-row probe so an exactly-full window is
not falsely flagged as overflow. Real overflow is then **made loud, never silently
truncated**.

The blank-query path does **not** use `RANK_WINDOW`; it is bounded by `page_length`,
clamped to `≤ 200` (`search.py:145`).

### 4.2 The `txt` correctness trap

If the Arabic query is consumed to resolve master IDs and the same `txt` is passed
downstream, the transaction-side query matches `name` / naming-series columns
(`SO-2026-00012`) and returns **zero rows**. The failure is silent and total.

**Contract:** the sidecar must call with `txt=""`. This is a *correctness* requirement, not
a performance one, and it must be asserted by a unit test — not merely documented.

### 4.3 Pre-resolution result cardinality — the real overflow risk

The trap above is the *easy* failure. The hard one is the inverse: an Arabic fragment such as
`شركة` may resolve to hundreds of master IDs, producing
`customer IN (…500 ids)` ordered by `modified DESC` with `page_length ≤ 200`. The user then
receives an arbitrary 200-row recency slice of a 500-way match — deterministic only in the
trivial sense, and not ranked by relevance at all.

**Required design:** cap the resolved-ID set at **top-K by master-side relevance**
(`exact > prefix > substring`, the same ranking the master path already performs), with K a
declared constant. Ranking then happens where the linguistic match actually occurs.

The transaction side returns a bounded, recency-ordered slice of a relevance-capped ID set.
Both bounds must be declared, tested at the boundary, and recorded in §7 evidence.

---

## 5. Registry Schema Extension — **not** taken

The originally drafted §5 proposed declaring `link_resolution_fields` in
`bilingual_registry.json`. That file is **inside the invariant triad** (§2.1); adding a key
is a nonzero diff and would breach the 0-diff guarantee the same commit claims to uphold.

**Decision: the registry is not modified.** Link-resolution configuration is held in the
sidecar module (target doctype → link field → master doctype → normalised field), subject to
the split-configuration cost acknowledged in §2.4.

If a future revision determines the registry *is* the right home, that becomes a standalone
invariant-renegotiation work item — it is not smuggled in as a schema note.

---

## 6. Deferred Ledgers Integration Path

`Asset`, `Brand`, and `Terms and Conditions` were deferred in wave 2b "contingent upon the
link-resolution RFC". They unblock **only if** their reference fields resolve through the
parent-level sidecar (§3.3). Each must be checked against the §3.4 class of exception:

- Does the doctype carry parent-level Links into registered masters?
- Or do its references live in child tables (like `Journal Entry`)?

No ledger opens on the strength of this RFC alone; each requires its own work item with the
standard evidence chain. This section establishes eligibility, not approval.

---

## 7. Test Matrix, Causal Verification & Matched-Set Proofs

### 7.1 Renegotiating wave 2b §7.3 — equivalence is unachievable as written

§7.3 demands "a matched-set equivalence proof per doctype". For transactional doctypes this
is **impossible by design**, not merely unmeasured:

- native `search_link` on `Sales Order` with `txt="المهندسون"` → **0 rows** (no Arabic on the table),
- governed sidecar with the same input → **the matching orders**.

Sets differ deliberately. Requiring `match_sets_equal: true` would require the governed path
to reproduce a result both paths are defined to disagree on.

**Proposed replacement property (directional, per doctype):**

> For fixture query `q`, let `G(q)` be governed results and `N(q)` native results.
> 1. **No phantom rows:** `G(q) ⊆ { r : r.<link_field> ∈ resolve(q) }`
> 2. **Bounded recall:** `|G(q)| ≤ page_length` and `|G(q)| ≤ K`
> 3. **Native agreement on shared vocabulary:** for Latin/ASCII `q` where `N(q) ≠ ∅`,
>    `N(q) ⊆ G(q)` within the same `page_length` window
> 4. **Determinism:** repeated evaluation of `G(q)` on an unchanged dataset is identical

Properties 1–2 are provable by construction; 3–4 require measurement. This is a **renegotiation
of prerequisite 3** — accepted as ratified under **D3 (2026-10-03)**, which adopts these four
properties in place of literal set equality.

### 7.2 Fixture scale (replacing the 253-row UOM class)

Measured live row counts on `v16.localhost`:

| Doctype | Rows | Parent-level party Links |
|---|---:|---|
| Sales Invoice | 3,977 | `customer`, `project`, `cost_center`, `department` + 7 Account |
| Stock Entry | 1,991 | `supplier`, `project`, `cost_center`, `department` |
| Journal Entry | 1,493 | **none** (§3.4 — child table) |
| Purchase Invoice | 994 | `supplier`, `project`, `cost_center`, `department` + 4 Account |
| Material Request | 670 | `customer` |
| Sales Order | 497 | `customer`, `project`, `cost_center`, `department` |
| Purchase Receipt | 497 | `supplier`, `project`, `cost_center`, `department` |
| Purchase Order | 0 | `supplier`, … |
| Timesheet / Payment Entry | 0 | … |

Fixtures must exercise at minimum **~4k rows** (`Sales Invoice`) — two orders of magnitude
beyond the 253-row `UOM` baseline. Doctypes with 0 rows must be seeded or excluded explicitly;
an excluded row is recorded as excluded, never as passing.

### 7.3 Tier classification

Transactional resolution is a two-query path (master pre-resolution + transaction fetch) over
tables far larger than any Tier 2B master measured so far, and Tier 2B's `n=50` band was
justified specifically on *sub-millisecond* baselines (`bilingual-performance-sla.md` §5.3).

**Proposal:** classify under **Tier 2B** (`≤ 1.50×`) with `n=100` min-of-rounds over 5 rounds —
i.e. adopt the *sample width* of Tier 2A while retaining Tier 2B's ratio band, because the
absolute latencies will exceed the sub-millisecond regime entirely. Final tier assignment is
made after the first measurement run, not before.

**Gate:** these fields must **not** be added to `search.fields` in any registry entry; they
are resolution metadata, not searchable identity.

### 7.4 Evidence & causal order

`final test run → capture log (2>&1) → compute git-blob digests → write MANIFEST.json → commit`

Digests verified via `git show HEAD:<path>`, never an `os.walk` of the working tree.

### 7.5 Invariants asserted on every commit

- Triad: `bilingual_service.py`, `search.py`, `bilingual_registry.json` → **0 diff lines**
- `apps/frappe`, `apps/erpnext` → 0 modifications
- Existing suites green: canonical matrix (12 modules, 153 tests), 19/19 ADR reconciliation
- New sidecar tests added to the canonical matrix **by editing
  `scripts/run_bilingual_regression_matrix.sh`**, not by ad-hoc invocation
