import os
import json
from urllib.parse import quote_plus

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from steel import Steel
from playwright.sync_api import sync_playwright


# =========================
# SETUP
# =========================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STEEL_API_KEY = os.getenv("STEEL_API_KEY")

if not GEMINI_API_KEY or not STEEL_API_KEY:
    raise RuntimeError(
        "Add GEMINI_API_KEY and STEEL_API_KEY to your .env file."
    )

client = genai.Client(api_key=GEMINI_API_KEY)
steel_client = Steel(steel_api_key=STEEL_API_KEY)

app = Flask(__name__)


# =========================
# JSON HELPER
# =========================

def clean_json(text):
    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    return json.loads(text)


# =========================
# GEMINI: UNDERSTAND REQUEST
# =========================

def understand_request(user_request, mode):

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are Kindly, a personal digital assistant.

The user has selected this mode:
{mode}

Read the user's request and extract the information that matters
for this specific type of task.

User request:
{user_request}

Do not invent information.

Return ONLY valid JSON in this exact format:

{{
    "request": "",
    "tasks": [],
    "location": "",
    "date": "",
    "time": "",
    "deadline": "",
    "preferences": [],
    "other_constraints": []
}}
"""
    )

    return clean_json(response.text)


# =========================
# GEMINI: DECIDE WHAT TO RESEARCH
# =========================

def create_research_plan(information, mode):

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are the research planner for Kindly.

Kindly has three different specialized agents:

1. APPOINTMENT AGENT
   Finds real businesses or organizations and information
   needed to help with an appointment.

2. GENERAL AGENT
   Handles messy everyday requests and figures out what
   needs to be researched before creating a plan.

3. CONNECTION AGENT
   Finds real activities, events, programs, classes,
   groups, or community opportunities.

The current agent is:
{mode}

USER INFORMATION:
{json.dumps(information, indent=2)}

Decide what information needs to be researched online.

Create up to 3 useful browser searches.

Searches should be specific and useful.
Do not make up facts.

Return ONLY valid JSON:

{{
    "research": [
        {{
            "purpose": "",
            "search_query": "",
            "information_needed": []
        }}
    ]
}}
"""
    )

    return clean_json(response.text)


# =========================
# STEEL: BROWSER RESEARCH
# =========================

def perform_browser_research(research_plan):

    all_research = []
    session_viewer_url = ""

    with sync_playwright() as p:

        session = steel_client.sessions.create()

        try:

            session_viewer_url = session.session_viewer_url

            print("Steel session created!")
            print("Session viewer:", session_viewer_url)

            browser = p.chromium.connect_over_cdp(
                f"{session.websocket_url}&apiKey={STEEL_API_KEY}"
            )

            for research_item in research_plan["research"]:

                purpose = research_item["purpose"]
                search_query = research_item["search_query"]

                print()
                print("Researching:", purpose)
                print("Search:", search_query)

                page = browser.contexts[0].new_page()

                search_url = (
                    "https://duckduckgo.com/?q="
                    + quote_plus(search_query)
                )

                page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                search_results = page.locator("body").inner_text()

                all_research.append({
                    "purpose": purpose,
                    "search_query": search_query,
                    "search_results": search_results[:12000]
                })

                page.close()

        finally:

            steel_client.sessions.release(session.id)

            print("Steel session released!")

    return all_research, session_viewer_url


# =========================
# APPOINTMENT AGENT
# =========================

def appointment_agent(user_request):

    information = understand_request(
        user_request,
        "APPOINTMENT AGENT"
    )

    research_plan = create_research_plan(
        information,
        "APPOINTMENT AGENT"
    )

    browser_research, session_viewer_url = perform_browser_research(
        research_plan
    )

    final_response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are Kindly's Appointment Agent.

The user wants help with an appointment.

USER REQUEST:
{user_request}

UNDERSTOOD REQUEST:
{json.dumps(information, indent=2)}

WEB RESEARCH:
{json.dumps(browser_research, indent=2)}

Your job is to identify the most useful real appointment options.

Only use information supported by the browser research.

Do NOT invent:
- businesses
- addresses
- hours
- appointment availability
- prices
- phone numbers
- travel times

If information is unknown, say that it is unknown.

Return ONLY valid JSON:

