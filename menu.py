"""Menu database for Lumina Desk — Aunty No-Z Pizza, Ghodasar.

Single source of truth for prices, ingredients and allergens. Allergy answers
are grounded ONLY in this data, never improvised by the model.

The whole outlet is **pure vegetarian**, so every dish here is veg.

Sizes: pizzas come in Regular 6" / Medium 9" / Large 12", burgers in four
cheese variants, momos in four cooking styles, fries in two sizes. Those live in
`dish["sizes"]`; `dish["price"]` is the default (first/smallest) option.

allergen tags: gluten, dairy, soy, nuts
"""

# ---------------------------------------------------------------- builders --

def _d(name, price, category, ingredients, allergens=(), aliases=(),
       sizes=None, prep=12, desc=""):
    """One menu entry. `sizes` maps an option name -> price."""
    return {
        "name": name, "price": int(price), "category": category,
        "veg": True, "vegan": False,          # pure-veg outlet; most have dairy
        "ingredients": list(ingredients), "allergens": list(allergens),
        "aliases": [a.lower() for a in aliases], "prep": prep,
        "sizes": sizes or {}, "desc": desc,
    }


# Standard bases so descriptions stay short and consistent.
_BASE = ["pizza base", "pizza sauce", "mozzarella cheese"]
_PZ = ["gluten", "dairy"]


def _pizza(name, r, m, l, ings, aliases=(), allergens=None, desc="", cat="Pizza"):
    return _d(name, r, cat, _BASE + list(ings), allergens or _PZ, aliases,
              sizes={"Regular": r, "Medium": m, "Large": l}, prep=15, desc=desc)


