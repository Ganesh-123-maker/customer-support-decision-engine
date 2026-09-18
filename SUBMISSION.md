# Customer Support Decision Engine - Submission Notes

## Project
**Customer Support Decision Engine**

## Repository
https://github.com/Ganesh-123-maker/customer-support-decision-engine

## How to Run

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server:**
   ```bash
   uvicorn app.main:app --port 8000
   ```

The application starts on `http://localhost:8000`. OpenAPI docs are accessible at `/docs` and health check at `/health`.

## How to Test

Run the full automated test suite:
```bash
pytest
```

Run specific test modules:
```bash
pytest tests/test_sample_cases.py -v       # Official sample test cases
pytest tests/test_adversarial.py -v        # Adversarial and edge case tests
pytest tests/test_boundaries_exhaustive.py # Boundary tests (threshold ± 1)
```

## API

- **Endpoint:** `POST /decision` (or `POST /decide`)
- **Headers:** `Content-Type: application/json`

### Example Request
```bash
curl -X POST http://localhost:8000/decision \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My ₹3,500 order arrived damaged yesterday.",
    "order_value_inr": 3500,
    "days_since_delivery": 1,
    "product_type": "non_food",
    "opened_status": "opened",
    "order_status": "delivered"
  }'
```

### Example Response
```json
{
  "action": "REQUEST_PHOTOS",
  "explanation": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
  "reason": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
  "issue_type": "damaged"
}
```

## Verification & Test Results
- **Total Tests:** 442
- **Passed:** 442 (100%)
- **Failed:** 0
- **Skipped:** 0
- **Sample Tests (`test_sample_cases.py`):** 5 passed / 5 (100%)
- **Adversarial / Edge Tests (`test_adversarial.py`):** 29 passed / 29 (100%)

## Key Implementation Points

1. **Policy-Driven Decision Engine:** Pure, deterministic business rule functions faithfully implement all policies from the knowledge base (`damaged_goods.md`, `defective_products.md`, `returns.md`, `cancellations.md`, `wrong_item.md`, `shipping.md`).
2. **Natural-Language Fact Extraction:** Deterministic regex and keyword extraction for currencies (`₹`, `Rs`, `INR`), time expressions (`yesterday`, `X days ago`), product types, and issue categories without external LLM latency or non-determinism.
3. **Deterministic Business Rules & Precedence:** Explicit, consistent precedence order: Cancellation > Wrong Item > Damaged Goods > Defective > Shipping Delay > Returns.
4. **Missing-Information Handling:** Returns `NEEDS_MORE_INFORMATION` with specific actionable explanations when essential decision fields (e.g., delivery date, order value, opened status) are absent.
5. **Robust API:** Built with FastAPI and Pydantic v2; strictly validates inputs (rejects negative numbers, empty or whitespace-only messages, and invalid types with HTTP 422).
6. **Automated Testing:** 442 comprehensive tests including boundary testing (threshold ± 1), hidden evaluation simulation, live API verification, and regression prevention.
7. **Historical-Data Compliance:** In strict accordance with `DATA_NOTES.md`, historical tickets are used solely as validation data (achieving 100% agreement on 214 historical tickets) and never as a decision-lookup mechanism for new tickets.
