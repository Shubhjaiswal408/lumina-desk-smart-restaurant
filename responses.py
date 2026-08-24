"""Spoken lines for Lumina.

Tone note: this outlet is a busy, casual pure-veg pizza place — not fine dining.
So the lines are friendly and quick, the way good counter staff talk. No
"good evening sir", no speeches; guests want to order and get on with it.

Kept separate from the audio loop so they're easy to tune or translate.
"""
import random

# Said the instant the wake word fires. Short, so it feels snappy.
GREETINGS = [
    "Yeah? What can I get you?",
    "I'm listening.",
    "Go ahead!",
    "Sure — what would you like?",
    "Yep, tell me.",
]

# First wake of a session. This one has to be SHORT.
#
# It used to be two sentences explaining what Lumina could do — 142 characters,
# which the neural voice takes about nine seconds to say. A guest says "Hey
# Lumina", hears a speech start, waits, decides it didn't hear them, and says it
# again — and that second "Hey Lumina" lands as their order. Watched it happen.
#
# Everything the old line explained is already printed on the screen in front of
# them. Say hello and get out of the way.
WELCOME = "Hi! What can I get you?"


def greeting() -> str:
    return random.choice(GREETINGS)
