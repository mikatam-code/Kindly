import os

from dotenv import load_dotenv
from steel import Steel

from browser_use import Agent, BrowserSession
from browser_use.llm import ChatOpenAI


load_dotenv()

STEEL_API_KEY = os.getenv("STEEL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def run_agent(task):
    """
    Runs the elderly assistant browser agent.

    Parameters:
        task: What the user wants the agent to do.

    Returns:
        The agent's final result.
    """

    if not STEEL_API_KEY:
        raise ValueError("STEEL_API_KEY is missing from .env")

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing from .env")

    # Create a cloud browser using Steel
    steel = Steel(
        steel_api_key=STEEL_API_KEY
    )

    session = steel.sessions.create()

    print()
    print("================================")
    print("Steel browser started!")
    print("Watch the agent here:")
    print(session.session_viewer_url)
    print("================================")
    print()

    # Connect Browser Use to the Steel browser
    cdp_url = (
        f"{session.websocket_url}"
        f"&apiKey={STEEL_API_KEY}"
    )

    browser_session = BrowserSession(
        cdp_url=cdp_url
    )

    # Give the AI its instructions
    agent = Agent(
        task=task,
        llm=ChatOpenAI(
            model="gpt-5",
            api_key=OPENAI_API_KEY
        ),
        browser_session=browser_session
    )

    try:
        result = await agent.run()

        print()
        print("================================")
        print("AGENT RESULT")
        print("================================")
        print(result)

        return result

    finally:
        # Important: release the Steel session
        steel.sessions.release(session.id)
