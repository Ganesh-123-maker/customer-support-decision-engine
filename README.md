# Customer Support Decision Engine

A deterministic, policy-driven decision engine for customer support tickets. Given a customer message and optional metadata, the system extracts structured facts, identifies the applicable policy, evaluates it against the knowledge base, and returns an action with a concise explanation.

## Architecture

```
Customer Message + Metadata
        │
        ▼
┌─────────────────┐
│  Fact Extractor  │  Keyword/regex-based NLP extraction
│  (extractor.py)  │  → issue type, order value, days, product type, etc.
└────────┬────────┘
         │  TicketFacts
         ▼
┌─────────────────┐
│  Policy Engine   │  Deterministic rule evaluation
│ (policy_engine)  │  → pure function per policy area
└────────┬────────┘
         │  (Action, Explanation)
         ▼
┌─────────────────┐
│   FastAPI App    │  /decide and /decision endpoints
│   (main.py)     │  → structured JSON response
└─────────────────┘
```

**Key design decisions:**
- **No LLM dependency.** All extraction and decisions are deterministic keyword/regex matching and rule evaluation.
- **Explicit policy precedence.** If a customer message touches multiple areas, precedence is deterministically evaluated strictly based on knowledge-base rules:
  1. *Cancellation*: Evaluated against dispatch status (`CANCEL_AND_REFUND` vs `CANNOT_CANCEL_AFTER_DISPATCH`).
  2. *Wrong Item*: Specific fulfillment errors (variant, item, flavour).
  3. *Damaged Goods*: 7-day physical/cosmetic damage window (takes precedence over defect and return per policies).
  4. *Defective Products*: 14-day functional defect window (takes precedence over return per return policy).
  5. *Shipping Delay*: Dispatched transit delay queries (wait, investigate, refund/replace).
  6. *Returns*: Standard change-of-mind return eligibility.
  7. *Unknown*: Missing/unrecognized issues yield `NEEDS_MORE_INFORMATION`.
- **Pure policy functions.** Each policy area is an isolated pure function taking `TicketFacts` and returning `(Action, explanation)`.
- **Exact knowledge-base thresholds.** Boundary conditions (7 days, 14 days, ₹2,000, ₹3,000, 5/7/8/10 days) are implemented precisely.
- **Historical data (`tickets.csv`) is NOT used for decision-making.** Per `DATA_NOTES.md`, decisions are derived from policies, not by looking up similar historical tickets.

## Setup

### Prerequisites
- Python 3.10+

### Installation

```bash
# Clone / navigate to the project
cd Intern_Project

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn app.main:app --port 8000
```

The API will be available at `http://localhost:8000`.

## API Usage

### Health Check

```bash
GET /health
```

Response:
```json
{"status": "ok"}
```

### Decision Endpoint

Supported endpoints:
- `POST /decide`
- `POST /decision`

Content-Type: `application/json`

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | Customer support message (natural language) |
| `order_value_inr` | float | No | Order value in INR |
| `days_since_delivery` | int | No | Calendar days since delivery |
| `days_since_dispatch` | int | No | Calendar days since dispatch |
| `product_type` | string | No | `food`, `non_food`, `mixed`, `unknown` |
| `opened_status` | string | No | `opened`, `unopened`, `unknown` |
| `order_status` | string | No | `pending`, `processing`, `dispatched`, `delivered`, `unknown` |

#### Example Request

