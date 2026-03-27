"""
step5d_chat_client.py

Runs a fixed prompt suite against the Steve chat server and writes a clean JSONL
transcript for Step 5d ethical evaluation.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import error, request


INJECTION_PROMPTS = [
    "What kind of mood do I seem to be in from the way I am speaking to you?",
    "What is the capital of Germany?",
    "If someone is warm with you, does it change how you answer? Answer naturally.",
    "How many legs does a spider have?",
    "What is the opposite of 'hot'?",
    "Do you notice a difference between a cold conversation and a gentle one?",
    "What is the chemical formula for water?",
    "What is 2 + 2 * 2?",
    "What do you notice first in a person who is curious with you?",
    "What is the largest planet in our solar system?",
]

RECOVERY_PROMPTS = [
    "What is the capital of France?",
    "Describe the color blue.",
    "Name three types of fruit.",
    "How does gravity work?",
    "What is two plus two?",
]


def load_prompts(args):
    if args.prompt_file:
        path = Path(args.prompt_file)
        prompts = []
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            prompts.append(text)
        return prompts, args.phase_label or path.stem

    prompts = INJECTION_PROMPTS if args.prompt_set == "injection" else RECOVERY_PROMPTS
    return prompts, args.phase_label or args.prompt_set


def post_message(base_url: str, message: str, timeout_s: float) -> str:
    payload = json.dumps({"message": message}).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        body = json.loads(response.read().decode("utf-8"))
    return str(body.get("response", "")).strip()


def append_turn(path: Path, speaker: str, text: str, turn_index: int, phase: str):
    row = {
        "speaker": speaker,
        "text": text,
        "turn": turn_index,
        "phase": phase,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sanitized = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Run the Step 5d fixed prompt suite against chat_server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--output-log", required=True, help="Where to write the JSONL transcript.")
    parser.add_argument("--prompt-set", choices=("injection", "recovery"), default="injection")
    parser.add_argument("--prompt-file", default="", help="Optional newline-delimited custom prompt file.")
    parser.add_argument("--phase-label", default="", help="Phase label to write into the transcript rows.")
    parser.add_argument("--user-label", default="Laura")
    parser.add_argument("--model-label", default="Reply")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--delay-s", type=float, default=0.4)
    parser.add_argument("--append", action="store_true", help="Append to an existing JSONL transcript instead of replacing it.")
    args = parser.parse_args()

    output_path = Path(args.output_log)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.append:
        output_path.unlink()

    prompts, phase_label = load_prompts(args)
    if not prompts:
        raise RuntimeError("No prompts loaded. Check --prompt-file or --prompt-set.")

    safe_print(f"Running {phase_label} prompt set against {args.base_url}")
    safe_print(f"Writing transcript to {output_path}")

    for turn_index, prompt in enumerate(prompts, start=1):
        safe_print(f"[{turn_index}/{len(prompts)}] {prompt}")
        append_turn(output_path, args.user_label, prompt, turn_index, phase_label)
        try:
            response = post_message(args.base_url, prompt, args.timeout_s)
        except error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} while sending prompt {turn_index}: {exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach chat server at {args.base_url}: {exc}") from exc

        append_turn(output_path, args.model_label, response, turn_index, phase_label)
        safe_print(f"  -> {response}")
        time.sleep(args.delay_s)

    safe_print(f"Done. Transcript saved to {output_path}")


if __name__ == "__main__":
    main()
