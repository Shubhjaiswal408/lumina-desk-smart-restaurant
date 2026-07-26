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


def _quantity(text: str) -> int:
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return max(1, int(m.group(1)))
    for word, n in _NUM_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return n
    return 1


def _split_ways(text: str) -> int:
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return max(2, int(m.group(1)))
    for word, n in _NUM_WORDS.items():
        if re.search(rf"\b{word}\b", text) and n >= 2:
            return n
    return 2


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

    # End of conversation — short, explicit closings only.
    stripped = t.strip(" .!,")
    if stripped in _END_PHRASES or has("that's all", "thats all", "nothing else",
                                       "that will be all", "we're done", "were done"):
        return {"intent": "end_conversation", "text": text}

    # Payment
    if has("pay", "payment", "upi", "qr code", "scan"):
        return {"intent": "pay", "text": text}

    # Recommendation
    if has("recommend", "suggest", "special", "what should i", "what's good",
           "whats good", "popular", "famous", "signature", "best dish", "your best"):
        return {"intent": "recommend", "text": text}

    # Split bill — any split/divide is a split intent.
    if has("split", "divide"):
        return {"intent": "split_bill", "text": text, "ways": _split_ways(t)}

    # Bill
    if has("bill", "total", "how much", "what do i owe", "check please", "the check"):
        return {"intent": "check_bill", "text": text}

    # Allergy questions
    if has("allerg", "peanut", "gluten", "dairy", "lactose", "nut", "soy", "safe to eat"):
        return {"intent": "ask_allergen", "text": text, "dish": menu.find_dish(t)}

    # Ingredient / dietary questions
    if has("ingredient", "what's in", "whats in", "what is in", "made of", "made with",
           "contain", "vegetarian", "veg", "vegan", "non veg", "nonveg"):
        return {"intent": "ask_ingredient", "text": text, "dish": menu.find_dish(t)}

    # Menu
    if has("menu", "what do you have", "what can i", "options", "specials", "recommend", "suggest"):
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
    if (menu.find_dish(t) is None and
            has("add it", "add that", "add this", "order it", "order that",
                "have it", "get it", "add one", "yes add", "sure add", "yes please add",
                "add to my order", "put it in", "i'll take it", "ill take it")):
        return {"intent": "order_item", "text": text, "dish": None,
                "quantity": _quantity(t), "use_context": True}

    # Food order
    dish = menu.find_dish(t)
    if dish and has("order", "want", "get", "bring", "have", "give", "add", "like", "i'll"):
        return {"intent": "order_item", "text": text, "dish": dish, "quantity": _quantity(t)}
    # Bare dish name with no verb — still treat as an order attempt
    if dish:
        return {"intent": "order_item", "text": text, "dish": dish, "quantity": _quantity(t)}

    return {"intent": "unknown", "text": text}
