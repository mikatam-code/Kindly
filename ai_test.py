import os
import json
from dotenv import load_dotenv
from google import genai
from steel import Steel
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STEEL_API_KEY = os.getenv("STEEL_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
steel_client = Steel(steel_api_key=STEEL_API_KEY)


# ---------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------

def clean_json(text):

    text = text.replace("```json", "")
    text = text.replace("```", "")

    return json.loads(text)


# ---------------------------------------------------------
# GET USER'S REQUEST
# ---------------------------------------------------------

print()
print("========================================")
print("        PERSONAL DAY PLANNER")
print("========================================")
print()

print("Tell me what you need to get done.")
print("Include things like your starting location,")
print("time limits, and preferences if they matter.")
print()

brain_dump = input("You: ")

print()
print("Thinking...")


# ---------------------------------------------------------
# STEP 1: UNDERSTAND THE USER
# ---------------------------------------------------------

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=f"""
You are a personal logistics planning assistant.

Read the user's messy request and extract the important information.

Identify:
- every task the user wants to complete
- where the user starts, if provided
- when the user becomes available
- when they need to be home or finish
- deadlines
- preferences
- restrictions
- anything else that could affect the plan

Do not invent information.

If something is not provided, use an empty string or empty list.

Return ONLY valid JSON in this exact format:

{{
    "tasks": [],
    "starting_location": "",
    "available_from": "",
    "must_be_finished_by": "",
    "preferences": [],
    "other_constraints": []
}}

User request:

{brain_dump}
"""
)


if response.text is None:
    print("Gemini did not return a response.")
    exit()


information = clean_json(response.text)


print()
print("I understood:")

for task in information["tasks"]:
    print("-", task)

print()

if information["starting_location"] != "":
    print("Starting from:", information["starting_location"])

if information["available_from"] != "":
    print("Available from:", information["available_from"])

if information["must_be_finished_by"] != "":
    print("Must be finished by:", information["must_be_finished_by"])

if len(information["preferences"]) > 0:
    print("Preferences:")

    for preference in information["preferences"]:
        print("-", preference)


# ---------------------------------------------------------
# STEP 2: FIGURE OUT WHAT NEEDS RESEARCH
# ---------------------------------------------------------

print()
print("Figuring out what I need to research...")


research_response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=f"""
You are a personal logistics planning assistant.

The user wants to complete these tasks:

Tasks:
{information["tasks"]}

Starting location:
{information["starting_location"]}

Available from:
{information["available_from"]}

Must be finished by:
{information["must_be_finished_by"]}

Preferences:
{information["preferences"]}

Other constraints:
{information["other_constraints"]}

For EACH task, decide what information needs to be researched
on the internet before creating a realistic plan.

Examples of useful research:
- nearby businesses
- physical locations
- opening and closing hours
- whether a business actually exists in the requested city
- appointment availability
- drop-off locations
- services offered
- estimated time needed
- other information needed to determine whether an option is usable

Also create a search query that a browser could use to find this information.

Do not assume that every task requires the same type of research.

Return ONLY valid JSON in this exact format:

{{
    "research": [
        {{
            "task": "",
            "search_query": "",
            "information_needed": []
        }}
    ]
}}
"""
)


if research_response.text is None:
    print("Gemini did not return research information.")
    exit()


research_information = clean_json(research_response.text)


print()
print("Research plan:")

for research_item in research_information["research"]:

    print()
    print("Task:", research_item["task"])
    print("Search:", research_item["search_query"])


# ---------------------------------------------------------
# STEP 3: START STEEL
# ---------------------------------------------------------

print()
print("Starting browser research...")


