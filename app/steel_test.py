import os

from dotenv import load_dotenv
from steel import Steel
from playwright.sync_api import sync_playwright


load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")

WEBSITE = "https://harbourfrontdental.com/dental-checkup-cleaning-appointment-toronto/"


def main():

    client = Steel(
        steel_api_key=STEEL_API_KEY
    )

    session = client.sessions.create()

    print("Watch the browser here:")
    print(session.session_viewer_url)

    playwright = sync_playwright().start()

    try:
        browser = playwright.chromium.connect_over_cdp(
            f"{session.websocket_url}&apiKey={STEEL_API_KEY}"
        )

        page = browser.contexts[0].pages[0]

        # Open Harbourfront Dental
        print("Opening Harbourfront Dental...")
        page.goto(WEBSITE)

        print("Website opened!")
        print("Title:", page.title())

        # Find the appointment button
        print("Looking for Book Appointment...")

        button = page.get_by_text(
            "Book Appointment",
            exact=False
        ).first

        # Click it
        button.click()

        print("Clicked Book Appointment! ✅")

        # Give the page a moment to load
        page.wait_for_timeout(3000)

        print("Looking for Hygiene Appointment...")

        # Second click: Hygiene Appointment
        hygiene_button = page.get_by_text(
            "Hygiene Appointment",
            exact=False
        ).first

        hygiene_button.click()

        print("Clicked Hygiene Appointment! ✅")

        page.wait_for_timeout(3000)

        print("Current page:")
        print(page.url)

        print()
        print("Press Enter to close...")
        input()

    finally:
        playwright.stop()
        client.sessions.release(session.id)


if __name__ == "__main__":
    main()
