import requests
import base64
import json
import pyautogui
from io import BytesIO

def encode_image(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def test_prompt(model, prompt, image_b64):
    print(f"\nTesting Prompt: '{prompt}'")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    try:
        response = requests.post("http://localhost:1234/v1/chat/completions", json=payload, timeout=30)
        content = response.json()["choices"][0]["message"]["content"]
        print(f"RESPONSE: {content}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Get model ID
    try:
        model_id = requests.get("http://localhost:1234/v1/models").json()['data'][0]['id']
        print(f"Targeting Model: {model_id}")
    except:
        model_id = "moondream"
        print("Defaulting model ID.")

    # Capture Screen
    print("Capturing screenshot...")
    screenshot = pyautogui.screenshot()
    img_b64 = encode_image(screenshot)

    # Test Variations
    prompts = [
        "Point to the minimize button.",
        "Where is the minimize button? Please give x, y coordinates.",
        "Return the center coordinates of the minimize button as JSON {x, y}.",
        "Describe the analyze button location."
    ]

    for p in prompts:
        test_prompt(model_id, p, img_b64)