with sync_playwright() as p:

    session = steel_client.sessions.create()

    try:

        print()
        print("Steel session created!")
        print("Session viewer:", session.session_viewer_url)


        browser = p.chromium.connect_over_cdp(
            f"{session.websocket_url}&apiKey={STEEL_API_KEY}"
        )


        # This will hold the information we find
        all_research = []


        # -------------------------------------------------
        # STEP 4: RESEARCH EACH TASK
        # -------------------------------------------------

        for research_item in research_information["research"]:

            task = research_item["task"]
            search_query = research_item["search_query"]


            print()
            print("========================================")
            print("Researching:", task)
            print("========================================")


            # ---------------------------------------------
            # SEARCH THE WEB
            # ---------------------------------------------

            page = browser.contexts[0].new_page()


            search_url = (
                "https://duckduckgo.com/?q="
                + search_query.replace(" ", "+")
            )


            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=60000
            )


            search_results = page.locator("body").inner_text()


            print()
            print("Browser found:")
            print(search_results[:3000])


            # ---------------------------------------------
            # HAVE GEMINI UNDERSTAND THE SEARCH RESULTS
            # ---------------------------------------------

            analysis_response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=f"""
You are helping plan a user's day.

The user's task is:

{task}

The user's starting location is:

{information["starting_location"]}

The user needs to finish by:

{information["must_be_finished_by"]}

The user's preferences are:

{information["preferences"]}

The browser searched for:

{search_query}

Here are the browser search results:

{search_results}

Analyze the search results and identify useful real-world options
for completing this task.

IMPORTANT:
- Do not invent businesses, addresses, hours, prices, availability,
  travel times, or other facts.
- Only claim something when the search results provide evidence.
- If information is missing, say that it is unknown.
- Keep multiple promising options when possible.
- Reject obviously irrelevant results.

Return ONLY valid JSON in this exact format:

{{
    "task": "",
    "options": [
        {{
            "name": "",
            "address": "",
            "hours": "",
            "useful_information": "",
            "missing_information": ""
        }}
    ]
}}
"""
            )


            if analysis_response.text is None:

                print("Gemini did not return analysis for this task.")

                continue


            analysis_information = clean_json(
                analysis_response.text
            )


            # ---------------------------------------------
            # SAVE RESEARCH
            # ---------------------------------------------

            all_research.append(analysis_information)


            print()
            print("Useful options found:")


            for option in analysis_information["options"]:

                print()
                print("Name:", option["name"])
                print("Address:", option["address"])
                print("Hours:", option["hours"])
                print(
                    "Information:",
                    option["useful_information"]
                )


        # -------------------------------------------------
        # STEP 5: GIVE ALL RESEARCH TO GEMINI
        # -------------------------------------------------

        print()
        print("========================================")
        print("Building your plan...")
        print("========================================")


        final_response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=f"""
You are the final decision-maker for a personal logistics assistant.

Create the best realistic plan for the user's day.

USER'S ORIGINAL REQUEST:

{brain_dump}


STRUCTURED INFORMATION:

Tasks:
{information["tasks"]}

Starting location:
{information["starting_location"]}

Available from:
{information["available_from"]}

Must be finished by:
{information["must_be_finished_by"]}

Preferences:
{information["preferences"]}

Other constraints:
{information["other_constraints"]}


RESEARCH COLLECTED FROM THE INTERNET:

{json.dumps(all_research, indent=4)}


Your job is to combine the research and create a realistic itinerary.

Consider:
- opening hours
- the user's time constraints
- the user's preferences
- the order of the stops
- avoiding unnecessary travel
- grouping nearby tasks when possible
- whether a task has a suitable confirmed location
- leaving reasonable buffer time
- whether the plan is actually possible

IMPORTANT:
- Do NOT invent travel times.
- Do NOT invent opening hours.
- Do NOT pretend an option is confirmed if the research does not support it.
- If exact travel time is unavailable, clearly say so.
- If a task cannot confidently be planned, say that.
- It is better to leave something unresolved than to hallucinate an answer.

Return ONLY valid JSON in this format:

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


        if final_response.text is None:

            print("Gemini did not return a final plan.")

        else:

            final_information = clean_json(
                final_response.text
            )


            # -------------------------------------------------
            # STEP 6: SHOW THE PLAN
            # -------------------------------------------------

            print()
            print()
            print("╔══════════════════════════════════════╗")
            print("║          YOUR PLAN                  ║")
            print("╚══════════════════════════════════════╝")


            for step in final_information["plan"]:

                print()
                print(
                    str(step["order"])
                    + ". "
                    + step["time"]
                )

                print(
                    "   Task:",
                    step["task"]
                )

                print(
                    "   Location:",
                    step["location"]
                )

                print(
                    "   Why:",
                    step["reason"]
                )


            print()
            print("----------------------------------------")
            print("SUMMARY")
            print("----------------------------------------")

            print(
                final_information["summary"]
            )


            if len(final_information["why_this_plan"]) > 0:

                print()
                print("----------------------------------------")
                print("WHY THIS PLAN")
                print("----------------------------------------")

                for reason in final_information["why_this_plan"]:

                    print("-", reason)


            if len(final_information["warnings"]) > 0:

                print()
                print("----------------------------------------")
                print("WARNINGS")
                print("----------------------------------------")

                for warning in final_information["warnings"]:

                    print("-", warning)


    finally:

        steel_client.sessions.release(session.id)

        print()
        print("Steel session released!")
