"""Historical tickets verification test.

Validates that the policy engine accurately resolves all historical tickets
from tickets.csv in accordance with the knowledge-base rules.
"""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV_PATH = Path(__file__).parent.parent / "candidate_pack" / "candidate_pack" / "data" / "tickets.csv"


def load_tickets():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(params=load_tickets(), ids=lambda row: f"Ticket_{row['ticket_id']}_{row['issue_type']}")
def ticket_row(request):
    return request.param


def test_historical_ticket_resolution(ticket_row):
    """Ensure each historical ticket evaluates to the expected action."""
    payload = {
        "message": ticket_row["message"],
        "order_value_inr": float(ticket_row["order_value_inr"]) if ticket_row["order_value_inr"] else None,
        "days_since_delivery": int(ticket_row["days_since_delivery"]) if ticket_row["days_since_delivery"] else None,
        "days_since_dispatch": int(ticket_row["days_since_dispatch"]) if ticket_row["days_since_dispatch"] else None,
        "product_type": ticket_row["product_type"] or None,
        "opened_status": ticket_row["opened_status"] or None,
        "order_status": ticket_row["order_status"] or None,
    }
    response = client.post("/decide", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == ticket_row["resolved_action"], (
        f"Ticket {ticket_row['ticket_id']} failed: "
        f"expected {ticket_row['resolved_action']}, got {data['action']}. "
        f"Message: '{ticket_row['message']}'. Explanation: {data['explanation']}"
    )
