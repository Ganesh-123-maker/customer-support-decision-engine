"""Pydantic models for API request/response schemas and internal data structures."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IssueType(str, Enum):
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    RETURN = "return"
    CANCELLATION = "cancellation"
    WRONG_ITEM = "wrong_item"
    SHIPPING_DELAY = "shipping_delay"
    UNKNOWN = "unknown"


class ProductType(str, Enum):
    FOOD = "food"
    NON_FOOD = "non_food"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class OpenedStatus(str, Enum):
    OPENED = "opened"
    UNOPENED = "unopened"
    UNKNOWN = "unknown"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    UNKNOWN = "unknown"


class Action(str, Enum):
    # Damaged goods
    APPROVE_REFUND_OR_REPLACEMENT = "APPROVE_REFUND_OR_REPLACEMENT"
    REQUEST_PHOTOS = "REQUEST_PHOTOS"

    # Defective products
    APPROVE_REPLACEMENT = "APPROVE_REPLACEMENT"
    REQUEST_DEFECT_EVIDENCE = "REQUEST_DEFECT_EVIDENCE"

    # Returns
    APPROVE_RETURN = "APPROVE_RETURN"
    REJECT_OPENED_ITEM = "REJECT_OPENED_ITEM"
    REJECT_FOOD_RETURN = "REJECT_FOOD_RETURN"

    # Cancellations
    CANCEL_AND_REFUND = "CANCEL_AND_REFUND"
    CANNOT_CANCEL_AFTER_DISPATCH = "CANNOT_CANCEL_AFTER_DISPATCH"

    # Wrong item
    REPLACE_CORRECT_ITEM = "REPLACE_CORRECT_ITEM"

    # Shipping
    WAIT_AND_TRACK = "WAIT_AND_TRACK"
    OPEN_SHIPPING_INVESTIGATION = "OPEN_SHIPPING_INVESTIGATION"
    OFFER_REPLACEMENT_OR_REFUND = "OFFER_REPLACEMENT_OR_REFUND"

    # General
    REJECT_OUTSIDE_WINDOW = "REJECT_OUTSIDE_WINDOW"
    NEEDS_MORE_INFORMATION = "NEEDS_MORE_INFORMATION"


class TicketInput(BaseModel):
    """Input schema for the decision endpoint."""
    message: str = Field(..., min_length=1, description="Customer support message")
    order_value_inr: Optional[float] = Field(None, ge=0, description="Order value in INR")
    days_since_delivery: Optional[int] = Field(None, ge=0, description="Days since delivery")
    days_since_dispatch: Optional[int] = Field(None, ge=0, description="Days since dispatch")
    product_type: Optional[str] = Field(None, description="Product type: food, non_food, mixed, unknown")
    opened_status: Optional[str] = Field(None, description="Opened status: opened, unopened, unknown")
    order_status: Optional[str] = Field(None, description="Order status: pending, dispatched, delivered, unknown")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v


class DecisionResponse(BaseModel):
    """Output schema for the decision endpoint."""
    action: str = Field(..., description="The policy action to take")
    explanation: str = Field(..., description="Concise explanation for the decision")
    reason: Optional[str] = Field(None, description="Reason for the decision (alias for explanation)")
    issue_type: str = Field(..., description="Detected issue type")


class TicketFacts(BaseModel):
    """Structured facts extracted from a customer message and metadata."""
    issue_type: IssueType = IssueType.UNKNOWN
    order_value_inr: Optional[float] = None
    days_since_delivery: Optional[int] = None
    days_since_dispatch: Optional[int] = None
    product_type: ProductType = ProductType.UNKNOWN
    opened_status: OpenedStatus = OpenedStatus.UNKNOWN
    order_status: OrderStatus = OrderStatus.UNKNOWN
    mentions_damage: bool = False
    mentions_defect: bool = False
    mentions_wrong_item: bool = False
    mentions_return: bool = False
    mentions_cancellation: bool = False
    mentions_shipping_delay: bool = False
    what_was_ordered: Optional[str] = None
    what_was_received: Optional[str] = None
