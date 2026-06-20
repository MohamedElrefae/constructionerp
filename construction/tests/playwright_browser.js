const { chromium } = require("playwright");

function browserLaunchOptions() {
	return {
		headless: process.env.PLAYWRIGHT_HEADFUL !== "1",
		executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined,
	};
}

async function launchChromium() {
	return chromium.launch(browserLaunchOptions());
}

module.exports = {
	browserLaunchOptions,
	launchChromium,
};
