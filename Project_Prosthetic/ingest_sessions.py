"""
ingest_sessions.py — Bulk Ingestion of Markdown Chat Logs into Qdrant
Reads markdown files, chunks them, embeds locally, stores in Qdrant.

Usage:
    python ingest_sessions.py                           # Ingest all .md files in default dirs
    python ingest_sessions.py path/to/file.md           # Ingest a single file
    python ingest_sessions.py path/to/folder/            # Ingest all .md files in a folder
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from memory_engine import MemoryEngine

# Default directories to scan for session logs
DEFAULT_DIRS = [
    Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\Claude_15_01_2026"),
    Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM\CHEESE_Memory"),
]

# Skip patterns (filenames to ignore)
SKIP_PATTERNS = [
    "00_DASHBOARD",       # Dashboard is ephemeral
    "dashboard_",         # Dashboard artifacts
    "test_",              # Test files
]


def chunk_markdown(content: str, source_name: str, max_chunk_size: int = 500) -> list[dict]:
    """
    Splits markdown into meaningful chunks.
    
    Strategy:
    1. Split by ## headers first (section-level)
    2. If a section is too long, split by paragraphs
    3. Discard tiny chunks (< 30 chars)
    """
    chunks = []
    
    # Split by ## headers
    sections = re.split(r'\n(?=## )', content)
    
    for section in sections:
        section = section.strip()
        if not section or len(section) < 30:
            continue
        
        # Extract section header if present
        header_match = re.match(r'^(#{1,3}\s+.+)', section)
        header = header_match.group(1).strip() if header_match else ""
        
        if len(section) <= max_chunk_size:
            chunks.append({
                "content": section,
                "header": header,
            })
        else:
            # Split long sections by paragraphs
            paragraphs = section.split("\n\n")
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                    
                if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "header": header,
                    })
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
            
            if current_chunk.strip() and len(current_chunk.strip()) > 30:
                chunks.append({
                    "content": current_chunk.strip(),
                    "header": header,
                })
    
    return chunks


def ingest_file(mem: MemoryEngine, filepath: Path) -> int:
    """Ingest a single markdown file. Returns number of chunks stored."""
    print(f"\n[INGEST] Processing: {filepath.name}")
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = filepath.read_text(encoding="latin-1")
        except Exception as e:
            print(f"  [SKIP] Cannot read: {e}")
            return 0
    
    if len(content.strip()) < 50:
        print(f"  [SKIP] Too short ({len(content)} chars)")
        return 0
    
    chunks = chunk_markdown(content, filepath.stem)
    
    if not chunks:
        print(f"  [SKIP] No meaningful chunks found")
        return 0
    
    # Determine type from path
    doc_type = "session_log"
    if "CHEESE_Memory" in str(filepath):
        doc_type = "memory"
    elif "Claude" in str(filepath):
        doc_type = "claude_session"
    elif "MF_Version" in str(filepath):
        doc_type = "creative_writing"
    
    # Extract date from filename if possible (e.g., "14_TWoS_3-4.md")
    date_str = datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d")
    
    stored = 0
    for i, chunk in enumerate(chunks):
        mem.store(
            content=chunk["content"],
            metadata={
                "type": doc_type,
                "source": filepath.name,
                "source_path": str(filepath),
                "section": chunk.get("header", ""),
                "chunk_index": i,
                "file_date": date_str,
            }
        )
        stored += 1
    
    print(f"  [DONE] {stored} chunks stored from {filepath.name}")
    return stored


def ingest_directory(mem: MemoryEngine, dirpath: Path) -> int:
    """Ingest all .md files in a directory. Returns total chunks stored."""
    if not dirpath.exists():
        print(f"[WARN] Directory not found: {dirpath}")
        return 0
    
    md_files = sorted(dirpath.glob("*.md"))
    
    # Filter out skipped files
    md_files = [
        f for f in md_files
        if not any(skip in f.stem for skip in SKIP_PATTERNS)
    ]
    
    print(f"\n[INGEST] Found {len(md_files)} markdown files in {dirpath.name}/")
    
    total = 0
    for f in md_files:
        total += ingest_file(mem, f)
    
    return total


def main():
    print("=== EXOCORTEX INGESTION ENGINE ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    mem = MemoryEngine()
    
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    total = 0
    
    if targets:
        for target in targets:
            p = Path(target)
            if p.is_file() and p.suffix == ".md":
                total += ingest_file(mem, p)
            elif p.is_dir():
                total += ingest_directory(mem, p)
            else:
                print(f"[SKIP] Not a .md file or directory: {target}")
    else:
        # Default: scan all configured directories
        for d in DEFAULT_DIRS:
            total += ingest_directory(mem, d)
    
    print(f"\n{'='*40}")
    print(f"[COMPLETE] {total} total chunks ingested.")
    print(f"[QDRANT] Total memories: {mem.count()}")


if __name__ == "__main__":
    main()
