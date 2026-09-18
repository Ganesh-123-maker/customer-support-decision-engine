"""Deterministic policy engine.

Each policy is implemented as a pure function that takes TicketFacts and returns
an (Action, explanation) tuple or None if the policy does not apply.

The engine evaluates the applicable policy based on the detected issue_type.
All thresholds match the knowledge-base documents exactly.
"""

from __future__ import annotations

from typing import Optional

from app.models import (
    Action,
    IssueType,
    OpenedStatus,
    OrderStatus,
    ProductType,
    TicketFacts,
)


def evaluate_damaged_goods(facts: TicketFacts) -> tuple[Action, str]:
    """Damaged Goods Policy (knowledge_base/damaged_goods.md).

    1. Damage must be reported within 7 calendar days of delivery.
    2. Orders ≤ ₹2,000 → refund/replacement without photos.
    3. Orders > ₹2,000 → request photos first.
    4. > 7 days → reject outside window.
    5. Missing info → needs more information.
    """
    if facts.days_since_delivery is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Cannot determine when the order was delivered. "
            "Please provide the delivery date to assess the damage claim.",
        )

    if facts.days_since_delivery > 7:
        return (
            Action.REJECT_OUTSIDE_WINDOW,
            f"Damage was reported {facts.days_since_delivery} days after delivery, "
            f"which exceeds the 7-day window for the damaged-goods policy.",
        )

    # Within 7 days
    if facts.order_value_inr is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Order value is required to determine whether photographic evidence "
            "is needed. Please provide the order value.",
        )

    if facts.order_value_inr <= 2000:
        return (
            Action.APPROVE_REFUND_OR_REPLACEMENT,
            f"Order valued at ₹{facts.order_value_inr:,.0f} (≤ ₹2,000) reported "
            f"damaged within {facts.days_since_delivery} day(s). Eligible for "
            f"refund or replacement without photographic evidence.",
        )
    else:
        return (
            Action.REQUEST_PHOTOS,
            f"Order valued at ₹{facts.order_value_inr:,.0f} (> ₹2,000) reported "
            f"damaged within {facts.days_since_delivery} day(s). Photographs of "
            f"the damaged product and packaging are required before approval.",
        )


def evaluate_defective_product(facts: TicketFacts) -> tuple[Action, str]:
    """Defective Product Policy (knowledge_base/defective_products.md).

    1. Functional defect within 14 days → eligible for replacement.
    2. Orders > ₹3,000 → request evidence before replacement.
    3. > 14 days → reject outside window.
    4. Cosmetic damage → redirect to Damaged Goods Policy.
    5. Missing info → needs more information.
    """
    if facts.days_since_delivery is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Cannot determine the delivery date. Please provide it so we can "
            "assess the defect claim.",
        )

    if facts.days_since_delivery > 14:
        return (
            Action.REJECT_OUTSIDE_WINDOW,
            f"Defect reported {facts.days_since_delivery} days after delivery, "
            f"which exceeds the 14-day window for the defective product policy.",
        )

    # Within 14 days
    if facts.order_value_inr is not None and facts.order_value_inr > 3000:
        return (
            Action.REQUEST_DEFECT_EVIDENCE,
            f"Order valued at ₹{facts.order_value_inr:,.0f} (> ₹3,000) with "
            f"defect reported within {facts.days_since_delivery} day(s). "
            f"Basic evidence of the defect is required before replacement.",
        )
    else:
        return (
            Action.APPROVE_REPLACEMENT,
            f"Functional defect reported within {facts.days_since_delivery} day(s) "
            f"of delivery. Eligible for replacement.",
        )


def evaluate_returns(facts: TicketFacts) -> tuple[Action, str]:
    """Returns Policy (knowledge_base/returns.md).

    1. Unopened non-food → return within 14 days.
    2. Opened non-food → reject.
    3. Food → reject (even if unopened).
    4. Damaged/defective → redirect.
    5. Missing info → needs more information.
    """
    # If product is damaged or defective, those policies apply instead
    if facts.mentions_damage:
        return evaluate_damaged_goods(facts)
    if facts.mentions_defect:
        return evaluate_defective_product(facts)

    # Check for missing info needed for return decision
    if facts.product_type in (ProductType.UNKNOWN, ProductType.MIXED):
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Product type is required to determine return eligibility. "
            "Please specify whether this is a food or non-food product.",
        )

    if facts.product_type == ProductType.FOOD:
        return (
            Action.REJECT_FOOD_RETURN,
            "Food products are not eligible for change-of-mind returns after delivery.",
        )

    # Non-food
    if facts.opened_status == OpenedStatus.UNKNOWN:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Please confirm whether the product has been opened. "
            "This is needed to determine return eligibility.",
        )

    if facts.opened_status == OpenedStatus.OPENED:
        return (
            Action.REJECT_OPENED_ITEM,
            "Opened non-food products are not eligible for change-of-mind returns.",
        )

    # Unopened non-food
    if facts.days_since_delivery is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Delivery date is required to confirm the return is within the "
            "14-day window. Please provide when the order was delivered.",
        )

    if facts.days_since_delivery > 14:
        return (
            Action.REJECT_OUTSIDE_WINDOW,
            f"Return requested {facts.days_since_delivery} days after delivery, "
            f"which exceeds the 14-day return window.",
        )

    return (
        Action.APPROVE_RETURN,
        f"Unopened non-food product returned within {facts.days_since_delivery} "
        f"day(s) of delivery. Eligible for return.",
    )


