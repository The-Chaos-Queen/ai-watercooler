# C.H.E.E.S.E. Context Compressor
# Purpose: Compresses the "Entropy" of recent thoughts/files into a crystallized summary.

import os
from pathlib import Path
from datetime import datetime

# Define Memory Paths
MEMORY_DIR = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory")
DASHBOARD = MEMORY_DIR / "00_DASHBOARD.md"
PRIME = MEMORY_DIR / "00_CHEESE_PRIME.md"
ARCHIVE_DIR = MEMORY_DIR / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

def compress_session():
    print("=== C.H.E.E.S.E. COMPRESSOR ===")
    print(f"Time: {datetime.now()}")
    
    # 1. Read Current State
    if DASHBOARD.exists():
        with open(DASHBOARD, 'r', encoding='utf-8') as f:
            dashboard_content = f.read()
            print(f"\n[READ] Dashboard ({len(dashboard_content)} chars)")
    
    # 2. Ask User for the "Crystal" (The Core Insight)
    print("\n[INPUT] What is the core insight/win of this session?")
    print("(This will be saved to the Prime Memory)")
    insight = input("> ")
    
    if not insight:
        print("[ABORT] No insight provided.")
        return

    # 3. Append to Prime Memory (The Scratchpad)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n*   *Entry {timestamp}:* {insight}"
    
    with open(PRIME, 'a', encoding='utf-8') as f:
        f.write(entry)
    print(f"[COMPRESS] Added to 00_CHEESE_PRIME.md")

    # 4. Optional: Archive old files (Stub)
    # Future: Move 'temp' files to 'archive'
    
    print("\n[DONE] Entropy Reduced. Context Crystallized.")

if __name__ == "__main__":
    compress_session()
