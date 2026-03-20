"""
server.py - Brain Microservice

FastAPI server that exposes the cognitive bridge as an HTTP endpoint.
Supports three modes:
    - mock:      Plumbing test, no models loaded
    - qwen:      Qwen instruct-only (legacy, for quick testing)
    - cognitive:  Full Mamba -> Hypernetwork -> LoRA -> Qwen base pipeline

The MUD agent wrapper (agent_wrapper.py) talks to this server.
The server talks to the models. Clean separation of concerns.

Author: Codex (original), Loom (cognitive mode)
Date: 2026-02-26
"""

import asyncio
import argparse
import logging
import os
import json
from typing import Any

import torch
from fastapi import FastAPI
from pydantic import BaseModel

from model_defaults import DEFAULT_MAMBA_MODEL_ID, DEFAULT_QWEN_MODEL_ID
from models import LoRAHypernetwork, MambaStateCompressor

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
except Exception:  # pragma: no cover
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None

try:
    from cognitive_bridge import CognitiveBridge, BridgeConfig
except Exception:
    CognitiveBridge = None
    BridgeConfig = None


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("BrainServer")

app = FastAPI()


class MUDEvent(BaseModel):
    player_id: str
    action: str
    context: str


# --- Globals ---
qwen_model = None
hypernetwork = None
compressor = None
tokenizer = None
device = None
active_mode = "mock"
hyper_device = None
cognitive_bridge = None  # NEW: the full pipeline
_bridge_lock = asyncio.Lock()  # Fix #2: serialize bridge access

# --- Runtime configuration ---
BRAIN_MODE = os.getenv("BRAIN_MODE", "mock").strip().lower()
QWEN_MODEL_ID = os.getenv("QWEN_MODEL_ID", DEFAULT_QWEN_MODEL_ID)
MAMBA_MODEL_ID = os.getenv("MAMBA_MODEL_ID", DEFAULT_MAMBA_MODEL_ID)
QWEN_MAX_NEW_TOKENS = int(os.getenv("QWEN_MAX_NEW_TOKENS", "220"))
QWEN_TEMPERATURE = float(os.getenv("QWEN_TEMPERATURE", "0.7"))
QWEN_TOP_P = float(os.getenv("QWEN_TOP_P", "0.90"))
QWEN_DO_SAMPLE = env_bool("QWEN_DO_SAMPLE", True)
QWEN_ENABLE_THINKING = env_bool("QWEN_ENABLE_THINKING", False)
TRUST_REMOTE_CODE = env_bool("TRUST_REMOTE_CODE", False)
ENABLE_HYPER_SCAFFOLD = env_bool("ENABLE_HYPER_SCAFFOLD", False)
HYPER_DEVICE = os.getenv("HYPER_DEVICE", "cpu").strip().lower()
USE_4BIT = env_bool("USE_4BIT", True)
BRAIN_BRIDGE_MODE = os.getenv("BRAIN_BRIDGE_MODE", "lora").strip().lower()
COGNITIVE_STARTUP_VALIDATION = env_bool("COGNITIVE_STARTUP_VALIDATION", True)
COGNITIVE_STARTUP_VALIDATION_TEXT = os.getenv(
    "COGNITIVE_STARTUP_VALIDATION_TEXT", "startup probe"
).strip()

# Hypernetwork dimensions
MAMBA_LAYERS = int(os.getenv("MAMBA_LAYERS", "64"))
MAMBA_D_MODEL = int(os.getenv("MAMBA_D_MODEL", "2560"))
MAMBA_D_STATE = int(os.getenv("MAMBA_D_STATE", "16"))
CONTEXT_DIM = int(os.getenv("CONTEXT_DIM", "2048"))
QWEN_TARGET_DIM = int(os.getenv("QWEN_TARGET_DIM", "2560"))
LORA_RANK = int(os.getenv("LORA_RANK", "8"))

SYSTEM_JSON_INSTRUCTION = (
    "You are a MUD action planner. Return exactly one JSON object with keys: "
    "thought, command, scratchpad_update. "
    "command must be a short valid MUD command. "
    "scratchpad_update must be either a short string or null. "
    "No markdown, no code fences, no extra text."
)


def apply_cli_overrides(args: argparse.Namespace) -> tuple[str, int]:
    global BRAIN_MODE, QWEN_MODEL_ID, MAMBA_MODEL_ID

    if args.brain_mode:
        BRAIN_MODE = args.brain_mode.strip().lower()
    if args.qwen_model_id:
        QWEN_MODEL_ID = args.qwen_model_id.strip()
    if args.mamba_model_id:
        MAMBA_MODEL_ID = args.mamba_model_id.strip()

    return args.host, args.port


