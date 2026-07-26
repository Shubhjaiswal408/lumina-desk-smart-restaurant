"""Menu database for Lumina Desk — single source of truth for prices,
ingredients, and allergens. Allergy answers are grounded ONLY in this data.

Each dish: name, price (INR), category, veg/vegan flags, full ingredient list,
allergen tags, and distinctive aliases for matching spoken orders.
allergen tags used: gluten, dairy, soy, nuts, peanut, egg
"""

MENU = [
    # ---------- Starters ----------
    {
        "name": "Paneer Tikka", "price": 280, "category": "Starter",
        "veg": True, "vegan": False,
        "ingredients": ["cottage cheese (paneer)", "hung yogurt", "ginger-garlic paste",
                        "red chili powder", "garam masala", "bell pepper", "onion", "mustard oil"],
        "allergens": ["dairy"],
        "aliases": ["paneer tikka", "paneer tika"],
    },
    {
        "name": "Chicken Tikka", "price": 320, "category": "Starter",
        "veg": False, "vegan": False,
        "ingredients": ["boneless chicken", "hung yogurt", "ginger-garlic paste",
                        "red chili", "garam masala", "lemon", "chaat masala"],
        "allergens": ["dairy"],
        "aliases": ["chicken tikka", "chicken tika"],
    },
    {
        "name": "Veg Spring Rolls", "price": 190, "category": "Starter",
        "veg": True, "vegan": True,
        "ingredients": ["cabbage", "carrot", "bean sprouts", "spring onion",
                        "refined flour wrapper", "soy sauce", "black pepper"],
        "allergens": ["gluten", "soy"],
        "aliases": ["spring rolls", "spring roll", "veg spring rolls"],
    },
    {
        "name": "Gobi Manchurian", "price": 210, "category": "Starter",
        "veg": True, "vegan": True,
        "ingredients": ["cauliflower", "cornflour", "refined flour", "soy sauce",
                        "garlic", "ginger", "green chili", "spring onion"],
        "allergens": ["gluten", "soy"],
        "aliases": ["gobi manchurian", "manchurian", "cauliflower manchurian"],
    },

    # ---------- Indian Mains ----------
    {
        "name": "Paneer Butter Masala", "price": 300, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["cottage cheese (paneer)", "tomato puree", "butter", "fresh cream",
                        "cashew paste", "kasuri methi", "garam masala", "sugar"],
        "allergens": ["dairy", "nuts"],
        "aliases": ["paneer butter masala", "butter paneer", "paneer makhani"],
    },
    {
        "name": "Butter Chicken", "price": 360, "category": "Main",
        "veg": False, "vegan": False,
        "ingredients": ["tandoori chicken", "tomato gravy", "butter", "fresh cream",
                        "cashew paste", "fenugreek", "garam masala", "honey"],
        "allergens": ["dairy", "nuts"],
        "aliases": ["butter chicken", "murgh makhani"],
    },
    {
        "name": "Dal Makhani", "price": 260, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["black lentils (urad)", "kidney beans", "butter", "fresh cream",
                        "tomato", "ginger-garlic", "garam masala"],
        "allergens": ["dairy"],
        "aliases": ["dal makhani", "dal makhni", "black dal"],
    },
    {
        "name": "Chicken Biryani", "price": 350, "category": "Main",
        "veg": False, "vegan": False,
        "ingredients": ["basmati rice", "chicken", "fried onions", "yogurt", "saffron",
                        "mint", "whole spices (bay leaf, cardamom, cloves)", "ghee"],
        "allergens": ["dairy"],
        "aliases": ["chicken biryani", "biryani", "biriyani", "chicken biriyani"],
    },
    {
        "name": "Chole Bhature", "price": 220, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["chickpeas", "onion", "tomato", "chole masala", "ginger",
                        "refined flour (maida)", "yogurt", "fried bhatura bread"],
        "allergens": ["gluten", "dairy"],
        "aliases": ["chole bhature", "chana bhature", "chole bature"],
    },
    {
        "name": "Masala Dosa", "price": 160, "category": "Main",
        "veg": True, "vegan": True,
        "ingredients": ["fermented rice & lentil batter", "potato masala filling",
                        "mustard seeds", "curry leaves", "served with sambar and coconut chutney"],
        "allergens": [],
        "aliases": ["masala dosa", "dosa"],
    },

    # ---------- Continental / Chinese ----------
    {
        "name": "Margherita Pizza", "price": 320, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["wheat pizza base", "tomato sauce", "mozzarella cheese",
                        "fresh basil", "olive oil", "oregano"],
        "allergens": ["gluten", "dairy"],
        "aliases": ["margherita pizza", "margherita", "margarita", "cheese pizza", "pizza"],
    },
    {
        "name": "Veg Hakka Noodles", "price": 220, "category": "Main",
        "veg": True, "vegan": True,
        "ingredients": ["wheat noodles", "cabbage", "carrot", "capsicum",
                        "spring onion", "soy sauce", "vinegar", "garlic"],
        "allergens": ["gluten", "soy"],
        "aliases": ["hakka noodles", "veg noodles", "noodles"],
    },
    {
        "name": "Veg Fried Rice", "price": 200, "category": "Main",
        "veg": True, "vegan": True,
        "ingredients": ["basmati rice", "carrot", "beans", "capsicum",
                        "spring onion", "soy sauce", "black pepper"],
        "allergens": ["soy"],
        "aliases": ["fried rice", "veg fried rice"],
    },
    {
        "name": "Paneer Wrap", "price": 180, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["whole wheat wrap", "grilled paneer", "onion", "capsicum",
                        "mint mayonnaise", "chaat masala"],
        "allergens": ["gluten", "dairy", "egg"],
        "aliases": ["paneer wrap", "paneer roll", "wrap"],
    },

    # ---------- Breads & Rice ----------
    {
        "name": "Butter Naan", "price": 60, "category": "Bread",
        "veg": True, "vegan": False,
        "ingredients": ["refined flour", "yogurt", "milk", "butter", "baking soda"],
        "allergens": ["gluten", "dairy"],
        "aliases": ["butter naan", "naan"],
    },
    {
        "name": "Garlic Naan", "price": 80, "category": "Bread",
        "veg": True, "vegan": False,
        "ingredients": ["refined flour", "yogurt", "garlic", "butter", "coriander"],
        "allergens": ["gluten", "dairy"],
        "aliases": ["garlic naan"],
    },
    {
        "name": "Jeera Rice", "price": 150, "category": "Rice",
        "veg": True, "vegan": False,
        "ingredients": ["basmati rice", "cumin seeds", "ghee", "bay leaf"],
        "allergens": ["dairy"],
        "aliases": ["jeera rice", "cumin rice"],
    },

    # ---------- Desserts ----------
    {
        "name": "Gulab Jamun", "price": 110, "category": "Dessert",
        "veg": True, "vegan": False,
        "ingredients": ["milk solids (khoya)", "refined flour", "sugar syrup",
                        "cardamom", "rose water", "ghee"],
        "allergens": ["dairy", "gluten"],
        "aliases": ["gulab jamun", "gulab jamoon"],
    },
    {
        "name": "Gajar Halwa", "price": 130, "category": "Dessert",
        "veg": True, "vegan": False,
        "ingredients": ["carrot", "full-fat milk", "ghee", "sugar", "cashew", "almonds", "cardamom"],
        "allergens": ["dairy", "nuts"],
        "aliases": ["gajar halwa", "carrot halwa", "halwa"],
    },
    {
        "name": "Peanut Chikki", "price": 90, "category": "Dessert",
        "veg": True, "vegan": True,
        "ingredients": ["roasted peanuts", "jaggery"],
        "allergens": ["peanut"],
        "aliases": ["peanut chikki", "chikki", "peanut dessert"],
    },

    # ---------- Beverages ----------
    {
        "name": "Masala Chai", "price": 50, "category": "Beverage",
        "veg": True, "vegan": False,
        "ingredients": ["black tea", "milk", "ginger", "cardamom", "sugar"],
        "allergens": ["dairy"],
        "aliases": ["masala chai", "chai", "tea", "masala tea"],
    },
    {
        "name": "Sweet Lassi", "price": 80, "category": "Beverage",
        "veg": True, "vegan": False,
        "ingredients": ["yogurt", "sugar", "cardamom", "saffron"],
        "allergens": ["dairy"],
        "aliases": ["sweet lassi", "lassi"],
    },
    {
        "name": "Fresh Lime Soda", "price": 70, "category": "Beverage",
        "veg": True, "vegan": True,
        "ingredients": ["fresh lime", "soda water", "sugar", "black salt", "mint"],
        "allergens": [],
        "aliases": ["lime soda", "fresh lime soda", "nimbu soda"],
    },

    # ---------- more Starters ----------
    {
        "name": "Chilli Paneer", "price": 240, "category": "Starter",
        "veg": True, "vegan": False,
        "ingredients": ["paneer", "capsicum", "onion", "soy sauce", "chilli", "cornflour"],
        "allergens": ["dairy", "gluten", "soy"], "aliases": ["chilli paneer", "chili paneer"],
    },
    {
        "name": "Hara Bhara Kabab", "price": 200, "category": "Starter",
        "veg": True, "vegan": False,
        "ingredients": ["spinach", "green peas", "potato", "paneer", "spices", "breadcrumbs"],
        "allergens": ["gluten", "dairy"], "aliases": ["hara bhara kabab", "hara bhara kebab"],
    },
    # ---------- more Mains ----------
    {
        "name": "Kadai Paneer", "price": 300, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["paneer", "capsicum", "onion", "tomato", "kadai masala", "cream"],
        "allergens": ["dairy"], "aliases": ["kadai paneer", "karahi paneer"],
    },
    {
        "name": "Palak Paneer", "price": 290, "category": "Main",
        "veg": True, "vegan": False,
        "ingredients": ["spinach", "paneer", "onion", "tomato", "garlic", "cream", "spices"],
        "allergens": ["dairy"], "aliases": ["palak paneer", "spinach paneer"],
    },
    {
        "name": "Mutton Rogan Josh", "price": 420, "category": "Main",
        "veg": False, "vegan": False,
        "ingredients": ["mutton", "yogurt", "onion", "kashmiri chilli", "aromatic spices"],
        "allergens": ["dairy"], "aliases": ["mutton rogan josh", "rogan josh", "mutton curry"],
    },
    # ---------- more Breads ----------
    {
        "name": "Tandoori Roti", "price": 40, "category": "Bread",
        "veg": True, "vegan": True,
        "ingredients": ["whole wheat flour", "water", "salt"],
        "allergens": ["gluten"], "aliases": ["tandoori roti", "roti"],
    },
    {
        "name": "Laccha Paratha", "price": 70, "category": "Bread",
        "veg": True, "vegan": False,
        "ingredients": ["refined flour", "ghee", "salt"],
        "allergens": ["gluten", "dairy"], "aliases": ["laccha paratha", "lachha paratha", "paratha"],
    },
    # ---------- more Rice ----------
    {
        "name": "Veg Pulao", "price": 190, "category": "Rice",
        "veg": True, "vegan": False,
        "ingredients": ["basmati rice", "mixed vegetables", "whole spices", "ghee"],
        "allergens": ["dairy"], "aliases": ["veg pulao", "pulao", "pulav"],
    },
    # ---------- more Desserts ----------
    {
        "name": "Rasmalai", "price": 140, "category": "Dessert",
        "veg": True, "vegan": False,
        "ingredients": ["chhena (milk curd)", "thickened milk", "sugar", "cardamom", "pistachio"],
        "allergens": ["dairy", "nuts"], "aliases": ["rasmalai", "ras malai"],
    },
    {
        "name": "Kulfi", "price": 100, "category": "Dessert",
        "veg": True, "vegan": False,
        "ingredients": ["thickened milk", "sugar", "cardamom", "pistachio", "almonds"],
        "allergens": ["dairy", "nuts"], "aliases": ["kulfi", "malai kulfi"],
    },
    # ---------- more Beverages ----------
    {
        "name": "Mango Lassi", "price": 90, "category": "Beverage",
        "veg": True, "vegan": False,
        "ingredients": ["yogurt", "mango pulp", "sugar", "cardamom"],
        "allergens": ["dairy"], "aliases": ["mango lassi"],
    },
    {
        "name": "Cold Coffee", "price": 110, "category": "Beverage",
        "veg": True, "vegan": False,
        "ingredients": ["milk", "coffee", "sugar", "ice cream"],
        "allergens": ["dairy"], "aliases": ["cold coffee", "iced coffee"],
    },
]

