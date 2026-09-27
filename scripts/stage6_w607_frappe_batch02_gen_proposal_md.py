#!/usr/bin/env python3
import csv
from pathlib import Path

APP_ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
PROP_CSV = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv"
OUT_MD = APP_ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.md"

with PROP_CSV.open(encoding="utf-8") as h:
    rows = list(csv.DictReader(h))

lines = [
    "# Stage 6 — W6-7 Frappe Framework Remainder Batch 02 Proposal (2026-09-27)",
    "",
    "**Status:** PROPOSAL ONLY — owner approval pending. No quorum review, no runtime import, no catalog update, no evidence re-pin, no git commit, no git push.",
    "",
    "---",
    "",
    "## 1. Scope and Artifacts",
    "",
    "| Artifact | Path | SHA-256 | Rows |",
    "| :--- | :--- | :--- | :---: |",
    "| **Scope CSV** | `docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | 244 |",
    "| **Proposal CSV** | `docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | 244 |",
    "| **Site Recon JSON** | `docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json` | Live reconciliation on `v16.localhost` | 244 |",
    "",
    "---",
    "",
    "## 2. Partition Summary",
    "",
    "| Disposition | Count | Description |",
    "| :--- | :---: | :--- |",
    "| **`preserved-site-override`** | 0 | No active site overrides on `v16.localhost` (all 244 keys missing in runtime `tabTranslation`) |",
    "| **`EXCEPTION-technical`** | 1 | Unresolved JS template literal expression (`{0} ${skip_list ? \"\" : type}`); empty translation |",
    "| **`PROPOSED-payload`** | 243 | Candidate Arabic translations for Frappe framework UI strings |",
    "| **Total** | **244** | **0 + 1 + 243 = 244** |",
    "",
    "---",
    "",
    "## 3. Structural Validation Notes",
    "",
    "- **Placeholder Multiset Parity:** All placeholders (`{0}`, `{1}`, `{2}`, `{3}`, `{4}`, `{}`, `%s`, `%d`) have exact multiset parity between source and proposed translation.",
    "- **Whitespace & Punctuation Parity:** Colons (`:`), ellipses (`...`), question marks (`؟`/`?`), and whitespace strictly match the source strings.",
    "- **Strict Environmental Isolation:** Non-production test site only (`v16.localhost`). Stage 8 and production remain untouched and gated.",
    "",
    "---",
    "",
    "## 4. Full 244-Row Proposal Table",
    "",
    "| # | Source Text | Proposed Translation | Disposition | Notes |",
    "| :-: | :--- | :--- | :--- | :--- |",
]

for idx, r in enumerate(rows, 1):
    st = r["source_text"].replace("|", "&#124;").replace("\n", " ")
    tr = r["proposed_translation"].replace("|", "&#124;").replace("\n", " ")
    disp = r["disposition"]
    notes = "Technical exclusion" if disp == "EXCEPTION-technical" else "Valid payload"
    lines.append(f"| {idx} | {st} | {tr} | `{disp}` | {notes} |")

lines.append("")
OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(rows)} rows to {OUT_MD}")