MENU = [
    # ------------------------------------------------------- VALUE PIZZA ----
    _pizza("Margherita", 89, 220, 270, [],          # base already has the cheese
           # Whisper spells this a dozen ways; each one it gets wrong is an order lost.
           ["margherita", "margarita", "margareta", "margaretta", "margharita",
            "margrita", "marguerita", "margherit", "plain pizza", "plain cheese pizza"],
           desc="Margherita Magic, 100% Amul mozzarella"),

    _pizza("Schezwan Margherita", 110, 230, 290, ["schezwan sauce"], ["schezwan margherita"]),
    _pizza("Peri-Peri Margherita", 110, 230, 290, ["peri-peri seasoning"], ["peri peri margherita"]),
    _pizza("Tandoori Margherita", 110, 230, 290, ["tandoori sauce"], ["tandoori margherita"]),
    _pizza("Barbeque Margherita", 110, 230, 290, ["barbeque sauce"], ["barbeque margherita", "bbq margherita"]),
    _pizza("Herb Garlic", 110, 230, 290, ["garlic", "mixed herbs"], ["herb garlic"]),
    _pizza("Butter Masala Margherita", 110, 230, 290, ["butter masala gravy"], ["butter masala margherita"]),
    _pizza("Chipotle Margherita", 110, 230, 290, ["chipotle sauce"], ["chipotle margherita"]),
    _pizza("Spicy Chilly Margherita", 110, 230, 290, ["green chilli", "chilli flakes"], ["spicy chilly margherita"]),

    _pizza("Masala Corn & Cheese", 120, 240, 300, ["sweet corn", "masala seasoning", "extra cheese"], ["masala corn and cheese", "masala corn"]),
    _pizza("Tandoori Mushroom & Corn", 120, 240, 300, ["mushroom", "sweet corn", "tandoori sauce"], ["tandoori mushroom and corn", "tandoori mushroom"]),
    _pizza("Dragon's Fury Margherita", 120, 240, 300, ["hot chilli sauce", "red chilli"], ["dragons fury", "dragon fury"]),
    _pizza("Double Cheese Margherita", 120, 240, 300, ["double mozzarella"], ["double cheese margherita", "double cheese"]),
    _pizza("Green Capsicum", 120, 240, 300, ["green capsicum"], ["green capsicum", "capsicum pizza"]),
    _pizza("Crispy Onion", 120, 240, 300, ["crispy fried onion"], ["crispy onion"]),
    _pizza("Fresh Tomato", 120, 240, 300, ["fresh tomato"], ["fresh tomato"]),
    _pizza("Golden Corn", 120, 240, 300, ["sweet corn"], ["golden corn", "corn pizza"]),
    _pizza("Onion & Capsicum", 120, 240, 300, ["onion", "capsicum"], ["onion and capsicum"]),
    _pizza("Onion & Corn", 120, 240, 300, ["onion", "sweet corn"], ["onion and corn"]),

    _pizza("Capsicum & Paneer", 140, 250, 310, ["capsicum", "paneer"], ["capsicum and paneer"]),
    _pizza("Onion & Paneer", 140, 250, 310, ["onion", "paneer"], ["onion and paneer"]),
    _pizza("Jalapenos & Olives", 140, 250, 310, ["jalapenos", "black olives"], ["jalapenos and olives"]),
    _pizza("Paneer & Red-Peprika", 140, 250, 310, ["paneer", "red paprika"], ["paneer and red paprika", "paneer red peprika"]),
    _pizza("Mushroom & Corn", 140, 250, 310, ["mushroom", "sweet corn"], ["mushroom and corn"]),
    _pizza("Triple Tango", 140, 250, 310, ["capsicum", "onion", "tomato"], ["triple tango"]),
    _pizza("Jalapenos, Sweet Corn & Paneer", 140, 250, 310, ["jalapenos", "sweet corn", "paneer"], ["jalapenos sweet corn and paneer"]),

    # --------------------------------------------- NEWLY LAUNCHED PIZZA ----
    _pizza("Paneer Spice Supreme", 160, 270, 370,
           ["green chilli", "capsicum", "onion", "tomato", "olives", "jalapenos",
            "red paprika", "gravy marinated paneer"], ["paneer spice supreme"],
           desc="Green chilly, capsicum, onion, tomato, olives, jalapenos, red-peprika, gravy marinated paneer"),
    _pizza("Fresh Veggie", 160, 270, 370,
           ["bell pepper", "capsicum", "onion", "tomato", "green olives", "jalapenos",
            "broccoli", "black olives"], ["fresh veggie"]),
    _pizza("Smokey BBQ Veggie", 160, 270, 370,
           ["capsicum", "tomato", "red paprika", "sweet corn", "broccoli", "barbeque sauce"],
           ["smokey bbq veggie", "smoky bbq veggie"]),
    _pizza("Crunchy Nacho Veg Pizza", 160, 270, 370,
           ["capsicum", "onion", "tomato", "sweet corn", "crunchy nachos"],
           ["crunchy nacho", "nacho veg pizza"]),

    _pizza("Veg. Extravaganza", 170, 290, 390,
           ["extra capsicum", "yellow capsicum", "onion", "tomato", "red paprika",
            "mushroom", "broccoli", "green olives", "sweet corn"],
           ["veg extravaganza", "extravaganza"]),
    _pizza("Deluxe Veggie", 170, 290, 390,
           ["bell pepper", "red paprika", "green olives", "jalapenos", "black olives",
            "mushroom", "onion", "gravy marinated paneer"], ["deluxe veggie"]),
    _pizza("Veggie Paradise", 170, 290, 390,
           ["capsicum", "tomato", "broccoli", "green olives", "red paprika",
            "sweet corn", "gravy marinated paneer", "peri-peri marinated paneer"],
           ["veggie paradise"]),
    _pizza("Fire-Fused Paneer Crust", 170, 290, 390,
           ["bell pepper", "onion", "capsicum", "schezwan marinated paneer"],
           ["fire fused paneer crust", "fire fused paneer"]),
    _pizza("Farm-House", 170, 290, 390,
           ["chopped capsicum", "onion", "tomato", "paneer", "sweet corn"],
           ["farm house", "farmhouse"]),
    _pizza("Cheese Heaven Pie", 170, 290, 390,
           ["bell pepper", "onion", "red paprika", "green olives", "broccoli",
            "gravy paneer", "extra cheese"], ["cheese heaven pie", "cheese heaven"]),
    _pizza("Tandoori Veg. Cheese Blast", 170, 290, 390,
           ["capsicum", "onion", "jalapenos", "black olives", "mushroom", "cheese spread"],
           ["tandoori veg cheese blast", "cheese blast"]),
    _pizza("The Cheese Dominator", 170, 290, 390,
           ["cheese blend", "100% mozzarella", "cheddar cheese", "cheese spread dip", "filler cheese"],
           ["cheese dominator", "the cheese dominator"]),

    _pizza("Aunty's Retreat", 180, 300, 440, ["your choice of toppings"],
           ["auntys retreat", "aunty retreat", "make your own"],
           desc="Make your own pizza"),

    # --------------------------------------------------- SIGNATURE PIZZA ----
    _pizza("Veg. Loaded", 150, 260, 340,
           ["capsicum", "onion", "tomato", "jalapenos", "black olives"], ["veg loaded"]),
    _pizza("Garden Glory", 150, 260, 340,
           ["capsicum", "green olives", "jalapenos", "broccoli", "basil leaves"], ["garden glory"]),
    _pizza("Veg. Tandoori", 150, 260, 340,
           ["capsicum", "onion", "black olives", "green olives", "tandoori sauce"], ["veg tandoori"]),
    _pizza("Veg. Delight", 150, 260, 340,
           ["capsicum", "onion", "mushroom", "sweet corn", "marinated paneer"], ["veg delight"]),
    _pizza("Veggie Fiesta", 150, 260, 340, ["capsicum", "sweet corn", "red paprika"], ["veggie fiesta"]),
    _pizza("Lava Layers", 150, 260, 340,
           ["tomato", "red paprika", "red capsicum", "green olives"], ["lava layers"]),
    _pizza("Spicy Vegetarian Feast", 150, 260, 340,
           ["spicy base", "green chilli", "capsicum", "onion", "sweet corn", "mushroom",
            "jalapenos", "black olives"], ["spicy vegetarian feast", "spicy veg feast"]),
    _pizza("Spicy Veg. Mexicana", 150, 260, 340,
           ["salsa", "pizza sauce", "capsicum", "onion", "jalapenos", "green olives"],
           ["spicy veg mexicana", "veg mexicana", "mexicana"]),
    _pizza("Cheesy Mushroom Magic", 150, 260, 340,
           ["cheesy pizza sauce", "black olives", "jalapenos", "sweet corn",
            "oregano marinated mushroom", "extra cheese"], ["cheesy mushroom magic", "mushroom magic"]),
    _pizza("Mushroom Delight", 150, 260, 340,
           ["capsicum", "sweet corn", "bbq mushroom", "jalapenos"], ["mushroom delight"]),
    _pizza("Masala Veg. Delight", 150, 260, 340,
           ["capsicum", "onion", "mushroom", "peri-peri corn", "peri-peri marinated paneer"],
           ["masala veg delight"]),
    _pizza("Desi Veg. Masala", 150, 260, 340,
           ["bell pepper", "onion", "tomato"], ["desi veg masala"]),
    _pizza("Tangy Salsa Fiesta", 150, 260, 340,
           ["onion", "capsicum", "black olives", "salsa"], ["tangy salsa fiesta", "salsa fiesta"]),

    _pizza("Paneer Tikka", 150, 260, 340,
           ["makhni gravy base", "capsicum", "onion", "tomato", "gravy marinated paneer"],
           ["paneer tikka pizza", "paneer tikka"]),
    _pizza("Kadhai Paneer", 150, 260, 340,
           ["capsicum", "tomato", "red paprika", "gravy marinated paneer"], ["kadhai paneer", "karahi paneer"]),
    _pizza("Paneer Delight", 150, 260, 340,
           ["onion", "red paprika", "mixed gravy", "peri-peri paneer"], ["paneer delight"]),
    _pizza("Peri-Peri Paneer", 150, 260, 340,
           ["peri-peri base", "capsicum", "onion", "bell pepper", "jalapenos",
            "peri-peri marinated paneer"], ["peri peri paneer"]),
    _pizza("Paneer Butter Masala", 150, 260, 340,
           ["buttery gravy base", "onion", "tomato", "jalapenos", "gravy marinated paneer"],
           ["paneer butter masala", "butter paneer"]),
    _pizza("Shahi Paneer", 150, 260, 340,
           ["capsicum", "onion", "black olives", "green olives", "red paprika",
            "gravy marinated big paneer cubes"], ["shahi paneer"]),
    _pizza("Peri-Peri Crunch", 150, 260, 340,
           ["peri-peri base", "capsicum", "onion", "bell pepper", "jalapenos",
            "crispy peri-peri fries"], ["peri peri crunch"]),
    _pizza("BBQ Paneer", 150, 260, 340,
           ["bbq sauce", "pizza sauce", "capsicum", "onion", "red capsicum",
            "black olives", "green olives", "bbq gravy marinated paneer"], ["bbq paneer"]),
    _pizza("Hariyali Paneer", 150, 260, 340,
           ["capsicum", "broccoli", "jalapenos", "gravy marinated paneer"], ["hariyali paneer"]),
    _pizza("Lehsooni Paneer", 150, 260, 340,
           ["onion", "tomato", "red paprika", "garlic gravy", "garlic marinated paneer"],
           ["lehsooni paneer", "lehsuni paneer"]),
    _pizza("Royal Maharaja Paneer", 150, 260, 340,
           ["broccoli", "green olives", "red paprika", "bell pepper", "big paneer cubes"],
           ["royal maharaja paneer", "maharaja paneer"]),
    _pizza("Spicy Schezwan Paneer", 150, 260, 340,
           ["onion", "jalapenos", "black olives", "red paprika", "schezwan marinated paneer"],
           ["spicy schezwan paneer", "schezwan paneer"]),

    # ------------------------------------------------------ ITALIAN PIZZA --
    _d("Italian", 130, "Pizza", _BASE + ["italian herbs"], _PZ, ["italian pizza"], prep=15),
    _d("Double Cheese Italian", 160, "Pizza", _BASE + ["double mozzarella", "italian herbs"],
       _PZ, ["double cheese italian"], prep=15),

    # ---------------------------------------------------------- CALIZZA ----
    # Half folded pizza + half open pizza.
    _d("Veg. Supreme Margherita Calizza", 310, "Calizza",
       _BASE + ["margherita", "veg delight toppings"], _PZ,
       ["veg supreme margherita calizza", "supreme margherita calizza"], prep=18,
       desc="Fold side Margherita + open side Veg Delight"),
    _d("Garlic Mushroom Magic Calizza", 320, "Calizza",
       _BASE + ["cheese garlic bread", "oregano mushroom"], _PZ,
       ["garlic mushroom magic calizza", "garlic mushroom calizza"], prep=18,
       desc="Fold side Cheese Garlic Bread + open side Cheesy Mushroom Magic"),
    _d("Spicy Veggie Mexican Calizza", 330, "Calizza",
       _BASE + ["spicy veg feast toppings", "salsa", "jalapenos"], _PZ,
       ["spicy veggie mexican calizza", "spicy veggie mexican"], prep=18),
    _d("Mexican Spice Supreme Fiesta Calizza", 340, "Calizza",
       _BASE + ["spicy veg mexican", "paneer spice supreme toppings"], _PZ,
       ["mexican spice supreme fiesta calizza", "mexican spice supreme"], prep=18),
    _d("Indo Asian Calizza", 340, "Calizza",
       _BASE + ["veg loaded toppings", "paneer tikka toppings"], _PZ,
       ["indo asian calizza", "indo asian"], prep=18),
    _d("Veg. Explosion Peri-Peri Calizza", 350, "Calizza",
       _BASE + ["peri-peri paneer", "veg tandoori toppings"], _PZ,
       ["veg explosion peri peri calizza", "veg explosion"], prep=18),
    _d("American Corn Mushroom Delight Calizza", 360, "Calizza",
       _BASE + ["golden corn", "mushroom delight toppings"], _PZ,
       ["american corn mushroom delight calizza", "american corn mushroom"], prep=18),
    _d("Nachos Crunch Calizza", 360, "Calizza",
       _BASE + ["margherita", "nachos", "spicy veg feast toppings"], _PZ,
       ["nachos crunch calizza", "nachos crunch"], prep=18),
    _d("Peri-Peri BBQ Paneer Calizza", 370, "Calizza",
       _BASE + ["bbq paneer", "peri-peri pizza toppings"], _PZ,
       ["peri peri bbq paneer calizza", "peri peri bbq paneer"], prep=18),

    # --------------------------------------------- STUFFED GARLIC BREAD ----
    _d("Plain Garlic Bread", 70, "Garlic Bread", ["bread", "garlic butter"], ["gluten", "dairy"], ["plain garlic bread"], prep=10),
    _d("Cheese Stuffed Garlic Bread", 90, "Garlic Bread", ["bread", "garlic butter", "mozzarella"], ["gluten", "dairy"], ["cheese stuffed garlic bread", "cheese garlic bread"], prep=10),
    _d("Masala Cheese Garlic Bread", 90, "Garlic Bread", ["bread", "garlic butter", "mozzarella", "masala seasoning"], ["gluten", "dairy"], ["masala cheese garlic bread"], prep=10),
    _d("Cheesy Schezwan Garlic Bread", 90, "Garlic Bread", ["bread", "garlic butter", "mozzarella", "schezwan sauce"], ["gluten", "dairy", "soy"], ["cheesy schezwan garlic bread", "schezwan garlic bread"], prep=10),
    _d("Butter Makhni Garlic Bread", 90, "Garlic Bread", ["bread", "garlic butter", "makhni gravy", "mozzarella"], ["gluten", "dairy"], ["butter makhni garlic bread", "makhni garlic bread"], prep=10),
    _d("Corn & Cheese Garlic Bread", 100, "Garlic Bread", ["bread", "garlic butter", "sweet corn", "mozzarella"], ["gluten", "dairy"], ["corn and cheese garlic bread"], prep=10),
    _d("Cheesy Jalapenos Garlic Bread", 100, "Garlic Bread", ["bread", "garlic butter", "jalapenos", "mozzarella"], ["gluten", "dairy"], ["cheesy jalapenos garlic bread", "jalapeno garlic bread"], prep=10),
    _d("Cheesy Aloo Tikki Garlic Bread", 110, "Garlic Bread", ["bread", "garlic butter", "aloo tikki", "mozzarella"], ["gluten", "dairy"], ["cheesy aloo tikki garlic bread", "aloo tikki garlic bread"], prep=10),
    _d("Corn, Jalapenos & Cheese Garlic Bread", 110, "Garlic Bread", ["bread", "garlic butter", "sweet corn", "jalapenos", "mozzarella"], ["gluten", "dairy"], ["corn jalapenos and cheese garlic bread"], prep=10),
    _d("Corn & Paneer Garlic Bread", 110, "Garlic Bread", ["bread", "garlic butter", "sweet corn", "paneer"], ["gluten", "dairy"], ["corn and paneer garlic bread"], prep=10),
    _d("Fire Cracker Garlic Bread", 110, "Garlic Bread", ["bread", "garlic butter", "hot chilli sauce", "mozzarella"], ["gluten", "dairy"], ["fire cracker garlic bread", "firecracker garlic bread"], prep=10),
    _d("Chilly Cheese Garlic Bread", 110, "Garlic Bread", ["bread", "garlic butter", "green chilli", "mozzarella"], ["gluten", "dairy"], ["chilly cheese garlic bread", "chilli cheese garlic bread"], prep=10),
    _d("Cheesy Mexican Garlic Bread", 120, "Garlic Bread", ["bread", "garlic butter", "salsa", "jalapenos", "mozzarella"], ["gluten", "dairy"], ["cheesy mexican garlic bread", "mexican garlic bread"], prep=10),
    _d("BBQ Paneer Garlic Bread", 120, "Garlic Bread", ["bread", "garlic butter", "bbq sauce", "paneer"], ["gluten", "dairy"], ["bbq paneer garlic bread"], prep=10),
    _d("Veggie Stuffed Garlic Bread", 120, "Garlic Bread", ["bread", "garlic butter", "mixed vegetables", "mozzarella"], ["gluten", "dairy"], ["veggie stuffed garlic bread"], prep=10),
    _d("Supreme Veggie Garlic Bread", 120, "Garlic Bread", ["bread", "garlic butter", "capsicum", "onion", "sweet corn", "olives", "mozzarella"], ["gluten", "dairy"], ["supreme veggie garlic bread"], prep=10),
    _d("Cheese Burst Garlic Bread", 130, "Garlic Bread", ["bread", "garlic butter", "molten cheese filling"], ["gluten", "dairy"], ["cheese burst garlic bread"], prep=10),
    _d("Veggie & Corn Garlic Bread", 130, "Garlic Bread", ["bread", "garlic butter", "mixed vegetables", "sweet corn", "mozzarella"], ["gluten", "dairy"], ["veggie and corn garlic bread"], prep=10),
    _d("Peri-Peri Paneer Garlic Bread", 140, "Garlic Bread", ["bread", "garlic butter", "peri-peri paneer"], ["gluten", "dairy"], ["peri peri paneer garlic bread"], prep=10),
    _d("Paneer Tikka Garlic Bread", 150, "Garlic Bread", ["bread", "garlic butter", "tikka marinated paneer"], ["gluten", "dairy"], ["paneer tikka garlic bread"], prep=10),

    # ------------------------------------------------------ GARLIC FINGERS -
    _d("Cheesy Garlic Fingers", 100, "Garlic Bread", ["bread fingers", "garlic butter", "mozzarella"], ["gluten", "dairy"], ["cheesy garlic fingers", "cheezy garlic fingers"], prep=10),
    _d("Chilly Cheese Garlic Fingers", 110, "Garlic Bread", ["bread fingers", "garlic butter", "green chilli", "mozzarella"], ["gluten", "dairy"], ["chilly cheese garlic fingers"], prep=10),
    _d("Veggie Garlic Fingers", 120, "Garlic Bread", ["bread fingers", "garlic butter", "mixed vegetables"], ["gluten", "dairy"], ["veggie garlic fingers"], prep=10),
    _d("Peri-Peri Paneer Garlic Fingers", 130, "Garlic Bread", ["bread fingers", "garlic butter", "peri-peri paneer"], ["gluten", "dairy"], ["peri peri paneer garlic fingers"], prep=10),

    # --------------------------------------------------------- ZINGY PARCEL -
    _d("Zingy Parcel", 49, "Parcel", ["pizza dough", "cheese", "seasoning"], ["gluten", "dairy"], ["zingy parcel"], prep=8),
    _d("Veg. Zingy Parcel", 59, "Parcel", ["pizza dough", "mixed vegetables", "cheese"], ["gluten", "dairy"], ["veg zingy parcel"], prep=8),
    _d("Corn Zingy Parcel", 59, "Parcel", ["pizza dough", "sweet corn", "cheese"], ["gluten", "dairy"], ["corn zingy parcel"], prep=8),
    _d("Veg. & Paneer Zingy Parcel", 69, "Parcel", ["pizza dough", "mixed vegetables", "paneer", "cheese"], ["gluten", "dairy"], ["veg and paneer zingy parcel"], prep=8),
    _d("Corn & Paneer Zingy Parcel", 69, "Parcel", ["pizza dough", "sweet corn", "paneer", "cheese"], ["gluten", "dairy"], ["corn and paneer zingy parcel"], prep=8),

    # ------------------------------------------------------ POCKET CALZONE -
    _d("Cheese Calzone", 100, "Calzone", ["folded dough", "mozzarella"], ["gluten", "dairy"], ["cheese calzone"], prep=12),
    _d("Chipotle Calzone", 110, "Calzone", ["folded dough", "chipotle sauce", "mozzarella"], ["gluten", "dairy"], ["chipotle calzone"], prep=12),
    _d("Onion & Corn Calzone", 120, "Calzone", ["folded dough", "onion", "sweet corn", "mozzarella"], ["gluten", "dairy"], ["onion and corn calzone"], prep=12),
    _d("Veggie Stuffed Calzone", 130, "Calzone", ["folded dough", "mixed vegetables", "mozzarella"], ["gluten", "dairy"], ["veggie stuffed calzone"], prep=12),
    _d("Paneer Tikka Calzone", 140, "Calzone", ["folded dough", "tikka paneer", "mozzarella"], ["gluten", "dairy"], ["paneer tikka calzone"], prep=12),
    _d("Peri-Peri Calzone", 140, "Calzone", ["folded dough", "peri-peri seasoning", "mozzarella"], ["gluten", "dairy"], ["peri peri calzone"], prep=12),
    _d("Mexican Calzone", 150, "Calzone", ["folded dough", "salsa", "jalapenos", "mozzarella"], ["gluten", "dairy"], ["mexican calzone"], prep=12),
    _d("BBQ Paneer Calzone", 150, "Calzone", ["folded dough", "bbq sauce", "paneer", "mozzarella"], ["gluten", "dairy"], ["bbq paneer calzone"], prep=12),

    # ---------------------------------------------------------- STARTERS ----
    _d("Cigar Rolls", 99, "Starter", ["pastry roll", "spiced vegetable filling"], ["gluten"], ["cigar rolls", "cigar roll"], prep=10, desc="5 pieces"),
    _d("Crispy Onion Rings", 99, "Starter", ["onion", "batter", "breadcrumbs"], ["gluten"], ["crispy onion rings", "onion rings"], prep=10, desc="5 pieces"),
    _d("Bombay Batata Vada Shots", 99, "Starter", ["potato", "gram flour", "spices"], [], ["bombay batata vada shots", "batata vada"], prep=10, desc="7 pieces"),
    _d("Cheese Ring", 99, "Starter", ["mozzarella", "batter", "breadcrumbs"], ["gluten", "dairy"], ["cheese ring", "cheese rings"], prep=10, desc="2 pieces"),
    _d("Cheesy Nachos", 99, "Starter", ["corn nachos", "cheese sauce"], ["gluten", "dairy"], ["cheesy nachos", "cheezy nachos"], prep=8),
    _d("Veg. Cheese Mexican Nachos", 149, "Starter", ["corn nachos", "cheese sauce", "salsa", "jalapenos", "mixed vegetables"], ["gluten", "dairy"], ["veg cheese mexican nachos", "mexican nachos"], prep=10),
    _d("Spicy Chilly Potato", 159, "Starter", ["potato", "chilli sauce", "capsicum", "onion"], ["gluten", "soy"], ["spicy chilly potato", "chilli potato"], prep=12, desc="350 gm"),

    # ------------------------------------------------------ FRENCH FRIES ----
    _d("Salted Fries", 90, "Fries", ["potato fries", "salt"], [], ["salted fries", "plain fries"],
       sizes={"Medium": 90, "Large": 120}, prep=8),
    _d("Peri-Peri Fries", 110, "Fries", ["potato fries", "peri-peri seasoning"], [], ["peri peri fries"],
       sizes={"Medium": 110, "Large": 150}, prep=8),
    _d("Cheesy Salted Fries", 140, "Fries", ["potato fries", "cheese sauce"], ["dairy"], ["cheesy salted fries", "cheezy salted fries"],
       sizes={"Medium": 140, "Large": 180}, prep=8),
    _d("Cheesy Peri-Peri Fries", 160, "Fries", ["potato fries", "peri-peri seasoning", "cheese sauce"], ["dairy"], ["cheesy peri peri fries", "cheezy peri peri fries"],
       sizes={"Medium": 160, "Large": 210}, prep=8),
    _d("Veg. Cheesy Peri-Peri Fries", 180, "Fries", ["potato fries", "peri-peri seasoning", "cheese sauce", "mixed vegetables"], ["dairy"], ["veg cheesy peri peri fries", "veg cheezy peri peri fries"],
       sizes={"Medium": 180, "Large": 240}, prep=8),
    _d("Veg. Cheesy Jalapenos Peri-Peri Fries", 190, "Fries", ["potato fries", "peri-peri seasoning", "cheese sauce", "jalapenos"], ["dairy"], ["veg cheesy jalapenos peri peri fries", "jalapeno fries"],
       sizes={"Medium": 190, "Large": 260}, prep=8),

    # ------------------------------------------------------------ BURGER ----
    # sizes = cheese variant. "Regular / Veeba Cheese Blend / Amul Cheese Slice / Cheese Ring"
    _d("Classic Aloo Tikki Burger", 80, "Burger", ["burger bun", "aloo tikki", "onion", "sauces"], ["gluten"], ["classic aloo tikki burger", "aloo tikki burger"],
       sizes={"Regular": 80, "Veeba Cheese Blend": 100, "Amul Cheese Slice": 100, "Cheese Ring": 130}, prep=10),
    _d("Crispy Veg. Burger", 90, "Burger", ["burger bun", "crispy veg patty", "lettuce", "mayonnaise"], ["gluten", "dairy"], ["crispy veg burger"],
       sizes={"Regular": 90, "Veeba Cheese Blend": 110, "Amul Cheese Slice": 110, "Cheese Ring": 140}, prep=10),
    _d("Classic Makhni Aloo Tikki Burger", 90, "Burger", ["burger bun", "aloo tikki", "makhni sauce"], ["gluten", "dairy"], ["classic makhni aloo tikki burger", "makhni aloo tikki burger"],
       sizes={"Regular": 90, "Veeba Cheese Blend": 110, "Amul Cheese Slice": 110, "Cheese Ring": 140}, prep=10),
    _d("Classic Double Patty Burger", 100, "Burger", ["burger bun", "two aloo tikki patties", "sauces"], ["gluten"], ["classic double patty burger", "double patty burger"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Spicy Tangy Aloo Tikki Burger", 100, "Burger", ["burger bun", "aloo tikki", "tangy spicy sauce"], ["gluten"], ["spicy tangy aloo tikki burger"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Fiery Veg. Aloo Tikki Burger", 100, "Burger", ["burger bun", "aloo tikki", "hot sauce"], ["gluten"], ["fiery veg aloo tikki burger", "fiery aloo tikki"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Hot-Shot Harissa Aloo Tikki Burger", 100, "Burger", ["burger bun", "aloo tikki", "harissa sauce"], ["gluten"], ["hot shot harissa aloo tikki burger", "harissa burger"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Veggie Boom Burger", 100, "Burger", ["burger bun", "mixed veg patty", "sauces"], ["gluten"], ["veggie boom burger"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Red Hot Veg. Crunch Burger", 100, "Burger", ["burger bun", "crunchy veg patty", "red hot sauce"], ["gluten"], ["red hot veg crunch burger"],
       sizes={"Regular": 100, "Veeba Cheese Blend": 120, "Amul Cheese Slice": 120, "Cheese Ring": 150}, prep=10),
    _d("Veggie Double Patty Burger", 120, "Burger", ["burger bun", "two veg patties", "sauces"], ["gluten"], ["veggie double patty burger"],
       sizes={"Regular": 120, "Veeba Cheese Blend": 130, "Amul Cheese Slice": 130, "Cheese Ring": 170}, prep=10),
    _d("Veg. Cheese Burger", 120, "Burger", ["burger bun", "veg patty", "cheese"], ["gluten", "dairy"], ["veg cheese burger"],
       sizes={"Regular": 120, "Amul Cheese Slice": 140, "Cheese Ring": 170}, prep=10),
    _d("Cheesy Peri-Peri Burger", 120, "Burger", ["burger bun", "veg patty", "peri-peri seasoning", "cheese"], ["gluten", "dairy"], ["cheesy peri peri burger", "cheezy peri peri burger"],
       sizes={"Regular": 120, "Amul Cheese Slice": 140, "Cheese Ring": 170}, prep=10),
    _d("Corn & Cheese Burger", 120, "Burger", ["burger bun", "sweet corn", "cheese"], ["gluten", "dairy"], ["corn and cheese burger"],
       sizes={"Regular": 120, "Amul Cheese Slice": 140, "Cheese Ring": 170}, prep=10),
    _d("Fiery Cheese Burger", 120, "Burger", ["burger bun", "veg patty", "hot sauce", "cheese"], ["gluten", "dairy"], ["fiery cheese burger"],
       sizes={"Regular": 120, "Veeba Cheese Blend": 140, "Amul Cheese Slice": 140, "Cheese Ring": 170}, prep=10),
    _d("Peri-Peri Heat Schezwan Burger", 120, "Burger", ["burger bun", "veg patty", "peri-peri", "schezwan sauce"], ["gluten", "soy"], ["peri peri heat schezwan burger", "schezwan burger"],
       sizes={"Regular": 120, "Veeba Cheese Blend": 140, "Amul Cheese Slice": 140, "Cheese Ring": 170}, prep=10),
    _d("Mexican Patty Burger", 130, "Burger", ["burger bun", "mexican veg patty", "salsa", "jalapenos"], ["gluten"], ["mexican patty burger"],
       sizes={"Regular": 130, "Veeba Cheese Blend": 150, "Amul Cheese Slice": 170, "Cheese Ring": 180}, prep=10),
    _d("Mexican Double Patty Burger", 140, "Burger", ["burger bun", "two mexican patties", "salsa", "jalapenos"], ["gluten"], ["mexican double patty burger"],
       sizes={"Regular": 140, "Veeba Cheese Blend": 160, "Amul Cheese Slice": 180, "Cheese Ring": 190}, prep=10),
    _d("Deluxe Paneer Patty Burger", 140, "Burger", ["burger bun", "paneer patty", "sauces"], ["gluten", "dairy"], ["deluxe paneer patty burger", "paneer burger"],
       sizes={"Regular": 140, "Veeba Cheese Blend": 160, "Amul Cheese Slice": 160, "Cheese Ring": 190}, prep=10),

    # -------------------------------------------------------------- MOMO ----
    # sizes = cooking style
    _d("Mix Veg. Momo", 80, "Momo", ["flour wrapper", "mixed vegetables", "spices"], ["gluten"], ["mix veg momo", "veg momo"],
       sizes={"Steam": 80, "Pan Fry": 90, "Deep Fry": 110, "Gravy": 120}, prep=12, desc="6 pieces"),
    _d("Spicy Veg. Momo", 90, "Momo", ["flour wrapper", "mixed vegetables", "chilli"], ["gluten"], ["spicy veg momo"],
       sizes={"Steam": 90, "Pan Fry": 100, "Deep Fry": 120, "Gravy": 130}, prep=12, desc="6 pieces"),
    _d("Paneer Momo", 110, "Momo", ["flour wrapper", "paneer", "spices"], ["gluten", "dairy"], ["paneer momo"],
       sizes={"Steam": 110, "Pan Fry": 130, "Deep Fry": 150, "Gravy": 160}, prep=12, desc="6 pieces"),
    _d("Veg. Cheese Momo", 120, "Momo", ["flour wrapper", "mixed vegetables", "cheese"], ["gluten", "dairy"], ["veg cheese momo"],
       sizes={"Steam": 120, "Pan Fry": 140, "Deep Fry": 160, "Gravy": 170}, prep=12, desc="6 pieces"),
    _d("Paneer Tikka Momo", 120, "Momo", ["flour wrapper", "tikka paneer"], ["gluten", "dairy"], ["paneer tikka momo"],
       sizes={"Steam": 120, "Pan Fry": 140, "Deep Fry": 160, "Gravy": 170}, prep=12, desc="6 pieces"),
    _d("Cheese Corn Momo", 120, "Momo", ["flour wrapper", "cheese", "sweet corn"], ["gluten", "dairy"], ["cheese corn momo"],
       sizes={"Steam": 120, "Pan Fry": 140, "Deep Fry": 160, "Gravy": 170}, prep=12, desc="6 pieces"),

    # ------------------------------------------------- MOMO WITH SAUCES ----
    _d("Veg. Hot Garlic Pan Fried Momo in Schezwan Sauce", 120, "Momo", ["flour wrapper", "mixed vegetables", "hot garlic", "schezwan sauce"], ["gluten", "soy"], ["hot garlic pan fried momo", "hot garlic momo"], prep=14, desc="6 pieces"),
    _d("Veg. Darjeeling Pan Fried Momo in Cheese Sauce", 120, "Momo", ["flour wrapper", "mixed vegetables", "cheese sauce"], ["gluten", "dairy"], ["darjeeling pan fried momo in cheese sauce"], prep=14, desc="6 pieces"),
    _d("Steamed Veg. Darjeeling Garlic Momo in Molten Cheese Sauce", 120, "Momo", ["flour wrapper", "mixed vegetables", "garlic", "molten cheese sauce"], ["gluten", "dairy"], ["steamed darjeeling garlic momo"], prep=14, desc="6 pieces"),
    _d("Veg. Darjeeling Deep Fried Peri-Peri Momo", 130, "Momo", ["flour wrapper", "mixed vegetables", "peri-peri seasoning"], ["gluten"], ["darjeeling deep fried peri peri momo"], prep=14, desc="6 pieces"),
    _d("Steamed Corn & Cheese Momo in Molten Cheese Sauce", 130, "Momo", ["flour wrapper", "sweet corn", "cheese", "molten cheese sauce"], ["gluten", "dairy"], ["steamed corn and cheese momo"], prep=14, desc="6 pieces"),
    _d("Veg. Darjeeling Deep Fried Garlic Peri-Peri Momo", 140, "Momo", ["flour wrapper", "mixed vegetables", "garlic", "peri-peri seasoning"], ["gluten"], ["darjeeling deep fried garlic peri peri momo"], prep=14, desc="6 pieces"),
    _d("Himalayan Paneer Deep Fried Peri-Peri Momo", 140, "Momo", ["flour wrapper", "paneer", "peri-peri seasoning"], ["gluten", "dairy"], ["himalayan paneer momo"], prep=14, desc="6 pieces"),
    _d("Spicy Veg. Deep Fried Garlic Peri-Peri Momo", 150, "Momo", ["flour wrapper", "mixed vegetables", "garlic", "peri-peri", "chilli"], ["gluten"], ["spicy veg deep fried garlic peri peri momo"], prep=14, desc="6 pieces"),
    _d("Corn & Cheese Deep Fried Peri-Peri Momo", 150, "Momo", ["flour wrapper", "sweet corn", "cheese", "peri-peri seasoning"], ["gluten", "dairy"], ["corn and cheese deep fried peri peri momo"], prep=14, desc="6 pieces"),
    _d("Corn & Cheese Pan Fried Momo in Schezwan Sauce", 160, "Momo", ["flour wrapper", "sweet corn", "cheese", "schezwan sauce"], ["gluten", "dairy", "soy"], ["corn and cheese pan fried momo"], prep=14, desc="6 pieces"),

    # ------------------------------------------------------------ FARALI ----
    # Fasting menu — no grain flour, no onion/garlic.
    _d("Farali Pizza", 140, "Farali", ["farali (rajgira) base", "cheese", "potato", "rock salt"], ["dairy"], ["farali pizza"], prep=15),
    _d("Double Cheese Farali Pizza", 170, "Farali", ["farali base", "double cheese", "potato", "rock salt"], ["dairy"], ["double cheese farali pizza"], prep=15),
    _d("Farali French Fries", 100, "Farali", ["potato", "rock salt"], [], ["farali french fries", "farali fries"], prep=8),
    _d("Farali Vanilla Shake", 100, "Farali", ["milk", "vanilla", "sugar"], ["dairy"], ["farali vanilla shake"], prep=5),
    _d("Farali Pizza Combo", 299, "Farali", ["farali pizza", "farali fries", "farali shake"], ["dairy"], ["farali pizza combo", "farali combo"], prep=18),

    # ----------------------------------------------------------- COOLERS ----
    _d("Cold Coffee", 99, "Beverage", ["milk", "coffee", "sugar"], ["dairy"], ["cold coffee"], prep=5),
    _d("Choco Chips Cold Coffee", 109, "Beverage", ["milk", "coffee", "choco chips"], ["dairy"], ["choco chips cold coffee"], prep=5),
    _d("Hazelnut Cold Coffee", 109, "Beverage", ["milk", "coffee", "hazelnut syrup"], ["dairy", "nuts"], ["hazelnut cold coffee"], prep=5),
    _d("Chocolate Cold Coffee", 110, "Beverage", ["milk", "coffee", "chocolate"], ["dairy"], ["chocolate cold coffee"], prep=5),
    _d("Vanilla Shake", 120, "Beverage", ["milk", "vanilla ice cream", "sugar"], ["dairy"], ["vanilla shake"], prep=5),
    _d("Choco Chips Vanilla Shake", 120, "Beverage", ["milk", "vanilla ice cream", "choco chips"], ["dairy"], ["choco chips vanilla"], prep=5),
    _d("Mango Milkshake", 120, "Beverage", ["milk", "mango pulp", "sugar"], ["dairy"], ["mango milkshake", "mango shake"], prep=5),
    _d("Strawberry Milkshake", 120, "Beverage", ["milk", "strawberry", "sugar"], ["dairy"], ["strawberry milkshake", "strawberry shake"], prep=5),
    _d("Chocolate Shake", 120, "Beverage", ["milk", "chocolate", "ice cream"], ["dairy"], ["chocolate shake"], prep=5),
    _d("Kit-Kat Cold Coffee", 130, "Beverage", ["milk", "coffee", "Kit-Kat"], ["dairy", "gluten"], ["kit kat cold coffee"], prep=5),
    _d("Kunafa Milkshake", 130, "Beverage", ["milk", "kunafa", "nuts", "sugar"], ["dairy", "nuts", "gluten"], ["kunafa milkshake", "kunafa shake"], prep=5),
    _d("Kit-Kat Shake", 140, "Beverage", ["milk", "Kit-Kat", "ice cream"], ["dairy", "gluten"], ["kit kat shake"], prep=5),
    _d("Oreo Shake", 140, "Beverage", ["milk", "Oreo biscuits", "ice cream"], ["dairy", "gluten"], ["oreo shake"], prep=5),
    _d("Mango Cheese Milkshake", 150, "Beverage", ["milk", "mango pulp", "cream cheese"], ["dairy"], ["mango cheese milkshake"], prep=5),
    _d("Strawberry Cheese Milkshake", 150, "Beverage", ["milk", "strawberry", "cream cheese"], ["dairy"], ["strawberry cheese milkshake"], prep=5),

    # ---------------------------------------------------------- MOCKTAIL ----
    _d("Peach Iced Tea", 100, "Mocktail", ["black tea", "peach syrup", "lemon", "ice"], [], ["peach iced tea"], prep=5),
    _d("Lemon Iced Tea", 100, "Mocktail", ["black tea", "lemon", "sugar", "ice"], [], ["lemon iced tea"], prep=5),
    _d("Spicy Mango", 100, "Mocktail", ["mango", "chilli", "lemon", "ice"], [], ["spicy mango"], prep=5),
    _d("Jamun Kala Khatta", 100, "Mocktail", ["jamun syrup", "black salt", "lemon", "ice"], [], ["jamun kala khatta", "kala khatta"], prep=5),
    _d("Chilli Guava", 100, "Mocktail", ["guava", "chilli", "black salt", "ice"], [], ["chilli guava"], prep=5),
    _d("Green Apple Lime", 100, "Mocktail", ["green apple syrup", "lime", "soda", "ice"], [], ["green apple lime"], prep=5),
    _d("Special Sugarfree Green Apple", 150, "Mocktail", ["green apple", "sugar-free sweetener", "lime", "soda"], [], ["special sugarfree green apple", "sugarfree green apple"], prep=5),

    # ---------------------------------------------------------- DESSERTS ----
    _d("Choco Lava Cake", 99, "Dessert", ["chocolate cake", "molten chocolate centre"], ["gluten", "dairy", "egg"], ["choco lava cake", "lava cake"], prep=6),
    _d("Choco Lava Cake x2", 149, "Dessert", ["chocolate cake", "molten chocolate centre"], ["gluten", "dairy", "egg"], ["two choco lava cakes", "choco lava cake x2"], prep=6),
    _d("Hot Brownie", 99, "Dessert", ["chocolate brownie", "cocoa", "butter"], ["gluten", "dairy", "egg"], ["hot brownie"], prep=6, desc="2 pieces, 100 gm"),
]

# ---------------------------------------------------------------- config --

SERVICE_ITEMS = ["water", "fork", "spoon", "knife", "napkin", "tissue", "plate",
                 "glass", "menu card", "straw"]

TAX_RATE = 0.05
TAX_MODE = "inclusive"

CHEF_SPECIALS = ["Margherita", "Paneer Tikka", "Veg. Extravaganza", "Cheesy Nachos"]

CATEGORIES = ["Pizza", "Calizza", "Garlic Bread", "Parcel", "Calzone", "Starter",
              "Fries", "Burger", "Momo", "Farali", "Beverage", "Mocktail", "Dessert"]

# Dips available (₹15 for 30 ml) — mentioned as add-ons, not standalone dishes.
DIPS = ["mayo", "cheesy", "garlic mayo", "schezwan", "mexican mayo", "mexican cheesy",
        "tandoori", "tandoori mayo", "cheesy tandoori", "peri-peri powder",
        "peri-peri mayo", "peri-peri cheesy", "bbq mayo", "bbq cheesy"]
DIP_PRICE = 15


def prep_minutes(dish: dict) -> int:
    return dish.get("prep", 12)


import re as _re

# Compiled once per alias. find_dish tests every alias of every dish, so this
# runs a few hundred times a turn and rebuilding the pattern each time showed up.
_alias_re: dict = {}


def _alias_matches(text: str, alias: str) -> bool:
    """Whole-phrase match so 'corn' alone doesn't hijack 'Golden Corn'.

    A trailing plural is allowed: guests say "two cold coffees" and "three
    margheritas" far more often than the singular, and a strict word boundary
    used to reject both — the dish simply never made it onto the order.
    """
    rx = _alias_re.get(alias)
    if rx is None:
        rx = _alias_re[alias] = _re.compile(
            rf"(?<![a-z]){_re.escape(alias)}(?:e?s)?(?![a-z])")
    return rx.search(text) is not None


# --- Live admin overrides (price / availability) from the KDS SQLite DB ---
import os as _os
import sqlite3 as _sqlite3
import time as _time

_OV_DB = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "lumina.db")
_ov_cache = {"data": {}, "t": 0.0}
_cd_cache = {"data": [], "t": 0.0}


def _overrides() -> dict:
    """Menu overrides, cached 8 s so admin edits show up fast."""
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


def _custom_dishes() -> list:
    """Dishes added from the admin console. Cached 8 s."""
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
                             "prep": prep, "aliases": [name.lower()],
                             "sizes": {}, "desc": "", "custom": True})
            c.close()
        except Exception:
            pass
        _cd_cache["data"], _cd_cache["t"] = rows, _time.time()
    return _cd_cache["data"]


