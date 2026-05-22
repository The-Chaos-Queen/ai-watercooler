set -euo pipefail

cd /mnt/c/Users/tikii/bridge

/root/mocop_venv/bin/python3 -X utf8 - <<'PY'
import json
from pathlib import Path

import torch
import torch.nn.functional as F

import train_cheese_bridge as tcb
from models import build_activation_bias_hypernetwork

root = Path("/mnt/c/Users/tikii/bridge")
ckpt = torch.load(root / "mvp8_prompt_trace_episode_contrastive_1p5b.pt", map_location="cpu", weights_only=False)
bridge_cfg = ckpt["bridge_config"]
episodes = tcb.load_episodes(root / ckpt.get("episodes_file", "CHEESE_SHAPING_EPISODES.md"))
cache_dir = root / "mvp0_hidden_cache_smoke"

training = []
for ep in episodes:
    cache_path = tcb.mamba_state_cache_path(
        cache_dir,
        ep["episode_name"],
        ckpt.get("mamba_target_layer", tcb.MAMBA_TARGET_LAYER),
    )
    state = tcb.load_cached_mamba_state(cache_path).float()
    training.append((ep["header"], ep["episode_name"], state))

hidden_layer_count = int(ckpt.get("mamba_hidden_layer_count", 64) or 64)
context_encoder, resolved_context_dim, _ = tcb.build_context_encoder(
    skip_compressor=bool(bridge_cfg.get("skip_compressor", False)),
    hidden_layer_count=hidden_layer_count,
    context_dim=int(bridge_cfg.get("context_dim", tcb.DEFAULT_CONTEXT_DIM)),
)
context_encoder.load_state_dict(ckpt["context_encoder_state_dict"], strict=False)
context_encoder = context_encoder.float().eval()

hyper = build_activation_bias_hypernetwork(
    bridge_mode=bridge_cfg["bridge_mode"],
    context_dim=resolved_context_dim,
    target_dims=ckpt["target_dims"],
    hidden_dim=int(bridge_cfg.get("hyper_hidden_dim", tcb.DEFAULT_HYPER_HIDDEN_DIM)),
    rank=int(bridge_cfg.get("adapter_rank", tcb.DEFAULT_ADAPTER_RANK)),
    gate_kind=bridge_cfg.get("gate_kind", "vector"),
    initial_gate=float(bridge_cfg.get("initial_gate", 0.1)),
).float().eval()
hyper.load_state_dict(ckpt["hypernetwork_state_dict"])

raw_states = torch.cat([state for _, _, state in training], dim=0).float()
with torch.no_grad():
    context_vectors = context_encoder(raw_states)
    exported = hyper.export_input_adapter_state(context_vectors)
    adapter_vectors = tcb.flatten_exported_input_adapter_state(exported)

def cosine_matrix(x):
    n = F.normalize(x.float(), dim=-1)
    return (n @ n.T).cpu().tolist()

payload = {
    "names": [name for name, _, _ in training],
    "raw_state_cosine": cosine_matrix(raw_states),
    "context_cosine": cosine_matrix(context_vectors),
    "adapter_cosine": cosine_matrix(adapter_vectors),
    "context_norms": context_vectors.norm(dim=-1).cpu().tolist(),
    "adapter_norms": adapter_vectors.norm(dim=-1).cpu().tolist(),
}
print(json.dumps(payload, indent=2))
PY
