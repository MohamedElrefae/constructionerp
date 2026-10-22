#!/usr/bin/env python3
"""F25 full-asset sweep: every hooks-registered asset, source vs served (byte identity).

Covers app_include_css, app_include_js, web_include_css, web_include_js and
website_context images — not just the 5 previously probed. Records presence,
byte-identity (md5 source vs served), and version-consistency findings.
"""

import hashlib
import re
import sys

APP = "/home/mohamed/frappe-bench/apps/construction"
SRC = APP + "/construction/public"
SITES_ASSETS = "/home/mohamed/frappe-bench/sites/assets/construction"

hooks = open(APP + "/construction/hooks.py").read()


def strip_block(name):
    m = re.search(rf"^{name}\s*=\s*(\[.*?\]|\".*?\")", hooks, re.S | re.M)
    if not m:
        return None
    return m.group(1)


def urls_from(block):
    if block is None:
        return []
    return re.findall(r'"(/assets/construction/[^"]+)"', block)


targets = []
for var in ("app_include_css", "app_include_js", "web_include_css", "web_include_js"):
    for u in urls_from(strip_block(var)):
        targets.append((var, u))

# website_context images
for u in re.findall(r'"(/assets/construction/images/[^"]+)"', hooks):
    targets.append(("website_context", u))

rows = []
findings = []
for var, url in targets:
    base, _, ver = url.partition("?v=")
    rel = base.replace("/assets/construction/", "")
    src_path = f"{SRC}/{rel}"
    srv_path = f"{SITES_ASSETS}/{rel}"
    r = {"hook": var, "url": url, "version": ver or "(none)"}

    def md5(p):
        return hashlib.md5(open(p, "rb").read()).hexdigest()

    if not __import__("os").path.exists(src_path):
        r["status"] = "SOURCE_MISSING"
    else:
        r["source"] = md5(src_path)
        r["source_size"] = __import__("os").path.getsize(src_path)
        if __import__("os").path.exists(srv_path):
            r["served"] = md5(srv_path)
            r["identity"] = "identical" if r["source"] == r["served"] else "MISMATCH"
        else:
            r["served"] = None
            r["identity"] = "NOT_SYNCED"
    rows.append(r)

# version consistency: same base file across hooks must carry same ?v=
by_base = {}
for var, url in targets:
    base, _, ver = url.partition("?v=")
    by_base.setdefault(base, set()).add(ver or "(none)")
for base, vers in sorted(by_base.items()):
    if len(vers) > 1:
        findings.append(f"VERSION_SPLIT: {base} registered as {sorted(vers)}")

missing_src = [r for r in rows if r.get("status") == "SOURCE_MISSING"]
not_synced = [r for r in rows if r.get("identity") == "NOT_SYNCED"]
mismatch = [r for r in rows if r.get("identity") == "MISMATCH"]
no_ver = [r for r in rows if r["version"] == "(none)"]

print(
    f"registered assets swept: {len(rows)} "
    f"(css={sum(1 for r in rows if r['hook'].endswith('css'))}, "
    f"js={sum(1 for r in rows if r['hook'].endswith('js'))}, "
    f"images={sum(1 for r in rows if r['hook'] == 'website_context')})"
)
for r in rows:
    print(f"  [{r['identity'] if 'identity' in r else r['status']:>11}] " f"{r['url']}  (v={r['version']})")
print()
print("FINDINGS:")
for f in findings:
    print("  " + f)
if not findings:
    print("  none")
print(f"source-missing: {len(missing_src)}")
for r in missing_src:
    print(f"  {r['url']}")
print(f"not-synced (source present, served absent): {len(not_synced)}")
for r in not_synced:
    print(f"  {r['url']}")
print(f"byte-mismatch: {len(mismatch)}")
for r in mismatch:
    print(f"  {r['url']} src={r.get('source')} served={r.get('served')}")
print(f"registered without ?v= (framework pipeline): {len(no_ver)}")
for r in no_ver:
    print(f"  {r['url']}")

fails = len(missing_src) + len(mismatch) + len(findings)
print()
print(
    "SWEEP RESULT:",
    "FINDINGS PRESENT"
    if fails
    else "CLEAN (not-synced rows need bench --site <site> build/clear-cache before browser evidence)",
)
sys.exit(0 if fails == 0 else 1)
