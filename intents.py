"""Rule-based intent parser for Lumina Desk (MVP).

Turns a transcribed sentence into a structured intent. Keyword/rule based for
now — fast, offline, debuggable. Swap for an LLM classifier later without
changing callers, as long as the returned dict shape stays the same.

Returned dict: {"intent": str, "text": str, ...slots}
Intents: order_item, request_item, check_bill, split_bill, ask_ingredient,
         ask_allergen, show_menu, call_staff, pay, unknown
"""
import re

import menu

_NUM_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


# Offline speech recognition hears "two" as "to" or "too" almost every time, and
# a quantity that quietly becomes 1 is a wrong bill. Only trust the homophone at
# the very start of a clause — that is where a count goes ("too cold coffees"),
# and it keeps "not too spicy" from ordering a second pizza.
_TWO_HOMOPHONE = re.compile(r"^(?:to|too)\b")


def _quantity(text: str) -> int:
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return max(1, int(m.group(1)))
    for word, n in _NUM_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return n
    if _TWO_HOMOPHONE.match(text.strip()):
        return 2
    return 1


def _split_ways(text: str) -> int:
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return max(2, int(m.group(1)))
    for word, n in _NUM_WORDS.items():
        if re.search(rf"\b{word}\b", text) and n >= 2:
            return n
    return 2


# "one margherita and two cold coffees" is one sentence but two order lines, so
# the offline path has to split it — otherwise a guest ordering two things
# offline silently gets one of them.
# Deliberately no "with": "a pizza with extra cheese" is one dish and a
# modifier, not two dishes.
_JOINERS = re.compile(r"\s*(?:,|\band\b|\bplus\b|\balso\b|&)\s*")
_AND, _AMP = "\x00", "\x01"


def _protect_names(t: str) -> str:
    """Menu names contain joiners of their own — "Corn & Cheese Garlic Bread",
    "Veg. & Paneer Zingy Parcel". Hide those before splitting so a dish never
    gets cut in half."""
    for d in menu.all_dishes():
        for name in [d["name"]] + list(d.get("aliases") or []):
            n = name.lower()
            if (" and " in n or "&" in n) and n in t:
                t = t.replace(n, n.replace(" and ", _AND).replace("&", _AMP))
    return t


def _order_items(t: str) -> list:
    """Every dish named in the sentence, each with its own quantity and size."""
    items, seen = [], set()
    for clause in _JOINERS.split(_protect_names(t)):
        clause = clause.replace(_AND, " and ").replace(_AMP, "&").strip()
        if not clause:
            continue
        d = menu.find_dish(clause)
        if d is None or d["name"] in seen:
            continue
        seen.add(d["name"])
        items.append({"dish": d, "quantity": _quantity(clause),
                      "size": menu.find_size(clause, d) or ""})
    return items


# Does the sentence read like a question at all?
_QUESTION = re.compile(r"^(is|are|was|does|do|can|could|would|has|have|which|what|any)\b"
                       r"|\?\s*$")

_END_PHRASES = {
    "no", "nope", "no thanks", "no thank you", "nothing", "nothing else",
    "that's all", "thats all", "that's it", "thats it", "that will be all",
    "i'm done", "im done", "we're done", "were done", "done", "no that's all",
    "goodbye", "bye", "that's everything", "all good", "we are good", "i'm good",
}


