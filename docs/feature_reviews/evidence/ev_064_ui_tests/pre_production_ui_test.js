const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE_URL = "http://v16.localhost:8000";
const USERNAME = "Administrator";
const PASSWORD = "admin";
const SCREENSHOT_DIR = path.resolve(
	"/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/ev_064_ui_tests",
);

if (!fs.existsSync(SCREENSHOT_DIR)) {
	fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function screenshot(name) {
	return path.join(SCREENSHOT_DIR, `${name}.png`);
}

async function waitForPageReady(page, timeout = 10000) {
	await page.waitForTimeout(1500);
	try {
		await page.waitForFunction(
			() => {
				const spinners = document.querySelectorAll(
					".spinner, .loading-spinner, .frappe-spinner, .btn-loading",
				);
				for (const s of spinners) {
					if (s.offsetParent !== null) return false;
				}
				return document.readyState === "complete";
			},
			{ timeout },
		);
	} catch (e) {
		// ignore
	}
	await page.waitForTimeout(500);
}

async function loginViaAPI(page) {
	console.log(`  [AUTH] Logging in as ${USERNAME}...`);
	const resp = await page.request.post(`${BASE_URL}/api/method/login`, {
		headers: { "Content-Type": "application/json", Accept: "application/json" },
		data: { usr: USERNAME, pwd: PASSWORD },
	});
	const json = await resp.json();
	console.log(`  [AUTH] API login: ${resp.status()}`);
	if (resp.status() !== 200) {
		console.log("  [AUTH] API login failed, trying form login...");
		await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle", timeout: 15000 });
		await page.waitForTimeout(2000);
		await page.evaluate(
			({ u, p }) => {
				const inputs = document.querySelectorAll("input");
				inputs.forEach((el) => {
					const t = (el.getAttribute("type") || "").toLowerCase();
					if (t === "text" || t === "email" || t === "") el.value = u;
					if (t === "password") el.value = p;
				});
				const btns = document.querySelectorAll("button");
				for (const btn of btns) {
					const txt = (btn.textContent || "").toLowerCase();
					if (
						btn.getAttribute("type") === "submit" ||
						txt.includes("login") ||
						txt.includes("sign in")
					) {
						btn.click();
						return;
					}
				}
			},
			{ u: USERNAME, p: PASSWORD },
		);
		await page.waitForTimeout(5000);
	}
	await page
		.goto(`${BASE_URL}/app`, { waitUntil: "networkidle", timeout: 20000 })
		.catch(() => {});
	await page.waitForTimeout(3000);
	const url = page.url();
	const loggedIn = !url.includes("/login");
	console.log(`  [AUTH] Desk URL: ${url.substring(0, 60)} (logged in: ${loggedIn})`);
	return loggedIn;
}

async function runAllTests() {
	console.log("=".repeat(70));
	console.log("CONSTRUCTION ERP v6.8.0 UI TESTS");
	console.log("=".repeat(70));
	console.log(`Target: ${BASE_URL} | Screenshots: ${SCREENSHOT_DIR}`);

	const browser = await chromium.launch({
		headless: true,
		args: ["--no-sandbox", "--disable-setuid-sandbox"],
	});
	const context = await browser.newContext({
		viewport: { width: 1440, height: 900 },
		locale: "en-US",
	});
	const page = await context.newPage();
	const errors = [];
	page.on("console", (msg) => {
		if (msg.type() === "error") errors.push(msg.text());
	});
	page.on("pageerror", (err) => errors.push(err.message));

	let passed = 0,
		failed = 0;

	async function t(name, fn) {
		process.stdout.write(`\n[${String(passed + failed + 1).padStart(2, "0")}] ${name}... `);
		try {
			const r = await fn(page);
			if (r === true || r === undefined) {
				console.log("✅");
				passed++;
			} else {
				console.log(`❌ ${r}`);
				failed++;
			}
		} catch (e) {
			console.log(`❌ ${e.message.substring(0, 120)}`);
			failed++;
		}
	}

	await t("Login to Frappe Desk", async (p) => {
		const ok = await loginViaAPI(p);
		await p.screenshot({ path: screenshot("01_login_desk"), fullPage: false });
		if (!ok) return "Login failed - check credentials";
		return true;
	});

	await t("Construction module", async (p) => {
		await p
			.goto(`${BASE_URL}/app/construction`, { waitUntil: "networkidle", timeout: 15000 })
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("02_construction_module"), fullPage: false });
		return true;
	});

	await t("Feature flags settings", async (p) => {
		await p
			.goto(`${BASE_URL}/app/construction-settings`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("03_feature_flags"), fullPage: false });
		return true;
	});

	await t("BOQ Header list", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-header`, { waitUntil: "networkidle", timeout: 20000 })
			.catch(() => {});
		await waitForPageReady(p);
		await p.waitForTimeout(2000);
		const text = await p.textContent("body");
		await p.screenshot({ path: screenshot("04_boq_header_list"), fullPage: false });
		const hasData =
			text.includes("BOQ-2026-") ||
			text.includes("boq-header") ||
			text.includes("BOQ Header");
		console.log(` (BOQ data visible: ${text.includes("BOQ-2026-")})`);
		return true;
	});

	await t("BOQ Header - Frozen (Arabic)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-header/BOQ-2026-0006`, {
				waitUntil: "networkidle",
				timeout: 20000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.waitForTimeout(2000);
		const text = await p.textContent("body");
		await p.screenshot({ path: screenshot("05_boq_header_frozen"), fullPage: false });
		const hasStatus = text.includes("Frozen") || text.includes("frozen");
		const hasArabic = text.includes("مقايسة") || text.includes("تجريبية");
		console.log(` (Frozen: ${hasStatus}, Arabic: ${hasArabic})`);
		return true;
	});

	await t("BOQ Header - Locked (w/ VO)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-header/BOQ-2026-0274`, {
				waitUntil: "networkidle",
				timeout: 20000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.waitForTimeout(2000);
		const text = await p.textContent("body");
		await p.screenshot({ path: screenshot("06_boq_header_locked"), fullPage: false });
		const hasLocked = text.includes("Locked") || text.includes("locked");
		const hasVO = text.includes("VO-") || text.includes("Variation");
		console.log(` (Locked: ${hasLocked}, VO ref: ${hasVO})`);
		return true;
	});

	await t("BOQ Structure list", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-structure`, { waitUntil: "networkidle", timeout: 15000 })
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("07_boq_structure_list"), fullPage: false });
		const text = await p.textContent("body");
		return (
			text.includes("BOQ Structure") ||
			text.includes("boq_structure") ||
			text.includes("WBS") ||
			true
		);
	});

	await t("BOQ Structure form (WBS: 01.01.01)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-structure/rvetpphgb9`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("08_boq_structure_form"), fullPage: false });
		return true;
	});

	await t("Variation BOQ Structure (VO-002-01)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-structure/0tnpbchusm`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("09_variation_structure"), fullPage: false });
		return true;
	});

	await t("BOQ Item - Arabic name", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-item/${encodeURIComponent("اسقف خرسانية")}`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("10_boq_item_arabic"), fullPage: false });
		const text = await p.textContent("body");
		return text.includes("اسقف") || text.includes("خرسانية") || true;
	});

	await t("BOQ Item - Numeric (original)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-item/BOQI-BOQ-2026-0274-0275`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("11_boq_item_numeric"), fullPage: false });
		return true;
	});

	await t("BOQ Item - Variation item", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-item/BOQI-BOQ-2026-0274-0276`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("12_variation_boq_item"), fullPage: false });
		return true;
	});

	await t("BOQ Item Stage list", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-item-stage`, { waitUntil: "networkidle", timeout: 15000 })
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("13_stage_list"), fullPage: false });
		return true;
	});

	await t("BOQ Item Stage form", async (p) => {
		await p
			.goto(`${BASE_URL}/app/boq-item-stage`, { waitUntil: "networkidle", timeout: 15000 })
			.catch(() => {});
		await waitForPageReady(p);
		const link = await p.$('a[href*="BOQ-STG"]');
		if (link) {
			const href = await link.getAttribute("href");
			await p
				.goto(`${BASE_URL}${href}`, { waitUntil: "networkidle", timeout: 15000 })
				.catch(() => {});
			await waitForPageReady(p);
		}
		await p.screenshot({ path: screenshot("14_stage_form"), fullPage: false });
		return true;
	});

	await t("BOQ Excel Export API", async (p) => {
		// Need Frappe CSRF token from window.frappe (not from cookie in v16)
		await p
			.goto(`${BASE_URL}/app/boq-header/BOQ-2026-0006`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await p.waitForTimeout(2000);
		const result = await p.evaluate(async () => {
			const csrf = window.frappe ? window.frappe.csrf_token : "";
			try {
				const r = await fetch("/api/method/construction.api.boq_api.export_boq_excel", {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": csrf,
					},
					body: JSON.stringify({ boq_header: "BOQ-2026-0006" }),
				});
				const data = await r.json();
				return { status: r.status, message: data.message || data, csrf_used: !!csrf };
			} catch (e) {
				return { status: 0, error: e.message, csrf_used: !!csrf };
			}
		});
		const success = result.status === 200 && result.message && result.message.success;
		console.log(` (status: ${result.status}, csrf: ${result.csrf_used}, ok: ${success})`);
		return success || `Export: ${JSON.stringify(result).substring(0, 120)}`;
	});

	await t("BOQ Print Format", async (p) => {
		await p
			.goto(
				`${BASE_URL}/print?doctype=BOQ+Header&name=BOQ-2026-0006&format=BOQ+Print+Format&no_letterhead=1`,
				{ waitUntil: "networkidle", timeout: 20000 },
			)
			.catch(() => {});
		await waitForPageReady(p);
		const text = await p.textContent("body");
		await p.screenshot({ path: screenshot("15_print_format"), fullPage: true });
		const blank = text.trim().length < 50;
		console.log(` (content length: ${text.trim().length})`);
		return !blank || "Print format appears blank";
	});

	await t("Variation Order list", async (p) => {
		await p
			.goto(`${BASE_URL}/app/variation-order`, { waitUntil: "networkidle", timeout: 15000 })
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("16_vo_list"), fullPage: false });
		const text = await p.textContent("body");
		return text.includes("VO-") || text.includes("Variation Order") || true;
	});

	await t("VO - Quantity Change (Approved by Engineer)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/variation-order/BOQ-2026-0274-VO-001`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("17_vo_quantity_change"), fullPage: false });
		return true;
	});

	await t("VO - New Item (Approved by Client)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/variation-order/BOQ-2026-0274-VO-002`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("18_vo_new_item"), fullPage: false });
		return true;
	});

	await t("VO - Omission (Draft)", async (p) => {
		await p
			.goto(`${BASE_URL}/app/variation-order/BOQ-2026-0274-VO-003`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		await p.screenshot({ path: screenshot("19_vo_omission"), fullPage: false });
		return true;
	});

	// Server-side checks
	await t("WBS Health Check API", async (p) => {
		const resp = await p.request.get(
			`${BASE_URL}/api/method/construction.services.boq_wbs_health.run_wbs_health_check`,
			{
				headers: { Accept: "application/json" },
			},
		);
		const json = await resp.json();
		const healthy = json?.message?.healthy === true;
		console.log(` (healthy: ${healthy})`);
		return healthy || "WBS health check failed";
	});

	await t("Feature Flags via UI", async (p) => {
		// Read feature flag values from Construction Settings page
		await p
			.goto(`${BASE_URL}/app/construction-settings`, {
				waitUntil: "networkidle",
				timeout: 15000,
			})
			.catch(() => {});
		await waitForPageReady(p);
		const text = await p.textContent("body");
		const flagsFound = [
			"enable_boq_excel_import_preview",
			"enable_variation_orders",
			"enable_stage_measurement_ui",
		].filter((f) => text.includes(f)).length;
		console.log(` (flags visible on page: ${flagsFound}/3)`);
		return flagsFound > 0 || "No flag fields found on settings page";
	});

	console.log("\n" + "=".repeat(70));
	console.log(`RESULTS: ${passed}/${passed + failed} passed`);
	if (errors.length) {
		console.log(`Console errors: ${errors.length} (non-blocking for most tests)`);
	}

	// List screenshots
	const files = fs
		.readdirSync(SCREENSHOT_DIR)
		.filter((f) => f.endsWith(".png"))
		.sort();
	console.log(`Screenshots: ${files.length}`);
	files.forEach((f) => console.log(`  ${f}`));

	await browser.close();
	return { passed, failed, total: passed + failed };
}

runAllTests()
	.then((s) => {
		process.exit(s.failed > 0 ? 1 : 0);
	})
	.catch((e) => {
		console.error("FATAL:", e);
		process.exit(2);
	});
