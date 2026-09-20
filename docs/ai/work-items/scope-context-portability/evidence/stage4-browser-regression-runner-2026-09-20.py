import json, pathlib, sys, time

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
JS_PATH = "/home/mohamed/frappe-bench/apps/construction/construction/public/js/bilingual/account_bilingual_browser_tests.js"
PW = "/tmp/opencode/pw.log"


def run_session(pw, lang, out):
    sess = {"session": lang, "steps": []}
    out["sessions"].append(sess)
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text[-300:]))

    def step(name, fn):
        try:
            sess["steps"].append({"step": name, "ok": True, "detail": fn()})
        except Exception as e:
            sess["steps"].append({"step": name, "ok": False, "error": repr(e)[:600]})

    step("login", lambda: (
        page.goto(BASE + "/login", wait_until="networkidle", timeout=60000),
        page.fill("#login_email", "Administrator"),
        page.fill("#login_password", "CtBrw-2026-tmp"),
        page.click(".btn-login"),
        page.wait_for_url(lambda u: "/index" in u or "/app" in u, timeout=60000),
        page.wait_for_function("() => window.frappe && frappe.boot && frappe.boot.lang", timeout=60000),
        page.evaluate("frappe.boot.lang"),
        "ok",
    ) and "logged in")

    def boot():
        return {"boot_lang": page.evaluate("frappe.boot.lang"),
                "user_language": page.evaluate("frappe.boot.user && frappe.boot.user.language")}
    step("boot", boot)

    results = []

    def run_script(where):
        page.wait_for_timeout(3000)
        js = pathlib.Path(JS_PATH).read_text()
        summary = page.evaluate(js)
        results.append({
            "where": where,
            "summary": summary,
            "boot_lang": page.evaluate("frappe.boot.lang"),
            "results": page.evaluate("window.ct_bilingual_results || []"),
        })
        return summary

    def form():
        page.goto(BASE + "/app/account/GST%20-%20E", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function(
            "() => window.cur_frm && cur_frm.doctype === 'Account' && !cur_frm.is_new()"
            " && cur_frm.fields_dict.ct_bilingual_identity"
            " && cur_frm.fields_dict.ct_bilingual_identity.$wrapper"
            " && cur_frm.fields_dict.ct_bilingual_identity.$wrapper.find('.ct-bi-row').length > 0",
            timeout=60000)
        page.wait_for_timeout(2000)
        snap = page.evaluate("""() => {
            const $w = cur_frm.fields_dict.ct_bilingual_identity && cur_frm.fields_dict.ct_bilingual_identity.$wrapper;
            if (!$w) return null;
            return {en: $w.find('.ct-bi-en').text(), ar: $w.find('.ct-bi-ar').text(),
                    complete: $w.find('.ct-bi-complete').text(), boot_lang: frappe.boot.lang};
        }""")
        return {"summary": run_script("account-form/GST - E"), "identity_section": snap}
    step("account-form", form)

    def tree():
        page.goto(BASE + "/app/account/view/tree", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".tree-label", timeout=60000)
        page.wait_for_timeout(4000)
        return run_script("account-tree")
    step("account-tree", tree)

    sess["console"] = logs[-40:]
    sess["results"] = results
    ctx.close()
    browser.close()


def main():
    langs = json.loads(sys.argv[1]) if len(sys.argv) > 1 else ["ar"]
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sessions": []}
    with sync_playwright() as pw:
        for lang in langs:
            try:
                run_session(pw, lang, out)
            except Exception as e:
                out["sessions"].append({"session": lang, "fatal": repr(e)[:600]})
    with open(PW, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("__DONE__ sessions=%d" % len(out["sessions"]))


main()
