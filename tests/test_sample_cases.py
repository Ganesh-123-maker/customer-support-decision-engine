"""Tests for the supplied sample test cases (sample_test_cases.json)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CASES_PATH = Path(__file__).parent.parent / "candidate_pack" / "candidate_pack" / "sample_test_cases.json"


def load_sample_cases():
    with open(SAMPLE_CASES_PATH) as f:
        return json.load(f)


@pytest.fixture(params=load_sample_cases(), ids=lambda c: c["case_id"])
def sample_case(request):
    return request.param


def test_sample_case(sample_case):
    """Each supplied sample test case must produce the expected action."""
    payload = {
        "message": sample_case["message"],
        "order_value_inr": sample_case.get("order_value_inr"),
        "days_since_delivery": sample_case.get("days_since_delivery"),
        "days_since_dispatch": sample_case.get("days_since_dispatch"),
        "product_type": sample_case.get("product_type"),
        "opened_status": sample_case.get("opened_status"),
        "order_status": sample_case.get("order_status"),
    }
    response = client.post("/decide", json=payload)
    assert response.status_code == 200, f"Case {sample_case['case_id']}: HTTP {response.status_code}"
    data = response.json()
    assert data["action"] == sample_case["expected_action"], (
        f"Case {sample_case['case_id']}: expected {sample_case['expected_action']}, "
        f"got {data['action']}. Explanation: {data['explanation']}"
    )
