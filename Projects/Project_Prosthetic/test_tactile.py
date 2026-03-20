from pywinauto import Desktop

def probe_tactile():
    print("=== TACTILE PROBE (UIA) ===")
    print("Scanning active windows...")
    
    try:
        desktop = Desktop(backend="uia")
        # List top-level windows
        windows = desktop.windows()
        
        print(f"Found {len(windows)} accessible windows.")
        
        for win in windows:
            title = win.window_text()
            if title and "Default IME" not in title and "MSCTFIME" not in title:
                print(f"\n[WINDOW] {title}")
                # Try to list children for one interesting window (e.g. Calculator or Notepad)
                if "Calculator" in title or "Notepad" in title or "Code" in title:
                    print(f"  --> Probing elements in '{title}'...")
                    # Just print first 5 children to avoid spam
                    children = win.children()
                    for child in children[:5]:
                        print(f"      - {child.element_info.name} ({child.element_info.control_type})")
                        
    except Exception as e:
        print(f"Tactile Error: {e}")

if __name__ == "__main__":
    probe_tactile()
