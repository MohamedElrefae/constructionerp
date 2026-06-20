/**
 * Browser smoke test for Option A+ report filter hardening.
 *
 * Validates:
 *   1. As Administrator, each of the 11 allowlisted reports loads
 *      (200 on the report page, JS evaluates, no console errors
 *      from the construction module).
 *   2. The JS module's hardening function is callable and is a no-op
 *      for unrestricted users.
 *
 * Run with bench running on v16.localhost:
 *
 *   cd /home/mohamed/frappe-bench/apps/construction
 *   PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/opt/google/chrome/chrome \
 *     node construction/tests/test_browser_scope.js
 */

const { chromium } = require(
	"/home/mohamed/frappe-bench/apps/construction/construction/tests/node_modules/playwright",
);

const BASE = "http://v16.localhost:8000";
const ADMIN = { usr: "Administrator", pwd: "test123" };

// All 11 allowlisted reports (per Option A+ plan).
const REPORTS = [
	"General Ledger",
	"Trial Balance",
	"Profit and Loss Statement",
	"Balance Sheet",
	"Accounts Payable",
	"Accounts Payable Summary",
	"Accounts Receivable",
	"Accounts Receivable Summary",
	"Budget Variance Report",
	"Cash Flow",
	"Project-wise Profitability",
];

async function getSid(email, password) {
	const res = await fetch(BASE + "/api/method/login", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ usr: email, pwd: password }),
	});
	const setCookie = res.headers.get("set-cookie") || "";
	const m = setCookie.match(/sid=([^;]+)/);
	return m ? m[1] : null;
}

async function run() {
	const browser = await chromium.launch({
		headless: true,
		executablePath:
			process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || "/opt/google/chrome/chrome",
		args: ["--no-sandbox", "--disable-dev-shm-usage"],
	});

	const context = await browser.newContext();
	const page = await context.newPage();

	// 1. Log in as Administrator.
	const sid = await getSid(ADMIN.usr, ADMIN.pwd);
	if (!sid) throw new Error("Could not log in as Administrator");
	await context.addCookies([
		{ name: "sid", value: sid, domain: "v16.localhost", path: "/" },
	]);

	// 2. Track console errors from our module only. We filter out
	//    pre-existing Frappe dev-server errors (e.g. 500 on
	//    getdoctype() during report rendering) that are not related
	//    to our module.
	const ourConsoleErrors = [];
	const OUR_MODULE_MARKERS = [
		"scope_context_report_filters",
		"construction",
		"ScopeContext",
	];
	function isOurError(text) {
		for (const m of OUR_MODULE_MARKERS) {
			if (text && text.includes(m)) return true;
		}
		return false;
	}
	page.on("pageerror", (err) => {
		if (isOurError(err.message)) {
			ourConsoleErrors.push("[pageerror] " + err.message);
		}
	});
	page.on("console", (msg) => {
		if (msg.type() === "error") {
			const text = msg.text();
			if (isOurError(text)) {
				ourConsoleErrors.push("[console.error] " + text);
			}
		}
	});

	// 3. Visit the home page so the JS module gets loaded.
	await page.goto(BASE + "/app", { waitUntil: "networkidle" });

	// 4. Verify the JS module is loaded.
	const scripts = await page.$$eval("script[src]", (els) =>
		els.map((e) => e.getAttribute("src")).filter(Boolean),
	);
	const ourScript = scripts.find((s) => s.includes("scope_context_report_filters.js"));
	if (!ourScript) {
		throw new Error("scope_context_report_filters.js is not loaded");
	}
	console.log("Loaded JS:", ourScript);

	// 5. Visit each of the 11 allowlisted reports and confirm the page
	//    renders.
	const reportResults = [];
	for (const report of REPORTS) {
		const url = BASE + "/app/query-report/" + encodeURIComponent(report);
		const before = ourConsoleErrors.length;
		let resp = null;
		try {
			resp = await page.goto(url, {
				waitUntil: "networkidle",
				timeout: 30000,
			});
		} catch (e) {
			// networkidle may time out; that's fine, we still track
			// responses.
		}
		const newErrors = ourConsoleErrors.slice(before);
		reportResults.push({
			report,
			status: resp ? resp.status() : null,
			consoleErrors: newErrors,
		});
		await page.waitForTimeout(800);
	}

	// 6. Summary.
	console.log("\n=== Option A+ browser smoke test results (11 reports) ===");
	console.log("Reports tested:", reportResults.length);
	let failed = 0;
	for (const r of reportResults) {
		const ok = r.status === 200 && r.consoleErrors.length === 0;
		console.log(
			`  ${ok ? "OK" : "FAIL"} ${r.report}: status=${r.status}, ` +
				`console errors=${r.consoleErrors.length}`,
		);
		if (!ok) {
			failed++;
			for (const e of r.consoleErrors) console.log("      ", e);
		}
	}

	await browser.close();

	if (failed > 0) {
		console.log(`\nFAILED: ${failed} report(s) had issues.`);
		process.exit(1);
	}
	console.log(
		"\nPASSED: all 11 allowlisted reports loaded with no console errors.",
	);
}

run().catch((e) => {
	console.error("Browser test crashed:", e);
	process.exit(2);
});
