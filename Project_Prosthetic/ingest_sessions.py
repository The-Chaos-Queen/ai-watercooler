"""
ingest_sessions.py — The Exocortex Ingestion Engine (v2)
Reads markdown files, classifies them, chunks them, embeds locally, stores in Qdrant.

Key improvement over v1: Proper metadata tagging for multi-source content.
Supports: novels, chat sessions, memory files, character cards, codex entries.

Usage:
    python ingest_sessions.py                              # Ingest all configured sources
    python ingest_sessions.py path/to/file.md              # Ingest a single file
    python ingest_sessions.py path/to/folder/              # Ingest all .md files in a folder
    python ingest_sessions.py --wipe                       # Wipe Qdrant and re-ingest everything
    python ingest_sessions.py --wipe-only                  # Wipe Qdrant without re-ingesting
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
from memory_engine import MemoryEngine

# === Source Registry ===
# Each source maps a directory to its default metadata.
# source_type: novel_canon | creative_spinoff | chat_history | session_log | memory | codex | character_card
# book: main_epic | mm_spinoff | mf_spinoff | exocortex | None

WRITING_ROOT = Path(r"C:\Users\cerub\OneDrive\Dokumente\Writing")
LLM_ROOT = Path(r"C:\Users\cerub\OneDrive\Dokumente\LLM")
ANTIGRAVITY_BRAIN = Path(r"C:\Users\cerub\.gemini\antigravity\brain")

SOURCE_REGISTRY = [
    # --- Novels (Writing directory) ---
    {
        "path": WRITING_ROOT / "Original_Fiction_Canon",
        "source_type": "novel_canon",
        "book": "main_epic",
        "recursive": False,
        "extensions": [".md", ".txt"],
    },
    {
        "path": WRITING_ROOT / "MM_Version",
        "source_type": "novel_canon",
        "book": "mm_spinoff",
        "recursive": False,
        "extensions": [".md"],
        "skip_patterns": ["fanfiction_draft", "00_kimi_chat"],  # Chat logs, not canon
    },
    {
        "path": WRITING_ROOT / "MF_Version",
        "source_type": "novel_canon",
        "book": "mf_spinoff",
        "recursive": False,
        "extensions": [".md"],
    },
    # Root-level writing files (various drafts)
    {
        "path": WRITING_ROOT,
        "source_type": "novel_canon",
        "book": "main_epic",
        "recursive": False,
        "extensions": [".md"],
        "skip_patterns": ["20251227"],  # Date-named files are usually chat dumps
    },
    # --- Exocortex Memory ---
    {
        "path": LLM_ROOT / "CHEESE_Memory",
        "source_type": "memory",
        "book": None,
        "recursive": True,
        "extensions": [".md"],
        "skip_patterns": ["00_DASHBOARD", "dashboard_", "00_HANDOFF"],
    },
    # --- Claude Sessions ---
    {
        "path": LLM_ROOT / "Claude_15_01_2026",
        "source_type": "chat_history",
        "book": None,
        "recursive": False,
        "extensions": [".md"],
    },
]

# MM_Version files that are chat-derived creative content (not pure canon)
MM_CHAT_DERIVED = {"fanfiction_draft", "00_andrej_rimmon_Claude", "00_kimi_chat_2026-01-18T21-36-49"}

# MM_Version files that are reference/meta (character cards, summaries)
MM_REFERENCE = {"00_chapter_summaries", "00_character_cards"}

# Chapter number extraction pattern
CHAPTER_NUM_RE = re.compile(r'^(\d+)[_\-]')


def classify_file(filepath: Path, registry_entry: dict) -> dict:
    """
    Classify a file and return its full metadata dict.
    Uses the registry entry as defaults, then refines based on filename patterns.
    """
    meta = {
        "source_type": registry_entry["source_type"],
        "book": registry_entry.get("book"),
        "source": filepath.name,
        "source_path": str(filepath),
        "file_date": datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d"),
    }
    
    stem = filepath.stem
    
    # Special handling for MM_Version files
    if registry_entry.get("book") == "mm_spinoff":
        if stem in MM_CHAT_DERIVED:
            meta["source_type"] = "chat_history"
        elif stem in MM_REFERENCE:
            meta["source_type"] = "codex"
        
        # Extract chapter number from filename (e.g., "5_Guilt.md" -> chapter 5)
        ch_match = CHAPTER_NUM_RE.match(stem)
        if ch_match:
            meta["chapter"] = int(ch_match.group(1))
            meta["chapter_name"] = stem[ch_match.end():].replace("_", " ").strip()
    
    # MF_Version special handling
    elif registry_entry.get("book") == "mf_spinoff":
        if stem.startswith("00_"):
            meta["source_type"] = "codex"
    
    # CHEESE_Memory special handling
    elif registry_entry.get("source_type") == "memory":
        if "session_logs" in str(filepath):
            meta["source_type"] = "session_log"
        elif stem == "laura":
            meta["source_type"] = "codex"
        elif stem == "00_CHEESE_PRIME":
            meta["source_type"] = "codex"
        elif "exocortex" in str(filepath):
            meta["source_type"] = "codex"
    
    return meta


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


def ingest_file(mem: MemoryEngine, filepath: Path, file_meta: dict) -> int:
    """Ingest a single file with pre-classified metadata. Returns number of chunks stored."""
    print(f"\n[INGEST] {filepath.name}  [{file_meta['source_type']}|{file_meta.get('book', '-')}]")
    
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
    
    # Use larger chunks for novel content (preserves narrative flow)
    max_chunk = 800 if file_meta["source_type"] in ("novel_canon", "creative_spinoff") else 500
    
    chunks = chunk_markdown(content, filepath.stem, max_chunk_size=max_chunk)
    
    if not chunks:
        print(f"  [SKIP] No meaningful chunks found")
        return 0
    
    stored = 0
    for i, chunk in enumerate(chunks):
        metadata = {
            **file_meta,
            "section": chunk.get("header", ""),
            "chunk_index": i,
        }
        mem.store(content=chunk["content"], metadata=metadata)
        stored += 1
    
    print(f"  [DONE] {stored} chunks stored")
    return stored


def ingest_directory(mem: MemoryEngine, registry_entry: dict) -> int:
    """Ingest all matching files from a registry entry. Returns total chunks stored."""
    dirpath = registry_entry["path"]
    
    if not dirpath.exists():
        print(f"[WARN] Directory not found: {dirpath}")
        return 0
    
    extensions = registry_entry.get("extensions", [".md"])
    skip_patterns = registry_entry.get("skip_patterns", [])
    recursive = registry_entry.get("recursive", False)
    
    # Collect files
    all_files = []
    for ext in extensions:
        if recursive:
            all_files.extend(dirpath.rglob(f"*{ext}"))
        else:
            all_files.extend(dirpath.glob(f"*{ext}"))
    
    all_files = sorted(set(all_files))
    
    # Filter out skipped files
    all_files = [
        f for f in all_files
        if not any(skip in f.stem for skip in skip_patterns)
    ]
    
    print(f"\n{'='*60}")
    print(f"[SOURCE] {dirpath}")
    print(f"  Type: {registry_entry['source_type']} | Book: {registry_entry.get('book', '-')}")
    print(f"  Files found: {len(all_files)}")
    
    total = 0
    for f in all_files:
        file_meta = classify_file(f, registry_entry)
        total += ingest_file(mem, f, file_meta)
    
    return total


def wipe_collection(mem: MemoryEngine):
    """Delete and recreate the Qdrant collection."""
    from qdrant_client.models import Distance, VectorParams
    
    collection = "exocortex"
    print(f"\n[WIPE] Deleting collection '{collection}'...")
    try:
        mem.client.delete_collection(collection)
        print(f"[WIPE] Collection deleted.")
    except Exception as e:
        print(f"[WIPE] Collection didn't exist or error: {e}")
    
    mem.client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(
            size=384,  # all-MiniLM-L6-v2
            distance=Distance.COSINE,
        ),
    )
    print(f"[WIPE] Fresh collection '{collection}' created.")


def main():
    print("=== EXOCORTEX INGESTION ENGINE v2 ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    args = sys.argv[1:]
    
    # Handle --wipe-only
    if "--wipe-only" in args:
        mem = MemoryEngine()
        wipe_collection(mem)
        print("\n[DONE] Collection wiped. No ingestion performed.")
        return
    
    # Handle --wipe
    do_wipe = "--wipe" in args
    args = [a for a in args if not a.startswith("--")]
    
    mem = MemoryEngine()
    
    if do_wipe:
        wipe_collection(mem)
    
    total = 0
    
    if args:
        # Manual targets
        for target in args:
            p = Path(target)
            if p.is_file() and p.suffix in (".md", ".txt"):
                file_meta = {
                    "source_type": "unknown",
                    "book": None,
                    "source": p.name,
                    "source_path": str(p),
                    "file_date": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d"),
                }
                total += ingest_file(mem, p, file_meta)
            elif p.is_dir():
                # Create a minimal registry entry for ad-hoc directories
                entry = {
                    "path": p,
                    "source_type": "unknown",
                    "book": None,
                    "recursive": False,
                    "extensions": [".md"],
                }
                total += ingest_directory(mem, entry)
            else:
                print(f"[SKIP] Not a .md/.txt file or directory: {target}")
    else:
        # Full ingest from registry
        print(f"[REGISTRY] {len(SOURCE_REGISTRY)} sources configured.\n")
        for entry in SOURCE_REGISTRY:
            total += ingest_directory(mem, entry)
    
    print(f"\n{'='*60}")
    print(f"[COMPLETE] {total} total chunks ingested.")
    print(f"[QDRANT] Total memories: {mem.count()}")
    
    # Summary by type
    print(f"\n[SOURCES PROCESSED]")
    for entry in SOURCE_REGISTRY:
        status = "[OK]" if entry["path"].exists() else "[MISSING]"
        print(f"  {status} {entry['path'].name}/ [{entry['source_type']}|{entry.get('book', '-')}]")


if __name__ == "__main__":
    main()
