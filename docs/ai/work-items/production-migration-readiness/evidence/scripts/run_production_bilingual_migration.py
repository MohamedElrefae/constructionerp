"""Tier 5J deliverable B — consolidated fail-closed production bilingual migration runner.

Usage (bench python, from the bench root):

    env/bin/python <this file> --site v16.localhost [--dry-run] [--force]
        [--values PATH] [--allow-sites v16.localhost]
        [--reapply] [--rollback-rehearsal]

Contract (SCOPE §3.2, invariants §5):
  * Pre-flight, all gates fail-closed: site allowlist / production_mutation_authorized
    flag, values bundle sha256, registry+schema fields (arabic+norm columns on all 15
    doctypes), utf8mb4 table collation, doc_events policy hooks bound, fresh DB backup
    (age gate; --force bypasses ONLY the age gate), redis queue(11000)+cache(13000).
  * Classification before any write: ALREADY_APPLIED (skip, idempotent) /
    WOULD_WRITE (empty target) / CONFLICT (divergent value -> abort, never overwrite) /
    ABSENT_ON_TARGET (missing document -> abort).
  * Apply: topological doctype order; Account via the governed `set_account_name_ar`
    path; all other doctypes via doc.save() with server-derived norm (hook-owned);
    tree roots route through the proven F-5J-6 quirk map (scoped, restored in
    finally). Any exception -> frappe.db.rollback() + exit 1 (zero partial writes).
  * --reapply: resave rows even when already equal (validation only; still respects
    CONFLICT). --rollback-rehearsal: VALIDATION-ONLY — persist nothing: after the
    in-transaction verification, rollback and re-verify the pre-state (refused on
    non-allowlisted sites).
  * Never writes norm fields; never renames; never touches parents/lft/rgt directly.
"""

import argparse
import hashlib
import importlib
import json
import os
import socket
import sys
import time
from urllib.parse import urlparse
from collections import OrderedDict

BENCH = "/home/mohamed/frappe-bench"
APPS = f"{BENCH}/apps"
SITES = f"{BENCH}/sites"
sys.path.insert(0, f"{APPS}/construction")

import frappe  # noqa: E402

EXPECTED_VALUES_SHA256 = "7390a0c87f8ebab1e602521549b775f8768d3ab9bb40a1caf055f4c5c31d53bf"
DEFAULT_ALLOW_SITES = {"v16.localhost"}
BACKUP_MAX_AGE_S = 24 * 3600

# Topological order (briefing §order; company first, leaf masters last).
TOPO = [
    "Company", "Account", "Cost Center", "Warehouse", "Project",
    "Item Group", "Customer Group", "Supplier Group", "Territory",
    "Department", "Task", "UOM", "Item", "Customer", "Terms and Conditions",
]

TREE_PARENT = {
    "Company": "parent_company",
    "Account": "parent_account",
    "Cost Center": "parent_cost_center",
    "Warehouse": "parent_warehouse",
    "Item Group": "parent_item_group",
    "Customer Group": "parent_customer_group",
    "Supplier Group": "parent_supplier_group",
    "Territory": "parent_territory",
    "Department": "parent_department",
    "Task": "parent_task",
}

# F-5J-6 — every mechanism below is proven by a closed tier (5C/5D/5G/Stage-4).
# `patch_get_root_of`: module namespace whose get_root_of is temporarily lambda: None.
# `in_test`: temporarily set frappe.in_test (Item Group vendor guard, item_group.py:35).
# `ignore_mandatory`: doc.flags.ignore_mandatory for reqd root fields (R3a).
ROOT_QUIRKS = {
    "Item Group": {"in_test": True},
    "Customer Group": {"patch_get_root_of": "erpnext.setup.doctype.customer_group.customer_group"},
    "Supplier Group": {"patch_get_root_of": "erpnext.setup.doctype.supplier_group.supplier_group"},
    "Territory": {"patch_get_root_of": "erpnext.setup.doctype.territory.territory"},
    "Department": {"patch_get_root_of": "erpnext.setup.doctype.department.department",
                   "ignore_mandatory": True},
    "Cost Center": {"ignore_mandatory": True},
    # Account roots: `Account.validate_root_details` throws RootNotEditable on ANY
    # save of an existing root (account.py:213-215) — narrow scoped no-op patch of
    # ONLY that method (restored in finally); all other vendor validations and the
    # governed enforce_account_arabic_policy token/norm hook still run (F-5J-11).
    "Account": {"skip_validate": "validate_root_details"},
    # Warehouse / Task: plain (5C / task row is non-root). Company: plain (5H).
}