{{
    "summary": "",
    "options": [
        {{
            "name": "",
            "address": "",
            "hours": "",
            "availability": "",
            "details": ""
        }}
    ],
    "warnings": [],
    "next_steps": []
}}
"""
    )

    result = clean_json(final_response.text)

    return {
        "mode": "appointment",
        "understanding": information,
        "research": browser_research,
        "result": result,
        "session_viewer_url": session_viewer_url
    }


# =========================
# CONNECTION AGENT
# =========================

def connection_agent(user_request):

    information = understand_request(
        user_request,
        "CONNECTION AGENT"
    )

    research_plan = create_research_plan(
        information,
        "CONNECTION AGENT"
    )

    browser_research, session_viewer_url = perform_browser_research(
        research_plan
    )

    final_response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are Kindly's Connection Agent.

The user wants to find activities, events, programs,
groups, classes, or ways to connect with other people.

USER REQUEST:
{user_request}

UNDERSTOOD REQUEST:
{json.dumps(information, indent=2)}

WEB RESEARCH:
{json.dumps(browser_research, indent=2)}

Find the most relevant real opportunities.

Pay attention to:
- location
- date
- time
- activity type
- preferences
- accessibility information if mentioned

Do not invent information.

Only claim information supported by the research.

Return ONLY valid JSON:

{{
    "summary": "",
    "activities": [
        {{
            "name": "",
            "location": "",
            "date": "",
            "time": "",
            "details": ""
        }}
    ],
    "warnings": [],
    "next_steps": []
}}
"""
    )

    result = clean_json(final_response.text)

    return {
        "mode": "connection",
        "understanding": information,
        "research": browser_research,
        "result": result,
        "session_viewer_url": session_viewer_url
    }


# =========================
# GENERAL AGENT
# =========================

def general_agent(user_request):

    information = understand_request(
        user_request,
        "GENERAL AGENT"
    )

    research_plan = create_research_plan(
        information,
        "GENERAL AGENT"
    )

    browser_research, session_viewer_url = perform_browser_research(
        research_plan
    )

    final_response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are Kindly's General Personal Logistics Agent.

The user gave you a messy everyday request.

Your job is to turn it into a realistic plan.

USER REQUEST:
{user_request}

UNDERSTOOD INFORMATION:
{json.dumps(information, indent=2)}

WEB RESEARCH:
{json.dumps(browser_research, indent=2)}

Create the best realistic plan.

Consider:
- deadlines
- opening hours
- order of tasks
- location
- preferences
- avoiding unnecessary travel
- grouping tasks when possible
- reasonable buffer time

IMPORTANT:

Do not invent:
- travel times
- opening hours
- addresses
- availability
- prices
- other real-world facts

If something cannot be confidently determined,
say that it is unknown.

Respect hard constraints.

Return ONLY valid JSON:

{{
    "plan": [
        {{
            "order": 1,
            "time": "",
            "task": "",
            "location": "",
            "reason": ""
        }}
    ],
    "summary": "",
    "warnings": [],
    "why_this_plan": []
}}
"""
    )

    result = clean_json(final_response.text)

    return {
        "mode": "general",
        "understanding": information,
        "research": browser_research,
        "result": result,
        "session_viewer_url": session_viewer_url
    }


# =========================
# HOME PAGE
# =========================

@app.route("/")
def index():
    return render_template("index.html")


# =========================
# GENERAL REQUEST
# =========================

@app.route("/api/plan", methods=["POST"])
def api_plan():

    data = request.get_json(silent=True) or {}

    brain_dump = (
        data.get("prompt") or ""
    ).strip()

    if not brain_dump:

        return jsonify({
            "error": "Please describe what you need to get done."
        }), 400

    try:

        result = general_agent(brain_dump)

        return jsonify(result)

    except Exception as exc:

        print("GENERAL AGENT ERROR:", exc)

        return jsonify({
            "error": str(exc)
        }), 500


# =========================
# APPOINTMENT REQUEST
# =========================

@app.route("/book-appointment", methods=["POST"])
def book_appointment():

    data = request.get_json(silent=True) or {}

    appointment_request = (
        data.get("request") or ""
    ).strip()

    if not appointment_request:

        return jsonify({
            "error": "Please describe the appointment you need."
        }), 400

    try:

        result = appointment_agent(
            appointment_request
        )

        return jsonify(result)

    except Exception as exc:

        print("APPOINTMENT AGENT ERROR:", exc)

        return jsonify({
            "error": str(exc)
        }), 500


# =========================
# CONNECTION REQUEST
# =========================

@app.route("/api/connect", methods=["POST"])
def api_connect():

    data = request.get_json(silent=True) or {}

    connection_request = (
        data.get("prompt") or ""
    ).strip()

    if not connection_request:

        return jsonify({
            "error": "Please describe what activity you are looking for."
        }), 400

    try:

        result = connection_agent(
            connection_request
        )

        return jsonify(result)

    except Exception as exc:

        print("CONNECTION AGENT ERROR:", exc)

        return jsonify({
            "error": str(exc)
        }), 500


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )
