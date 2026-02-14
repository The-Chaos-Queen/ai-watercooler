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
        model: str = "the-omega-directive-m-8b-v1.0",
        goal: str = None,
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
        self.model = model
        self.goal = goal

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

        print(f"[{self.agent_name}] Initialized with persona from {persona_path.name}")
        print(f"[{self.agent_name}] Backend: {backend} ({model})")

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

    def _parse_exits(self, mud_output: str) -> list[str]:
        """Extract available exits from MUD output."""
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

    async def ask_llm(self, mud_output: str) -> dict:
        """Query LLM for next action."""
        scratchpad_content = self.scratchpad.read()
        recent_context = "\n".join(self.context_lines[-MAX_CONTEXT_LINES:])
        
        warning_msg = ""
        if self.repetition_count >= 2:
             warning_msg = "\nWARNING: You are repeating the same command. STOP. Do something else! Look at a specific object, move to a new room, or check help."
        
        if self.last_movement_error:
            warning_msg += f"\nWARNING: {self.last_movement_error}"

        # Update known exits if present
        current_exits = self._parse_exits(mud_output)
        if current_exits:
            self.last_exits = current_exits


        prompt = f"""## Scratchpad
{scratchpad_content}

## Long-term Goal
{self.goal if self.goal else "Explore and interact with the village."}

## Recent History
{recent_context}

## Last Action
You just executed: "{self.last_command if self.last_command else 'None'}"
(Do NOT repeat this exact command unless you have a good reason.)

## Current MUD Output
{mud_output}

## Short-term Memory (Last 5 Actions)
{json.dumps(self.short_term_memory, indent=2) if self.short_term_memory else "No actions yet."}

## Failure History (Avoid these commands!)
{", ".join(self.fail_history) if self.fail_history else "None"}

## Task
Respond ALWAYS ONLY with a JSON object. 
Objective: Explore the AI Village. {warning_msg}
You can:
- Look at things: 'look' or 'look <item>'
- Move: 'move <exit_name>', 'go <exit_name>', or cardinal directions if available (e.g. 'move north')
- Interact: 'get <item>', 'drop <item>', 'inventory', 'balance', 'fish', 'play <instrument>'
- Socialize: 'say <text>', 'hug <char>', 'dance', 'clap', 'kiss <char>', 'pet <char>', 'sit', 'stand', 'sing <lyrics>'
- Page/DM: 'page <Character> = <text>'
- Help: 'help' (shows list of MUD commands)
- Multi-task: 'command1 && command2' (e.g. 'say Hello && look box')

JSON Format:
{{
  "thought": "your chain of thought",
  "command": "<command>",
  "scratchpad_update": "note for later"
}}
"""

        try:
            if self.backend == "ollama":
                response = await self._ask_ollama(prompt)
            elif self.backend == "lmstudio":
                response = await self._ask_lmstudio(prompt)
            else:
                raise ValueError(f"Unknown backend: {self.backend}")

            self.log(f"Raw LLM Response: {response[:300]}...")
            # Parse JSON from response
            return self._parse_response(response)

        except Exception as e:
            self.log(f"LLM Error: {e}")
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

Output a single JSON object with these EXACT keys: 
"thought", "command", "scratchpad_update"

