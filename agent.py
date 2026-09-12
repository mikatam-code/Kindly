import os
from dotenv import load_dotenv
from steel import Steel
from playwright.sync_api import sync_playwright

load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")

user_request = "I need to buy groceries and get a haircut."
tasks = ["buy groceries", "get a haircut"]
print("User request:", user_request)
print("Tasks:")
for task in tasks:
    print("-", task)

client = Steel(steel_api_key=STEEL_API_KEY)

with sync_playwright() as p:
    session = client.sessions.create()

    try:
        print("Steel session created!")
        print("Session viewer:", session.session_viewer_url)

        browser = p.chromium.connect_over_cdp(
            f"{session.websocket_url}&apiKey={STEEL_API_KEY}"
        )

        page = browser.contexts[0].new_page()

        page.goto("https://www.google.com")

        print("Opened Google!")

        # Research the grocery task
        page.goto("https://www.metro.ca")

        print("Opened Metro!")
        print(page.title())

        text = page.locator("body").inner_text()
        print("Grocery information found:")
        print(text[:1000])

    finally:
        client.sessions.release(session.id)
        print("Steel session released!")