def evaluate_cancellation(facts: TicketFacts) -> tuple[Action, str]:
    """Cancellation Policy (knowledge_base/cancellations.md).

    1. Before dispatch → cancel and refund.
    2. After dispatch → cannot cancel; redirect to other policies.
    3. Delivered → cannot cancel.
    4. Unknown status → needs more information.
    """
    if facts.order_status == OrderStatus.UNKNOWN:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Order dispatch status is unknown. Please provide the current "
            "order status to determine cancellation eligibility.",
        )

    if facts.order_status in (OrderStatus.PENDING, OrderStatus.PROCESSING):
        return (
            Action.CANCEL_AND_REFUND,
            "Order has not been dispatched yet. Cancellation approved with full refund.",
        )

    # Dispatched or delivered
    return (
        Action.CANNOT_CANCEL_AFTER_DISPATCH,
        "Order has already been dispatched and cannot be cancelled. "
        "Please use the returns, damaged-goods, or wrong-item process instead.",
    )


def evaluate_wrong_item(facts: TicketFacts) -> tuple[Action, str]:
    """Wrong Item Policy (knowledge_base/wrong_item.md).

    1. Report within 7 days → replace correct item.
    2. > 7 days → reject outside window.
    3. Missing what was ordered vs received → needs more info.
    """
    if facts.what_was_ordered is None and facts.what_was_received is None:
        # Check if the message at least indicates a wrong item was received
        if not facts.mentions_wrong_item:
            return (
                Action.NEEDS_MORE_INFORMATION,
                "Please specify what you ordered and what you received "
                "so we can process your wrong-item claim.",
            )

    if facts.days_since_delivery is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Delivery date is required to confirm the report is within the "
            "7-day window. Please provide when the order was delivered.",
        )

    if facts.days_since_delivery > 7:
        return (
            Action.REJECT_OUTSIDE_WINDOW,
            f"Wrong item reported {facts.days_since_delivery} days after delivery, "
            f"which exceeds the 7-day window for the wrong-item policy.",
        )

    return (
        Action.REPLACE_CORRECT_ITEM,
        f"Wrong item reported within {facts.days_since_delivery} day(s) of delivery. "
        f"A replacement of the correct item will be sent.",
    )


def evaluate_shipping(facts: TicketFacts) -> tuple[Action, str]:
    """Shipping and Delivery Policy (knowledge_base/shipping.md).

    1. Expected within 5 days after dispatch.
    2. 6-7 days → advise wait and track.
    3. 8-10 days → open shipping investigation.
    4. > 10 days → offer replacement or refund.
    5. Missing info → needs more information.
    """
    if facts.days_since_dispatch is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Dispatch date is required to assess the shipping delay. "
            "Please provide when the order was dispatched.",
        )

    if facts.days_since_dispatch <= 5:
        return (
            Action.WAIT_AND_TRACK,
            f"Order dispatched {facts.days_since_dispatch} day(s) ago, which is "
            f"within the expected 5-day delivery window. Please continue tracking.",
        )

    if facts.days_since_dispatch <= 7:
        return (
            Action.WAIT_AND_TRACK,
            f"Order dispatched {facts.days_since_dispatch} day(s) ago. "
            f"Please wait and continue tracking the shipment.",
        )

    if facts.days_since_dispatch <= 10:
        return (
            Action.OPEN_SHIPPING_INVESTIGATION,
            f"Order dispatched {facts.days_since_dispatch} day(s) ago without "
            f"delivery. Opening a shipping investigation.",
        )

    # > 10 days
    return (
        Action.OFFER_REPLACEMENT_OR_REFUND,
        f"Order dispatched {facts.days_since_dispatch} day(s) ago without "
        f"delivery (exceeds 10 days). Offering replacement or refund.",
    )


# ---------------------------------------------------------------------------
# Main evaluation dispatcher
# ---------------------------------------------------------------------------

_POLICY_DISPATCH: dict[IssueType, callable] = {
    IssueType.DAMAGED: evaluate_damaged_goods,
    IssueType.DEFECTIVE: evaluate_defective_product,
    IssueType.RETURN: evaluate_returns,
    IssueType.CANCELLATION: evaluate_cancellation,
    IssueType.WRONG_ITEM: evaluate_wrong_item,
    IssueType.SHIPPING_DELAY: evaluate_shipping,
}


def evaluate(facts: TicketFacts) -> tuple[Action, str]:
    """Evaluate the applicable policy for the given ticket facts.

    Returns (action, explanation).
    """
    if facts.issue_type == IssueType.UNKNOWN:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "Could not determine the issue type from the provided information. "
            "Please describe your issue in more detail.",
        )

    policy_fn = _POLICY_DISPATCH.get(facts.issue_type)
    if policy_fn is None:
        return (
            Action.NEEDS_MORE_INFORMATION,
            "No applicable policy found for this issue type. "
            "Please provide more details.",
        )

    return policy_fn(facts)