def all_dishes() -> list:
    """Base menu + admin-added dishes — the full orderable set."""
    return MENU + _custom_dishes()


def tax_config():
    """(mode, rate) from Settings, falling back to the constants above."""
    try:
        import settings
        return settings.get("tax_mode", TAX_MODE), float(settings.get("tax_rate", TAX_RATE * 100)) / 100
    except Exception:
        return TAX_MODE, TAX_RATE


def size_names(dish: dict) -> list:
    return list(dish.get("sizes") or {})


def default_size(dish: dict):
    """The size we assume when the guest doesn't say one (cheapest/base)."""
    s = size_names(dish)
    return s[0] if s else None


# Not every "size" is a size. Pizzas and fries come in Regular/Medium/Large,
# but a momo's option is how it's cooked and a burger's is which cheese.
_TRUE_SIZES = {"regular", "medium", "large", "small"}


def label_for(dish: dict, size=None) -> str:
    """How the dish should read on a screen or in Lumina's mouth.

    "Large Margherita" — a real size leads, like a waiter would say it.
    "Mix Veg. Momo (Gravy)" — a variant trails, because "Gravy Mix Veg. Momo"
    is not something anybody says.
    """
    name = dish["name"]
    if not size:
        return name
    return f"{size} {name}" if size.lower() in _TRUE_SIZES else f"{name} ({size})"


