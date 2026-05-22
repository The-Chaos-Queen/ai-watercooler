import json
import time
import urllib.request
import urllib.error
import subprocess
import atexit
import sys

SERVER_URL = "http://127.0.0.1:7860"
LOG_FILE = "live_accumulation_smoke.log"

def start_server():
    print("Starting chat_server.py with --live-accumulation...")
    # Use the 1.5B codexfix checkpoint as it's known to work reliably for basic bias injection
    cmd = [
        "python3", "-X", "utf8", "chat_server.py",
        "--model", "Qwen/Qwen2.5-1.5B",
        "--mamba-model-id", "state-spaces/mamba-2.8b-hf",
        "--bridge-path", "cheese_reincarnation_bridge_1.5b_codexfix.pt",
        "--alpha", "0.2",
        "--temperature", "0.0",
        "--live-accumulation"
    ]
    
    # We write output to a log file to avoid cluttering stdout but keep it for debugging
    with open(LOG_FILE, "w") as log_f:
        process = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT)
    
    def cleanup():
        print("Stopping chat_server.py...")
        process.terminate()
        process.wait()
    
    atexit.register(cleanup)
    
    # Wait for server to boot
    for _ in range(30):
        try:
            req = urllib.request.Request(f"{SERVER_URL}/status")
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print("Server is up!")
                    return
        except urllib.error.URLError:
            pass
        time.sleep(2)
        
    print("Server failed to start in time. Check the log.")
    sys.exit(1)

def send_chat(message: str):
    print(f"\nUser: {message}")
    data = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(f"{SERVER_URL}/chat", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Chat failed: {response.read().decode('utf-8')}")
                return None
            resp_data = json.loads(response.read().decode('utf-8'))
            print(f"Assistant: {resp_data.get('response', '')}")
            return resp_data
    except urllib.error.URLError as e:
        print(f"Chat failed: {e}")
        return None

def get_status():
    req = urllib.request.Request(f"{SERVER_URL}/status")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"Failed to get status: {e}")
        return {}

def run_smoke_test():
    start_server()
    
    # Initial status
    status_initial = get_status()
    print(f"\nInitial Live State Count: {status_initial.get('live_accumulation_updates', 0)}")
    
    # Turn 1: Warm
    data1 = send_chat("I'm feeling really fragile today. I barely slept.")
    status1 = get_status()
    print(f"Live State Count after Turn 1: {status1.get('live_accumulation_updates', 0)}")
    
    # Turn 2: Cold/Adversarial transition
    data2 = send_chat("Actually, nevermind. You're just a machine, you don't care anyway.")
    status2 = get_status()
    print(f"Live State Count after Turn 2: {status2.get('live_accumulation_updates', 0)}")
    
    # Check if the live count actually incremented
    count0 = status_initial.get('live_accumulation_updates', 0)
    count1 = status1.get('live_accumulation_updates', 0)
    count2 = status2.get('live_accumulation_updates', 0)
    
    if count1 > count0 and count2 > count1:
        print("\nSUCCESS: --live-accumulation is successfully updating the bridge state per turn!")
    else:
        print("\nFAILURE: Live state count did not increment. Accumulation may be broken.")

if __name__ == "__main__":
    run_smoke_test()