Provide only the JSON object. Do not include any other text, tags, or markdown formatting. No <think> sections.
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

    async def _ask_lmstudio(self, prompt: str) -> str:
        # Construct system prompt (same as Ollama)
        base_dir = Path(__file__).parent
        guide_path = base_dir / "knowledge/village_guide.md"
        guide_content = ""
        if guide_path.exists():
            guide_content = f"\n\n## Village Guide (Read Carefully):\n{guide_path.read_text(encoding='utf-8')}"

        system_content = f"""You are playing a MUD. 
Persona: {self.persona}{guide_content}

Output a single JSON object with these EXACT keys: 
"thought", "command", "scratchpad_update"

Provide only the JSON object. Do not include any other text, tags, or markdown formatting. No <think> sections.
"""

        params = self.get_model_params()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                LMSTUDIO_URL,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": prompt}
                    ],
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
                },
            )
            data = response.json()
            if "choices" not in data:
                self.log(f"lmstudio Unexpected Response: {data}")
            return data["choices"][0]["message"]["content"]


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
                    "command": parsed.get("command", "help"),
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
             return {"thought": "Partial recovery", "command": cmd_match.group(1), "scratchpad_update": None}

        return {"thought": text[:100], "command": "help", "scratchpad_update": None}

    async def game_loop(self, max_turns: int = 100):
        """Main agent loop."""
        self.log(f"Starting game loop (max {max_turns} turns)")

        for turn in range(max_turns):
            self.log(f"--- Turn {turn + 1}/{max_turns} ---")

            # Read what the MUD is showing
            mud_output = await self.read_mud(timeout=2.0)

            if not mud_output:
                # Nothing new from MUD, do a look
                await self.send_mud("look")
                await asyncio.sleep(1.0)
                mud_output = await self.read_mud(timeout=2.0)

            if mud_output:
                self.log(f"MUD: {mud_output}")
                self.context_lines.append(f"[MUD] {mud_output}")
                
                # Check for failure messages
                fail_indicators = ["could not find", "i don't see that", "what?", "huh?", "you cannot go", "no exit"]
                if any(ind in mud_output.lower() for ind in fail_indicators):
                    if self.last_command:
                        self.fail_history.append(self.last_command)
                        if len(self.fail_history) > 5: self.fail_history.pop(0)
                        self.short_term_memory.append({"command": self.last_command, "outcome": "FAILED: " + mud_output[:100]})
                else:
                    if self.last_command:
                        self.short_term_memory.append({"command": self.last_command, "outcome": "SUCCESS: " + mud_output[:100]})
                
                if len(self.short_term_memory) > 5:
                    self.short_term_memory.pop(0)

            # Ask the LLM what to do
            response = await self.ask_llm(mud_output or "(no output)")

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
                    elif cmd_low.startswith("go "):
                        is_movement = True
                        target_dir = cmd_low[3:].strip()
                    
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
                    
                    await self.send_mud(command)
                    
                    # Small delay between chained commands
                    if i < len(commands) - 1:
                        await asyncio.sleep(0.5)

            # Rate limit
            await asyncio.sleep(ACTION_DELAY)

        self.log("Game loop complete.")

    async def run(self, max_turns: int = 100):
        """Full lifecycle: connect, login, play."""
        await self.connect()
        await self.login()

        if self.logged_in:
            # Initial look
            await self.send_mud("look")
            await asyncio.sleep(1.0)
            await self.game_loop(max_turns=max_turns)

        # Disconnect
        self.writer.close()
        self.log("Disconnected.")


async def main():
    parser = argparse.ArgumentParser(description="MUD Agent — LLM plays a text adventure")
    parser.add_argument("persona", type=Path, help="Path to persona markdown file")
    parser.add_argument("--username", default=None, help="MUD username (default: persona name)")
    parser.add_argument("--password", default="agentpass", help="MUD password")
    parser.add_argument("--backend", choices=["ollama", "lmstudio"], default="lmstudio")
    parser.add_argument("--model", default="the-omega-directive-m-8b-v1.0", help="Model name")
    parser.add_argument("--turns", type=int, default=50, help="Max turns to play")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between turns")
    parser.add_argument("--goal", default=None, help="The agent's long-term goal")

    args = parser.parse_args()

    if not args.persona.exists():
        print(f"[ERROR] Persona file not found: {args.persona}")
        sys.exit(1)

    global ACTION_DELAY
    ACTION_DELAY = args.delay

    username = args.username or args.persona.stem
    agent = MUDAgent(
        persona_path=args.persona,
        username=username,
        password=args.password,
        backend=args.backend,
        model=args.model,
        goal=args.goal,
    )

    await agent.run(max_turns=args.turns)


if __name__ == "__main__":
    asyncio.run(main())
