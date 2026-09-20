"""Vendor upgrade-delta reporter (Stage 2).

Compares two git refs of a vendor app's Arabic catalog and emits a governed
add/change/remove/context-shift delta for triage. Writes nothing by default;
use --write to store the artifact (reviewed operation).

Usage:
  python3 scripts/vendor_upgrade_delta.py --app frappe --old <sha> --new <sha> [--write]
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_localization_gates import parse_po_file  # noqa: E402


def _root(root):
    return Path(root) if root else ROOT


def blob(app, ref, root=None):
    root = _root(root)
    Path(root).mkdir(parents=True, exist_ok=True)
    po_rel = f"{app}/locale/ar.po"
    out = subprocess.run(
        ["git", "-C", str(root.parent / app), "show", f"{ref}:{po_rel}"],
        capture_output=True, timeout=120,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {app}@{ref}:{po_rel}: {out.stderr.decode()[:200]}")
    import tempfile, shutil as _sh
    tmpdir = tempfile.mkdtemp(prefix=f"vendor-{app}-{ref[:8]}-", dir=str(root))
    try:
        tmp = Path(tmpdir) / "candidate.po"
        tmp.write_bytes(out.stdout)
        entries, errors = parse_po_file(tmp)
    finally:
        _sh.rmtree(tmpdir, ignore_errors=True)
    if errors:
        print(f"warning: {len(errors)} parse notes at {ref}")
    return {(e["context"], e["msgid"]): e for e in entries if not e["obsolete"]}




def classify_delta(old_map, new_map):
    """Split two {(context, msgid): entry} maps into add/remove/change/shift."""
    added = sorted(k for k in new_map if k not in old_map)
    removed = sorted(k for k in old_map if k not in new_map)
    changed = sorted(
        k for k in old_map if k in new_map
        and old_map[k]["targets"] != new_map[k]["targets"]
    )
    old_by_msgid, new_by_msgid = {}, {}
    for (c, m) in old_map:
        old_by_msgid.setdefault(m, set()).add(c)
    for (c, m) in new_map:
        new_by_msgid.setdefault(m, set()).add(c)
    context_shift = sorted(
        {"msgid": m, "old_contexts": sorted(old_by_msgid[m]),
         "new_contexts": sorted(new_by_msgid[m])}
        for m in old_by_msgid
        if m in new_by_msgid and old_by_msgid[m] != new_by_msgid[m]
    )
    return added, removed, changed, context_shift

def main(argv, root=None):
    root = _root(root)
    args = list(argv)
    rflag = [a for a in args if a.startswith("--root=")]
    if rflag and root == ROOT:
        root = Path(rflag[0].split("=", 1)[1])
        args = [a for a in args if not a.startswith("--root=")]
    app = args[args.index("--app") + 1]
    old = args[args.index("--old") + 1]
    new = args[args.index("--new") + 1]
    old_map, new_map = blob(app, old, root), blob(app, new, root)
    added, removed, changed, context_shift = classify_delta(old_map, new_map)
    import sys as _sys
    _sys.path.insert(0, str(root / "scripts"))
    from check_localization_gates import canonical_delta_sets
    import hashlib as _hl
    delta = {"app": app, "old": old, "new": new,
             "old_po_sha": None, "new_po_sha": None,
             **canonical_delta_sets(added, removed, changed, context_shift),
             "triage_status": "pending",
             "disposition": "",
             "dispositions": {},
             "disposition_key_format": "context + \\x00 + msgid (context shifts keyed as \\x00 + msgid)"}
    for ref, key in ((old, "old_po_sha"), (new, "new_po_sha")):
        out = subprocess.run(
            ["git", "-C", str(root.parent / app), "show", f"{ref}:{app}/locale/ar.po"],
            capture_output=True, timeout=120,
        )
        if out.returncode == 0:
            delta[key] = _hl.sha256(out.stdout).hexdigest()
    print(json.dumps(
        {"added": len(added), "removed": len(removed), "changed": len(changed),
         "context_shift": len(context_shift)},
        sort_keys=True))
    if "--write" in args:
        out = root / "construction" / "data" / "localization" / f"vendor_delta_{app}_{new[:8]}.json"
        out.write_text(json.dumps(delta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(f"wrote {out} — set triage_status/disposition under review")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
