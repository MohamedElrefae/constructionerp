#!/usr/bin/env python
"""Reproduce latent defect D4 — custom-query calling convention vs Frappe `search_link`.

Read-only. Run from the bench root:

    ./env/bin/python apps/construction/docs/ai/work-items/search-query-convention/evidence/scripts/reproduce_d4.py

Sections
    A  signatures and the positional mapping `search_widget` actually applies
    B  why `frappe.call` cannot repair the mapping (kwargs filtered, args not)
    C  live reproduction through the genuine entry point (`search_link`)
    D  wiring audit — who does (not) instantiate the enhancer that sets `get_query`
    E  contrast — a custom query that *is* canonical and tuple-shaped (BOQ)
"""

import inspect
import re
import traceback
from pathlib import Path

import frappe

APP_ROOT = Path(__file__).resolve().parents[6]
SITE = "v16.localhost"
MASTER_QUERY = "construction.searchable_dropdown.api.search.searchable_link_search"


def hr(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def section_a():
    hr("A. Signatures and the positional mapping search_widget applies")
    from frappe.desk.search import search_widget
    from construction.searchable_dropdown.api.search import searchable_link_search

    src = inspect.getsource(search_widget)
    call_block = [
        line.strip()
        for line in src.splitlines()
        if re.search(r"frappe\.call\(|^\s*query,|doctype,|txt,|searchfield,|start,|page_length,|filters,|as_dict=", line)
    ]
    print("search_widget custom-query call site (frappe/desk/search.py):")
    for line in call_block[:12]:
        print("   ", line)

    callee = list(inspect.signature(searchable_link_search).parameters)
    print("\ncallee parameter order:", callee)

    # positional slots actually sent by search_widget: (doctype, txt, searchfield, start, page_length, filters)
    sent = ["doctype", "txt", "searchfield", "start", "page_length", "filters"]
    print("\n  # | search_widget sends | -> | callee parameter")
    print("  ---+---------------------+----+------------------")
    for i, (got, want) in enumerate(zip(sent, callee), start=1):
        flag = "  <-- SHIFTED" if got != want else ""
        print(f"  {i:>2} | {got:<19} | -> | {want}{flag}")


def section_b():
    hr("B. frappe.call filters kwargs only — positional args pass through")
    import frappe as f

    print(inspect.getsource(f.call).strip())
    from frappe import get_newargs
    from construction.searchable_dropdown.api.search import searchable_link_search

    kwargs = {"as_dict": False, "reference_doctype": None, "ignore_user_permissions": False, "link_fieldname": None}
    kept = get_newargs(searchable_link_search, kwargs)
    print("kwargs sent :", sorted(kwargs))
    print("kwargs kept :", sorted(kept), " <- 'as_dict' has nowhere to go")
    print("=> the six positional slots are never re-bound by name; the shift is permanent.")


def section_c():
    hr("C. Live reproduction through the genuine entry point (search_link)")
    from frappe.desk.search import search_link

    try:
        results = search_link(
            doctype="Account",
            txt="cash",
            query=MASTER_QUERY,
            page_length=5,
        )
        print("NO EXCEPTION — results:", results)
    except Exception as exc:
        tb = traceback.format_exc().strip().splitlines()
        print("RAISED:", type(exc).__name__)
        print("\n".join(tb[-14:]))
        print(
            "\nbuild_for_autosuggest iterates item[0] on rows the custom query "
            "returned as dicts -> KeyError. Row shape is defect D4b."
        )


def section_d():
    hr("D. Wiring audit — who instantiates the enhancer that sets get_query")
    hooks = (APP_ROOT / "construction/hooks.py").read_text(encoding="utf-8")
    block = hooks.split("app_include_js = [", 1)[1].split("]", 1)[0]
    assets = re.findall(r'["\'](/assets/construction/js/[^"\']+)["\']', block)
    loaded = []
    for asset in assets:
        rel = asset.split("/js/", 1)[1].split("?")[0]
        loaded.append(APP_ROOT / "construction/public/js" / rel)

    def scan(pattern):
        hits = []
        for path in loaded:
            if not path.exists():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(pattern, line):
                    hits.append((path.name, lineno, line.strip()[:96]))
        return hits

    ctor_hits = scan(r"new SearchableDropdownEnhancer|searchable_dropdown\.enhance\s*\(|enhanceCustomerField|enhanceSupplierField")
    print("loaded JS files scanned            :", len(loaded))
    print("enhancer constructor / enhance() call sites:")
    for name, lineno, text in ctor_hits:
        print(f"    {name}:{lineno}: {text}")
    external = [h for h in ctor_hits if h[0] != "searchable_dropdown.js"]
    print("    -> call sites OUTSIDE the enhancer module:", external or "NONE")

    print("\n'get_query' + 'searchable_link_search' occurrences in loaded JS:")
    query_hits = [
        (name, lineno, text)
        for name, lineno, text in scan(r"searchable_link_search")
        if "searchable_link_search" in text
    ]
    for name, lineno, text in query_hits:
        kind = "comment" if text.lstrip().startswith(("*", "//", "/*")) else "code"
        print(f"    {name}:{lineno} [{kind}]: {text}")
    code_users = [h for h in query_hits if not h[2].lstrip().startswith(("*", "//", "/*")) and h[0] != "searchable_dropdown.js"]
    print("    -> code references outside the enhancer module:", code_users or "NONE")

    configs = sorted((APP_ROOT / "construction/public/js/searchable_dropdown/config").glob("*.js"))
    print("\nconfig files that WOULD wire it     :", [c.name for c in configs])
    for cfg in configs:
        print(f"    registered in hooks.py? {cfg.name}: {cfg.name in hooks}")
    print("nested searchable_dropdown/hooks.py loaded by root hooks.py?:",
          "searchable_dropdown.hooks" in hooks,
          "(Frappe only reads the app-root hooks.py)")
    print("=> the class is exported, never instantiated; the defective path has no browser caller.")


def section_e():
    hr("E. Contrast — a canonical, tuple-shaped custom query (BOQ)")
    from construction.api.boq_link_queries import get_boq_headers

    params = list(inspect.signature(get_boq_headers).parameters)
    expected = ["doctype", "txt", "searchfield", "start", "page_len", "filters"]
    print("get_boq_headers parameters :", params[: len(expected)])
    print("search_widget positional   :", expected)
    print("canonical match            :", params[: len(expected)] == expected)

    src = inspect.getsource(get_boq_headers)
    returns = [line.strip() for line in src.splitlines() if line.strip().startswith("return") and "(" in line]
    print("return statements          :")
    for line in returns[:3]:
        print("    ", line[:96])
    print("    -> frappe.db.sql(...) without as_dict yields list-of-tuples,")
    print("       which is exactly the shape build_for_autosuggest indexes with item[0].")
    print("=> BOQ works through search_link; the master query matches neither convention.")


def main():
    frappe.init(site=SITE, sites_path="sites")
    frappe.connect()
    try:
        section_a()
        section_b()
        section_c()
        section_d()
        section_e()
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
