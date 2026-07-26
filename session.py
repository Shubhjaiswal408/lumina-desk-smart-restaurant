"""Per-table session state: the cart and bill math.

In-memory for the MVP; one instance per running device = one table.
"""
import menu


class Session:
    def __init__(self):
        # cart: list of {"dish": <menu dict>, "qty": int}
        self.cart = []
        self.staff_called = False
        # Last dish discussed/suggested, so "add it" / "what's in it" resolve.
        self.last_dish = None
        # Rolling chat history for the LLM: [{"role","content"}, ...]
        self.history = []

    @classmethod
    def from_items(cls, items):
        """Rebuild a session from published [{name, qty}] (for the display
        service). Dish details come from the menu, so facts stay authoritative."""
        s = cls()
        for it in items:
            dish = menu.find_dish(it["name"])
            if dish:
                s.add_dish(dish, int(it.get("qty", 1)), it.get("size"))
        return s

    def add_dish(self, dish: dict, qty: int, size=None) -> None:
        """Add `qty` of a dish. A sized dish (pizza size, burger cheese variant,
        momo style) keeps each size as its own cart line — they're priced
        differently, so a Large and a Regular can't share a line."""
        if size is None:
            size = menu.default_size(dish)
        for line in self.cart:
            if line["dish"]["name"] == dish["name"] and line.get("size") == size:
                line["qty"] += qty
                return
        self.cart.append({"dish": dish, "qty": qty, "size": size})

    def clear(self) -> None:
        self.cart = []
        self.last_dish = None

    def remove_dish(self, dish: dict) -> bool:
        """Remove a dish entirely from the cart. Returns True if it was there."""
        before = len(self.cart)
        self.cart = [l for l in self.cart if l["dish"]["name"] != dish["name"]]
        return len(self.cart) != before

    def decrement_dish(self, dish: dict, qty: int) -> bool:
        """Reduce a dish's quantity; drop the line if it hits zero."""
        for l in self.cart:
            if l["dish"]["name"] == dish["name"]:
                l["qty"] -= qty
                if l["qty"] <= 0:
                    self.cart.remove(l)
                return True
        return False

    def remember(self, role: str, content: str, keep: int = 12) -> None:
        self.history.append({"role": role, "content": content})
        self.history = self.history[-keep:]

    def is_empty(self) -> bool:
        return not self.cart

    def line_price(self, line) -> int:
        """Unit price for a cart line, in its chosen size."""
        return menu.price_for(line["dish"], line.get("size"))

    def subtotal(self) -> float:
        # Uses live prices so admin menu edits are reflected in the bill.
        return sum(self.line_price(l) * l["qty"] for l in self.cart)

    def tax(self) -> float:
        """GST on the order. In 'inclusive' mode this is the portion already
        contained in the menu prices (shown for the record, not added on top).
        Mode and rate come from Settings so a manager can change them live."""
        sub = self.subtotal()
        mode, rate = menu.tax_config()
        if mode == "none":
            return 0.0
        if mode == "inclusive":
            return round(sub - sub / (1 + rate), 2)
        return round(sub * rate, 2)

    def total(self) -> float:
        """What the guest actually pays."""
        sub = self.subtotal()
        if menu.tax_config()[0] == "exclusive":
            return round(sub + self.tax(), 2)
        return round(sub, 2)          # inclusive / none -> menu price is final

    def est_prep_time(self, kitchen_load: int = 0) -> int:
        """Minutes until the whole order is ready.

        The kitchen cooks in parallel, so the slowest dish sets the floor. Each
        extra *portion* (not just each line) adds a little, because 3 biryanis
        take longer than 1. `kitchen_load` is the number of portions already
        queued at other tables, which pushes every new order back a bit.
        """
        if not self.cart:
            return 0
        slowest = max(menu.prep_minutes(l["dish"]) for l in self.cart)
        portions = sum(l["qty"] for l in self.cart)
        eta = slowest + 1.5 * (portions - 1) + 0.5 * max(0, kitchen_load)
        return int(min(round(eta), slowest * 2 + 20))   # never promise absurd times

    def line_label(self, line) -> str:
        """'2 Large Margherita' — size first, the way a waiter would say it."""
        size = line.get("size")
        return f'{size} {line["dish"]["name"]}' if size else line["dish"]["name"]

    def line_summary(self) -> str:
        parts = [f'{line["qty"]} {self.line_label(line)}' for line in self.cart]
        if len(parts) > 1:
            return ", ".join(parts[:-1]) + " and " + parts[-1]
        return parts[0] if parts else ""
