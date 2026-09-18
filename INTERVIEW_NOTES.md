# Interview & Demo Defense Notes

## Project Overview
The **Customer Support Decision Engine** is a deterministic, policy-driven backend service built with FastAPI and Python 3.11. Given customer support messages and optional metadata, it extracts structured facts via pattern and keyword analysis, maps the issue to specific knowledge-base policies, and outputs a policy action with a concise explanation.

---

## Architecture
### Request Flow
```
Customer Ticket (JSON payload: message + optional metadata)
  │
  ▼
API Validation (Pydantic models in app/models.py: schema check, whitespace check, range checks)
  │
  ▼
Fact Extractor (app/extractor.py)
  ├── Regex extraction for currency (₹, Rs, INR, rupees)
  ├── Natural language extraction for days (e.g., "yesterday" = 1, "3 days ago" = 3)
  ├── Keyword matching for issue types (damaged, defective, returns, cancellations, wrong item, shipping delay)
  └── Explicit deterministic precedence resolution
  │
  ▼
Policy Engine (app/policy_engine.py)
  └── Evaluates isolated pure functions against extracted TicketFacts:
      • evaluate_damaged_goods()
      • evaluate_defective_products()
      • evaluate_returns()
      • evaluate_cancellations()
      • evaluate_wrong_item()
      • evaluate_shipping_delay()
  │
  ▼
Decision & Explanation Generation
  └── Formulates structured Action, detailed Explanation, Reason alias, and detected IssueType
  │
  ▼
HTTP 200 JSON Response (via /decision or /decide)
```

---

## Why Policy-Driven Logic?
1. **Compliance and Auditability:** Company policies (e.g., damage windows, refund thresholds) are legal and financial commitments. Rule-based engines guarantee 100% adherence to documented policies without probabilistic hallucination.
2. **Determinism:** The same input with the same facts will always yield the exact same decision, avoiding non-deterministic edge cases.
3. **Traceability:** Every decision produces a transparent, deterministic explanation directly citing the policy rule and threshold applied.

---

## Historical Data
Per `DATA_NOTES.md`:
- `tickets.csv` is **never used as a lookup table** or KNN/similarity search mechanism to copy historical `resolved_action` for new tickets.
- Instead, historical data is used exclusively as a validation test suite (`tests/test_historical_tickets.py`). The test suite feeds each historical ticket's message and metadata into the policy engine and confirms 100% agreement (214/214 tickets) between policy-derived actions and historical outcomes.

---

## Natural Language Extraction
- **Currency:** Extracted via regex supporting `₹3,500`, `₹3500`, `Rs. 3500`, `Rs 3500`, `INR 3500`, and `3500 rupees`.
- **Timing:** Relative time expressions such as `yesterday` (1 day), `today` (0 days), `X days ago`, `X days back`, `X calendar days` are parsed into integer day counts.
- **Keywords:** Stemmed/normalized keyword sets detect issues (e.g., "cracked", "shattered", "does not work", "stopped working", "received X instead of Y", "still not delivered").
- **Priority:** Explicit metadata (`order_value_inr`, `days_since_delivery`, etc.) always takes precedence over message text if provided.

---

## Missing Information
When a ticket lacks the required factual attributes to evaluate policy conditions (e.g., customer reports damage within window but does not provide order value, or reports an issue without delivery timing), the engine deterministically returns:
- **Action:** `NEEDS_MORE_INFORMATION`
- **Explanation:** Explicitly states what specific facts are missing (e.g., *"Customer reported damaged item within the 7-day window, but order value is missing. Please collect order value to determine if photos are required."*).

---

## Boundary Handling
All numerical and calendar thresholds are strictly applied per the knowledge base:
- **Damaged Goods:** Auto-approved if `order_value_inr <= 2000` and `days_since_delivery <= 7`. If `order_value_inr > 2000`, requires `REQUEST_PHOTOS`. If `days_since_delivery > 7`, `REJECT_OUTSIDE_WINDOW`.
- **Defective Products:** 14-day window (`days_since_delivery <= 14`). If `order_value_inr > 3000`, requires `REQUEST_DEFECT_EVIDENCE`; otherwise `APPROVE_REPLACEMENT`.
- **Returns:** Non-food and unopened items within 14 days (`APPROVE_RETURN`). Opened items rejected (`REJECT_OPENED_ITEM`). Food items rejected (`REJECT_FOOD_RETURN`).
- **Shipping:** `<= 5` days normal, `6–7` days `WAIT_AND_TRACK`, `8–10` days `OPEN_SHIPPING_INVESTIGATION`, `> 10` days `OFFER_REPLACEMENT_OR_REFUND`.
- **Cancellations:** Pre-dispatch (`pending`, `processing`) → `CANCEL_AND_REFUND`. Dispatched or delivered → `CANNOT_CANCEL_AFTER_DISPATCH`.

Tested exhaustively with threshold - 1, threshold, and threshold + 1.

---

## API Contract
- **Endpoints:** `POST /decision` and `POST /decide`
- **Health Check:** `GET /health` → `{"status": "ok"}`
- **OpenAPI Docs:** `GET /docs` and `GET /openapi.json`
- **Request Body:**
  ```json
  {
    "message": "My ₹3,500 order arrived damaged yesterday.",
    "order_value_inr": 3500,
    "days_since_delivery": 1,
    "product_type": "non_food",
    "opened_status": "opened",
    "order_status": "delivered"
  }
  ```
- **Response Body:**
  ```json
  {
    "action": "REQUEST_PHOTOS",
    "explanation": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
    "reason": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
    "issue_type": "damaged"
  }
  ```

---

