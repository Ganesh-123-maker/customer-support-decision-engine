"""Extracts structured facts from natural-language customer messages and metadata.

Uses keyword/pattern matching for deterministic extraction — no LLM required.
"""

from __future__ import annotations

import re
from typing import Optional

from app.models import (
    IssueType,
    OpenedStatus,
    OrderStatus,
    ProductType,
    TicketFacts,
    TicketInput,
)

# ---------------------------------------------------------------------------
# Keyword / pattern sets
# ---------------------------------------------------------------------------

_DAMAGE_KEYWORDS = [
    "damaged", "damage", "broken", "crushed", "cracked", "shattered",
    "dented", "torn", "smashed", "scratched", "bent", "chipped",
    "ripped", "destroyed", "battered",
]

_DEFECT_KEYWORDS = [
    "defective", "defect", "malfunction", "not working", "doesn't work",
    "won't turn on", "stops working", "stopped working", "faulty", "fault",
    "doesn't function", "does not function", "not functioning", "stopped functioning",
    "dead on arrival", "doa", "won't start", "does not turn on", "doesn't turn on",
    "stops functioning", "malfunctioning", "non-functional",
]

_WRONG_ITEM_KEYWORDS = [
    "wrong item", "wrong product", "wrong colour", "wrong color",
    "wrong size", "wrong flavour", "wrong flavor", "wrong variant",
    "received different", "got different", "sent wrong", "incorrect item",
    "not what i ordered", "not what I ordered", "ordered .+ but received",
    "ordered .+ but got", "ordered .+ received", "different from what i ordered",
    "different from what I ordered", "different flavour", "different flavor",
    "different item", "sent me the wrong", "received the wrong",
]

_RETURN_KEYWORDS = [
    "return", "changed my mind", "change of mind", "don't want",
    "no longer need", "want to send back", "send it back",
    "want my money back", "refund",
]

_CANCEL_KEYWORDS = [
    "cancel", "cancellation", "cancel my order", "don't want this order",
    "stop my order", "withdraw my order",
]

_SHIPPING_KEYWORDS = [
    "not arrived", "hasn't arrived", "hasn't been delivered",
    "has not arrived", "not delivered", "still waiting",
    "where is my order", "where's my order", "missing delivery",
    "missing parcel", "missing package", "not received",
    "haven't received", "have not received", "still not arrived",
    "never arrived", "lost in transit", "lost package", "lost parcel",
    "delayed", "delay", "tracking", "in transit", "not here", "still not here",
    "no delivery", "delivery", "since dispatch", "days since dispatch",
]

_FOOD_KEYWORDS = [
    "food", "chocolate", "strawberry", "vanilla", "cookie", "cookies",
    "biscuit", "biscuits", "cake", "snack", "snacks", "candy", "sweets",
    "chips", "juice", "drink", "beverage", "flavour", "flavor",
    "perishable", "edible", "grocery", "groceries", "fruit", "fruits",
    "meat", "dairy", "milk", "cheese", "bread", "tea", "coffee",
    "spice", "spices", "sauce", "pasta", "rice", "cereal",
    "ice cream", "yogurt", "butter", "jam", "honey",
]

_NON_FOOD_KEYWORDS = [
    "non-food", "non food", "nonfood", "electronics", "electronic",
    "device", "gadget", "phone", "laptop", "tablet", "headphones",
    "earphones", "charger", "cable", "clothing", "clothes", "shirt",
    "shoes", "shoe", "book", "books", "furniture", "toy", "toys",
    "appliance", "kitchen appliance", "watch", "bag", "backpack",
    "accessory", "accessories", "cosmetics", "beauty", "skincare",
]

_OPENED_KEYWORDS = ["opened", "open", "used", "tried", "tested", "wore"]
_UNOPENED_KEYWORDS = ["unopened", "sealed", "still in packaging", "still packed",
                      "not opened", "never opened", "in original packaging",
                      "still in box", "untouched"]


