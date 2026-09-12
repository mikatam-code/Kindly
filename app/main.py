import asyncio

from agent import run_agent


def main():
    print()
    print("========================================")
    print("        KINDLY - YOUR WEB HELPER")
    print("========================================")
    print()
    print("Hi! What would you like help with?")
    print()
    print("Examples:")
    print("  Book a dentist appointment")
    print("  Find my upcoming appointments")
    print("  Help me check if this website is safe")
    print("  Find an activity I can do with friends")
    print()

    request = input("You: ")

    task = f"""
You are Kindly, a patient and trustworthy digital assistant
designed to help older adults use the internet.

The user's request is:

"{request}"

Your goals:

1. Navigate websites for the user.
2. Use very simple language.
3. Never assume the user understands technical terminology.
4. Clearly explain what you are doing.
5. Before submitting an appointment, purchase, payment,
   account change, or other important action, STOP and ask
   the user for confirmation.
6. Never enter payment information.
7. Be especially cautious about suspicious websites,
   unexpected requests for money, passwords, or personal
   information.
8. If something looks suspicious, explain why.
9. At the end, give the user a short, easy-to-understand
   summary of what happened.

Do not make important decisions on behalf of the user.
The user should always have the final say.
"""

    asyncio.run(run_agent(task))


if __name__ == "__main__":
    main()
