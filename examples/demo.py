import sys
import httpx
import json

# Ensure UTF-8 output encoding across all operating systems including Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run_demo():
    print("Running Customer Support Decision Engine Demo...\n")
    url = "http://localhost:8000/decision"
    
    samples = [
        {
            "ticket_id": "DEMO-1",
            "message": "I want to cancel my order, I just placed it.",
            "order_status": "processing"
        },
        {
            "ticket_id": "DEMO-2",
            "message": "My ₹1,500 phone arrived yesterday but the screen is cracked.",
            "order_value_inr": 1500,
            "days_since_delivery": 1,
            "order_status": "delivered"
        },
        {
            "ticket_id": "DEMO-3",
            "message": "My ₹4,500 headphones arrived broken today.",
            "order_value_inr": 4500,
            "days_since_delivery": 0,
            "order_status": "delivered"
        },
        {
            "ticket_id": "DEMO-4",
            "message": "I received a toaster instead of the blender I ordered.",
            "days_since_delivery": 2,
            "order_status": "delivered"
        },
        {
            "ticket_id": "DEMO-5",
            "message": "It has been 9 days since my order was dispatched and it has not arrived.",
            "days_since_dispatch": 9,
            "order_status": "dispatched"
        },
        {
            "ticket_id": "DEMO-6",
            "message": "My item is damaged.",
            "order_status": "delivered"
        }
    ]

    try:
        with httpx.Client() as client:
            for sample in samples:
                ticket_id = sample.pop("ticket_id")
                print(f"--- Ticket: {ticket_id} ---")
                print(f"Payload: {json.dumps(sample)}")
                
                response = client.post(url, json=sample)
                if response.status_code == 200:
                    result = response.json()
                    print(f"Issue: {result.get('issue_type')}")
                    print(f"Action: {result.get('action')}")
                    print(f"Reason: {result.get('reason')}\n")
                else:
                    print(f"Error: {response.status_code} - {response.text}\n")
    except httpx.ConnectError:
        print("Error: Could not connect to the API. Make sure the server is running on http://localhost:8000")
        print("Start it with: uvicorn app.main:app --port 8000")

if __name__ == "__main__":
    run_demo()
