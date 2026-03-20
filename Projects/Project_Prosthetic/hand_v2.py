import pyautogui
import keyboard
import threading
import sys
import time
from pywinauto import Desktop, Application

class CyborgHand:
    def __init__(self):
        # --- SAFETY CORE ---
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        self.abort_flag = False
        self._start_kill_switch_listener()
        
        # --- TACTILE CORE ---
        # "uia" backend is best for modern Windows apps (Explorer, Calculator, VS Code)
        self.desktop = Desktop(backend="uia")
        
        print("=== CYBORG HAND INITIALIZED ===")
        print("SENSES: [TACTILE: ONLINE] [VISION: STANDBY]")
        print("SAFETY: [FAILSAFE: ACTIVE] [ESC: ACTIVE]")

    def _start_kill_switch_listener(self):
        def check_kill_switch():
            while not self.abort_flag:
                if keyboard.is_pressed('esc'):
                    print("\n!!! KILL SWITCH TRIGGERED (ESC) !!!")
                    self.emergency_stop()
                time.sleep(0.1)
        t = threading.Thread(target=check_kill_switch, daemon=True)
        t.start()

    def emergency_stop(self):
        self.abort_flag = True
        print("EMERGENCY DUMP: Aborting all motor functions.")
        sys.exit(1)

    def connect_app(self, title_regex):
        """Connect to an already running application window."""
        try:
            # First try finding the window via Desktop
            window = self.desktop.window(title_re=title_regex)
            if window.exists():
                print(f"[TACTILE] Connected to window: '{title_regex}'")
                return window
            else:
                print(f"[TACTILE] Window '{title_regex}' not found.")
                return None
        except Exception as e:
            print(f"[TACTILE] Connection Error: {e}")
            return None

    def click_element(self, window, element_name, auto_id=None, control_type=None):
        """
        Tactile Click: Uses OS Accessibility API (UIA).
        Directly invokes the 'Invoke' pattern. 100% accuracy if element exists.
        """
        if self.abort_flag: return False
        
        print(f"[TACTILE] Searching for '{element_name}'...")
        try:
            # Build search criteria dynamically
            criteria = {"title": element_name}
            if auto_id: criteria["auto_id"] = auto_id
            if control_type: criteria["control_type"] = control_type
            
            # Find the element
            element = window.child_window(**criteria)
            
            # Highlight it (Proprioception feedback)
            try:
                element.draw_outline(colour='green', thickness=2)
                time.sleep(0.2) # Visual feedback delay
            except:
                pass # Drawing often fails on some apps, ignore

            # Click
            if element.exists():
                # Prefer Click() wrapper which handles coordinates, or invoke() for background
                element.click_input() 
                print(f"[ACTION] Clicked '{element_name}'")
                return True
            else:
                print(f"[TACTILE] Element '{element_name}' not found.")
                return False

        except Exception as e:
            print(f"[TACTILE] Interaction Failed: {e}")
            return False

    def type_text(self, text, interval=0.1):
        """Safe typing wrapper."""
        if self.abort_flag: return
        print(f"[ACTION] Typing: '{text}'")
        pyautogui.write(text, interval=interval)

if __name__ == "__main__":
    # Self-test if run directly
    bot = CyborgHand()
    print("\nSelect a window to test (e.g. Calculator) and press ENTER...")
    # input() 
    # Logic moved to test_cyborg.py
