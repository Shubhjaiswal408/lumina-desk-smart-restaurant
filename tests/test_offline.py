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

print("\nSizes and labels")
order("i want a paneer momo in gravy and one peri peri fries large",
      [("Paneer Momo (Gravy)", 1), ("Large Peri-Peri Fries", 1)])
pizza = menu.find_dish("margherita")
burger = menu.find_dish("classic aloo tikki burger")
check(menu.label_for(pizza, "Large") == "Large Margherita", "a real size leads")
check(menu.label_for(burger, "Cheese Ring") == "Classic Aloo Tikki Burger (Cheese Ring)",
      "a variant trails in brackets")

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
