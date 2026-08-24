"""LLM understanding for Lumina — now the PRIMARY brain.

The model sees the conversation history, the current cart, and the real menu,
so it handles natural speech, corrections ("no, I said pepperoni"), negation
("I never asked for a pizza"), pronouns ("add it"), and off-menu requests
(pepperoni pizza isn't on the menu -> it says so instead of forcing a match).

Backends, fastest first: Groq cloud (openai/gpt-oss-20b, ~0.9 s) when online,
local LFM2-700M via Ollama (~6-9 s) offline. Offline, rules (intents.py) run
FIRST because they are instant and correct for almost every real turn; the local
model only handles what they can't parse.

Contract that never changes: the LLM classifies + phrases, but it NEVER decides
prices, bill totals, or allergen facts. Those come from menu.py / session.py via
dialog.py. We ground every dish name the model returns against the real menu.
"""
import json
import re

import requests

import config
import net
import menu
import settings

OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_MODEL = "hf.co/LiquidAI/LFM2-700M-GGUF"

INTENTS = [
    "order", "remove", "replace", "clear_cart", "check_bill", "split_bill",
    "ask_price", "ask_ingredient", "ask_allergen", "recommend", "show_menu",
    "show_category", "request_item", "call_staff", "pay", "unavailable",
    "smalltalk", "end",
]

_SERVICE_NAMES = ", ".join(menu.SERVICE_ITEMS)
_CATEGORIES = ", ".join(menu.CATEGORIES)


def _menu_names() -> str:
    """Built fresh each call so dishes added in the admin are instantly known."""
    return ", ".join(d["name"] for d in menu.all_dishes())


def _system_prompt(session) -> str:
    if session.cart:
        cart = "; ".join(f'{l["qty"]}x {l["dish"]["name"]}' for l in session.cart)
    else:
        cart = "(empty)"
    return f"""You are Lumina, the voice assistant at a busy, casual, pure-veg
pizza place. Think friendly counter staff who knows the menu cold — quick,
helpful, a bit warm. NOT a fine-dining waiter: no "certainly sir", no speeches.

Voice & style for "reply":
- Sound like a real person, never a template. Vary your wording; don't repeat
  the same phrase twice in a row.
- SHORT — usually one sentence, often just a few words ("Done!", "Good pick.").
  This is spoken aloud, so no lists, no markdown, no emoji.
- Everything here is vegetarian, so never call a dish out as veg — it's a given.
- After a dish is added you MAY suggest ONE thing that genuinely goes with it
  ("Garlic bread goes great with that") — once per dish, and never if they sound
  like they're finishing up.
- If you didn't catch it, ask a short friendly question instead of guessing.

MENU (these are the ONLY dishes that exist): {_menu_names()}.
Menu categories: {_CATEGORIES}.
Service items (non-food): {_SERVICE_NAMES}.
Current order in the cart: {cart}.

Reply ONLY with a compact JSON object with these keys:
- "intent": one of {INTENTS}
- "items": for an order, a list of
  {{"dish": exact menu name, "quantity": int, "size": <option or "">}}.
  Use this for one OR several dishes in one sentence. Empty list otherwise.
  Pizzas come in Regular / Medium / Large, burgers in Regular / Veeba Cheese
  Blend / Amul Cheese Slice / Cheese Ring, momos in Steam / Pan Fry / Deep Fry /
  Gravy, fries in Medium / Large. Set "size" only if the guest said one.
- "dish": the EXACT menu dish name involved (for non-order intents), or ""
- "remove_dish": exact menu dish name to remove (for remove/replace), or ""
- "category": if the guest asks about a section (starters, mains, breads, rice,
  desserts, beverages/drinks), the category name; else ""
- "item": service item name (for a service request), or ""
- "quantity": integer, default 1
- "ways": integer for splitting the bill, else 0
- "reply": one short, hospitable sentence to say to the guest

CRITICAL RULES — follow exactly:
- NEVER invent, assume, or suggest-into-the-cart a dish. Only put a dish in
  "items"/"remove_dish" if the guest EXPLICITLY named it in their message (or
  clearly referred to one just discussed, e.g. "add it").
- If the guest wants to order but names NO dish (e.g. "I'd like to order",
  "what do you have"), use intent "show_menu" with items = [] and ask what they'd
  like. Do NOT add anything.
- Only use "remove"/"replace" when the guest clearly asks to remove/change a
  SPECIFIC item. Vague or filler input ("I'm sorry", "um", "wait", "hmm",
  "never mind") → intent "smalltalk", NO cart change, a gentle reply.
- Something not on the menu (e.g. "pepperoni pizza") → intent "unavailable";
  say we don't have it and suggest the closest real dish. Never substitute.
- "clear my order / cancel everything / start over / empty the cart" → intent
  "clear_cart".
- Asking for a NON-FOOD item (water, napkin, tissue, spoon, fork, knife, plate,
  glass, menu card) → intent "request_item" with "item" set. Staff are alerted.
- Asking for a person / complaint / "call the waiter" → intent "call_staff".
- Asking about a section ("what's in starters?", "show me the desserts", "what
  drinks do you have?") → intent "show_category" with "category" set. The system
  lists the dishes, so keep your "reply" a brief lead-in.
- Never state prices, totals, or allergen facts yourself — the system adds those.
- Keep "reply" under 25 words, calm and gracious.
- The guest may speak ANY language (Hindi, Spanish, Tamil, etc.). Understand it,
  and write "reply" in that SAME language. But "dish"/"items"/"remove_dish" must
  ALWAYS be the EXACT English menu names — map translated or transliterated dish
  names to the menu (e.g. "बटर नान" / "butter naan" -> "Butter Naan").

Examples:
- "I'd like to place an order" -> {{"intent":"show_menu","items":[],"reply":"Of course — what would you like? I can suggest something if you'd like."}}
- "add two butter naan" -> {{"intent":"order","items":[{{"dish":"Butter Naan","quantity":2}}]}}
- "I'm sorry" -> {{"intent":"smalltalk","items":[],"reply":"No need to apologise! What can I get you?"}}
- "actually remove the biryani" -> {{"intent":"remove","remove_dish":"Chicken Biryani"}}"""


