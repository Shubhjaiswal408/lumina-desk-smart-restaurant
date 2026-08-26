"""Maps a parsed intent to a spoken response and updates session state.

Accepts intents from either source:
  * LLM (llm.py):   order, remove, replace, check_bill, split_bill,
                    ask_ingredient, ask_allergen, recommend, show_menu,
                    call_staff, pay, unavailable, smalltalk, end
  * Rules (intents.py, offline): order_item, request_item, end_conversation,
                    unknown, ... (mapped onto the same handlers)

Facts (prices, allergens, bill math) are always computed here from menu.py /
session.py — never taken from the model.
"""
import re

import menu
from session import Session

# Normalise the two naming schemes onto one internal set.
_ALIASES = {
    "order_item": "order",
    "end_conversation": "end",
    "unknown": "smalltalk",
}


def canonical(intent: str) -> str:
    """Map either naming scheme (rules or LLM) onto the internal one."""
    return _ALIASES.get(intent, intent)


# The allergen words a guest actually uses, mapped to the menu's tags.
_ALLERGEN_WORDS = {
    "gluten": "gluten", "wheat": "gluten", "maida": "gluten",
    "dairy": "dairy", "milk": "dairy", "lactose": "dairy", "cheese": "dairy",
    "paneer": "dairy", "butter": "dairy",
    "soy": "soy", "soya": "soy",
    "nut": "nuts", "nuts": "nuts", "peanut": "nuts", "peanuts": "nuts",
    "egg": "egg", "eggs": "egg",
}


def _allergen_named(text: str):
    """Which allergen did the guest say they can't have?"""
    low = (text or "").lower()
    for word, tag in _ALLERGEN_WORDS.items():
        if re.search(rf"\b{word}\b", low):
            return tag
    return None


def _diet(dish: dict) -> str:
    if dish["vegan"]:
        return "vegan"
    return "vegetarian" if dish["veg"] else "non-vegetarian"


