"""Offline fast-path tests — no mic, no network, no services.

The rule parser (intents.py) is what answers the guest when the internet is down,
so it has to be right. Every case here is a mistake this system actually made.

    ./venv/bin/python tests/test_offline.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dialog          # noqa: E402
import intents         # noqa: E402
import menu            # noqa: E402
from session import Session   # noqa: E402

FAILURES = []


def check(cond, what):
    if not cond:
        FAILURES.append(what)
    print(("  ok  " if cond else "  FAIL") + "  " + what)


def intent(text, expected):
    got = intents.parse_intent(text)["intent"]
    check(got == expected, f'"{text}" -> {expected} (got {got})')


def cart_of(text):
    """Run one utterance through the offline path and return the resulting cart."""
    s = Session()
    dialog.handle(intents.parse_intent(text), s)
    return [(s.line_label(l), l["qty"]) for l in s.cart]


def order(text, expected):
    got = cart_of(text)
    check(got == expected, f'"{text}" -> {expected} (got {got})')


print("\nIntent classification")
# Half this menu has "Veg." in the name — those are orders, not diet questions.
intent("one veg cheese momo", "order_item")
intent("two mix veg momo", "order_item")
intent("crispy veg burger", "order_item")
# "nut" hides inside "Hazelnut", so allergen matching must be whole-word.
intent("one hazelnut cold coffee", "order_item")
# Real questions still classify as questions.
intent("is the margherita vegetarian", "ask_ingredient")
intent("what is in the veg cheese momo", "ask_ingredient")
intent("does it contain nuts", "ask_allergen")
intent("i am allergic to gluten", "ask_allergen")
# The rest of the everyday commands.
intent("what is my bill", "check_bill")
intent("remove the cold coffee", "remove")
intent("bring me two water", "request_item")
intent("i want to pay", "pay")
intent("cancel my order", "clear_cart")
intent("that's all", "end_conversation")

print("\nPrice questions are not orders")
# "what's the price of X" used to ADD X to the cart, and "how much is X" used to
# be answered with the guest's bill.
intent("how much is a margherita", "ask_price")
intent("what is the price of paneer momo", "ask_price")
intent("how much for two cold coffee", "ask_price")
order("what is the price of paneer momo", [])
order("how much is a margherita", [])
intent("what's my bill", "check_bill")
intent("what do i owe", "check_bill")

print("\nA category is a question, not a dish")
# "momo" used to be an alias of Mix Veg. Momo, so a slightly-misheard "paneer
# momo" silently quoted (or ordered) a different dish. There are sixteen momos —
# naming the section should read the section back.
check(menu.find_dish("momo") is None, "'momo' alone doesn't resolve to one dish")
check(menu.find_dish("fries") is None, "'fries' alone doesn't resolve to one dish")
check(menu.find_dish("paneer momo")["name"] == "Paneer Momo", "a named momo still works")
check(menu.find_dish("salted fries")["name"] == "Salted Fries", "a named fries still works")
intent("momo", "show_category")
intent("what pizzas do you have", "show_category")
order("momo", [])

print("\nWhisper prompt fits Groq's limit")
import stt                                                        # noqa: E402
prompt = stt._stt_prompt()
check(len(prompt) <= 896, f"prompt is {len(prompt)} chars (Groq rejects >896)")
check("Paneer" in prompt and "Calizza" in prompt,
      "prompt keeps the words Whisper actually needs help with")

print("\nSpoken replies lead with a short clause")
import tts                                                        # noqa: E402
long_reply = ("I've added 1 Large Margherita and 2 Cold Coffees to your order, "
              "468 rupees. Anything else?")
lead = tts._phrases(long_reply)[0]
check(len(lead) < len(long_reply), "a long reply is split so speech starts sooner")
check(tts._phrases("Cleared. What would you like?") == ["Cleared. What would you like?"],
      "a short reply is left alone")
check("".join(tts._phrases(long_reply)).replace(" ", "")
      == long_reply.replace(" ", ""), "splitting never loses a word")

print("\nMulti-item orders")
order("one large margherita and two cold coffee",
      [("Large Margherita", 1), ("Cold Coffee", 2)])
order("three choco lava cake, one hot brownie and two lemon iced tea",
      [("Choco Lava Cake", 3), ("Hot Brownie", 1), ("Lemon Iced Tea", 2)])
# Dish names contain "and"/"&" of their own — the split must not cut them.
order("two corn and cheese garlic bread", [("Corn & Cheese Garlic Bread", 2)])
order("veg and paneer zingy parcel", [("Veg. & Paneer Zingy Parcel", 1)])
# "with" introduces a modifier, not a second dish.
order("one margherita with extra cheese", [("Regular Margherita", 1)])

print("\nGuests speak in plurals")
# A strict word boundary rejected the trailing "s", so "two cold coffees" put
# nothing on the order at all.
order("two cold coffees", [("Cold Coffee", 2)])
order("three margheritas", [("Regular Margherita", 3)])
order("two paneer momos", [("Paneer Momo (Steam)", 2)])
check(menu.find_dish("burgers") is None, "a plural category is still a category")

print("\nOffline speech recognition hears 'two' as 'too'")
# Vosk transcribes "two cold coffees" as "too cold coffees" almost every time,
# and the quantity silently became 1 — a wrong bill, offline, unnoticed.
order("too cold coffees", [("Cold Coffee", 2)])
order("one large margarita and too cold coffees",
      [("Large Margherita", 1), ("Cold Coffee", 2)])
# ...but only at the start of a clause, where a count actually goes.
order("one margherita not too spicy", [("Regular Margherita", 1)])
order("i want to order a margherita", [("Regular Margherita", 1)])

print("\nAnswers a guest can actually use")
# "I'm allergic to gluten, what can I eat" used to be answered with the last
# dish mentioned — which contained gluten.
_r = intents.parse_intent("i'm allergic to gluten, what can i eat")
_s = Session(); _s.last_dish = menu.find_dish("margherita")
_a = dialog.handle(_r, _s)
check("Without gluten" in _a, "an allergy with no dish named lists safe options")
check("Margherita" not in _a, "and does not offer the dish that contains it")
# ...but a question about one dish stays a question about that dish.
_s2 = Session(); _s2.last_dish = menu.find_dish("margherita")
check("contains" in dialog.handle(
    intents.parse_intent("does the margherita have dairy"), _s2),
    "a direct question still gets a direct answer")
_s3 = Session(); _s3.last_dish = menu.find_dish("margherita")
check("Margherita" in dialog.handle(
    intents.parse_intent("does it contain nuts"), _s3),
    "'it' still means the dish we were just discussing")

# Sixty-six pizza names read aloud is a wall of sound.
_big = dialog.handle(intents.parse_intent("what pizzas do you have"), Session())
check("66 pizzas" in _big and len(_big) < 200, "a big section is summarised, not recited")
check("Choco Lava Cake" in dialog.handle(
    intents.parse_intent("show me the desserts"), Session()),
    "a small section is still read out in full")

# "give me a medium one" names a size but no dish.
_s4 = Session(); _s4.last_dish = menu.find_dish("veg extravaganza")
dialog.handle(intents.parse_intent("okay give me a medium one"), _s4)
check([(_s4.line_label(l), l["qty"]) for l in _s4.cart] == [("Medium Veg. Extravaganza", 1)],
      "a size given without a dish is honoured")

print("\nAnswering Lumina's own question")
# Lumina asked "Want the Margherita?", the guest said "Yes", and it read out the
# menu. It had no notion of what an answer was.
_s = Session()
_offer = dialog.handle(intents.parse_intent("can you recommend something"), _s)
check("Want the" in _offer, "a recommendation ends in an offer")
_yes = dialog.handle(intents.parse_intent("Yes."), _s)
check([(l["dish"]["name"], l["qty"]) for l in _s.cart] == [("Margherita", 1)],
      "'yes' orders the dish that was offered")
for word in ("sure", "haan", "ok please", "yeah"):
    _s2 = Session()
    dialog.handle(intents.parse_intent("can you recommend something"), _s2)
    dialog.handle(intents.parse_intent(word), _s2)
    check(len(_s2.cart) == 1, f"'{word}' counts as yes")
# ...but only when something was actually offered.
check("what would you like" in dialog.handle(
    intents.parse_intent("yes"), Session()).lower(),
    "'yes' out of nowhere orders nothing")
# An offer expires the moment anything else is said.
_s3 = Session()
dialog.handle(intents.parse_intent("can you recommend something"), _s3)
dialog.handle(intents.parse_intent("what is my bill"), _s3)
dialog.handle(intents.parse_intent("yes"), _s3)
check(not _s3.cart, "a stale offer can't be accepted a turn later")

print("\nSizes and labels")
order("i want a paneer momo in gravy and one peri peri fries large",
      [("Paneer Momo (Gravy)", 1), ("Large Peri-Peri Fries", 1)])
pizza = menu.find_dish("margherita")
burger = menu.find_dish("classic aloo tikki burger")
check(menu.label_for(pizza, "Large") == "Large Margherita", "a real size leads")
check(menu.label_for(burger, "Cheese Ring") == "Classic Aloo Tikki Burger (Cheese Ring)",
      "a variant trails in brackets")

print("\nThe feedback QR knows which table it came from")
import json                                                       # noqa: E402
import pathlib                                                    # noqa: E402
import settings                                                   # noqa: E402

_sp = pathlib.Path(sys.path[0]) / "settings.json"
_orig = _sp.read_text() if _sp.exists() else None
try:
    _d = json.loads(_orig) if _orig else {}
    _d["feedback_url"] = ("https://docs.google.com/forms/d/e/1FAIpQLSxTABLEx/viewform"
                          "?usp=pp_url&entry.1234567=TABLE")
    _sp.write_text(json.dumps(_d, indent=2))
    settings._mtime = 0
    check(settings.feedback_url("07").endswith("entry.1234567=07"),
          "the table is filled into the pre-filled link")
    # A form id can contain the letters TABLE; only an exact answer value moves.
    check("1FAIpQLSxTABLEx" in settings.feedback_url("07"),
          "the form id is never rewritten")
    _d["feedback_url"] = "https://forms.gle/abc123"
    _sp.write_text(json.dumps(_d, indent=2))
    settings._mtime = 0
    check(settings.feedback_url("07") == "https://forms.gle/abc123",
          "a plain form link is left exactly as pasted")
finally:
    if _orig is not None:
        _sp.write_text(_orig)
    settings._mtime = 0

print("\nThe voice falls back, never doubles up")
# _edge returning False must mean "nothing was played", or the fallback would
# repeat a line the guest already heard half of.
check(tts._edge("hi", "xx-not-a-language") is False,
      "an unknown language declines instead of guessing a voice")
_engine = settings.get("tts_engine")
try:
    settings.save({"tts_engine": "local"})
    check(tts._edge("hi", "en") is False, "the local setting skips the online voice")
    settings.save({"tts_engine": "natural", "mode": "offline"})
    check(tts._edge("hi", "en") is False, "offline mode never reaches the network")
finally:
    settings.save({"tts_engine": _engine, "mode": "auto"})
check("en-IN" in tts.EDGE_VOICES["en"], "English guests hear an Indian voice")
check(set(("hi", "gu")) <= set(tts.EDGE_VOICES), "Hindi and Gujarati have voices")

print("\nThe pay QR survives both panels")
# The mono panel's firmware maps red to black. The UPI QR has to stay scannable
# after that — an unreadable QR means the guest simply cannot pay.
import numpy as np                                                # noqa: E402
import payments                                                   # noqa: E402
import ui_render                                                  # noqa: E402
from PIL import Image                                             # noqa: E402

_s = Session()
_s.add_dish(menu.find_dish("margherita"), 1, "Large")
_url, _ = payments.upi_url(_s.total(), "07")
_img = ui_render.to_epaper(ui_render.render_payment(_s, _url, table="07"))
_a = np.asarray(_img, dtype=np.uint8)
check(set(np.unique(_a)) <= {0, 1, 2}, "the frame only uses the panel's 3 colours")

try:
    from pyzbar.pyzbar import decode                              # noqa: E402
    # Palette: 0 = white, 1 = black, 2 = red.
    # Colour panel — only true black reads as dark; a QR that leaned on red
    # would fall apart here, which is why ui_render thresholds it to pure B/W.
    # Mono panel — the firmware maps red to black.
    for label, arr in (("colour panel", np.where(_a == 1, 0, 255)),
                       ("mono panel", np.where(_a == 0, 255, 0))):
        got = decode(Image.fromarray(arr.astype(np.uint8), "L"))
        check(bool(got) and got[0].data.decode() == _url,
              f"UPI QR decodes on the {label}")
except ImportError:
    print("  skip  QR decode (pip install pyzbar for this one)")

print("\nMoney is computed, never spoken by a model")
s = Session()
s.add_dish(pizza, 2, "Large")
check(s.subtotal() == 2 * menu.price_for(pizza, "Large"), "subtotal multiplies correctly")
check(s.total() == s.subtotal(), "inclusive tax leaves the total alone")
check(all(d["veg"] for d in menu.MENU), "the whole menu is vegetarian")

print()
if FAILURES:
    print(f"{len(FAILURES)} failure(s):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("all good")
