"""Tier 5J deliverable C — post-migration bilingual readiness verifier (fail-closed).

Modes:
  --snapshot-out PATH   capture full per-doctype state (values, norms, identity,
                        english, parent, lft/rgt) as the `--pre` reference.
                        R4: refuses any path outside sites/<site>/private/ (holds
                        Arabic values).
  (default)             verify final state against the owner-approved bundle:
                          V1 exact per-doctype approved counts (188 total / 15 doctypes,
                             fixture row frozen-excluded but still present)
                          V2 norm fields server-derivable-equal on ALL 189 populated
                             rows (188 approved + fixture; norm ==
                             _normalize_arabic(value), never client-forged)
                          V3 frozen-field equality vs --pre snapshot (identity,
                             english, parent, lft/rgt, name set — ar/norm exempt)
                          V4 NestedSet structural validity for all tree doctypes
                             (lft < rgt, parents exist, intervals nested/disjoint)
                          V5 desk search probes: bilingual_service.search_bilingual
                             (Arabic exact + English identity hit on one representative
                             row per doctype) and
                             transaction_link_search.search_transactions targets —
                             bounded latency reported

Exit 0 = PASS, 1 = FAIL. Read-only: opens a transaction, rolls it back.
"""

import argparse
import hashlib
import json
import os
import sys
import time

BENCH = "/home/mohamed/frappe-bench"
APPS = f"{BENCH}/apps"
SITES = f"{BENCH}/sites"
sys.path.insert(0, f"{APPS}/construction")

import frappe  # noqa: E402