@app.on_event("startup")
async def load_models():
    """Boot the brain in the configured mode."""
    global qwen_model, hypernetwork, compressor, tokenizer, device
    global active_mode, hyper_device, cognitive_bridge

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    active_mode = "mock"
    logger.info("Brain mode requested: %s", BRAIN_MODE)
    logger.info("Primary torch device: %s", device)

    if HYPER_DEVICE == "cuda" and not torch.cuda.is_available():
        logger.warning("HYPER_DEVICE=cuda but CUDA unavailable; falling back to cpu")
        hyper_device = torch.device("cpu")
    else:
        hyper_device = torch.device(HYPER_DEVICE)

    # --- COGNITIVE MODE ---
    if BRAIN_MODE == "cognitive":
        if CognitiveBridge is None:
            logger.error("cognitive_bridge.py not importable. Falling back to mock.")
            return

        config = BridgeConfig(
            qwen_model_id=QWEN_MODEL_ID,
            mamba_model_id=MAMBA_MODEL_ID,
            context_dim=CONTEXT_DIM,
            lora_rank=LORA_RANK,
            bridge_mode=BRAIN_BRIDGE_MODE,
            hyper_hidden_dim=1024,
            max_new_tokens=QWEN_MAX_NEW_TOKENS,
            temperature=QWEN_TEMPERATURE,
            top_p=QWEN_TOP_P,
            use_4bit=USE_4BIT,
            hyper_device=HYPER_DEVICE,
            startup_validation=COGNITIVE_STARTUP_VALIDATION,
            startup_validation_text=COGNITIVE_STARTUP_VALIDATION_TEXT,
        )

        cognitive_bridge = CognitiveBridge(config)
        try:
            cognitive_bridge.load_models()
            active_mode = "cognitive"
            logger.info("Cognitive mode active. Full pipeline loaded.")
        except Exception as exc:
            logger.exception("Failed to load cognitive bridge: %s", exc)
            cognitive_bridge = None
            logger.info("Falling back to mock mode.")
        return

    # --- LEGACY: Hypernetwork scaffold (geometry check only) ---
    if ENABLE_HYPER_SCAFFOLD:
        logger.info("Initializing hypernetwork scaffold on %s", hyper_device)
        compressor = MambaStateCompressor(
            MAMBA_LAYERS, MAMBA_D_MODEL, MAMBA_D_STATE, CONTEXT_DIM,
        ).to(hyper_device)
        hypernetwork = LoRAHypernetwork(
            context_dim=CONTEXT_DIM,
            target_dims=[(QWEN_TARGET_DIM, QWEN_TARGET_DIM)],
            lora_rank=LORA_RANK,
        ).to(hyper_device)
    else:
        logger.info("Hypernetwork scaffold disabled (ENABLE_HYPER_SCAFFOLD=0)")

    # --- QWEN INSTRUCT MODE ---
    if BRAIN_MODE != "qwen":
        logger.info("Running in mock mode. API ready.")
        return

    if AutoModelForCausalLM is None or AutoTokenizer is None or BitsAndBytesConfig is None:
        logger.error("transformers/bitsandbytes not importable; falling back to mock")
        return

    logger.info("Loading Qwen instruct model: %s", QWEN_MODEL_ID)
    try:
        model_kwargs: dict[str, Any] = {"device_map": "auto"}
        if torch.cuda.is_available():
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:
            model_kwargs["torch_dtype"] = torch.float32

        tokenizer = AutoTokenizer.from_pretrained(
            QWEN_MODEL_ID, use_fast=True, trust_remote_code=TRUST_REMOTE_CODE,
        )
        qwen_model = AutoModelForCausalLM.from_pretrained(
            QWEN_MODEL_ID, trust_remote_code=TRUST_REMOTE_CODE, **model_kwargs,
        )

        if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
            tokenizer.pad_token = tokenizer.eos_token

        active_mode = "qwen"
        logger.info("Qwen instruct loaded successfully. API ready.")
    except Exception as exc:
        logger.exception("Failed to load Qwen (%s). Falling back to mock mode.", exc)


def run_hyper_scaffold_once() -> None:
    """Optional geometry check for compressor/hypernetwork wiring."""
    if compressor is None or hypernetwork is None:
        return
    with torch.inference_mode():
        state = torch.randn(1, MAMBA_LAYERS, MAMBA_D_MODEL, MAMBA_D_STATE,
                            device=hyper_device)
        context_vector = compressor(state)
        lora_pairs = hypernetwork(context_vector)
        A, B = lora_pairs[0]
        logger.info("Scaffold LoRA A: %s | B: %s", tuple(A.shape), tuple(B.shape))