def handle(result: dict, session: Session) -> str:
    intent = _ALIASES.get(result["intent"], result["intent"])
    llm_reply = result.get("reply", "")
    # An offer only stands until the next thing is said. Whatever this turn is,
    # it answers the last question — anything that isn't a yes cancels it.
    offered, session.pending_offer = session.pending_offer, None

    if intent == "affirm":
        if not offered:
            return llm_reply or "Sure, what would you like?"
        intent = "order"
        result = {**result, "intent": "order", "dish": offered, "items": [],
                  "quantity": result.get("quantity", 1)}

    if intent == "order":
        items = result.get("items") or []
        # Fall back to single dish / context ("add it") if no items array.
        if not items:
            dish = result.get("dish") or session.last_dish
            if not dish:
                return "Sure, what would you like?"
            items = [{"dish": dish, "quantity": result.get("quantity", 1)}]

        added, total, unavailable, assumed = [], 0, [], []
        for it in items:
            dish = it["dish"]
            if not menu.is_available(dish):               # 86'd in the admin
                unavailable.append(dish["name"])
                continue
            # "give me a medium one" names a size but not a dish. Whoever
            # resolved the dish, the size is still sitting in what they said —
            # so look there before assuming the cheapest option and telling the
            # guest they could have had the one they just asked for.
            said = it.get("size") or menu.find_size(result.get("text", ""), dish)
            size = said or menu.default_size(dish)
            # If the dish comes in sizes and the guest didn't pick one, we take
            # the base size and say so, so they can trade up.
            if menu.size_names(dish) and not said:
                assumed.append(dish)
            session.add_dish(dish, it["quantity"], size)
            label = menu.label_for(dish, size)
            added.append(f"{it['quantity']} {label}")
            total += it["quantity"] * menu.price_for(dish, size)
        if added:
            session.last_dish = items[-1]["dish"]

        if not added:
            return f"Ah, the {unavailable[0]} is finished for today — want something else?"
        summary = added[0] if len(added) == 1 else ", ".join(added[:-1]) + " and " + added[-1]
        note = ""
        if unavailable:
            note = f" Sorry, the {unavailable[0]} is finished today."
        # Spoken, not written. "I've added X to your order" is four seconds of
        # throat-clearing before the guest hears anything they didn't know, and
        # the natural voice is slower than Piper — so every clause costs.
        #
        # The assumed size needs no announcement either: `summary` already says
        # "2 Paneer Momo (Steam)", so the guest hears the choice and can correct
        # it. Spelling out the alternatives cost three seconds on every order.
        # "Anything else?" every single time is 1.3 s of nothing — the guest
        # already knows they can keep talking. Say what was heard and the money.
        return f"{summary} — {total} rupees.{note}"

    if intent == "remove":
        dish = result.get("remove_dish") or result.get("dish") or session.last_dish
        if not dish:
            return "Sorry, which one should I take off?"
        # "remove one naan" drops just one; "remove the naan" drops the whole line.
        qty = result.get("quantity", 0) if result.get("qty_explicit") else 0
        if qty and qty > 0:
            ok = session.decrement_dish(dish, qty)
            return (f"Done, {qty} {dish['name']} off." if ok
                    else f"You don't have {dish['name']} on the order.")
        if session.remove_dish(dish):
            return f"Taken off the {dish['name']}."
        return f"You don't have {dish['name']} on the order."

    if intent == "replace":
        old, new = result.get("remove_dish"), result.get("dish")
        if old:
            session.remove_dish(old)
        if new:
            size = result.get("size") or menu.default_size(new)
            session.add_dish(new, result.get("quantity", 1), size)
            session.last_dish = new
            price = menu.price_for(new, size)
            label = menu.label_for(new, size)
            msg = f"Got it — {label}, {price} rupees."
            if old:
                msg = f"Swapped it for {label}, {price} rupees."
            return msg
        return "No problem, what instead?"

    if intent == "ask_price":
        d = result.get("dish") or session.last_dish
        if not d:
            return "Sorry, which dish did you mean?"
        session.last_dish = d          # so "yes, one of those" works next turn
        size = result.get("size")
        if size:
            session.pending_offer = d
            return f"{menu.label_for(d, size)} is {menu.price_for(d, size)} rupees. Want one?"
        sizes = menu.size_names(d)
        if sizes:
            bits = ", ".join(f"{s} {menu.price_for(d, s)}" for s in sizes)
            return f"{d['name']} — {bits} rupees. Which one?"
        session.pending_offer = d
        return f"{d['name']} is {menu.price_for(d)} rupees. Want one?"

    if intent == "request_item":
        item, qty = result.get("item"), result.get("quantity", 1)
        return f"Sure, {qty} {item} coming to your table."

    if intent == "check_bill":
        if session.is_empty():
            return "Nothing on the order yet. What can I get you?"
        mode = menu.tax_config()[0]
        if mode == "exclusive":
            return (
                f"Your order is {session.line_summary()}. "
                f"Subtotal {int(session.subtotal())} rupees, plus {session.tax():.0f} rupees tax, "
                f"for a total of {session.total():.0f} rupees."
            )
        incl = ", GST included" if mode == "inclusive" else ""
        return (f"{session.line_summary()} — "
                f"{session.total():.0f} rupees{incl}.")

    if intent == "split_bill":
        if session.is_empty():
            return "Nothing to split yet — want me to run through the menu?"
        ways = result.get("ways", 2)
        each = session.total() / ways
        return f"Splitting {session.total():.0f} rupees {ways} ways comes to {each:.0f} rupees each."

    if intent == "ask_ingredient":
        dish = result.get("dish") or session.last_dish
        if not dish:
            return "Sorry, which one do you mean?"
        session.last_dish = dish
        ings = dish.get("ingredients") or []
        if not ings:   # e.g. a dish added from the console with no recipe yet
            alg = (f" It does have {', '.join(dish['allergens'])} in it."
                   if dish.get("allergens") else "")
            return (f"I don't have the full recipe for the {dish['name']}.{alg} "
                    f"Want me to check with the kitchen?")
        return f"{dish['name']}: {', '.join(ings)}."

    if intent == "ask_allergen":
        dish = result.get("dish") or session.last_dish
        # "I'm allergic to gluten, what can I eat?" names an allergen and no
        # dish. Answering about whatever they last mentioned is worse than
        # useless when that dish contains the very thing they can't have.
        said = (result.get("text", "") or "").lower()
        avoid = _allergen_named(said)
        # Only offer alternatives when they asked what they CAN have. "Does the
        # margherita have dairy" and "does it contain nuts" are questions about
        # one dish, and answering either with a menu tour would be a non-answer.
        refers = re.search(r"\b(it|this|that|these|those|the one)\b", said)
        if avoid and not result.get("dish") and not refers:
            safe = [d for d in menu.all_dishes()
                    if avoid not in d["allergens"] and menu.is_available(d)]
            if not safe:
                return (f"Honestly, everything on our menu has {avoid} in it. "
                        f"Let me get someone from the kitchen for you.")
            names = ", ".join(d["name"] for d in safe[:6])
            more = f", and {len(safe) - 6} more" if len(safe) > 6 else ""
            return (f"Without {avoid} we've got {names}{more}. "
                    f"For a serious allergy I'll have the kitchen confirm before you order.")
        if not dish:
            return "Sorry, which one should I check?"
        session.last_dish = dish
        if dish["allergens"]:
            return (
                f"Heads up — the {dish['name']} contains {', '.join(dish['allergens'])}. "
                f"If it's a serious allergy I'll get someone from the kitchen to confirm."
            )
        return (f"No common allergens listed for the {dish['name']}. "
                f"I can double-check with the kitchen if you'd like.")

    if intent == "recommend":
        if result.get("dish"):
            session.last_dish = result["dish"]
        if llm_reply:
            return llm_reply
        picks = [p for p in menu.CHEF_SPECIALS if menu.find_dish(p)][:3]
        session.last_dish = menu.find_dish(picks[0]) if picks else None
        session.pending_offer = session.last_dish
        return (f"{picks[0]} is our most-ordered — {' and '.join(picks[1:])} go fast too. "
                f"Want the {picks[0]}?"
                if picks else "What are you in the mood for?")

    if intent == "clear_cart":
        if session.is_empty():
            return "That's already empty, what can I get you?"
        session.clear()
        return "Cleared, what would you like?"

    if intent == "show_category":
        cat = result.get("category")
        if not cat:
            return "Which one — pizzas, garlic bread, burgers, momos, fries, or drinks?"
        dishes = [d for d in menu.by_category(cat) if menu.is_available(d)]
        if not dishes:
            return "Nothing in that section today, sorry. What else can I get you?"
        label = {"Starter": "starters", "Dessert": "desserts", "Beverage": "drinks",
                 "Mocktail": "mocktails", "Momo": "momos", "Burger": "burgers",
                 "Pizza": "pizzas", "Calzone": "calzones", "Calizza": "calizzas",
                 "Parcel": "parcels", "Farali": "the farali menu",
                 "Fries": "fries", "Garlic Bread": "garlic breads"}.get(cat, cat.lower())

        def _q(d):
            base = menu.price_for(d, menu.default_size(d))
            return f"{d['name']} from {base}" if menu.size_names(d) else f"{d['name']} at {base}"

        # This is spoken aloud. Reeling off eight names and "58 more" is a wall
        # of sound nobody can hold in their head — so for a big section, say how
        # many there are, name the cheapest few as an anchor, and let them steer.
        if len(dishes) > 6:
            cheap = min(menu.price_for(d, menu.default_size(d)) for d in dishes)
            picks = ", ".join(d["name"] for d in dishes[:3])
            return (f"We've got {len(dishes)} {label}, from {cheap} rupees — "
                    f"{picks} and plenty more. Any flavour you're after, "
                    f"or shall I read a few out?")
        names = ", ".join(_q(d) for d in dishes)
        return f"In {label}: {names} rupees. Want any of those?"

    if intent == "show_menu":
        # Twenty seconds of sections, spoken at someone who just wants to order,
        # is worse than no answer. Name the headline categories and hand the
        # conversation straight back — the printed menu is on the table anyway.
        return "Pizzas, garlic bread, burgers, momos, fries, shakes. Which one?"

    if intent == "call_staff":
        session.staff_called = True
        return llm_reply or "Done, someone's on their way."

    if intent == "pay":
        if session.is_empty():
            return "There's no bill to pay yet."
        return (
            f"Your total is {session.total():.0f} rupees. I'll show a UPI QR code on the screen "
            f"for you to scan."
        )

    if intent == "unavailable":
        return llm_reply or "I'm sorry, we don't have that on the menu. Could I suggest something similar?"

    if intent == "end":
        if not session.is_empty():
            return f"That's {session.total():.0f} rupees. Enjoy — just say Hey Lumina if you need anything."
        return "Cool, say Hey Lumina whenever you need me."

    # smalltalk / unknown. Listing everything Lumina can do takes seven seconds
    # and doesn't help someone who was probably just misheard — ask them again.
    return llm_reply or "Sorry, could you say that again?"
