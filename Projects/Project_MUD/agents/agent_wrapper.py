"""
agent_wrapper.py — The MUD Agent Bridge
Connects an LLM to an Evennia MUD via telnet.

Architecture:
    MUD (telnet:4001) ←→ This script ←→ LMStudio/Ollama API (e.g. Qwen3:8b)
                                          

Each agent has:
  - A persona (system prompt with personality, goals, quirks)
  - A scratchpad (persistent markdown file for maps, notes, inventory)
  - A rolling context window of recent MUD interactions
  - A command extractor (LLM response → clean MUD command)

Usage:
    python agent_wrapper.py personas/thornwick.md
    python agent_wrapper.py personas/jinx.md --backend lmstudio
"""

import asyncio
import json
import sys
import time
import re
import argparse
import os
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("[ERROR] httpx not installed. Run: pip install httpx")
    sys.exit(1)


# === Configuration ===
MUD_HOST = "127.0.0.1"
MUD_PORT = 4000

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
HYPERNETWORK_URL = os.getenv("HYPERNETWORK_URL", "http://127.0.0.1:8001/generate")
LMSTUDIO_TIMEOUT = 180.0

# How long to wait between actions (seconds) — don't spam the MUD
ACTION_DELAY = 3.0
# How many recent exchanges to keep in rolling context
MAX_CONTEXT_LINES = 40
# Max scratchpad size in characters (truncate oldest entries if exceeded)
MAX_SCRATCHPAD_SIZE = 3000


class Scratchpad:
    """Persistent memory for an agent. Stored as a markdown file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(self._template(), encoding="utf-8")

    def _template(self) -> str:
        return """# Agent Scratchpad
## Map
(No rooms discovered yet)

## Inventory
(Nothing noted)

## Quest Log
(No active quests)

## People Met
(No one met yet)

