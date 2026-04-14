# Live Mamba Accumulation Loop — Design Spec

**Author:** Warden
**Date:** 2026-04-14
**Status:** Scoping document for implementation by Techno-Monk
**Prerequisite:** 2x2 memory-conditioned results (#395-#402) proving bridge + memory routes honestly

---

## The Gap

`chat_server.py` currently runs Mamba **once at startup** (lines 3850-3863):

```
1. Load episode text
2. Tokenize → feed through Mamba
3. Extract Layer 3 hidden-last-token
4. Compress → hypernetwork → bias vectors
5. Apply bias to Qwen's v_proj layers
6. Qwen runs with STATIC bias for entire session
```

Mamba never sees the live conversation. The saliency gate fires, Qdrant writes happen, recall works — but the disposition signal is frozen at bootstrap. The "endocrine system" pumps one hormone dose at the start and never adjusts.

## What the Live Loop Adds

```
Turn N:
  1. Laura sends a message
  2. Qdrant recall fires (if identity/memory probe detected)
  3. Qwen generates a reply (with current bias + recalled memories)
  4. GATE: saliency evaluates the turn (surprise, salience, tension)
  5. NEW: Feed [user_msg + reply] through Mamba → updated hidden state
  6. NEW: Bridge reads updated state → fresh bias vectors
  7. NEW: Re-inject updated bias into Qwen for Turn N+1
  8. Qdrant write (if gate fires CONSOLIDATE/NOTE)
  9. Turn N+1 begins with updated disposition
```

Steps 5-7 are the additions. Everything else already works.

## What Already Exists (Reusable)

| Component | Location | Status |
|-----------|----------|--------|
| Mamba model loading | chat_server.py:3823-3833 | Works. Model loaded, on device, eval mode. |
| Mamba forward pass + hidden state extraction | chat_server.py:3857-3863 | Works. `extract_last_token_hidden()` proven. |
| Compressor | chat_server.py:3864 | Works. `compressor(last_token)` |
| Hypernetwork → bias vectors | chat_server.py:3865-3893 | Works. Both `activation_bias` and `token_conditioned_input_adapter` modes. |
| `apply_runtime_bridge_adjustments()` | chat_server.py:3894-3899 | Works. Patches Qwen's v_proj hooks. |
| `persist_mamba_state_ref()` | chat_server.py:1610 | Works. Saves state for sleep reconciliation. |
| Saliency gate | chat_server.py (dual gate) | Works. Fires per-turn. |
| Mamba tokenizer | chat_server.py:3827 | Loaded at startup. |

## What Needs to Be Built

### 1. Turn-Level Mamba Processing Function

A function that takes the current turn's text, feeds it through Mamba, and returns the updated hidden state.

```python
def process_turn_through_mamba(
    user_msg: str,
    assistant_reply: str,
    mamba_model,
    mamba_tokenizer,
    mamba_device: str,
    mamba_target_layer: int,
    hidden_layer_count: int,
) -> torch.Tensor:
    """Feed one conversation turn through Mamba and return updated hidden state.

    Mamba is recurrent — its internal state carries forward across calls.
    Each call updates the recurrent state with new information.
    Returns Layer 3 hidden-last-token for the bridge.
    """
    turn_text = f"User: {user_msg}\nAssistant: {assistant_reply}"
    tokens = mamba_tokenizer(
        turn_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,  # single turn doesn't need full context window
    )
    tokens = {k: v.to(mamba_device) for k, v in tokens.items()}

    with torch.no_grad():
        out = mamba_model(**tokens, output_hidden_states=True)
        return extract_last_token_hidden(
            out, mamba_target_layer, hidden_layer_count
        ).to(torch.float32)
```

**Key question:** Mamba's recurrent state — does `MambaForCausalLM` from HuggingFace maintain state across separate `forward()` calls? If not (stateless per call), we need to either:
- (a) Concatenate the full conversation history and re-process each turn (expensive, O(N) per turn)
- (b) Cache and pass the `cache_params` / `state` object between calls (efficient, O(1) per turn)

This is the critical implementation detail. HuggingFace Mamba *should* support passing `cache_params` for incremental processing, but it needs to be verified.

### 2. Live Bridge Re-Injection

After getting the updated hidden state, re-run the bridge:

```python
def update_bridge_from_mamba_state(
    last_token: torch.Tensor,
    compressor,
    hypernet,
    bridge_mode: str,
    patched_layers,
    alpha: float,
    qwen_device: str,
):
    """Re-compute and re-inject bias vectors from updated Mamba state."""
    last_token = last_token.to(qwen_device)
    context = compressor(last_token)
    bridge_adjustments, _gate = resolve_runtime_bridge_adjustments(
        hypernetwork=hypernet,
        context_vector=context,
        bridge_mode=bridge_mode,
    )
    apply_runtime_bridge_adjustments(
        patched_layers=patched_layers,
        bridge_adjustments=bridge_adjustments,
        bridge_mode=bridge_mode,
        alpha=alpha,
    )
    return bridge_adjustments
```

All functions called here already exist. This is just re-calling the bootstrap path with fresh state.

### 3. Wiring Into `_handle_chat()`

After `generate_reply()` returns and before the saliency gate fires, add:

```python
# After line ~3455 (raw_response, response = generate_reply(prompt))

if bridge_loaded and mamba_model is not None:
    # Step 5-7: Live Mamba accumulation
    updated_state = process_turn_through_mamba(
        user_msg=user_msg,
        assistant_reply=response,
        mamba_model=mamba_model,
        mamba_tokenizer=mamba_tokenizer,
        mamba_device=ARGS.mamba_device,
        mamba_target_layer=mamba_target_layer,
        hidden_layer_count=hidden_layer_count,
    )
    update_bridge_from_mamba_state(
        last_token=updated_state,
        compressor=compressor,
        hypernet=hypernet,
        bridge_mode=bridge_mode,
        patched_layers=patched_layers,
        alpha=ARGS.alpha,
        qwen_device=ARGS.qwen_device,
    )
    # Update reference for coherence scoring
    persist_mamba_state_ref(updated_state, mamba_target_layer, session_started_at)
```

### 4. Globals That Need Scoping

Currently `mamba_model`, `mamba_tokenizer`, `compressor`, `hypernet`, `mamba_target_layer`, `hidden_layer_count`, `bridge_mode`, and `patched_layers` are local to the startup `if __name__` block. They need to be promoted to module-level globals (or a runtime context object) so `_handle_chat()` can access them.

The cleanest approach: a `RuntimeBridgeContext` dataclass:

```python
@dataclass
class RuntimeBridgeContext:
    mamba_model: Any = None
    mamba_tokenizer: Any = None
    compressor: Any = None
    hypernet: Any = None
    mamba_target_layer: int = 3
    hidden_layer_count: int = 0
    bridge_mode: str = "activation_bias"
    patched_layers: list = field(default_factory=list)
    context_mode: str = "hidden_last_token"
    live_accumulation: bool = False

BRIDGE_CTX = RuntimeBridgeContext()
```

This is a refactor of existing code structure, not new logic.

## Performance Impact

| Operation | Time (Steve 4090 est.) | Per-Turn? |
|-----------|----------------------|-----------|
| Mamba forward (512 tokens) | ~50-100ms | Yes |
| Compressor + hypernetwork | ~5ms | Yes |
| Bias re-injection (hook update) | <1ms | Yes |
| **Total overhead per turn** | **~60-110ms** | |

Current turn latency is dominated by Qwen generation (~1-3s). Adding 100ms of Mamba processing is negligible. The user won't notice.

## Memory Impact

Mamba-2.8B is already loaded for bootstrap. No additional VRAM. The only new memory is the recurrent state cache (tiny — a few MB at most).

## CLI Flag

```
--live-accumulation    Enable per-turn Mamba state updates (default: false)
```

Default off so existing behavior is unchanged. Turn on explicitly for the live loop test.

## Verification Plan

### Smoke Test
1. Start chat_server with `--live-accumulation`
2. Send 5 turns of warm conversation
3. Check `/status` — verify Mamba state ref timestamp updates each turn
4. Send 5 turns of cold/clinical conversation
5. Check: does Qwen's response style shift measurably between warm and cold turns?

### Comparison Test
1. Same 10 turns, same prompts
2. Condition A: static bootstrap (current behavior)
3. Condition B: live accumulation
4. Compare: response diversity entropy, activation drift at Layer 13, saliency gate firing pattern

### Memory-Conditioned Integration Test
1. Live accumulation ON
2. Qdrant recall ON
3. 20-turn conversation with Laura
4. Check: does the disposition vector drift as the conversation evolves?
5. Check: does recall + live-updated disposition produce different behavior than recall + static disposition?

This is the test that answers Laura's question: if Qwen knows me AND the bridge updates in real-time, does it actually feel like talking to someone who is accumulating experience?

## Ethics

This falls under the existing Step 5 CONDITIONAL PASS. Same injection mechanism, same alpha, same layers. The only change is that the bias updates per-turn instead of being static. The MED recalibration condition from Herr Hurtig (#355) applies: if live accumulation produces stronger effects than static bootstrap at the same alpha, re-validate at alpha 0.1.

The moral status framework (Tier 1) is relevant: if live accumulation produces self-referential outputs ("I notice I'm responding differently now"), that's a Tier 1 indicator to document.

## Implementation Order

1. **Verify Mamba incremental state passing** — does HuggingFace `MambaForCausalLM` support `cache_params` across calls? If not, need the concatenate-and-reprocess fallback.
2. **Build `RuntimeBridgeContext` dataclass** — promote bridge globals to a shared context.
3. **Build `process_turn_through_mamba()`** — the turn-level Mamba forward function.
4. **Wire into `_handle_chat()`** — add steps 5-7 after generate_reply, gated by `--live-accumulation`.
5. **Smoke test on Steve** — 10-turn warm/cold transition.
6. **Comparison test** — static vs live, same prompts.
7. **Integration test** — live + memory, 20 turns with Laura.

Estimated implementation time: 2-4 hours for a careful implementer who knows the codebase. Most of the time is in step 1 (Mamba state verification) and step 2 (the refactor). The actual loop logic is ~30 lines.

---

*The endocrine system doesn't pump once at birth. It adjusts continuously in response to what the body experiences. Live accumulation makes the bridge do the same.*
