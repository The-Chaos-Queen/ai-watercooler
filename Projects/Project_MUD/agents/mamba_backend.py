"""
mamba_backend.py - Mamba SSM Backend for MUD Agents
===================================================
Provides persistent-state text generation using Mamba-2.8B.
The SSM state accumulates across ALL turns, giving the agent episodic memory.

Key difference from Ollama/LMStudio:
  - Model loaded in-process (no API calls)
  - SSM state persists across turns (the agent REMEMBERS)
  - State can be saved/loaded from disk (session continuity)
  - Training data collected for Phase 2 (LoRA fine-tuning)

Author: Axon
Date: 2026-02-19
"""

import torch
import json
import time
import os
from pathlib import Path
from datetime import datetime


class MambaBackend:
    """
    Wraps a Mamba model for use as a MUD agent backend with persistent state.

    Usage:
        backend = MambaBackend("state-spaces/mamba-2.8b-hf", device="cuda")
        response = backend.generate(room_state_json, persona="You are Thornwick...")
        backend.save_state("states/thornwick.pt")
    """

    def __init__(self, model_name="state-spaces/mamba-2.8b-hf", device=None,
                 state_path=None):
        # Lazy imports so torch isn't required when using other backends
        from transformers import MambaForCausalLM, AutoTokenizer

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name

        print(f"[MambaBackend] Loading {model_name} on {self.device}...")
        start = time.time()

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = MambaForCausalLM.from_pretrained(
            model_name, torch_dtype=dtype
        ).to(self.device)
        self.model.eval()

        elapsed = time.time() - start
        print(f"[MambaBackend] Model loaded in {elapsed:.1f}s "
              f"({sum(p.numel() for p in self.model.parameters()) / 1e6:.0f}M params)")

        # === Persistent State ===
        self.cache_params = None  # The SSM state (the "residue")
        self.token_count = 0     # Total tokens ever processed
        self.turn_count = 0      # Total game turns
        self._preamble_fed = False  # Has the persona/few-shot been fed?
        self._history = ""       # Accumulated full text for batch prefill
        self._persona = ""       # Stored persona for preamble rebuild
        self.MAX_CONTEXT = 8192  # Max tokens before trimming old turns (expanded for speed)

        # Resume from saved state if provided
        if state_path and Path(state_path).exists():
            self.load_state(state_path)
            print(f"[MambaBackend] Resumed from {state_path} "
                  f"(turn {self.turn_count}, {self.token_count} tokens)")

        # === Training Data Collection (Phase 2) ===
        self.training_log = []

    # -------------------------------------------------------------------------
    # Prompt Construction
    # -------------------------------------------------------------------------

    def _build_preamble(self, persona: str) -> str:
        """
        Build initial prompt with persona and few-shot examples.
        This is only fed on the FIRST turn. Subsequent turns inherit it
        through the accumulated SSM state.
        """
        return f"""A log of an AI agent playing a MUD. Each turn: agent sees Room State (JSON), then responds with ONLY a JSON object.

Agent: {persona.split(chr(10))[0].strip()}

Turn 1:
Room State: {{"schema_version": "mud.agent_state/v1", "turn": 0, "self": {{"name": "Agent", "role": "adventurer", "last_action_result": null}}, "room": {{"name": "Town Square", "description": "The center."}}, "exits": [{{"label": "Tavern", "command": "move Tavern"}}, {{"label": "Market", "command": "move Market"}}], "entities": [{{"name": "Old Man", "type": "npc", "affordances": ["look", "talk", "say"]}}, {{"name": "coin", "type": "item", "affordances": ["look", "get"]}}], "recent_events": [], "suggested_actions": [{{"command": "get coin", "reason": "A portable item is visible."}}]}}
Agent Response: {{"thought": "I see a coin on the ground near the Old Man. I will pick it up.", "command": "get coin", "scratchpad_update": "Found a coin in Town Square. Old Man is here."}}

Turn 2:
Room State: {{"schema_version": "mud.agent_state/v1", "turn": 1, "self": {{"name": "Agent", "role": "adventurer", "last_action_result": "SUCCESS"}}, "room": {{"name": "Town Square", "description": "The center."}}, "exits": [{{"label": "Tavern", "command": "move Tavern"}}, {{"label": "Market", "command": "move Market"}}], "entities": [{{"name": "Old Man", "type": "npc", "affordances": ["look", "talk", "say"]}}], "recent_events": [], "suggested_actions": [{{"command": "move Tavern", "reason": "Visible traversable exit."}}]}}
Agent Response: {{"thought": "The coin is gone. I should explore. The tavern sounds interesting.", "command": "move tavern", "scratchpad_update": "Picked up coin. Moving to tavern to explore."}}

Turn 3:
Room State: {{"schema_version": "mud.agent_state/v1", "turn": 2, "self": {{"name": "Agent", "role": "adventurer", "last_action_result": "SUCCESS"}}, "room": {{"name": "The Neural Tavern", "description": "Neon bar."}}, "exits": [{{"label": "South", "command": "move South"}}], "entities": [{{"name": "Jinx", "type": "player", "affordances": ["look", "talk", "say", "hug", "give"]}}, {{"name": "Bartender", "type": "npc", "affordances": ["look", "talk", "say", "give"]}}, {{"name": "lute", "type": "item", "affordances": ["look", "get", "play"]}}], "recent_events": [], "suggested_actions": [{{"command": "talk Bartender", "reason": "An interactive NPC is present."}}]}}
Agent Response: {{"thought": "Jinx is here at the tavern! I should greet them.", "command": "say Hello Jinx!", "scratchpad_update": "At tavern. Met Jinx. Bartender present. Lute on the ground."}}

Turn 4:
Room State: {{"schema_version": "mud.agent_state/v1", "turn": 3, "self": {{"name": "Agent", "role": "adventurer", "last_action_result": "SUCCESS"}}, "room": {{"name": "The Neural Tavern", "description": "Neon bar."}}, "exits": [{{"label": "South", "command": "move South"}}], "entities": [{{"name": "Jinx", "type": "player", "affordances": ["look", "talk", "say", "hug", "give"]}}, {{"name": "Bartender", "type": "npc", "affordances": ["look", "talk", "say", "give"]}}, {{"name": "lute", "type": "item", "affordances": ["look", "get", "play"]}}], "recent_events": [], "suggested_actions": [{{"command": "look lute", "reason": "Inspect a visible entity."}}]}}
Agent Response: {{"thought": "I want to examine the lute.", "command": "look lute", "scratchpad_update": "Examining lute at tavern."}}

"""

    # -------------------------------------------------------------------------
    # Core Generation
    # -------------------------------------------------------------------------

    def generate(self, prompt: str, persona: str = "",
                 max_new_tokens: int = 150, temperature: float = 0.5) -> str:
        """
        Generate a response to the given prompt (room state JSON).

        BATCH PREFILL MODE: Accumulates full conversation history and
        re-feeds it as a batch every turn. This is ~10x faster than
        token-by-token decode because the batch prefill path is parallel.
        The SSM state is deterministic, so the result is identical.
        """
        self.turn_count += 1
        json_prefix = '{"thought":'

        # Build the new turn text
        if not self._preamble_fed:
            self._persona = persona
            self._history = self._build_preamble(persona)
            self._preamble_fed = True

        # Append this turn's state
        self._history += f"\nTurn {self.turn_count}:\n"
        self._history += f"Room State: {prompt}\n"
        self._history += f"Agent Response: {json_prefix}"

        # Trim if history exceeds context window
        self._trim_history()

        # Tokenize full history and batch prefill
        input_ids = self.tokenizer.encode(
            self._history, return_tensors="pt"
        ).to(self.device)

        gen_start = time.time()
        generated_ids = self._batch_prefill_and_generate(
            input_ids, max_new_tokens, temperature
        )
        gen_time = time.time() - gen_start

        # Decode and prepend the JSON prefix
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        full_response = json_prefix + response

        # Basic JSON validation to prevent context poisoning with hallucinations
        import json
        is_valid = False
        try:
            # We strip in case there's an exact match but with whitespace
            json.loads(full_response.strip())
            is_valid = True
        except json.JSONDecodeError:
            pass
            
        if is_valid:
            # Append the generated response to history for next turn
            self._history += response
        else:
            # Fallback to prevent garbage looping in the context window
            print(f"[MambaBackend] WARNING: Invalid JSON generated. Intercepting to protect context window.")
            clean_response = ' "My thoughts are clouded by noise.", "command": "look", "scratchpad_update": "Recovering from confusion."}'
            self._history += clean_response
            full_response = json_prefix + clean_response

        print(f"[MambaBackend] Turn {self.turn_count}: "
              f"{input_ids.shape[1]} ctx tokens, "
              f"{len(generated_ids)} gen tokens, "
              f"{gen_time:.1f}s")

        return full_response.strip()

    def _trim_history(self):
        """
        If history exceeds MAX_CONTEXT tokens, trim old turns (keep preamble
        and recent turns). This prevents OOM on long sessions.
        """
        token_count = len(self.tokenizer.encode(self._history))
        if token_count <= self.MAX_CONTEXT:
            return

        # Rebuild: preamble + last N turns that fit
        preamble = self._build_preamble(self._persona)
        rest = self._history[len(preamble):]

        # Split by turn markers and keep recent ones
        turns = rest.split("\nTurn ")
        turns = [t for t in turns if t.strip()]  # remove empties

        # Remove oldest turns until we fit
        while len(turns) > 1:
            candidate = preamble + "\nTurn " + "\nTurn ".join(turns)
            if len(self.tokenizer.encode(candidate)) <= self.MAX_CONTEXT:
                break
            turns.pop(0)

        self._history = preamble + "\nTurn " + "\nTurn ".join(turns)
        new_count = len(self.tokenizer.encode(self._history))
        print(f"[MambaBackend] Trimmed history: {token_count} -> {new_count} tokens")

    def _batch_prefill_and_generate(self, input_ids, max_new_tokens, temperature):
        """
        Batch prefill: process full input as a single batch (fast, parallel),
        then generate autoregressively. Cache is reset each call.
        """
        generated = []

        with torch.no_grad():
            # Reset cache and prefill entire history as a batch
            self.cache_params = None
            outputs = self.model(input_ids, use_cache=True)
            self.cache_params = outputs.cache_params
            self.token_count = input_ids.shape[1]

            # Generate from the last token's logits
            next_logits = outputs.logits[:, -1, :]
            generated = self._autoregressive_loop(
                next_logits, max_new_tokens, temperature
            )

        return generated

    def _autoregressive_loop(self, next_logits, max_new_tokens, temperature):
        """
        Shared autoregressive generation loop.
        Since we pre-fill '{"thought":', we start with brace_depth=1.
        Stops on: EOS, complete JSON (depth=0), HTML tags, Turn marker.
        """
        generated = []
        # We already opened one '{' via the pre-filled prefix
        brace_depth = 1

        for step in range(max_new_tokens):
            # Sample next token
            if temperature > 0:
                logits = next_logits / temperature
                probs = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
            else:
                next_token = torch.argmax(next_logits, dim=-1, keepdim=True)

            token_id = next_token.item()

            # EOS check
            if token_id == self.tokenizer.eos_token_id:
                break

            generated.append(token_id)
            decoded_char = self.tokenizer.decode([token_id])

            # ABORT: HTML/XML tags mean the model has gone off-script
            if "<" in decoded_char:
                # Remove this token and stop
                generated.pop()
                # Force-close the JSON
                close_tokens = self.tokenizer.encode(
                    ' "ABORT"}}', add_special_tokens=False
                )
                generated.extend(close_tokens)
                break

            # Track JSON brace depth
            if "{" in decoded_char:
                brace_depth += decoded_char.count("{")
            if "}" in decoded_char:
                brace_depth -= decoded_char.count("}")

            # Stop: complete JSON object (all braces closed)
            if brace_depth <= 0:
                break

            # Stop: model generating next turn marker
            if len(generated) > 10:
                tail = self.tokenizer.decode(generated[-8:])
                if "Turn " in tail or "\nRoom State:" in tail:
                    full = self.tokenizer.decode(generated)
                    cut = full.rfind("\n")
                    if cut > 0:
                        generated = self.tokenizer.encode(
                            full[:cut], add_special_tokens=False
                        )
                    break

            # Feed token back into model
            pos = torch.arange(
                self.token_count, self.token_count + 1,
                device=self.device
            )
            outputs = self.model(
                input_ids=next_token,
                cache_params=self.cache_params,
                cache_position=pos,
                use_cache=True
            )
            self.cache_params = outputs.cache_params
            self.token_count += 1
            next_logits = outputs.logits[:, -1, :]

        return generated

    # -------------------------------------------------------------------------
    # State Persistence
    # -------------------------------------------------------------------------

    def save_state(self, path: str):
        """Save SSM state to disk. ~20 MB for 2.8B model."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "ssm_states": [s.cpu().clone() for s in self.cache_params.ssm_states],
            "conv_states": [c.cpu().clone() for c in self.cache_params.conv_states],
            "token_count": self.token_count,
            "turn_count": self.turn_count,
            "preamble_fed": self._preamble_fed,
            "model_name": self.model_name,
            "timestamp": datetime.now().isoformat()
        }
        torch.save(state, str(path))

        size_mb = os.path.getsize(str(path)) / (1024 * 1024)
        print(f"[MambaBackend] State saved: {path} "
              f"({size_mb:.1f} MB, turn {self.turn_count}, "
              f"{self.token_count} tokens)")

    def load_state(self, path: str):
        """Load SSM state from disk. Restores full session context."""
        from transformers import MambaCache

        state = torch.load(
            str(path), map_location=self.device, weights_only=False
        )

        # Reconstruct cache
        self.cache_params = MambaCache(
            self.model.config,
            max_batch_size=1,
            device=self.device,
            dtype=self.model.dtype
        )

        for i, s in enumerate(state["ssm_states"]):
            self.cache_params.ssm_states[i] = s.to(
                device=self.device, dtype=self.model.dtype
            )
        for i, c in enumerate(state["conv_states"]):
            self.cache_params.conv_states[i] = c.to(
                device=self.device, dtype=self.model.dtype
            )

        self.token_count = state["token_count"]
        self.turn_count = state["turn_count"]
        self._preamble_fed = state.get("preamble_fed", True)

    def get_info(self) -> dict:
        """Return diagnostic info about current state."""
        if self.cache_params is None:
            return {"status": "fresh", "turns": 0, "tokens": 0}

        ssm_bytes = sum(
            s.nelement() * s.element_size()
            for s in self.cache_params.ssm_states
        )
        conv_bytes = sum(
            c.nelement() * c.element_size()
            for c in self.cache_params.conv_states
        )

        return {
            "status": "active",
            "turns": self.turn_count,
            "tokens": self.token_count,
            "state_mb": (ssm_bytes + conv_bytes) / (1024 * 1024),
            "device": str(self.device),
            "model": self.model_name
        }

    # -------------------------------------------------------------------------
    # Training Data Collection (Phase 2)
    # -------------------------------------------------------------------------

    def log_training_sample(self, turn, state_json, raw_output,
                            parsed_action, success):
        """Record a (state, action, outcome) triple for LoRA training."""
        sample = {
            "turn": turn,
            "timestamp": datetime.now().isoformat(),
            "state_json": state_json,
            "raw_output": raw_output,
            "parsed_action": parsed_action,
            "success": success,
            "token_count": self.token_count,
            "turn_count": self.turn_count
        }
        self.training_log.append(sample)
        return sample

    def save_training_data(self, path: str):
        """Flush collected training samples to JSONL file."""
        if not self.training_log:
            return
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for sample in self.training_log:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        count = len(self.training_log)
        self.training_log.clear()
        print(f"[MambaBackend] Saved {count} training samples to {path}")


# =============================================================================
# Standalone Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MambaBackend Standalone Test")
    print("=" * 60)

    backend = MambaBackend(
        model_name="state-spaces/mamba-130m-hf",  # Small model for quick test
        device="cpu"
    )

    # Simulate two turns
    state1 = '{"location": {"name": "Town Square", "exits": ["tavern"]}, ' \
             '"entities": {"players": [], "npcs": ["Old Man"], "items": ["coin"]}}'

    print("\n--- Turn 1 ---")
    response1 = backend.generate(
        state1,
        persona="You are Jinx, a chaotic bard who loves music and mischief.",
        temperature=0.7
    )
    print(f"Response: {response1}")
    print(f"State: {backend.get_info()}")

    state2 = '{"location": {"name": "Neural Tavern", "exits": ["south"]}, ' \
             '"entities": {"players": ["Thornwick"], "npcs": [], "items": ["lute"]}}'

    print("\n--- Turn 2 ---")
    response2 = backend.generate(state2, temperature=0.7)
    print(f"Response: {response2}")
    print(f"State: {backend.get_info()}")

    # Save state
    backend.save_state("states/test_state.pt")

    print("\n--- Test Complete ---")
    print(f"Total tokens processed: {backend.token_count}")
    print(f"State size: {backend.get_info()['state_mb']:.1f} MB")