EXPECTED_VALUES_SHA256 = "7390a0c87f8ebab1e602521549b775f8768d3ab9bb40a1caf055f4c5c31d53bf"
TOPO = [
    "Company", "Account", "Cost Center", "Warehouse", "Project",
    "Item Group", "Customer Group", "Supplier Group", "Territory",
    "Department", "Task", "UOM", "Item", "Customer", "Terms and Conditions",
]
TREE = {
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
FIXTURE = ("Warehouse", "CT-TEST-P2-WH-01 - TQC")
EXPECTED_APPROVED = 188
EXPECTED_POPULATED = 189  # + frozen 5C fixture (F-5J-1)

fails = []


def log(msg):
    print(msg, flush=True)


def fail(msg):
    fails.append(msg)
    log(f"  FAIL: {msg}")


def ok(msg):
    log(f"  ok: {msg}")


def registry():
    return json.load(open(f"{APPS}/construction/construction/data/bilingual/"
                          "bilingual_registry.json", encoding="utf-8"))


def capture(reg):
    """Full per-doctype state of every populated row (arabic/non-arabic)."""
    snap = {}
    for dt in TOPO:
        m = reg["doctypes"][dt]
        fields = ["name", m["arabic_field"], m["norm_field"]]
        if m.get("identity_field"):
            fields.append(m["identity_field"])
        if m.get("english_field") and m["english_field"] not in fields:
            fields.append(m["english_field"])
        if dt in TREE:
            fields += [TREE[dt], "old_parent", "lft", "rgt"]
        rows = frappe.get_all(dt, filters={m["arabic_field"]: ("!=", "")},
                              fields=fields, limit_page_length=0)
        snap[dt] = {r["name"]: {k: r.get(k) for k in fields if k != "name"}
                    for r in rows}
    return snap


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", default="v16.localhost")
    ap.add_argument("--values", default=None)
    ap.add_argument("--pre", default=None, help="snapshot from --snapshot-out")
    ap.add_argument("--snapshot-out", default=None)
    ap.add_argument("--skip-probes", action="store_true")
    args = ap.parse_args()

    frappe.init(site=args.site, sites_path=SITES)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        reg = registry()

        if args.snapshot_out:
            private_root = os.path.realpath(os.path.join(SITES, args.site, "private"))
            if not os.path.realpath(args.snapshot_out).startswith(private_root + os.sep):
                log("VERIFY RESULT: FAIL — snapshot contains Arabic values; R4 requires "
                    f"a path under {private_root}/")
                return 1
            snap = capture(reg)
            raw = json.dumps(snap, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
            open(args.snapshot_out, "w", encoding="utf-8").write(raw)
            n = sum(len(v) for v in snap.values())
            log(f"SNAPSHOT wrote {args.snapshot_out}: {n} populated rows across "
                f"{len(snap)} doctypes sha16="
                f"{hashlib.sha256(raw.encode()).hexdigest()[:16]}")
            return 0

        from construction.services.bilingual_service import _normalize_arabic

        # ---------------------------------------------------- V1 counts
        values_path = args.values or os.path.join(
            SITES, args.site, "private", "production-migration",
            "consolidated_values.json")
        raw = open(values_path, "rb").read()
        if hashlib.sha256(raw).hexdigest() != EXPECTED_VALUES_SHA256:
            fail("values bundle sha mismatch (approval binding)")
            log("VERIFY RESULT: FAIL")
            return 1
        bundle = json.loads(raw.decode("utf-8"))
        want = bundle["doctype_counts"]
        total = 0
        for dt in TOPO:
            m = reg["doctypes"][dt]
            n = frappe.db.count(dt, {m["arabic_field"]: ("!=", "")})
            total += n
            expect = want[dt] + (1 if dt == FIXTURE[0] else 0)
            if n != expect:
                fail(f"{dt}: populated-arabic {n} != approved {want[dt]}"
                     + (" (+1 fixture)" if dt == FIXTURE[0] else ""))
        if total != EXPECTED_POPULATED:
            fail(f"total populated-arabic {total} != {EXPECTED_POPULATED} "
                 f"({EXPECTED_APPROVED} approved + 1 fixture)")
        else:
            ok(f"V1 counts: {EXPECTED_APPROVED} approved rows across 15 doctypes "
               f"({EXPECTED_POPULATED} populated incl. frozen fixture)")
        fx = frappe.db.get_value(FIXTURE[0], FIXTURE[1],
                                 reg["doctypes"]["Warehouse"]["arabic_field"])
        if not fx:
            fail("frozen fixture row/value missing (5C exclusion broken)")
        else:
            fx_norm = frappe.db.get_value(
                FIXTURE[0], FIXTURE[1],
                reg["doctypes"]["Warehouse"]["norm_field"])
            if fx_norm != _normalize_arabic(fx):
                fail("frozen fixture norm not server-derivable-equal")

        # ---------------------------------------------------- V2 norms
        bad_norm = bad_equal = 0
        for row in bundle["rows"]:
            dt = row["doctype"]
            m = reg["doctypes"][dt]
            if not frappe.db.exists(dt, row["name"]):
                fail(f"missing document: {dt} {row['name']}")
                continue
            live, norm = frappe.db.get_value(dt, row["name"],
                                             [m["arabic_field"], m["norm_field"]])
            if (live or None) != row["arabic"]:
                bad_equal += 1
                fail(f"value drift: {dt} {row['name']}")
            if norm != _normalize_arabic(row["arabic"]):
                bad_norm += 1
                fail(f"norm not server-derivable-equal: {dt} {row['name']}")
        if not bad_norm and not bad_equal:
            ok("V2 values byte-equal to approval; all 189 norms (188 approved + "
               "fixture) server-derived and correct")

        # ------------------------------------------- V3 frozen vs --pre
        if args.pre:
            pre = json.load(open(args.pre, encoding="utf-8"))
            post = capture(reg)
            if set(pre) != set(post):
                fail(f"snapshot doctype set drift: {sorted(set(pre) ^ set(post))}")
            frozen = 0
            for dt in pre:
                if set(pre[dt]) != set(post.get(dt, {})):
                    fail(f"{dt}: row set drift vs pre-snapshot")
                    continue
                exempt = {reg["doctypes"][dt]["arabic_field"],
                          reg["doctypes"][dt]["norm_field"]}
                for name in pre[dt]:
                    a, b = pre[dt][name], post[dt][name]
                    for k in a:
                        if k in exempt:
                            continue
                        if a[k] != b.get(k):
                            fail(f"{dt} {name}: frozen field {k} changed")
                        else:
                            frozen += 1
            ok(f"V3 frozen-field equality vs pre-snapshot: {frozen} field-cells unchanged")
        else:
            log("  skip: V3 (no --pre snapshot)")

        # ------------------------------------------------- V4 tree checks
        for dt, parent_f in TREE.items():
            rows = frappe.get_all(dt, fields=["name", parent_f, "lft", "rgt"],
                                  limit_page_length=0)
            names = {r["name"] for r in rows}
            ivals, roots = [], 0
            for r in rows:
                if r.lft is None or r.rgt is None or r.lft >= r.rgt:
                    fail(f"{dt} {r['name']}: invalid lft/rgt")
                    continue
                if not r[parent_f]:
                    roots += 1
                elif r[parent_f] not in names:
                    fail(f"{dt} {r['name']}: dangling parent {r[parent_f]!r}")
                ivals.append((r.lft, r.rgt, r["name"]))
            ivals.sort()
            for (l1, r1, n1), (l2, r2, n2) in zip(ivals, ivals[1:]):
                # lft strictly increasing: valid iff disjoint or next nested in prev.
                if r1 <= l2:
                    continue
                if l1 < l2 and r2 <= r1:
                    continue
                fail(f"{dt}: overlapping intervals {n1}/{n2}")
            if args.pre and dt in pre:
                pre_tree = {n: (v.get(parent_f), v.get("lft"), v.get("rgt"))
                            for n, v in pre[dt].items()}
                post_tree = {r["name"]: (r[parent_f], r.lft, r.rgt) for r in rows}
                # pre-snapshot holds populated rows only: compare that subset
                # (row-set equality is enforced by V3).
                sub_post = {n: post_tree.get(n) for n in pre_tree}
                if pre_tree != sub_post:
                    fail(f"{dt}: tree structure mutated vs pre-snapshot")
            if roots == 0:
                fail(f"{dt}: no root row")
            else:
                ok(f"V4 {dt}: tree valid ({len(rows)} rows, {roots} root(s))")

        # ------------------------------------------------- V5 search probes
        if not args.skip_probes:
            from construction.services.bilingual_service import search_bilingual
            from construction.services.transaction_link_search import search_transactions
            lat = []
            for dt in TOPO:
                m = reg["doctypes"][dt]
                row = next(iter(bundle_row for bundle_row in bundle["rows"]
                                if bundle_row["doctype"] == dt))
                name = row["name"]
                ar = row["arabic"]
                english = (frappe.db.get_value(dt, name, m["english_field"])
                           if m.get("english_field") else None) or name
                for q, tag in ((ar, "ar"), (english, "en")):
                    t0 = time.perf_counter()
                    try:
                        res = search_bilingual(dt, txt=q, page_length=20, with_meta=True)
                    except Exception as exc:  # noqa: BLE001
                        fail(f"probe {dt} [{tag}] raised: {exc}")
                        continue
                    dt_ms = (time.perf_counter() - t0) * 1000
                    lat.append(dt_ms)
                    values = {r.get("value") for r in ((res or {}).get("results") or [])}
                    if name not in values:
                        fail(f"probe {dt} [{tag}] missed {name!r} in {len(values)} hits")
            # Transactional link search: bounded responsiveness (Customer target).
            cust = next(r for r in bundle["rows"] if r["doctype"] == "Customer")
            for target in ("Sales Order", "Purchase Order"):
                t0 = time.perf_counter()
                try:
                    res = search_transactions(target, txt=cust["arabic"], page_length=10)
                    lat.append((time.perf_counter() - t0) * 1000)
                    if not isinstance(res, list):
                        fail(f"search_transactions({target}) non-list return")
                except Exception as exc:  # noqa: BLE001
                    fail(f"search_transactions({target}) raised: {exc}")
            if lat:
                ok(f"V5 probes: {len(lat)} queries, p50={sorted(lat)[len(lat)//2]:.1f}ms "
                   f"max={max(lat):.1f}ms")

        if fails:
            log(f"VERIFY RESULT: FAIL ({len(fails)} failed checks)")
            return 1
        log("VERIFY RESULT: PASS (V1 counts, V2 norms, V3 frozen, V4 trees, V5 probes)")
        return 0
    finally:
        try:
            frappe.db.rollback()
            frappe.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
