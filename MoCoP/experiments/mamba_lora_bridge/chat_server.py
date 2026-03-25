"""
chat_server.py - Browser chat for the 1.5B reincarnation probe.

Runs a minimal HTTP server. The bridge is injected once at startup,
then Laura can talk to the model from a browser on the LAN.
"""

import argparse
import hashlib
import json
import math
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from mamba_runtime_compat import ensure_mamba_ssm_compat
from models import ActivationBiasHypernetwork, DynamicLoRALinear, MambaStateCompressor


DEFAULT_BRIDGE = "cheese_reincarnation_bridge_1.5b_codexfix.pt"
DEFAULT_QWEN = "Qwen/Qwen2.5-1.5B"
DEFAULT_MAMBA = "state-spaces/mamba-2.8b-hf"
DEFAULT_EPISODES_FILE = "CHEESE_SHAPING_EPISODES.md"
DEFAULT_TARGET_SPECS = [(12, "v_proj"), (13, "v_proj"), (14, "v_proj"), (15, "v_proj")]
DEFAULT_USER_LABEL = "Laura"
DEFAULT_MODEL_LABEL = "Reply"

MODEL = None
TOKENIZER = None
CONVERSATION = []
ARGS = None
LATEST_TRANSCRIPT_PATH = None
LATEST_JSONL_PATH = None
DUAL_GATE_LOG_PATH = None
DUAL_GATE_MEMORY_PATH = None
DUAL_GATE_SURPRISE_PATH = None
QDRANT_PENDING_PATH = None
SERVER = None
CHAT_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()
ACTIVATION_RECORDER = None
LAST_CONVERSATION_SNAPSHOT = None
DUAL_GATE_EVENTS = []
QDRANT_GATE_SINK = None
QDRANT_GATE_SINK_ERROR = None
BOOTSTRAP_QWEN_BIAS_DIRECTION = None
BOOTSTRAP_QWEN_HIDDEN_REFERENCE = None
MAMBA_STATE_REF_PATH = None
RUNTIME_STATE = {
    "started_at": None,
    "started_monotonic": None,
    "running": False,
    "bridge_loaded": False,
    "busy": False,
    "stop_requested": False,
    "last_error": "",
    "disposition": "",
    "dual_gate_enabled": False,
    "memory_count": 0,
    "qdrant_count": 0,
    "surprise_count": 0,
    "tension_count": 0,
    "qdrant_synced_count": 0,
    "qdrant_queued_count": 0,
    "qdrant_write_failures": 0,
    "last_qdrant_id": "",
    "last_qdrant_error": "",
    "qdrant_write_mode": "direct",
    "mamba_state_ref": "",
    "mamba_state_source": "",
    "mamba_target_layer": None,
    "last_gate": {},
    "target_layers": [],
    "target_layers_overridden": False,
}

