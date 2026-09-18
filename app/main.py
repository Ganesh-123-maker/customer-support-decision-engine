"""FastAPI application — Customer Support Decision Engine."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.extractor import extract_facts
from app.models import DecisionResponse, TicketInput
from app.policy_engine import evaluate

app = FastAPI(
    title="Customer Support Decision Engine",
    description=(
        "Accepts a customer support ticket, extracts facts, applies the "
        "relevant knowledge-base policy, and returns a deterministic action "
        "with explanation."
    ),
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return clean, structured JSON errors for request validation failures."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg", "Invalid value")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": errors},
    )


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


def _process_ticket(ticket: TicketInput) -> DecisionResponse:
    facts = extract_facts(ticket)
    action, explanation = evaluate(facts)
    return DecisionResponse(
        action=action.value,
        explanation=explanation,
        reason=explanation,
        issue_type=facts.issue_type.value,
    )


@app.post("/decide", response_model=DecisionResponse)
def decide(ticket: TicketInput) -> DecisionResponse:
    """Main decision endpoint.

    Accepts a customer support ticket and returns the policy action.
    """
    return _process_ticket(ticket)


@app.post("/decision", response_model=DecisionResponse)
def decision(ticket: TicketInput) -> DecisionResponse:
    """Alias for /decide endpoint."""
    return _process_ticket(ticket)