def _text_contains(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords (supports simple regex)."""
    for kw in keywords:
        if "." in kw or "+" in kw or "*" in kw:
            if re.search(kw, text, re.IGNORECASE):
                return True
        else:
            if kw.lower() in text:
                return True
    return False


def _extract_currency(text: str) -> Optional[float]:
    """Extract INR amount from text like ₹3,500, Rs. 3500, 3500 rupees, 3500/-, INR 3500."""
    patterns = [
        r"₹\s?([\d,]+(?:\.\d+)?)",
        r"Rs\.?\s?([\d,]+(?:\.\d+)?)",
        r"INR\s?([\d,]+(?:\.\d+)?)",
        r"([\d,]+(?:\.\d+)?)\s?(?:rupees|inr|rs\.?|/-)",
        r"(?:cost|paid|worth|price(?:\s+is)?|valued\s+at)\s+(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _extract_days(text: str) -> Optional[int]:
    """Extract days count from phrases like '2 days ago', 'yesterday', 'today', 'after 10 days'."""
    if re.search(r"\byesterday\b", text, re.IGNORECASE):
        return 1
    if re.search(r"\btoday\b", text, re.IGNORECASE):
        return 0
    patterns = [
        r"(\d+)\s*(?:calendar\s+)?days?\s*(?:ago|back|since|old)",
        r"(?:arrived|delivered|received|dispatched|shipped)\s+(\d+)\s+days?\s+ago",
        r"(?:after|past|been)\s+(\d+)\s*(?:calendar\s+)?days?",
        r"(\d+)\s*(?:calendar\s+)?days?\s*(?:have\s+passed|passed)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _extract_wrong_item_details(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract what was ordered vs received for wrong-item cases."""
    patterns = [
        r"ordered\s+(.+?)\s+but\s+(?:received|got)\s+(.+?)(?:\.|$|,)",
        r"ordered\s+(.+?)\s+(?:received|got)\s+(.+?)(?:\.|$|,)",
        r"wanted\s+(.+?)\s+but\s+(?:received|got)\s+(.+?)(?:\.|$|,)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    return None, None


def _detect_issue_type(text: str, facts: TicketFacts) -> IssueType:
    """Determine issue type from extracted signals using explicit policy precedence.

    Precedence hierarchy (derived strictly from the knowledge base rules):
    1. Cancellation: Customer requests to cancel an order. Cancellation policy
       determines whether pre-dispatch (full refund) or post-dispatch (redirect).
    2. Wrong Item: Customer received wrong variant/flavour/item (specific fulfillment error).
    3. Damaged Goods: Physical/cosmetic damage (7-day window). Per defective_products.md rule 4
       ('Cosmetic damage should be evaluated under Damaged Goods') and returns.md rule 4
       ('Damaged or defective products are handled under Damaged Goods'), damage takes precedence.
    4. Defective Product: Functional defects (14-day window). Per returns.md rule 4, defect takes
       precedence over general change-of-mind returns.
    5. Shipping Delay: Delivery delay, transit status, or missing shipment queries.
    6. Return: Change-of-mind return request.
    7. Unknown: No recognized policy applies or information is insufficient.
    """
    if facts.mentions_cancellation:
        return IssueType.CANCELLATION

    if facts.mentions_wrong_item:
        return IssueType.WRONG_ITEM

    if facts.mentions_damage:
        return IssueType.DAMAGED

    if facts.mentions_defect:
        return IssueType.DEFECTIVE

    if facts.mentions_shipping_delay or (
        facts.days_since_dispatch is not None and facts.order_status == OrderStatus.DISPATCHED
    ):
        return IssueType.SHIPPING_DELAY

    if facts.mentions_return:
        return IssueType.RETURN

    return IssueType.UNKNOWN


def _normalize_enum(value: Optional[str], enum_type: type) -> str:
    """Normalize a string to an enum value, defaulting to 'unknown'."""
    if value is None:
        return "unknown"
    val = value.strip().lower()
    try:
        return enum_type(val).value
    except ValueError:
        return "unknown"


def extract_facts(ticket: TicketInput) -> TicketFacts:
    """Extract structured facts from a TicketInput (message + metadata)."""
    text = ticket.message.lower()

    # Signal detection
    mentions_damage = _text_contains(text, _DAMAGE_KEYWORDS)
    mentions_defect = _text_contains(text, _DEFECT_KEYWORDS)
    mentions_wrong_item = _text_contains(text, _WRONG_ITEM_KEYWORDS)
    mentions_return = _text_contains(text, _RETURN_KEYWORDS)
    mentions_cancellation = _text_contains(text, _CANCEL_KEYWORDS)
    mentions_shipping = _text_contains(text, _SHIPPING_KEYWORDS)

    # Product type from metadata or text
    product_type_str = _normalize_enum(ticket.product_type, ProductType)
    if product_type_str == "unknown":
        if _text_contains(text, _FOOD_KEYWORDS) and not _text_contains(text, _NON_FOOD_KEYWORDS):
            product_type_str = "food"
        elif _text_contains(text, _NON_FOOD_KEYWORDS) and not _text_contains(text, _FOOD_KEYWORDS):
            product_type_str = "non_food"

    # Opened status from metadata or text
    opened_str = _normalize_enum(ticket.opened_status, OpenedStatus)
    if opened_str == "unknown":
        if _text_contains(text, _UNOPENED_KEYWORDS):
            opened_str = "unopened"
        elif _text_contains(text, _OPENED_KEYWORDS):
            opened_str = "opened"

    # Order status
    order_status_str = _normalize_enum(ticket.order_status, OrderStatus)

    # Days values — prefer metadata, fallback to NLP extraction
    days_since_delivery = ticket.days_since_delivery
    days_since_dispatch = ticket.days_since_dispatch

    if days_since_delivery is None and days_since_dispatch is None:
        extracted = _extract_days(ticket.message)
        if extracted is not None:
            if order_status_str == "dispatched":
                days_since_dispatch = extracted
            else:
                days_since_delivery = extracted

    # Order value — prefer metadata, fallback to NLP extraction
    order_value = ticket.order_value_inr
    if order_value is None:
        order_value = _extract_currency(ticket.message)

    # Wrong item details
    what_ordered, what_received = _extract_wrong_item_details(ticket.message)

    facts = TicketFacts(
        order_value_inr=order_value,
        days_since_delivery=days_since_delivery,
        days_since_dispatch=days_since_dispatch,
        product_type=ProductType(product_type_str),
        opened_status=OpenedStatus(opened_str),
        order_status=OrderStatus(order_status_str),
        mentions_damage=mentions_damage,
        mentions_defect=mentions_defect,
        mentions_wrong_item=mentions_wrong_item,
        mentions_return=mentions_return,
        mentions_cancellation=mentions_cancellation,
        mentions_shipping_delay=mentions_shipping,
        what_was_ordered=what_ordered,
        what_was_received=what_received,
    )

    # Detect issue type
    facts.issue_type = _detect_issue_type(text, facts)

    return facts
