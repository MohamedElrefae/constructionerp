"""Stage 3 live HTTP dispatch evidence (reproducible bundle runner).

Prerequisites (recorded in README.md of this bundle):
  1. bench --site v16.localhost console < setup.session   (fixture + output)
  2. bench serve --port 8000 > serve.log 2>&1 &           (dev server)
  3. ./env/bin/python http_dispatch.py > transcript.raw   (this script)
  4. cleanup.session run + output                          (fixture removal)

This script performs the actual HTTP requests with full request/response
transcription (method, URL, headers, form body, status, response body).
"""

import json
import os
import socket
from datetime import datetime, timezone

import requests

BASE = "http://127.0.0.1:8000"
ACC = "CT-HTTP-1 - CT HTTP Probe - E"
started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
s = requests.Session()


def emit(tag, request, response=None):
    record = {
        "tag": tag,
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "request": {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "body": getattr(request, "body", None),
        },
    }
    if response is not None:
        record["response"] = {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:2000],
        }
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))


preq = requests.Request(
    "POST", BASE + "/api/method/login", data={"usr": "Administrator", "pwd": "ct-browser-evidence-1"}
).prepare()
r0 = s.send(preq, timeout=30)
emit("login", preq, r0)

# 1) reason-free call through the vendor path (overridden -> governed refusal)
r1_req = requests.Request(
    "POST",
    BASE + "/api/method/erpnext.accounts.doctype.account.account.update_account_number",
    data={"name": ACC, "account_name": "CT HTTP Probe", "account_number": "CT-HTTP-2"},
).prepare()
r1 = s.send(r1_req, timeout=30)
emit("reason_free_call", r1_req, r1)

# 2) reasoned call through the same path
r2_req = requests.Request(
    "POST",
    BASE + "/api/method/erpnext.accounts.doctype.account.account.update_account_number",
    data={
        "name": ACC,
        "account_name": "CT HTTP Probe",
        "account_number": "CT-HTTP-2",
        "reason": "Live HTTP dispatch evidence",
    },
).prepare()
r2 = s.send(r2_req, timeout=30)
emit("reasoned_call", r2_req, r2)

print(
    json.dumps(
        {
            "summary": {
                "started_utc": started,
                "finished_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "host": socket.gethostname(),
                "reason_free_status": r1.status_code,
                "reason_free_exc": r1.json().get("exc_type"),
                "reasoned_status": r2.status_code,
                "reasoned_ok": (r2.json().get("message") or {}).get("ok"),
                "reasoned_renamed": (r2.json().get("message") or {}).get("renamed"),
                "reasoned_new_name": (r2.json().get("message") or {}).get("name"),
            }
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
