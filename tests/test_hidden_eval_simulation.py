"""Hidden Evaluation Simulation Test Suite.

Simulates hidden evaluator test cases with unseen customer messages, diverse products,
prices, dates, missing facts, and edge-case combinations across all 6 business policies.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def decide(payload: dict) -> dict:
    resp = client.post("/decide", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ============================================================================
# 1. DAMAGED GOODS UNSEEN SCENARIOS
# ============================================================================
class TestHiddenDamagedGoods:
    def test_cheap_ceramic_mug_damaged_today(self):
        res = decide({
            "message": "The ceramic mug arrived cracked today.",
            "order_value_inr": 250,
            "days_since_delivery": 0,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REFUND_OR_REPLACEMENT"
        assert res["issue_type"] == "damaged"

    def test_expensive_tv_damaged_day_6(self):
        res = decide({
            "message": "Our ₹45,000 smart television screen was shattered on delivery.",
            "order_value_inr": 45000,
            "days_since_delivery": 6,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "REQUEST_PHOTOS"
        assert res["issue_type"] == "damaged"

    def test_damaged_goods_day_9_late_report(self):
        res = decide({
            "message": "The wooden bookshelf arrived damaged 9 days ago.",
            "order_value_inr": 3500,
            "days_since_delivery": 9,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"
        assert res["issue_type"] == "damaged"


# ============================================================================
# 2. DEFECTIVE PRODUCT UNSEEN SCENARIOS
# ============================================================================
class TestHiddenDefectiveProducts:
    def test_bluetooth_earbuds_low_value_defect(self):
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

    def test_laptop_high_value_defect(self):
        res = decide({
            "message": "The laptop keyboard is defective and some keys do not function.",
            "order_value_inr": 62000,
            "days_since_delivery": 11,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "REQUEST_DEFECT_EVIDENCE"
        assert res["issue_type"] == "defective"

    def test_smartwatch_defect_reported_day_16(self):
        res = decide({
            "message": "The smartwatch display stopped functioning 16 days after delivery.",
            "order_value_inr": 4000,
            "days_since_delivery": 16,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"


# ============================================================================
# 3. WRONG ITEM UNSEEN SCENARIOS
# ============================================================================
class TestHiddenWrongItem:
    def test_wrong_apparel_size(self):
        res = decide({
            "message": "I ordered size Large but received size Small yesterday.",
            "order_value_inr": 1499,
            "days_since_delivery": 1,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "REPLACE_CORRECT_ITEM"
        assert res["issue_type"] == "wrong_item"

    def test_wrong_beverage_flavour_late(self):
        res = decide({
            "message": "Received almond milk instead of oat milk 12 days ago.",
            "order_value_inr": 600,
            "days_since_delivery": 12,
            "product_type": "food",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"


# ============================================================================
# 4. RETURNS UNSEEN SCENARIOS
# ============================================================================
class TestHiddenReturns:
    def test_gourmet_olive_oil_food_return(self):
        """Food item return is rejected even if unopened and within 2 days."""
        res = decide({
            "message": "I want to return this unopened bottle of olive oil.",
            "order_value_inr": 1200,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_FOOD_RETURN"
        assert res["issue_type"] == "return"

    def test_unopened_running_shoes_day_13(self):
        res = decide({
            "message": "Changed my mind about these running shoes, box is still factory sealed.",
            "order_value_inr": 3400,
            "days_since_delivery": 13,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_RETURN"
        assert res["issue_type"] == "return"

    def test_opened_jacket_return_rejected(self):
        res = decide({
            "message": "I opened and tried on the jacket but decided I don't want it.",
            "order_value_inr": 2900,
            "days_since_delivery": 4,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OPENED_ITEM"


# ============================================================================
# 5. SHIPPING DELAY UNSEEN SCENARIOS
# ============================================================================
class TestHiddenShipping:
    def test_dispatched_3_days_ago_wait(self):
        res = decide({
            "message": "Where is my parcel? Dispatched 3 days ago.",
            "days_since_dispatch": 3,
            "order_status": "dispatched",
        })
        assert res["action"] == "WAIT_AND_TRACK"
        assert res["issue_type"] == "shipping_delay"

    def test_dispatched_8_days_ago_investigate(self):
        res = decide({
            "message": "Tracking has not updated and it has been 8 days since dispatch.",
            "days_since_dispatch": 8,
            "order_status": "dispatched",
        })
        assert res["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_dispatched_15_days_ago_refund_replace(self):
        res = decide({
            "message": "It has been 15 days since dispatch and the order has not arrived.",
            "days_since_dispatch": 15,
            "order_status": "dispatched",
        })
        assert res["action"] == "OFFER_REPLACEMENT_OR_REFUND"


# ============================================================================
# 6. CANCELLATION UNSEEN SCENARIOS
# ============================================================================
class TestHiddenCancellations:
    def test_cancel_pending_order(self):
        res = decide({
            "message": "I placed the order by mistake, please cancel it immediately.",
            "order_status": "pending",
        })
        assert res["action"] == "CANCEL_AND_REFUND"

    def test_cancel_processing_order(self):
        res = decide({
            "message": "Please cancel my purchase before it leaves your warehouse.",
            "order_status": "processing",
        })
        assert res["action"] == "CANCEL_AND_REFUND"

    def test_cancel_already_shipped_order(self):
        res = decide({
            "message": "Please cancel my order now.",
            "order_status": "dispatched",
        })
        assert res["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"


# ============================================================================
# 7. NATURAL LANGUAGE FUZZING VARIATIONS
# ============================================================================
class TestNLPFuzzing:
    @pytest.mark.parametrize(
        "phrase",
        [
            "The product was damaged when delivered.",
            "Received damaged goods yesterday.",
            "My order was broken on arrival.",
            "The parcel got damaged in courier transit.",
            "Outer box was crushed and item shattered.",
        ],
    )
    def test_damage_variations(self, phrase):
        res = decide({
            "message": phrase,
            "order_value_inr": 1500,
            "days_since_delivery": 1,
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REFUND_OR_REPLACEMENT"
        assert res["issue_type"] == "damaged"

    @pytest.mark.parametrize(
        "phrase",
        [
            "The electronic gadget completely stopped functioning.",
            "The appliance is faulty and won't turn on.",
            "Device malfunctioned after 2 days.",
            "The unit is defective and dead on arrival.",
        ],
    )
    def test_defect_variations(self, phrase):
        res = decide({
            "message": phrase,
            "order_value_inr": 2200,
            "days_since_delivery": 3,
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REPLACEMENT"
        assert res["issue_type"] == "defective"
