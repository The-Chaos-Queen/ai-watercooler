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
# source_type: novel_canon | creative_spinoff | chat_history | session_log | memory | codex | codex_session | character_card | research
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
    # --- Research / Architecture Docs ---
    {
        "path": LLM_ROOT / "Research",
        "source_type": "research",
        "book": None,
        "recursive": True,
        "extensions": [".md"],
    },
    {
        "path": LLM_ROOT / "MoCoP",
        "source_type": "research",
        "book": None,
        "recursive": True,
        "extensions": [".md"],
    },
    # --- Claude Sessions ---
    {
        "path": LLM_ROOT / "Claude_15_01_2026",
        "source_type": "chat_history",
        "book": None,
        "recursive": False,
        "extensions": [".md"],
    },
    {
        "path": LLM_ROOT / "Preserved-History",
        "source_type": "chat_history",
        "book": None,
        "recursive": True,
        "extensions": [".md", ".txt"],
    },
]

# MM_Version files that are chat-derived creative content (not pure canon)
MM_CHAT_DERIVED = {"fanfiction_draft", "00_andrej_rimmon_Claude", "00_kimi_chat_2026-01-18T21-36-49"}

# MM_Version files that are reference/meta (character cards, summaries)
MM_REFERENCE = {"00_chapter_summaries", "00_character_cards"}

# Chapter number extraction pattern
CHAPTER_NUM_RE = re.compile(r'^(\d+)[_\-]')

SOURCE_TYPE_DEFAULTS = {
    "novel_canon": {
        "trust_level": "canonical",
        "retrieval_priority": "high",
        "project": "writing",
    },
    "creative_spinoff": {
        "trust_level": "working",
        "retrieval_priority": "normal",
        "project": "writing",
    },
    "chat_history": {
        "trust_level": "ephemeral",
        "retrieval_priority": "low",
        "project": "archive",
    },
    "session_log": {
        "trust_level": "working",
        "retrieval_priority": "high",
        "project": "exocortex",
    },
    "memory": {
        "trust_level": "working",
        "retrieval_priority": "normal",
        "project": "exocortex",
    },
    "codex": {
        "trust_level": "canonical",
        "retrieval_priority": "high",
        "project": "exocortex",
    },
    "codex_session": {
        "trust_level": "working",
        "retrieval_priority": "high",
        "project": "exocortex",
    },
    "character_card": {
        "trust_level": "working",
        "retrieval_priority": "normal",
        "project": "writing",
    },
    "research": {
        "trust_level": "working",
        "retrieval_priority": "normal",
        "project": "research",
    },
    "unknown": {
        "trust_level": "working",
        "retrieval_priority": "normal",
        "project": "unknown",
    },
}


def _coerce_frontmatter_value(raw: str):
    raw = raw.strip()
    if not raw:
        return ""

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]

    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)

    return raw.strip("'\"")


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---\n"):
        return {}, content

    end_marker = content.find("\n---\n", 4)
    if end_marker == -1:
        return {}, content

    frontmatter_text = content[4:end_marker].strip()
    body = content[end_marker + len("\n---\n") :].lstrip()
    meta = {}

    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = _coerce_frontmatter_value(value)

    return meta, body


def _infer_project(filepath: Path) -> str:
    lowered_parts = {part.lower() for part in filepath.parts}
    if "mocop" in lowered_parts:
        return "mocop"
    if "project_mud" in lowered_parts:
        return "project_mud"
    if "project_prosthetic" in lowered_parts:
        return "project_prosthetic"
    if "research" in lowered_parts:
        return "research"
    if "cheese_memory" in lowered_parts:
        return "exocortex"
    if "writing" in lowered_parts:
        return "writing"
    return "unknown"