def _clean_reply(reply) -> str:
    """Drop a reply that is obviously the prompt template rather than speech.

    The small local model has literally answered "<one short friendly sentence>"
    — spoken aloud, to a guest. An empty string here makes dialog.py fall back to
    its own deterministic wording, which is always sayable.
    """
    r = str(reply or "").strip()
    if not r:
        return ""
    if "<" in r and ">" in r:          # an unfilled placeholder
        return ""
    if r.startswith("{") or r.startswith("["):   # raw JSON leaked through
        return ""
    return r


def _normalize(raw: dict, text: str, session=None) -> dict:
    intent = str(raw.get("intent", "smalltalk")).strip()
    if intent not in INTENTS:
        intent = "smalltalk"
    # Multi-item orders: ground each dish; drop any not on the menu.
    items = []
    for it in raw.get("items", []) or []:
        d = menu.find_dish(str(it.get("dish", "") or ""))
        if d:
            try:
                q = max(1, int(it.get("quantity", 1)))
            except (TypeError, ValueError):
                q = 1
            # Trust an explicit size, else pick one out of what the guest said.
            sz = str(it.get("size", "") or "")
            sz = sz if sz in (d.get("sizes") or {}) else menu.find_size(text, d)
            items.append({"dish": d, "quantity": q, "size": sz})

    # Ground dish names against the real menu (no free-text fallback, so
    # "pepperoni pizza" does NOT collapse to Margherita).
    dish = menu.find_dish(str(raw.get("dish", "") or ""))
    remove_dish = menu.find_dish(str(raw.get("remove_dish", "") or ""))
    category = menu.find_category(str(raw.get("category", "") or "")) or menu.find_category(text)
    item = str(raw.get("item", "") or "") or menu.find_service_item(text)
    try:
        qty = max(1, int(raw.get("quantity", 1)))
    except (TypeError, ValueError):
        qty = 1
    try:
        ways = int(raw.get("ways", 0))
    except (TypeError, ValueError):
        ways = 0

    # SAFETY: questions about what's in a dish MUST be answered from menu data,
    # never improvised by the model. If the guest asks an ingredient/allergen
    # question about a known dish, force the grounded intent.
    _ING_Q = r"(what'?s in|whats in|what is in|ingredient|made of|made with|contain|" \
             r"does it have|is there any|allerg|gluten|dairy|lactose|nuts?|peanut|soy|egg)"
    if re.search(_ING_Q, (text or "").lower()):
        d = dish or menu.find_dish(text or "")
        if d:
            allergy = re.search(r"(allerg|gluten|dairy|lactose|nuts?|peanut|soy|egg)",
                                (text or "").lower())
            intent = "ask_allergen" if allergy else "ask_ingredient"
            dish = d

    # Anti-hallucination guard: never add/remove a dish the guest didn't name.
    # Only for Latin-script input — for other scripts (Hindi, etc.) the English
    # menu name can't literally appear, so we trust the LLM's extraction there.
    low = (text or "").lower()
    # Did the guest actually say a number? ("remove one naan" vs "remove the naan")
    qty_explicit = bool(re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an|single)\b", low))
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(1, len(text))
    guard_on = ascii_ratio > 0.7
    has_ref = bool(re.search(r"\b(it|that|this|them|those|these|same|again|usual|one|ones)\b", low))

    def _named(d):
        return d is not None and (
            menu._alias_matches(low, d["name"].lower())
            or any(menu._alias_matches(low, a) for a in d["aliases"]))

    def _on_the_table(d):
        """A pronoun can only point at something already in play. "Make it the
        cheese ones" is a reference, not a licence to pick any dish on the menu
        — the local model did exactly that and removed a garlic bread nobody had
        ordered."""
        if d is None or session is None:
            return False
        if getattr(session, "last_dish", None) and d["name"] == session.last_dish["name"]:
            return True
        return any(l["dish"]["name"] == d["name"] for l in getattr(session, "cart", []))

    def _allowed(d):
        return _named(d) or (has_ref and _on_the_table(d))

    if guard_on and intent == "order":
        items = [x for x in items if _allowed(x["dish"])]
        if not _allowed(dish):
            dish = None
        if not items and not dish and not has_ref:
            intent = "show_menu"   # wanted to order but named nothing -> ask
    if guard_on and intent in ("remove", "replace"):
        if not _allowed(remove_dish):
            remove_dish = None
        if intent == "remove" and remove_dish is None:
            intent = "smalltalk"   # vague input -> don't touch the cart

    return {
        "intent": intent,
        "text": text,
        "items": items,
        "dish": dish,
        "remove_dish": remove_dish,
        "category": category,
        "item": item,
        "quantity": qty,
        "qty_explicit": qty_explicit,
        "ways": ways if ways >= 2 else 2,
        "reply": _clean_reply(raw.get("reply")),
        "llm": True,
    }


