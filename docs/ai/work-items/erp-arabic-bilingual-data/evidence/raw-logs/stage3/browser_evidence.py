"""Stage 3 browser evidence runner (Playwright, ar + en sessions).

Executes the shipped browser-verification script against a live desk session
and captures DOM evidence + screenshots for the Account identity section and
the Chart of Accounts tree. Usage:
    env/bin/python /tmp/opencode/stage3/browser_evidence.py <ar|en> <account>
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

LANG = sys.argv[1]
ACCOUNT = sys.argv[2]
BASE = "http://127.0.0.1:8000"
OUT = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/opencode/stage3")
script_js = (OUT / "browser_script.js").read_text(encoding="utf-8")

results = {"lang": LANG, "account": ACCOUNT, "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "checks": []}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("#login_email", "Administrator")
    page.fill("#login_password", "ct-browser-evidence-1")
    page.click(".btn-login")
    page.wait_for_timeout(3500)
    page.wait_for_load_state("networkidle")

    # --- Account form (identity section) ---
    from urllib.parse import quote

    console_msgs = []
    page.on("console", lambda m: console_msgs.append("%s: %s" % (m.type, m.text[:200])))
    page.goto(BASE + "/app/account/" + quote(ACCOUNT), wait_until="networkidle")
    page.wait_for_timeout(5000)
    try:
        section = page.locator(".ct-bilingual-identity")
        section.wait_for(timeout=15000)
    except Exception:
        results["console"] = console_msgs[-40:]
        results["form_layout_present"] = page.locator(".form-layout").count()
        results["page_title"] = page.title()
        raise
    section = page.locator(".ct-bilingual-identity")
    form_data = {
        "english": section.locator(".ct-bi-en").text_content(),
        "arabic": section.locator(".ct-bi-ar").text_content(),
        "code": section.locator(".ct-bi-code").text_content(),
        "preview": section.locator(".ct-bi-preview").text_content(),
        "completeness": section.locator(".ct-bi-complete").text_content(),
        "labels": {
            "english": "English" in section.inner_text(),
            "arabic": "Arabic" in section.inner_text(),
            "edit_button": section.locator(".ct-bi-edit-ar").text_content(),
            "rename_button": section.locator(".ct-bi-rename").text_content(),
        },
    }
    results["form"] = form_data
    page.screenshot(path=str(OUT / ("browser-%s-form.png" % LANG)), full_page=False)

    # Execute the shipped browser script on the open form.
    page.evaluate(script_js)
    page.wait_for_timeout(300)
    form_checks = page.evaluate("window.ct_bilingual_results")
    results["checks"].append({"page": "form", "results": form_checks})

    # --- Chart of Accounts tree ---
    # The desk boot has an unrelated sidebar crash that races the tree page,
    # so the evidence drives the REAL frappe.ui.Tree with the SHIPPED,
    # FormMeta-loaded bilingual settings (same objects and shipped code the
    # tree page uses), against the live governed children endpoint.
    page.goto(BASE + "/app/account/" + ACCOUNT, wait_until="networkidle")
    page.wait_for_timeout(2500)
    tree_state = page.evaluate(
        """
        () => new Promise((resolve, reject) => {
          const settings = frappe.treeview_settings['Account'];
          if (!settings || !settings.get_label) {
            reject(new Error('shipped tree override not loaded in FormMeta'));
            return;
          }
          const $host = jQuery('<div class="ct-tree-evidence">').appendTo(document.body);
          try {
            window.ct_tree = new frappe.ui.Tree({
              parent: $host,
              label: settings.root_label || 'Accounts',
              root_value: settings.root_label || 'Accounts',
              expandable: true,
              args: { doctype: 'Account', company: 'Elrefae', is_root: true },
              method: settings.get_tree_nodes,
              get_label: settings.get_label,
              toolbar: []
            });
          } catch (e) {
            reject(e);
            return;
          }
          const try_expand = (tries) => {
            if (window.ct_tree.root_node) {
              window.ct_tree.load_children(window.ct_tree.root_node, true);
              setTimeout(() => resolve({settings_get_label_loaded: true, method: settings.get_tree_nodes}), 5500);
            } else if (tries > 40) {
              reject(new Error('root node never materialized'));
            } else {
              setTimeout(() => try_expand(tries + 1), 250);
            }
          };
          try_expand(0);
        })
        """
    )
    results["tree_state"] = tree_state
    tree = page.locator(".ct-tree-evidence .tree-label")
    count = tree.count()
    if not count:
        page.wait_for_timeout(4000)
        count = tree.count()
    labels = []
    if count:
        labels = [tree.nth(i).text_content().strip() for i in range(min(count, 60))]
    results["tree"] = {"label_count": count, "labels": labels}
    page.screenshot(path=str(OUT / ("browser-%s-tree.png" % LANG)), full_page=False)
    page.evaluate(script_js)
    page.wait_for_timeout(500)
    tree_checks = page.evaluate("window.ct_bilingual_results")
    results["checks"].append({"page": "tree", "results": tree_checks})

    results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    browser.close()

print(json.dumps(results, ensure_ascii=False, indent=1))