def _infer_fiction_book(lowered_stem: str) -> str:
    """Classify Preserved-History fiction exports into book sub-projects."""
    # M-M romance timeline (Andrej + Rimmon)
    if any(k in lowered_stem for k in ("mm_fanfic", "mm-sonnet", "mm_chapter", "mm_wardum", "mm_slavery", "rimmon_andrej", "sonnetonopus")):
        return "andrej_rimmon_mm"
    # M-F Romantasy rewrite (Aya + Claudius)
    if any(k in lowered_stem for k in ("female_protagonist", "mf_rewrite", "aya_claudius")):
        return "aya_claudius_mf"
    # Dark High Fantasy (The Blade / Andrej's transformation)
    if "blade" in lowered_stem:
        return "the_blade"
    # Canon platonic version (romantic-to-platonic rewrites)
    if "romantic-to-platonic" in lowered_stem or "also-canon" in lowered_stem:
        return "canon_platonic"
    return ""


def _infer_chat_provider(filepath: Path) -> str:
    lowered = filepath.stem.lower()
    for needle, provider in (
        ("codex", "codex"),
        ("claude", "claude"),
        ("gemini", "gemini"),
        ("grok", "grok"),
        ("kimi", "kimi"),
        ("lmarena", "lmarena"),
        ("arena", "arena"),
    ):
        if needle in lowered:
            return provider
    return ""


def _normalize_metadata(meta: dict, filepath: Path) -> dict:
    normalized = dict(meta)
    source_type = normalized.get("source_type") or normalized.get("type") or "unknown"
    defaults = SOURCE_TYPE_DEFAULTS.get(source_type, SOURCE_TYPE_DEFAULTS["unknown"])

    normalized["source_type"] = source_type
    normalized["type"] = source_type
    normalized.setdefault("project", defaults["project"])
    normalized["project"] = _infer_project(filepath) if normalized["project"] == "unknown" else normalized["project"]
    normalized.setdefault("trust_level", defaults["trust_level"])
    normalized.setdefault("retrieval_priority", defaults["retrieval_priority"])
    normalized.setdefault("ingest_mode", "curated")

    tags = normalized.get("tags")
    if isinstance(tags, str):
        normalized["tags"] = [part.strip() for part in tags.split(",") if part.strip()]

    return normalized


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
        "ingest_mode": registry_entry.get("ingest_mode", "curated"),
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
    elif "preserved-history" in str(filepath).lower():
        provider = _infer_chat_provider(filepath)
        tags = ["preserved-history", "chat-export"]
        if provider:
            meta["provider"] = provider
            tags.append(provider)
            if provider == "codex":
                meta["source_type"] = "codex_session"

        # Fiction sub-project tagging for Preserved-History exports
        lowered_stem = filepath.stem.lower()
        fiction_book = _infer_fiction_book(lowered_stem)
        if fiction_book:
            meta["project"] = "creative_writing"
            meta["book"] = fiction_book
            tags.append("fiction")
            tags.append(fiction_book)

        meta["tags"] = sorted(set(tags))

    return meta


def find_registry_entry_for_path(filepath: Path) -> dict | None:
    target = filepath.resolve()
    for entry in SOURCE_REGISTRY:
        base = entry["path"].resolve()
        if target == base or base in target.parents:
            return entry
    return None


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

    frontmatter_meta, content = _parse_frontmatter(content)
    file_meta = _normalize_metadata(
        {
            **file_meta,
            **frontmatter_meta,
            "source": filepath.name,
            "source_path": str(filepath),
        },
        filepath=filepath,
    )
    
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
                registry_entry = find_registry_entry_for_path(p)
                if registry_entry:
                    file_meta = classify_file(p, registry_entry)
                else:
                    file_meta = {
                        "source_type": "unknown",
                        "book": None,
                        "source": p.name,
                        "source_path": str(p),
                        "file_date": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d"),
                        "ingest_mode": "ad_hoc",
                    }
                total += ingest_file(mem, p, file_meta)
            elif p.is_dir():
                registry_entry = find_registry_entry_for_path(p)
                if registry_entry and p.resolve() == registry_entry["path"].resolve():
                    entry = registry_entry
                else:
                    # Create a minimal registry entry for ad-hoc directories
                    entry = {
                        "path": p,
                        "source_type": "unknown",
                        "book": None,
                        "recursive": False,
                        "extensions": [".md"],
                        "ingest_mode": "ad_hoc",
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
