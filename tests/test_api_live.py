"""API endpoint verification, live client tests, and determinism check."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("endpoint", ["/decide", "/decision"])
def test_both_decision_endpoints_work_identically(endpoint):
    payload = {
        "message": "My \u20b93,500 order arrived damaged yesterday.",
        "order_value_inr": 3500,
        "days_since_delivery": 1,
        "product_type": "non_food",
        "opened_status": "opened",
        "order_status": "delivered",
    }
    resp = client.post(endpoint, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "REQUEST_PHOTOS"
    assert "explanation" in data
    assert "reason" in data
    assert data["reason"] == data["explanation"]
    assert data["issue_type"] == "damaged"


def test_response_schema_fields():
    payload = {
        "message": "I changed my mind about this unopened non-food product. It arrived 10 days ago.",
        "order_value_inr": 1200,
        "days_since_delivery": 10,
        "product_type": "non_food",
        "opened_status": "unopened",
        "order_status": "delivered",
    }
    resp = client.post("/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Confirm exact expected keys
    assert set(data.keys()) >= {"action", "explanation", "reason", "issue_type"}
    assert data["action"] == "APPROVE_RETURN"
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 0


def test_determinism_50_iterations():
    """Ensure that 50 consecutive runs of identical input produce identical output."""
    payload = {
        "message": "The product turns on but does not function correctly.",
        "order_value_inr": 2499,
        "days_since_delivery": 14,
        "product_type": "non_food",
        "opened_status": "opened",
        "order_status": "delivered",
    }

    first_resp = client.post("/decide", json=payload).json()
    for _ in range(50):
        resp = client.post("/decide", json=payload).json()
        assert resp == first_resp, "Output must be completely deterministic!"
