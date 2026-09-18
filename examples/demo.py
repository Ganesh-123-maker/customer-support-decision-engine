import httpx
import json

def run_demo():
    print("Running Customer Support Decision Engine Demo...\n")
    url = "http://localhost:8000/decision"
    
    samples = [
        {
            "ticket_id": "DEMO-1",
            "customer_id": "CUST-1",
            "customer_text": "I want to cancel my order, I just placed it.",
            "order_status": "processing"
        },
        {
            "ticket_id": "DEMO-2",
            "customer_id": "CUST-2",
            "customer_text": "My phone arrived but the screen is cracked.",
            "order_status": "delivered"
        },
        {
            "ticket_id": "DEMO-3",
            "customer_id": "CUST-3",
            "customer_text": "I received a toaster instead of the blender I ordered.",
            "order_status": "delivered"
        },
        {
            "ticket_id": "DEMO-4",
            "customer_id": "CUST-4",
            "customer_text": "It's been 5 days and my package hasn't arrived.",
            "order_status": "shipped"
        }
    ]

    try:
        with httpx.Client() as client:
            for sample in samples:
                print(f"--- Ticket: {sample['ticket_id']} ---")
                print(f"Text: {sample['customer_text']}")
                print(f"Status: {sample['order_status']}")
                
                response = client.post(url, json=sample)
                if response.status_code == 200:
                    result = response.json()
                    print(f"Decision: {result.get('action')}")
                    print(f"Reason: {result.get('reason')}\n")
                else:
                    print(f"Error: {response.status_code} - {response.text}\n")
    except httpx.ConnectError:
        print("Error: Could not connect to the API. Make sure the server is running on http://localhost:8000")
        print("Start it with: uvicorn app.main:app --reload")

if __name__ == "__main__":
    run_demo()
