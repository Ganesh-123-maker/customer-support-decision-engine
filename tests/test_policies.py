"""Comprehensive policy tests covering every branch, boundary, and edge case.

Tests are organized by policy area and independently verify expected behavior
from the knowledge-base documents.
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
# DAMAGED GOODS POLICY
# ===================================================================


class TestDamagedGoods:
    """knowledge_base/damaged_goods.md"""

    def test_low_value_within_window(self):
        """≤ ₹2,000 + within 7 days → APPROVE_REFUND_OR_REPLACEMENT"""
        result = decide({
            "message": "My order arrived broken",
            "order_value_inr": 2000,
            "days_since_delivery": 7,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_low_value_boundary_exactly_2000(self):
        """Exactly ₹2,000 → no photos needed"""
        result = decide({
            "message": "Package was damaged",
            "order_value_inr": 2000,
            "days_since_delivery": 3,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_high_value_boundary_2001(self):
        """₹2,001 → photos required"""
        result = decide({
            "message": "Item was damaged in transit",
            "order_value_inr": 2001,
            "days_since_delivery": 3,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_PHOTOS"

    def test_high_value_within_window(self):
        """> ₹2,000 + within 7 days → REQUEST_PHOTOS"""
        result = decide({
            "message": "My expensive item arrived crushed",
            "order_value_inr": 5000,
            "days_since_delivery": 1,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_PHOTOS"

    def test_exactly_7_days(self):
        """Day 7 = still within window"""
        result = decide({
            "message": "Product was damaged",
            "order_value_inr": 1500,
            "days_since_delivery": 7,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_exactly_8_days(self):
        """Day 8 = outside window"""
        result = decide({
            "message": "Product was damaged",
            "order_value_inr": 1500,
            "days_since_delivery": 8,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_day_0(self):
        """Same day = within window"""
        result = decide({
            "message": "Just received, it's damaged",
            "order_value_inr": 800,
            "days_since_delivery": 0,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_missing_delivery_date(self):
        """No delivery date → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "My order was damaged",
            "order_value_inr": 3000,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_missing_order_value(self):
        """Within window but no order value → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "My package arrived damaged",
            "days_since_delivery": 3,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_far_outside_window(self):
        """30 days → reject"""
        result = decide({
            "message": "I noticed damage on my order",
            "order_value_inr": 500,
            "days_since_delivery": 30,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OUTSIDE_WINDOW"


# ===================================================================
# DEFECTIVE PRODUCT POLICY
# ===================================================================


class TestDefectiveProduct:
    """knowledge_base/defective_products.md"""

    def test_low_value_within_window(self):
        """≤ ₹3,000 + within 14 days → APPROVE_REPLACEMENT"""
        result = decide({
            "message": "The device is defective and won't turn on",
            "order_value_inr": 3000,
            "days_since_delivery": 10,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REPLACEMENT"

    def test_high_value_within_window(self):
        """> ₹3,000 + within 14 days → REQUEST_DEFECT_EVIDENCE"""
        result = decide({
            "message": "This product is defective, it stops working",
            "order_value_inr": 3001,
            "days_since_delivery": 5,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"

    def test_boundary_exactly_3000(self):
        """Exactly ₹3,000 → no evidence needed"""
        result = decide({
            "message": "Product is not working properly, it's defective",
            "order_value_inr": 3000,
            "days_since_delivery": 7,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REPLACEMENT"

    def test_boundary_exactly_3001(self):
        """₹3,001 → evidence required"""
        result = decide({
            "message": "Item doesn't work, defective product",
            "order_value_inr": 3001,
            "days_since_delivery": 7,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"

    def test_exactly_14_days(self):
        """Day 14 = within window"""
        result = decide({
            "message": "The product is defective",
            "order_value_inr": 2000,
            "days_since_delivery": 14,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REPLACEMENT"

    def test_exactly_15_days(self):
        """Day 15 = outside window"""
        result = decide({
            "message": "The product is defective",
            "order_value_inr": 2000,
            "days_since_delivery": 15,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_missing_delivery_date(self):
        """No delivery date → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "Product is defective and malfunctioning",
            "order_value_inr": 4000,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_high_value_evidence_request(self):
        """₹3,999 defective → request evidence"""
        result = decide({
            "message": "The device is defective and stops working after a few minutes.",
            "order_value_inr": 3999,
            "days_since_delivery": 9,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"


# ===================================================================
# RETURNS POLICY
# ===================================================================


class TestReturns:
    """knowledge_base/returns.md"""

    def test_unopened_non_food_within_window(self):
        """Unopened non-food within 14 days → APPROVE_RETURN"""
        result = decide({
            "message": "I changed my mind, want to return this",
            "order_value_inr": 1200,
            "days_since_delivery": 10,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_RETURN"

    def test_opened_non_food(self):
        """Opened non-food → REJECT_OPENED_ITEM"""
        result = decide({
            "message": "I want to return this product",
            "order_value_inr": 1200,
            "days_since_delivery": 5,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OPENED_ITEM"

    def test_food_product_return(self):
        """Food → REJECT_FOOD_RETURN"""
        result = decide({
            "message": "I want to return this food item",
            "order_value_inr": 500,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_FOOD_RETURN"

    def test_unopened_non_food_exactly_14_days(self):
        """Day 14 = within window"""
        result = decide({
            "message": "Want to return, changed my mind",
            "order_value_inr": 800,
            "days_since_delivery": 14,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_RETURN"

    def test_unopened_non_food_day_15(self):
        """Day 15 = outside window"""
        result = decide({
            "message": "I want to return this item",
            "order_value_inr": 800,
            "days_since_delivery": 15,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_missing_product_type(self):
        """Unknown product type → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "I want to return this.",
            "order_value_inr": 900,
            "days_since_delivery": 5,
            "product_type": "unknown",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_missing_opened_status(self):
        """Unknown opened status for non-food → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "I want to return this item",
            "order_value_inr": 900,
            "days_since_delivery": 5,
            "product_type": "non_food",
            "opened_status": "unknown",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_missing_delivery_date_unopened_nonfood(self):
        """Unopened non-food, no delivery date → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "I changed my mind, want to return",
            "order_value_inr": 900,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_food_even_if_unopened(self):
        """Unopened food → still rejected"""
        result = decide({
            "message": "I changed my mind about this food order",
            "order_value_inr": 300,
            "days_since_delivery": 1,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_FOOD_RETURN"


# ===================================================================
# CANCELLATION POLICY
# ===================================================================


class TestCancellation:
    """knowledge_base/cancellations.md"""

    def test_cancel_before_dispatch(self):
        """Pending order → CANCEL_AND_REFUND"""
        result = decide({
            "message": "I want to cancel my order",
            "order_value_inr": 1500,
            "order_status": "pending",
            "product_type": "non_food",
        })
        assert result["action"] == "CANCEL_AND_REFUND"

    def test_cancel_after_dispatch(self):
        """Dispatched order → CANNOT_CANCEL_AFTER_DISPATCH"""
        result = decide({
            "message": "Please cancel my order",
            "order_value_inr": 1500,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"

    def test_cancel_after_delivery(self):
        """Delivered order → CANNOT_CANCEL_AFTER_DISPATCH"""
        result = decide({
            "message": "Cancel this order please",
            "order_value_inr": 1500,
            "order_status": "delivered",
            "product_type": "non_food",
        })
        assert result["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"

    def test_cancel_unknown_status(self):
        """Unknown order status → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "I want to cancel my order",
            "order_value_inr": 1500,
            "order_status": "unknown",
            "product_type": "non_food",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"


# ===================================================================
# WRONG ITEM POLICY
# ===================================================================


class TestWrongItem:
    """knowledge_base/wrong_item.md"""

    def test_wrong_item_within_window(self):
        """Within 7 days → REPLACE_CORRECT_ITEM"""
        result = decide({
            "message": "I ordered strawberry but received chocolate",
            "order_value_inr": 650,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REPLACE_CORRECT_ITEM"

    def test_wrong_item_exactly_7_days(self):
        """Day 7 = within window"""
        result = decide({
            "message": "They sent wrong item instead of what I ordered",
            "order_value_inr": 1000,
            "days_since_delivery": 7,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REPLACE_CORRECT_ITEM"

    def test_wrong_item_day_8(self):
        """Day 8 = outside window"""
        result = decide({
            "message": "Got wrong item, ordered blue but got red",
            "order_value_inr": 1000,
            "days_since_delivery": 8,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_OUTSIDE_WINDOW"

    def test_wrong_item_missing_delivery(self):
        """No delivery date → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "I received the wrong item",
            "order_value_inr": 1000,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_wrong_flavour(self):
        """Wrong flavour within 7 days → replace"""
        result = decide({
            "message": "I ordered vanilla but received chocolate 2 days ago",
            "order_value_inr": 400,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REPLACE_CORRECT_ITEM"


# ===================================================================
# SHIPPING AND DELIVERY POLICY
# ===================================================================


class TestShipping:
    """knowledge_base/shipping.md"""

    def test_within_5_days(self):
        """≤ 5 days → WAIT_AND_TRACK"""
        result = decide({
            "message": "My parcel hasn't arrived yet, dispatched 5 days ago",
            "order_value_inr": 850,
            "days_since_dispatch": 5,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "WAIT_AND_TRACK"

    def test_6_days(self):
        """6 days → WAIT_AND_TRACK"""
        result = decide({
            "message": "Still waiting for my order, it was shipped 6 days ago",
            "order_value_inr": 1200,
            "days_since_dispatch": 6,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "WAIT_AND_TRACK"

    def test_7_days(self):
        """7 days → WAIT_AND_TRACK"""
        result = decide({
            "message": "Order not arrived, dispatched 7 days ago",
            "order_value_inr": 1200,
            "days_since_dispatch": 7,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "WAIT_AND_TRACK"

    def test_8_days(self):
        """8 days → OPEN_SHIPPING_INVESTIGATION"""
        result = decide({
            "message": "My package has not arrived, dispatched 8 days ago",
            "order_value_inr": 850,
            "days_since_dispatch": 8,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_9_days(self):
        """9 days → OPEN_SHIPPING_INVESTIGATION"""
        result = decide({
            "message": "My parcel has still not arrived and it was dispatched 9 days ago",
            "order_value_inr": 850,
            "days_since_dispatch": 9,
            "order_status": "dispatched",
            "product_type": "mixed",
            "opened_status": "unknown",
        })
        assert result["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_10_days(self):
        """10 days → OPEN_SHIPPING_INVESTIGATION"""
        result = decide({
            "message": "Order dispatched 10 days ago, still not here",
            "order_value_inr": 850,
            "days_since_dispatch": 10,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_11_days(self):
        """11 days → OFFER_REPLACEMENT_OR_REFUND"""
        result = decide({
            "message": "It's been 11 days since dispatch and no delivery",
            "order_value_inr": 850,
            "days_since_dispatch": 11,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "OFFER_REPLACEMENT_OR_REFUND"

    def test_20_days(self):
        """20 days → OFFER_REPLACEMENT_OR_REFUND"""
        result = decide({
            "message": "Order dispatched 20 days ago, still not arrived",
            "order_value_inr": 2000,
            "days_since_dispatch": 20,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "OFFER_REPLACEMENT_OR_REFUND"

    def test_missing_dispatch_date(self):
        """No dispatch date → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "My order hasn't arrived",
            "order_value_inr": 850,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"


# ===================================================================
# EDGE CASES AND GENERAL TESTS
# ===================================================================


class TestEdgeCases:
    """Edge cases, invalid inputs, and general behavior."""

    def test_empty_message_rejected(self):
        """Empty message → 422"""
        resp = client.post("/decide", json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message(self):
        """No message field → 422"""
        resp = client.post("/decide", json={})
        assert resp.status_code == 422

    def test_completely_unknown_issue(self):
        """Unrecognizable message → NEEDS_MORE_INFORMATION"""
        result = decide({
            "message": "Hello, I need help with something",
            "order_value_inr": 1000,
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_negative_days_rejected(self):
        """Negative days_since_delivery → 422"""
        resp = client.post("/decide", json={
            "message": "damaged item",
            "days_since_delivery": -1,
        })
        assert resp.status_code == 422

    def test_negative_order_value_rejected(self):
        """Negative order value → 422"""
        resp = client.post("/decide", json={
            "message": "damaged item",
            "order_value_inr": -100,
        })
        assert resp.status_code == 422

    def test_response_schema(self):
        """Response must include action, explanation, issue_type."""
        result = decide({
            "message": "My order was damaged",
            "order_value_inr": 1000,
            "days_since_delivery": 3,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert "action" in result
        assert "explanation" in result
        assert "issue_type" in result
        assert len(result["explanation"]) > 0

    def test_health_endpoint(self):
        """GET /health returns ok"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ===================================================================
# NATURAL LANGUAGE EXTRACTION TESTS
# ===================================================================


class TestNaturalLanguage:
    """Tests for realistic natural-language messages."""

    def test_nlp_damage_with_currency(self):
        """Extract damage + amount from natural text"""
        result = decide({
            "message": "My ₹3,500 order arrived damaged yesterday.",
            "order_value_inr": 3500,
            "days_since_delivery": 1,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_PHOTOS"

    def test_nlp_wrong_flavour(self):
        """Detect wrong flavour from natural text"""
        result = decide({
            "message": "I ordered strawberry but received chocolate 2 days ago.",
            "order_value_inr": 650,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "REPLACE_CORRECT_ITEM"

    def test_nlp_shipping_delay(self):
        """Detect shipping delay from natural text"""
        result = decide({
            "message": "My parcel has still not arrived and it was dispatched 9 days ago.",
            "order_value_inr": 850,
            "days_since_dispatch": 9,
            "product_type": "mixed",
            "opened_status": "unknown",
            "order_status": "dispatched",
        })
        assert result["action"] == "OPEN_SHIPPING_INVESTIGATION"

    def test_nlp_return_change_of_mind(self):
        """Detect return from change of mind message"""
        result = decide({
            "message": "I changed my mind about this unopened non-food product. It arrived 10 days ago.",
            "order_value_inr": 1200,
            "days_since_delivery": 10,
            "product_type": "non_food",
            "opened_status": "unopened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_RETURN"

    def test_nlp_minimal_info(self):
        """Minimal message with missing info"""
        result = decide({
            "message": "I want to return this.",
            "order_value_inr": 900,
            "product_type": "unknown",
            "opened_status": "unknown",
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"

    def test_nlp_defective_device(self):
        """Detect defective device"""
        result = decide({
            "message": "The device is defective and stops working after a few minutes.",
            "order_value_inr": 3999,
            "days_since_delivery": 9,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"

    def test_nlp_cancel_order(self):
        """Detect cancellation from natural text"""
        result = decide({
            "message": "I don't want this order anymore, please cancel it",
            "order_value_inr": 2500,
            "order_status": "pending",
            "product_type": "non_food",
        })
        assert result["action"] == "CANCEL_AND_REFUND"


# ===================================================================
# UNSEEN COMBINATIONS
# ===================================================================


class TestUnseenCombinations:
    """Combinations not in sample_test_cases or tickets.csv."""

    def test_damaged_food_low_value(self):
        """Damaged food under ₹2000 within window"""
        result = decide({
            "message": "My food order arrived damaged",
            "order_value_inr": 500,
            "days_since_delivery": 2,
            "product_type": "food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_defective_low_value_day_14(self):
        """Defective exactly day 14, low value"""
        result = decide({
            "message": "Product is defective, not functioning",
            "order_value_inr": 1500,
            "days_since_delivery": 14,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REPLACEMENT"

    def test_wrong_item_day_0(self):
        """Wrong item same day"""
        result = decide({
            "message": "Just received the wrong item, ordered red got blue",
            "order_value_inr": 2000,
            "days_since_delivery": 0,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REPLACE_CORRECT_ITEM"

    def test_shipping_day_1(self):
        """Shipping complaint day 1 = wait"""
        result = decide({
            "message": "Order not arrived yet, was dispatched yesterday",
            "order_value_inr": 500,
            "days_since_dispatch": 1,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "WAIT_AND_TRACK"

    def test_return_opened_food(self):
        """Opened food return → reject food"""
        result = decide({
            "message": "Want to return this food product, I opened it but don't want it",
            "order_value_inr": 300,
            "days_since_delivery": 1,
            "product_type": "food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REJECT_FOOD_RETURN"

    def test_cancel_dispatched_order(self):
        """Cancel dispatched → cannot cancel"""
        result = decide({
            "message": "Please cancel my order, I don't need it anymore",
            "order_value_inr": 5000,
            "order_status": "dispatched",
            "product_type": "non_food",
        })
        assert result["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"

    def test_damaged_exactly_zero_rupees(self):
        """Free order (₹0) damaged → still approve without photos"""
        result = decide({
            "message": "My free sample arrived damaged",
            "order_value_inr": 0,
            "days_since_delivery": 1,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_high_value_defect_day_1(self):
        """Expensive defective item day 1"""
        result = decide({
            "message": "This ₹10,000 gadget is defective, doesn't work at all",
            "order_value_inr": 10000,
            "days_since_delivery": 1,
            "product_type": "non_food",
            "opened_status": "opened",
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"