# Approximate kitchen prep time per dish (minutes). Used for the "ready in ~X"
# estimate on the display. Kitchen parallelises, so the order estimate is the
# slowest item plus a small allowance per additional line (see session.py).
PREP_MIN = {
    "Paneer Tikka": 15, "Chicken Tikka": 18, "Veg Spring Rolls": 12,
    "Gobi Manchurian": 15, "Paneer Butter Masala": 20, "Butter Chicken": 22,
    "Dal Makhani": 18, "Chicken Biryani": 30, "Chole Bhature": 20,
    "Masala Dosa": 12, "Margherita Pizza": 18, "Veg Hakka Noodles": 15,
    "Veg Fried Rice": 15, "Paneer Wrap": 12, "Butter Naan": 8, "Garlic Naan": 8,
    "Jeera Rice": 12, "Gulab Jamun": 4, "Gajar Halwa": 8, "Peanut Chikki": 2,
    "Masala Chai": 6, "Sweet Lassi": 4, "Fresh Lime Soda": 3,
    "Chilli Paneer": 18, "Hara Bhara Kabab": 15, "Kadai Paneer": 20, "Palak Paneer": 20,
    "Mutton Rogan Josh": 35, "Tandoori Roti": 8, "Laccha Paratha": 10, "Veg Pulao": 18,
    "Rasmalai": 4, "Kulfi": 3, "Mango Lassi": 4, "Cold Coffee": 6,
}


