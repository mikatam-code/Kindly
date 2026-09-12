import json
import os
from datetime import datetime


FILE_NAME = "reminders.json"


def load_reminders():
    """Load saved reminders."""

    if not os.path.exists(FILE_NAME):
        return []

    with open(FILE_NAME, "r") as file:
        return json.load(file)


def save_reminders(reminders):
    """Save reminders to a JSON file."""

    with open(FILE_NAME, "w") as file:
        json.dump(reminders, file, indent=4)


def add_reminder(title, date, time):
    """
    Add a reminder.

    Parameters:
        title: What the reminder is for.
        date: Date of the reminder.
        time: Time of the reminder.
    """

    reminders = load_reminders()

    reminder = {
        "title": title,
        "date": date,
        "time": time
    }

    reminders.append(reminder)

    save_reminders(reminders)

    print()
    print("Reminder saved!")
    print(f"{title}")
    print(f"{date} at {time}")


def show_reminders():
    """Display all saved reminders."""

    reminders = load_reminders()

    if not reminders:
        print("You don't have any reminders yet.")
        return

    print()
    print("Your reminders:")
    print()

    for reminder in reminders:
        print(
            f"- {reminder['title']} "
            f"on {reminder['date']} "
            f"at {reminder['time']}"
        )
