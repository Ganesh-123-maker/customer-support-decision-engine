"""Regression Test Suite.

Contains explicit regression tests for every bug, edge-case, and ambiguity resolved
during implementation and testing:
1. `processing` order status treated as pre-dispatch cancellation.
2. "does not function correctly" phrasing for defective products.
3. "stopped working" phrasing for defective products.
4. "does not work" phrasing for defective products.
5. "different from what I ordered" phrasing for wrong item claims.
6. "instead of" phrasing for wrong item claims.
7. "still not here" phrasing for shipping delay inquiry.
8. "no delivery" phrasing for shipping delay inquiry.
9. Intent precedence: cancellation request with shipping/tracking mentions on dispatched orders.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def decide(payload: dict) -> dict:
    resp = client.post("/decide", json=payload)
    assert resp.status_code == 200
    return resp.json()


def test_regression_order_status_processing():
    """Bug 1: 'processing' order status previously normalized to unknown -> NEEDS_MORE_INFORMATION.

    Fix: 'processing' is recognized as pre-dispatch status eligible for CANCEL_AND_REFUND.
    """
    res = decide({
        "message": "Please cancel my order. It has not been dispatched yet.",
        "order_status": "processing",
        "order_value_inr": 999,
    })
    assert res["action"] == "CANCEL_AND_REFUND"
    assert res["issue_type"] == "cancellation"


def test_regression_defective_does_not_function():
    """Bug 2: 'does not function correctly' was unmapped in defect keywords.

    Fix: Added 'does not function' to _DEFECT_KEYWORDS.
    """
    res = decide({
        "message": "The product turns on but does not function correctly.",
        "order_value_inr": 2499,
        "days_since_delivery": 14,
        "product_type": "non_food",
        "opened_status": "opened",
        "order_status": "delivered",
    })
    assert res["action"] == "APPROVE_REPLACEMENT"
    assert res["issue_type"] == "defective"


def test_regression_defective_stopped_working():
    """Bug 3: 'has stopped working' was unmapped in defect keywords.

    Fix: Added 'stopped working' to _DEFECT_KEYWORDS.
    """
    res = decide({
        "message": "The device has stopped working and I want a replacement.",
        "order_value_inr": 2499,
        "days_since_delivery": 18,
        "product_type": "non_food",
        "opened_status": "opened",
        "order_status": "delivered",
    })
    assert res["action"] == "REJECT_OUTSIDE_WINDOW"
    assert res["issue_type"] == "defective"


def test_regression_defective_does_not_work():
    """Bug 4: 'does not work' was missing from _DEFECT_KEYWORDS.

    Fix: Added 'does not work' to _DEFECT_KEYWORDS.
    """
    res = decide({
        "message": "The left earbud does not work and has no sound.",
        "order_value_inr": 1800,
        "days_since_delivery": 8,
        "product_type": "non_food",
        "opened_status": "opened",
        "order_status": "delivered",
    })
    assert res["action"] == "APPROVE_REPLACEMENT"
    assert res["issue_type"] == "defective"


def test_regression_wrong_item_different_from_ordered():
    """Bug 5: 'flavour in the box is different from what I ordered' was unmapped.

    Fix: Added 'different from what I ordered' and 'different flavour' to _WRONG_ITEM_KEYWORDS.
    """
    res = decide({
        "message": "The flavour in the box is different from what I ordered.",
        "order_value_inr": 399,
        "days_since_delivery": 0,
        "product_type": "food",
        "opened_status": "unopened",
        "order_status": "delivered",
    })
    assert res["action"] == "REPLACE_CORRECT_ITEM"
    assert res["issue_type"] == "wrong_item"


def test_regression_wrong_item_instead_of():
    """Bug 6: 'Received X instead of Y' was unmapped in wrong item keywords.

    Fix: Added 'instead of' to _WRONG_ITEM_KEYWORDS.
    """
    res = decide({
        "message": "Received almond milk instead of oat milk 12 days ago.",
        "order_value_inr": 600,
        "days_since_delivery": 12,
        "product_type": "food",
        "order_status": "delivered",
    })
    assert res["action"] == "REJECT_OUTSIDE_WINDOW"
    assert res["issue_type"] == "wrong_item"


def test_regression_shipping_delay_still_not_here():
    """Bug 7: 'still not here' was unmapped in shipping keywords.

    Fix: Added 'still not here' and 'not here' to _SHIPPING_KEYWORDS.
    """
    res = decide({
        "message": "Order dispatched 10 days ago, still not here",
        "order_value_inr": 850,
        "days_since_dispatch": 10,
        "order_status": "dispatched",
        "product_type": "non_food",
    })
    assert res["action"] == "OPEN_SHIPPING_INVESTIGATION"
    assert res["issue_type"] == "shipping_delay"


def test_regression_shipping_delay_no_delivery():
    """Bug 8: 'no delivery' was unmapped in shipping keywords.

    Fix: Added 'no delivery' and 'since dispatch' to _SHIPPING_KEYWORDS.
    """
    res = decide({
        "message": "It's been 11 days since dispatch and no delivery",
        "order_value_inr": 850,
        "days_since_dispatch": 11,
        "order_status": "dispatched",
        "product_type": "non_food",
    })
    assert res["action"] == "OFFER_REPLACEMENT_OR_REFUND"
    assert res["issue_type"] == "shipping_delay"


def test_regression_cancellation_tracking_precedence():
    """Bug 9: Message mentions tracking/shipped while asking to cancel -> shipping delay took over.

    Fix: Cancellation intent takes precedence so post-dispatch cancellation correctly returns
    CANNOT_CANCEL_AFTER_DISPATCH.
    """
    res = decide({
        "message": "I want to cancel my order but tracking says it has already shipped.",
        "order_status": "dispatched",
        "days_since_dispatch": 2,
    })
    assert res["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"
    assert res["issue_type"] == "cancellation"
