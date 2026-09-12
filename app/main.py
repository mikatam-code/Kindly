from flask import Flask, request, jsonify, send_from_directory
from google import genai
from dotenv import load_dotenv
import os
import asyncio

from agent import run_agent


# Load API keys from .env
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Location of Kindly's website
PUBLIC_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "public"
)


@app.route("/")
def home():
    return send_from_directory(
        PUBLIC_FOLDER,
        "index.html"
    )


@app.route("/book-appointment", methods=["POST"])
def book_appointment():

    # Get what the user typed on the Kindly website
    data = request.get_json()

    user_request = data.get("request", "")

    if not user_request.strip():
        return jsonify({
            "message": "Please tell me what appointment you need."
        })

    print("BOOK APPOINTMENT ROUTE REACHED")
    print("USER REQUEST:", user_request)
    # Ask Gemini to understand the user's request
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=f"""
You are Kindly, a patient and trustworthy digital assistant
designed to help older adults use the internet.

Analyze the user's appointment request.

Identify:
1. What type of appointment they want
2. When they want it
3. Any time preference

User request:
{user_request}

Respond in exactly this format:

Appointment type: ...
When: ...
Time preference: ...
"""
    )

    # Gemini's understanding of the request
    appointment_info = getattr(interaction, "output_text", "")
    print("GEMINI RESULT:", appointment_info)

    # Give the browser agent a task based on what the user asked
    task = f"""
You are Kindly, a patient and trustworthy digital assistant
designed to help an older adult book an appointment online.

The user originally said:
"{user_request}"

Gemini understood the request as:
{appointment_info}

Your job is to help the user find an appropriate appointment online.

Important rules:

1. Use simple language.
2. Clearly explain what you are doing.
3. Find available appointment times.
4. Do NOT book anything yet.
5. Before submitting an appointment, STOP and ask the user
   for confirmation.
6. Never enter payment information.
7. Be careful with personal information.
8. If the website looks suspicious, explain why.
"""

   # Run the Steel browser agent
    try:

     result = asyncio.run(
         run_agent(task)
    )

    except Exception as e:

        print()
        print("================================")
        print("AGENT ERROR")
        print("================================")
        print(repr(e))
        print()

        return jsonify({
            "message": "The browser agent failed.",
            "error": str(e),
            "understanding": appointment_info
        }), 500


    return jsonify({
        "message": str(result),
        "understanding": appointment_info
    })


if __name__ == "__main__":
    print()
    print("========================================")
    print("        KINDLY - YOUR WEB HELPER")
    print("========================================")
    print()
    print("Open Kindly at:")
    print("http://127.0.0.1:5000")
    print()

    app.run(
        port=5000,
        debug=True
    )
