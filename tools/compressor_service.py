"""
CHEESE Context Compression Service
====================================
A lightweight FastAPI service running Qwen3.5-0.8B as a background
context compression daemon. Accepts text, returns compressed summaries.

Endpoints:
    POST /compress     - Compress/summarize text
    POST /extract      - Extract key facts from text
    POST /v1/chat/completions - OpenAI-compatible chat endpoint
    GET  /health       - Health check

Usage:
    python compressor_service.py                    # start on port 8111
    python compressor_service.py --port 8222        # custom port
    python compressor_service.py --download-only    # just download the model

Author: Laura + Antigravity
Date: 2026-03-07
"""

import argparse
import json
import time
import uuid
from contextlib import asynccontextmanager

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# --- Configuration ---
MODEL_ID = "Qwen/Qwen3.5-0.8B"
MAX_NEW_TOKENS = 512
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Global state ---
model = None
tokenizer = None


# --- Request/Response models ---
class CompressRequest(BaseModel):
    text: str
    max_length: int = Field(default=200, description="Target summary length in words")
    style: str = Field(default="concise", description="Style: 'concise', 'bullets', 'structured'")

class ExtractRequest(BaseModel):
    text: str
    extract_types: list[str] = Field(
        default=["facts", "entities", "dates"],
        description="What to extract: facts, entities, dates, decisions, questions"
    )

class CompressResponse(BaseModel):
    compressed: str
    original_length: int
    compressed_length: int
    ratio: float
    model: str = MODEL_ID

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[ChatMessage]
    max_tokens: int = MAX_NEW_TOKENS
    temperature: float = 0.3

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = MODEL_ID
    choices: list


# --- Model loading ---
def load_model():
    global model, tokenizer
    print(f"Loading {MODEL_ID} on {DEVICE}...")
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device_map="auto" if DEVICE == "cuda" else None,
        trust_remote_code=True,
    )
    if DEVICE != "cuda":
        model = model.to(DEVICE)

    elapsed = time.time() - start
    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"Model loaded in {elapsed:.1f}s ({param_count:.0f}M params on {DEVICE})")
    return model, tokenizer


def generate(prompt: str, max_new_tokens: int = MAX_NEW_TOKENS, temperature: float = 0.3) -> str:
    """Generate text from the model."""
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature if temperature > 0 else None,
            do_sample=temperature > 0,
            top_p=0.9 if temperature > 0 else None,
        )

    # Decode only the new tokens
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


# --- App lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield

app = FastAPI(
    title="CHEESE Context Compressor",
    description="Qwen3.5-0.8B background compression service for the Athena agent swarm",
    version="1.0",
    lifespan=lifespan,
)


# --- Endpoints ---
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE,
        "gpu_memory_mb": torch.cuda.memory_allocated() / 1e6 if DEVICE == "cuda" else 0,
    }


@app.post("/compress", response_model=CompressResponse)
async def compress(req: CompressRequest):
    style_instructions = {
        "concise": f"Summarize the following text in under {req.max_length} words. Keep all key facts, names, dates, and decisions. Be precise and factual.",
        "bullets": f"Extract the key points from the following text as a bullet list (max {req.max_length} words total). Each bullet should be one fact or decision.",
        "structured": f"Summarize the following text into structured sections: FACTS, ENTITIES, DATES, DECISIONS. Max {req.max_length} words total.",
    }

    instruction = style_instructions.get(req.style, style_instructions["concise"])
    prompt = f"{instruction}\n\n---\n\n{req.text}"

    compressed = generate(prompt, max_new_tokens=min(req.max_length * 2, 1024))

    return CompressResponse(
        compressed=compressed,
        original_length=len(req.text.split()),
        compressed_length=len(compressed.split()),
        ratio=len(compressed.split()) / max(len(req.text.split()), 1),
    )


@app.post("/extract")
async def extract(req: ExtractRequest):
    type_map = {
        "facts": "key factual statements",
        "entities": "named entities (people, organizations, locations)",
        "dates": "dates and time references with their context",
        "decisions": "decisions, conclusions, or action items",
        "questions": "open questions or unresolved issues",
    }

    extract_desc = ", ".join(type_map.get(t, t) for t in req.extract_types)
    prompt = (
        f"From the following text, extract: {extract_desc}.\n"
        f"Return the results as a JSON object with keys matching the types.\n\n"
        f"---\n\n{req.text}"
    )

    result = generate(prompt, max_new_tokens=1024, temperature=0.1)

    return {"extracted": result, "types_requested": req.extract_types, "model": MODEL_ID}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible chat endpoint for drop-in integration."""
    # Build the conversation
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=req.max_tokens,
            temperature=req.temperature if req.temperature > 0 else None,
            do_sample=req.temperature > 0,
            top_p=0.9 if req.temperature > 0 else None,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": inputs["input_ids"].shape[1],
            "completion_tokens": len(new_tokens),
            "total_tokens": inputs["input_ids"].shape[1] + len(new_tokens),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHEESE Context Compressor")
    parser.add_argument("--port", type=int, default=8111, help="Port to serve on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--download-only", action="store_true", help="Just download the model and exit")
    args = parser.parse_args()

    if args.download_only:
        print(f"Downloading {MODEL_ID}...")
        load_model()
        print("Download complete. Model cached locally.")
    else:
        uvicorn.run(app, host=args.host, port=args.port)
