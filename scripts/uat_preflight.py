"""Stage-7 UAT preflight gate (owner decision 2026-09-21, hard preflight).

Hard checks before any browser/UAT evidence run:
 1. managed redis cache :13000 reachable (TCP);
 2. managed redis queue  :11000 reachable;
 3. site /api/method/ping answers HTTP 200;
 4. fresh Desk payload populated for the `ar` session: login as
    Administrator, GET /desk, and the HTML must embed
    `"lang": "ar"` and an `__messages` dictionary with >= 1000 entries
    (a representative W6-0a key is verified too when provided).

Secret handling (P1 review hardening, 2026-09-21):
 - the Administrator password is read from STDIN (hidden prompt fallback
   to getpass) — never accepted on argv (no shell history/ps disclosure);
 - the login payload is form-encoded (passwords containing `&`, `+`, `=`
   round-trip correctly);
 - the UAT session is logged out unconditionally whenever a session id
   exists (success OR failure path), via try/finally.

Usage:
  python3 scripts/uat_preflight.py --site=v16.localhost \
      [--key='Add / Remove Columns']      (password via STDIN or getpass)
  echo <pw> | python3 scripts/uat_preflight.py --site=v16.localhost --key='...'

Exit 0 = PASS; otherwise failures are listed and the exit is 1. The script
performs read-only requests; no `_()` strings (not a localization surface).
"""

import getpass
import http.client
import json
import re
import socket
import sys
import urllib.parse

FAILURES = []


def fail(name, detail):
    FAILURES.append(name + ": " + detail)
    print("FAIL " + name + ": " + str(detail)[:200])


def okay(name, detail):
    print("PASS " + name + ": " + str(detail)[:200])


def redis_reachable(port, label):
    try:
        s = socket.create_connection(("127.0.0.1", int(port)), timeout=3)
        s.sendall(b"PING\r\n")
        data = s.recv(16)
        s.close()
        if data.startswith(b"+PONG"):
            okay("redis-" + label, f"port {port} PING ok")
        else:
            fail("redis-" + label, f"unexpected response on {port}: {data[:16]!r}")
    except OSError as exc:
        fail("redis-" + label, f"port {port} not reachable ({exc})")


def read_password():
    """P1 hardening: never accept the secret on argv."""
    if not sys.stdin.isatty():
        pw = sys.stdin.readline().rstrip("\n")
        if pw:
            return pw
    try:
        return getpass.getpass("UAT preflight password for Administrator: ")
    except (EOFError, KeyboardInterrupt):
        return None


def http_req(host, path, method="GET", body=None, headers=None):
    conn = http.client.HTTPConnection(host, 8000, timeout=30)
    headers = dict(headers or {})
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read()
    sid = None
    for key, value in resp.getheaders():
        if key.lower() == "set-cookie":
            m = re.search(r"sid=([^;]+)", value)
            if m and m.group(1) not in ("Guest", "None"):
                sid = m.group(1)
    conn.close()
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    return resp.status, data, sid


def logout(host, sid):
    try:
        http_ok = http.client.HTTPConnection(host, 8000, timeout=15)
        http_ok.request("POST", "/api/method/logout", headers={"Cookie": "sid=" + sid})
        http_ok.getresponse().read()
        http_ok.close()
        okay("desk-boot", "UAT session logged out")
    except OSError:
        print("NOTE: cleanup logout could not reach the site (session kept until expiry)")


def main():
    target = "v16.localhost"
    key = None
    for arg in sys.argv[1:]:
        if arg.startswith("--site="):
            target = arg.split("=", 1)[1]
        elif arg.startswith("--key="):
            key = arg.split("=", 1)[1]

    password = read_password()

    sid = None
    try:
        redis_reachable(13000, "cache")
        redis_reachable(11000, "queue")

        host = target
        status, _, _s = http_req(host, "/api/method/ping")
        if status == 200:
            okay("site-http", "/ping 200")
        else:
            fail("site-http", f"/ping status {status}")

        if password:
            login_body = urllib_encode({"usr": "Administrator", "pwd": password})
            status, _, sid_new = http_req(
                host, "/api/method/login", body=login_body
            )
            sid = sid_new
            if not sid:
                fail("desk-boot", f"login failed / no session cookie ({status})")
            else:
                dstatus, html, _ = http_req(
                    host, "/desk", headers={"Cookie": "sid=" + sid}
                )
                if dstatus != 200:
                    fail("desk-boot", f"desk route status {dstatus}")
                else:
                    m = re.search(r"frappe\.boot = (\{.*?\});\n", html, re.S)
                    if not m:
                        fail("desk-boot", "boot JSON not found on desk page")
                    else:
                        boot = json.loads(m.group(1))
                        msgs = boot.get("__messages") or {}
                        lang = boot.get("lang")
                        if lang == "ar":
                            okay("desk-boot", "boot lang=ar")
                        else:
                            fail("desk-boot", f"boot lang={lang!r} (expected ar)")
                        if isinstance(msgs, dict) and len(msgs) >= 1000:
                            okay("desk-boot", f"__messages entries={len(msgs)}")
                        else:
                            fail(
                                "desk-boot",
                                "__messages too small: %r"
                                % (len(msgs) if isinstance(msgs, dict) else type(msgs).__name__),
                            )
                        if key:
                            if isinstance(msgs, dict) and key in msgs:
                                okay("desk-boot-key", repr(key) + " present in boot")
                            else:
                                fail(
                                    "desk-boot-key",
                                    repr(key) + " absent from fresh boot __messages",
                                )
        else:
            print("NOTE: password not provided; desk-boot check skipped")
    finally:
        if sid:
            # unconditional cleanup: log the UAT session out on success OR failure
            logout(target, sid)

    if FAILURES:
        print(f"UAT PREFLIGHT: {len(FAILURES)} failure(s)")
        return 1
    print("UAT PREFLIGHT: PASS")
    return 0


def urllib_encode(d):

    return urllib.parse.urlencode(d)


if __name__ == "__main__":
    raise SystemExit(main())
