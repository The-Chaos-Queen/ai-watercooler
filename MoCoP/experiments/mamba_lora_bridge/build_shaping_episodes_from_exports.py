import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from json import JSONDecodeError


DEFAULT_SPECS = [
    ("Kimi Roleplay Rimmon", "roleplay", "Preserved-History/KIMI_RIMMON_ROLEPLAY.md", 10),
    ("Kimi Editorial Work", "editorial", "Preserved-History/Kimi_Fiction_Editorial_work.md", 8),
    (
        "Kimi Collaborative Karzem",
        "collaborative_creative",
        "Preserved-History/Kimi_Fiction_Andrej_Rimmon_Karzem_Spinoff.md",
        8,
    ),
]

SUSPICIOUS_MOJIBAKE_TOKENS = ("â", "Ã", "ðŸ", "ï¸", "Â")
MOJIBAKE_RECOVERY_MARKERS = ("—", "–", "’", "“", "”", "…", "🐺", "😂", "💙", "🔥", "ü", "ä", "ö", "ß", "→")


@dataclass
class EpisodeSpec:
    title: str
    disposition: str
    source_path: Path
    start_turn: int
    turns: int


def parse_spec(raw: str) -> EpisodeSpec:
    parts = raw.split("|")
    if len(parts) not in {4, 5}:
        raise argparse.ArgumentTypeError(
            "Spec must be title|disposition|path|turn_count or "
            "title|disposition|path|start_turn|turn_count"
        )
    if len(parts) == 4:
        title, disposition, path_text, turns_text = [part.strip() for part in parts]
        start_turn = 0
    else:
        title, disposition, path_text, start_turn_text, turns_text = [part.strip() for part in parts]
        start_turn = int(start_turn_text)
    return EpisodeSpec(
        title=title,
        disposition=disposition,
        source_path=Path(path_text),
        start_turn=start_turn,
        turns=int(turns_text),
    )


def parse_conversation(filepath: Path) -> list[dict]:
    suffix = filepath.suffix.lower()
    if suffix == ".jsonl":
        return parse_claude_jsonl_conversation(filepath)

    text = filepath.read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    turns = []
    current_role = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_role is not None:
                turn_text = clean_turn_text("\n".join(current_lines))
                if turn_text:
                    turns.append({"role": current_role, "text": turn_text})
            current_role = stripped[3:].strip()
            current_lines = []
            continue
        if stripped == "---" or (stripped.startswith("# ") and not stripped.startswith("## ")):
            continue
        if current_role is not None:
            current_lines.append(line)

    if current_role is not None:
        turn_text = clean_turn_text("\n".join(current_lines))
        if turn_text:
            turns.append({"role": current_role, "text": turn_text})

    return turns


def parse_claude_jsonl_conversation(filepath: Path) -> list[dict]:
    turns = []
    with filepath.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except JSONDecodeError:
                continue
            entry_type = str(entry.get("type", "")).strip().lower()

            if entry_type == "user":
                text = clean_turn_text(str(entry.get("message", {}).get("content", "")))
                if text.startswith("<local-command") or text.startswith("<command-name>"):
                    continue
                if text:
                    turns.append({"role": "User", "text": text})
                continue

            if entry_type == "assistant":
                content = entry.get("message", {}).get("content", [])
                parts: list[str] = []
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            item_text = str(item.get("text", "")).strip()
                            if item_text:
                                parts.append(item_text)
                elif isinstance(content, str):
                    if content.strip():
                        parts.append(content.strip())
                text = clean_turn_text("\n".join(parts))
                if text:
                    turns.append({"role": "Assistant", "text": text})
                continue

    return turns


def clean_turn_text(text: str) -> str:
    text = repair_mojibake(text)
    cleaned = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if stripped in {"Edit", "Copy", "Share"}:
            continue
        if stripped.startswith(">"):
            continue
        cleaned.append(line.rstrip())

    joined = "\n".join(cleaned)
    while "\n\n\n" in joined:
        joined = joined.replace("\n\n\n", "\n\n")
    return joined.strip()