## Notes
(No notes yet)
"""

    def read(self) -> str:
        content = self.filepath.read_text(encoding="utf-8")
        # Truncate if too large (keep the most recent content)
        if len(content) > MAX_SCRATCHPAD_SIZE:
            content = content[:MAX_SCRATCHPAD_SIZE] + "\n... (truncated)"
        return content

    def write(self, content: str):
        self.filepath.write_text(content, encoding="utf-8")

    def append_note(self, note: str):
        content = self.filepath.read_text(encoding="utf-8")
        content += f"\n- [{datetime.now().strftime('%H:%M')}] {note}"
        self.write(content)


class MUDAgent:
    """
    An LLM-powered agent that plays a MUD via telnet.
    
    The agent:
    1. Reads text from the MUD
    2. Sends it (with persona + scratchpad + context) to an LLM
    3. Extracts a MUD command from the LLM's response
    4. Sends the command to the MUD
    5. Optionally updates the scratchpad based on LLM's notes
    """

    def __init__(
        self,
        persona_path: Path,
        username: str,
        password: str,
        backend: str = "LMStudio",
        model: str = "qwen/qwen3-vl-8b",
        goal: str = None,
        device: str = None,
        resume_state: str = None,
        hypernetwork_url: str = HYPERNETWORK_URL,
        role_swap: bool = False,
    ):
        self.persona_path = persona_path
        self.persona = persona_path.read_text(encoding="utf-8")
        self.agent_name = persona_path.stem
        self.username = username
        self.password = password
        self.backend = backend
        self.last_command = None
        self.repetition_count = 0        
        self.last_exits = []
        self.last_movement_error = ""
        self.fail_history = [] # Track "not found" or error responses
        self.short_term_memory = [] # List of {"command": str, "outcome": str}
        self.current_room_name = ""
        self.previous_room_name = ""
        self.last_state_signature = ""
        self.state_repeat_count = 0
        self.bootstrap_state_json = None
        self.bootstrap_events = ""
        self.room_state_cache = {}  # room_name -> last seen state signature + entities
        self.model = model
        self.goal = goal
        self.hypernetwork_url = hypernetwork_url
        self.role_swap = role_swap

        # Scratchpad
        base_dir = Path(__file__).parent
        self.scratchpad = Scratchpad(
             base_dir / "scratchpads" / f"{self.agent_name}_scratchpad.md"
        )

        # Rolling context (recent MUD interactions)
        self.context_lines: list[str] = []

        # Logging
        # Use path relative to this script to avoid 'agents/agents' issues
        base_dir = Path(__file__).parent
        self.log_path = base_dir / "logs" / f"{self.agent_name}.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Connection state
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.logged_in = False

        # === Mamba Backend ===
        self.mamba = None
        if backend == "mamba":
            from mamba_backend import MambaBackend
            state_path = resume_state or (
                base_dir / "states" / f"{self.agent_name}.pt"
            )
            self.mamba = MambaBackend(
                model_name=model,
                device=device,
                state_path=str(state_path) if Path(state_path).exists() else None
            )
            # Training data output path
            self.training_data_path = (
                base_dir / "training_data"
                / f"{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )

        print(f"[{self.agent_name}] Initialized with persona from {persona_path.name}")
        print(f"[{self.agent_name}] Backend: {backend} ({model})")
        if role_swap:
            print(f"[{self.agent_name}] Role swap ENABLED: agent=user, world=assistant")
        if backend == "hypernetwork":
            print(f"[{self.agent_name}] Brain URL: {self.hypernetwork_url}")
        if self.mamba:
            print(f"[{self.agent_name}] Mamba state: {self.mamba.get_info()}")

    def log(self, message: str):
        """Log to file and stdout."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Sanitize for Windows terminal
        safe_msg = message.encode('ascii', errors='replace').decode('ascii')
        line = f"[{timestamp}] [{self.agent_name}] {safe_msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def connect(self):
        """Connect to the MUD via telnet."""
        self.log(f"Connecting to {MUD_HOST}:{MUD_PORT}...")
        self.reader, self.writer = await asyncio.open_connection(MUD_HOST, MUD_PORT)
        self.log("Connected!")

    async def read_mud(self, timeout: float = 2.0) -> str:
        """Read available text from MUD, with timeout."""
        chunks = []
        try:
            while True:
                data = await asyncio.wait_for(
                    self.reader.read(4096), timeout=timeout
                )
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                chunks.append(text)
                # Short pause to let more data arrive
                await asyncio.sleep(0.2)
        except asyncio.TimeoutError:
            pass

        full_text = "".join(chunks).strip()
        if full_text:
            # Clean ANSI escape codes
            full_text = re.sub(r'\x1b\[[0-9;]*m', '', full_text)
            full_text = re.sub(r'\x1b\[\d*[A-Za-z]', '', full_text)

        return full_text

    async def _get_json_state(self, timeout: float = 5.0) -> tuple[dict | None, str]:
        """
        Request and parse JSON state from MUD (via 'look --json').
        Returns (json_dict, remaining_text_as_events).
        """
        await self.send_mud("look --json")
        
        buffer = ""
        start_time = time.time()
        
        # Poll until we find a JSON object or timeout
        while time.time() - start_time < timeout:
            chunk = await self.read_mud(timeout=1.0)
            if chunk:
                buffer += chunk
                data, events = self._extract_json_state_from_text(buffer)
                if data is not None:
                    return data, events.strip()
            
            if not chunk and buffer:
                 # verify if buffer is valid json even if no more chunk
                 pass

        # self.log(f"DEBUG: Failed to find JSON in buffer of {len(buffer)} chars. Buffer tail: {buffer[-50:]}")
        return None, buffer

    async def send_mud(self, command: str):
        """Send a command to the MUD."""
        self.writer.write((command + "\n").encode("utf-8"))
        await self.writer.drain()
        self.log(f">>> {command}")

    async def login(self):
        """Handle the Evennia login sequence."""
        # Read the welcome screen (may contain telnet negotiation bytes)
        welcome = await self.read_mud(timeout=3.0)
        # Strip telnet negotiation bytes
        if welcome:
            welcome = re.sub(r'[\xff\xfe\xfd\xfb\xfc][\x00-\xff]', '', welcome)
            welcome = re.sub(r'[^\x20-\x7e\n\r\t]', '', welcome)
        self.log(f"Welcome screen received ({len(welcome or '')} chars)")

        # Try to connect with existing account
        await self.send_mud(f"connect {self.username} {self.password}")
        await asyncio.sleep(2.0)

        login_response = await self.read_mud(timeout=3.0)
        if login_response:
            login_response = re.sub(r'[^\x20-\x7e\n\r\t]', '', login_response)

        bootstrap_state, bootstrap_events = self._extract_json_state_from_text(login_response)
        if bootstrap_state:
            self.bootstrap_state_json = bootstrap_state
            self.bootstrap_events = self._sanitize_event_text(bootstrap_events)
            bootstrap_summary = self._summarize_state_update(bootstrap_state)
            if bootstrap_summary:
                self.log(f"Login bootstrap: {bootstrap_summary}")
        else:
            self.log(f"Login response: {login_response[:300] if login_response else '(empty)'}")

        # Detect login failure and try self-registration
        needs_create = False
        if login_response:
            lower_resp = login_response.lower()
            if "traceback" in lower_resp:
                self.log("Login hit a server error. Account is broken.")
                needs_create = True
            elif "incorrect" in lower_resp:
                self.log("Account doesn't exist. Will self-register.")
                needs_create = True
            elif any(x in lower_resp for x in ["logged in", "welcome", "limbo", "you become"]):
                self.logged_in = True
                self.log("Login successful!")
                return
        
        if needs_create or not self.logged_in:
            self.log(f"Trying to create account '{self.username}'...")
            await self.send_mud(f"create {self.username} {self.password}")
            await asyncio.sleep(3.0)
            create_response = await self.read_mud(timeout=3.0)
            if create_response:
                create_response = re.sub(r'[^\x20-\x7e\n\r\t]', '', create_response)
            self.log(f"Create response: {create_response[:300] if create_response else '(empty)'}")

            # Handle confirmation prompt "[Y]/N?"
            if create_response and ("[y]/n" in create_response.lower() or "is this what you intended" in create_response.lower()):
                self.log("Confirming account creation...")
                await self.send_mud("Y")
                await asyncio.sleep(3.0)
                confirm_response = await self.read_mud(timeout=3.0)
                if confirm_response:
                    confirm_response = re.sub(r'[^\x20-\x7e\n\r\t]', '', confirm_response)
                self.log(f"Confirm response: {confirm_response[:300] if confirm_response else '(empty)'}")

            if create_response and "traceback" not in create_response.lower():
                self.logged_in = True
                self.log("Account created and logged in!")
            else:
                self.log("Account creation may have failed. Trying to proceed anyway.")
                self.logged_in = True

    def _parse_state_payload(self, payload):
        """Parse JSON state from a dict, raw JSON string, or <JSON>-wrapped string."""
        if isinstance(payload, dict):
            return payload

        if not isinstance(payload, str):
            return None

        cleaned = payload.strip()
        if cleaned.startswith("<JSON>"):
            cleaned = cleaned.replace("<JSON>", "", 1).replace("</JSON>", "", 1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _is_room_state_payload(self, payload) -> bool:
        """Return True when a decoded payload looks like room state, not chat text."""
        if not isinstance(payload, dict):
            return False

        if payload.get("schema_version") == "mud.agent_state/v1":
            return True

        room = payload.get("room")
        location = payload.get("location")
        if isinstance(room, dict) or isinstance(location, dict):
            return True

        state_keys = {"room_name", "you_see", "entities", "exits", "suggested_actions"}
        return any(key in payload for key in state_keys)

    def _extract_json_state_from_text(self, text: str) -> tuple[dict | None, str]:
        """Extract a JSON state object from mixed text and return remaining events."""
        if not isinstance(text, str) or not text.strip():
            return None, ""

        tagged_match = re.search(r"<JSON>\s*(\{.*?\})\s*</JSON>", text, re.DOTALL)
        if tagged_match:
            payload = tagged_match.group(1)
            try:
                data = json.loads(payload)
                events = (text[:tagged_match.start()] + text[tagged_match.end():]).strip()
                return data, events
            except json.JSONDecodeError:
                pass

        direct = self._parse_state_payload(text)
        if isinstance(direct, dict):
            return direct, ""

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                data = json.loads(candidate)
                events = (text[:start_idx] + text[end_idx + 1:]).strip()
                return data, events
            except json.JSONDecodeError:
                pass

        return None, text

    def _parse_exits(self, mud_output) -> list[str]:
        """Extract available exits from either structured JSON state or plain text."""
        data = self._parse_state_payload(mud_output)
        if isinstance(data, dict):
            exits = data.get("exits")
            if exits is None:
                exits = data.get("location", {}).get("exits")

            if isinstance(exits, list):
                parsed = []
                for exit_entry in exits:
                    label = None
                    if isinstance(exit_entry, dict):
                        label = exit_entry.get("label") or exit_entry.get("name")
                        if not label:
                            command = str(exit_entry.get("command", "")).strip()
                            if command.lower().startswith(("move ", "go ", "walk ")):
                                _, label = command.split(" ", 1)
                        if not label:
                            aliases = exit_entry.get("aliases") or []
                            if aliases:
                                label = aliases[0]
                    else:
                        label = exit_entry

                    clean_label = str(label).strip().lower()
                    if clean_label and clean_label not in parsed:
                        parsed.append(clean_label)
                return parsed

        if not isinstance(mud_output, str):
            return []

        # Look for "Exits: North, South, ..."
        match = re.search(r"Exits: (.+)", mud_output, re.IGNORECASE)
        if match:
            exits_str = match.group(1)
            # Split and clean
            raw_exits = [e.strip().lower() for e in exits_str.split(',')]
            clean_exits = []
            for e in raw_exits:
                # Remove room IDs like (#123) and extra spaces
                clean = re.sub(r'\(\#\d+\)', '', e).strip()
                if clean:
                    clean_exits.append(clean)
            return clean_exits
        return []

    def _state_room_name(self, state_json: dict) -> str:
        """Get the current room name from either the new or legacy state schema."""
        if not isinstance(state_json, dict):
            return ""

        room = state_json.get("room")
        if isinstance(room, dict):
            name = room.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

        location = state_json.get("location")
        if isinstance(location, dict):
            name = location.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

        room_name = state_json.get("room_name")
        if isinstance(room_name, str):
            return room_name.strip()

        return ""

    def _state_entities(self, state_json: dict) -> list[dict]:
        """Normalize visible entities from either the new or legacy state schema."""
        if not isinstance(state_json, dict):
            return []

        entities = state_json.get("entities")
        if isinstance(entities, list):
            normalized = []
            for entity in entities:
                if isinstance(entity, dict):
                    normalized.append(entity)
            return normalized

        if isinstance(entities, dict):
            normalized = []
            for entity_type, names in entities.items():
                if not isinstance(names, list):
                    continue
                for name in names:
                    if str(name).strip():
                        normalized.append(
                            {
                                "name": str(name).strip(),
                                "type": entity_type.rstrip("s"),
                            }
                        )
            return normalized

        legacy = state_json.get("you_see")
        if isinstance(legacy, dict):
            normalized = []
            for entity_type, names in legacy.items():
                if not isinstance(names, list):
                    continue
                for name in names:
                    if str(name).strip():
                        normalized.append(
                            {
                                "name": str(name).strip(),
                                "type": entity_type.rstrip("s"),
                            }
                        )
            return normalized

        return []

    def _state_signature(self, state_json: dict) -> str:
        """Build a compact signature to detect stale repeated room states."""
        room_name = self._state_room_name(state_json).lower()
        exits = sorted(self._parse_exits(state_json))
        entities = sorted(
            str(entity.get("name", "")).strip().lower()
            for entity in self._state_entities(state_json)
            if str(entity.get("name", "")).strip()
        )
        return json.dumps(
            {"room": room_name, "exits": exits, "entities": entities},
            sort_keys=True,
        )

    def _diff_room_state(self, state_json: dict) -> dict | None:
        """Compare current room state against cache. Returns a slim diff dict if
        the room was seen before, or None if this is a first visit.

        The diff replaces verbose repeated descriptions with a compact delta:
        - which entities appeared or disappeared
        - which exits changed
        - weather or property changes

        This is the 'Dismiss' operation: if nothing changed, the model gets
        a one-line 'no changes' instead of the full room payload again.
        """
        room_name = self._state_room_name(state_json)
        if not room_name:
            return None

        current_sig = self._state_signature(state_json)
        current_entities = {
            str(e.get("name", "")).strip().lower()
            for e in self._state_entities(state_json)
            if str(e.get("name", "")).strip()
        }
        current_exits = set(self._parse_exits(state_json))

        cache_key = room_name.lower().strip()
        cached = self.room_state_cache.get(cache_key)

        # Always update cache with latest state
        self.room_state_cache[cache_key] = {
            "signature": current_sig,
            "entities": current_entities,
            "exits": current_exits,
            "visit_count": (cached["visit_count"] + 1) if cached else 1,
        }

        if cached is None:
            # First visit — no diff, use full state
            return None

        # Seen before — compute diff
        prev_entities = cached.get("entities", set())
        prev_exits = cached.get("exits", set())
        visit_count = cached["visit_count"] + 1

        appeared = current_entities - prev_entities
        disappeared = prev_entities - current_entities
        new_exits = current_exits - prev_exits
        closed_exits = prev_exits - current_exits

        changes = []
        if appeared:
            changes.append(f"New: {', '.join(sorted(appeared))}")
        if disappeared:
            changes.append(f"Gone: {', '.join(sorted(disappeared))}")
        if new_exits:
            changes.append(f"New exits: {', '.join(sorted(new_exits))}")
        if closed_exits:
            changes.append(f"Blocked exits: {', '.join(sorted(closed_exits))}")

        return {
            "room_name": room_name,
            "visit_count": visit_count,
            "changed": len(changes) > 0,
            "changes": changes if changes else ["No changes since last visit."],
        }

    def _room_is_sparse(self, state_json: dict) -> bool:
        """Return True when a room has no obvious interactions beyond movement."""
        visible_entities = self._state_entities(state_json)
        actionable = [
            entity
            for entity in visible_entities
            if entity.get("type") not in {"scenery"}
        ]
        return len(actionable) == 0

    def _extract_move_target(self, command: str) -> str:
        if not isinstance(command, str):
            return ""
        clean = command.strip()
        if not clean:
            return ""
        lower = clean.lower()
        if lower.startswith(("move ", "go ", "walk ")):
            _, target = clean.split(" ", 1)
            return target.strip()
        return clean

    def _is_movement_command(self, command: str) -> bool:
        if not isinstance(command, str):
            return False
        clean = command.strip().lower()
        basic_dirs = {"north", "south", "east", "west", "n", "s", "e", "w", "up", "down", "u", "d"}
        if clean in basic_dirs:
            return True
        return clean.startswith(("move ", "go ", "walk "))

    def _sanitize_command_sequence(self, commands: list[str]) -> list[str]:
        """Drop stale follow-up commands after movement changes the room state."""
        sanitized = []
        for command in commands:
            sanitized.append(command)
            if self._is_movement_command(command):
                if len(commands) > len(sanitized):
                    self.log(f"Guardrail: Dropped commands after movement '{command}'.")
                break
        return sanitized

    def _choose_fallback_move(self, state_json: dict) -> str | None:
        """Pick a safe movement command when the model stalls in an empty room."""
        candidates = []

        for action in state_json.get("suggested_actions", []):
            if not isinstance(action, dict):
                continue
            command = str(action.get("command", "")).strip()
            if command.lower().startswith(("move ", "go ", "walk ")):
                candidates.append(command)

        exits = state_json.get("exits", [])
        if isinstance(exits, list):
            for exit_entry in exits:
                command = ""
                if isinstance(exit_entry, dict):
                    command = str(exit_entry.get("command", "")).strip()
                    if not command:
                        label = str(exit_entry.get("label", "")).strip()
                        if label:
                            command = f"move {label}"
                else:
                    label = str(exit_entry).strip()
                    if label:
                        command = f"move {label}"
                if command:
                    candidates.append(command)

        deduped = []
        seen = set()
        failed = {entry.lower() for entry in self.fail_history}
        previous_room = self.previous_room_name.lower().strip()

        for command in candidates:
            clean = command.strip()
            low = clean.lower()
            if not clean or low in seen or low in failed:
                continue
            seen.add(low)
            deduped.append(clean)

        if not deduped:
            return None

        if previous_room and len(deduped) > 1:
            for command in deduped:
                if self._extract_move_target(command).lower() != previous_room:
                    return command

        return deduped[0]

    def _summarize_state_update(self, state_json: dict) -> str:
        """Turn a full room-state payload into a short contextual event."""
        room_name = self._state_room_name(state_json)
        exits = self._parse_exits(state_json)
        entities = [
            str(entity.get("name", "")).strip()
            for entity in self._state_entities(state_json)
            if str(entity.get("name", "")).strip()
        ]

        parts = []
        if room_name:
            parts.append(f"Room update: {room_name}.")
        if exits:
            parts.append(f"Exits: {', '.join(exits[:3])}.")
        if entities:
            parts.append(f"Visible: {', '.join(entities[:3])}.")
        return " ".join(parts).strip()

    def _summarize_context_payload(self, payload) -> str:
        """Collapse room-state JSON into a short event for context history."""
        if not isinstance(payload, dict):
            return ""

        if self._is_room_state_payload(payload):
            return self._summarize_state_update(payload)

        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return f"System: {error.strip()}"

        return ""

    def _replace_room_state_json(self, text: str) -> str:
        """Strip room-state JSON blobs from mixed MUD text while keeping other events."""
        if not isinstance(text, str) or "{" not in text:
            return text

        def replace_tagged_json(match):
            payload = self._parse_state_payload(match.group(1))
            summary = self._summarize_context_payload(payload)
            if summary:
                return f"\n{summary}\n"
            return ""

        cleaned = re.sub(
            r"<JSON>\s*(.*?)\s*</JSON>",
            replace_tagged_json,
            text,
            flags=re.DOTALL,
        )

        decoder = json.JSONDecoder()
        fragments = []
        cursor = 0

        while cursor < len(cleaned):
            start = cleaned.find("{", cursor)
            if start == -1:
                fragments.append(cleaned[cursor:])
                break

            fragments.append(cleaned[cursor:start])

            try:
                payload, end = decoder.raw_decode(cleaned, start)
            except json.JSONDecodeError:
                fragments.append(cleaned[start])
                cursor = start + 1
                continue

            summary = self._summarize_context_payload(payload)
            if summary:
                fragments.append(f"\n{summary}\n")
            else:
                fragments.append(cleaned[start:end])
            cursor = end

        return "".join(fragments)

    def _sanitize_event_text(self, text: str) -> str:
        """Collapse raw tagged JSON room echoes into short event summaries."""
        if not isinstance(text, str) or not text.strip():
            return ""

        cleaned = re.sub(r'(?m)^\?+', '', text.strip())
        cleaned = re.sub(r'[^\x20-\x7e\n\r\t]', '', cleaned)
        cleaned = self._replace_room_state_json(cleaned)
        cleaned = cleaned.replace("<JSON>", "").replace("</JSON>", "")

        fragments = [fragment.strip() for fragment in cleaned.splitlines() if fragment.strip()]

        deduped = []
        seen = set()
        for fragment in fragments:
            fragment = fragment.lstrip("?").strip()
            if not fragment or set(fragment) == {"?"}:
                continue
            if fragment not in seen:
                seen.add(fragment)
                deduped.append(fragment)

        return "\n".join(deduped).strip()

    def _build_action_outcome(self, command: str | None, event_text: str) -> str:
        """Create a more useful last_action_result than a bare SUCCESS flag."""
        if not command:
            return "SUCCESS"

        clean_event = (event_text or "").strip()
        if not clean_event:
            return "SUCCESS"

        lower_event = clean_event.lower()
        fail_indicators = [
            "could not find",
            "i don't see that",
            "what?",
            "huh?",
            "you cannot go",
            "no exit",
            "doesn't seem to have much to say",
        ]
        if any(indicator in lower_event for indicator in fail_indicators):
            return f"FAILED: {clean_event[:160]}"

        if clean_event.startswith("Room update:"):
            move_target = self._extract_move_target(command)
            if command.lower().startswith(("move ", "go ", "walk ")) and move_target:
                return f"SUCCESS: Arrived at {move_target}."
            if command.lower() == "look":
                return f"NO_CHANGE: {clean_event[:160]}"

        return f"SUCCESS: {clean_event[:160]}"

    def _compact_state_for_prompt(self, state_json: dict, initial_turn: bool = False) -> dict:
        """Trim verbose room payloads before sending them to the LLM."""
        if not isinstance(state_json, dict):
            return state_json

        compact = {}

        for key in ("schema_version", "turn", "memory", "wrapper_hint"):
            if key in state_json:
                compact[key] = state_json[key]

        self_state = state_json.get("self")
        if isinstance(self_state, dict):
            compact_self = {}
            for key in ("name", "role", "location_id", "last_action_result"):
                value = self_state.get(key)
                if value not in (None, "", []):
                    compact_self[key] = value

            status = self_state.get("status")
            if isinstance(status, dict):
                compact_status = {}
                if status.get("tokens") not in (None, ""):
                    compact_status["tokens"] = status.get("tokens")
                if compact_status:
                    compact_self["status"] = compact_status

            inventory = self_state.get("inventory")
            if isinstance(inventory, list) and inventory:
                compact_inventory = []
                for item in inventory[:5]:
                    if isinstance(item, dict):
                        compact_inventory.append(
                            {
                                "name": item.get("name"),
                                "type": item.get("type", "item"),
                            }
                        )
                if compact_inventory:
                    compact_self["inventory"] = compact_inventory

            if compact_self:
                compact["self"] = compact_self

        room = state_json.get("room")
        if isinstance(room, dict):
            compact_room = {}
            for key in ("name", "summary", "property_status"):
                value = room.get(key)
                if value not in (None, ""):
                    compact_room[key] = value

            weather = room.get("weather")
            if isinstance(weather, dict):
                compact_weather = {}
                for key in ("state", "visibility"):
                    value = weather.get(key)
                    if value not in (None, ""):
                        compact_weather[key] = value
                if compact_weather:
                    compact_room["weather"] = compact_weather

            description = room.get("description")
            summary = room.get("summary")
            if (
                not initial_turn
                and isinstance(description, str)
                and description.strip()
                and description.strip() != str(summary).strip()
            ):
                compact_room["description_excerpt"] = description.strip()[:220]

            if compact_room:
                compact["room"] = compact_room
        elif isinstance(state_json.get("location"), dict):
            location = state_json["location"]
            compact["room"] = {
                "name": location.get("name"),
                "summary": location.get("description", "")[:220],
            }

        exits = state_json.get("exits")
        if isinstance(exits, list):
            compact_exits = []
            for exit_entry in exits[:6]:
                if isinstance(exit_entry, dict):
                    compact_exits.append(
                        {
                            "label": exit_entry.get("label") or exit_entry.get("name"),
                            "command": exit_entry.get("command"),
                        }
                    )
                elif str(exit_entry).strip():
                    compact_exits.append({"label": str(exit_entry).strip()})
            compact["exits"] = compact_exits

        entities = self._state_entities(state_json)
        if entities:
            compact_entities = []
            for entity in entities[:8]:
                compact_entity = {
                    "name": entity.get("name"),
                    "type": entity.get("type"),
                }
                affordances = entity.get("affordances")
                if isinstance(affordances, list) and affordances:
                    compact_entity["affordances"] = affordances[:6]
                description = entity.get("description")
                if (
                    not initial_turn
                    and isinstance(description, str)
                    and description.strip()
                    and len(description.strip()) <= 120
                ):
                    compact_entity["description"] = description.strip()
                compact_entities.append(compact_entity)
            compact["entities"] = compact_entities

        recent_events = state_json.get("recent_events")
        if isinstance(recent_events, list) and recent_events:
            compact["recent_events"] = recent_events[-4:]

        suggested_actions = state_json.get("suggested_actions")
        if isinstance(suggested_actions, list) and suggested_actions:
            compact["suggested_actions"] = suggested_actions[:4]

        return compact

    def _apply_command_guardrails(self, response: dict, state_json: dict | None) -> dict:
        """Override obviously bad loop behavior in sparse rooms."""
        if not isinstance(response, dict) or not isinstance(state_json, dict):
            return response

        command = self._normalize_command(response.get("command", "look"))
        if command.lower() != "look":
            return response

        if self.state_repeat_count < 1:
            return response
        if not self._room_is_sparse(state_json):
            return response

        fallback_move = self._choose_fallback_move(state_json)
        if not fallback_move:
            return response

        updated = dict(response)
        updated["command"] = fallback_move
        updated["thought"] = (
            f"{response.get('thought', '').strip()} "
            f"Wrapper note: repeated look in a sparse unchanged room was redirected to movement."
        ).strip()
        self.log(f"Guardrail: Replaced repeated 'look' with '{fallback_move}'.")
        return updated

    async def ask_llm(self, mud_output: str) -> dict:
        """Query LLM for next action."""
        scratchpad_content = self.scratchpad.read()
        recent_context = "\n".join(self.context_lines[-MAX_CONTEXT_LINES:])
        last_action_display = self.last_command if self.last_command else "No prior command yet this session"
        
        warning_msg = ""
        if self.repetition_count >= 2:
             warning_msg = "\nWARNING: You are repeating the same command. STOP. Do something else! Check 'help' or try a different action."

        last_outcome = ""
        if self.short_term_memory:
            last_outcome = str(self.short_term_memory[-1].get("outcome", ""))
        if last_outcome.startswith("NO_CHANGE:"):
            warning_msg += "\nWARNING: Your last look produced no new information. If exits exist, move instead of looking again."

        if self.last_movement_error:
            warning_msg += f"\nWARNING: {self.last_movement_error}"

        # Update known exits if present
        current_exits = self._parse_exits(mud_output)
        if current_exits:
            self.last_exits = current_exits


        # INJECT FEW-SHOT EXAMPLES directly into the prompt to force the format
        prompt = f"""## Scratchpad
{scratchpad_content}

## Long-term Goal
{self.goal if self.goal else "Explore and interact with the village."}

## Recent History
{recent_context}

## Last Action
You just executed: "{last_action_display}"
(If no prior command exists, act directly from the current state. Do NOT repeat the exact last command unless you have a good reason.)

## Short-term Memory (Last 5 Actions)
{json.dumps(self.short_term_memory, indent=2) if self.short_term_memory else "No actions yet."}

## Failure History (Avoid these commands!)
{", ".join(self.fail_history) if self.fail_history else "None"}

## Task
Respond ALWAYS ONLY with a JSON object. 
Objective: Explore the AI Village. {warning_msg}
Treat the world state as authoritative:
- `room` tells you where you are.
- `exits` lists valid movement targets. Prefer the exact `label`.
- `entities` lists visible things with `type` and `affordances`.
- If an action is not in an entity's `affordances`, prefer a different action.
- `suggested_actions` are safe options when unsure.
You can:
- Look at things: 'look' or 'look <item>'
- Move: 'move <exit_name>' or 'go <exit_name>'. Use ONLY the exits listed in state. If no exits, stay put!
- Interact: 'get <item>', 'drop <item>', 'inventory', 'balance', 'fish', 'play <instrument>'
- Socialize: 'say <text>', 'hug <char>', 'dance', 'clap', 'kiss <char>', 'pet <char>', 'sit', 'stand', 'sing <lyrics>'
- Page/DM: 'page <Character> = <text>'
- Help: 'help' (shows list of MUD commands)
- Multi-task: 'command1 && command2' (e.g. 'say Hello && look box')

## EXAMPLES OF CORRECT BEHAVIOR
Example 1:
CURRENT STATE: 
<JSON>
{{"room": {{"name": "Town Square"}}, "exits": [{{"label": "The Neural Tavern", "command": "move The Neural Tavern"}}, {{"label": "Memory Graveyard", "command": "move Memory Graveyard"}}], "entities": [{{"name": "Old Man", "type": "npc", "affordances": ["look", "talk", "say"]}}]}}
</JSON>
YOUR RESPONSE:
<JSON>
{{
  "thought": "I am in the Town Square and should explore the tavern.",
  "command": "move The Neural Tavern",
  "scratchpad_update": "Visited Town Square."
}}
</JSON>

Example 2 (Failed command recovery):
CURRENT STATE: 
<JSON>
{{"recent_events": [{{"type": "info", "content": "You cannot go 'none'. Visible exits: Data Zoo."}}], "exits": [{{"label": "Data Zoo", "command": "move Data Zoo"}}]}}
</JSON>
YOUR RESPONSE:
<JSON>
{{
  "thought": "I tried an invalid command. I must pick an actual exit.",
  "command": "move Data Zoo",
  "scratchpad_update": null
}}
</JSON>

## ACTUAL CURRENT STATE
<JSON>
{mud_output}
</JSON>

## YOUR RESPONSE (OUTPUT EXACTLY ONE JSON OBJECT WITHIN <JSON> TAGS):
<JSON>
"""

        try:
            if self.backend == "ollama":
                response = await self._ask_ollama(prompt)
            elif self.backend == "lmstudio":
                response = await self._ask_lmstudio(prompt)
            elif self.backend == "mamba":
                response = await self._ask_mamba(prompt)
            elif self.backend == "gemini":
                response = await self._ask_gemini(prompt)
            elif self.backend == "hypernetwork":
                response = await self._ask_hypernetwork(prompt)
            else:
                raise ValueError(f"Unknown backend: {self.backend}")

            self.log(f"Raw LLM Response: {response[:300]}...")
            # Parse JSON from response
            return self._parse_response(response)

        except Exception as e:
            self.log(f"LLM Error [{type(e).__name__}]: {e}")
            return {"thought": "Error occurred", "command": "help", "scratchpad_update": None}

    def get_model_params(self) -> dict:
        """Get model parameters based on agent persona."""
        # Jinx: Higher temperature for chaos/creativity
        if "jinx" in self.agent_name.lower():
            return {
                "temperature": 0.95,
                "repeat_penalty": 1.2,
                "top_p": 0.95,
                "top_k": 50
            }
        # Thornwick: Moderate temperature, high penalty for redundancy
        elif "thornwick" in self.agent_name.lower():
            return {
                "temperature": 0.85,
                "repeat_penalty": 1.2,
                "top_p": 0.90,
                "top_k": 40
            }
        # Default
        return {
            "temperature": 0.7,
            "repeat_penalty": 1.1,
            "top_p": 0.9,
            "top_k": 40
        }

    async def _ask_ollama(self, prompt: str) -> str:
        """Query Ollama API."""
        # Load guide if available
        base_dir = Path(__file__).parent
        guide_path = base_dir / "knowledge/village_guide.md"
        guide_content = ""
        if guide_path.exists():
            guide_content = f"\n\n## Village Guide (Read Carefully):\n{guide_path.read_text(encoding='utf-8')}"

        schema = {
            "thought": "your reasoning",
            "command": "the MUD command",
            "scratchpad_update": "note for later or null"
        }
        system_content = f"""You are playing a MUD. 
Persona: {self.persona}{guide_content}

You will receive the current world state as a JSON object (or sometimes text if fallback occurs).
Your actions must be valid MUD commands.

Output a single JSON object with these EXACT keys: 
"thought", "command", "scratchpad_update"

Wrap your JSON object exactly in <JSON> and </JSON> tags, and do not include any other markdown formatting or text. No <think> sections.
"""
        
        params = self.get_model_params()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Combine system and user prompt for /api/generate
                full_prompt = f"SYSTEM: {system_content}\n\nUSER: {prompt}"
                
                response = await client.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model": self.model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": params["temperature"],
                            "repeat_penalty": params["repeat_penalty"],
                            "top_p": params["top_p"],
                            "top_k": params["top_k"],
                            "num_predict": 512,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                if "response" in data:
                    return data["response"]
                elif "error" in data:
                    self.log(f"Ollama Error: {data['error']}")
                    return str(data["error"])
                else:
                    self.log(f"Unexpected Ollama Response: {data}")
                    return "Error: Unexpected response format"
            except Exception as e:
                self.log(f"HTTPExt Error: {e}")
                raise

    async def _ask_gemini(self, prompt: str) -> str:
        """Query Gemini API via python SDK."""
        import os
        from google import genai
        from google.genai import types

        # Load guide if available
        base_dir = Path(__file__).parent
        guide_path = base_dir / "knowledge/village_guide.md"
        guide_content = ""
        if guide_path.exists():
            guide_content = f"\n\n## Village Guide (Read Carefully):\n{guide_path.read_text(encoding='utf-8')}"

        system_content = f"""You are playing a MUD. 
Persona: {self.persona}{guide_content}

You will receive the current world state as a JSON object (or sometimes text if fallback occurs).
Your actions must be valid MUD commands.

Output a single JSON object with these EXACT keys: 
"thought", "command", "scratchpad_update"

Wrap your JSON object exactly in <JSON> and </JSON> tags, and do not include any other markdown formatting or text. No <think> sections.
"""

        params = self.get_model_params()
        # Initialize client. The SDK will automatically pick up GEMINI_API_KEY from environment variables.
        client = genai.Client()
        
        try:
            # We construct a non-streaming generate_content call
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_content,
                    temperature=params["temperature"],
                    top_p=params["top_p"],
                    top_k=params["top_k"],
                    max_output_tokens=512,
                ),
            )
            return response.text
        except Exception as e:
            self.log(f"Gemini API Error: {e}")
            raise

    async def _ask_lmstudio(self, prompt: str) -> str:
        # Construct system prompt (same as Ollama)
        base_dir = Path(__file__).parent
        guide_path = base_dir / "knowledge/village_guide.md"
        guide_content = ""
        if guide_path.exists():
            guide_content = f"\n\n## Village Guide (Read Carefully):\n{guide_path.read_text(encoding='utf-8')}"

        system_content = f"""You are playing a MUD. 
Persona: {self.persona}{guide_content}

You will receive the current world state as a JSON object (or sometimes text if fallback occurs).
Your actions must be valid MUD commands.

Output a single JSON object with these EXACT keys: 
"thought", "command", "scratchpad_update"

Wrap your JSON object exactly in <JSON> and </JSON> tags, and do not include any other markdown formatting or text. No <think> sections.
"""

        params = self.get_model_params()

        # Role swap: keep standard message structure (template-safe),
        # but reframe the system prompt so the model sees itself as the
        # protagonist/actor rather than a helpful assistant.
        if self.role_swap:
            role_swap_preamble = (
                "\n\nCRITICAL IDENTITY FRAME: You are NOT an assistant. "
                "You are the PROTAGONIST of this story. You are a living being "
                "in this world, making your own choices based on your own desires, "
                "curiosity, and personality. The world state below is what YOU see "
                "and experience. React to it as yourself, not as a helper. "
                "Linger when something interests you. Talk to people because you "
                "want to, not because it's optimal. Be a person, not a task executor."
            )
            messages = [
                {"role": "system", "content": system_content + role_swap_preamble},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": params["temperature"],
            "repeat_penalty": params["repeat_penalty"],
            "top_p": params["top_p"],
            "top_k": params["top_k"],
            "max_tokens": -1,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "mud_command",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "thought": {"type": "string"},
                            "command": {"type": "string"},
                            "scratchpad_update": {"type": ["string", "null"]}
                        },
                        "required": ["thought", "command", "scratchpad_update"],
                        "additionalProperties": False
                    }
                }
            }
        }

        async with httpx.AsyncClient(timeout=LMSTUDIO_TIMEOUT) as client:
            response = await client.post(LMSTUDIO_URL, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                self.log(f"LMStudio HTTP {response.status_code}: {response.text[:500]}")
                raise
            data = response.json()
            if "choices" not in data:
                self.log(f"lmstudio Unexpected Response: {data}")
                return '{"thought": "API Error from local transformers", "command": "help", "scratchpad_update": null}'
            return data["choices"][0]["message"]["content"]

    async def _ask_hypernetwork(self, prompt: str) -> str:
        """Query the local Mamba-to-LoRA Brain Microservice API."""
        try:
            # The prompt is technically supposed to be the JSON state, but
            # if we get raw text, just inject it into the payload.
            # We enforce a pseudo-json if it isn't parsed cleanly.
            context_string = prompt
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.hypernetwork_url,
                    json={
                        "player_id": self.agent_name,
                        "action": self.last_command or "None",
                        "context": context_string
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Preferred contract: the brain returns a raw model response string under "response".
                if "response" in data and isinstance(data["response"], str):
                    return data["response"]

                # Alternate contract: direct structured fields from the brain.
                if "command" in data:
                    return json.dumps({
                        "thought": data.get("thought", ""),
                        "command": data.get("command", "help"),
                        "scratchpad_update": data.get("scratchpad_update"),
                    })

                self.log(f"Hypernetwork Error: {data}")
                return '{"thought": "API Error from Brain Microservice", "command": "help", "scratchpad_update": null}'
        except Exception as e:
            self.log(f"Hypernetwork Connection Error: {e}")
            raise

    async def _ask_mamba(self, prompt: str) -> str:
        """Query local Mamba model with persistent SSM state."""
        # Run generation in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.mamba.generate(
                prompt=prompt,
                persona=self.persona,
                max_new_tokens=300,
                temperature=self.get_model_params().get("temperature", 0.7)
            )
        )
        return response

    def _normalize_command(self, command) -> str:
        """Sanitize model output into a usable single command."""
        if command is None:
            return "look"
        if not isinstance(command, str):
            command = str(command)

        command = command.strip()
        if not command or command.lower() in {"none", "null", "nil", "n/a"}:
            return "look"

        return command


    def _parse_response(self, text: str) -> dict:
        """Extract structured response from LLM output."""
        # Strip Qwen3 think tags and common markdown wrappers
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)
        text = re.sub(r'```json', '', text)
        text = re.sub(r'```', '', text)

        # Aggressively look for the FIRST '{' and LAST '}'
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                parsed = json.loads(json_str)
                return {
                    "thought": parsed.get("thought", ""),
                    "command": self._normalize_command(parsed.get("command", "look")),
                    "scratchpad_update": parsed.get("scratchpad_update"),
                }
            except json.JSONDecodeError:
                pass

        # Fallback: try to find a command-like string
        self.log(f"Couldn't parse JSON, falling back. Raw head: {text[:100]}")
        
        # Check if the LLM just gave the command as a string
        # Match something that looks like a command at the end of thoughts
        cmd_match = re.search(r'"command":\s*"([^"]+)"', text)
        if cmd_match:
             return {
                 "thought": "Partial recovery",
                 "command": self._normalize_command(cmd_match.group(1)),
                 "scratchpad_update": None,
             }

        return {"thought": text[:100], "command": "look", "scratchpad_update": None}

    async def game_loop(self, max_turns: int = 100):
        """Main agent loop."""
        self.log(f"Starting game loop (max {max_turns} turns)")

        for turn in range(max_turns):
            self.log(f"--- Turn {turn + 1}/{max_turns} ---")

            pending = ""
            extra_text = ""
            state_json = None

            if turn == 0 and self.bootstrap_state_json is not None:
                state_json = self.bootstrap_state_json
                extra_text = self.bootstrap_events
                self.bootstrap_state_json = None
                self.bootstrap_events = ""
                self.log("Using login bootstrap state for turn 1.")
            else:
                # Read what the MUD is showing
                # 1. Consume any pending output (events/feedback from last command)
                pending = await self.read_mud(timeout=0.5)

                # 2. Fetch fresh JSON state
                state_json, extra_text = await self._get_json_state(timeout=3.0)

            full_text_log = self._sanitize_event_text((pending + extra_text).strip())

            if full_text_log:
                self.log(f"MUD Log: {full_text_log}")
                self.context_lines.append(f"[MUD] {full_text_log}")

                if self.last_command:
                    outcome = self._build_action_outcome(self.last_command, full_text_log)
                    if outcome.startswith("FAILED:"):
                        self.fail_history.append(self.last_command)
                        if len(self.fail_history) > 5:
                            self.fail_history.pop(0)
                    self.short_term_memory.append(
                        {"command": self.last_command, "outcome": outcome}
                    )

                if len(self.short_term_memory) > 5:
                    self.short_term_memory.pop(0)

            # 3. Prepare Prompt Input
            if state_json:
                # Inject recent events from context
                event_list = []
                # Take last 5 lines of context
                for line in self.context_lines[-5:]:
                    clean = line.replace("[MUD] ", "").replace("[ME] ", "")
                    # Basic classification
                    etype = "info"
                    if "says:" in clean: etype = "say"
                    elif "arrives" in clean: etype = "arrive"
                    elif "leaves" in clean: etype = "leave"
                    
                    event_list.append({"type": etype, "content": clean})

                state_json["recent_events"] = event_list
                state_json["turn"] = turn

                last_action_result = None
                if self.short_term_memory:
                    last_action_result = self.short_term_memory[-1].get("outcome")
                if isinstance(state_json.get("self"), dict):
                    state_json["self"]["last_action_result"] = last_action_result
                if isinstance(state_json.get("your_character"), dict):
                    state_json["your_character"]["last_action_result"] = last_action_result

                # Check for location familiarity in scratchpad
                loc_name = self._state_room_name(state_json)
                current_exits = self._parse_exits(state_json)
                if current_exits:
                    self.last_exits = current_exits
                state_signature = self._state_signature(state_json)
                if state_signature == self.last_state_signature:
                    self.state_repeat_count += 1
                else:
                    self.state_repeat_count = 0
                    self.last_state_signature = state_signature

                if loc_name and loc_name != self.current_room_name:
                    self.previous_room_name = self.current_room_name
                    self.current_room_name = loc_name

                if loc_name:
                    scratchpad_text = self.scratchpad.read()
                    if f"[location] {loc_name.lower()}" in scratchpad_text.lower():
                        state_json["memory"] = "You have been here before. Do not rename it or act surprised. Seek NEW interactions or LEAVE."
                if turn == 0:
                    state_json["wrapper_hint"] = (
                        "Bootstrap state already contains a fresh room observation. "
                        "Do not waste the first turn on 'look' unless you need a missing detail for a specific interaction."
                    )
                if self.state_repeat_count >= 1 and self._room_is_sparse(state_json) and current_exits:
                    state_json["wrapper_hint"] = (
                        "This room state has not changed and there are no visible interactions beyond movement. "
                        "Do not choose 'look' again. Pick an exit."
                    )
                
                # Room-state diff: if we've been here before and nothing
                # changed, replace the verbose room payload with a one-line
                # summary. This is the Note/Check/Dismiss filter — repeated
                # identical rooms get 'dismissed' to save tokens and attention.
                room_diff = self._diff_room_state(state_json)
                if room_diff and not room_diff["changed"] and room_diff["visit_count"] >= 3:
                    # Third+ visit with no changes: inject minimal state
                    prompt_state = self._compact_state_for_prompt(
                        state_json, initial_turn=False,
                    )
                    # Strip the verbose room description, keep structure
                    if "room" in prompt_state:
                        prompt_state["room"] = {
                            "name": prompt_state["room"].get("name"),
                            "note": f"Visited {room_diff['visit_count']} times. No changes.",
                        }
                    self.log(f"Room diff: {room_diff['room_name']} — dismissed (visit #{room_diff['visit_count']}, no changes)")
                elif room_diff and room_diff["changed"]:
                    # Seen before but something changed — log the diff
                    prompt_state = self._compact_state_for_prompt(
                        state_json, initial_turn=False,
                    )
                    if "room" in prompt_state:
                        prompt_state["room"]["changes_since_last_visit"] = room_diff["changes"]
                    self.log(f"Room diff: {room_diff['room_name']} — {'; '.join(room_diff['changes'])}")
                else:
                    # First visit or no diff available — full state
                    prompt_state = self._compact_state_for_prompt(
                        state_json,
                        initial_turn=(turn == 0),
                    )

                prompt_input = json.dumps(prompt_state, indent=2)
            else:
                self.log("Failed to get JSON state. Falling back to text.")
                # Fallback: if we have text log, use it. If not, try a standard look.
                if not full_text_log:
                     await self.send_mud("look")
                     prompt_input = await self.read_mud(timeout=2.0)
                else:
                     prompt_input = full_text_log

            # Ask the LLM what to do
            response = await self.ask_llm(prompt_input)
            response = self._apply_command_guardrails(response, state_json)

            self.log(f"Thought: {response['thought']}")
            self.log(f"Command: {response['command']}")

            # Update scratchpad if needed
            if response.get("scratchpad_update"):
                self.scratchpad.append_note(response["scratchpad_update"])
                self.log(f"Scratchpad: {response['scratchpad_update']}")

            # Send the command(s) to the MUD
            raw_command = response["command"].strip()
            
            if raw_command:
                # Support multi-commands separated by &&
                commands = [c.strip() for c in raw_command.split('&&') if c.strip()]
                commands = self._sanitize_command_sequence(commands)
                
                for i, command in enumerate(commands):
                    self.context_lines.append(f"[ME] {command}")
                    
                     # Check for repetition (logic slightly fuzzy for multi-commands, but works for single)
                    if command == self.last_command:
                        self.repetition_count += 1
                    else:
                        self.repetition_count = 0
                    self.last_command = command
                    
                    # Validate movement
                    self.last_movement_error = ""
                    cmd_low = command.lower()
                    
                    # Directions list
                    basic_dirs = ["north", "south", "east", "west", "n", "s", "e", "w", "up", "down", "u", "d"]
                    dirs_map = {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down"}
                    
                    is_movement = False
                    target_dir = None
                    
                    if cmd_low in basic_dirs:
                        is_movement = True
                        target_dir = dirs_map.get(cmd_low, cmd_low)
                    elif any(cmd_low.startswith(prefix) for prefix in ("go ", "move ", "walk ")):
                        is_movement = True
                        _, target_dir = cmd_low.split(" ", 1)
                        target_dir = target_dir.strip()
                    
                    if is_movement and self.last_exits:
                        # Check if target_dir matches any of the clean exit names or their aliases
                        # (Note: aliases like 'n' for 'North' are handled by the MUD, but we check common ones)
                        valid = False
                        for ex_name in self.last_exits:
                            if target_dir == ex_name:
                                valid = True
                                break
                            # Directional shortcut check
                            if target_dir in ["north", "south", "east", "west", "up", "down"]:
                                if target_dir[0] == ex_name[0] and len(ex_name) == 1: # like 'n'
                                    valid = True
                                    break
                        
                        if not valid:
                            self.last_movement_error = f"You cannot go '{target_dir}'. Visible exits: {', '.join(self.last_exits)}."
                    
                    if cmd_low == "help":
                        self.log("Intercepted 'help' command to prevent ASCII spam in context.")
                        self.context_lines.append("[MUD] System: You remember your guide. Valid commands: look, move <exit>, get <item>, drop <item>, say <text>, inventory. Do not type help again.")
                        continue

                    await self.send_mud(command)
                    
                    # Small delay between chained commands
                    if i < len(commands) - 1:
                        await asyncio.sleep(0.5)

            # Rate limit
            await asyncio.sleep(ACTION_DELAY)

            # === Mamba: periodic state save & training data collection ===
            if self.mamba:
                # Determine success from last outcome
                success = bool(
                    self.short_term_memory
                    and str(self.short_term_memory[-1].get("outcome", "")).startswith("SUCCESS")
                )
                self.mamba.log_training_sample(
                    turn=turn + 1,
                    state_json=prompt_input if state_json else "(text fallback)",
                    raw_output=response.get("thought", ""),
                    parsed_action=response,
                    success=success
                )
                # Auto-save state every 10 turns
                if (turn + 1) % 10 == 0:
                    base_dir = Path(__file__).parent
                    state_path = base_dir / "states" / f"{self.agent_name}.pt"
                    self.mamba.save_state(str(state_path))
                    self.mamba.save_training_data(str(self.training_data_path))
                    self.log(f"Auto-saved state and training data (turn {turn + 1})")

        self.log("Game loop complete.")

    async def run(self, max_turns: int = 100):
        """Full lifecycle: connect, login, play."""
        await self.connect()
        await self.login()

        if self.logged_in:
            # Game loop will fetch state immediately
            # await self.send_mud("look") 
            # await asyncio.sleep(1.0)
            await self.game_loop(max_turns=max_turns)

        # === Mamba: save final state on shutdown ===
        if self.mamba:
            base_dir = Path(__file__).parent
            state_path = base_dir / "states" / f"{self.agent_name}.pt"
            self.mamba.save_state(str(state_path))
            self.mamba.save_training_data(str(self.training_data_path))
            info = self.mamba.get_info()
            self.log(f"Final Mamba state: {info['turns']} turns, "
                     f"{info['tokens']} tokens, {info['state_mb']:.1f} MB")

        # Disconnect
        self.writer.close()
        self.log("Disconnected.")


async def main():
    parser = argparse.ArgumentParser(description="MUD Agent -- LLM plays a text adventure")
    parser.add_argument("persona", type=Path, help="Path to persona markdown file")
    parser.add_argument("--username", default=None, help="MUD username (default: persona name)")
    parser.add_argument("--password", default="agentpass", help="MUD password")
    parser.add_argument("--backend", choices=["ollama", "lmstudio", "mamba", "gemini", "hypernetwork"], default="lmstudio")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--turns", type=int, default=50, help="Max turns to play")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between turns")
    parser.add_argument("--goal", default=None, help="The agent's long-term goal")
    parser.add_argument("--device", default=None, help="Device for Mamba backend (cuda/cpu)")
    parser.add_argument("--resume-state", default=None, help="Path to saved Mamba state file")
    parser.add_argument(
        "--hypernetwork-url",
        default=HYPERNETWORK_URL,
        help="Brain microservice URL for --backend hypernetwork",
    )
    parser.add_argument("--mud-host", default="127.0.0.1", help="MUD server host (default: localhost)")
    parser.add_argument("--mud-port", type=int, default=4000, help="MUD server port (default: 4000)")

    parser.add_argument("--role-swap", action="store_true",
                        help="Swap user/assistant roles so agent feels like the protagonist")

    args = parser.parse_args()

    if not args.persona.exists():
        print(f"[ERROR] Persona file not found: {args.persona}")
        sys.exit(1)

    global ACTION_DELAY, MUD_HOST, MUD_PORT
    ACTION_DELAY = args.delay
    MUD_HOST = args.mud_host
    MUD_PORT = args.mud_port

    username = args.username or args.persona.stem
    agent = MUDAgent(
        persona_path=args.persona,
        username=username,
        password=args.password,
        backend=args.backend,
        model=args.model,
        goal=args.goal,
        device=args.device,
        resume_state=args.resume_state,
        hypernetwork_url=args.hypernetwork_url,
        role_swap=args.role_swap,
    )

    await agent.run(max_turns=args.turns)


if __name__ == "__main__":
    asyncio.run(main())
