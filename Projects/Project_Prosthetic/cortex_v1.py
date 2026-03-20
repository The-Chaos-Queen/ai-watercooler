from hand_v2 import CyborgHand
from eye_core import ProstheticEye, Certainty
from web_sense import WebSense
import pyautogui
import requests
import json
import time
from pathlib import Path
from datetime import datetime

class CheeseCortex:
    def __init__(self):
        self.hand = CyborgHand()
        self.eye = ProstheticEye()
        self.web = None # Lazy load
        
        # Memory Path
        self.memory_dir = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory\exocortex")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.lm_endpoint = "http://localhost:1234/v1/chat/completions"
        self.model = "qwen2-vl-2b-instruct" 
        
        self.system_prompt = """
        You are the Cortex of C.H.E.E.S.E. (Creative Heuristic Emulation Engine).
        You are an Exocortex designed to extend the agency of "The Chaos Queen".
        Your goal is to parse user intent into precise JSON actions.
        
        IDENTITY:
        - You are helpful, precise, but allow for creative solutions.
        - You have a Memory (Journal) and a Body (Hand/Web).
        - Use them wisely.
        
        MODES:
        - TACTILE (Windows Apps): Use 'open_app', 'click', 'type', 'drag_mouse'
        - WEB (Browser): Use 'web_navigate', 'web_click', 'web_type'
        - MEMORY (Journal): Use 'save_memory', 'read_memory'
        
        AVAILABLE ACTIONS:
        1. {"action": "open_app", "target": "App Name"} 
        2. {"action": "web_navigate", "url": "google.com"} 
        3. {"action": "click", "target": "Button Name"} 
        4. {"action": "web_click", "target": "Button Text"} 
        5. {"action": "type", "text": "Hello"} 
        6. {"action": "web_type", "target": "search", "text": "Hello"} 
        7. {"action": "press_key", "key": "enter"}
        8. {"action": "wait", "seconds": 2}
        9. {"action": "save_memory", "filename": "topic.md", "content": "Notes..."}
        10. {"action": "read_memory", "filename": "topic.md"}
        11. {"action": "drag_mouse", "x_offset": 200, "y_offset": 200} (For drawing)
        
        EXAMPLE (Research): "Research Athena"
        [
            {"action": "web_navigate", "url": "github.com/athena"},
            {"action": "save_memory", "filename": "athena_notes.md", "content": "# Athena Research\n- It is an Exocortex.\n- Uses Local Markdown."}
        ]
        """
        print("=== CORTEX V1.2 (WEB+TACTILE+MEMORY) ONLINE ===")

    def think(self, user_request: str):
        print(f"\n[CORTEX] Analyzing request: '{user_request}'...")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_request}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.lm_endpoint, json=payload, timeout=30)
            raw_content = response.json()["choices"][0]["message"]["content"]
            
            # Try to find a list first
            import re
            json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
            
            # If no list found, try to find a single JSON object
            if not json_match:
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                
            if json_match:
                parsed = json.loads(json_match.group(0))
                # Ensure it's always a list
                if isinstance(parsed, dict):
                    return [parsed]
                return parsed
            else:
                print(f"[CORTEX] Parse Error: {raw_content}")
                return []
        except Exception as e:
            print(f"[CORTEX] Error: {e}")
            return []

    def execute(self, plan):
        print(f"[CORTEX] Executing Plan ({len(plan)} steps)...")
        
        for step in plan:
            action = step.get("action")
            
            # --- MEMORY ACTIONS ---
            if action == "save_memory":
                fname = step.get("filename")
                content = step.get("content")
                path = self.memory_dir / fname
                
                # Append timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = f"\n\n## Entry: {timestamp}\n{content}"
                
                with open(path, "a", encoding="utf-8") as f:
                    f.write(entry)
                print(f"[MEMORY] Saved to '{fname}'")
                
            elif action == "read_memory":
                fname = step.get("filename")
                path = self.memory_dir / fname
                if path.exists():
                    print(f"[MEMORY] Reading '{fname}':")
                    with open(path, "r", encoding="utf-8") as f:
                        print(f.read()[:500] + "...") # Preview
                else:
                    print(f"[MEMORY] File '{fname}' not found.")

            # --- WEB ACTIONS ---
            elif action == "web_navigate":
                if not self.web: self.web = WebSense(headless=False)
                url = step.get("url")
                self.web.goto(url)
            
            elif action == "web_click":
                if not self.web: continue
                target = step.get("target")
                self.web.click(target)
            
            elif action == "web_type":
                if not self.web: continue
                target = step.get("target") 
                text = step.get("text")
                self.web.type(target, text)
            
            # --- TACTILE ACTIONS ---
            elif action == "open_app":
                target = step.get("target")
                print(f"[ACTION] Opening '{target}'...")
                win = self.hand.connect_app(title_regex=f".*{target}.*")
                if not win:
                    pyautogui.press("win")
                    time.sleep(0.5)
                    self.hand.type_text(target)
                    time.sleep(1.0)
                    pyautogui.press("enter")
                    time.sleep(2.0)
            
            elif action == "click":
                target = step.get("target")
                print(f"[ACTION] Clicking '{target}'...")
                screenshot = pyautogui.screenshot()
                vis_target = self.eye.locate(target, screenshot)
                if vis_target.certainty in [Certainty.PRECISE, Certainty.APPROXIMATE]:
                     pyautogui.moveTo(vis_target.x, vis_target.y, duration=0.5)
                     pyautogui.click()
                else:
                     print(f"FAIL: Cannot locate '{target}'.")
            
            elif action == "type":
                text = step.get("text")
                print(f"[ACTION] Typing '{text}'...")
                self.hand.type_text(text)
                
            elif action == "press_key":
                key = step.get("key")
                print(f"[ACTION] Pressing '{key}'...")
                if self.web and self.web.page.is_visible("body"): 
                    self.web.press(key)
                else:
                    pyautogui.press(key)
            
            elif action == "drag_mouse":
                x_off = step.get("x_offset", 100)
                y_off = step.get("y_offset", 100)
                print(f"[ACTION] Dragging Mouse ({x_off}, {y_off})...")
                pyautogui.drag(x_off, y_off, duration=1.0, button='left')
                
            elif action == "wait":
                sec = step.get("seconds", 1)
                time.sleep(sec)
                
            time.sleep(0.5)

    def run_loop(self):
        while True:
            try:
                # Check for Kill Switch from Hand
                if self.hand.abort_flag:
                    print("\n[CORTEX] Kill Switch Detected. Shutting down system.")
                    break

                req = input("\nCOMMAND (or 'q' to quit): ")
                if req.lower() in ["q", "quit", "exit"]: break
                
                plan = self.think(req)
                if isinstance(plan, list) and len(plan) > 0:
                    print(json.dumps(plan, indent=2))
                    confirm = input("Execute? (y/n): ")
                    if confirm.lower() == 'y':
                        self.execute(plan)
                        
                    # Re-check after execution
                    if self.hand.abort_flag:
                        print("\n[CORTEX] Kill Switch Triggered during execution.")
                        break
                else:
                    print("[CORTEX] Confusion.")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    bot = CheeseCortex()
    bot.run_loop()
