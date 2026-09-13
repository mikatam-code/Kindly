import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from playwright.sync_api import sync_playwright
from steel import Steel

# IMPORTANT:
# If your file is called ai.py, use:
from ai_test import run_web_agent
# If your file is actually called ai_test.py, use:
# from ai_test import run_web_agent


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STEEL_API_KEY = os.getenv("STEEL_API_KEY")

if not GEMINI_API_KEY or not STEEL_API_KEY:
    raise RuntimeError(
        "Set GEMINI_API_KEY and STEEL_API_KEY in .env"
    )

gemini = genai.Client(
    api_key=GEMINI_API_KEY
)

steel_client = Steel(
    steel_api_key=STEEL_API_KEY
)

app = FastAPI(title="Kindly")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================================================
# JSON CLEANING
# =========================================================

def clean_json(text: str):

    text = (
        text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    return json.loads(text)


# =========================================================
# DUCKDUCKGO SEARCH THROUGH STEEL
# =========================================================

def steel_search(query: str) -> str:

    """
    Live web research through a Steel browser session
    using DuckDuckGo.

    Speed improvements:
    - shorter browser/navigation timeouts
    - no unnecessary 1.5 second sleep after the page loads
    - only waits a short moment if the results need to settle
    """

    with sync_playwright() as p:

        session = steel_client.sessions.create(
            timeout=90000
        )

        print()
        print("========================================")
        print("        STEEL BROWSER SESSION")
        print("========================================")
        print(f"Session ID: {session.id}")

        browser = None

        try:

            browser = p.chromium.connect_over_cdp(
                f"{session.websocket_url}&apiKey={STEEL_API_KEY}"
            )

            context = browser.contexts[0]

            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()

            url = (
                "https://html.duckduckgo.com/html/?q="
                + quote_plus(query)
            )

            print(f"Steel is searching for: {query}")

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # DuckDuckGo HTML results are normally available immediately
            # after DOMContentLoaded. A tiny pause is enough for late text.
            page.wait_for_timeout(250)

            return page.locator(
                "body"
            ).inner_text(timeout=5000)[:16000]

        except Exception as e:

            print("STEEL SEARCH ERROR:")
            print(repr(e))
            return ""

        finally:

            # Close the Playwright connection AND release the cloud
            # browser. The old code left sessions alive until timeout,
            # which could make later searches slower and waste resources.
            try:
                if browser:
                    browser.close()
            except Exception:
                pass

            try:
                steel_client.sessions.release(
                    session.id
                )
            except Exception:
                pass

            print(
                f"Steel session released: {session.id}"
            )


# =========================================================
# GEMINI JSON AI
# =========================================================

def ask(prompt: str):

    response = gemini.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    if not response.text:

        raise ValueError(
            "Gemini returned an empty response."
        )

    return clean_json(response.text)


# =========================================================
# AI WEB AGENT
# =========================================================

def ai_location_research(
    task: str,
    user_location: str
) -> str:

    request = f"""
Find useful real-world places for this student's task.

Task:
{task}

Starting location:
{user_location}

The student wants something reasonably close to:

{user_location}

Research the type of place/service they need.

Prioritize:

- places near the starting location
- relevant businesses
- realistic student travel distance
- useful services
- addresses or areas
- hours when available
- ratings/reputation when available
- price/value when available

IMPORTANT:

The user's location is specifically:

{user_location}

Do not silently replace it with a completely different city.

If there are no good options directly around the exact
location, think about the nearest reasonable broader area.

Return up to 5 useful candidates.

Do not invent businesses.

If you are unsure whether a place exists,
clearly say that the information needs verification.

Task:
{task}

Location:
{user_location}
"""

    try:

        result = run_web_agent(request)

        if not result:

            return ""

        return result

    except Exception as e:

        print()
        print("AI LOCATION RESEARCH ERROR:")
        print(repr(e))
        print()

        return ""


# =========================================================
# BROADER LOCATION
# =========================================================

def get_broader_location(
    user_location: str,
    task: str,
    ai_research: str = ""
) -> str:

    broader = ask(f"""
The user entered this location:

{user_location}

They need to:

{task}

The exact-location search did not find a suitable
real business.

An AI research assistant also looked for possibilities:

{ai_research}

Suggest ONE slightly broader geographic area that is
still reasonably close to the user's original location.

IMPORTANT:

- Stay in the same city whenever possible.
- Do NOT jump to another city.
- Do NOT suggest an entire province/state.
- Do NOT suggest a huge geographic region.
- The broader area should be practical for a student.
- Only broaden the search by ONE reasonable level.

Examples:

"UTSG campus" -> "downtown Toronto"

"York University" -> "North York"

"Scarborough Town Centre" -> "Scarborough"

"Yorkdale Shopping Centre" -> "North York"

If the original location is already broad,
return the same location.

Return ONLY JSON:

{{
  "broader_location": ""
}}
""")

    return broader.get(
        "broader_location",
        ""
    ).strip()


# =========================================================
# VERIFY LOCAL RESULTS
# =========================================================

def analyze_local_results(
    task: str,
    search_location: str,
    search_query: str,
    results: str,
    original_location: str,
    ai_research: str = "",
    fallback_used: bool = False
):

    return ask(f"""
You are Kindly's local business verification assistant.

The student needs:

Task:
{task}

Original user location:

{original_location}

Current search location:

{search_location}

Search query:

{search_query}

AI research:

{ai_research}

LIVE DUCKDUCKGO RESULTS:

{results}

IMPORTANT RULES:

1. Only use businesses that actually appear in
   the live search results.

2. Never invent a business.

3. Never invent an address.

4. Never invent ratings.

5. Never invent hours.

6. Never invent prices.

7. Return up to 3 strong options.

8. If only 1 or 2 are supported, return only those.

9. If no businesses are supported, return an empty array.

10. Only include a source URL if it actually appears.

Return ONLY JSON:

{{
  "task": "{task}",
  "search_location": "{search_location}",
  "fallback_used": {str(fallback_used).lower()},
  "options": [
    {{
      "rank": 1,
      "name": "",
      "address": "",
      "hours": "",
      "rating": "",
      "distance": "",
      "price": "",
      "useful_information": "",
      "why_it_fits": "",
      "source_url": ""
    }}
  ],
  "missing_information": ""
}}
""")


# =========================================================
# FAST LOCATION RESEARCH WORKER
# =========================================================

def research_location_item(
    item: dict,
    user_location: str
) -> dict | None:

    """
    Research one location task quickly.

    The live Steel search is done first because it is the source of
    truth. The extra AI research is only used when the exact search
    fails, avoiding an unnecessary Gemini call for successful searches.
    """

    task = item.get("task", "").strip()
    search_query_base = item.get("search_query", "").strip()

    if not task or not search_query_base:
        return None

    exact_query = (
        f"{search_query_base} "
        f"near {user_location}"
    )

    print()
    print("========================================")
    print("       KINDLY LOCATION RESEARCH")
    print("========================================")
    print(f"Task: {task}")
    print(f"Search: {exact_query}")
    print()

    # Search the live web immediately.
    exact_results = steel_search(
        exact_query
    )

    # Verify only what the live search actually found.
    exact_analyzed = analyze_local_results(
        task=task,
        search_location=user_location,
        search_query=exact_query,
        results=exact_results,
        original_location=user_location,
        ai_research="",
        fallback_used=False
    )

    if exact_analyzed.get("options"):
        return exact_analyzed

    # ---------------------------------------------------------
    # ONLY DO EXTRA AI RESEARCH IF EXACT SEARCH FAILED
    # ---------------------------------------------------------

    print()
    print("NO EXACT LOCATION RESULTS.")
    print("Using broader-location research...")

    ai_research = ai_location_research(
        task=task,
        user_location=user_location
    )

    broader_location = get_broader_location(
        user_location=user_location,
        task=task,
        ai_research=ai_research
    )

    if (
        not broader_location
        or broader_location.lower() == user_location.lower()
    ):
        return {
            "task": task,
            "search_location": user_location,
            "fallback_used": False,
            "options": [],
            "missing_information": (
                "No suitable location was found."
            )
        }

    broader_query = (
        f"{search_query_base} "
        f"near {broader_location}"
    )

    broader_results = steel_search(
        broader_query
    )

    broader_analyzed = analyze_local_results(
        task=task,
        search_location=broader_location,
        search_query=broader_query,
        results=broader_results,
        original_location=user_location,
        ai_research=ai_research,
        fallback_used=True
    )

    if broader_analyzed.get("options"):
        return broader_analyzed

    return {
        "task": task,
        "search_location": user_location,
        "fallback_used": False,
        "options": [],
        "missing_information": (
            "No suitable location was found."
        )
    }


# =========================================================
# SMART TIME PARSER
# =========================================================

def parse_time(time_string: str):

    """
    Convert a time such as:

    9:00 AM
    14:30
    2 PM

    into a datetime object.

    Returns None if the time cannot be understood.
    """

    if not time_string:

        return None

    formats = [
        "%I:%M %p",
        "%I %p",
        "%H:%M",
        "%H"
    ]

    cleaned = (
        time_string
        .strip()
        .upper()
    )

    for fmt in formats:

        try:

            return datetime.strptime(
                cleaned,
                fmt
            )

        except ValueError:

            pass

    return None


# =========================================================
# FORMAT TIME
# =========================================================

def format_time(dt):

    return dt.strftime("%-I:%M %p")


def build_schedule(tasks, available_from, must_finish_by):
    start = parse_time(available_from)
    end = parse_time(must_finish_by)

    if start is None:
        start = datetime.strptime("9:00 AM", "%I:%M %p")

    if end is None:
        end = datetime.strptime("9:00 PM", "%I:%M %p")

    if end <= start:
        end += timedelta(days=1)

    fixed_tasks = []
    flexible_tasks = []

    for index, task in enumerate(tasks):
        task["_original_order"] = index

        if task.get("fixed_time", ""):
            fixed_tasks.append(task)
        else:
            flexible_tasks.append(task)

    fixed_events = []

    for task in fixed_tasks:
        fixed_start = parse_time(task.get("fixed_time", ""))

        if fixed_start is None:
            continue

        duration = int(task.get("duration_minutes", 30))
        fixed_end = fixed_start + timedelta(minutes=duration)

        fixed_events.append({
            "task": task.get("task", "Task"),
            "start_dt": fixed_start,
            "end_dt": fixed_end,
            "duration_minutes": duration,
            "status": "fixed",
            "original_order": task.get("_original_order", 0)
        })

    fixed_events.sort(key=lambda item: item["start_dt"])

    def is_lunch(task):
        name = task.get("task", "").lower()
        return "lunch" in name or "eat lunch" in name or "have lunch" in name

    def is_dinner(task):
        name = task.get("task", "").lower()
        return "dinner" in name or "eat dinner" in name or "have dinner" in name

    lunch_window_start = start.replace(hour=11, minute=30)
    lunch_window_end = start.replace(hour=13, minute=30)

    dinner_window_start = start.replace(hour=17, minute=30)
    dinner_window_end = start.replace(hour=19, minute=30)

    def find_slot(current_time, duration, preferred_start=None):
        candidate = current_time

        if preferred_start is not None and candidate < preferred_start:
            candidate = preferred_start

        while True:
            candidate_end = candidate + timedelta(minutes=duration)

            if candidate_end > end:
                return None

            conflict = None

            for event in fixed_events:
                if (
                    candidate < event["end_dt"]
                    and candidate_end > event["start_dt"]
                ):
                    conflict = event
                    break

            if conflict is None:
                return candidate

            candidate = conflict["end_dt"] + timedelta(minutes=10)

    schedule = []
    current_time = start

    for task in flexible_tasks:
        duration = int(task.get("duration_minutes", 30))
        preferred_start = None

        if is_lunch(task):
            preferred_start = lunch_window_start

        elif is_dinner(task):
            preferred_start = dinner_window_start

        task_start = find_slot(
            current_time,
            duration,
            preferred_start
        )

        if task_start is None:
            schedule.append({
                "task": task.get("task", "Task"),
                "time": "Could not fit",
                "start": "",
                "end": "",
                "duration_minutes": duration,
                "status": "needs_rescheduling",
                "original_order": task.get("_original_order", 0)
            })
            continue

        task_end = task_start + timedelta(minutes=duration)

        schedule.append({
            "task": task.get("task", "Task"),
            "time": f"{format_time(task_start)} - {format_time(task_end)}",
            "start": format_time(task_start),
            "end": format_time(task_end),
            "duration_minutes": duration,
            "status": "scheduled",
            "original_order": task.get("_original_order", 0)
        })

        current_time = task_end + timedelta(minutes=10)

    for event in fixed_events:
        schedule.append({
            "task": event["task"],
            "time": (
                f"{format_time(event['start_dt'])} - "
                f"{format_time(event['end_dt'])}"
            ),
            "start": format_time(event["start_dt"]),
            "end": format_time(event["end_dt"]),
            "duration_minutes": event["duration_minutes"],
            "status": "fixed",
            "original_order": event["original_order"]
        })

    def get_start_time(item):
        parsed = parse_time(item.get("start", ""))
        return parsed if parsed else datetime.max

    schedule.sort(key=get_start_time)

    for i in range(len(schedule) - 1):
        current = schedule[i]
        next_task = schedule[i + 1]

        current_end = parse_time(current.get("end", ""))
        next_start = parse_time(next_task.get("start", ""))

        if current_end and next_start and next_start < current_end:
            current["status"] = "overlap_needs_rescheduling"
            next_task["status"] = "overlap_needs_rescheduling"

    for item in schedule:
        item.pop("original_order", None)

    for task in tasks:
        task.pop("_original_order", None)

    return schedule
# =========================================================
# HOME
# =========================================================

@app.get("/")
def index():

    return FileResponse(
        "static/index.html"
    )


# =========================================================
# PLANNER
# =========================================================

@app.post("/api/plan")
def plan(payload: dict):

    brain_dump = payload.get(
        "request",
        ""
    ).strip()

    user_location = payload.get(
        "location",
        ""
    ).strip()

    if not brain_dump:

        return {
            "error": (
                "Tell me what you need to get done."
            )
        }

    if not user_location:

        return {
            "error": (
                "Please enter a location so Kindly "
                "can find nearby places."
            )
        }

    # =====================================================
    # STEP 1
    # UNDERSTAND THE REQUEST
    # =====================================================

    info = ask(f"""
You are a personal logistics planning assistant.

Extract the important information from this messy request.

Identify:

- tasks
- locations
- availability
- finish deadline
- preferences
- restrictions
- tasks that require finding a real-world location

IMPORTANT SCHEDULING RULES:

For EVERY task, estimate a realistic duration.

Also determine whether the task has a natural time of day.

MEAL TIMES:

If the user mentions lunch without a specific time,
assume lunch should happen around 12:00 PM.

If the user mentions dinner without a specific time,
assume dinner should happen around 6:00 PM.

Do NOT treat lunch or dinner as something that can be placed
randomly at any time of day.

Examples:

Studying for a calculus test:
120 minutes
No natural time of day.

Getting lunch:
45 minutes
Natural time of day: around noon.

Getting dinner:
45 minutes
Natural time of day: around 6:00 PM.

Grocery shopping:
45 minutes
No natural time of day unless the user specifies one.

Dentist appointment:
60 minutes
Fixed if the user gives a specific time.

Walking between nearby places:
15 minutes
Flexible.

If the user gives a specific time, ALWAYS treat that task
as fixed.

For example:

"I have class at 10"
→ fixed_time = "10:00 AM"

"I have math at 2"
→ fixed_time = "2:00 PM"

"I have a dentist appointment at 3"
→ fixed_time = "3:00 PM"

If the user does NOT give a specific time, leave
fixed_time empty.

IMPORTANT:
Do not create a location request for an existing class,
lecture, appointment, meeting, or work shift unless the user
explicitly asks to find its location.

Existing scheduled events already have a designated location.

Return ONLY JSON:

{{
  "tasks": [
    {{
      "task": "",
      "duration_minutes": 30,
      "fixed_time": "",
      "important": false,
      "requires_location": false
    }}
  ],
  "available_from": "",
  "must_be_finished_by": "",
  "preferences": [],
  "other_constraints": [],
  "location_needed_for_tasks": []
}}

User's chosen search location:

{user_location}

User request:

{brain_dump}
""")

    # =====================================================
    # STEP 2
    # DETERMINE WEB RESEARCH
    # =====================================================

    research_plan = ask(f"""
Decide what must be researched on the live internet.

Tasks:

{json.dumps(info.get("tasks", []), indent=2)}

User location:

{user_location}

Available from:

{info.get("available_from", "")}

Finish by:

{info.get("must_be_finished_by", "")}

Preferences:

{info.get("preferences", [])}

Constraints:

{info.get("other_constraints", [])}

Only create a research item when the user actually needs
Kindly to FIND a place or service.

DO NOT research the location of:
- an existing class
- an existing lecture
- an existing appointment
- an existing meeting
- an existing work shift
- any other event that the user already has scheduled

For example:

"I have math at 2"
→ NO web research.

"I have math at 2 and need somewhere to study afterward"
→ Research study locations only.

"I have math at 2 but I don't know where it is"
→ Research the math location because the user explicitly
asks for help finding it.

Return ONLY JSON:

{{
  "research": [
    {{
      "task": "",
      "search_query": "",
      "information_needed": [],
      "needs_top_3": false
    }}
  ]
}}
""")

    # =====================================================
    # STEP 3
    # LIVE WEB RESEARCH
    # =====================================================

    research_items = [
        item
        for item in research_plan.get("research", [])
        if item.get("task", "").strip()
        and item.get("search_query", "").strip()
    ]

    collected = []

    if research_items:

        # Different tasks are independent, so research them in
        # parallel instead of waiting for each task to finish.
        max_workers = min(4, len(research_items))

        with ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:

            futures = [
                executor.submit(
                    research_location_item,
                    item,
                    user_location
                )
                for item in research_items
            ]

            for future in futures:
                try:
                    result = future.result()

                    if result:
                        collected.append(result)

                except Exception as e:

                    print()
                    print("LOCATION RESEARCH ERROR:")
                    print(repr(e))
                    print()

    # =====================================================
    # STEP 4
    # PYTHON BUILDS THE ACTUAL TIMES
    # =====================================================

    schedule = build_schedule(
        tasks=info.get(
            "tasks",
            []
        ),
        available_from=info.get(
            "available_from",
            ""
        ),
        must_finish_by=info.get(
            "must_be_finished_by",
            ""
        )
    )

    # =====================================================
    # STEP 5
    # GEMINI ADDS LOCATIONS + EXPLANATIONS
    # =====================================================

    final = ask(f"""
You are Kindly's final planning assistant.

The Python scheduler has ALREADY calculated the times.

DO NOT change the times.

PYTHON SCHEDULE:

{json.dumps(schedule, indent=2)}

Original request:

{brain_dump}

User location:

{user_location}

Task information:

{json.dumps(info, indent=2)}

Live research:

{json.dumps(collected, indent=2)}

Your job is ONLY to attach the correct locations,
explanations, and research information to the schedule.

IMPORTANT:

1. Keep the exact times created by Python.

2. Do NOT move tasks.

3. Do NOT invent businesses.

4. Do NOT invent addresses.

5. Do NOT invent hours.

6. Do NOT invent ratings.

7. If multiple locations exist, include them as options.

8. Use the best researched option as the main location.

9. If no location was found, use:
   "No reliable location found"

10. Explain why the schedule makes sense.

Return ONLY JSON:

{{
  "plan": [
    {{
      "order": 1,
      "time": "",
      "task": "",
      "duration_minutes": 0,
      "location": "",
      "reason": "",
      "status": "",
      "location_options": [
        {{
          "rank": 1,
          "name": "",
          "address": "",
          "why_it_fits": ""
        }}
      ]
    }}
  ],
  "summary": "",
  "warnings": [],
  "why_this_plan": []
}}
""")

    # =====================================================
    # RETURN EVERYTHING
    # =====================================================

    return {
        "plan": final,
        "research": collected,
        "location_used": user_location,
        "calculated_schedule": schedule
    }


# =========================================================
# APPOINTMENTS
# =========================================================

@app.post("/api/appointments")
def appointments(payload: dict):

    what = payload.get(
        "what",
        ""
    ).strip()

    where = payload.get(
        "where",
        ""
    ).strip()

    when = payload.get(
        "when",
        ""
    ).strip()

    extras = payload.get(
        "extras",
        ""
    ).strip()

    if not what or not where or not when:

        return {
            "error": (
                "Please fill in what, where, and when."
            )
        }

    query = (
        f"{what} appointment "
        f"{where} {when} {extras}"
    ).strip()

    results = steel_search(
        query
    )

    options = ask(f"""
You are an appointment-finding assistant.

The student wants:

What:
{what}

Where:
{where}

When:
{when}

Extra preferences:
{extras}

A Steel-powered browser searched the live web for:

{query}

Search results:

{results}

Find strong real businesses.

IMPORTANT:

- Only use businesses actually found.
- Never invent businesses.
- Never invent addresses.
- Never invent booking websites.
- Never invent appointment availability.
- Availability will be checked separately.
- Only return a booking URL if one appears.

Return ONLY JSON:

{{
  "query_summary": "",
  "options": [
    {{
      "name": "",
      "address": "",
      "hours": "",
      "booking_url": "",
      "why_it_fits": "",
      "evidence": ""
    }}
  ],
  "notes": []
}}
""")

    return {
        "search_query": query,
        "result": options
    }


# =========================================================
# APPOINTMENT AVAILABILITY
# =========================================================

@app.post("/api/appointments/availability")
def appointment_availability(payload: dict):

    name = payload.get(
        "name",
        ""
    ).strip()

    address = payload.get(
        "address",
        ""
    ).strip()

    booking_url = payload.get(
        "booking_url",
        ""
    ).strip()

    what = payload.get(
        "what",
        ""
    ).strip()

    when = payload.get(
        "when",
        ""
    ).strip()

    extras = payload.get(
        "extras",
        ""
    ).strip()

    if not name:

        return {
            "error": (
                "No appointment option was selected."
            )
        }

    task = f"""
You are Kindly's appointment availability agent.

Business:
{name}

Address:
{address}

Booking website:
{booking_url}

Service:
{what}

Requested time:
{when}

Extra preferences:
{extras}

Investigate the ACTUAL booking website.

IMPORTANT:

1. Open the booking website if a URL is provided.

2. If no URL is provided, search for the official
   booking page for this exact business.

3. Navigate through the booking flow.

4. Select the requested service if necessary.

5. Look for the requested date/time.

6. Find REAL appointment slots currently shown.

7. DO NOT book anything.

8. DO NOT submit an appointment.

9. DO NOT enter payment information.

10. DO NOT bypass CAPTCHAs or security.

11. If login/manual action is required,
    report that instead.

12. Only return availability actually seen.

Return ONLY JSON:

{{
  "business": "{name}",
  "website": "",
  "status": "confirmed",
  "date": "",
  "requested_time": "{when}",
  "slots": [
    {{
      "date": "",
      "time": "",
      "service": "",
      "availability": "available"
    }}
  ],
  "message": "",
  "manual_action_required": false
}}
"""

    try:

        availability_result = run_web_agent(
            task
        )

        if not availability_result:

            return {
                "error": (
                    "The appointment agent did "
                    "not return a result."
                )
            }

        try:

            parsed = clean_json(
                availability_result
            )

        except Exception:

            parsed = {
                "status": "unable_to_verify",
                "slots": [],
                "message": availability_result,
                "manual_action_required": True
            }

        return {
            "business": name,
            "address": address,
            "booking_url": booking_url,
            "result": parsed
        }

    except Exception as e:

        print()
        print(
            "APPOINTMENT AVAILABILITY ERROR:"
        )
        print(repr(e))
        print()

        return {
            "error": (
                "Kindly could not check availability."
            )
        }


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