def prep_minutes(dish: dict) -> int:
    return dish.get("prep") or PREP_MIN.get(dish["name"], 15)


# Non-food items a guest can request (routed to staff, not the kitchen cart).
SERVICE_ITEMS = ["water", "fork", "spoon", "knife", "napkin", "tissue", "plate", "glass", "menu card"]

TAX_RATE = 0.05  # 5% GST
# "inclusive": menu prices already include GST — the guest pays exactly the menu
#              price (₹2 dish = ₹2 due). The tax portion is shown for the record.
# "exclusive": GST is added on top (₹2 dish = ₹2.10 due).
# "none":      no tax at all.
TAX_MODE = "inclusive"

# Dishes the house suggests when a guest asks for a recommendation.
CHEF_SPECIALS = ["Paneer Butter Masala", "Butter Chicken", "Chicken Biryani", "Masala Dosa"]

# Categories in serving order for menu read-outs.
CATEGORIES = ["Starter", "Main", "Bread", "Rice", "Dessert", "Beverage"]


def _alias_matches(text: str, alias: str) -> bool:
    """Whole-phrase match so 'masala' alone doesn't hijack 'Masala Dosa'."""
    import re
    return re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", text) is not None


def find_dish(text: str):
    """Return the menu dish whose longest alias/name appears in `text`, else None."""
    t = text.lower()
    best, best_len = None, 0
    for dish in all_dishes():
        for alias in [dish["name"].lower()] + dish["aliases"]:
            if _alias_matches(t, alias) and len(alias) > best_len:
                best, best_len = dish, len(alias)
    return best


