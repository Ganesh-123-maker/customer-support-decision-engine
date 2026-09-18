"""Complete Policy Test Matrix.

Implements a systematic test matrix covering every business policy rule:
1. Damaged Goods
2. Defective Products
3. Returns (Change of Mind)
4. Cancellations
5. Wrong Item
6. Shipping & Delivery

For each rule, tests:
- Normal eligible case
- Normal ineligible case
- Exact boundary case
- Missing-information case
- Contradictory-information case
- Natural-language variation
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
# 1. DAMAGED GOODS POLICY MATRIX
# ============================================================================
class TestDamagedGoodsMatrix:
    def test_normal_eligible_low_value(self):
        """≤ 2000 INR within 7 days -> approved without photos."""
        res = decide({
            "message": "My item was broken when it arrived.",
            "order_value_inr": 1200,
            "days_since_delivery": 3,
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REFUND_OR_REPLACEMENT"
        assert res["issue_type"] == "damaged"

    def test_normal_eligible_high_value(self):
        """> 2000 INR within 7 days -> photos required."""
        res = decide({
            "message": "My package arrived damaged.",
            "order_value_inr": 4500,
            "days_since_delivery": 4,
            "order_status": "delivered",
        })
        assert res["action"] == "REQUEST_PHOTOS"
        assert res["issue_type"] == "damaged"

    def test_normal_ineligible_outside_window(self):
        """> 7 days -> rejected outside window."""
        res = decide({
            "message": "The item arrived damaged.",
            "order_value_inr": 1000,
            "days_since_delivery": 12,
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_boundary_day_7_and_day_8(self):
        """Day 7 is eligible; day 8 is ineligible."""
        res7 = decide({
            "message": "Item arrived broken.",
            "order_value_inr": 1500,
            "days_since_delivery": 7,
            "order_status": "delivered",
        })
        assert res7["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

        res8 = decide({
            "message": "Item arrived broken.",
            "order_value_inr": 1500,
            "days_since_delivery": 8,
            "order_status": "delivered",
        })
        assert res8["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_boundary_value_2000_and_2001(self):
        """₹2,000 approves without photos; ₹2,001 requests photos."""
        res2000 = decide({
            "message": "Broken item.",
            "order_value_inr": 2000,
            "days_since_delivery": 2,
            "order_status": "delivered",
        })
        assert res2000["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

        res2001 = decide({
            "message": "Broken item.",
            "order_value_inr": 2001,
            "days_since_delivery": 2,
            "order_status": "delivered",
        })
        assert res2001["action"] == "REQUEST_PHOTOS"

    def test_missing_info_no_delivery_date(self):
        res = decide({
            "message": "My order arrived crushed.",
            "order_value_inr": 1500,
            "order_status": "delivered",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"

    def test_missing_info_no_order_value(self):
        res = decide({
            "message": "My order arrived crushed yesterday.",
            "days_since_delivery": 1,
            "order_status": "delivered",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"

    def test_contradictory_damaged_and_defective(self):
        """Per defective rule 4: cosmetic damage handled under Damaged Goods."""
        res = decide({
            "message": "The product is cracked and damaged, but also defective and won't turn on.",
            "order_value_inr": 1500,
            "days_since_delivery": 2,
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REFUND_OR_REPLACEMENT"
        assert res["issue_type"] == "damaged"

    def test_natural_language_variations(self):
        variations = [
            "My ₹3500 order is damaged.",
            "The order cost Rs. 3,500 and arrived broken.",
            "I paid 3500 rupees for this damaged item.",
            "Package was damaged 2 days ago.",
        ]
        for var in variations:
            res = decide({
                "message": var,
                "days_since_delivery": 2,
                "order_value_inr": 3500,
                "order_status": "delivered",
            })
            assert res["action"] == "REQUEST_PHOTOS"


# ============================================================================
# 2. DEFECTIVE PRODUCTS POLICY MATRIX
# ============================================================================
class TestDefectiveProductMatrix:
    def test_normal_eligible_low_value(self):
        """≤ 3000 INR within 14 days -> approve replacement."""
        res = decide({
            "message": "The device is defective and does not function correctly.",
            "order_value_inr": 2500,
            "days_since_delivery": 5,
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_REPLACEMENT"
        assert res["issue_type"] == "defective"

    def test_normal_eligible_high_value(self):
        """> 3000 INR within 14 days -> request defect evidence."""
        res = decide({
            "message": "The product is defective and won't start.",
            "order_value_inr": 4999,
            "days_since_delivery": 7,
            "order_status": "delivered",
        })
        assert res["action"] == "REQUEST_DEFECT_EVIDENCE"
        assert res["issue_type"] == "defective"

    def test_normal_ineligible_outside_window(self):
        """> 14 days -> reject outside window."""
        res = decide({
            "message": "This defective unit has stopped working.",
            "order_value_inr": 2000,
            "days_since_delivery": 20,
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_boundary_day_14_and_day_15(self):
        """Day 14 eligible; day 15 ineligible."""
        res14 = decide({
            "message": "Item is defective.",
            "order_value_inr": 2000,
            "days_since_delivery": 14,
            "order_status": "delivered",
        })
        assert res14["action"] == "APPROVE_REPLACEMENT"

        res15 = decide({
            "message": "Item is defective.",
            "order_value_inr": 2000,
            "days_since_delivery": 15,
            "order_status": "delivered",
        })
        assert res15["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_boundary_value_3000_and_3001(self):
        """₹3,000 approves replacement; ₹3,001 requests evidence."""
        res3000 = decide({
            "message": "Defective device.",
            "order_value_inr": 3000,
            "days_since_delivery": 5,
            "order_status": "delivered",
        })
        assert res3000["action"] == "APPROVE_REPLACEMENT"

        res3001 = decide({
            "message": "Defective device.",
            "order_value_inr": 3001,
            "days_since_delivery": 5,
            "order_status": "delivered",
        })
        assert res3001["action"] == "REQUEST_DEFECT_EVIDENCE"

    def test_missing_delivery_date(self):
        res = decide({
            "message": "Device is defective and stops working.",
            "order_value_inr": 2000,
            "order_status": "delivered",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"


# ============================================================================
# 3. RETURNS POLICY MATRIX
# ============================================================================
class TestReturnsMatrix:
    def test_normal_eligible_unopened_nonfood(self):
        """Unopened non-food within 14 days -> APPROVE_RETURN."""
        res = decide({
            "message": "I changed my mind, returning unopened non-food product.",
            "days_since_delivery": 10,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res["action"] == "APPROVE_RETURN"

    def test_normal_ineligible_opened_nonfood(self):
        """Opened non-food -> REJECT_OPENED_ITEM."""
        res = decide({
            "message": "I want to return this, but I opened it.",
            "days_since_delivery": 5,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OPENED_ITEM"

    def test_normal_ineligible_food(self):
        """Food -> REJECT_FOOD_RETURN."""
        res = decide({
            "message": "I changed my mind about this food product.",
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_FOOD_RETURN"

    def test_boundary_day_14_and_day_15(self):
        res14 = decide({
            "message": "Want to return unopened non-food item.",
            "days_since_delivery": 14,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res14["action"] == "APPROVE_RETURN"

        res15 = decide({
            "message": "Want to return unopened non-food item.",
            "days_since_delivery": 15,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res15["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_missing_info_all_variants(self):
        # Missing product type
        res1 = decide({
            "message": "I want to return this.",
            "days_since_delivery": 5,
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert res1["action"] == "NEEDS_MORE_INFORMATION"

        # Missing opened status for non-food
        res2 = decide({
            "message": "Return non-food product please.",
            "days_since_delivery": 5,
            "product_type": "non_food",
            "order_status": "delivered",
        })
        assert res2["action"] == "NEEDS_MORE_INFORMATION"


# ============================================================================
# 4. CANCELLATIONS POLICY MATRIX
# ============================================================================
class TestCancellationsMatrix:
    def test_eligible_before_dispatch_pending(self):
        res = decide({
            "message": "Please cancel my order.",
            "order_status": "pending",
        })
        assert res["action"] == "CANCEL_AND_REFUND"

    def test_eligible_before_dispatch_processing(self):
        res = decide({
            "message": "I want to cancel this order before shipping.",
            "order_status": "processing",
        })
        assert res["action"] == "CANCEL_AND_REFUND"

    def test_ineligible_after_dispatch(self):
        res = decide({
            "message": "Cancel my order please.",
            "order_status": "dispatched",
        })
        assert res["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"

    def test_ineligible_after_delivery(self):
        res = decide({
            "message": "I want to cancel this order.",
            "order_status": "delivered",
        })
        assert res["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"

    def test_missing_order_status(self):
        res = decide({
            "message": "Can I cancel my order?",
            "order_status": "unknown",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"


# ============================================================================
# 5. WRONG ITEM POLICY MATRIX
# ============================================================================
class TestWrongItemMatrix:
    def test_normal_eligible(self):
        res = decide({
            "message": "You sent me the wrong item 3 days ago.",
            "days_since_delivery": 3,
            "order_status": "delivered",
        })
        assert res["action"] == "REPLACE_CORRECT_ITEM"

    def test_normal_ineligible_outside_window(self):
        res = decide({
            "message": "I got the wrong item 10 days ago.",
            "days_since_delivery": 10,
            "order_status": "delivered",
        })
        assert res["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_boundary_day_7_and_day_8(self):
        res7 = decide({
            "message": "Wrong flavour delivered 7 days ago.",
            "days_since_delivery": 7,
            "order_status": "delivered",
        })
        assert res7["action"] == "REPLACE_CORRECT_ITEM"

        res8 = decide({
            "message": "Wrong flavour delivered 8 days ago.",
            "days_since_delivery": 8,
            "order_status": "delivered",
        })
        assert res8["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_missing_delivery_date(self):
        res = decide({
            "message": "I ordered vanilla but received chocolate.",
            "order_status": "delivered",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"


# ============================================================================
# 6. SHIPPING & DELIVERY POLICY MATRIX
# ============================================================================
class TestShippingMatrix:
    def test_normal_wait_and_track_day_5(self):
        res = decide({
            "message": "My package has not arrived yet.",
            "days_since_dispatch": 5,
            "order_status": "dispatched",
        })
        assert res["action"] == "WAIT_AND_TRACK"

    def test_normal_wait_and_track_day_7(self):
        res = decide({
            "message": "Still waiting for my order.",
            "days_since_dispatch": 7,
            "order_status": "dispatched",
        })
        assert res["action"] == "WAIT_AND_TRACK"

    def test_normal_investigation_day_9(self):
        res = decide({
            "message": "My package still has not arrived after dispatch.",
            "days_since_dispatch": 9,
            "order_status": "dispatched",
        })
        assert res["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_normal_refund_replace_day_12(self):
        res = decide({
            "message": "Order has not arrived and it's been delayed.",
            "days_since_dispatch": 12,
            "order_status": "dispatched",
        })
        assert res["action"] == "OFFER_REPLACEMENT_OR_REFUND"

    def test_boundary_day_7_8_10_11(self):
        res7 = decide({"message": "Not arrived", "days_since_dispatch": 7, "order_status": "dispatched"})
        assert res7["action"] == "WAIT_AND_TRACK"

        res8 = decide({"message": "Not arrived", "days_since_dispatch": 8, "order_status": "dispatched"})
        assert res8["action"] == "OPEN_SHIPPING_INVESTIGATION"

        res10 = decide({"message": "Not arrived", "days_since_dispatch": 10, "order_status": "dispatched"})
        assert res10["action"] == "OPEN_SHIPPING_INVESTIGATION"

        res11 = decide({"message": "Not arrived", "days_since_dispatch": 11, "order_status": "dispatched"})
        assert res11["action"] == "OFFER_REPLACEMENT_OR_REFUND"

    def test_missing_dispatch_date(self):
        res = decide({
            "message": "My package is missing in transit.",
            "order_status": "dispatched",
        })
        assert res["action"] == "NEEDS_MORE_INFORMATION"