def parse_intent(text: str) -> dict:
    t = (text or "").lower().strip()
    if not t:
        return {"intent": "unknown", "text": text}

    has = lambda *kw: any(k in t for k in kw)
    # Whole-word test. Needed for short tokens that hide inside dish names —
    # "nut" is in "Hazelnut Cold Coffee", "veg" is in half this menu.
    word = lambda *kw: any(re.search(rf"\b{k}\b", t) for k in kw)

    # End of conversation — short, explicit closings only.
    stripped = t.strip(" .!,")
    if stripped in _END_PHRASES or has("that's all", "thats all", "nothing else",
                                       "that will be all", "we're done", "were done"):
        return {"intent": "end_conversation", "text": text}

    # Payment
    if has("pay", "payment", "upi", "qr code", "scan"):
        return {"intent": "pay", "text": text}

    # Clear the whole order
    if has("clear my order", "cancel everything", "cancel my order", "start over",
           "empty the cart", "clear the order", "cancel the order"):
        return {"intent": "clear_cart", "text": text}

    # Remove a dish (kept before ordering so "remove the naan" isn't an order)
    if has("remove", "take off", "take out", "cancel the", "don't want", "dont want",
           "no longer want"):
        d = menu.find_dish(t)
        if d:
            return {"intent": "remove", "text": text, "remove_dish": d,
                    "quantity": _quantity(t),
                    "qty_explicit": bool(re.search(
                        r"\b(\d+|one|two|three|four|five|a|an|single)\b", t))}

    # Recommendation
    if has("recommend", "suggest", "special", "what should i", "what's good",
           "whats good", "popular", "famous", "signature", "best dish", "your best"):
        return {"intent": "recommend", "text": text}

    # Split bill — any split/divide is a split intent.
    if has("split", "divide"):
        return {"intent": "split_bill", "text": text, "ways": _split_ways(t)}

    # "How much is a margherita" is a PRICE question, not a bill question, and
    # certainly not an order — answering it by adding the dish to the cart is the
    # kind of thing that gets a guest charged for something they never ordered.
    if has("how much is", "how much are", "how much for", "how much does",
           "price of", "price for", "the price", "cost of", "how much do"):
        d = menu.find_dish(t)
        if d:
            return {"intent": "ask_price", "text": text, "dish": d,
                    "size": menu.find_size(t, d) or ""}
        # A price question we couldn't pin to a dish — usually a misheard name.
        # Ask which one. Reading the guest their bill instead would be a
        # confident answer to a question they didn't ask.
        if not has("bill", "total", "owe", "the check", "altogether", "in all"):
            cat = menu.find_category(t)
            if cat:
                return {"intent": "show_category", "text": text, "category": cat}
            return {"intent": "ask_price", "text": text, "dish": None}

    # Bill
    if has("bill", "total", "how much", "what do i owe", "check please", "the check"):
        return {"intent": "check_bill", "text": text}

    # Allergy questions
    if has("allerg", "lactose", "safe to eat") or word("peanut", "peanuts", "gluten",
                                                       "dairy", "nut", "nuts", "soy"):
        return {"intent": "ask_allergen", "text": text, "dish": menu.find_dish(t)}

    # Ingredient / dietary questions. Diet words alone aren't enough: on an
    # all-veg menu, "two mix veg momo" is an ORDER, not a question about veg.
    asking = has("ingredient", "what's in", "whats in", "what is in", "made of",
                 "made with", "contain")
    diet = word("vegetarian", "vegan", "eggless", "jain") or has("non veg", "nonveg", "non-veg")
    if asking or (diet and _QUESTION.search(t)):
        return {"intent": "ask_ingredient", "text": text, "dish": menu.find_dish(t)}

    # A whole section: "what momos do you have", or just "momos". Naming a
    # category is not enough to order — there are sixteen momos — so read the
    # section back instead of silently picking one.
    if menu.find_dish(t) is None:
        cat = menu.find_category(t)
        if cat:
            return {"intent": "show_category", "text": text, "category": cat}

    # Menu. "I'd like to order" names no dish — it is a request for the menu,
    # not something to guess at. Without this it fell through to "I didn't quite
    # catch that", which is a strange answer to a perfectly clear sentence.
    if has("menu", "what do you have", "what can i", "options", "specials",
           "recommend", "suggest"):
        return {"intent": "show_menu", "text": text}
    # ...and only when they haven't already said what they want: "I want to
    # order a margherita" is an order, not a request for the menu.
    if menu.find_dish(t) is None and has(
            "place an order", "like to order", "want to order", "can i order",
            "start an order", "take my order"):
        return {"intent": "show_menu", "text": text}

    # Call staff
    if has("waiter", "staff", "manager", "call someone", "help me", "human", "complain"):
        return {"intent": "call_staff", "text": text}

    # Service item request (fork, water...) — check before generic order
    service = menu.find_service_item(t)
    if service and has("bring", "get", "need", "want", "can i", "give", "pass", "order", "some", "a "):
        return {"intent": "request_item", "text": text, "item": service, "quantity": _quantity(t)}

    # Pronoun order referencing the dish just discussed ("add it", "yes add that",
    # "sure, order one"). dish stays None -> dialog fills it from session context.
    # Pronoun order referencing the dish just discussed. "Give me a medium one"
    # is the common shape after asking about a dish — it names a size and no
    # dish at all, and used to fall through to "I didn't catch that".
    _REFERS = ("add it", "add that", "add this", "order it", "order that",
               "have it", "get it", "add one", "yes add", "sure add",
               "yes please add", "add to my order", "put it in",
               "i'll take it", "ill take it", "i'll take one", "ill take one",
               "give me one", "give me a", "make it a", "make it one",
               "i'll have one", "ill have one", "one of those", "one of them",
               "that one", "this one", "the same")
    if menu.find_dish(t) is None and (
            has(*_REFERS) or re.search(r"\b(one|ones)\b", t) and has(
                "medium", "large", "regular", "small", "steam", "gravy",
                "pan fry", "deep fry", "fried")):
        return {"intent": "order_item", "text": text, "dish": None,
                "quantity": _quantity(t), "use_context": True}

    # Food order. A bare dish name with no verb still counts as an order attempt.
    items = _order_items(t)
    if items:
        first = items[0]
        return {"intent": "order_item", "text": text, "items": items,
                "dish": first["dish"], "quantity": first["quantity"],
                "size": first["size"]}

    return {"intent": "unknown", "text": text}