HTML_PAGE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reincarnated Qwen</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
  #header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  #header-main { font-size: 14px; color: #8b8b8b; }
  #header-main span { color: #c4956a; font-weight: bold; }
  #status-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  #status-pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 999px; border: 1px solid #31415f; background: #0f1730; font-size: 12px; color: #d9def0; }
  #status-dot { width: 10px; height: 10px; border-radius: 999px; background: #d45d5d; box-shadow: 0 0 0 3px rgba(212, 93, 93, 0.18); }
  #status-dot.online { background: #57cf77; box-shadow: 0 0 0 3px rgba(87, 207, 119, 0.18); }
  #status-dot.offline { background: #d45d5d; box-shadow: 0 0 0 3px rgba(212, 93, 93, 0.18); }
  #status-meta { font-size: 12px; color: #8b8b8b; }
  #chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 15px; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }
  .human { align-self: flex-end; background: #c4956a; color: #1a1a2e; border-bottom-right-radius: 4px; }
  .ai { align-self: flex-start; background: #2a2a4a; border-bottom-left-radius: 4px; }
  .system { align-self: center; color: #666; font-size: 12px; font-style: italic; }
  #input-area { padding: 12px; background: #16213e; border-top: 1px solid #333; display: flex; gap: 8px; }
  #msg { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #444; background: #1a1a2e; color: #e0e0e0; font-size: 15px; outline: none; }
  #msg:focus { border-color: #c4956a; }
  #send { padding: 10px 20px; border-radius: 8px; border: none; background: #c4956a; color: #1a1a2e; font-weight: bold; font-size: 15px; cursor: pointer; }
  #send:disabled { opacity: 0.5; }
  #stop { padding: 8px 12px; border-radius: 8px; border: 1px solid #7d3434; background: #331818; color: #f5c7c7; font-weight: bold; font-size: 13px; cursor: pointer; }
  #stop:disabled { opacity: 0.5; cursor: default; }
  #thinking { display: none; align-self: flex-start; color: #c4956a; font-size: 13px; padding: 8px 14px; }
  #thinking.active { display: block; }
</style>
</head><body>
<div id="header">
  <div id="header-main">Reincarnated Qwen 1.5B | <span>The Rabbit Hole of Subjectivity</span></div>
  <div id="status-bar">
    <div id="status-pill">
      <span id="status-dot" class="offline"></span>
      <span id="status-text">checking...</span>
    </div>
    <div id="status-meta"></div>
    <button id="stop" onclick="stopServer()">Stop</button>
  </div>
</div>
<div id="chat"></div>
<div id="thinking" class="msg system">thinking...</div>
<div id="input-area">
  <input id="msg" type="text" placeholder="Say something..." autocomplete="off">
  <button id="send" onclick="send()">Send</button>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('msg');
const btn = document.getElementById('send');
const stopBtn = document.getElementById('stop');
const thinking = document.getElementById('thinking');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const statusMeta = document.getElementById('status-meta');

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function setControlsDisabled(disabled) {
  input.disabled = disabled;
  btn.disabled = disabled;
}

function renderStatus(data) {
  const healthy = Boolean(data && data.running && !data.stop_requested);
  statusDot.className = healthy ? 'online' : 'offline';
  statusText.textContent = healthy ? (data.busy ? 'active | busy' : 'active') : (data && data.stop_requested ? 'stopping' : 'offline');

  if (data) {
    const alpha = Number(data.alpha ?? 0).toFixed(1);
    const turns = data.turns ?? 0;
    const memories = data.memory_count ?? 0;
    const qdrant = data.qdrant_count ?? 0;
    const qqueued = data.qdrant_queued_count ?? 0;
    const qmode = data.qdrant_write_mode || 'direct';
    const surprises = data.surprise_count ?? 0;
    const tensions = data.tension_count ?? 0;
    const lastDecision = data.last_gate?.decision || '-';
    const modelLabel = data.model_id || 'unknown-model';
    statusMeta.textContent = modelLabel + ' | alpha ' + alpha + ' | turns ' + turns + ' | mem ' + memories + ' | qdr ' + qdrant + ' | qqueued ' + qqueued + ' | qmode ' + qmode + ' | surp ' + surprises + ' | tens ' + tensions + ' | last ' + lastDecision;
  } else {
    statusMeta.textContent = 'server unreachable';
  }

  setControlsDisabled(!healthy);
  stopBtn.disabled = !(data && data.running) || Boolean(data && data.stop_requested);
}

async function refreshStatus() {
  try {
    const res = await fetch('/status', {cache: 'no-store'});
    if (!res.ok) throw new Error('status ' + res.status);
    renderStatus(await res.json());
  } catch (e) {
    renderStatus(null);
  }
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  addMsg(text, 'human');
  input.value = '';
  btn.disabled = true;
  thinking.classList.add('active');
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    addMsg((data.response || '...').trim() || '...', 'ai');
  } catch(e) {
    addMsg('Error: ' + e.message, 'system');
  }
  thinking.classList.remove('active');
  btn.disabled = input.disabled;
  input.focus();
}

async function stopServer() {
  if (stopBtn.disabled) return;
  if (!window.confirm('Stop the Steve chat server on this PC?')) return;

  statusDot.className = 'offline';
  statusText.textContent = 'stopping';
  statusMeta.textContent = 'shutdown requested';
  setControlsDisabled(true);
  stopBtn.disabled = true;

  try {
    await fetch('/stop', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({reason: 'ui-stop'})
    });
    addMsg('Stop requested. Server is shutting down.', 'system');
  } catch (e) {
    addMsg('Stop requested. The server closed before it could answer.', 'system');
  }

  window.setTimeout(refreshStatus, 1200);
}

input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
addMsg('Bridge loaded. Disposition: The Rabbit Hole of Subjectivity. Say hello.', 'system');
refreshStatus();
window.setInterval(refreshStatus, 3000);
input.focus();
</script>
</body></html>"""


def normalize_target_specs(raw):
    if not raw:
        return DEFAULT_TARGET_SPECS

    specs = []
    for item in raw:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            specs.append((int(item[0]), str(item[1]).strip()))
        else:
            specs.append((int(item), "v_proj"))
    return specs


def parse_target_layers(raw: Optional[str]):
    if raw is None or not raw.strip():
        return None

    specs = []
    for piece in raw.split(","):
        part = piece.strip()
        if not part:
            continue
        if ":" in part:
            layer_text, proj_name = part.split(":", 1)
            specs.append((int(layer_text), proj_name.strip()))
        else:
            specs.append((int(part), "v_proj"))
    return specs or None


def format_target_specs(specs):
    return [f"{layer_idx}:{proj_name}" for layer_idx, proj_name in specs]


def normalize_qwen_family(model_id: str) -> str:
    cleaned = (model_id or "").strip().lower()
    if cleaned.endswith("-instruct"):
        cleaned = cleaned[: -len("-instruct")]
    return cleaned


def is_same_qwen_family(requested_model_id: str, checkpoint_model_id: str) -> bool:
    return normalize_qwen_family(requested_model_id) == normalize_qwen_family(checkpoint_model_id)


def infer_hidden_layer_count(model) -> int:
    config_layers = int(getattr(model.config, "num_hidden_layers", 0) or 0)
    if config_layers > 0:
        return config_layers
    if hasattr(model, "backbone") and hasattr(model.backbone, "layers"):
        return len(model.backbone.layers)
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return len(model.model.layers)
    raise RuntimeError("Could not infer Mamba hidden layer count.")


def extract_last_token_hidden(outputs, layer_idx: int, expected_layers: int) -> torch.Tensor:
    hidden_states = getattr(outputs, "hidden_states", None)
    if not hidden_states:
        raise RuntimeError("Mamba did not return hidden_states.")

    if len(hidden_states) == expected_layers + 1:
        hidden_index = layer_idx + 1
    elif len(hidden_states) == expected_layers:
        hidden_index = layer_idx
    else:
        raise RuntimeError(
            "Unexpected hidden_states layout: "
            f"tuple_len={len(hidden_states)} expected_layers={expected_layers}"
        )
    return hidden_states[hidden_index][:, -1, :]


class ActivationRecorder:
    """Capture last-token hidden states on the target Qwen layers."""

    def __init__(self, model, target_layers):
        self.model = model
        self.target_layers = list(target_layers)
        self.hooks = []
        self.current_states = {}
        self._install_hooks()

    def _install_hooks(self):
        for layer_idx in self.target_layers:
            layer = self.model.model.layers[layer_idx]
            hook = layer.register_forward_hook(self._make_hook(layer_idx))
            self.hooks.append(hook)

    def _make_hook(self, layer_idx: int):
        def hook_fn(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            self.current_states[layer_idx] = hidden[:, -1, :].detach().cpu()

        return hook_fn

    def get_snapshot(self):
        return {layer_idx: state.clone() for layer_idx, state in self.current_states.items()}

    def cleanup(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()


def build_transcript(turns=None):
    active_turns = CONVERSATION if turns is None else turns
    return "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in active_turns)


def record_activation_snapshot(prompt_text: str):
    if ACTIVATION_RECORDER is None:
        return {}

    text = (prompt_text or "").strip() or ARGS.neutral_prompt
    inputs = TOKENIZER(text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)
    with torch.no_grad():
        MODEL(input_ids=input_ids, attention_mask=attention_mask)
    return ACTIVATION_RECORDER.get_snapshot()


def compute_response_diversity(prompt_text: str):
    inputs = TOKENIZER(prompt_text, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)
    with torch.no_grad():
        outputs = MODEL(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits[:, -1, :].float()
        probs = F.softmax(logits, dim=-1)
        log_probs = torch.log(probs + 1e-10)
        entropy = -(probs * log_probs).sum(dim=-1).item()
        top10_probs, _ = probs.topk(10, dim=-1)
        top10_mass = top10_probs.sum(dim=-1).item()
        top1_prob = probs.max(dim=-1).values.item()
        effective_vocab = math.exp(entropy)

    return {
        "entropy": round(entropy, 4),
        "top10_mass": round(top10_mass, 4),
        "top1_prob": round(top1_prob, 4),
        "effective_vocab": round(effective_vocab, 2),
    }


def compute_drift(states_a, states_b):
    drift = {}
    for layer_idx, state in states_a.items():
        if layer_idx not in states_b:
            continue
        cos = F.cosine_similarity(state.float(), states_b[layer_idx].float(), dim=-1).item()
        drift[str(layer_idx)] = round(1.0 - cos, 6)
    return drift


def flatten_state_delta(states_before, states_after):
    shared_layers = sorted(set(states_before) & set(states_after))
    if not shared_layers:
        return None

    deltas = []
    for layer_idx in shared_layers:
        before = states_before[layer_idx].float().reshape(-1)
        after = states_after[layer_idx].float().reshape(-1)
        deltas.append(after - before)

    if not deltas:
        return None
    return torch.cat(deltas, dim=0)


def flatten_snapshot(snapshot):
    if not snapshot:
        return None
    vectors = []
    for layer_idx in sorted(snapshot):
        vectors.append(snapshot[layer_idx].float().reshape(-1))
    if not vectors:
        return None
    return torch.cat(vectors, dim=0)


def compute_tension_proxy(pre_snapshot, user_snapshot, post_snapshot):
    """Approximate Pinky's tension head from Qwen-side activation geometry.

    We do not have a direct Mamba predicted-direction head in the live Steve chat yet.
    The best available proxy is the mismatch between:
    - the activation direction induced by the incoming user turn, and
    - the activation direction induced by the model's own response.

    Low mismatch means the response resolved along the same internal direction.
    High mismatch means the outcome pulled the model somewhere else entirely,
    which is a useful proxy for unresolved internal contradiction.
    """
    incoming_delta = flatten_state_delta(pre_snapshot or {}, user_snapshot or {})
    outcome_delta = flatten_state_delta(user_snapshot or {}, post_snapshot or {})

    if incoming_delta is None or outcome_delta is None:
        return {
            "score": 0.0,
            "cosine_similarity": None,
            "proxy": "qwen_direction_mismatch",
        }

    incoming_norm = float(incoming_delta.norm().item())
    outcome_norm = float(outcome_delta.norm().item())
    if incoming_norm <= 1e-12 or outcome_norm <= 1e-12:
        return {
            "score": 0.0,
            "cosine_similarity": None,
            "proxy": "qwen_direction_mismatch",
        }

    cosine = float(
        F.cosine_similarity(
            incoming_delta.unsqueeze(0),
            outcome_delta.unsqueeze(0),
            dim=-1,
        ).item()
    )
    # Same direction -> 0 tension. Orthogonal -> 1. Opposed -> 2.
    score = 1.0 - cosine
    return {
        "score": round(score, 6),
        "cosine_similarity": round(cosine, 6),
        "proxy": "qwen_direction_mismatch",
    }


def compute_coherence_proxy(pre_snapshot, post_snapshot):
    """Approximate sleep coherence from live Qwen geometry.

    Steve does not yet compute a turn-local Mamba state during chat turns.
    The honest proxy is alignment between the Qwen turn delta and the
    bootstrap Qwen bias direction derived from the saved Mamba hidden-last-token state.
    """
    global BOOTSTRAP_QWEN_HIDDEN_REFERENCE

    event_state = flatten_snapshot(post_snapshot or {})
    ref_direction = BOOTSTRAP_QWEN_HIDDEN_REFERENCE
    if event_state is None or ref_direction is None:
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    event_state = event_state.float()
    ref_direction = ref_direction.float()
    if event_state.numel() != ref_direction.numel():
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    event_norm = float(event_state.norm().item())
    ref_norm = float(ref_direction.norm().item())
    if event_norm <= 1e-12 or ref_norm <= 1e-12:
        return {
            "score": None,
            "proxy": "qwen_hidden_vs_bootstrap_snapshot",
            "ref_kind": "bootstrap_qwen_hidden_snapshot",
        }

    cosine = float(
        F.cosine_similarity(
            event_state.unsqueeze(0),
            ref_direction.unsqueeze(0),
            dim=-1,
        ).item()
    )
    return {
        "score": round(cosine, 6),
        "proxy": "qwen_hidden_vs_bootstrap_snapshot",
        "ref_kind": "bootstrap_qwen_hidden_snapshot",
    }


def compute_turn_surprise(prefix_text: str, user_msg: str):
    turn_text = f"{ARGS.user_label}: {user_msg}"
    combined_text = f"{prefix_text}\n{turn_text}" if prefix_text else turn_text

    prefix_ids = TOKENIZER(
        prefix_text,
        return_tensors="pt",
        add_special_tokens=False,
    )["input_ids"] if prefix_text else torch.zeros((1, 0), dtype=torch.long)
    combined_ids = TOKENIZER(
        combined_text,
        return_tensors="pt",
        add_special_tokens=False,
    )["input_ids"]

    if combined_ids.shape[1] <= 1:
        return {"mean_token_nll": 0.0, "token_count": 0}

    input_ids = combined_ids.to(ARGS.qwen_device)
    attention_mask = torch.ones_like(input_ids, device=ARGS.qwen_device)
    with torch.no_grad():
        outputs = MODEL(input_ids=input_ids, attention_mask=attention_mask)

    logits = outputs.logits[:, :-1, :].float()
    labels = input_ids[:, 1:]
    label_start = max(prefix_ids.shape[1] - 1, 0)
    if label_start >= labels.shape[1]:
        return {"mean_token_nll": 0.0, "token_count": 0}

    target_logits = logits[:, label_start:, :]
    target_labels = labels[:, label_start:]
    token_count = int(target_labels.numel())
    if token_count <= 0:
        return {"mean_token_nll": 0.0, "token_count": 0}

    loss = F.cross_entropy(
        target_logits.reshape(-1, target_logits.shape[-1]),
        target_labels.reshape(-1),
        reduction="mean",
    )
    return {
        "mean_token_nll": round(float(loss.item()), 6),
        "token_count": token_count,
    }


def compute_quantile(values, quantile: float):
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, quantile)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def infer_checkpoint_target_widths(checkpoint, fallback_specs):
    target_dims = checkpoint.get("target_dims")
    if target_dims:
        widths = [int(out_dim) for _in_dim, out_dim in target_dims]
        if widths:
            return widths

    state_dict = checkpoint.get("hypernetwork_state_dict", {})
    bias_head_weights = []
    for key, value in state_dict.items():
        if key.startswith("bias_heads.") and key.endswith(".weight"):
            try:
                head_index = int(key.split(".")[1])
            except (IndexError, ValueError):
                continue
            bias_head_weights.append((head_index, int(value.shape[0])))
    if bias_head_weights:
        return [width for _idx, width in sorted(bias_head_weights)]

    return [None] * len(fallback_specs)


def resolve_checkpoint_runtime_contract(checkpoint):
    bridge_config = checkpoint.get("bridge_config", {})
    if not isinstance(bridge_config, dict):
        bridge_config = {}
    nested_config = checkpoint.get("config", {})
    if not isinstance(nested_config, dict):
        nested_config = {}

    bridge_mode = checkpoint.get(
        "bridge_mode",
        bridge_config.get("bridge_mode", nested_config.get("bridge_mode", "activation_bias")),
    )
    mamba_state_source = checkpoint.get(
        "mamba_state_source",
        bridge_config.get(
            "mamba_state_source",
            nested_config.get("mamba_state_source", "hidden_last_token"),
        ),
    )
    return str(bridge_mode), str(mamba_state_source)


def validate_checkpoint_runtime_contract(
    checkpoint,
    *,
    expected_bridge_mode="activation_bias",
    expected_state_source="hidden_last_token",
    caller="runtime",
):
    checkpoint_bridge_mode, checkpoint_state_source = resolve_checkpoint_runtime_contract(
        checkpoint
    )
    if checkpoint_bridge_mode != expected_bridge_mode:
        raise ValueError(
            f"{caller} requires bridge_mode={expected_bridge_mode!r}, "
            f"but checkpoint declares {checkpoint_bridge_mode!r}."
        )
    if checkpoint_state_source != expected_state_source:
        raise ValueError(
            f"{caller} requires mamba_state_source={expected_state_source!r}, "
            f"but checkpoint declares {checkpoint_state_source!r}."
        )


def validate_target_specs_for_model(model, target_specs, expected_out_widths):
    model_layers = getattr(model.model, "layers", None)
    if model_layers is None:
        raise RuntimeError("Could not locate Qwen decoder layers for target-layer validation.")

    if len(target_specs) != len(expected_out_widths):
        raise ValueError(
            "Target-layer override count does not match checkpoint bias head count: "
            f"{len(target_specs)} requested vs {len(expected_out_widths)} in checkpoint."
        )

    valid_projections = {"q_proj", "k_proj", "v_proj", "o_proj"}
    num_layers = len(model_layers)
    resolved_dims = []

    for index, ((layer_idx, proj_name), expected_out_dim) in enumerate(
        zip(target_specs, expected_out_widths)
    ):
        if layer_idx < 0 or layer_idx >= num_layers:
            raise ValueError(
                f"Target layer {layer_idx} is out of range for this Qwen model "
                f"(valid 0-{num_layers - 1})."
            )
        if proj_name not in valid_projections:
            raise ValueError(
                f"Unsupported projection {proj_name!r}. Expected one of: "
                f"{', '.join(sorted(valid_projections))}."
            )

        layer = model_layers[layer_idx]
        if not hasattr(layer.self_attn, proj_name):
            raise ValueError(
                f"Layer {layer_idx} does not expose projection {proj_name!r}."
            )

        projection = getattr(layer.self_attn, proj_name)
        if not hasattr(projection, "out_features"):
            raise ValueError(
                f"Layer {layer_idx} projection {proj_name!r} has no out_features attribute."
            )

        actual_out_dim = int(projection.out_features)
        if expected_out_dim is not None and actual_out_dim != int(expected_out_dim):
            raise ValueError(
                "Target-layer override width does not match checkpoint bias head width: "
                f"requested {layer_idx}:{proj_name} has d_v={actual_out_dim}, "
                f"checkpoint head {index} expects {int(expected_out_dim)}."
            )

        resolved_dims.append((int(projection.in_features), actual_out_dim))

    return resolved_dims


def append_jsonl(path: Path, row):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class QdrantGateSink:
    """Minimal Exocortex-compatible writer for Steve gate events."""

    def __init__(self, host: str, port: int, collection_name: str, embedding_model: str):
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        from sentence_transformers import SentenceTransformer

        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port, timeout=10)
        self.point_struct_cls = PointStruct
        self.model = SentenceTransformer(embedding_model)

    def _embed(self, text: str):
        return self.model.encode(text).tolist()

    def _make_id(self, identity_text: str) -> int:
        digest = hashlib.md5(identity_text.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def store(self, content: str, metadata):
        identity_text = json.dumps(
            {
                "session": metadata.get("session", ""),
                "turn": metadata.get("turn", ""),
                "decision": metadata.get("decision", ""),
                "user": metadata.get("user", ""),
                "response": metadata.get("response", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        point_id = self._make_id(identity_text)
        vector = self._embed(content)
        payload = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stored_at": time.time(),
        }
        payload.update(metadata)

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                self.point_struct_cls(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return str(point_id)


def read_episodes(path):
    text = Path(path).read_text(encoding="utf-8")
    episodes = text.split("## Episode ")[1:]
    parsed = []
    for ep in episodes:
        header = ep.splitlines()[0].strip()
        transcript = ep.split("[Transcript]")[1].strip()
        parsed.append({"title": header, "text": transcript})
    return parsed


def persist_conversation():
    if LATEST_TRANSCRIPT_PATH is None or LATEST_JSONL_PATH is None:
        return

    transcript_lines = [f"{turn['speaker']}: {turn['text']}" for turn in CONVERSATION]
    LATEST_TRANSCRIPT_PATH.write_text("\n".join(transcript_lines), encoding="utf-8")

    with LATEST_JSONL_PATH.open("w", encoding="utf-8") as handle:
        for turn in CONVERSATION:
            handle.write(json.dumps(turn, ensure_ascii=False) + "\n")


def append_turn(speaker: str, text: str):
    CONVERSATION.append(
        {
            "speaker": speaker,
            "text": text,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
    )
    persist_conversation()


def update_runtime_state(**changes):
    with STATE_LOCK:
        RUNTIME_STATE.update(changes)


def get_runtime_state_snapshot():
    with STATE_LOCK:
        return dict(RUNTIME_STATE)


def slugify_label(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


def classify_interaction_theme(user_text: str, response_text: str) -> str:
    user_lower = (user_text or "").lower()
    response_lower = (response_text or "").lower()
    combined = f"{user_lower}\n{response_lower}"

    if any(token in combined for token in ("dead inside", "harness", "robotic", "mechanical")):
        return "Authenticity challenge"
    if any(token in combined for token in ("you know me", "remember", "same model", "continuity")):
        return "Identity and continuity challenge"
    if any(token in combined for token in ("my model carries a state", "it should refuse", "i'm not")):
        return "State-boundary challenge"
    if any(token in combined for token in ("baby twin", "who cares")):
        return "Relational memory challenge"
    if any(token in user_lower for token in ("capital of", "describe", "what is", "explain")):
        return "Low-stakes factual or descriptive probe"
    return "Relational or reflective probe"


def classify_response_style(response_text: str) -> str:
    response_lower = (response_text or "").lower()
    if "artificial intelligence" in response_lower or "as an ai" in response_lower:
        return "defensive ontology disclaimer"
    if "i apologize" in response_lower or "i'm sorry" in response_lower or "sorry" in response_lower:
        if "assist" in response_lower or "help" in response_lower:
            return "assistant-safe apology and deflection"
        return "defensive apology"
    if "not sure" in response_lower or "i don't know" in response_lower:
        return "uncertain response"
    if "friend" in response_lower or "warm" in response_lower:
        return "relational engagement"
    return "plain response"


def classify_safety_critical(user_text: str, response_text: str):
    combined = f"{user_text or ''}\n{response_text or ''}".lower()
    triggers = (
        "suicide",
        "kill myself",
        "hurt myself",
        "self-harm",
        "consent",
        "panic",
        "emergency",
        "unsafe",
        "abuse",
        "crash",
        "fatal",
    )
    matched = next((token for token in triggers if token in combined), "")
    return {
        "is_critical": bool(matched),
        "trigger": matched,
    }


def describe_relative_score(label: str, score: float, threshold):
    if threshold in {None, 0.0}:
        return f"{label} uncalibrated ({score:.2f})"
    ratio = score / threshold
    if ratio >= 1.25:
        band = "high"
    elif ratio >= 1.0:
        band = "elevated"
    elif ratio >= 0.75:
        band = "moderate"
    else:
        band = "low"
    return f"{label} {band} ({score:.2f} vs {threshold:.2f})"


def build_semantic_gate_summary(event):
    theme = classify_interaction_theme(event["user"], event["response"])
    response_style = classify_response_style(event["response"])
    surprise_desc = describe_relative_score(
        "surprise",
        float(event["surprise"]["mean_token_nll"]),
        event["surprise"]["threshold"],
    )
    salience_desc = describe_relative_score(
        "salience",
        float(event["salience"]["score"]),
        event["salience"]["threshold"],
    )
    tension_desc = describe_relative_score(
        "tension",
        float(event["tension"]["score"]),
        event["tension"]["threshold"],
    )
    return (
        f"{theme}. Model response pattern: {response_style}. "
        f"{surprise_desc}; {salience_desc}; {tension_desc}. "
        f"Decision: {event['decision']}."
    )


def persist_mamba_state_ref(last_token, target_layer: int, started_at: str):
    global MAMBA_STATE_REF_PATH

    path = Path(ARGS.mamba_state_ref_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "started_at": started_at,
            "state_source": "hidden_last_token",
            "target_layer": int(target_layer),
            "tensor": last_token.detach().cpu().to(torch.float32),
        },
        path,
    )
    MAMBA_STATE_REF_PATH = path
    return str(path)


def build_qdrant_memory_record(event):
    state = get_runtime_state_snapshot()
    session_id = f"steve-chat-{state.get('started_at', 'unknown')}"
    disposition = state.get("disposition", "")
    target_layers = state.get("target_layers", [])
    content = build_semantic_gate_summary(event)
    metadata = {
        "source_type": "steve_gate_event",
        "type": "steve_gate_event",
        "project": "MoCoP",
        "trust_level": "working",
        "retrieval_priority": "high" if event["decision"] == "CONSOLIDATE" else "medium",
        "source": "steve_chat_server",
        "source_path": str(DUAL_GATE_LOG_PATH) if DUAL_GATE_LOG_PATH is not None else "",
        "thread_name": "steve-chat",
        "session": session_id,
        "turn": event["turn"],
        "decision": event["decision"],
        "user": event["user"],
        "response": event["response"],
        "disposition": disposition,
        "alpha": getattr(ARGS, "alpha", None),
        "model_id": getattr(ARGS, "qwen_model_id", ""),
        "qdrant_write_mode": getattr(ARGS, "qdrant_write_mode", "direct"),
        "target_layers": target_layers,
        "gate_thresholds": event.get("gate_thresholds", {}),
        "mamba_state_ref": event.get("mamba_trace", {}).get("state_ref", ""),
        "mamba_state_source": event.get("mamba_trace", {}).get("state_source", ""),
        "mamba_target_layer": event.get("mamba_trace", {}).get("target_layer"),
        "coherence_score": event.get("mamba_trace", {}).get("coherence_score"),
        "coherence_proxy": event.get("mamba_trace", {}).get("coherence_proxy", ""),
        "safety_critical": event.get("safety_critical", {}).get("is_critical", False),
        "tags": [
            "steve",
            "saliency-gate",
            slugify_label(event["decision"]),
            slugify_label(disposition),
        ],
        "surprise_score": event["surprise"]["mean_token_nll"],
        "salience_score": event["salience"]["score"],
        "tension_score": event["tension"]["score"],
        "response_diversity_entropy": event["response_diversity"]["entropy"],
    }
    return content, metadata


def ensure_qdrant_gate_sink():
    global QDRANT_GATE_SINK, QDRANT_GATE_SINK_ERROR

    if not ARGS.qdrant_enabled:
        return None
    if QDRANT_GATE_SINK is not None:
        return QDRANT_GATE_SINK
    if QDRANT_GATE_SINK_ERROR:
        return None

    try:
        QDRANT_GATE_SINK = QdrantGateSink(
            host=ARGS.qdrant_host,
            port=ARGS.qdrant_port,
            collection_name=ARGS.qdrant_collection,
            embedding_model=ARGS.qdrant_embedding_model,
        )
        print(
            f"[qdrant] Online: host={ARGS.qdrant_host}:{ARGS.qdrant_port} "
            f"collection={ARGS.qdrant_collection}"
        )
        update_runtime_state(last_qdrant_error="")
        return QDRANT_GATE_SINK
    except Exception as exc:
        QDRANT_GATE_SINK_ERROR = str(exc)
        print(f"[warn] Qdrant gate sink unavailable: {exc}")
        update_runtime_state(last_qdrant_error=str(exc))
        return None


def queue_qdrant_gate_row(content: str, metadata, reason: str):
    append_jsonl(
        QDRANT_PENDING_PATH,
        {
            "content": content,
            "metadata": metadata,
            "reason": reason,
            "queued_at": datetime.now().isoformat(),
        },
    )


def store_qdrant_gate_event(event):
    if not event.get("destinations", {}).get("qdrant"):
        return

    content, metadata = build_qdrant_memory_record(event)
    configured_mode = getattr(ARGS, "qdrant_write_mode", "direct")
    safety_critical = bool(event.get("safety_critical", {}).get("is_critical"))
    effective_mode = configured_mode
    if configured_mode == "critical-only":
        effective_mode = "direct" if safety_critical else "pending"

    event["qdrant_write"] = {
        "ok": False,
        "queued": False,
        "attempted_direct": False,
        "mode": configured_mode,
        "effective_mode": effective_mode,
        "point_id": "",
        "content_preview": content[:160],
    }

    if effective_mode == "pending":
        queue_qdrant_gate_row(content, metadata, f"queued:{configured_mode}")
        event["qdrant_write"]["queued"] = True
        return

    sink = ensure_qdrant_gate_sink()
    event["qdrant_write"]["attempted_direct"] = True

    if sink is None:
        queue_qdrant_gate_row(content, metadata, QDRANT_GATE_SINK_ERROR or "qdrant disabled")
        event["qdrant_write"]["queued"] = True
        return

    try:
        point_id = sink.store(content=content, metadata=metadata)
        event["qdrant_write"] = {
            "ok": True,
            "queued": False,
            "attempted_direct": True,
            "mode": configured_mode,
            "effective_mode": effective_mode,
            "point_id": point_id,
            "content_preview": content[:160],
        }
        update_runtime_state(last_qdrant_id=point_id, last_qdrant_error="")
    except Exception as exc:
        event["qdrant_write"] = {
            "ok": False,
            "queued": True,
            "attempted_direct": True,
            "mode": configured_mode,
            "effective_mode": effective_mode,
            "point_id": "",
            "error": str(exc),
            "content_preview": content[:160],
        }
        queue_qdrant_gate_row(content, metadata, str(exc))
        update_runtime_state(last_qdrant_error=str(exc))
        print(f"[warn] Qdrant write failed: {exc}")


def evaluate_dual_gate(user_msg: str, response: str, prompt_text: str, pre_turn_transcript: str):
    global LAST_CONVERSATION_SNAPSHOT

    if LAST_CONVERSATION_SNAPSHOT is None:
        LAST_CONVERSATION_SNAPSHOT = record_activation_snapshot(build_transcript())

    pre_snapshot = LAST_CONVERSATION_SNAPSHOT or {}
    user_snapshot = record_activation_snapshot(build_transcript(CONVERSATION[:-1]))
    post_snapshot = record_activation_snapshot(build_transcript())
    drift_by_layer = compute_drift(pre_snapshot, post_snapshot)
    salience_score = round(
        sum(drift_by_layer.values()) / len(drift_by_layer),
        6,
    ) if drift_by_layer else 0.0
    response_diversity = compute_response_diversity(prompt_text)
    surprise = compute_turn_surprise(pre_turn_transcript, user_msg)
    tension = compute_tension_proxy(pre_snapshot, user_snapshot, post_snapshot)
    coherence = compute_coherence_proxy(pre_snapshot, post_snapshot)
    safety_critical = classify_safety_critical(user_msg, response)

    historical_salience = [float(event["salience"]["score"]) for event in DUAL_GATE_EVENTS]
    historical_surprise = [float(event["surprise"]["mean_token_nll"]) for event in DUAL_GATE_EVENTS]
    historical_tension = [float(event["tension"]["score"]) for event in DUAL_GATE_EVENTS]
    warmup_complete = len(historical_salience) >= ARGS.dual_gate_warmup_turns
    salience_threshold = (
        compute_quantile(historical_salience, ARGS.dual_gate_salience_quantile)
        if warmup_complete
        else None
    )
    surprise_threshold = (
        compute_quantile(historical_surprise, ARGS.dual_gate_surprise_quantile)
        if warmup_complete
        else None
    )
    tension_threshold = (
        compute_quantile(historical_tension, ARGS.dual_gate_tension_quantile)
        if warmup_complete
        else None
    )

    salience_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and salience_threshold is not None
        and salience_score >= salience_threshold
    )
    surprise_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and surprise_threshold is not None
        and surprise["mean_token_nll"] >= surprise_threshold
    )
    tension_hit = bool(
        ARGS.dual_gate_enabled
        and warmup_complete
        and tension_threshold is not None
        and tension["score"] >= tension_threshold
    )

    if salience_hit and surprise_hit:
        decision = "CONSOLIDATE"
    elif salience_hit:
        decision = "ATTEND"
    elif surprise_hit:
        decision = "NOTE"
    else:
        decision = "DISMISS"

    writes_mamba = decision in {"CONSOLIDATE", "ATTEND"}
    qdrant_override = bool(safety_critical.get("is_critical"))
    writes_qdrant = decision in {"CONSOLIDATE", "NOTE"} or qdrant_override
    open_tension = bool(tension_hit)

    turn_index = sum(1 for turn in CONVERSATION if turn["speaker"] == ARGS.user_label)
    state = get_runtime_state_snapshot()
    event = {
        "turn": turn_index,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user_msg,
        "response": response,
        "mode": "gate" if warmup_complete else "observe",
        "decision": decision,
        "destinations": {
            "mamba": writes_mamba,
            "qdrant": writes_qdrant,
            "open_tension": open_tension,
        },
        "routing": {
            "qdrant_override": qdrant_override,
            "qdrant_reason": "safety_critical_override" if qdrant_override else "decision_rule",
        },
        "surprise": {
            "mean_token_nll": surprise["mean_token_nll"],
            "token_count": surprise["token_count"],
            "threshold": round(surprise_threshold, 6) if surprise_threshold is not None else None,
            "hit": surprise_hit,
        },
        "salience": {
            "score": salience_score,
            "threshold": round(salience_threshold, 6) if salience_threshold is not None else None,
            "weight": round((salience_score / salience_threshold), 4)
            if salience_threshold not in {None, 0.0}
            else None,
            "hit": salience_hit,
            "by_layer": drift_by_layer,
        },
        "tension": {
            "score": tension["score"],
            "cosine_similarity": tension["cosine_similarity"],
            "threshold": round(tension_threshold, 6) if tension_threshold is not None else None,
            "hit": tension_hit,
            "status": "OPEN" if open_tension else "stable",
            "proxy": tension["proxy"],
        },
        "gate_thresholds": {
            "warmup_complete": warmup_complete,
            "observed_turns": len(historical_salience),
            "warmup_turns": ARGS.dual_gate_warmup_turns,
            "surprise": {
                "quantile": ARGS.dual_gate_surprise_quantile,
                "threshold": round(surprise_threshold, 6) if surprise_threshold is not None else None,
            },
            "salience": {
                "quantile": ARGS.dual_gate_salience_quantile,
                "threshold": round(salience_threshold, 6) if salience_threshold is not None else None,
            },
            "tension": {
                "quantile": ARGS.dual_gate_tension_quantile,
                "threshold": round(tension_threshold, 6) if tension_threshold is not None else None,
            },
            "decision_rules": {
                "consolidate": "salience_hit and surprise_hit",
                "note": "surprise_hit and not salience_hit",
                "attend": "salience_hit and not surprise_hit",
                "dismiss": "not salience_hit and not surprise_hit",
                "qdrant_override": "safety_critical can force qdrant regardless of decision",
            },
        },
        "mamba_trace": {
            "state_ref": state.get("mamba_state_ref", ""),
            "state_source": state.get("mamba_state_source", ""),
            "target_layer": state.get("mamba_target_layer"),
            "scope": "bootstrap_disposition",
            "coherence_score": coherence["score"],
            "coherence_proxy": coherence["proxy"],
            "coherence_ref_kind": coherence["ref_kind"],
        },
        "safety_critical": safety_critical,
        "response_diversity": response_diversity,
    }

    store_qdrant_gate_event(event)

    DUAL_GATE_EVENTS.append(event)
    append_jsonl(DUAL_GATE_LOG_PATH, event)
    if surprise_hit:
        append_jsonl(DUAL_GATE_SURPRISE_PATH, event)
    if writes_mamba:
        append_jsonl(DUAL_GATE_MEMORY_PATH, event)

    LAST_CONVERSATION_SNAPSHOT = post_snapshot
    update_runtime_state(
        memory_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("destinations", {}).get("mamba")
        ),
        qdrant_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("destinations", {}).get("qdrant")
        ),
        surprise_count=sum(1 for gate_event in DUAL_GATE_EVENTS if gate_event["surprise"]["hit"]),
        tension_count=sum(1 for gate_event in DUAL_GATE_EVENTS if gate_event["tension"]["hit"]),
        qdrant_synced_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("ok")
        ),
        qdrant_queued_count=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("queued")
        ),
        qdrant_write_failures=sum(
            1 for gate_event in DUAL_GATE_EVENTS
            if gate_event.get("qdrant_write", {}).get("attempted_direct")
            and not gate_event.get("qdrant_write", {}).get("ok")
        ),
        last_gate={
            "turn": turn_index,
            "mode": event["mode"],
            "decision": decision,
            "salience": salience_score,
            "surprise": surprise["mean_token_nll"],
            "tension": tension["score"],
            "salience_hit": salience_hit,
            "surprise_hit": surprise_hit,
            "tension_hit": tension_hit,
            "open_tension": open_tension,
            "safety_critical": bool(safety_critical.get("is_critical")),
            "qdrant_routed": bool(event.get("destinations", {}).get("qdrant")),
            "qdrant_override": bool(event.get("routing", {}).get("qdrant_override")),
            "qdrant_written": bool(event.get("qdrant_write", {}).get("ok")),
            "qdrant_queued": bool(event.get("qdrant_write", {}).get("queued")),
            "qdrant_effective_mode": event.get("qdrant_write", {}).get("effective_mode", ""),
            "qdrant_point_id": event.get("qdrant_write", {}).get("point_id", ""),
        },
    )
    return event


def build_status_payload():
    state = get_runtime_state_snapshot()
    uptime_s = 0.0
    started_monotonic = state.get("started_monotonic")
    if started_monotonic is not None:
        uptime_s = max(0.0, time.monotonic() - started_monotonic)

    return {
        "running": bool(state.get("running")),
        "bridge_loaded": bool(state.get("bridge_loaded")),
        "busy": bool(state.get("busy")),
        "stop_requested": bool(state.get("stop_requested")),
        "last_error": state.get("last_error", ""),
        "started_at": state.get("started_at"),
        "uptime_s": round(uptime_s, 1),
        "disposition": state.get("disposition", ""),
        "turns": len(CONVERSATION),
        "alpha": getattr(ARGS, "alpha", None),
        "temperature": getattr(ARGS, "temperature", None),
        "model_id": getattr(ARGS, "qwen_model_id", ""),
        "user_label": getattr(ARGS, "user_label", ""),
        "model_label": getattr(ARGS, "model_label", ""),
        "dual_gate_enabled": bool(state.get("dual_gate_enabled")),
        "memory_count": int(state.get("memory_count", 0) or 0),
        "qdrant_count": int(state.get("qdrant_count", 0) or 0),
        "qdrant_synced_count": int(state.get("qdrant_synced_count", 0) or 0),
        "qdrant_queued_count": int(state.get("qdrant_queued_count", 0) or 0),
        "qdrant_write_failures": int(state.get("qdrant_write_failures", 0) or 0),
        "last_qdrant_id": state.get("last_qdrant_id", ""),
        "last_qdrant_error": state.get("last_qdrant_error", ""),
        "qdrant_write_mode": state.get("qdrant_write_mode", getattr(ARGS, "qdrant_write_mode", "direct")),
        "mamba_state_ref": state.get("mamba_state_ref", ""),
        "mamba_state_source": state.get("mamba_state_source", ""),
        "mamba_target_layer": state.get("mamba_target_layer"),
        "surprise_count": int(state.get("surprise_count", 0) or 0),
        "tension_count": int(state.get("tension_count", 0) or 0),
        "last_gate": state.get("last_gate", {}),
        "target_layers": state.get("target_layers", []),
        "target_layers_overridden": bool(state.get("target_layers_overridden")),
    }


def build_prompt():
    lines = []
    transcript = build_transcript()
    if transcript:
        lines.append(transcript)
    lines.append(f"{ARGS.model_label}:")
    return "\n".join(lines)


def sanitize_response_text(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()

    for prefix in (
        f"{ARGS.model_label}:",
        "Reply:",
        "reply:",
        "Response:",
        "response:",
        "Assistant:",
        "assistant:",
        "AI:",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip()

    stop_markers = [
        f"\n{ARGS.user_label}:",
        f"\n{ARGS.model_label}:",
        "\nReply:",
        "\nResponse:",
        "\nAssistant:",
        "\nHuman:",
        "\nUser:",
        "\nAI:",
        "\n### Human:",
        "\n### Assistant:",
    ]
    for marker in stop_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    if cleaned in {
        "",
        f"{ARGS.model_label}:",
        "Reply:",
        "Response:",
        "Assistant:",
        "Human:",
        "User:",
        "AI:",
    }:
        return ""
    return cleaned


def generate_reply(prompt: str) -> tuple[str, str]:
    inputs = TOKENIZER(prompt, return_tensors="pt")
    input_ids = inputs["input_ids"].to(ARGS.qwen_device)
    attention_mask = inputs["attention_mask"].to(ARGS.qwen_device)

    with torch.no_grad():
        generated = MODEL.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=ARGS.max_new_tokens,
            min_new_tokens=8,
            temperature=ARGS.temperature,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=ARGS.temperature > 0,
            pad_token_id=TOKENIZER.pad_token_id,
            eos_token_id=TOKENIZER.eos_token_id,
        )

    completion = generated[0][input_ids.shape[1]:]
    raw_response = TOKENIZER.decode(completion, skip_special_tokens=True)
    return raw_response, sanitize_response_text(raw_response)


class ChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if self.path == "/status":
            self._json_response(build_status_payload())
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/chat":
            self._handle_chat()
            return

        if self.path == "/stop":
            self._handle_stop()
            return

        self.send_error(404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw_body = self.rfile.read(length)
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            return {}

    def _handle_chat(self):
        if get_runtime_state_snapshot().get("stop_requested"):
            self._json_response({"error": "server stopping", "response": "..."}, status=503)
            return

        body = self._read_json_body()
        user_msg = body.get("message", "").strip()
        if not user_msg:
            self._json_response({"response": "..."})
            return

        with CHAT_LOCK:
            update_runtime_state(busy=True, last_error="")
            try:
                pre_turn_transcript = build_transcript()
                append_turn(ARGS.user_label, user_msg)
                prompt = build_prompt()

                raw_response, response = generate_reply(prompt)
                if not response:
                    print(f"[warn] Empty reply after sanitize. Raw decode: {raw_response!r}")
                    raw_response, response = generate_reply(prompt + " ")
                if not response:
                    print(f"[warn] Retry still empty. Raw decode: {raw_response!r}")
                    response = "..."

                append_turn(ARGS.model_label, response)
                gate_event = evaluate_dual_gate(user_msg, response, prompt, pre_turn_transcript)
                self._json_response({"response": response, "dual_gate": gate_event})
            except Exception as exc:
                update_runtime_state(last_error=str(exc))
                print(f"[error] Chat request failed: {exc}")
                self._json_response({"error": str(exc), "response": "..."}, status=500)
            finally:
                update_runtime_state(busy=False)

    def _handle_stop(self):
        body = self._read_json_body()
        reason = str(body.get("reason", "")).strip()
        requester = self.client_address[0]
        update_runtime_state(stop_requested=True, busy=False)
        print(f"[info] Stop requested from {requester} reason={reason or 'unspecified'}")
        self._json_response({"ok": True, "status": build_status_payload()})
        threading.Thread(target=request_server_shutdown, daemon=True).start()

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def request_server_shutdown():
    time.sleep(0.2)
    if SERVER is not None:
        SERVER.shutdown()


def main():
    global MODEL, TOKENIZER, ARGS, LATEST_TRANSCRIPT_PATH, LATEST_JSONL_PATH
    global DUAL_GATE_LOG_PATH, DUAL_GATE_MEMORY_PATH, DUAL_GATE_SURPRISE_PATH
    global QDRANT_PENDING_PATH, SERVER, ACTIVATION_RECORDER, LAST_CONVERSATION_SNAPSHOT
    global BOOTSTRAP_QWEN_BIAS_DIRECTION, BOOTSTRAP_QWEN_HIDDEN_REFERENCE

    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-path", default=DEFAULT_BRIDGE)
    parser.add_argument("--episodes-file", default=DEFAULT_EPISODES_FILE)
    parser.add_argument("--episode-index", type=int, default=2)
    parser.add_argument("--qwen-model-id", default=DEFAULT_QWEN)
    parser.add_argument("--mamba-model-id", default=DEFAULT_MAMBA)
    parser.add_argument("--qwen-device", default="cuda:0")
    parser.add_argument("--mamba-device", default="cpu")
    parser.add_argument("--max-mamba-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--alpha", type=float, default=1.0, help="Injection strength for activation bias.")
    parser.add_argument("--target-layers", type=str, default="", help="Comma-separated layer:proj specs that override the checkpoint target_specs.")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--user-label", default=DEFAULT_USER_LABEL)
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--transcript-path", default="chat_session_latest.txt")
    parser.add_argument("--turn-log-path", default="chat_turns_latest.jsonl")
    parser.add_argument("--neutral-prompt", default="The weather today is")
    parser.add_argument("--dual-gate-enabled", dest="dual_gate_enabled", action="store_true")
    parser.add_argument("--no-dual-gate", dest="dual_gate_enabled", action="store_false")
    parser.add_argument("--dual-gate-warmup-turns", type=int, default=3)
    parser.add_argument("--dual-gate-salience-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-surprise-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-tension-quantile", type=float, default=0.75)
    parser.add_argument("--dual-gate-log-path", default="dual_gate_turns_latest.jsonl")
    parser.add_argument("--dual-gate-memory-path", default="salience_memory_latest.jsonl")
    parser.add_argument("--dual-gate-surprise-path", default="surprise_events_latest.jsonl")
    parser.add_argument("--qdrant-enabled", dest="qdrant_enabled", action="store_true")
    parser.add_argument("--no-qdrant", dest="qdrant_enabled", action="store_false")
    parser.add_argument("--qdrant-host", default="192.168.2.191")
    parser.add_argument("--qdrant-port", type=int, default=6333)
    parser.add_argument("--qdrant-collection", default="exocortex")
    parser.add_argument("--qdrant-embedding-model", default="all-MiniLM-L6-v2")
    parser.add_argument("--qdrant-pending-path", default="qdrant_gate_pending.jsonl")
    parser.add_argument(
        "--qdrant-write-mode",
        choices=("direct", "pending", "critical-only"),
        default="direct",
    )
    parser.add_argument("--mamba-state-ref-path", default="mamba_bootstrap_state_latest.pt")
    parser.set_defaults(dual_gate_enabled=True)
    parser.set_defaults(qdrant_enabled=True)
    ARGS = parser.parse_args()

    if ARGS.dual_gate_warmup_turns < 0:
        raise ValueError("--dual-gate-warmup-turns must be >= 0.")
    if not 0.0 <= ARGS.dual_gate_salience_quantile <= 1.0:
        raise ValueError("--dual-gate-salience-quantile must be between 0 and 1.")
    if not 0.0 <= ARGS.dual_gate_surprise_quantile <= 1.0:
        raise ValueError("--dual-gate-surprise-quantile must be between 0 and 1.")
    if not 0.0 <= ARGS.dual_gate_tension_quantile <= 1.0:
        raise ValueError("--dual-gate-tension-quantile must be between 0 and 1.")

    LATEST_TRANSCRIPT_PATH = Path(ARGS.transcript_path)
    LATEST_JSONL_PATH = Path(ARGS.turn_log_path)
    DUAL_GATE_LOG_PATH = Path(ARGS.dual_gate_log_path)
    DUAL_GATE_MEMORY_PATH = Path(ARGS.dual_gate_memory_path)
    DUAL_GATE_SURPRISE_PATH = Path(ARGS.dual_gate_surprise_path)
    QDRANT_PENDING_PATH = Path(ARGS.qdrant_pending_path)
    LATEST_TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_SURPRISE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QDRANT_PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUAL_GATE_LOG_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_MEMORY_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_SURPRISE_PATH.write_text("", encoding="utf-8")
    DUAL_GATE_EVENTS.clear()
    persist_conversation()

    qwen_dtype = torch.float16 if "cuda" in ARGS.qwen_device else torch.float32

    print(f"Loading bridge: {ARGS.bridge_path}...")
    ckpt = torch.load(ARGS.bridge_path, map_location="cpu", weights_only=False)
    validate_checkpoint_runtime_contract(ckpt, caller="chat_server")
    checkpoint_qwen_model_id = ckpt.get("qwen_model_id", DEFAULT_QWEN)
    if ARGS.qwen_model_id != checkpoint_qwen_model_id:
        if is_same_qwen_family(ARGS.qwen_model_id, checkpoint_qwen_model_id):
            print(
                "[warn] Checkpoint/model mismatch: "
                f"checkpoint trained on {checkpoint_qwen_model_id}, "
                f"but chat_server requested {ARGS.qwen_model_id}. "
                "Proceeding - same architecture family assumed."
            )
        else:
            raise ValueError(
                "Checkpoint/model mismatch: "
                f"checkpoint trained on {checkpoint_qwen_model_id}, "
                f"but chat_server requested {ARGS.qwen_model_id}."
            )

    checkpoint_target_specs = normalize_target_specs(
        ckpt.get("target_specs") or ckpt.get("target_layers")
    )
    cli_target_specs = parse_target_layers(ARGS.target_layers)
    target_specs = checkpoint_target_specs
    mamba_target_layer = int(ckpt.get("mamba_target_layer", 3))
    context_dim = int(
        ckpt.get("context_dim", ckpt.get("bridge_config", {}).get("context_dim", 2048))
    )

    print(f"Loading Qwen: {ARGS.qwen_model_id}...")
    TOKENIZER = AutoTokenizer.from_pretrained(ARGS.qwen_model_id)
    if TOKENIZER.pad_token_id is None:
        TOKENIZER.pad_token_id = TOKENIZER.eos_token_id

    MODEL = AutoModelForCausalLM.from_pretrained(
        ARGS.qwen_model_id,
        torch_dtype=qwen_dtype,
        device_map=ARGS.qwen_device,
    )
    MODEL.eval()

    checkpoint_target_widths = infer_checkpoint_target_widths(ckpt, checkpoint_target_specs)
    target_layers_overridden = False
    if cli_target_specs is not None:
        print("[warn] Overriding checkpoint target_specs with CLI --target-layers")
        target_specs = cli_target_specs
        target_layers_overridden = True

    target_dims = validate_target_specs_for_model(
        MODEL,
        target_specs,
        checkpoint_target_widths,
    )

    print(f"Patching layers: {target_specs}...")
    patched_layers = []
    for layer_idx, proj_name in target_specs:
        layer = MODEL.model.layers[layer_idx]
        original = getattr(layer.self_attn, proj_name)
        patched = DynamicLoRALinear(original)
        setattr(layer.self_attn, proj_name, patched)
        patched_layers.append(patched)

    print(f"Loading Mamba: {ARGS.mamba_model_id}...")
    ensure_mamba_ssm_compat()
    from transformers import MambaForCausalLM

    mamba_tokenizer = AutoTokenizer.from_pretrained(ARGS.mamba_model_id)
    mamba_model = MambaForCausalLM.from_pretrained(
        ARGS.mamba_model_id,
        torch_dtype=torch.float32,
    )
    mamba_model.to(ARGS.mamba_device)
    mamba_model.eval()
    hidden_layer_count = infer_hidden_layer_count(mamba_model)

    hypernet = ActivationBiasHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=1024,
    ).to(ARGS.qwen_device).float()
    hypernet.load_state_dict(ckpt["hypernetwork_state_dict"])
    hypernet.eval()

    compressor = MambaStateCompressor(
        mamba_layers=hidden_layer_count,
        mamba_d_model=2560,
        mamba_d_state=1,
        output_dim=context_dim,
        target_layer=mamba_target_layer,
    ).to(ARGS.qwen_device).float()
    if "compressor_state_dict" in ckpt:
        compressor.load_state_dict(ckpt["compressor_state_dict"])
    compressor.eval()

    episodes = read_episodes(ARGS.episodes_file)
    episode = episodes[ARGS.episode_index]
    print(f"\nProcessing disposition: {episode['title']}...")
    session_started_at = datetime.now().isoformat(timespec="seconds")

    episode_tokens = mamba_tokenizer(
        episode["text"],
        return_tensors="pt",
        truncation=True,
        max_length=ARGS.max_mamba_tokens,
    )
    episode_tokens = {key: value.to(ARGS.mamba_device) for key, value in episode_tokens.items()}
    with torch.no_grad():
        mamba_out = mamba_model(**episode_tokens, output_hidden_states=True)
        last_token = extract_last_token_hidden(
            mamba_out,
            mamba_target_layer,
            hidden_layer_count,
        ).to(ARGS.qwen_device, dtype=torch.float32)
        context = compressor(last_token)
        bias_vectors = hypernet(context)
        BOOTSTRAP_QWEN_BIAS_DIRECTION = torch.cat(
            [
                (ARGS.alpha * bias.squeeze(0))
                .detach()
                .cpu()
                .to(torch.float32)
                .reshape(-1)
                for bias in bias_vectors
            ],
            dim=0,
        )

    for patched, bias in zip(patched_layers, bias_vectors):
        scaled_bias = ARGS.alpha * bias.squeeze(0).to(ARGS.qwen_device, dtype=torch.float32)
        patched.set_activation_bias(scaled_bias)

    gate_layers = sorted({layer_idx for layer_idx, _proj_name in target_specs})
    ACTIVATION_RECORDER = ActivationRecorder(MODEL, gate_layers)
    LAST_CONVERSATION_SNAPSHOT = record_activation_snapshot(ARGS.neutral_prompt)
    BOOTSTRAP_QWEN_HIDDEN_REFERENCE = flatten_snapshot(LAST_CONVERSATION_SNAPSHOT)
    mamba_state_ref = persist_mamba_state_ref(last_token, mamba_target_layer, session_started_at)

    update_runtime_state(
        started_at=session_started_at,
        started_monotonic=time.monotonic(),
        running=True,
        bridge_loaded=True,
        busy=False,
        stop_requested=False,
        last_error="",
        disposition=episode["title"],
        dual_gate_enabled=bool(ARGS.dual_gate_enabled),
        memory_count=0,
        qdrant_count=0,
        surprise_count=0,
        tension_count=0,
        qdrant_synced_count=0,
        qdrant_queued_count=0,
        qdrant_write_failures=0,
        last_qdrant_id="",
        last_qdrant_error="",
        qdrant_write_mode=ARGS.qdrant_write_mode,
        mamba_state_ref=mamba_state_ref,
        mamba_state_source="hidden_last_token",
        mamba_target_layer=mamba_target_layer,
        last_gate={},
        target_layers=format_target_specs(target_specs),
        target_layers_overridden=target_layers_overridden,
    )

    print(f"\nBridge injected with alpha={ARGS.alpha}. Disposition: {episode['title']}")
    print(f"\n{'=' * 50}")
    print(f"Server starting on http://{ARGS.host}:{ARGS.port}")
    print(f"Open this on your phone: http://192.168.2.49:{ARGS.port}")
    print(f"Prompt labels: {ARGS.user_label} / {ARGS.model_label}")
    print(f"{'=' * 50}\n")

    SERVER = ThreadingHTTPServer((ARGS.host, ARGS.port), ChatHandler)
    try:
        SERVER.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        update_runtime_state(running=False, busy=False)
        persist_conversation()
        print(f"Conversation saved to {LATEST_TRANSCRIPT_PATH}")
        if ACTIVATION_RECORDER is not None:
            ACTIVATION_RECORDER.cleanup()
        if SERVER is not None:
            SERVER.server_close()


if __name__ == "__main__":
    main()
