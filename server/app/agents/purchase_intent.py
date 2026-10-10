"""Catalog-grounded purchase intent. Generative output is never purchase authority."""
import re
from decimal import Decimal
from typing import Any

# Families deliberately separate unrelated products sharing a database category.
FAMILIES = {
    "monitor": r"monitors?|displays?",
    "keyboard": r"keyboards?",
    "mouse": r"mouse|mice",
    "hub": r"(?:usb[ -]?c\s+)?hubs?|docking\s+stations?",
    "desk_mat": r"desk\s+mats?|cable\s+organizers?",
    "coffee": r"coffee|(?:arabica\s+)?beans?",
    "compute": r"(?:gpu\s+)?(?:cloud\s+)?compute\s+(?:credits?|packs?)|gpu\s+(?:cloud|hours?|credits?)|cloud\s+credits?",
    "headphones": r"headphones?|headsets?",
    "motherboard": r"motherboards?",
}
CATEGORIES = {"monitor": "monitors", "keyboard": "keyboards", "mouse": "mice", "hub": "accessories", "desk_mat": "accessories", "coffee": "subscriptions", "compute": "subscriptions", "headphones": "electronics", "motherboard": "electronics"}
BUDGET = re.compile(r"(?:under|below|max(?:imum)?|budget(?:\s+of)?|within|upto|up\s+to|less\s+than)\s*(?:of\s+)?(?:₹|inr|rs\.?)?\s*(-?\d[\d,]*(?:\.\d+)?)(\s*[kl]\b|\s*lakh\b)?", re.I)
NEGATION = re.compile(r"\b(?:do\s+not|don't|dont|without|exclude|excluding|no)\b", re.I)


def families(text: str) -> list[str]:
    return [name for name, pattern in FAMILIES.items() if re.search(r"\b(?:" + pattern + r")\b", text, re.I)]


def parse_purchase_intent(text: str, cap: float) -> dict[str, Any]:
    text = text.strip()
    budgets = [Decimal(str(cap))]
    for match in BUDGET.finditer(text):
        value = Decimal(match[1].replace(",", ""))
        suffix = (match[2] or "").strip().lower()
        value *= 100000 if suffix in ("l", "lakh") else 1000 if suffix == "k" else 1
        if value <= 0:
            raise ValueError("The budget in your request must be greater than zero.")
        budgets.append(value)
    clean = BUDGET.sub("", text.lower())
    # Exclusions are constraints, never positive product requests.
    clauses = re.split(r"\s*(?:;|\band\b|\+|,(?!\d))\s*", clean)
    positive, excluded, unresolved = [], [], []
    for clause in clauses:
        parts = NEGATION.split(clause, maxsplit=1)
        if len(parts) > 1:
            excluded.extend(families(parts[1]))
        part = parts[0].strip()
        if not part:
            continue
        positive.append(part)
        if not families(part) and not re.search(r"\bitem_[a-z0-9_]+\b", part):
            unresolved.append(part)
    requested = list(dict.fromkeys(families(" ".join(positive))))
    quantity_pattern = r"(?<!\w)(?:0|[2-9]|[1-9]\d+|-\d+|two|three|four|five|six|seven|eight|nine|ten|multiple|several|pair\s+of)\s+(?:(?:ergonomic|wireless|mechanical|4k|usb-c)\s+){0,3}(?:" + "|".join(FAMILIES.values()) + r")\b"
    quantity_unsupported = bool(re.search(quantity_pattern, clean, re.I))
    quantity_unsupported |= any(sum(f in families(p) for p in positive) > 1 for f in requested)
    if re.search(r"\b(?:or|either|usd|eur|dollars?|euros?)\b|[$€]", clean):
        unresolved.append("Choose specific products and use an INR budget.")
    return {"target_categories": list(dict.fromkeys(CATEGORIES[f] for f in requested)), "target_skus": re.findall(r"\bitem_[a-z0-9_]+\b", clean), "requested_families": requested, "excluded_families": excluded, "specs_filter": {}, "effective_budget": float(min(budgets)), "raw_goal": text, "positive_goal": " and ".join(positive), "unresolved_clauses": unresolved, "quantity_unsupported": quantity_unsupported, "strict_items_only": bool(excluded or re.search(r"\b(?:only|no\s+(?:extras|add-ons|upsells))\b", clean))}


def select_products(products, intent):
    """One explicitly requested SKU per family; never convert candidates into a cart."""
    if intent["quantity_unsupported"] or intent["unresolved_clauses"]:
        return []
    query = intent["positive_goal"]
    requested = intent["requested_families"]
    excluded = intent["excluded_families"]
    if set(requested) & set(excluded):
        return []
    available = [p for p in products if p.stock_quantity > 0 and p.retail_price <= intent["effective_budget"]]
    if intent["target_skus"]:
        found = [p for p in available if p.sku in intent["target_skus"]]
        return found if len(found) == len(set(intent["target_skus"])) and not requested else []
    if not requested:
        return []
    chosen = []
    for family in requested:
        candidates = [p for p in available if family in families(p.name)]
        # Honor explicit hardware constraints and named variants that the catalog supports.
        constraints = re.findall(r"\b(?:4k|1080p|1440p|\d+\s*hz|wireless|anc|ddr[45]|z790|lga1700|usb[ -]?c)\b", query)
        family_query = " ".join(c for c in re.split(r"\band\b|;|\+", query) if family in families(c))
        constraints = [c for c in constraints if c in family_query]
        variants = [word for word in ("creator", "ultraview", "ergotype", "mastergrip", "studiomaster", "gigabyte", "aorus", "elite", "xtreme", "pro", "split", "alice") if re.search(r"\b" + word + r"\b", family_query)]
        def matches(p):
            content = (p.name + " " + (p.description or "") + " " + (p.specifications or "")).lower()
            normalized = re.sub(r"[ -]", "", content)
            return all(re.sub(r"[ -]", "", c) in normalized for c in constraints) and all(re.search(r"\b" + v + r"\b", p.name.lower()) for v in variants)
        candidates = [p for p in candidates if matches(p)]
        if not candidates:
            return []  # A multi-item request must not silently become a partial purchase.
        chosen.append(min(candidates, key=lambda p: (p.retail_price, p.sku)))
    return chosen