REGISTRY_PATH = f"{APPS}/construction/construction/data/bilingual/bilingual_registry.json"
TABLE = lambda dt: "tab" + dt  # noqa: E731  (Frappe keeps spaces: "tabCost Center")


class PreflightError(Exception):
    pass


def log(msg):
    print(msg, flush=True)


def fail(msg):
    raise PreflightError(msg)


# ---------------------------------------------------------------- pre-flight

def check_site(site, allow_sites):
    cfg_path = os.path.join(SITES, site, "site_config.json")
    if not os.path.isfile(cfg_path):
        fail(f"site {site!r}: site_config.json missing")
    cfg = json.load(open(cfg_path))
    authorized = cfg.get("production_mutation_authorized") is True
    if site in allow_sites:
        return "allowlist", authorized
    if authorized:
        return "site_config flag", True
    fail(f"site {site!r} not in --allow-sites and site_config lacks "
         f"production_mutation_authorized: true (F-5J-8 governance guard)")


def check_values(path):
    if not os.path.isfile(path):
        fail(f"values bundle missing: {path}")
    raw = open(path, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_VALUES_SHA256:
        fail(f"values bundle sha256 {digest[:16]} != committed "
             f"{EXPECTED_VALUES_SHA256[:16]} (owner-approval binding broken)")
    bundle = json.loads(raw.decode("utf-8"))
    if bundle.get("row_count") != 188:
        fail(f"bundle row_count {bundle.get('row_count')} != 188")
    return bundle, digest


def load_registry():
    reg = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    for dt in TOPO:
        meta = reg["doctypes"].get(dt)
        if not meta:
            fail(f"registry: doctype {dt!r} absent")
        for key in ("arabic_field", "norm_field"):
            if not meta.get(key):
                fail(f"registry: {dt}.{key} absent")
    return reg


def check_schema(reg):
    schema = frappe.conf.db_name
    for dt in TOPO:
        table = TABLE(dt)
        cols = {r.COLUMN_NAME for r in frappe.db.sql(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
            (schema, table), as_dict=True)}
        meta = reg["doctypes"][dt]
        for field in (meta["arabic_field"], meta["norm_field"]):
            if field not in cols:
                fail(f"schema: {table}.{field} missing (custom-field patch not applied)")
        coll = frappe.db.sql(
            "SELECT TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (schema, table), as_dict=True)
        if not coll or not (coll[0].TABLE_COLLATION or "").startswith("utf8mb4"):
            fail(f"schema: {table} collation "
                 f"{coll[0].TABLE_COLLATION if coll else None} != utf8mb4 (F-5J-3)")


def check_hooks():
    import construction.hooks as h
    doc_events = getattr(h, "doc_events", {})
    for dt in TOPO:
        ev = doc_events.get(dt, {})
        validates = ev.get("validate", [])
        if isinstance(validates, str):
            validates = [validates]
        wanted = ("enforce_account_arabic_policy" if dt == "Account"
                  else "enforce_bilingual_arabic_policy")
        if not any(wanted in v for v in validates):
            fail(f"hooks: {dt}.validate not bound to {wanted} (F-5J-4)")


def check_backup(site, force):
    bdir = os.path.join(SITES, site, "private", "backups")
    if not os.path.isdir(bdir):
        fail(f"backup: {bdir} missing — take `bench backup --site {site}` first (F-5J-5)")
    candidates = [os.path.join(bdir, f) for f in os.listdir(bdir)
                  if f.endswith((".sql", ".sql.gz", ".sql.bz2", ".sql.xz"))]
    if not candidates:
        fail(f"backup: no dump in {bdir} — take `bench backup --site {site}` first (F-5J-5)")
    newest = max(candidates, key=os.path.getmtime)
    if os.path.getsize(newest) < 1024:
        fail(f"backup: newest dump is implausibly small "
             f"({os.path.getsize(newest)} bytes): {os.path.basename(newest)}")
    age = time.time() - os.path.getmtime(newest)
    if age > BACKUP_MAX_AGE_S and not force:
        fail(f"backup: newest dump is {age/3600:.1f}h old (>24h): {os.path.basename(newest)} "
             f"— refresh or --force (age gate only; F-5J-5)")
    return newest, age


def check_redis():
    pinged = []
    for label, url in (("queue", frappe.conf.redis_queue or ""),
                       ("cache", frappe.conf.redis_cache or "")):
        if not url:
            fail(f"redis: frappe.conf.redis_{label} unset")
        netloc = urlparse(url).netloc or urlparse("//" + url).netloc
        port = int(netloc.rsplit(":", 1)[-1])
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.sendall(b"PING\r\n")
            if not s.recv(64).startswith(b"+PONG"):
                raise OSError("no PONG")
            s.close()
            pinged.append((label, port))
        except OSError as exc:
            fail(f"redis {label} (127.0.0.1:{port}) unreachable: {exc} (F-5J-7) — "
                 f"start it: redis-server --port {port} ...")
    return pinged


# ------------------------------------------------------- classification model

def classify(bundle, reg, mode):
    """Read-only classification. Returns (rows_by_doctype, summary)."""
    summary = {"ALREADY_APPLIED": 0, "WOULD_WRITE": 0, "CONFLICT": 0, "ABSENT": 0}
    out = OrderedDict((dt, []) for dt in TOPO)
    for row in bundle["rows"]:
        dt = row["doctype"]
        ar = reg["doctypes"][dt]["arabic_field"]
        live_raw = frappe.db.get_value(dt, row["name"], ar, order_by=None) \
            if frappe.db.exists(dt, row["name"]) else None
        if not frappe.db.exists(dt, row["name"]):
            status = "ABSENT"
        elif (live_raw or None) == row["arabic"]:
            status = "ALREADY_APPLIED"
        elif live_raw:
            status = "CONFLICT"
        else:
            status = "WOULD_WRITE"
        summary[status] += 1
        out[dt].append((row, status))
    return out, summary


# -------------------------------------------------------------- root quirks

class RootQuirk:
    """Scoped, restorable root-save workaround (F-5J-6). Restores in finally."""

    def __init__(self, doctype, is_root):
        self.dt, self.is_root = doctype, is_root
        self.spec = ROOT_QUIRKS.get(doctype, {}) if is_root else {}
        self.saved = {}

    def __enter__(self):
        try:
            if "patch_get_root_of" in self.spec:
                mod = importlib.import_module(self.spec["patch_get_root_of"])
                self.saved["module"] = mod
                self.saved["fn"] = mod.get_root_of
                mod.get_root_of = lambda _dt: None
            if self.spec.get("in_test"):
                self.saved["in_test"] = frappe.in_test
                frappe.in_test = True
            if "skip_validate" in self.spec:
                mod = importlib.import_module("erpnext.accounts.doctype.account.account")
                self.saved["cls"] = mod.Account
                self.saved["method"] = getattr(mod.Account, self.spec["skip_validate"])
                setattr(mod.Account, self.spec["skip_validate"], lambda self: None)
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, *exc):
        if "module" in self.saved:
            self.saved["module"].get_root_of = self.saved["fn"]
        if "cls" in self.saved:
            setattr(self.saved["cls"], self.spec["skip_validate"], self.saved["method"])
        if self.spec.get("in_test") and "in_test" in self.saved:
            frappe.in_test = self.saved["in_test"]
        return False

    def save_root(self, name, arabic):
        """Account root save (F-5J-11).

        `set_account_name_ar` cannot be reused here: it loads the doc itself, so we
        cannot pre-set `doc.flags.ignore_mandatory` (root parent_account is reqd=1
        and `_validate_mandatory` only honors doc flags). This helper mirrors the
        governed contract exactly — same token binding the
        enforce_account_arabic_policy hook validates (doctype/name/old/new), same
        identity check, norm derived server-side by the hook, Version recorded —
        plus the root-only mandatory bypass, all while the scoped
        validate_root_details no-op is active.
        """
        from construction.services.bilingual_service import (
            GOVERNED_EDIT_FLAG, validate_identity_text)
        if not frappe.has_permission("Account", "write", doc=name):
            frappe.throw("root account save requires Account write permission",
                         frappe.PermissionError)
        text = arabic.strip()
        if not validate_identity_text(text):
            frappe.throw("root account Arabic value failed identity validation",
                         frappe.ValidationError)
        doc = frappe.get_doc("Account", name)
        doc.account_name_ar = text
        stored_old = frappe.db.get_value("Account", name, "account_name_ar") or None
        prior_flag = frappe.flags.get(GOVERNED_EDIT_FLAG)  # read BEFORE install
        setattr(frappe.flags, GOVERNED_EDIT_FLAG,
                {"doctype": "Account", "name": doc.name,
                 "old": stored_old, "new": text})
        try:
            doc.flags.ignore_mandatory = True  # root parent_account reqd=1
            doc.save()
        finally:
            setattr(frappe.flags, GOVERNED_EDIT_FLAG, prior_flag)

    def save(self, doc):
        if self.spec.get("ignore_mandatory"):
            doc.flags.ignore_mandatory = True
        try:
            doc.save()
        except frappe.MandatoryError:
            if not self.is_root:
                raise  # non-root MandatoryError is a real data problem: fail closed
            # Disclosed R3A safety net: reqd root field missed by the map.
            doc.flags.ignore_mandatory = True
            doc.save()


# --------------------------------------------------------------------- apply

def apply_writes(by_doctype, reg, reapply, rollback_rehearsal):
    from construction.services.bilingual_service import (
        _normalize_arabic, set_account_name_ar)

    pre_state = snapshot_all(reg)
    counts = {"SAVED": 0, "SKIPPED": 0, "ROOT_SAVES": 0}
    frappe.db.begin()
    # F-5J-12: vendor bulk-import path (chart_of_accounts.py:71, company.py:526)
    # sets ignore_update_nsm so NestedSet.on_update does NOT renumber the tree.
    # Values-only saves never move nodes; stale `old_parent` bookkeeping from
    # earlier bulk imports would otherwise trigger update_move_node and shift
    # sibling lft/rgt (observed: 12 Account rows renumbered by ONE save).
    had_nsm = frappe.local.flags.get("ignore_update_nsm")
    frappe.local.flags.ignore_update_nsm = True
    try:
        for dt in TOPO:
            for row, status in by_doctype[dt]:
                if status == "CONFLICT":
                    raise PreflightError("CONFLICT reached apply (should abort earlier)")
                if status == "ABSENT":
                    raise PreflightError(f"ABSENT document reached apply: {dt} {row['name']}")
                if status == "ALREADY_APPLIED" and not reapply:
                    counts["SKIPPED"] += 1
                    continue
                name = row["name"]
                parent_field = TREE_PARENT.get(dt)
                is_root = bool(parent_field and not frappe.db.get_value(
                    dt, name, parent_field))
                with RootQuirk(dt, is_root) as quirk:
                    if dt == "Account":
                        # Governed path: binds doctype/name/old/new token, derives
                        # norm server-side, records Version (bilingual_service.py:372+).
                        # Root accounts additionally need quirk.save's scoped
                        # validate_root_details no-op (F-5J-11).
                        if is_root:
                            quirk.save_root(name, row["arabic"])
                        else:
                            set_account_name_ar(name, row["arabic"])
                    else:
                        meta = reg["doctypes"][dt]
                        doc = frappe.get_doc(dt, name)
                        doc.set(meta["arabic_field"], row["arabic"])
                        quirk.save(doc)
                if is_root:
                    counts["ROOT_SAVES"] += 1
                counts["SAVED"] += 1

        # In-transaction verification: every row written/skipped is present,
        # byte-equal, norm server-derived and correct.
        for dt in TOPO:
            ar = reg["doctypes"][dt]["arabic_field"]
            norm = reg["doctypes"][dt]["norm_field"]
            for row, status in by_doctype[dt]:
                live, live_norm = frappe.db.get_value(
                    dt, row["name"], [ar, norm])
                if (live or None) != row["arabic"]:
                    raise PreflightError(f"post-write mismatch: {dt} {row['name']}")
                if row["arabic"] and live_norm != _normalize_arabic(row["arabic"]):
                    raise PreflightError(f"norm mismatch: {dt} {row['name']}")
        post_state = snapshot_all(reg)
        tree_changed = compare_trees(pre_state, post_state)
        if tree_changed:
            raise PreflightError(f"tree structure mutated by values-only save: "
                                 f"{sorted(tree_changed)[:5]}")

        if rollback_rehearsal:
            frappe.db.rollback()
            back = snapshot_all(reg)
            if back != pre_state:
                diffs = [k for k in pre_state if pre_state[k] != back.get(k)]
                raise PreflightError(f"rollback incomplete: {sorted(diffs)[:5]}")
            log("ROLLBACK-REHEARSAL: db rolled back; full pre-state snapshot re-verified byte-identical")
        else:
            frappe.db.commit()
            log("COMMIT: all rows persisted")
        return counts, pre_state, post_state
    except BaseException:
        frappe.db.rollback()
        log("ROLLBACK on error — zero partial writes")
        raise
    finally:
        if had_nsm is None:
            frappe.local.flags.pop("ignore_update_nsm", None)
        else:
            frappe.local.flags.ignore_update_nsm = had_nsm


def snapshot_all(reg):
    snap = {}
    for dt in TOPO:
        ar = reg["doctypes"][dt]["arabic_field"]
        rows = frappe.get_all(dt, fields=["name", ar], limit_page_length=0)
        snap[dt] = {r["name"]: r[ar] for r in rows}
        if dt in TREE_PARENT:
            tree = frappe.get_all(
                dt, fields=["name", TREE_PARENT[dt], "old_parent", "lft", "rgt"],
                limit_page_length=0)
            snap[dt + "::tree"] = {r["name"]: (r[TREE_PARENT[dt]] or None,
                                               r.lft, r.rgt, r.old_parent) for r in tree}
    return snap


def compare_trees(a, b):
    changed = []
    for key in a:
        if not key.endswith("::tree"):
            continue
        if a[key] != b.get(key):
            changed.append(key)
    return changed


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", default="v16.localhost")
    ap.add_argument("--values", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="bypass ONLY the backup age gate")
    ap.add_argument("--allow-sites", default="v16.localhost",
                    help="comma-separated development allowlist (F-5J-8)")
    ap.add_argument("--reapply", action="store_true",
                    help="resave rows already equal (validation; still conflict-safe)")
    ap.add_argument("--rollback-rehearsal", action="store_true",
                    help="VALIDATION-ONLY: apply all writes, verify, then roll back")
    args = ap.parse_args()

    if args.rollback_rehearsal and not args.dry_run:
        log("*** VALIDATION-ONLY MODE: no data will be persisted ***")

    frappe.init(site=args.site, sites_path=SITES)
    frappe.connect()
    frappe.set_user("Administrator")
    started = time.time()
    try:
        allow = {s.strip() for s in args.allow_sites.split(",") if s.strip()}
        gate, authorized = check_site(args.site, allow)
        if args.rollback_rehearsal and gate != "allowlist":
            fail("--rollback-rehearsal is validation-only: refused on non-allowlisted sites")
        log(f"PREFLIGHT site={args.site} gate={gate} "
            f"production_mutation_authorized={authorized}")

        reg = load_registry()
        log(f"PREFLIGHT registry: {len(TOPO)} doctypes, arabic+norm fields present")

        values_path = args.values or os.path.join(
            SITES, args.site, "private", "production-migration", "consolidated_values.json")
        bundle, digest = check_values(values_path)
        log(f"PREFLIGHT values: rows={bundle['row_count']} sha256={digest[:16]}…")

        check_schema(reg)
        log("PREFLIGHT schema: arabic+norm columns present, utf8mb4 on all 15 tables")

        check_hooks()
        log("PREFLIGHT hooks: enforce_*_policy bound on all 15 doctypes (Account=governed)")

        backup, age = check_backup(args.site, args.force)
        log(f"PREFLIGHT backup: {os.path.basename(backup)} ({age/60:.0f} min old)")

        redises = check_redis()
        log("PREFLIGHT redis: " + ", ".join(f"{n}:{p}" for n, p in redises))

        by_doctype, summary = classify(bundle, reg, args.dry_run)
        log("CLASSIFY " + json.dumps(summary, sort_keys=True))
        if summary["CONFLICT"]:
            for dt, rows in by_doctype.items():
                for row, st in rows:
                    if st == "CONFLICT":
                        log(f"  CONFLICT {dt} {row['name']}")
            log("RESULT: FAIL (conflict — fail-closed, zero writes)")
            return 2
        if summary["ABSENT"]:
            log("RESULT: FAIL (absent documents — fail-closed, zero writes)")
            return 2

        if args.dry_run:
            for dt in TOPO:
                n_w = sum(1 for _, st in by_doctype[dt] if st == "WOULD_WRITE")
                n_a = sum(1 for _, st in by_doctype[dt] if st == "ALREADY_APPLIED")
                if n_w or n_a:
                    log(f"  {dt}: would_write={n_w} already_applied={n_a}")
            # Prove zero writes: classify again and roll back (reads only).
            again, s2 = classify(bundle, reg, "dry")
            if s2 != summary:
                raise PreflightError("dry-run mutated state")
            log(f"RESULT: PASS dry-run, 0 writes, {summary['WOULD_WRITE']} would_write, "
                f"{summary['ALREADY_APPLIED']} already_applied "
                f"({time.time()-started:.1f}s)")
            return 0

        if args.rollback_rehearsal:
            counts, _, _ = apply_writes(by_doctype, reg, args.reapply, True)
        else:
            counts, _, _ = apply_writes(by_doctype, reg, args.reapply, False)
        log("APPLY " + json.dumps(counts, sort_keys=True))

        # Post-apply re-classification (transaction committed or rolled back).
        _, final = classify(bundle, reg, "final")
        log("FINAL " + json.dumps(final, sort_keys=True))
        if args.rollback_rehearsal:
            if final["WOULD_WRITE"] != summary["WOULD_WRITE"]:
                raise PreflightError("post-rollback state drift")
            log(f"RESULT: PASS rehearsal ({time.time()-started:.1f}s) — site unchanged")
        else:
            if final["ALREADY_APPLIED"] != 188:
                raise PreflightError("post-apply not all rows applied — NOTE: the "
                                     "commit already happened; data IS persisted, "
                                     "re-run the verifier to inspect final state")
            log(f"RESULT: PASS apply ({time.time()-started:.1f}s)")
        return 0
    except PreflightError as exc:
        log(f"RESULT: FAIL — {exc}")
        try:
            frappe.db.rollback()
        except Exception:
            pass
        return 1
    finally:
        try:
            frappe.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