## Testing Strategy
The automated test suite contains **442 tests** covering:
1. **Sample Tests (`test_sample_cases.py`):** 5 official assignment sample cases (`S01` to `S05`).
2. **Adversarial & Edge Cases (`test_adversarial.py`):** Contradictory claims, missing facts, extreme values, whitespace validation, currency format variations.
3. **Exhaustive Boundary Matrix (`test_boundaries_exhaustive.py`):** Off-by-one verification for every numerical threshold.
4. **Hidden Evaluation Simulation (`test_hidden_eval_simulation.py`):** Unseen products, prices, and complex multi-issue sentences.
5. **Live API Tests (`test_api_live.py`):** Status codes, route aliases, schema integrity, and repeated determinism calls.
6. **Policy Engine Matrix (`test_policy_matrix.py` & `test_policies.py`):** Full branch coverage across all 6 policies.
7. **Extractor Unit Tests (`test_extractor.py`):** NLP parsing accuracy.
8. **Historical Regression (`test_historical_tickets.py`):** 214/214 agreement against `tickets.csv`.

---

## Limitations
- Extraction relies on deterministic keyword and regex heuristics; highly poetic or obscure idioms without standard keywords default to `NEEDS_MORE_INFORMATION`.
- Handles INR currency notation only.
- Metadata is considered trusted when provided directly.

---

## Questions I Should Be Ready For

**Q: Why did you choose a rule-based policy engine instead of training a machine learning model?**  
*A:* Company refund and return policies are rigid business constraints with clear numerical thresholds. A machine learning classifier can hallucinate, drift over time, and requires retraining whenever a policy threshold changes. A rule-based policy engine is 100% deterministic, auditable, and allows instant updates whenever business policies are amended.

**Q: How do you prevent historical resolved_action from becoming the decision source?**  
*A:* The application runtime has zero dependency on `tickets.csv`. The CSV is solely read within `tests/test_historical_tickets.py` during pytest test execution as an offline regression benchmark.

**Q: How do you handle missing information?**  
*A:* Rather than guessing or assuming default values (e.g., assuming an order is below ₹2,000 or assuming it was delivered yesterday), the system flags missing required fields and safely returns `NEEDS_MORE_INFORMATION`, prompting the agent or customer for the exact missing attribute.

**Q: How do you handle conflicting information?**  
*A:* We use explicit policy precedence defined by the business policies: Cancellation takes highest priority, followed by Wrong Item, Damaged Goods (which explicitly supersedes defect and standard return for broken goods), Defective Products, Shipping Delays, and lastly standard Returns.

**Q: How are policy boundaries tested?**  
*A:* Through `test_boundaries_exhaustive.py`, which systematically tests `threshold - 1`, `threshold`, and `threshold + 1` for every single numerical boundary (₹2000, ₹3000, 5 days, 7 days, 8 days, 10 days, 14 days).

**Q: How would you scale this system?**  
*A:* Because all policy evaluation functions and fact extractors are pure and stateless with no database locks or external network dependencies, the FastAPI application scales horizontally across multiple worker processes (e.g., with Gunicorn/Uvicorn workers) or container replicas behind a standard load balancer.

**Q: What would you improve if given more development time?**  
*A:* I would add a policy configuration layer (e.g., YAML or database-backed policy rules) so business teams can adjust thresholds like ₹2,000 or 14 days without changing Python code, and potentially integrate an optional local embedding model as a fallback classifier for ambiguous natural language phrasing.

---

## 2-Minute Demo

1. **Start the service:**
   ```bash
   uvicorn app.main:app --port 8000
   ```
2. **Send a standard Damaged Goods ticket (High-Value):**
   ```bash
   curl -X POST http://localhost:8000/decision -H "Content-Type: application/json" -d "{\"message\": \"My phone arrived cracked yesterday\", \"order_value_inr\": 3500, \"days_since_delivery\": 1, \"order_status\": \"delivered\"}"
   ```
   *Output:* `REQUEST_PHOTOS` (Order value > ₹2,000 within 7-day window).
3. **Show Missing Information handling:**
   ```bash
   curl -X POST http://localhost:8000/decision -H "Content-Type: application/json" -d "{\"message\": \"My package was damaged on delivery\", \"days_since_delivery\": 2, \"order_status\": \"delivered\"}"
   ```
   *Output:* `NEEDS_MORE_INFORMATION` (Identifies that `order_value_inr` is needed).
4. **Show Boundary Handling (₹2,000 vs ₹2,001):**
   - At ₹2,000: `APPROVE_REFUND_OR_REPLACEMENT`
   - At ₹2,001: `REQUEST_PHOTOS`
5. **Run the automated test suite:**
   ```bash
   pytest
   ```
   *Output:* 442 passed in ~6 seconds.

---

## Explain the Project in 60 Seconds
"I built a deterministic customer support decision engine using FastAPI and Python. When a customer submits a ticket, the system parses the natural language text using robust regex and keyword heuristics to extract key facts—like the issue type, order value in INR, and delivery or dispatch time windows. It then routes these facts through pure, isolated policy functions derived directly from company policy documentation—covering damaged goods, defective items, returns, cancellations, wrong items, and shipping delays. 

If any required information is missing, it returns `NEEDS_MORE_INFORMATION` specifying exactly what is needed, rather than guessing. If multiple issues are raised, it resolves them deterministically using explicit policy precedence. Most importantly, per the assignment instructions, decisions are never made by looking up historical tickets; instead, historical tickets were used strictly as an offline test suite where the engine achieved 100% agreement. The repository is backed by 442 automated tests covering all boundaries, edge cases, and live API contracts."