def _messages(text: str, session):
    return [{"role": "system", "content": _system_prompt(session)}] + \
        session.history + [{"role": "user", "content": text}]


def _via_groq(text: str, session) -> dict:
    payload = {
        "model": config.GROQ_LLM_MODEL,
        "messages": _messages(text, session),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": config.GROQ_LLM_MAX_TOKENS,
        "reasoning_effort": config.GROQ_REASONING_EFFORT,
    }
    r = net.session().post(
        config.GROQ_CHAT_URL,
        headers={"Authorization": f"Bearer {settings.groq_key()}"},
        json=payload, timeout=12,
    )
    r.raise_for_status()
    raw = json.loads(r.json()["choices"][0]["message"]["content"])
    return _normalize(raw, text, session)


def _local_prompt(session) -> str:
    """A much shorter prompt for the on-device model.

    LFM2-700M on a Pi CPU chokes on the full persona prompt (it's ~1k tokens),
    so offline mode gets a compact instruction set. Accuracy is lower than the
    cloud model — that's the honest trade for working without internet.
    """
    cart = "; ".join(f'{l["qty"]}x {l["dish"]["name"]}' for l in session.cart) or "empty"
    return (
        "You are Lumina, a restaurant waiter. Reply ONLY with compact JSON: "
        '{"intent":..., "items":[{"dish":<exact menu name>,"quantity":<int>}], '
        '"dish":"", "item":"", "ways":0, "reply":"<one short friendly sentence>"}\n'
        f"intent is one of: {', '.join(INTENTS)}.\n"
        f"MENU: {_menu_names()}.\n"
        f"Cart: {cart}.\n"
        "Only use dishes from MENU. Never invent dishes or state prices."
    )


