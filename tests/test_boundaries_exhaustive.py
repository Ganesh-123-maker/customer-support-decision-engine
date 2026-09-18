"""Exhaustive boundary testing across all thresholds defined in knowledge base policies.

For every numerical threshold:
- threshold - 1
- threshold
- threshold + 1
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def decide(payload: dict) -> dict:
    resp = client.post("/decide", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ===================================================================
# 1. DAMAGED GOODS THRESHOLDS: 7 Days & ₹2,000
# ===================================================================


class TestDamagedGoodsBoundaries:
    """Damaged goods: 7 calendar days; ₹2,000 order value."""

    @pytest.mark.parametrize(
        "days,expected_action",
        [
            (6, "APPROVE_REFUND_OR_REPLACEMENT"),  # threshold - 1 (within window)
            (7, "APPROVE_REFUND_OR_REPLACEMENT"),  # threshold (boundary day)
            (8, "REJECT_OUTSIDE_WINDOW"),          # threshold + 1 (outside window)
        ],
    )
    def test_damage_delivery_days_boundary(self, days, expected_action):
        res = decide({
            "message": "Order arrived damaged",
            "order_value_inr": 1500,
            "days_since_delivery": days,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action

    @pytest.mark.parametrize(
        "value,expected_action",
        [
            (1999, "APPROVE_REFUND_OR_REPLACEMENT"),  # threshold - 1 (no photos)
            (2000, "APPROVE_REFUND_OR_REPLACEMENT"),  # threshold (≤ 2000, no photos)
            (2001, "REQUEST_PHOTOS"),                  # threshold + 1 (> 2000, photos required)
        ],
    )
    def test_damage_order_value_boundary(self, value, expected_action):
        res = decide({
            "message": "Product broken on arrival",
            "order_value_inr": value,
            "days_since_delivery": 3,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action


# ===================================================================
# 2. DEFECTIVE PRODUCTS THRESHOLDS: 14 Days & ₹3,000
# ===================================================================


class TestDefectiveProductBoundaries:
    """Defective products: 14 calendar days; ₹3,000 order value."""

    @pytest.mark.parametrize(
        "days,expected_action",
        [
            (13, "APPROVE_REPLACEMENT"),   # threshold - 1 (within window)
            (14, "APPROVE_REPLACEMENT"),   # threshold (boundary day)
            (15, "REJECT_OUTSIDE_WINDOW"), # threshold + 1 (outside window)
        ],
    )
    def test_defect_delivery_days_boundary(self, days, expected_action):
        res = decide({
            "message": "Device is defective and does not function",
            "order_value_inr": 2500,
            "days_since_delivery": days,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action

    @pytest.mark.parametrize(
        "value,expected_action",
        [
            (2999, "APPROVE_REPLACEMENT"),       # threshold - 1 (no evidence needed)
            (3000, "APPROVE_REPLACEMENT"),       # threshold (≤ 3000, no evidence needed)
            (3001, "REQUEST_DEFECT_EVIDENCE"),   # threshold + 1 (> 3000, evidence requested)
        ],
    )
    def test_defect_order_value_boundary(self, value, expected_action):
        res = decide({
            "message": "Gadget is defective and stopped working",
            "order_value_inr": value,
            "days_since_delivery": 5,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action


# ===================================================================
# 3. RETURNS THRESHOLD: 14 Days
# ===================================================================


class TestReturnsBoundaries:
    """Returns policy: 14 calendar days for unopened non-food items."""

    @pytest.mark.parametrize(
        "days,expected_action",
        [
            (13, "APPROVE_RETURN"),        # threshold - 1 (within window)
            (14, "APPROVE_RETURN"),        # threshold (boundary day)
            (15, "REJECT_OUTSIDE_WINDOW"), # threshold + 1 (outside window)
        ],
    )
    def test_returns_delivery_days_boundary(self, days, expected_action):
        res = decide({
            "message": "I changed my mind, returning unopened item",
            "order_value_inr": 1000,
            "days_since_delivery": days,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action


# ===================================================================
# 4. WRONG ITEM THRESHOLD: 7 Days
# ===================================================================


class TestWrongItemBoundaries:
    """Wrong item policy: 7 calendar days."""

    @pytest.mark.parametrize(
        "days,expected_action",
        [
            (6, "REPLACE_CORRECT_ITEM"),   # threshold - 1 (within window)
            (7, "REPLACE_CORRECT_ITEM"),   # threshold (boundary day)
            (8, "REJECT_OUTSIDE_WINDOW"),  # threshold + 1 (outside window)
        ],
    )
    def test_wrong_item_delivery_days_boundary(self, days, expected_action):
        res = decide({
            "message": "I ordered chocolate but received strawberry",
            "order_value_inr": 800,
            "days_since_delivery": days,
            "product_type": "food",
            "order_status": "delivered",
        })
        assert res["action"] == expected_action


# ===================================================================
# 5. SHIPPING AND DELIVERY THRESHOLDS: 5, 7, 8, 10, 11 Days
# ===================================================================


class TestShippingBoundaries:
    """Shipping policy:
    - ≤ 5 days: within expected delivery window -> WAIT_AND_TRACK
    - 6-7 days: wait and track -> WAIT_AND_TRACK
    - 8-10 days: open investigation -> OPEN_SHIPPING_INVESTIGATION
    - > 10 days (11+): offer replacement or refund -> OFFER_REPLACEMENT_OR_REFUND
    """

    @pytest.mark.parametrize(
        "days,expected_action",
        [
            (4, "WAIT_AND_TRACK"),                  # Day 4: early wait
            (5, "WAIT_AND_TRACK"),                  # Day 5: normal delivery expectation
            (6, "WAIT_AND_TRACK"),                  # Day 6: 6-7 window start
            (7, "WAIT_AND_TRACK"),                  # Day 7: 6-7 window end (threshold)
            (8, "OPEN_SHIPPING_INVESTIGATION"),     # Day 8: 8-10 investigation start (threshold + 1)
            (9, "OPEN_SHIPPING_INVESTIGATION"),     # Day 9: inside investigation window
            (10, "OPEN_SHIPPING_INVESTIGATION"),    # Day 10: investigation window end (threshold)
            (11, "OFFER_REPLACEMENT_OR_REFUND"),    # Day 11: >10 days cutoff (threshold + 1)
            (25, "OFFER_REPLACEMENT_OR_REFUND"),    # Day 25: far beyond cutoff
        ],
    )
    def test_shipping_dispatch_days_boundary(self, days, expected_action):
        res = decide({
            "message": "My parcel has still not arrived after dispatch",
            "order_value_inr": 1200,
            "days_since_dispatch": days,
            "order_status": "dispatched",
        })
        assert res["action"] == expected_action
