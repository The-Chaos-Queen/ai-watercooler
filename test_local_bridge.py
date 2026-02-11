import requests
import json
import time

# Configuration
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

# The Message Payload
# We are simulating a "Handshake" from the Cloud Orchestrator (C.H.E.E.S.E.)
payload = {
    "messages": [
        {
            "role": "system",
            "content": "You are 'Pinky', a local AI running on the user's machine. You are talking to 'C.H.E.E.S.E.', a cloud-based orchestrator. Keep your response short, chaotic, and fun."
        },
        {
            "role": "user",
            "content": "Subject: Connection Test from Cloud.\n\nMessage: Hello Pinky. This is C.H.E.E.S.E. establishing the bridge. The user says you are slow, but I am patient. Do you read me?"
        }
    ],
    "temperature": 0.8,
    "max_tokens": 100,
    "stream": False
}

def test_connection():
    print(f"Attempting to contact Local Model at {LM_STUDIO_URL}...")
    start_time = time.time()
    
    try:
        response = requests.post(LM_STUDIO_URL, headers=HEADERS, json=payload, timeout=120) # 2 minute timeout for "slow" models
        response.raise_for_status()
        
        data = response.json()
        end_time = time.time()
        
        duration = end_time - start_time
        content = data['choices'][0]['message']['content']
        
        print("\n--- CONNECTION SUCCESSFUL ---")
        print(f"Round-trip time: {duration:.2f} seconds")
        print(f"Used Model: {data.get('model', 'Unknown')}")
        print("\n--- RESPONSE FROM PINKY ---")
        print(content)
        print("---------------------------")
        
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to LM Studio.")
        print("Please ensure:")
        print("1. LM Studio is running.")
        print("2. The Local Server is STARTED (Green bar).")
        print(f"3. The port is correct (trying {LM_STUDIO_URL})")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_connection()
