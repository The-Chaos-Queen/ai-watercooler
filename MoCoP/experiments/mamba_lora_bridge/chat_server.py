"""
chat_server.py - Browser chat for the 1.5B reincarnation probe.

Runs a minimal HTTP server. The bridge is injected once at startup,
then Laura can talk to the model from a browser on the LAN.
"""

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import torch
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

HTML_PAGE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reincarnated Qwen</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
  #header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #333; font-size: 14px; color: #8b8b8b; }
  #header span { color: #c4956a; font-weight: bold; }
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
  #thinking { display: none; align-self: flex-start; color: #c4956a; font-size: 13px; padding: 8px 14px; }
  #thinking.active { display: block; }
</style>
</head><body>
<div id="header">Reincarnated Qwen 1.5B | <span>The Rabbit Hole of Subjectivity</span></div>
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
const thinking = document.getElementById('thinking');

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
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
  btn.disabled = false;
  input.focus();
}

input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
addMsg('Bridge loaded. Disposition: The Rabbit Hole of Subjectivity. Say hello.', 'system');
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


def build_prompt():
    lines = []
    for turn in CONVERSATION:
        lines.append(f"{turn['speaker']}: {turn['text']}")
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
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        user_msg = body.get("message", "").strip()
        if not user_msg:
            self._json_response({"response": "..."})
            return

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
        self._json_response({"response": response})

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    global MODEL, TOKENIZER, ARGS, LATEST_TRANSCRIPT_PATH, LATEST_JSONL_PATH

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
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--user-label", default=DEFAULT_USER_LABEL)
    parser.add_argument("--model-label", default=DEFAULT_MODEL_LABEL)
    parser.add_argument("--transcript-path", default="chat_session_latest.txt")
    parser.add_argument("--turn-log-path", default="chat_turns_latest.jsonl")
    ARGS = parser.parse_args()

    LATEST_TRANSCRIPT_PATH = Path(ARGS.transcript_path)
    LATEST_JSONL_PATH = Path(ARGS.turn_log_path)
    LATEST_TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    persist_conversation()

    qwen_dtype = torch.float16 if "cuda" in ARGS.qwen_device else torch.float32

    print(f"Loading bridge: {ARGS.bridge_path}...")
    ckpt = torch.load(ARGS.bridge_path, map_location="cpu", weights_only=False)
    checkpoint_qwen_model_id = ckpt.get("qwen_model_id", DEFAULT_QWEN)
    if ARGS.qwen_model_id != checkpoint_qwen_model_id:
        raise ValueError(
            "Checkpoint/model mismatch: "
            f"checkpoint trained on {checkpoint_qwen_model_id}, "
            f"but chat_server requested {ARGS.qwen_model_id}."
        )

    target_specs = normalize_target_specs(
        ckpt.get("target_specs") or ckpt.get("target_layers")
    )
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

    print(f"Patching layers: {target_specs}...")
    patched_layers = []
    for layer_idx, proj_name in target_specs:
        layer = MODEL.model.layers[layer_idx]
        original = getattr(layer.self_attn, proj_name)
        patched = DynamicLoRALinear(original)
        setattr(layer.self_attn, proj_name, patched)
        patched_layers.append(patched)

    target_dims = [(layer.in_features, layer.out_features) for layer in patched_layers]

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

    for patched, bias in zip(patched_layers, bias_vectors):
        patched.set_activation_bias(bias.squeeze(0).to(ARGS.qwen_device, dtype=torch.float32))

    print(f"\nBridge injected. Disposition: {episode['title']}")
    print(f"\n{'=' * 50}")
    print(f"Server starting on http://{ARGS.host}:{ARGS.port}")
    print(f"Open this on your phone: http://192.168.2.49:{ARGS.port}")
    print(f"Prompt labels: {ARGS.user_label} / {ARGS.model_label}")
    print(f"{'=' * 50}\n")

    server = HTTPServer((ARGS.host, ARGS.port), ChatHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        persist_conversation()
        print(f"Conversation saved to {LATEST_TRANSCRIPT_PATH}")


if __name__ == "__main__":
    main()
