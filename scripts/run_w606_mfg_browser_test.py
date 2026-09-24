"""UAT Preflight and Playwright browser evidence runner with atomic teardown."""
from __future__ import annotations

import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/mohamed/frappe-bench/apps/construction")
SCRIPT_DIR = ROOT / "docs/ai/work-items/scope-context-portability/evidence/raw-logs/stage6-w606-mfg-batch01"
PYTHON = "/home/mohamed/frappe-bench/env/bin/python3"

# 1. Setup temporary credential
temp_password = "uat-" + secrets.token_hex(16)

def run_bench_eval(code: str) -> None:
    res = subprocess.run(
        ["bench", "--site", "v16.localhost", "execute", "frappe.db.sql"],
        input="", text=True, capture_output=True, cwd="/home/mohamed/frappe-bench"
    )

print("Configuring temporary Administrator credentials...")
setup_cmd = f"""
import frappe
from frappe.utils.password import update_password

frappe.init("v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
update_password("Administrator", "{temp_password}")
frappe.db.set_value("User", "Administrator", "language", "ar")
frappe.db.commit()
try:
    frappe.cache.flushall()
except Exception as e:
    print("cache flush warning:", e)
frappe.destroy()
print("Administrator configured with temp password and language=ar")
"""

res = subprocess.run([PYTHON, "-c", setup_cmd], capture_output=True, text=True, cwd="/home/mohamed/frappe-bench")
print(res.stdout)
if res.returncode != 0:
    print(res.stderr)
    sys.exit(1)

try:
    # 2. Run UAT preflight
    print("Running uat_preflight.py...")
    preflight_proc = subprocess.run(
        [
            PYTHON, str(ROOT / "scripts/uat_preflight.py"),
            "--site", "v16.localhost",
            "--user", "Administrator",
            "--key", "Learn Manufacturing",
            "--min-messages", "1000",
        ],
        input=temp_password + "\n",
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    print("PREFLIGHT STDOUT:\n", preflight_proc.stdout)
    if preflight_proc.returncode != 0:
        print("PREFLIGHT STDERR:\n", preflight_proc.stderr)
        raise RuntimeError("UAT preflight failed")

    # 3. Run Playwright browser verification
    print("Running browser_evidence_w606_mfg_batch01.py...")
    browser_proc = subprocess.run(
        [PYTHON, str(SCRIPT_DIR / "browser_evidence_w606_mfg_batch01.py")],
        input=temp_password + "\n",
        text=True,
        capture_output=True,
        cwd=str(ROOT),
    )
    print("BROWSER STDOUT:\n", browser_proc.stdout)
    if browser_proc.returncode != 0:
        print("BROWSER STDERR:\n", browser_proc.stderr)
        raise RuntimeError("Browser evidence verification failed")

finally:
    # 4. Teardown: rotate password and restore language to en
    print("Teardown: restoring language to 'en' and rotating password...")
    final_rotated_pwd = "rotated-" + secrets.token_hex(16)
    teardown_cmd = f"""
import frappe
from frappe.utils.password import update_password

frappe.init("v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
frappe.connect()
update_password("Administrator", "{final_rotated_pwd}")
frappe.db.set_value("User", "Administrator", "language", "en")
frappe.db.set_value("System Settings", "System Settings", "language", "en")
frappe.db.commit()
try:
    frappe.cache.flushall()
except Exception as e:
    pass
frappe.destroy()
print("Teardown complete: language='en', password rotated.")
"""
    t_res = subprocess.run([PYTHON, "-c", teardown_cmd], capture_output=True, text=True, cwd="/home/mohamed/frappe-bench")
    print(t_res.stdout)

print("UAT Preflight and Browser verification completed successfully!")
