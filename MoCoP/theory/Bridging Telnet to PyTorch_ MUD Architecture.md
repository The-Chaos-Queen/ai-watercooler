# Bridging the Telnet Wrapper to the PyTorch Brain

**Status:** Architecture note

Your current setup (Evennia -> Telnet -> Python JSON Wrapper) is fantastic. To attach your new Mamba + Qwen 4B PoC to this without crashing the MUD connection, you need to enforce a strict **Decoupled Architecture**.

## The Danger of "Blocking" the Telnet Socket

Telnet is a continuous, asynchronous stream. PyTorch inference (especially generating LoRA weights and running a Transformer) is a heavy, synchronous, "blocking" mathematical operation. If your Python wrapper imports PyTorch directly and tries to generate a response in the same script that is listening to the Telnet socket, the MUD will "hang" or disconnect the player due to a timeout while waiting for the GPU to finish calculating.

## The Solution: The Local Microservice

You need to keep the "Body" (the Telnet wrapper) and the "Brain" (the PyTorch script) completely separate. You run them as two different Python scripts communicating locally.

### 1. The Body (Your Existing Wrapper)

Keep your Telnet wrapper almost exactly as it is. It maintains the connection to Evennia and parses the text into JSON.

* **The Modification:** Instead of sending the JSON to LMStudio's API, it uses the standard Python requests library to send an HTTP POST request to http://localhost:8000/generate.

### 2. The Brain (The New PyTorch PoC)

Have your coding AI wrap your 10GB Mamba/Qwen PyTorch script in a lightweight **FastAPI** server. FastAPI will act exactly like your own private, highly specialized version of LMStudio.

**The Workflow:**

1. FastAPI receives the JSON payload from the Telnet wrapper: {"player": "Alice", "action": "Look at goblin"}.
2. The endpoint passes the text to the Mamba model.
3. Mamba updates its state and passes the 20MB tensor to the Hypernetwork.
4. The Hypernetwork generates the LoRA weights and injects them into Qwen 4B.
5. Qwen 4B generates the narrative text (e.g., "The goblin snarls at you.").
6. FastAPI wraps that text back into JSON and returns it as an HTTP response to the Telnet wrapper.
7. The Telnet wrapper pushes it over the socket to Evennia.

## FastAPI Implementation Skeleton (For your AI Coder)

Feed this to your coding AI to generate the brain's API layer:

from fastapi import FastAPI
from pydantic import BaseModel
import torch
# ... (Import your custom Mamba, Qwen, and Hypernetwork classes here) ...

app = FastAPI()

# Pydantic model enforces the JSON structure coming from your Telnet wrapper
class MUDEvent(BaseModel):
 player\_id: str
 action: str
 context: str

# Load the models globally so they stay in the 10GB VRAM
print("Loading Models into VRAM...")
# mamba\_model = load\_mamba()
# qwen\_4b = load\_qwen\_4bit()
# hypernetwork = load\_hypernet()
print("Models Loaded. API Ready.")

@app.post("/generate")
async def generate\_response(event: MUDEvent):
 # 1. Update Mamba State
 # current\_state = mamba\_model(event.action)

 # 2. Generate LoRA via Hypernetwork
 # lora\_A, lora\_B = hypernetwork(current\_state)

 # 3. Inject and Generate with Qwen
 # response\_text = qwen\_4b.generate\_with\_lora(event.context, lora\_A, lora\_B)

 # Mock response for testing
 response\_text = f"You perform '{event.action}'. The world reacts to your presence."

 return {"status": "success", "response": response\_text}

# Run with: uvicorn brain\_api:app --reload

## Why This Architecture Wins

* **Crash Resilience:** If you run out of VRAM and the PyTorch script crashes, your Telnet wrapper stays alive. The player just sees a "Server thinking..." message while you restart the AI.
* **Drop-in Replacement:** By building this FastAPI bridge, your PyTorch PoC will perfectly mimic the exact same JSON inputs and outputs that your current LMStudio setup uses. You literally just change the URL in your Telnet wrapper from LMStudio's port to port 8000.