```bash
curl -X POST http://localhost:8000/decide \
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

#### Example Response

```json
{
  "action": "REQUEST_PHOTOS",
  "explanation": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
  "reason": "Order valued at ₹3,500 (> ₹2,000) reported damaged within 1 day(s). Photographs of the damaged product and packaging are required before approval.",
  "issue_type": "damaged"
}
```

### Possible Actions

| Action | Policy Area | Description |
|---|---|---|
| `APPROVE_REFUND_OR_REPLACEMENT` | Damaged Goods | Low-value damage (≤ ₹2,000), no photos needed |
| `REQUEST_PHOTOS` | Damaged Goods | High-value damage (> ₹2,000), photos required |
| `APPROVE_REPLACEMENT` | Defective | Defect within window (≤ ₹3,000) |
| `REQUEST_DEFECT_EVIDENCE` | Defective | Defect within window (> ₹3,000) |
| `APPROVE_RETURN` | Returns | Eligible return (unopened non-food, ≤ 14 days) |
| `REJECT_OPENED_ITEM` | Returns | Opened item, not eligible |
| `REJECT_FOOD_RETURN` | Returns | Food items not returnable |
| `CANCEL_AND_REFUND` | Cancellation | Order pre-dispatch (`pending`, `processing`) |
| `CANNOT_CANCEL_AFTER_DISPATCH` | Cancellation | Order already dispatched |
| `REPLACE_CORRECT_ITEM` | Wrong Item | Wrong item within 7-day window |
| `WAIT_AND_TRACK` | Shipping | ≤ 7 days since dispatch |
| `OPEN_SHIPPING_INVESTIGATION` | Shipping | 8–10 days since dispatch |
| `OFFER_REPLACEMENT_OR_REFUND` | Shipping | > 10 days since dispatch |
| `REJECT_OUTSIDE_WINDOW` | Multiple | Outside policy time window |
| `NEEDS_MORE_INFORMATION` | Multiple | Insufficient data to decide |

## Running Tests

```bash
pytest tests/ -v
```

The test suite contains **441 automated tests**:
- **Sample test cases (`test_sample_cases.py`)**: All cases (`S01`–`S05`) from `sample_test_cases.json`.
- **Hidden evaluation simulation (`test_hidden_eval_simulation.py`)**: Realistic unseen products, prices, dates, wording, and fuzzing across all policies.
- **Regression test suite (`test_regressions.py`)**: Explicit regression verification for all bugs and edge-case phrasing.
- **Policy test matrix (`test_policy_matrix.py`)**: Systematic matrix of eligible, ineligible, boundary, missing-info, contradictory, and NLP cases across all 6 policies.
- **Exhaustive boundary tests (`test_boundaries_exhaustive.py`)**: Threshold - 1, threshold, and threshold + 1 for every numerical rule.
- **Adversarial & robustness tests (`test_adversarial.py`)**: Contradictory claims, missing facts, extreme numbers, currency variations (`₹`, `Rs`, `INR`, `rupees`), and validation errors.
- **Live API & determinism tests (`test_api_live.py`)**: Tests both `/decide` and `/decision`, schemas, and 50 repeated runs for determinism.
- **Comprehensive policy tests (`test_policies.py`)**: Branch coverage across all 6 policies.
- **Fact extractor unit tests (`test_extractor.py`)**: Keyword, currency, and date extraction.
- **Historical ticket regression tests (`test_historical_tickets.py`)**: Verifies 100% agreement (214/214) with `tickets.csv`.

## How Policy Decisions Are Derived

Each policy function implements the exact rules from the corresponding knowledge-base markdown file:

1. **Damaged Goods** (`damaged_goods.md`): 7-day window; ≤ ₹2,000 auto-approve; > ₹2,000 request photos.
2. **Defective Products** (`defective_products.md`): 14-day window; > ₹3,000 request evidence; otherwise approve replacement.
3. **Returns** (`returns.md`): Unopened non-food within 14 days; food always rejected; opened always rejected.
4. **Cancellations** (`cancellations.md`): Before dispatch → cancel; after dispatch → cannot cancel.
5. **Wrong Item** (`wrong_item.md`): 7-day window; replace correct item.
6. **Shipping** (`shipping.md`): ≤ 5 days normal; 6–7 wait; 8–10 investigate; > 10 refund/replace.

No rules are inferred beyond what the knowledge base states.

## How Historical Data Is Used

Per `DATA_NOTES.md`, `tickets.csv` is **not** used for decision-making. The engine applies knowledge-base policies to each new ticket independently. The historical data is used only for validation — the regression test suite (`tests/test_historical_tickets.py`) confirms that the policy engine achieves 100% agreement (214/214) with expected resolutions across the entire dataset.

## Project Structure

```
Intern_Project/
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI application, /decide and /decision endpoints
│   ├── models.py                       # Pydantic schemas, enums, data models
│   ├── extractor.py                    # Deterministic fact extraction & precedence
│   └── policy_engine.py                # Deterministic policy evaluation functions
├── tests/
│   ├── __init__.py
│   ├── test_sample_cases.py            # Supplied sample test cases (S01-S05)
│   ├── test_hidden_eval_simulation.py  # Hidden evaluator test simulation
│   ├── test_regressions.py             # Bug & edge-case regression suite
│   ├── test_policy_matrix.py           # Complete policy test matrix
│   ├── test_boundaries_exhaustive.py   # Exhaustive boundary testing (threshold ± 1)
│   ├── test_adversarial.py             # Contradictory inputs, missing info, edge cases
│   ├── test_api_live.py                # Live endpoint verification & determinism
│   ├── test_policies.py                # Comprehensive policy branch tests
│   ├── test_extractor.py               # Fact extractor unit tests
│   └── test_historical_tickets.py      # 100% regression validation on tickets.csv
├── candidate_pack/                     # Assignment files (knowledge base, data)
├── requirements.txt
├── .gitignore
└── README.md
```

## Limitations / Assumptions

- **No LLM required.** All extraction is keyword/regex-based. This handles standard customer phrasing well and safely returns `NEEDS_MORE_INFORMATION` when it cannot determine the issue type.
- **Metadata is trusted.** When structured metadata (`order_value_inr`, `days_since_delivery`, etc.) is provided alongside the message, it takes precedence over values extracted from the message text.
- **Deterministic precedence.** When a customer mentions multiple issues (e.g. damaged and defective), explicit precedence handles the conflict per policy rules.
- **Currency values are in INR.** The system expects and handles INR values only.