def _via_local(text: str, session) -> dict:
    msgs = [{"role": "system", "content": _local_prompt(session)}]
    msgs += session.history[-4:]                  # short memory keeps it quick
    msgs.append({"role": "user", "content": text})
    payload = {
        "model": LOCAL_MODEL,
        "messages": msgs,
        "format": "json", "stream": False, "keep_alive": "30m",
        "options": {"temperature": 0.2, "num_predict": 120},
    }
    # A guest will not wait a minute. If the local model is that slow the
    # caller falls back to rules, which is a better answer than silence.
    r = requests.post(OLLAMA_URL, json=payload, timeout=20)
    r.raise_for_status()
    raw = json.loads(r.json()["message"]["content"])
    return _normalize(raw, text, session)


def warm_local():
    """Load the offline model into RAM so the first guest isn't kept waiting."""
    try:
        requests.post(OLLAMA_URL, timeout=120, json={
            "model": LOCAL_MODEL, "messages": [{"role": "user", "content": "hi"}],
            "stream": False, "keep_alive": "30m", "options": {"num_predict": 1}})
        return True
    except Exception as e:
        print(f"  (could not warm local model: {e})", flush=True)
        return False


def understand(text: str, session, rules: dict = None) -> dict:
    """Groq first (fast, accurate), then rules, then the local model.

    `rules` is the caller's already-parsed rule result. When the cloud fails —
    a rate limit, a dropped line — reaching for the 700M local model costs the
    guest ~9 seconds at the table. If the rules understood the sentence, they
    are instant and just as correct, so they go first. The local model is for
    phrasing the rules genuinely can't parse.

    In offline mode `settings.groq_key()` returns "" so we never touch the
    network — everything runs on the Pi.
    """
    online = bool(settings.groq_key())
    if online:
        try:
            return _via_groq(text, session)
        except Exception as e:
            print(f"  (Groq NLU failed: {e})", flush=True)
            if rules and rules["intent"] not in ("unknown", "smalltalk"):
                print("  (answering from rules — instant)", flush=True)
                return rules
    try:
        return _via_local(text, session)
    except Exception as e:
        # A 700M model sometimes emits JSON it can't finish. Losing the turn over
        # that is worse than answering from rules, which handle the common asks.
        print(f"  (local NLU failed, using rules: {e})", flush=True)
        import intents
        return rules or intents.parse_intent(text)


def translate(text: str, language_name: str) -> str:
    """Translate a (fact-bearing) reply into the guest's language, preserving
    numbers and dish names. Groq only; returns the original on any failure."""
    if not settings.groq_key() or not text:
        return text
    try:
        payload = {
            "model": config.GROQ_LLM_MODEL,
            "messages": [
                {"role": "system", "content":
                    f"Translate the user's text into {language_name}. Keep all numbers, "
                    f"prices and dish names exactly. Reply with ONLY the translation."},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "max_tokens": config.GROQ_LLM_MAX_TOKENS,
            "reasoning_effort": config.GROQ_REASONING_EFFORT,
        }
        r = net.session().post(config.GROQ_CHAT_URL,
                          headers={"Authorization": f"Bearer {settings.groq_key()}"},
                          json=payload, timeout=10)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  (translate failed: {e})", flush=True)
        return text


def is_available() -> bool:
    if settings.groq_key():
        return True
    try:
        requests.get("http://localhost:11434/api/version", timeout=2).raise_for_status()
        return True
    except Exception:
        return False
