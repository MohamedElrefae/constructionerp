#!/usr/bin/env python3
"""W6-0b batch split — bounded workflow batches from the short-UI candidate set.

Owner directive (2026-09-22): do NOT treat the 1,915-row cut as one governed
import batch. Split the 1,894 translation-candidates into batches of ~200–300
rows; prioritize batch 1 by most-used Desk + accounting workflow; keep the 21
EXCEPTION-technical rows as documented exclusions (not batched for translation).

Deterministic; regenerates:
  docs/translation/stage6_w60b_batch_plan_2026-09-22.csv
  docs/translation/stage6_w60b_batch01_rows_2026-09-22.csv
  docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv

Ranking for batch order (classification unchanged):
  tier 0 — accounting workflow (tight GL/payment/currency/period terms)
  tier 1 — core Desk chrome/actions (exact short labels + desk phrases)
  tier 2 — remaining candidates by desk-surface quoted frequency, then text
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "docs" / "translation" / "stage6_w60b_short_ui_rows_2026-09-22.csv"
BENCH = ROOT.parents[1]
OUT_PLAN = ROOT / "docs" / "translation" / "stage6_w60b_batch_plan_2026-09-22.csv"
OUT_B1 = ROOT / "docs" / "translation" / "stage6_w60b_batch01_rows_2026-09-22.csv"
OUT_TECH = ROOT / "docs" / "translation" / "stage6_w60b_technical_exclusions_2026-09-22.csv"

TARGET = 271
MIN_BATCH = 200
MAX_BATCH = 300

ACCT = re.compile(
    r"(?i)\b("
    r"journal(\s+entr(y|ies))?|ledgers?|invoices?|payments?"
    r"|payment\s+(entry|term|request|authorization|mandate|charge|paid|failed)"
    r"|debits?|credits?|tax(es|ation)?|withholding|\bvat\b|\btds\b"
    r"|vouchers?|trial\s+balance|general\s+ledger"
    r"|cost\s+cent(er|res)|fiscal|period\s+clos\w*|closing\s+entr"
    r"|opening\s+entr|posting"
    r"|accounts?\s+receivable|accounts?\s+payable|receivables?|payables?"
    r"|exchange\s+rate|currency|budget|payroll"
    r"|reconcil\w*|chart\s+of\s+accounts|accounting\s+dimension"
    r"|debit\s+note|credit\s+note|outstanding|ageing|aging"
    r")\b"
)
ACCT_EXCLUDE = re.compile(
    r"(?i)\b("
    r"email\s+account|user\s+account|have\s+an\s+account|your\s+account"
    r"|account\s+deletion|accounts?\s+user|accounts?\s+manager"
    r"|set\s+up\s+your\s+account|setup\s+your\s+account"
    r"|total\s+(users|images|errors|outgoing|background|working)"
    r"|manage\s+3rd\s+party\s+apps"
    r")\b"
)

# Exact single-token / short chrome labels (normalized lower, strip)
DESK_CORE = {
    s.lower()
    for s in """
Save Submit Cancel Draft New Edit Delete Refresh Filter Sort Search Print
Export Import Duplicate Rename Update Add Remove Create Open Close View
List Settings Workspace Sidebar Menu Yes No OK Confirm Back Next Previous
Home User Role Permission Email Report Dashboard Status Type Date Name
Title From To All None Select Apply Reset Clear Copy Paste Show Hide Enable
Disable Theme Language Help About Logout Login Loading Error Warning
Success Message Dialog Modal Section Tab Field Value Group Upload Download
Attach Link Action Share Assign Comment History Version Page Total Count
Results Required Optional Mandatory Default Label Description Options
First Last Expand Collapse Preview Publish Activate Deactivate Lock Unlock
Approve Reject Review Sign Pin Favorite Trash More Toolbar Header Footer
Row Column Undo Redo Cut Archive Restore Discard Revert Amend Kanban
Move Insert Reload Star Follow Subscribe Desktop Workspaces Typography
Full Width Notices Info Warning Danger Primary Secondary Inline
Indent Outdent Merge Split Unstar Unfollow Unsubscribe
""".split()
}

DESK_EXACT_MULTI = {
    s.lower()
    for s in """