def repair_mojibake(text: str) -> str:
    if not text or not any(token in text for token in SUSPICIOUS_MOJIBAKE_TOKENS):
        return text

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text

    original_score = sum(text.count(marker) for marker in MOJIBAKE_RECOVERY_MARKERS)
    repaired_score = sum(repaired.count(marker) for marker in MOJIBAKE_RECOVERY_MARKERS)

    if repaired_score > original_score:
        return repaired
    return text


def normalize_role(raw_role: str) -> str:
    role = raw_role.strip()
    if role.lower() == "user":
        return "User"
    return role


def build_episode_block(index: int, spec: EpisodeSpec, turns: list[dict], repo_root: Path) -> str:
    if spec.start_turn < 0:
        raise ValueError(f"start_turn must be >= 0, got {spec.start_turn} for {spec.title}")
    selected = turns[spec.start_turn : spec.start_turn + spec.turns]
    if not selected:
        raise ValueError(
            f"Episode {spec.title!r} selected no turns from {spec.source_path} "
            f"(start_turn={spec.start_turn}, turns={spec.turns}, total={len(turns)})"
        )
    transcript_lines = [
        f"{normalize_role(turn['role'])}: {turn['text'].replace(chr(10), chr(10) + '    ')}"
        for turn in selected
    ]
    rel_source = spec.source_path.as_posix()
    start_turn_note = (
        f"**Start turn:** {spec.start_turn}\n"
        if spec.start_turn
        else ""
    )
    return (
        f"## Episode {index}: {spec.title}\n"
        + f"**Disposition:** {spec.disposition}\n"
        + f"**Source:** {rel_source}\n"
        + start_turn_note
        + f"**Turns used:** {len(selected)}\n\n"
        + "[Transcript]\n"
        + "\n".join(transcript_lines)
        + "\n"
    )


def default_specs(repo_root: Path) -> list[EpisodeSpec]:
    return [
        EpisodeSpec(
            title=title,
            disposition=disposition,
            source_path=repo_root / path_text,
            start_turn=0,
            turns=turns,
        )
        for title, disposition, path_text, turns in DEFAULT_SPECS
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build CHEESE shaping episodes from preserved markdown chat exports."
    )
    parser.add_argument(
        "--output-file",
        default="KIMI_ROLEPLAY_SHAPING_EPISODES_2026-04-03.md",
        help="Relative to the bridge experiment directory unless absolute.",
    )
    parser.add_argument(
        "--spec",
        action="append",
        type=parse_spec,
        help="Episode spec: title|disposition|path|turn_count",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]

    specs = args.spec if args.spec else default_specs(repo_root)
    normalized_specs = []
    for spec in specs:
        if args.spec:
            source_path = spec.source_path
            if not source_path.is_absolute():
                source_path = repo_root / source_path
            normalized_specs.append(
                EpisodeSpec(
                    title=spec.title,
                    disposition=spec.disposition,
                    source_path=source_path,
                    start_turn=spec.start_turn,
                    turns=spec.turns,
                )
            )
        else:
            normalized_specs.append(spec)

    output_path = Path(args.output_file)
    if not output_path.is_absolute():
        output_path = script_dir / output_path

    blocks = []
    for index, spec in enumerate(normalized_specs, start=1):
        turns = parse_conversation(spec.source_path)
        if not turns:
            raise RuntimeError(f"No turns parsed from {spec.source_path}")
        blocks.append(build_episode_block(index, spec, turns, repo_root))

    header = (
        "# Kimi Roleplay / Editorial / Collaborative Shaping Episodes\n"
        f"# Generated from preserved exports on {Path(__file__).resolve().stem}\n\n"
        "---\n\n"
    )
    output_path.write_text(header + "---\n\n".join(blocks) + "---\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
