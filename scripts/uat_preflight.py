"""Stage-7 UAT preflight gate (owner decision 2026-09-21, hard preflight).

Hard checks before any browser/UAT evidence run:
 1. managed redis cache :13000 reachable (TCP);
 2. managed redis queue  :11000 reachable;
 3. site /api/method/ping answers HTTP 200;
 4. fresh Desk payload populated for the `ar` session: login as
    Administrator, GET /desk, and the HTML must embed
    `"lang": "ar"` and an `__messages` dictionary with >= 1000 entries
    (a representative W6-0a key is verified too when provided).

Usage:
  python3 scripts/uat_preflight.py --site=v16.localhost --password=<pw> \
      [--key='Add / Remove Columns']

Exit 0 = PASS; otherwise failures are listed and the exit is 1. The script
performs read-only requests; no `_()` strings (not a localization surface).
"""

import http.client
import json
import re
import socket
import sys

FAILURES = []


def fail(name, detail):
    FAILURES.append(name + ": " + detail)
    print("FAIL " + name + ": " + detail[:200])


def okay(name, detail):
    print("PASS " + name + ": " + str(detail)[:200])


def redis_reachable(port, label):
    try:
        s = socket.create_connection(("127.0.0.1", int(port)), timeout=3)
        s.sendall(b"PING\r\n")
        data = s.recv(16)
        s.close()
        if data.startswith(b"+PONG"):
            okay("redis-" + label, "port %s PING ok" % port)
        else:
            fail("redis-" + label, "unexpected response on %d: %r" % (port, data[:16]))
    except OSError as exc:
        fail("redis-" + label, "port %s not reachable: %s" % (port, exc))


def get_desk_boot(host, path="/desk", body=None):
    conn = http.client.HTTPConnection(host, 8000, timeout=30)
    headers = {"Accept": "text/html"}
    if body:
        conn.request("POST", path, body=body, headers=dict(headers, **{"Content-Type": "application/x-www-form-urlencoded"}))
    else:
        conn.request("GET", path, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()

    sid = None
    for key, value in resp.getheaders():
        if key.lower() == "set-cookie":
            m = re.search(r"sid=([^;]+)", value)
            if m and m.group(1) not in ("Guest", "None"):
                sid = m.group(1)
    return resp.status, data, sid


def main():
    target = "v16.localhost"
    password = None
    key = None
    for arg in sys.argv[1:]:
        if arg.startswith("--site="):
            target = arg.split("=", 1)[1]
        elif arg.startswith("--password="):
            password = arg.split("=", 1)[1]
        elif arg.startswith("--key="):
            key = arg.split("=", 1)[1]
        elif arg.startswith("--key-index"):
            pass

    redis_reachable(13000, "cache")
    redis_reachable(11000, "queue")

    host = target
    try:
        conn = http.client.HTTPConnection(host, 8000, timeout=15)
        conn.request("GET", "/api/method/ping")
        r = conn.getresponse()
        r.read()
        if r.status == 200:
            okay("site-http", "/ping 200")
        else:
            fail("site-http", "/ping status %s" % r.status)
        conn.close()
    except OSError as exc:
        fail("site-http", str(exc)[:160])

    if password:
        body = "usr=Administrator&pwd=" + password
        status, _, sid = get_desk_boot(host, "/api/method/login", body)
        if not sid:
            fail("desk-boot", "login failed / no session cookie")
        else:
            conn = http.client.HTTPConnection(host, 8000, timeout=30)
            conn.request("GET", "/desk", headers={"Cookie": "sid=" + sid})
            resp = conn.getresponse()
            html = resp.read().decode("utf-8", "replace")
            conn.close()
            if resp.status != 200:
                fail("desk-boot", "desk route status %s" % resp.status)
            else:
                m = re.search(r'frappe\.boot = (\{.*?\});\n', html, re.S)
                if not m:
                    fail("desk-boot", "boot JSON not found on desk page")
                else:
                    boot = json.loads(m.group(1))
                    msgs = boot.get("__messages") or {}
                    lang = boot.get("lang")
                    if lang == "ar":
                        okay("desk-boot", "boot lang=ar")
                    else:
                        fail("desk-boot", "boot lang=%r (expected ar)" % lang)
                    if isinstance(msgs, dict) and len(msgs) >= 1000:
                        okay("desk-boot", "__messages entries=%d" % len(msgs))
                    else:
                        fail("desk-boot", "__messages too small: %r" % (len(msgs) if isinstance(msgs, dict) else type(msgs).__name__))
                    if key:
                        if isinstance(msgs, dict) and key in msgs:
                            okay("desk-boot-key", repr(key) + " present in boot")
                        else:
                            fail("desk-boot-key", repr(key) + " absent from fresh boot __messages")
        if sid and not FAILURES:
            # proactive logout of the UAT session
            conn = http.client.HTTPConnection(host, 8000, timeout=15)
            conn.request("POST", "/api/method/logout", headers={"Cookie": "sid=" + sid})
            conn.getresponse().read()
            conn.close()
    else:
        print("NOTE: --password not provided; desk-boot check skipped")

    if FAILURES:
        print("UAT PREFLIGHT: %d failure(s)" % len(FAILURES))
        return 1
    print("UAT PREFLIGHT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
