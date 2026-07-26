"""Spoken responses for the Lumina Desk restaurant scenario.

Kept separate from the audio loop so lines are easy to tune / translate later.
"""
import random

# Said the moment the wake word is detected. Short so it feels responsive.
GREETINGS = [
    "Yes, how can I help?",
    "At your service — what would you like?",
    "Of course, go ahead.",
    "I'm right here. What can I get you?",
    "Yes? Tell me what you'd like.",
]

# A fuller welcome — used for the very first wake of a session.
WELCOME = (
    "Good evening, and welcome. I'm Lumina, your waiter this evening. "
    "I can walk you through the menu, take your order, or answer anything about "
    "a dish. What can I get started for you?"
)


def greeting() -> str:
    return random.choice(GREETINGS)
