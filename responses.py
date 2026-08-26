"""Spoken lines for Lumina.

Tone note: this outlet is a busy, casual pure-veg pizza place — not fine dining.
So the lines are friendly and quick, the way good counter staff talk. No
"good evening sir", no speeches; guests want to order and get on with it.

Kept separate from the audio loop so they're easy to tune or translate.
"""
import random

# Every line here starts with a word that can be lost without losing the
# meaning. The reSpeaker swallows roughly the first quarter second whatever we
# feed it — dither, ramps and a held-open device all failed to stop it — so the
# reply is written to survive it instead. Drop "Yes" from "Yes, what can I get
# you?" and a guest still hears a complete question.
#
# The rule for anything added here: read it without its first word. If it still
# works, it's fine.

# Said the instant the wake word fires, mid-meal.
GREETINGS = [
    "Yes, what can I get you?",
    "Sure, go ahead.",
    "Yes, tell me.",
    "Right, what would you like?",
]

# First wake of a session. Short, because the guest is waiting to talk — and
# front-loaded with a throwaway word for the same reason as the rest.
WELCOME = "Yes, what can I get you?"


def greeting(session=None) -> str:
    """What to say on a re-wake, mid-meal.

    Picking at random from a list is what a machine does. Someone who has
    already ordered doesn't need "What can I get you?" again — they came back
    for something specific, so get out of the way and let them say it.
    """
    if session is not None and getattr(session, "cart", None):
        return random.choice(["Yes, go ahead.", "Sure, tell me.", "Yes, I'm listening."])
    return random.choice(GREETINGS)
