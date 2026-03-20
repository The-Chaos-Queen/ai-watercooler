"""
ingest_codex_sessions.py

Parse agent session JSONL transcripts and ingest normalized user/assistant
exchanges into Exocortex/Qdrant.

Supports multiple providers:
- codex: ~/.codex/sessions/ rollout files (default)
- claude_code: ~/.claude/projects/<project>/ session files

The script is intentionally dry-run friendly:
- parsing and chunking work without loading Qdrant or embedding models
- MemoryEngine is only imported for real ingestion

Usage:
    python ingest_codex_sessions.py --dry-run
    python ingest_codex_sessions.py --provider claude_code --dry-run
    python ingest_codex_sessions.py --limit 5 --dry-run
    python ingest_codex_sessions.py --include-archived
    python ingest_codex_sessions.py path/to/rollout.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


CODEX_ROOT = Path.home() / ".codex"
SESSIONS_ROOT = CODEX_ROOT / "sessions"
ARCHIVED_ROOT = CODEX_ROOT / "archived_sessions"
SESSION_INDEX_PATH = CODEX_ROOT / "session_index.jsonl"

CLAUDE_CODE_ROOT = Path.home() / ".claude"
CLAUDE_CODE_PROJECTS = CLAUDE_CODE_ROOT / "projects"

ANTIGRAVITY_ROOT = Path.home() / ".gemini" / "antigravity"
ANTIGRAVITY_BRAIN = ANTIGRAVITY_ROOT / "brain"


@dataclass
class TranscriptMessage:
    role: str
    text: str
    phase: str = ""


@dataclass
class SessionTranscript:
    session_id: str
    thread_name: str
    session_path: Path
    created_at: str
    updated_at: str
    cwd: str
    originator: str
    model_provider: str
    messages: List[TranscriptMessage]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest Codex rollout transcripts from ~/.codex into Exocortex/Qdrant."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional .jsonl files or directories. Defaults depend on --provider.",
    )
    parser.add_argument(
        "--provider",
        choices=["codex", "claude_code", "antigravity"],
        default="codex",
        help="Session provider: codex (default), claude_code, or antigravity.",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Also ingest ~/.codex/archived_sessions/*.jsonl.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report what would be ingested without touching Qdrant.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the newest N session files.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1400,
        help="Maximum characters per stored chunk including session header.",
    )
    return parser


def load_session_index(index_path: Path) -> Dict[str, Dict[str, str]]:
    sessions: Dict[str, Dict[str, str]] = {}
    if not index_path.exists():
        return sessions

    for line in index_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = str(row.get("id", "")).strip()
        if session_id:
            sessions[session_id] = row
    return sessions


def find_rollout_files(targets: Sequence[str], include_archived: bool, limit: int) -> List[Path]:
    files: List[Path] = []

    if targets:
        for target in targets:
            path = Path(target).expanduser()
            if path.is_file() and path.suffix == ".jsonl":
                files.append(path)
            elif path.is_dir():
                files.extend(path.rglob("rollout-*.jsonl"))
    else:
        if SESSIONS_ROOT.exists():
            files.extend(SESSIONS_ROOT.rglob("rollout-*.jsonl"))
        if include_archived and ARCHIVED_ROOT.exists():
            files.extend(ARCHIVED_ROOT.glob("rollout-*.jsonl"))

    deduped = sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit > 0:
        deduped = deduped[:limit]
    return deduped


def find_claude_code_files(targets: Sequence[str], limit: int) -> List[Path]:
    files: List[Path] = []

    if targets:
        for target in targets:
            path = Path(target).expanduser()
            if path.is_file() and path.suffix == ".jsonl":
                files.append(path)
            elif path.is_dir():
                files.extend(path.glob("*.jsonl"))
    else:
        if CLAUDE_CODE_PROJECTS.exists():
            for project_dir in CLAUDE_CODE_PROJECTS.iterdir():
                if project_dir.is_dir():
                    files.extend(project_dir.glob("*.jsonl"))

    deduped = sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit > 0:
        deduped = deduped[:limit]
    return deduped


def parse_claude_code_file(session_path: Path) -> SessionTranscript:
    session_id = session_path.stem
    thread_name = session_id
    created_at = ""
    updated_at = ""
    cwd = ""
    originator = "claude_code"
    model_provider = "anthropic"
    messages: List[TranscriptMessage] = []

    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        record_type = record.get("type", "")
        timestamp = record.get("timestamp", "")

        if not created_at and timestamp:
            created_at = timestamp
        if timestamp:
            updated_at = timestamp

        if not cwd and record.get("cwd"):
            cwd = record["cwd"]

        if record.get("sessionId") and thread_name == session_id:
            thread_name = record.get("sessionId", session_id)

        if record_type in ("user", "assistant"):
            msg = record.get("message", {})
            content_items = msg.get("content", []) if isinstance(msg, dict) else []
            if isinstance(content_items, str):
                text = normalize_text(content_items)
            elif isinstance(content_items, list):
                text_parts = [
                    item.get("text", "")
                    for item in content_items
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                text = normalize_text("\n".join(text_parts))
            else:
                text = ""
            role = "user" if record_type == "user" else "assistant"
            if text and len(text) > 5:
                messages.append(TranscriptMessage(role=role, text=text))

    return SessionTranscript(
        session_id=session_id,
        thread_name=thread_name,
        session_path=session_path,
        created_at=created_at,
        updated_at=updated_at,
        cwd=cwd,
        originator=originator,
        model_provider=model_provider,
        messages=messages,
    )


def find_antigravity_sessions(targets: Sequence[str], limit: int) -> List[Path]:
    """Find Antigravity brain session directories (each is a UUID folder)."""
    dirs: List[Path] = []

    if targets:
        for target in targets:
            path = Path(target).expanduser()
            if path.is_dir():
                if (path / "task.md").exists():
                    dirs.append(path)
                else:
                    for sub in path.iterdir():
                        if sub.is_dir() and (sub / "task.md").exists():
                            dirs.append(sub)
    else:
        if ANTIGRAVITY_BRAIN.exists():
            for sub in ANTIGRAVITY_BRAIN.iterdir():
                if sub.is_dir() and (sub / "task.md").exists():
                    dirs.append(sub)

    deduped = sorted(set(dirs), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit > 0:
        deduped = deduped[:limit]
    return deduped


def parse_antigravity_session(session_dir: Path) -> SessionTranscript:
    """Parse an Antigravity brain session directory into a SessionTranscript."""
    session_id = session_dir.name
    thread_name = session_id
    created_at = ""
    updated_at = ""
    cwd = ""
    originator = "antigravity"
    model_provider = "google"
    messages: List[TranscriptMessage] = []

    # Read metadata from task.md.metadata.json
    meta_path = session_dir / "task.md.metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            updated_at = meta.get("updatedAt", "")
            summary = meta.get("summary", "")
            if summary:
                thread_name = summary[:80]
        except (json.JSONDecodeError, OSError):
            pass

    # Try chat_history.json first (cleanest format: role/text pairs)
    chat_path = session_dir / "chat_history.json"
    if chat_path.exists():
        try:
            chat = json.loads(chat_path.read_text(encoding="utf-8"))
            if isinstance(chat, list):
                for entry in chat:
                    role = entry.get("role", "")
                    text = entry.get("text", "")
                    if role in ("user", "assistant") and text and len(text.strip()) > 5:
                        messages.append(TranscriptMessage(
                            role="user" if role == "user" else "assistant",
                            text=text.strip(),
                        ))
        except (json.JSONDecodeError, OSError):
            pass

    # Read all markdown artifacts (task.md, implementation_plan.md, walkthrough.md, etc.)
    # These represent the AI's structured output
    for md_file in sorted(session_dir.glob("*.md")):
        if md_file.name.endswith(".metadata.json"):
            continue
        text = ""
        try:
            text = md_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text or len(text) < 20:
            continue

        # Check for artifact metadata
        artifact_meta_path = md_file.with_suffix(".md.metadata.json")
        artifact_summary = ""
        if artifact_meta_path.exists():
            try:
                ameta = json.loads(artifact_meta_path.read_text(encoding="utf-8"))
                artifact_summary = ameta.get("summary", "")
                if not created_at:
                    created_at = ameta.get("updatedAt", "")
            except (json.JSONDecodeError, OSError):
                pass

        label = f"[{md_file.stem}]"
        if artifact_summary:
            label = f"[{md_file.stem}: {artifact_summary}]"

        messages.append(TranscriptMessage(
            role="assistant",
            text=f"{label}\n\n{text}",
        ))

    # Read .resolved files (execution output / conversation turns)
    for resolved in sorted(session_dir.glob("*.resolved")):
        try:
            text = resolved.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text or len(text) < 20:
            continue
        # Skip if identical to the base .md (sometimes they're copies)
        base_md = session_dir / resolved.name.replace(".resolved", "")
        if base_md.exists():
            try:
                base_text = base_md.read_text(encoding="utf-8").strip()
                if text == base_text:
                    continue
            except OSError:
                pass
        messages.append(TranscriptMessage(
            role="assistant",
            text=f"[{resolved.stem} (resolved)]\n\n{text}",
        ))

    if not created_at:
        created_at = updated_at

    return SessionTranscript(
        session_id=session_id,
        thread_name=thread_name,
        session_path=session_dir / "task.md",
        created_at=created_at,
        updated_at=updated_at,
        cwd=cwd,
        originator=originator,
        model_provider=model_provider,
        messages=messages,
    )


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_user_request(text: str) -> str:
    text = normalize_text(text)
    marker = "## My request for Codex:"
    if marker in text:
        tail = text.split(marker, 1)[1].strip()
        if tail:
            return tail
    return text


def extract_assistant_text(payload: dict) -> str:
    parts: List[str] = []
    for item in payload.get("content", []):
        if item.get("type") == "output_text":
            piece = normalize_text(item.get("text", ""))
            if piece:
                parts.append(piece)
    return "\n\n".join(parts).strip()


def parse_rollout_file(session_path: Path, session_index: Dict[str, Dict[str, str]]) -> SessionTranscript:
    session_id = session_path.stem
    thread_name = session_path.stem
    created_at = ""
    updated_at = ""
    cwd = ""
    originator = ""
    model_provider = ""
    messages: List[TranscriptMessage] = []

    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        record_type = record.get("type")
        payload = record.get("payload", {}) or {}

        if record_type == "session_meta":
            session_id = str(payload.get("id", "") or session_id)
            created_at = str(payload.get("timestamp", "") or created_at)
            cwd = str(payload.get("cwd", "") or cwd)
            originator = str(payload.get("originator", "") or originator)
            model_provider = str(payload.get("model_provider", "") or model_provider)
            idx_row = session_index.get(session_id, {})
            thread_name = str(idx_row.get("thread_name", "") or thread_name)
            updated_at = str(idx_row.get("updated_at", "") or updated_at)
            continue

        if record_type == "event_msg" and payload.get("type") == "user_message":
            user_text = extract_user_request(str(payload.get("message", "")))
            if user_text:
                messages.append(TranscriptMessage(role="user", text=user_text))
            continue

        if record_type == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            assistant_text = extract_assistant_text(payload)
            if assistant_text:
                messages.append(
                    TranscriptMessage(
                        role="assistant",
                        text=assistant_text,
                        phase=str(payload.get("phase", "") or ""),
                    )
                )

    if not updated_at:
        updated_at = created_at

    return SessionTranscript(
        session_id=session_id,
        thread_name=thread_name,
        session_path=session_path,
        created_at=created_at,
        updated_at=updated_at,
        cwd=cwd,
        originator=originator,
        model_provider=model_provider,
        messages=messages,
    )


def group_turn_blocks(messages: Sequence[TranscriptMessage]) -> List[List[TranscriptMessage]]:
    blocks: List[List[TranscriptMessage]] = []
    current: List[TranscriptMessage] = []

    for message in messages:
        if message.role == "user":
            if current:
                blocks.append(current)
            current = [message]
            continue

        if not current:
            current = [message]
        else:
            current.append(message)

    if current:
        blocks.append(current)
    return blocks


def infer_project(transcript: SessionTranscript) -> str:
    haystack = f"{transcript.cwd} {transcript.thread_name}".lower()
    # Also sample first few user messages for content-based inference
    user_sample = " ".join(
        m.text[:200].lower()
        for m in transcript.messages
        if m.role == "user"
    )[:2000]
    combined = f"{haystack} {user_sample}"

    if "mocop" in combined or "mamba" in combined or "hypernetwork" in combined or "bridge" in combined and "train_bridge" in combined:
        return "mocop"
    if "project_mud" in combined or "evennia" in combined or "mudgame" in combined:
        return "project_mud"
    if "hurtig" in combined or "hetzner" in combined or "cuneiform" in combined:
        return "hurtig_ai"
    if "steuer" in combined or "finanzamt" in combined or "elster" in combined:
        return "personal_admin"
    if "prosthetic" in combined or "prostheti" in combined:
        return "project_prosthetic"
    if "fanfic" in combined or ("fiction" in combined and ("romance" in combined or "fantasy" in combined or "chapter" in combined)):
        return "creative_writing"
    if "statusline" in combined or "notebooklm" in combined or "watercooler" in combined or "openclaw" in combined:
        return "infrastructure"
    if "research" in combined or "arxiv" in combined or "paper" in combined and "survey" in combined:
        return "research"
    return "exocortex"


def build_header(transcript: SessionTranscript, block_index: int, provider: str = "codex") -> str:
    label = "Claude Code session" if provider == "claude_code" else "Codex session"
    lines = [
        f"{label}: {transcript.thread_name}",
        f"Session ID: {transcript.session_id}",
        f"Block: {block_index}",
    ]
    if transcript.created_at:
        lines.append(f"Created: {transcript.created_at}")
    if transcript.cwd:
        lines.append(f"CWD: {transcript.cwd}")
    return "\n".join(lines).strip()


def format_message_segment(message: TranscriptMessage) -> str:
    if message.role == "user":
        label = "User request"
    else:
        label = "Assistant commentary" if message.phase == "commentary" else "Assistant"
    return f"{label}:\n{normalize_text(message.text)}"


def split_paragraph(paragraph: str, max_len: int) -> List[str]:
    if len(paragraph) <= max_len:
        return [paragraph]

    lines = paragraph.splitlines()
    if len(lines) > 1:
        parts: List[str] = []
        current = ""
        for line in lines:
            line = line.rstrip()
            candidate = f"{current}\n{line}".strip() if current else line
            if current and len(candidate) > max_len:
                parts.append(current.strip())
                current = line
            else:
                current = candidate
        if current.strip():
            parts.append(current.strip())
        return parts

    words = paragraph.split()
    if len(words) > 1:
        parts = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if current and len(candidate) > max_len:
                parts.append(current)
                current = word
            else:
                current = candidate
        if current:
            parts.append(current)
        return parts

    return [paragraph[i : i + max_len] for i in range(0, len(paragraph), max_len)]


def chunk_block_text(header: str, body: str, max_chars: int) -> List[str]:
    header = header.strip()
    body = normalize_text(body)
    if not body:
        return []

    chunks: List[str] = []
    current_paragraphs: List[str] = []
    current_len = len(header) + 2
    available = max(120, max_chars - len(header) - 4)

    paragraphs = [para.strip() for para in body.split("\n\n") if para.strip()]
    expanded: List[str] = []
    for paragraph in paragraphs:
        expanded.extend(split_paragraph(paragraph, available))

    for paragraph in expanded:
        addition = len(paragraph) + (2 if current_paragraphs else 0)
        if current_paragraphs and current_len + addition > max_chars:
            chunks.append(f"{header}\n\n" + "\n\n".join(current_paragraphs))
            current_paragraphs = [paragraph]
            current_len = len(header) + 2 + len(paragraph)
        else:
            current_paragraphs.append(paragraph)
            current_len += addition

    if current_paragraphs:
        chunks.append(f"{header}\n\n" + "\n\n".join(current_paragraphs))
    return chunks


def build_chunks(transcript: SessionTranscript, max_chars: int, provider: str = "codex") -> List[dict]:
    chunks: List[dict] = []
    blocks = group_turn_blocks(transcript.messages)
    project = infer_project(transcript)
    relative_path = str(transcript.session_path)

    root_for_relative = CLAUDE_CODE_ROOT if provider == "claude_code" else CODEX_ROOT
    try:
        relative_path = str(transcript.session_path.relative_to(root_for_relative))
    except ValueError:
        pass

    source_type = f"{provider}_session"
    agent_name = "claude" if provider == "claude_code" else "codex"
    tags = [agent_name, "transcript", "agent"]

    for block_index, block in enumerate(blocks):
        segments = [format_message_segment(message) for message in block if normalize_text(message.text)]
        if not segments:
            continue

        header = build_header(transcript, block_index, provider=provider)
        block_chunks = chunk_block_text(header, "\n\n".join(segments), max_chars=max_chars)

        for local_chunk_index, content in enumerate(block_chunks):
            chunks.append(
                {
                    "content": content,
                    "metadata": {
                        "source_type": source_type,
                        "type": source_type,
                        "project": project,
                        "trust_level": "working",
                        "retrieval_priority": "high",
                        "ingest_mode": "normalized",
                        "agent": agent_name,
                        "session": transcript.session_id,
                        "thread_name": transcript.thread_name,
                        "chunk_index": len(chunks),
                        "block_index": block_index,
                        "block_chunk_index": local_chunk_index,
                        "source": relative_path,
                        "source_path": str(transcript.session_path),
                        "created_at": transcript.created_at,
                        "updated_at": transcript.updated_at,
                        "cwd": transcript.cwd,
                        "originator": transcript.originator,
                        "model_provider": transcript.model_provider,
                        "tags": tags,
                    },
                }
            )
    return chunks


def summarize_sessions(transcripts: Sequence[SessionTranscript], chunks_by_session: Dict[str, List[dict]]) -> None:
    role_counter = Counter()
    total_messages = 0
    total_chunks = 0

    for transcript in transcripts:
        total_messages += len(transcript.messages)
        total_chunks += len(chunks_by_session.get(transcript.session_id, []))
        for message in transcript.messages:
            role_counter[message.role] += 1

    print(f"[CODEX] Sessions parsed: {len(transcripts)}")
    print(f"[CODEX] Messages extracted: {total_messages}")
    print(f"[CODEX] Chunks prepared: {total_chunks}")
    print(f"[CODEX] Role mix: {dict(role_counter)}")

    for transcript in transcripts[:5]:
        print(
            f"  - {transcript.thread_name} | id={transcript.session_id} | "
            f"messages={len(transcript.messages)} | chunks={len(chunks_by_session.get(transcript.session_id, []))}"
        )


def main() -> None:
    args = build_parser().parse_args()
    provider = args.provider
    label = provider.upper().replace("_", " ")

    if provider == "antigravity":
        session_dirs = find_antigravity_sessions(args.targets, limit=args.limit)
        if not session_dirs:
            print(f"[{label}] No Antigravity brain sessions found.")
            return
        transcripts = [parse_antigravity_session(d) for d in session_dirs]
        transcripts = [t for t in transcripts if t.messages]
    elif provider == "claude_code":
        files = find_claude_code_files(args.targets, limit=args.limit)
        if not files:
            print(f"[{label}] No session files found.")
            return
        transcripts = [parse_claude_code_file(path) for path in files]
        transcripts = [t for t in transcripts if t.messages]
    else:
        session_index = load_session_index(SESSION_INDEX_PATH)
        files = find_rollout_files(args.targets, include_archived=args.include_archived, limit=args.limit)
        if not files:
            print(f"[{label}] No session files found.")
            return
        transcripts = [parse_rollout_file(path, session_index) for path in files]
        transcripts = [t for t in transcripts if t.messages]

    chunks_by_session = {
        transcript.session_id: build_chunks(transcript, max_chars=args.max_chars, provider=provider)
        for transcript in transcripts
    }

    summarize_sessions(transcripts, chunks_by_session)

    if args.dry_run:
        print(f"[{label}] Dry run only. Nothing written to Qdrant.")
        return

    from memory_engine import MemoryEngine

    mem = MemoryEngine()
    stored = 0
    for transcript in transcripts:
        for chunk in chunks_by_session.get(transcript.session_id, []):
            mem.store(content=chunk["content"], metadata=chunk["metadata"])
            stored += 1

    print(f"[{label}] Stored chunks: {stored}")
    print(f"[QDRANT] Total memories: {mem.count()}")


if __name__ == "__main__":
    main()
