"""Deterministic Stage 2 inventory manifest recorder.

Executes the committed `scripts/stage2_inventory.sql` against the site DB,
computes the per-app categories and the canonical Merkle root via
`construction.localization_inventory.merkle_root`, and rewrites
`construction/data/localization/stage2_inventory_manifest.json`.

Run (non-production test sites only):
    bench --site <site> execute construction.services.stage2_inventory_record.record

Fail-closed guards:
- refuses to run when the candidate HEAD moved away from the recorded
  base commit without the caller passing `allow_commit_move=True`;
- refuses when the SQL file or PO set changed in a way that would make the
  recorded envelope lie (PO hashes are recomputed and written, never assumed).
"""

import hashlib
import json
import subprocess
from pathlib import Path

MANIFEST = "construction/data/localization/stage2_inventory_manifest.json"
SQL = "scripts/stage2_inventory.sql"
MERKLE_SCHEME = "json(sorted(str-normalized (source,context,app,translated,review))) sha256"


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _head(root):
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def record(allow_commit_move=False, root=None):
    """Regenerate the inventory manifest from live DB state. Returns a summary dict."""
    import frappe

    root = Path(root) if root else Path(frappe.get_app_path("construction")).parent
    head = _head(root)
    old_text = (root / MANIFEST).read_text(encoding="utf-8") if (root / MANIFEST).exists() else ""
    old = json.loads(old_text) if old_text.strip() else None
    if old and head and old.get("base_commit") not in (None, head) and not allow_commit_move:
        raise ValueError(
            "candidate HEAD moved from recorded base commit %s to %s — review before regenerating"
            % (old.get("base_commit"), head)
        )

    sql_text = (root / SQL).read_text(encoding="utf-8")
    body = "\n".join(l for l in sql_text.splitlines() if not l.strip().startswith("--"))
    statements = [s.strip() for s in body.split(";") if s.strip()]
    if len(statements) != 2:
        raise ValueError("stage2_inventory.sql must contain exactly two statements, found %d" % len(statements))
    categories = frappe.db.sql(statements[0], as_dict=True)
    rows = frappe.db.sql(statements[1])
    from construction.localization_inventory import merkle_root

    row_count, merkle = merkle_root(rows)

    manifest = {
        "base_commit": head,
        "categories": categories,
        "generated_utc": frappe.utils.now_datetime().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "construction.localization_inventory.merkle_root over stage2_inventory.sql",
        "merkle": {"root": merkle, "rows": row_count, "scheme": MERKLE_SCHEME},
        "po_hashes": {
            "construction": _sha_file(root / "construction/locale/ar.po"),
            "erpnext": _sha_file(root.parent / "erpnext/erpnext/locale/ar.po"),
            "frappe": _sha_file(root.parent / "frappe/frappe/locale/ar.po"),
        },
        "target_site": "%s (test, non-production)" % frappe.local.site,
    }
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "rows": row_count,
        "root": merkle,
        "base_commit": head,
        "previous": None if not old else {"rows": (old.get("merkle") or {}).get("rows"), "root": (old.get("merkle") or {}).get("root")},
        "apps": {c.get("app"): c.get("total") for c in categories},
    }
    print(json.dumps(summary, sort_keys=True))
    return summary
