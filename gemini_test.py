from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

user_request = input("What do you need help with? ")

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input=f"""
You are an assistant helping an elderly person use the internet.

Read the user's request and identify:
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

print(getattr(interaction, "output_text", ""))
