import os
from dotenv import load_dotenv
from google import genai

load_dotenv()


# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")


gemini = genai.Client(
    api_key=GEMINI_API_KEY
)


# ---------------------------------------------------------
# ASK KINDLY
# ---------------------------------------------------------

def ask_kindly(user_request):

    if not user_request.strip():
        return "Please tell me what you need help with."

    response = gemini.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are Kindly, a helpful digital assistant.

Answer the user's request clearly and naturally.

If the user asks you to find something online,
give useful and specific information about what they
are looking for.

Do not pretend that you completed an action that you
did not actually complete.

User request:

{user_request}
"""
    )

    if response.text is None:
        return "Sorry, I couldn't find an answer."

    return response.text


# ---------------------------------------------------------
# GEMINI WEB AGENT
# ---------------------------------------------------------

def run_web_agent(user_request):

    print()
    print("========================================")
    print("          KINDLY WEB AGENT")
    print("========================================")

    print()
    print("USER REQUEST:")
    print(user_request)

    print()
    print("Gemini is finding information...")
    print()

    response = gemini.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"""
You are the web-search assistant for Kindly.

Find useful, current information that answers the user's request.

The user could ask for ANYTHING, such as:
- study cafes
- restaurants
- appointments
- stores
- events
- services
- transportation
- products
- places
- other useful information



Do not assume the request is about a particular category.

For example, if the user says:
"Find me study cafes near the University of Toronto"

provide several actual study cafes near the University of Toronto
and useful information about them.

Be specific and useful.

FORMAT YOUR ANSWER EXACTLY LIKE THIS:

1. Name of place or option
Location: short address or area
Why it's good: one short sentence
Hours: if known, otherwise say "Check website"

2. Name of place or option
Location: short address or area
Why it's good: one short sentence
Hours: if known, otherwise say "Check website"

Continue for up to 4-5 options.

Rules:
- Each option starts with a number and a period, then the name.
- Each fact goes on its own line as "Label: value".
- Never put two facts on the same line.
- Do not use markdown headers, bold, or bullet dashes.
- Keep each line short.
- Do not claim an action was completed unless it actually was.



User request:

{user_request}
"""
    )

    if response.text is None:
        result = "I couldn't find useful information right now."
    else:
        result = response.text

    print()
    print("========================================")
    print("       GEMINI FOUND THIS INFORMATION")
    print("========================================")
    print()
    print(result)
    print()
    print("========================================")
    print("          END GEMINI RESULT")
    print("========================================")
    print()

    return result
