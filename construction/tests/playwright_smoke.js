const { launchChromium } = require("./playwright_browser");

async function main() {
	const browser = await launchChromium();
	try {
		const page = await browser.newPage();
		await page.goto("data:text/html,<title>playwright-smoke</title><h1>Playwright ready</h1>");
		const title = await page.title();
		console.log(`Playwright browser ready: ${title}`);
	} finally {
		await browser.close();
	}
}

main().catch((error) => {
	console.error(error);
	process.exit(1);
});