Clear All Reset Sorting No Data No Results Show Preview Hide Preview
Expand All Collapse All Switch Theme Notification Settings System Settings
Page Break Tab Break Reset Changes Redo Last Action Set by User
Select Field Global Search Quick Search List View Document Type
Add Row Delete Row Insert Row Save Draft Save As Click to Sort
Rows Selected Cells Copied No Filters No Values to Show Field Template
Section Title Sort Ascending Sort Descending Toggle Theme Edit Sidebar
Reload Page Open Menu Close Menu Show More Show Less Load More
View All View Details Copy Link Copy to Clipboard Download PDF Export CSV
Print View Preview Changes Discard Changes Apply Changes Search Results
No Search Results Filters Applied Clear Filters Add Filter Remove Filter
Select All Deselect All None Selected Items Selected Bulk Actions
Delete Selected Archive Selected Assign To Assigned To My Settings
User Settings Log Out Dark Mode Light Mode System Theme Keyboard Shortcuts
Recently Opened Mark as Read Mark as Unread Exit Full Screen
Sort By Filter By Ascending Descending Selected Actions Comments
Add Comment Notifications Notification Alert Results Result
Sr No Action Complete Please Enable Pop-ups No Images No Letterhead
Missing Values Required No Label Automated Message Column Title
Row Title Default View Custom View Reset to Default Comfortable
Compact Density Sign In Sign Out Language Selector
""".split()
}

DESK_PHRASE = re.compile(
    r"(?i)\b("
    r"save\s+draft|save\s+as|add\s+a?\s*row|delete\s+row|insert\s+row"
    r"|clear\s+all|reset\s+sorting|show\s+preview|hide\s+preview"
    r"|expand\s+all|collapse\s+all|click\s+to\s+sort|switch\s+theme"
    r"|notification\s+settings|system\s+settings|reset\s+changes"
    r"|redo\s+last\s+action|set\s+by\s+user|rows?\s+selected"
    r"|cells?\s+copied|select\s+(a\s+)?field|global\s+search|quick\s+search"
    r"|list\s+view|no\s+data|no\s+results|no\s+filters\s+found"
    r"|no\s+values\s+to\s+show|filter\s+by|sort\s+by|sort\s+ascending"
    r"|sort\s+descending|select\s+all|deselect\s+all|show\s+more"
    r"|show\s+less|load\s+more|view\s+all|copy\s+link|export\s+csv"
    r"|download\s+pdf|print\s+view|search\s+results|clear\s+filters"
    r"|add\s+filter|remove\s+filter|bulk\s+actions|delete\s+selected"
    r"|assign\s+to|my\s+settings|user\s+settings|log\s+out"
    r"|dark\s+mode|light\s+mode|full\s+screen|keyboard\s+shortcut"
    r"|recently\s+opened|mark\s+as\s+read|mark\s+as\s+unread"
    r"|are\s+you\s+sure|confirm\s+delet|document\s+type|page\s+of"
    r")\b"
)

# Schema/identifier tokens that rank high by raw quote count but are not
# everyday Desk workflow chrome — demote out of tier 1.
SCHEMA_DEMOTE = {
    s.lower()
    for s in """
