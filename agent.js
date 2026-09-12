import Steel from "steel-sdk";
import { chromium } from "playwright";
import "dotenv/config";

const client = new Steel({
    steelAPIKey: process.env.STEEL_API_KEY
});

async function main() {
    const session = await client.sessions.create();

    console.log("Steel browser started!");
    console.log("Watch the browser here:");
    console.log(session.sessionViewerUrl);

    const browser = await chromium.connectOverCDP(
        session.websocketUrl
    );

    const page = browser.contexts()[0].pages()[0];

    await page.goto("https://example.com");

    console.log("Page title:", await page.title());

    await browser.close();
    await client.sessions.release(session.id);
}

main().catch(console.error);
