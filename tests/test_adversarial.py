"""Adversarial and robust edge case testing.

Tests:
- Contradictory inputs (damaged AND defective, return of damaged item, cancel of dispatched item)
- Missing information checks across all policy branches
- Extreme values (zero, very large numbers)
- Unrecognized or gibberish messages
- Currency format variations (₹3500, ₹3,500, Rs 3500, Rs. 3,500, 3500 rupees, INR 3500)
- Validation errors for invalid data types or negative values
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def decide(payload: dict) -> dict:
    resp = client.post("/decide", json=payload)
    assert resp.status_code == 200
    return resp.json()


class TestAdversarialContradictions:
    """Testing how contradictory customer messages are resolved via business precedence."""

    def test_damaged_and_defective_precedence(self):
        """When customer claims both cosmetic damage and defect, Damaged Goods Policy takes precedence.

        (Per defective_products.md rule 4: 'Cosmetic damage should be evaluated under Damaged Goods Policy')
        """
        result = decide({
            "message": "The screen is cracked and broken, and it is defective and not working.",
            "order_value_inr": 1500,
            "days_since_delivery": 3,
            "order_status": "delivered",
            "product_type": "non_food",
            "opened_status": "opened",
        })
        # Damage policy applies: ≤ 2000 within 7 days -> APPROVE_REFUND_OR_REPLACEMENT
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"
        assert result["issue_type"] == "damaged"

    def test_return_of_damaged_product_precedence(self):
        """When customer says 'I want to return this, it arrived broken'.

        (Per returns.md rule 4: 'Damaged or defective products are handled under Damaged Goods Policy')
        """
        result = decide({
            "message": "I want to return this item because it arrived crushed and damaged.",
            "order_value_inr": 4500,
            "days_since_delivery": 2,
            "order_status": "delivered",
            "product_type": "non_food",
            "opened_status": "opened",
        })
        # Handled under Damaged Goods: > 2000 within 7 days -> REQUEST_PHOTOS
        assert result["action"] == "REQUEST_PHOTOS"
        assert result["issue_type"] == "damaged"

    def test_cancel_attempt_on_dispatched_order(self):
        """Customer attempts to cancel an order that is already dispatched."""
        result = decide({
            "message": "Please cancel my order right now",
            "order_status": "dispatched",
        })
        assert result["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"
        assert result["issue_type"] == "cancellation"

    def test_cancel_attempt_on_delivered_order(self):
        """Customer attempts to cancel an order that was delivered."""
        result = decide({
            "message": "I want to cancel this order",
            "order_status": "delivered",
        })
        assert result["action"] == "CANNOT_CANCEL_AFTER_DISPATCH"
        assert result["issue_type"] == "cancellation"

    def test_cancel_on_processing_order(self):
        """Customer cancels before dispatch."""
        result = decide({
            "message": "I want to cancel my order please",
            "order_status": "processing",
        })
        assert result["action"] == "CANCEL_AND_REFUND"
        assert result["issue_type"] == "cancellation"


class TestMissingInformationHandling:
    """Verify that every policy explicitly returns NEEDS_MORE_INFORMATION when a required fact is absent."""

    def test_missing_delivery_date_for_damage(self):
        result = decide({
            "message": "My order arrived broken and crushed",
            "order_value_inr": 1500,
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "delivery date" in result["explanation"].lower()

    def test_missing_order_value_for_damage_within_window(self):
        result = decide({
            "message": "My order arrived broken 2 days ago",
            "days_since_delivery": 2,
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "order value" in result["explanation"].lower()

    def test_missing_delivery_date_for_defect(self):
        result = decide({
            "message": "The product is defective and stopped working",
            "order_value_inr": 2500,
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "delivery date" in result["explanation"].lower()

    def test_missing_product_type_for_return(self):
        result = decide({
            "message": "I changed my mind, want to return this",
            "days_since_delivery": 3,
            "order_status": "delivered",
            "product_type": "unknown",
            "opened_status": "unopened",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "product type" in result["explanation"].lower()

    def test_missing_opened_status_for_nonfood_return(self):
        result = decide({
            "message": "I want to return this non-food item",
            "days_since_delivery": 3,
            "order_status": "delivered",
            "product_type": "non_food",
            "opened_status": "unknown",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "opened" in result["explanation"].lower()

    def test_missing_delivery_date_for_unopened_nonfood_return(self):
        result = decide({
            "message": "I want to return this unopened non-food product",
            "order_status": "delivered",
            "product_type": "non_food",
            "opened_status": "unopened",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "delivery date" in result["explanation"].lower()

    def test_missing_dispatch_date_for_shipping_delay(self):
        result = decide({
            "message": "My package has still not arrived, where is it?",
            "order_status": "dispatched",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "dispatch date" in result["explanation"].lower()

    def test_missing_order_status_for_cancellation(self):
        result = decide({
            "message": "Can I cancel my order?",
            "order_status": "unknown",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert "status" in result["explanation"].lower()


class TestExtremeValuesAndAdversarialInputs:
    """Extreme values, zero, very large numbers, and unusual characters."""

    def test_zero_order_value_damage(self):
        """Free promotional order (₹0) damaged within window -> approved without photos."""
        result = decide({
            "message": "My zero rupee promotional package arrived crushed yesterday",
            "order_value_inr": 0,
            "days_since_delivery": 1,
            "order_status": "delivered",
        })
        assert result["action"] == "APPROVE_REFUND_OR_REPLACEMENT"

    def test_very_large_order_value_defect(self):
        """₹500,000 defective industrial equipment -> evidence requested."""
        result = decide({
            "message": "Our ₹500,000 unit is defective and does not function",
            "order_value_inr": 500000,
            "days_since_delivery": 3,
            "order_status": "delivered",
        })
        assert result["action"] == "REQUEST_DEFECT_EVIDENCE"

    def test_gibberish_message_fails_safely(self):
        """Completely unrelated text without recognized signals -> NEEDS_MORE_INFORMATION."""
        result = decide({
            "message": "The weather in Bangalore is very pleasant today 12345.",
            "order_value_inr": 1000,
            "days_since_delivery": 2,
            "order_status": "delivered",
        })
        assert result["action"] == "NEEDS_MORE_INFORMATION"
        assert result["issue_type"] == "unknown"


class TestNaturalLanguageCurrencyFormats:
    """Test various natural language currency expressions."""

    @pytest.mark.parametrize(
        "message,expected_value",
        [
            ("My ₹3,500 order arrived damaged yesterday", 3500.0),
            ("My ₹3500 order arrived damaged yesterday", 3500.0),
            ("My Rs. 3500 order arrived damaged yesterday", 3500.0),
            ("My Rs 3,500 order arrived damaged yesterday", 3500.0),
            ("My INR 3500 order arrived damaged yesterday", 3500.0),
            ("My order of 3500 rupees arrived damaged yesterday", 3500.0),
            ("My order of 3500 inr arrived damaged yesterday", 3500.0),
        ],
    )
    def test_currency_extraction_formats(self, message, expected_value):
        result = decide({
            "message": message,
            "days_since_delivery": 1,
            "order_status": "delivered",
        })
        # In all cases value > 2000, so damaged policy should request photos
        assert result["action"] == "REQUEST_PHOTOS"


class TestInputValidationRejections:
    """Testing that invalid inputs fail at the validation layer with HTTP 422."""

    def test_empty_string_message(self):
        res = client.post("/decide", json={"message": ""})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body

    def test_negative_days_since_delivery(self):
        res = client.post("/decide", json={"message": "Damaged", "days_since_delivery": -5})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body

    def test_negative_days_since_dispatch(self):
        res = client.post("/decide", json={"message": "Shipping delay", "days_since_dispatch": -1})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body

    def test_negative_order_value(self):
        res = client.post("/decide", json={"message": "Damaged", "order_value_inr": -100})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body

    def test_malformed_json_body(self):
        res = client.post(
            "/decide",
            content=b"not a json",
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 422

    def test_whitespace_only_message(self):
        res = client.post("/decide", json={"message": "   \t\n  "})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body
