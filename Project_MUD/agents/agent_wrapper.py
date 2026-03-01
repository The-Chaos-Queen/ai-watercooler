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
        self.hypernetwork_url = hypernetwork_url

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
                
                # Try to find a valid JSON object in the buffer
                # We assume the server sends one JSON object per request
                s = buffer.find('{')
                e = buffer.rfind('}')
                
                if s != -1 and e != -1 and e > s:
                    candidate = buffer[s:e+1]
                    try:
                        data = json.loads(candidate)
                        # Success! Extract events before/after
                        events = buffer[:s] + buffer[e+1:]
                        # self.log("DEBUG: Successfully parsed JSON state")
                        return data, events.strip()
                    except json.JSONDecodeError as e:
                        pass
            
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
             warning_msg = "\nWARNING: You are repeating the same command. STOP. Do something else! Check 'help' or try a different action."
        
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
You just executed: "{self.last_command if self.last_command else 'None'}"
(Do NOT repeat this exact command unless you have a good reason.)

## Short-term Memory (Last 5 Actions)
{json.dumps(self.short_term_memory, indent=2) if self.short_term_memory else "No actions yet."}

## Failure History (Avoid these commands!)
{", ".join(self.fail_history) if self.fail_history else "None"}

## Task
Respond ALWAYS ONLY with a JSON object. 
Objective: Explore the AI Village. {warning_msg}
You can:
- Look at things: 'look' or 'look <item>'
- Move: 'move <exit_name>' or 'go <exit_name>'. Use ONLY the exits listed in the room description. If no exits, stay put!
- Interact: 'get <item>', 'drop <item>', 'inventory', 'balance', 'fish', 'play <instrument>'
- Socialize: 'say <text>', 'hug <char>', 'dance', 'clap', 'kiss <char>', 'pet <char>', 'sit', 'stand', 'sing <lyrics>'
- Page/DM: 'page <Character> = <text>'
- Help: 'help' (shows list of MUD commands)
- Multi-task: 'command1 && command2' (e.g. 'say Hello && look box')

## EXAMPLES OF CORRECT BEHAVIOR
Example 1:
CURRENT STATE: 
<JSON>
{{"location": {{"name": "Town Square"}}, "exits": ["The Neural Tavern", "Memory Graveyard"]}}
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
{{"events": ["You cannot go 'none'. Visible exits: Data Zoo."]}}
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
            # 1. Consume any pending output (events/feedback from last command)
            pending = await self.read_mud(timeout=0.5)

            # 2. Fetch fresh JSON state
            state_json, extra_text = await self._get_json_state(timeout=3.0)

            full_text_log = (pending + extra_text).strip()

            if full_text_log:
                self.log(f"MUD Log: {full_text_log}")
                self.context_lines.append(f"[MUD] {full_text_log}")
                
                # Check for failure messages
                fail_indicators = ["could not find", "i don't see that", "what?", "huh?", "you cannot go", "no exit"]
                if any(ind in full_text_log.lower() for ind in fail_indicators):
                    if self.last_command:
                        self.fail_history.append(self.last_command)
                        if len(self.fail_history) > 5: self.fail_history.pop(0)
                        self.short_term_memory.append({"command": self.last_command, "outcome": "FAILED: " + full_text_log[:100]})
                else:
                    if self.last_command:
                        self.short_term_memory.append({"command": self.last_command, "outcome": "SUCCESS"})
                
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
                
                # Check for location familiarity in scratchpad
                loc_name = state_json.get("location", {}).get("name", "")
                if loc_name:
                    scratchpad_text = self.scratchpad.read()
                    if f"[location] {loc_name.lower()}" in scratchpad_text.lower():
                        state_json["memory"] = "You have been here before. Do not rename it or act surprised. Seek NEW interactions or LEAVE."
                
                # Use the JSON string as the 'output' for the LLM
                prompt_input = json.dumps(state_json, indent=2)
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
                    and self.short_term_memory[-1].get("outcome") == "SUCCESS"
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
    )

    await agent.run(max_turns=args.turns)


if __name__ == "__main__":
    asyncio.run(main())