def find_service_item(text: str):
    t = text.lower()
    for item in SERVICE_ITEMS:
        if _alias_matches(t, item):
            return item
    return None


def by_category(category: str):
    return [d for d in all_dishes() if d["category"] == category]


CATEGORY_ALIASES = {
    "starter": "Starter", "starters": "Starter", "appetizer": "Starter",
    "appetizers": "Starter", "snack": "Starter", "snacks": "Starter", "tikka": "Starter",
    "main": "Main", "mains": "Main", "main course": "Main", "mains course": "Main",
    "curry": "Main", "curries": "Main", "sabzi": "Main",
    "bread": "Bread", "breads": "Bread", "naan": "Bread", "roti": "Bread", "paratha": "Bread",
    "rice": "Rice", "biryani section": "Rice",
    "dessert": "Dessert", "desserts": "Dessert", "sweet": "Dessert", "sweets": "Dessert", "mithai": "Dessert",
    "beverage": "Beverage", "beverages": "Beverage", "drink": "Beverage",
    "drinks": "Beverage", "cold drink": "Beverage",
}


def find_category(text: str):
    """Return the canonical category if the guest named one, else None."""
    t = text.lower()
    for alias, cat in sorted(CATEGORY_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if _alias_matches(t, alias):
            return cat
    return None


# --- Live admin overrides (price / availability) from the KDS SQLite DB ---
import os as _os
import sqlite3 as _sqlite3
import time as _time

_OV_DB = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "lumina.db")
_ov_cache = {"data": {}, "t": 0.0}


