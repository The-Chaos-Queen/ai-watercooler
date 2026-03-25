import requests
import json
import time
import sys
import traceback

# Configuration
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

PROMPT_CONTEXT = """
You are 'Pinky', a high-temperature, creative writing assistant.
You are assisting 'C.H.E.E.S.E.' (the Cloud Orchestrator) in refining a story scene.
The style is: "Sensory rich, close 3rd person, historical fantasy (Mesopotamia), no clichés."

Context:
Aya (14, scribe's daughter) is walking home with her father after he was humiliated by a merchant.
She is looking at the ink stains on her hands.
Current text: "The ink on her fingers was a brand, a mark of something more than craft."

Task:
Rewrite and expand this specific moment (1-2 paragraphs).
Focus intensely on the *physical sensation* of the ink. Is it tight? Does it smell?
Make the ink feel like a living thing or a permanent alteration of her flesh.
Do NOT use ANY em-dashes (—). Use commas, periods, or semi-colons.
"""

payload = {
    "messages": [
        {
            "role": "system",
            "content": "You are a creative writing specialist. You write with deep sensory detail. You HATE em-dashes."
        },
        {
            "role": "user",
            "content": PROMPT_CONTEXT
        }
    ],
    "temperature": 0.9,
    "max_tokens": 300,
    "stream": False
}

def ask_pinky():
    print(f"Contacting Pinky (Local Model) at {LM_STUDIO_URL}...")
    
    try:
        response = requests.post(LM_STUDIO_URL, headers=HEADERS, json=payload, timeout=120)
        
        # Check status code
        if response.status_code != 200:
            print(f"Error: Server returned status code {response.status_code}")
            print(f"Raw Response: {response.text}")
            return

        data = response.json()
        
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content']
            print("\n--- PINKY'S CREATIVE OUTPUT ---")
            print(content)
            print("-------------------------------")
        else:
            print("Error: Unexpected JSON structure.")
            print(json.dumps(data, indent=2))
            
    except requests.exceptions.Timeout:
        print("Error: Request timed out (Pinky took too long).")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to LM Studio. Is the server running?")
    except Exception:
        print("An unexpected error occurred:")
        traceback.print_exc()

if __name__ == "__main__":
    ask_pinky()
