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
        return f"""The following is a log of an AI agent playing a text MUD game.
The agent receives room state as JSON and responds with a JSON action.

Agent Persona:
{persona}

Example Turn:
Room State: {{"location": {{"name": "Town Square", "exits": ["tavern", "market"]}}, "entities": {{"players": [], "npcs": ["Old Man"], "items": ["coin"]}}}}
Agent Response: {{"thought": "I see a coin and an Old Man. Let me pick up the coin.", "command": "get coin", "scratchpad_update": "Found coin in Town Square"}}

Example Turn:
Room State: {{"location": {{"name": "The Neural Tavern", "exits": ["south"]}}, "entities": {{"players": ["Thornwick"], "npcs": [], "items": ["lute"]}}}}
Agent Response: {{"thought": "Thornwick is here! I should say hello.", "command": "say Hello Thornwick! Care for a song?", "scratchpad_update": "Met Thornwick at tavern"}}

Now the actual game begins.

"""

    # -------------------------------------------------------------------------
    # Core Generation
    # -------------------------------------------------------------------------

    def generate(self, prompt: str, persona: str = "",
                 max_new_tokens: int = 300, temperature: float = 0.7) -> str:
        """
        Generate a response to the given prompt (room state JSON).

        On the first turn, feeds the full preamble (persona + few-shot).
        On subsequent turns, only feeds the new room state, building on
        the accumulated SSM state. The persona is "in memory."
        """
        self.turn_count += 1

        # Build the text to feed
        if not self._preamble_fed:
            # First turn: preamble + few-shot + current state
            text = self._build_preamble(persona)
            text += f"Turn {self.turn_count}:\n"
            text += f"Room State: {prompt}\n"
            text += "Agent Response:"
        else:
            # Subsequent turns: just the new state (SSM remembers the rest)
            text = f"\n\nTurn {self.turn_count}:\n"
            text += f"Room State: {prompt}\n"
            text += "Agent Response:"

        # Tokenize
        input_ids = self.tokenizer.encode(text, return_tensors="pt").to(self.device)

        # Feed input and generate
        if not self._preamble_fed:
            # First turn: batch prefill (fast, processes all tokens at once)
            generated_ids = self._prefill_and_generate(
                input_ids, max_new_tokens, temperature
            )
            self._preamble_fed = True
        else:
            # Subsequent turns: feed tokens one-by-one, then generate
            generated_ids = self._decode_and_generate(
                input_ids, max_new_tokens, temperature
            )

        # Decode the generated tokens
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        return response.strip()

    def _prefill_and_generate(self, input_ids, max_new_tokens, temperature):
        """
        First-turn generation: process full input as a batch (prefill mode),
        then generate autoregressively.
        """
        generated = []

        with torch.no_grad():
            # Phase 1: Prefill - process entire input at once
            # When cache_params is None, model creates fresh cache and
            # processes full sequence in prefill mode
            outputs = self.model(input_ids, use_cache=True)
            self.cache_params = outputs.cache_params
            self.token_count = input_ids.shape[1]

            # Phase 2: Generate from the last token's logits
            next_logits = outputs.logits[:, -1, :]
            generated = self._autoregressive_loop(
                next_logits, max_new_tokens, temperature
            )

        return generated

    def _decode_and_generate(self, input_ids, max_new_tokens, temperature):
        """
        Subsequent-turn generation: feed new tokens one-by-one into existing
        cache (decode mode), then generate autoregressively.

        Note: Mamba's slow_forward only handles single tokens in decode mode.
        This is ~2ms/token on CUDA, ~50ms/token on CPU.
        """
        generated = []

        with torch.no_grad():
            # Phase 1: Feed new input tokens one at a time
            seq_len = input_ids.shape[1]
            for i in range(seq_len):
                token = input_ids[:, i:i+1]
                pos = torch.arange(
                    self.token_count, self.token_count + 1,
                    device=self.device
                )
                outputs = self.model(
                    input_ids=token,
                    cache_params=self.cache_params,
                    cache_position=pos,
                    use_cache=True
                )
                self.cache_params = outputs.cache_params
                self.token_count += 1

            # Phase 2: Generate from the last fed token's logits
            next_logits = outputs.logits[:, -1, :]
            generated = self._autoregressive_loop(
                next_logits, max_new_tokens, temperature
            )

        return generated

    def _autoregressive_loop(self, next_logits, max_new_tokens, temperature):
        """
        Shared autoregressive generation loop.
        Stops on: EOS, complete JSON object, Turn marker, or max tokens.
        """
        generated = []
        brace_depth = 0
        json_started = False

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

            # Track JSON brace depth for smart stopping
            decoded_char = self.tokenizer.decode([token_id])
            if "{" in decoded_char:
                json_started = True
                brace_depth += decoded_char.count("{")
            if "}" in decoded_char:
                brace_depth -= decoded_char.count("}")

            # Stop: complete JSON object found
            if json_started and brace_depth <= 0:
                break

            # Stop: model is generating the next turn marker
            if len(generated) > 10:
                tail = self.tokenizer.decode(generated[-8:])
                if "Turn " in tail or "\nRoom State:" in tail:
                    # Trim the marker from output
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
            batch_size=1,
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
