import json
import os
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
site = sys.argv[1]
os.environ["FRAPPE_BENCH_ROOT"] = str(LAB)
os.environ["FRAPPE_SITE"] = site
os.chdir(LAB / "sites")
sys.path[:0] = [str(LAB / "apps/construction"), str(LAB / "apps/erpnext")]
import frappe
import frappe.app
from frappe.app import application
from werkzeug.test import Client
from werkzeug.wrappers import Response

import construction

frappe.app._sites_path = str(LAB / "sites")
frappe.app._site = site
secret = json.loads((LAB / "run/credentials.json").read_text())
client = Client(application, Response, use_cookies=True)
r = client.post(
    "/api/method/login", data={"usr": "Administrator", "pwd": secret["admin"]}, headers={"Host": site}
)
results = {
    "site": site,
    "admin_login": r.status_code,
    "admin_login_message": r.json.get("message") if r.is_json else None,
}
r = client.get("/api/method/frappe.auth.get_logged_user", headers={"Host": site})
results["identity"] = r.json.get("message") if r.is_json else None
frappe.init(site, sites_path=str(LAB / "sites"))
frappe.connect()
frappe.set_user("Administrator")
files = frappe.get_all(
    "File",
    filters={"is_private": 1, "attached_to_doctype": "Variation Order"},
    fields=["file_url", "attached_to_name"],
    limit=1,
)
frappe.db.rollback()
frappe.destroy()
if files:
    url = files[0].file_url
    r = client.get(
        "/api/method/frappe.handler.download_file", query_string={"file_url": url}, headers={"Host": site}
    )
    results["private_download_admin"] = {
        "status": r.status_code,
        "bytes": len(r.data),
        "pdf": r.data.startswith(b"%PDF"),
    }
    guest = Client(application, Response, use_cookies=False)
    r = guest.get(
        "/api/method/frappe.handler.download_file", query_string={"file_url": url}, headers={"Host": site}
    )
    results["private_download_guest"] = {"status": r.status_code, "returned_pdf": r.data.startswith(b"%PDF")}
(LAB / "artifacts" / sys.argv[2]).write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
assert results["admin_login"] == 200 and results["identity"] == "Administrator"
if files:
    assert (
        results["private_download_admin"]["status"] == 200
        and results["private_download_guest"]["status"] in [401, 403]
        and not results["private_download_guest"]["returned_pdf"]
    )