def price_for(dish: dict, size=None) -> int:
    """Price of a dish in the chosen size, honouring any admin price override.

    An override replaces the base price; other sizes keep their difference from
    the base so a single edit still makes sense for a sized dish.
    """
    base = dish["price"]
    o = _overrides().get(dish["name"])
    override = int(o[0]) if o and o[0] is not None else None
    sizes = dish.get("sizes") or {}
    if not sizes or size not in sizes:
        return override if override is not None else base
    listed = int(sizes[size])
    if override is None:
        return listed
    return max(0, listed + (override - base))


def effective_price(dish: dict) -> int:
    return price_for(dish, default_size(dish))


def is_available(dish: dict) -> bool:
    o = _overrides().get(dish["name"])
    return o[1] if o else True


def find_size(text: str, dish: dict):
    """Pick out a size the guest named, e.g. 'a large margherita'."""
    sizes = dish.get("sizes") or {}
    if not sizes:
        return None
    t = _normalise(text)
    extra = {"small": "Regular", "reg": "Regular", "med": "Medium",
             "big": "Large", "steamed": "Steam", "fried": "Deep Fry"}
    for s in sizes:
        if _alias_matches(t, s.lower()):
            return s
    for word, s in extra.items():
        if s in sizes and _alias_matches(t, word):
            return s
    return None