def generate_with_qwen(prompt: str) -> str:
    """Legacy: instruct-mode Qwen generation."""
    if qwen_model is None or tokenizer is None:
        raise RuntimeError("Qwen not initialized")

    model_device = next(qwen_model.parameters()).device
    prompt_text = prompt
    if hasattr(tokenizer, "apply_chat_template"):
        messages = [
            {"role": "system", "content": SYSTEM_JSON_INSTRUCTION},
            {"role": "user", "content": prompt},
        ]
        try:
            prompt_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=QWEN_ENABLE_THINKING,
            )
        except TypeError:
            prompt_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )

    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=4096)
    inputs = {key: value.to(model_device) for key, value in inputs.items()}

    with torch.inference_mode():
        generated = qwen_model.generate(
            **inputs,
            max_new_tokens=QWEN_MAX_NEW_TOKENS,
            temperature=QWEN_TEMPERATURE,
            top_p=QWEN_TOP_P,
            do_sample=QWEN_DO_SAMPLE,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    generated_tokens = generated[0][inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    return text or '{"thought":"Empty completion","command":"look","scratchpad_update":null}'


def force_json_response(text: str) -> str:
    """Ensure the server response is always a parseable JSON object string."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidate = text[start:end + 1]
        try:
            parsed = json.loads(candidate)
            normalized = {
                "thought": str(parsed.get("thought", "")),
                "command": str(parsed.get("command", "look")).strip() or "look",
                "scratchpad_update": parsed.get("scratchpad_update"),
            }
            if normalized["scratchpad_update"] is not None and not isinstance(
                normalized["scratchpad_update"], str
            ):
                normalized["scratchpad_update"] = str(normalized["scratchpad_update"])
            return json.dumps(normalized, ensure_ascii=False)
        except Exception:
            pass

    fallback = {
        "thought": (text[:280] if text else "Model returned empty output."),
        "command": "look",
        "scratchpad_update": None,
    }
    return json.dumps(fallback, ensure_ascii=False)


@app.get("/health")
async def healthcheck():
    info = {
        "status": "ok",
        "mode": active_mode,
        "device": str(device),
        "hyper_scaffold": ENABLE_HYPER_SCAFFOLD,
        "qwen_model_id": QWEN_MODEL_ID,
        "mamba_model_id": MAMBA_MODEL_ID,
        "cognitive_startup_validation": COGNITIVE_STARTUP_VALIDATION,
    }
    if cognitive_bridge is not None:
        info["bridge"] = cognitive_bridge.get_info()
    return info


@app.post("/generate")
async def generate_response(event: MUDEvent):
    logger.info("Request: player=%s action=%s mode=%s",
                event.player_id, event.action, active_mode)

    # --- COGNITIVE MODE (Fix #2: serialized via lock) ---
    if active_mode == "cognitive" and cognitive_bridge is not None:
        async with _bridge_lock:
            try:
                diag = cognitive_bridge.generate(event.context)
                return {
                    "status": "success",
                    "mode": "cognitive",
                    "response": diag.raw_output,
                    "diagnostics": {
                        "turn": diag.turn_number,
                        "mamba_state_mb": round(diag.mamba_state_mb, 2),
                        "context_norm": round(diag.context_vector_norm, 4),
                        "generation_time_s": round(diag.generation_time_s, 2),
                        "tokens_in": diag.input_tokens,
                        "tokens_out": diag.output_tokens,
                    },
                }
            except Exception as exc:
                logger.exception("Cognitive generation failed: %s", exc)
                return {
                    "status": "error",
                    "mode": "cognitive",
                    "error": str(exc),
                    "response": '{"thought":"Cognitive pipeline error","command":"look","scratchpad_update":null}',
                }

    # --- LEGACY MODES ---
    if ENABLE_HYPER_SCAFFOLD:
        run_hyper_scaffold_once()

    if active_mode == "qwen":
        response_text = force_json_response(generate_with_qwen(event.context))
    else:
        response_text = (
            '{"thought":"Brain server is in mock mode; using a safe exploration action.",'
            '"command":"look","scratchpad_update":null}'
        )

    return {
        "status": "success",
        "mode": active_mode,
        "response": response_text,
    }


@app.post("/save_state")
async def save_state():
    """Save the cognitive bridge state (Mamba SSM + hypernetwork weights)."""
    if cognitive_bridge is None:
        return {"status": "error", "message": "Not in cognitive mode"}
    async with _bridge_lock:
        path = cognitive_bridge.save_state()
    return {"status": "ok", "path": path}


@app.post("/load_state")
async def load_state(filename: str):
    """Load a saved cognitive state. Fix #1: filename only, no arbitrary paths."""
    if cognitive_bridge is None:
        return {"status": "error", "message": "Not in cognitive mode"}
    # Only accept a filename, not a path. The bridge validates it's within state_dir.
    from pathlib import Path
    safe_path = str(Path(cognitive_bridge.config.state_dir) / Path(filename).name)
    async with _bridge_lock:
        cognitive_bridge.load_state(safe_path)
    return {"status": "ok", "turn_count": cognitive_bridge.turn_count}


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the MoCoP brain server.")
    parser.add_argument("--brain-mode", type=str, default="")
    parser.add_argument("--qwen-model-id", type=str, default="")
    parser.add_argument("--mamba-model-id", type=str, default="")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    cli_args = parser.parse_args()
    host, port = apply_cli_overrides(cli_args)
    uvicorn.run(app, host=host, port=port, reload=False)
