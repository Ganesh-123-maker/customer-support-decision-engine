"""Tests for the fact extractor module."""

import pytest

from app.extractor import extract_facts
from app.models import (
    IssueType,
    OpenedStatus,
    OrderStatus,
    ProductType,
    TicketInput,
)


class TestIssueTypeDetection:
    """Test that issue types are correctly detected from messages."""

    def test_damage_keywords(self):
        ticket = TicketInput(message="My package arrived damaged", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.DAMAGED

    def test_broken_keyword(self):
        ticket = TicketInput(message="The product was broken when I opened it", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.DAMAGED

    def test_defective_keyword(self):
        ticket = TicketInput(message="This device is defective", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.DEFECTIVE

    def test_not_working_keyword(self):
        ticket = TicketInput(message="The product is not working at all", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.DEFECTIVE

    def test_wrong_item_keyword(self):
        ticket = TicketInput(message="I received the wrong item", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.WRONG_ITEM

    def test_wrong_flavour_keyword(self):
        ticket = TicketInput(message="I ordered strawberry but received chocolate", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.WRONG_ITEM

    def test_return_keyword(self):
        ticket = TicketInput(message="I want to return this product", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.RETURN

    def test_changed_mind_keyword(self):
        ticket = TicketInput(message="I changed my mind about this purchase", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.RETURN

    def test_cancel_keyword(self):
        ticket = TicketInput(message="I want to cancel my order", order_status="pending")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.CANCELLATION

    def test_shipping_delay(self):
        ticket = TicketInput(message="My order has not arrived yet", order_status="dispatched")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.SHIPPING_DELAY

    def test_unknown_issue(self):
        ticket = TicketInput(message="Hello, I need help", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.issue_type == IssueType.UNKNOWN


class TestProductTypeDetection:
    """Test product type detection from text."""

    def test_food_from_text(self):
        ticket = TicketInput(message="My chocolate order was damaged", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.product_type == ProductType.FOOD

    def test_nonfood_from_text(self):
        ticket = TicketInput(message="My electronics order was damaged", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.product_type == ProductType.NON_FOOD

    def test_product_type_from_metadata(self):
        ticket = TicketInput(message="Order was damaged", product_type="food", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.product_type == ProductType.FOOD

    def test_metadata_overrides_text(self):
        """Metadata product_type takes precedence."""
        ticket = TicketInput(
            message="My chocolate order was damaged",
            product_type="non_food",
            order_status="delivered",
        )
        facts = extract_facts(ticket)
        assert facts.product_type == ProductType.NON_FOOD


class TestOpenedStatusDetection:
    """Test opened/unopened detection."""

    def test_unopened_from_text(self):
        ticket = TicketInput(message="The product is still sealed, want to return", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.opened_status == OpenedStatus.UNOPENED

    def test_opened_from_metadata(self):
        ticket = TicketInput(message="Want to return this", opened_status="opened", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.opened_status == OpenedStatus.OPENED


class TestCurrencyExtraction:
    """Test currency amount extraction from text."""

    def test_rupee_symbol(self):
        ticket = TicketInput(message="My ₹3,500 order was damaged", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.order_value_inr == 3500

    def test_rs_prefix(self):
        ticket = TicketInput(message="My Rs. 2500 order was damaged", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.order_value_inr == 2500

    def test_metadata_overrides_text(self):
        ticket = TicketInput(
            message="My ₹3,500 order was damaged",
            order_value_inr=5000,
            order_status="delivered",
        )
        facts = extract_facts(ticket)
        assert facts.order_value_inr == 5000


class TestDaysExtraction:
    """Test days extraction from text."""

    def test_yesterday(self):
        ticket = TicketInput(message="My order arrived damaged yesterday", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.days_since_delivery == 1

    def test_today(self):
        ticket = TicketInput(message="Received damaged order today", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.days_since_delivery == 0

    def test_n_days_ago(self):
        ticket = TicketInput(message="Received damaged item 5 days ago", order_status="delivered")
        facts = extract_facts(ticket)
        assert facts.days_since_delivery == 5

    def test_dispatch_days(self):
        ticket = TicketInput(
            message="Dispatched 9 days ago and still not arrived",
            order_status="dispatched",
        )
        facts = extract_facts(ticket)
        assert facts.days_since_dispatch == 9


class TestWrongItemExtraction:
    """Test extraction of ordered vs received details."""

    def test_ordered_but_received(self):
        ticket = TicketInput(
            message="I ordered strawberry but received chocolate",
            order_status="delivered",
        )
        facts = extract_facts(ticket)
        assert facts.what_was_ordered is not None
        assert facts.what_was_received is not None
        assert "strawberry" in facts.what_was_ordered.lower()
        assert "chocolate" in facts.what_was_received.lower()