def _overrides() -> dict:
    """Read menu overrides, cached 8s so the voice app picks up admin edits fast
    without hitting SQLite every order."""
    if _time.time() - _ov_cache["t"] > 8:
        data = {}
        try:
            c = _sqlite3.connect(_OV_DB)
            for name, price, avail in c.execute("SELECT name,price,available FROM menu_override"):
                data[name] = (price, bool(avail))
            c.close()
        except Exception:
            pass
        _ov_cache["data"], _ov_cache["t"] = data, _time.time()
    return _ov_cache["data"]


def tax_config():
    """(mode, rate) from Settings, falling back to the constants above."""
    try:
        import settings
        return settings.get("tax_mode", TAX_MODE), float(settings.get("tax_rate", TAX_RATE * 100)) / 100
    except Exception:
        return TAX_MODE, TAX_RATE


def effective_price(dish: dict) -> int:
    o = _overrides().get(dish["name"])
    return int(o[0]) if o and o[0] is not None else dish["price"]


def is_available(dish: dict) -> bool:
    o = _overrides().get(dish["name"])
    return o[1] if o else True


_cd_cache = {"data": [], "t": 0.0}


def _custom_dishes() -> list:
    """Admin-added dishes (from the KDS), so voice can order them too. Cached 8s."""
    if _time.time() - _cd_cache["t"] > 8:
        import json as _json
        rows = []
        try:
            c = _sqlite3.connect(_OV_DB)
            for name, cat, price, veg, allergens, prep, ing in c.execute(
                    "SELECT name,category,price,veg,allergens,prep,"
                    "COALESCE(ingredients,'[]') FROM custom_dish"):
                rows.append({"name": name, "category": cat, "price": int(price),
                             "veg": bool(veg), "vegan": False,
                             "ingredients": _json.loads(ing or "[]"),
                             "allergens": _json.loads(allergens or "[]"),
                             "prep": prep, "aliases": [name.lower()], "custom": True})
            c.close()
        except Exception:
            pass
        _cd_cache["data"], _cd_cache["t"] = rows, _time.time()
    return _cd_cache["data"]


def all_dishes() -> list:
    """Base menu + admin-added dishes — the full orderable set."""
    return MENU + _custom_dishes()