label DocType email Tab Break InnoDB HTML GET POST DocField Percent Dynamic
JSON Phone Duration ID gray short long Python yyyy-mm-dd Autocomplete
System Settings Website Settings Website Manager Kanban Board Desk User
Communication Note Note DocName DocTitle DocStatus Parentfield Parenttype
Issuetypes Social DOCTYPE doctype fieldname fieldtype default_value
allow_on_submit invert_hidden reqd hidden read_only no_copy
""".split()
}


def load_desk_blob() -> str:
    roots = [
        BENCH / "apps" / "frappe" / "frappe" / "public",
        BENCH / "apps" / "frappe" / "frappe" / "www",
        BENCH / "apps" / "frappe" / "frappe" / "templates",
        BENCH / "apps" / "construction" / "construction" / "public",
    ]
    parts: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() not in {".js", ".html", ".vue", ".ts"}:
                continue
            if "node_modules" in p.parts:
                continue
            try:
                parts.append(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(parts)


def is_accounting(text: str) -> bool:
    if ACCT_EXCLUDE.search(text):
        return False
    return bool(ACCT.search(text))


def desk_tier_score(text: str) -> int:
    """Return 0 if not desk-tier-1 material; else 3+ strength."""
    t = text.strip()
    low = t.lower()
    if low in SCHEMA_DEMOTE:
        return 0
    if low in DESK_CORE:
        return 5
    if low in DESK_EXACT_MULTI:
        return 5
    if DESK_PHRASE.search(t):
        return 4
    # short imperative/action phrases common on toolbars
    if re.search(
        r"(?i)\b(save|submit|cancel|filter|sort|search|refresh|export|import"
        r"|delete|duplicate|rename|assign|share|approve|reject|archive"
        r"|restore|discard|confirm|loading|notification|workspace|sidebar"
        r"|toolbar|modal|dialog|preview|publish|amend)\b",
        t,
    ) and len(t) <= 40:
        return 3
    if len(t) <= 20 and " " in t and t[0].isupper():
        return 2
    return 0


def assign_batches(n: int) -> list[int]:
    k = max(1, math.ceil(n / TARGET))
    base = n // k
    rem = n % k
    sizes = [base + (1 if i < rem else 0) for i in range(k)]
    # nudge into range if needed
    if sizes and any(s > MAX_BATCH or s < MIN_BATCH for s in sizes):
        # binary search feasible k
        for k2 in range(max(1, n // MAX_BATCH), n // MIN_BATCH + 2):
            base = n // k2
            rem = n % k2
            cand = [base + (1 if i < rem else 0) for i in range(k2)]
            if all(MIN_BATCH <= s <= MAX_BATCH for s in cand):
                return cand
        raise RuntimeError("cannot fit batch sizes in [200,300]")
    return sizes


def main() -> None:
    rows = list(csv.DictReader(SCOPE.open(encoding="utf-8")))
    cands = [r for r in rows if r["classification"] == "translation-candidate"]
    tech = [r for r in rows if r["classification"] == "EXCEPTION-technical"]
    assert len(cands) == 1894 and len(tech) == 21

    blob = load_desk_blob()
    for r in cands:
        t = r["source_text"]
        q = blob.count(f'"{t}"') + blob.count(f"'{t}'") + blob.count(f"`{t}`")
        acct = is_accounting(t)
        ds = desk_tier_score(t)
        if acct:
            tier = 0
        elif ds >= 4:
            tier = 1
        else:
            tier = 2
        r["_q"] = q
        r["_desk"] = ds
        r["_acct"] = int(acct)
        r["_tier"] = tier

    ranked = sorted(
        cands,
        key=lambda r: (
            r["_tier"],
            -min(r["_q"], 999),
            -r["_desk"],
            r["source_text"],
        ),
    )
    sizes = assign_batches(len(ranked))
    assert sum(sizes) == len(ranked)
    assert all(MIN_BATCH <= s <= MAX_BATCH for s in sizes)

    idx = 0
    plan_rows: list[dict] = []
    batch1: list[dict] = []
    for b, sz in enumerate(sizes, start=1):
        chunk = ranked[idx : idx + sz]
        idx += sz
        for r in chunk:
            plan_rows.append(
                {
                    "batch": f"{b:02d}",
                    "source_text": r["source_text"],
                    "classification": r["classification"],
                    "tier": str(r["_tier"]),
                    "desk_quoted_hits": str(r["_q"]),
                    "desk_score": str(r["_desk"]),
                    "accounting_workflow": str(r["_acct"]),
                    "length": r["length"],
                    "app": r["app"],
                    "location": r["location"],
                    "suppression_rationale": r["suppression_rationale"],
                    "ai_r_ref": r["ai_r_ref"],
                    "suggested_ar": r["suggested_ar"],
                }
            )
            if b == 1:
                batch1.append(r)
        print(
            f"batch {b:02d}: {sz} rows "
            f"(acct={sum(x['_acct'] for x in chunk)}, "
            f"tier0/1/2={sum(1 for x in chunk if x['_tier']==0)}/"
            f"{sum(1 for x in chunk if x['_tier']==1)}/"
            f"{sum(1 for x in chunk if x['_tier']==2)})"
        )

    assert len(batch1) == sizes[0]
    assert MIN_BATCH <= len(batch1) <= MAX_BATCH
    assert idx == 1894
    # batch1 must contain every accounting row (tier0 should fit in batch1)
    tier0 = [r for r in ranked if r["_tier"] == 0]
    assert len(tier0) <= len(batch1)
    assert all(r in batch1 for r in tier0)

    fields_plan = [
        "batch",
        "source_text",
        "classification",
        "tier",
        "desk_quoted_hits",
        "desk_score",
        "accounting_workflow",
        "length",
        "app",
        "location",
        "suppression_rationale",
        "ai_r_ref",
        "suggested_ar",
    ]
    with OUT_PLAN.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_plan)
        w.writeheader()
        w.writerows(plan_rows)

    fields_scope = [
        "source_text",
        "classification",
        "location",
        "suppression_rationale",
        "ai_r_ref",
        "length",
        "app",
        "suggested_ar",
    ]
    with OUT_B1.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_scope)
        w.writeheader()
        w.writerows({k: r[k] for k in fields_scope} for r in batch1)

    with OUT_TECH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields_scope)
        w.writeheader()
        w.writerows({k: r[k] for k in fields_scope} for r in tech)

    print(f"wrote {OUT_PLAN} ({len(plan_rows)} rows, {len(sizes)} batches)")
    print(f"wrote {OUT_B1} ({len(batch1)} rows)")
    print(f"wrote {OUT_TECH} ({len(tech)} rows)")
    print("batch1 accounting:", sum(r["_acct"] for r in batch1))
    print("batch1 first 40:")
    for r in batch1[:40]:
        print(" ", r["source_text"][:72])


if __name__ == "__main__":
    main()