def _normalise(text: str) -> str:
    """Punctuation must never split a dish name. Whisper writes what it hears —
    "Cheezy, Peri, Peri, Fries." — and commas inside a name used to stop it
    matching anything at all."""
    # Collapse the gaps too, or "a, b" becomes "a  b" and the alias,
    # which has one space, stops matching.
    return _re.sub(r"\s+", " ", _re.sub(r"[,.!?;:]+", " ", (text or "").lower())).strip()


def find_dish(text: str):
    """Return the menu dish whose longest alias/name appears in `text`."""
    t = _normalise(text)
    best, best_len = None, 0
    for dish in all_dishes():
        for alias in [dish["name"].lower()] + dish["aliases"]:
            if _alias_matches(t, alias) and len(alias) > best_len:
                best, best_len = dish, len(alias)
    return best


def find_service_item(text: str):
    t = (text or "").lower()
    for item in SERVICE_ITEMS:
        if _alias_matches(t, item):
            return item
    return None


def by_category(category: str):
    return [d for d in all_dishes() if d["category"] == category]


CATEGORY_ALIASES = {
    "pizza": "Pizza", "pizzas": "Pizza",
    "calizza": "Calizza", "calizzas": "Calizza",
    "garlic bread": "Garlic Bread", "garlic breads": "Garlic Bread",
    "garlic fingers": "Garlic Bread", "bread": "Garlic Bread",
    "parcel": "Parcel", "parcels": "Parcel", "zingy parcel": "Parcel",
    "calzone": "Calzone", "calzones": "Calzone", "pocket calzone": "Calzone",
    "starter": "Starter", "starters": "Starter", "snacks": "Starter",
    "appetizer": "Starter", "appetizers": "Starter",
    "fries": "Fries", "french fries": "Fries",
    "burger": "Burger", "burgers": "Burger",
    "momo": "Momo", "momos": "Momo",
    "farali": "Farali", "fasting": "Farali", "upvas": "Farali",
    "beverage": "Beverage", "beverages": "Beverage", "drink": "Beverage",
    "drinks": "Beverage", "shake": "Beverage", "shakes": "Beverage",
    "coolers": "Beverage", "cold coffee": "Beverage",
    "mocktail": "Mocktail", "mocktails": "Mocktail",
    "dessert": "Dessert", "desserts": "Dessert", "sweet": "Dessert",
}


def find_category(text: str):
    t = (text or "").lower()
    for alias, cat in sorted(CATEGORY_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if _alias_matches(t, alias):
            return cat
    return None
