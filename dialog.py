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
import menu
from session import Session

# Normalise the two naming schemes onto one internal set.
_ALIASES = {
    "order_item": "order",
    "end_conversation": "end",
    "unknown": "smalltalk",
}


def _diet(dish: dict) -> str:
    if dish["vegan"]:
        return "vegan"
    return "vegetarian" if dish["veg"] else "non-vegetarian"


def handle(result: dict, session: Session) -> str:
    intent = _ALIASES.get(result["intent"], result["intent"])
    llm_reply = result.get("reply", "")

    if intent == "order":
        items = result.get("items") or []
        # Fall back to single dish / context ("add it") if no items array.
        if not items:
            dish = result.get("dish") or session.last_dish
            if not dish:
                return "Sure — what would you like?"
            items = [{"dish": dish, "quantity": result.get("quantity", 1)}]

        added, total, unavailable, assumed = [], 0, [], []
        for it in items:
            dish = it["dish"]
            if not menu.is_available(dish):               # 86'd in the admin
                unavailable.append(dish["name"])
                continue
            size = it.get("size") or menu.default_size(dish)
            # If the dish comes in sizes and the guest didn't pick one, we take
            # the base size and say so, so they can trade up.
            if menu.size_names(dish) and not it.get("size"):
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
        if len(assumed) == 1:
            others = [s for s in menu.size_names(assumed[0]) if s != menu.default_size(assumed[0])]
            if others:
                note += f" That's the {menu.default_size(assumed[0])} — {' or '.join(others)} if you'd prefer."
        return f"I've added {summary} to your order, {total} rupees.{note} Anything else?"

    if intent == "remove":
        dish = result.get("remove_dish") or result.get("dish") or session.last_dish
        if not dish:
            return "Which one should I take off?"
        # "remove one naan" drops just one; "remove the naan" drops the whole line.
        qty = result.get("quantity", 0) if result.get("qty_explicit") else 0
        if qty and qty > 0:
            ok = session.decrement_dish(dish, qty)
            return (f"Done — {qty} {dish['name']} removed. Anything else?" if ok
                    else f"You don't have {dish['name']} on the order.")
        if session.remove_dish(dish):
            return f"Taken off the {dish['name']}. Anything else?"
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
            return msg + " Anything else?"
        return "No problem — what instead?"

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
        incl = f" including {session.tax():.0f} rupees GST" if mode == "inclusive" else ""
        return (f"Your order is {session.line_summary()}. "
                f"That comes to {session.total():.0f} rupees{incl}.")

    if intent == "split_bill":
        if session.is_empty():
            return "Nothing to split yet — want me to run through the menu?"
        ways = result.get("ways", 2)
        each = session.total() / ways
        return f"Splitting {session.total():.0f} rupees {ways} ways comes to {each:.0f} rupees each."

    if intent == "ask_ingredient":
        dish = result.get("dish") or session.last_dish
        if not dish:
            return "Which one do you mean?"
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
        if not dish:
            return "Which one should I check?"
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
        return (f"{picks[0]} is our most-ordered — {' and '.join(picks[1:])} go fast too. "
                f"Want the {picks[0]}?"
                if picks else "What are you in the mood for?")

    if intent == "clear_cart":
        if session.is_empty():
            return "It's already empty. What can I get you?"
        session.clear()
        return "Cleared. What would you like?"

    if intent == "show_category":
        cat = result.get("category")
        if not cat:
            return "Which one — pizzas, garlic bread, burgers, momos, fries, or drinks?"
        dishes = menu.by_category(cat)
        def _q(d):
            base = menu.price_for(d, menu.default_size(d))
            return f"{d['name']} from {base}" if menu.size_names(d) else f"{d['name']} at {base}"
        names = ", ".join(_q(d) for d in dishes[:8])
        more = f" and {len(dishes) - 8} more" if len(dishes) > 8 else ""
        label = {"Starter": "starters", "Main": "mains", "Bread": "breads",
                 "Rice": "rice dishes", "Dessert": "desserts", "Beverage": "drinks"}.get(cat, cat.lower())
        return f"In {label}: {names} rupees{more}. Want any of those?"

    if intent == "show_menu":
        pizzas = ", ".join(d["name"] for d in menu.by_category("Pizza")[:3])
        return (
            f"We're all pure veg. Pizzas from ninety rupees — {pizzas} and many more — "
            f"plus stuffed garlic breads, burgers, momos, calizza, fries, shakes and mocktails. "
            f"Which section shall I run through?"
        )

    if intent == "call_staff":
        session.staff_called = True
        return llm_reply or "Done — someone's on their way."

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
        return "Cool — say Hey Lumina whenever you need me."

    # smalltalk / unknown
    return llm_reply or (
        "Sorry, I didn't quite catch that. You can order food, check your bill, "
        "ask about a dish, or call a server."
    )
