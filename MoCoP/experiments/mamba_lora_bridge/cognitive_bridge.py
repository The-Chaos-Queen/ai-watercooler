"""
cognitive_bridge.py - The Orchestrator

Connects the three components of the cognitive architecture:
    1. Mamba SSM     - Continuous state tracker ("gut feeling")
    2. Hypernetwork  - Translates Mamba state to injection parameters ("endocrine system")
    3. Qwen (base)   - Frozen Transformer ("brain structure")

The full cycle per turn:
    MUD text -> Mamba processes (state updates)
             -> Compressor flattens state to context vector
             -> Hypernetwork generates per-layer adjustments (LoRA matrices or activation biases)
             -> Adjustments injected into Qwen's attention layers
             -> Qwen generates response (raw completion, no chat template)
             -> Adjustments stripped
             -> Response returned

The Transformer's weights never change. The Mamba state accumulates
experience. The bridge injection is the interface between memory and behavior.

Supports two bridge modes:
    - "lora": Dynamic LoRA weight matrices (original, higher capacity but unstable)
    - "activation_bias": Additive bias vectors in residual stream (simpler, stable)

Author: Loom
Date: 2026-02-26
Review: Codex (2026-02-26), Purple (2026-03-20, v2: activation_bias inference)
"""

import argparse
import logging
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import torch
import torch.nn as nn

from model_defaults import DEFAULT_MAMBA_MODEL_ID, DEFAULT_QWEN_MODEL_ID
from models import MambaStateCompressor, LoRAHypernetwork, ActivationBiasHypernetwork, DynamicLoRALinear

logger = logging.getLogger("CognitiveBridge")

# Maximum Mamba history length in tokens before trimming.
# Mamba is O(n) per pass, so this caps per-turn compute cost.
MAX_MAMBA_HISTORY_TOKENS = 8192


@dataclass
class BridgeConfig:
    """Configuration for the cognitive bridge."""

    # --- Model selection ---
    qwen_model_id: str = DEFAULT_QWEN_MODEL_ID
    mamba_model_id: str = DEFAULT_MAMBA_MODEL_ID

    # --- Mamba state geometry ---
    mamba_layers: int = 64
    mamba_d_model: int = 2560
    mamba_d_state: int = 16
    mamba_target_layer: int = 3

    # --- Hypernetwork ---
    context_dim: int = 2048           # Compressor output / Hypernetwork input
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_scaling: Optional[float] = None
    hyper_hidden_dim: int = 1024

    # --- Layer targeting ---
    # Which Qwen layers to patch with dynamic LoRA.
    # Format: list of (layer_index, projection_name) tuples.
    # If None, auto-selects every 4th layer's q_proj and v_proj.
    target_layers: Optional[List[Tuple[int, str]]] = None

    # --- Generation ---
    max_new_tokens: int = 200
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1

    # --- Device ---
    device: str = "auto"              # "auto", "cuda", "cpu"
    hyper_device: str = "cpu"         # Hypernetwork can run on CPU to save VRAM

    # --- Quantization ---
    use_4bit: bool = True

    # --- Paths ---
    state_dir: str = "states"

    # --- History limit ---
    max_mamba_history_tokens: int = MAX_MAMBA_HISTORY_TOKENS

    # --- Bridge mode ---
    bridge_mode: str = "lora"  # "lora" | "activation_bias"

    # --- Startup validation ---
    # Runs a lightweight probe pass (Mamba -> compressor -> hypernetwork -> inject)
    # during load_models() so shape/dtype wiring errors fail fast at boot.
    startup_validation: bool = True
    startup_validation_text: str = "startup probe"

    def __post_init__(self):
        if self.bridge_mode not in {"lora", "activation_bias", "constant_bias"}:
            raise ValueError(
                f"bridge_mode must be 'lora', 'activation_bias', or 'constant_bias', "
                f"got {self.bridge_mode!r}"
            )
        if self.bridge_mode == "lora":
            if self.lora_rank <= 0:
                raise ValueError(f"lora_rank must be > 0, got {self.lora_rank}")
            if self.lora_alpha <= 0:
                raise ValueError(f"lora_alpha must be > 0, got {self.lora_alpha}")
        if self.mamba_target_layer < 0:
            raise ValueError(
                f"mamba_target_layer must be >= 0, got {self.mamba_target_layer}"
            )
        if self.lora_scaling is None:
            self.lora_scaling = self.lora_alpha / self.lora_rank


@dataclass
class TurnDiagnostics:
    """Diagnostics from a single generation turn."""
    turn_number: int
    mamba_state_mb: float
    context_vector_norm: float
    injection_norms: List[float]
    num_patched_layers: int
    generation_time_s: float
    input_tokens: int
    output_tokens: int
    raw_output: str


class CognitiveBridge:
    """
    The orchestrator that ties Mamba, the Hypernetwork, and Qwen together.

    This is the brain. Everything else (server.py, agent_wrapper.py) is
    just plumbing that feeds input to this and reads output from it.
    """

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.turn_count = 0
        self.diagnostics_history: List[TurnDiagnostics] = []

        # Models (loaded by load_models())
        self.qwen_model = None
        self.qwen_tokenizer = None
        self.mamba_model = None
        self.mamba_tokenizer = None
        self.compressor = None
        self.hypernetwork = None

        # Layer patching state — store specs alongside dynamic layers
        self._patched_layers: List[DynamicLoRALinear] = []
        self._patch_specs: List[Tuple[int, str]] = []  # Fix #4: store specs, not encoded strings
        self._original_layers: Dict[Tuple[int, str], nn.Module] = {}
        self._is_patched = False

        # Mamba state tracking
        self._mamba_cache = None
        self._mamba_history_ids: Optional[torch.Tensor] = None
        self._last_context_vector: Optional[torch.Tensor] = None

        # Devices
        self._qwen_device = None
        self._mamba_device = None
        self._hyper_device = None

    @staticmethod
    def _count_params_safe(module: nn.Module) -> Tuple[int, int]:
        """
        Count parameters without failing on LazyModule uninitialized tensors.

        Returns:
            (initialized_param_count, uninitialized_param_tensors)
        """
        total = 0
        uninitialized = 0
        for p in module.parameters():
            try:
                total += p.numel()
            except ValueError:
                uninitialized += 1
        return total, uninitialized

    def _resolve_mamba_state_geometry(self) -> Tuple[int, int, int]:
        model_config = getattr(self.mamba_model, "config", None)
        if model_config is None:
            return (
                self.config.mamba_layers,
                self.config.mamba_d_model,
                self.config.mamba_d_state,
            )

        layer_count = int(
            getattr(
                model_config,
                "num_hidden_layers",
                getattr(model_config, "n_layer", self.config.mamba_layers),
            )
        )
        state_width = int(
            getattr(
                model_config,
                "intermediate_size",
                getattr(model_config, "hidden_size", self.config.mamba_d_model),
            )
        )
        state_depth = int(getattr(model_config, "state_size", self.config.mamba_d_state))
        return layer_count, state_width, state_depth

    def load_models(self):
        """Load all three model components."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        # Resolve devices
        if self.config.device == "auto":
            self._qwen_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self._qwen_device = torch.device(self.config.device)
        self._mamba_device = self._qwen_device  # Mamba goes where Qwen goes
        self._hyper_device = torch.device(self.config.hyper_device)

        is_cpu = str(self._qwen_device) == "cpu"

        logger.info("Devices — Qwen: %s | Mamba: %s | Hyper: %s",
                     self._qwen_device, self._mamba_device, self._hyper_device)

        # --- Load Qwen (base model, frozen) ---
        logger.info("Loading Qwen: %s", self.config.qwen_model_id)
        model_kwargs: Dict[str, Any] = {"device_map": "auto"}

        if self.config.use_4bit and not is_cpu:
            from transformers import BitsAndBytesConfig
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:
            # Fix #6: Use float32 on CPU; float16 has poor CPU support
            model_kwargs["torch_dtype"] = torch.float32 if is_cpu else torch.float16

        self.qwen_tokenizer = AutoTokenizer.from_pretrained(
            self.config.qwen_model_id, use_fast=True
        )
        self.qwen_model = AutoModelForCausalLM.from_pretrained(
            self.config.qwen_model_id, **model_kwargs
        )
        self.qwen_model.eval()
        for param in self.qwen_model.parameters():
            param.requires_grad = False

        if self.qwen_tokenizer.pad_token_id is None:
            self.qwen_tokenizer.pad_token = self.qwen_tokenizer.eos_token

        logger.info("Qwen loaded. Parameters: %s",
                     f"{sum(p.numel() for p in self.qwen_model.parameters()):,}")

        # --- Load Mamba ---
        logger.info("Loading Mamba: %s", self.config.mamba_model_id)
        # Fix #6: Use float32 on CPU
        mamba_dtype = torch.float32 if is_cpu else torch.float16
        self.mamba_tokenizer = AutoTokenizer.from_pretrained(self.config.mamba_model_id)
        self.mamba_model = AutoModelForCausalLM.from_pretrained(
            self.config.mamba_model_id,
            torch_dtype=mamba_dtype,
        )
        if not is_cpu:
            self.mamba_model = self.mamba_model.to(self._mamba_device)
        self.mamba_model.eval()
        for param in self.mamba_model.parameters():
            param.requires_grad = False
        logger.info("Mamba loaded.")

        resolved_mamba_layers, resolved_mamba_d_model, resolved_mamba_d_state = (
            self._resolve_mamba_state_geometry()
        )
        logger.info(
            "Resolved Mamba state geometry | layers=%d | width=%d | state=%d",
            resolved_mamba_layers,
            resolved_mamba_d_model,
            resolved_mamba_d_state,
        )

        # --- Determine target layers and validate ---
        target_specs = self._resolve_target_layers()
        self._validate_target_specs(target_specs)  # Fix #10

        # Build per-layer dimension list for the hypernetwork.
        # Each target layer can have its own (in_dim, out_dim),
        # enabling full GQA coverage (q_proj and v_proj may differ).
        target_dims = [
            (self._get_layer_module(s).in_features,
             self._get_layer_module(s).out_features)
            for s in target_specs
        ]
        logger.info("Target layers: %d | Unique dims: %s",
                     len(target_specs),
                     sorted(set(target_dims)))

        # --- Initialize Compressor + Hypernetwork ---
        self.compressor = MambaStateCompressor(
            resolved_mamba_layers,
            resolved_mamba_d_model,
            resolved_mamba_d_state,
            self.config.context_dim,
            target_layer=self.config.mamba_target_layer,
        ).to(self._hyper_device)

        if self.config.bridge_mode == "activation_bias":
            self.hypernetwork = ActivationBiasHypernetwork(
                context_dim=self.config.context_dim,
                target_dims=target_dims,
                hidden_dim=self.config.hyper_hidden_dim,
            ).to(self._hyper_device)
        else:
            self.hypernetwork = LoRAHypernetwork(
                context_dim=self.config.context_dim,
                target_dims=target_dims,
                lora_rank=self.config.lora_rank,
                hidden_dim=self.config.hyper_hidden_dim,
            ).to(self._hyper_device)

        # Count parameters safely so startup logs fail cleanly if a future module
        # reintroduces deferred initialization.
        hyper_params, hyper_uninit = self._count_params_safe(self.hypernetwork)
        comp_params, comp_uninit = self._count_params_safe(self.compressor)
        if hyper_uninit or comp_uninit:
            logger.info(
                "Hypernetwork params: %s | Compressor params (initialized): %s | "
                "Uninitialized lazy params: hyper=%d compressor=%d",
                f"{hyper_params:,}", f"{comp_params:,}", hyper_uninit, comp_uninit
            )
        else:
            logger.info(
                "Hypernetwork params: %s | Compressor params: %s",
                f"{hyper_params:,}", f"{comp_params:,}"
            )

        # --- Patch Qwen ---
        self._patch_transformer(target_specs)
        self._startup_validate_pipeline()
        logger.info("Cognitive Bridge loaded. Ready for input.")

    def _resolve_target_layers(self) -> List[Tuple[int, str]]:
        """
        Determine which Qwen layers to patch.

        Default strategy: every 4th decoder layer, q_proj and v_proj.
        This balances coverage against hypernetwork output size.
        """
        if self.config.target_layers is not None:
            return self.config.target_layers

        num_decoder_layers = len(self.qwen_model.model.layers)
        targets = []
        for i in range(0, num_decoder_layers, 4):
            targets.append((i, "q_proj"))
            targets.append((i, "v_proj"))

        logger.info("Auto-selected %d target projections across %d decoder layers",
                     len(targets), num_decoder_layers)
        return targets

    def _validate_target_specs(self, specs: List[Tuple[int, str]]):
        """
        Validate target layer specs. Fix #10: fail fast with clear errors.
        """
        if not specs:
            raise ValueError("target_layers is empty. At least one target required.")

        num_layers = len(self.qwen_model.model.layers)
        valid_projections = {"q_proj", "k_proj", "v_proj", "o_proj"}

        for idx, (layer_idx, proj_name) in enumerate(specs):
            if not isinstance(layer_idx, int) or layer_idx < 0 or layer_idx >= num_layers:
                raise ValueError(
                    f"Target spec [{idx}]: layer_idx={layer_idx} out of range "
                    f"[0, {num_layers})"
                )
            if proj_name not in valid_projections:
                raise ValueError(
                    f"Target spec [{idx}]: proj_name='{proj_name}' not in "
                    f"{valid_projections}"
                )



    def _get_layer_module(self, spec: Tuple[int, str]) -> nn.Linear:
        """Get the nn.Linear module at the given (layer_idx, proj_name) spec."""
        layer_idx, proj_name = spec
        decoder_layer = self.qwen_model.model.layers[layer_idx]
        return getattr(decoder_layer.self_attn, proj_name)

    def _set_layer_module(self, spec: Tuple[int, str], module: nn.Module):
        """Set the module at the given spec."""
        layer_idx, proj_name = spec
        decoder_layer = self.qwen_model.model.layers[layer_idx]
        setattr(decoder_layer.self_attn, proj_name, module)

    def _patch_transformer(self, target_specs: List[Tuple[int, str]]):
        """Replace target nn.Linear layers with DynamicLoRALinear wrappers."""
        self._patched_layers = []
        self._patch_specs = []      # Fix #4: store specs as tuples
        self._original_layers = {}

        for spec in target_specs:
            original = self._get_layer_module(spec)

            # Fix #4: Use the spec tuple directly as key, not an encoded string
            self._original_layers[spec] = original

            dynamic = DynamicLoRALinear(
                original, scaling=self.config.lora_scaling
            )
            self._set_layer_module(spec, dynamic)
            self._patched_layers.append(dynamic)
            self._patch_specs.append(spec)

        self._is_patched = True
        logger.info("Patched %d layers with DynamicLoRALinear", len(self._patched_layers))

    def unpatch_transformer(self):
        """Restore original nn.Linear layers. Fix #4: use stored spec tuples."""
        if not self._is_patched:
            return
        for spec, original in self._original_layers.items():
            self._set_layer_module(spec, original)
        self._patched_layers = []
        self._patch_specs = []
        self._original_layers = {}
        self._is_patched = False
        logger.info("Unpatched transformer. Restored original layers.")

    def _trim_mamba_history(self):
        """
        Fix #9: Cap Mamba history length.
        If history exceeds max, keep the most recent tokens.
        The SSM state from earlier tokens is already baked into the
        Mamba cache; we just need enough history to reconstruct it.
        """
        if self._mamba_history_ids is None:
            return
        max_len = self.config.max_mamba_history_tokens
        if self._mamba_history_ids.shape[1] > max_len:
            trimmed = self._mamba_history_ids.shape[1] - max_len
            self._mamba_history_ids = self._mamba_history_ids[:, -max_len:]
            logger.info("Trimmed Mamba history: removed %d tokens, kept %d",
                        trimmed, max_len)

    def feed_mamba(self, text: str) -> torch.Tensor:
        """
        Feed text into Mamba and return the updated SSM hidden state.

        Uses batch prefill: tokenize the full text and process in one pass.
        The Mamba state accumulates across calls (continuous experience).

        Returns:
            state_tensor: (1, num_layers, d_model, d_state)

        Raises:
            RuntimeError: If Mamba output has no cache object with ssm_states
        """
        input_ids = self.mamba_tokenizer.encode(text, return_tensors="pt")
        if str(self._mamba_device) != "cpu":
            input_ids = input_ids.to(self._mamba_device)

        # Append to history for continuous state accumulation
        if self._mamba_history_ids is not None:
            self._mamba_history_ids = torch.cat(
                [self._mamba_history_ids, input_ids], dim=1
            )
        else:
            self._mamba_history_ids = input_ids

        # Fix #9: Trim history if too long
        self._trim_mamba_history()

        # Process through Mamba — full history each time for correct state
        with torch.inference_mode():
            outputs = self.mamba_model(
                self._mamba_history_ids,
                use_cache=True,
            )

        # Extract the SSM cache (the hidden state). Prefer cache_params, but
        # also support implementations that expose it via past_key_values.
        cache = getattr(outputs, "cache_params", None)
        if cache is None:
            cache = getattr(outputs, "past_key_values", None)

        # Fix #5: Fail fast instead of broken fallback tensor math
        if cache is None or not hasattr(cache, 'ssm_states'):
            raise RuntimeError(
                "Mamba model did not return a cache object with ssm_states. "
                f"Model: {self.config.mamba_model_id}. "
                "The HuggingFace Mamba implementation may have changed. "
                "Check model output attributes: "
                f"{[attr for attr in dir(outputs) if not attr.startswith('_')]}"
            )

        self._mamba_cache = cache
        ssm_states = cache.ssm_states  # list of (batch, d_model, d_state)
        state_tensor = torch.stack(ssm_states, dim=1)  # (batch, layers, d_model, d_state)

        return state_tensor

    def _inject_lora(
        self, context_vector: torch.Tensor
    ) -> List[float]:
        """
        Generate LoRA matrices from context vector and inject into Qwen.

        Fix #12: Takes pre-computed context_vector (no duplicate compression).

        Args:
            context_vector: (1, context_dim) — already compressed from Mamba state.

        Returns:
            List of LoRA matrix norms (for diagnostics).
        """
        with torch.inference_mode():
            # Keep input dtype aligned with hypernetwork weights to avoid matmul dtype errors.
            hyper_dtype = next(self.hypernetwork.parameters()).dtype
            context_vector = context_vector.to(device=self._hyper_device, dtype=hyper_dtype)
            lora_pairs = self.hypernetwork(context_vector)  # List of (A, B)

        # Inject into patched layers
        if len(lora_pairs) != len(self._patched_layers):
            raise RuntimeError(
                f"Hypernetwork produced {len(lora_pairs)} LoRA pairs but "
                f"{len(self._patched_layers)} layers are patched"
            )
        norms = []
        for dynamic_layer, (A, B) in zip(self._patched_layers, lora_pairs):
            # For 4-bit quantized base layers, weight dtype can be uint8.
            # Keep LoRA tensors floating and only move to target device.
            # DynamicLoRALinear will cast to runtime activation dtype in forward().
            qwen_device = dynamic_layer.weight.device
            A_dev = A.to(device=qwen_device)
            B_dev = B.to(device=qwen_device)
            dynamic_layer.set_lora(A_dev, B_dev)
            norms.append(float(A_dev.float().norm()) + float(B_dev.float().norm()))

        return norms

    def _inject_activation_bias(
        self, context_vector: torch.Tensor
    ) -> List[float]:
        """
        Generate activation bias vectors from context and inject into Qwen.

        Args:
            context_vector: (1, context_dim) — compressed Mamba state.

        Returns:
            List of bias vector norms (for diagnostics).
        """
        with torch.inference_mode():
            hyper_dtype = next(self.hypernetwork.parameters()).dtype
            context_vector = context_vector.to(device=self._hyper_device, dtype=hyper_dtype)
            bias_vectors = self.hypernetwork(context_vector)  # List[Tensor (1, out_dim)]

        if len(bias_vectors) != len(self._patched_layers):
            raise RuntimeError(
                f"Hypernetwork produced {len(bias_vectors)} bias vectors but "
                f"{len(self._patched_layers)} layers are patched"
            )
        norms = []
        for dynamic_layer, bias in zip(self._patched_layers, bias_vectors):
            qwen_device = dynamic_layer.weight.device
            bias_dev = bias.squeeze(0).to(device=qwen_device)  # (out_dim,)
            dynamic_layer.set_activation_bias(bias_dev)
            norms.append(float(bias_dev.float().norm()))

        return norms

    def _clear_injections(self):
        """Clear all dynamic LoRA and activation bias state from patched layers."""
        for layer in self._patched_layers:
            layer.clear_lora()  # clear_lora() clears A, B, AND bias

    def _startup_validate_pipeline(self):
        """
        Lightweight boot-time validation of core tensor wiring.

        Catches shape/dtype/injection failures before the service starts
        accepting requests.
        """
        if not self.config.startup_validation:
            logger.info("Startup pipeline validation disabled by config.")
            return

        probe_text = (self.config.startup_validation_text or "").strip() or "startup probe"
        saved_history = self._mamba_history_ids
        saved_cache = self._mamba_cache
        saved_context = self._last_context_vector

        try:
            probe_state = self.feed_mamba(probe_text)
            with torch.inference_mode():
                comp_dtype = next(self.compressor.parameters()).dtype
                probe_state = probe_state.to(device=self._hyper_device, dtype=comp_dtype)
                probe_context = self.compressor(probe_state)
            if self.config.bridge_mode == "activation_bias":
                self._inject_activation_bias(probe_context)
            else:
                self._inject_lora(probe_context)
            logger.info("Startup pipeline validation passed (%s mode).", self.config.bridge_mode)
        except Exception as exc:
            raise RuntimeError(f"Startup pipeline validation failed: {exc}") from exc
        finally:
            self._clear_injections()
            self._mamba_history_ids = saved_history
            self._mamba_cache = saved_cache
            self._last_context_vector = saved_context

    def generate(self, mud_text: str) -> TurnDiagnostics:
        """
        Full cognitive cycle: process input → inject LoRA → generate → clean up.

        Fix #3: LoRA cleanup is guaranteed via try/finally.

        Args:
            mud_text: The raw MUD output (room descriptions, events, etc.)

        Returns:
            TurnDiagnostics with the generated response and metrics.
        """
        t_start = time.time()
        self.turn_count += 1

        # 1. Feed text to Mamba (state accumulates)
        mamba_state = self.feed_mamba(mud_text)
        state_mb = mamba_state.nelement() * mamba_state.element_size() / (1024 * 1024)

        # 2. Compress Mamba state to context vector (Fix #12: compute once)
        with torch.inference_mode():
            # Keep input dtype aligned with compressor weights to avoid matmul dtype errors
            # when state moves across devices (e.g., Half on CUDA -> Float on CPU).
            comp_dtype = next(self.compressor.parameters()).dtype
            state_for_compressor = mamba_state.to(device=self._hyper_device, dtype=comp_dtype)
            context_vec = self.compressor(state_for_compressor)
            self._last_context_vector = context_vec.detach().to("cpu")
        context_norm = float(context_vec.norm())

        # Fix #3: try/finally guarantees LoRA cleanup even on generation failure
        try:
            # 3. Inject bridge adjustments (LoRA or activation bias)
            if self.config.bridge_mode == "activation_bias":
                lora_norms = self._inject_activation_bias(context_vec)
            else:
                lora_norms = self._inject_lora(context_vec)

            # 4. Generate with Qwen (base model, raw completion)
            prompt = self._format_prompt(mud_text)
            input_ids = self.qwen_tokenizer.encode(prompt, return_tensors="pt")
            qwen_device = next(self.qwen_model.parameters()).device
            input_ids = input_ids.to(qwen_device)
            input_len = input_ids.shape[1]

            with torch.inference_mode():
                generated = self.qwen_model.generate(
                    input_ids,
                    max_new_tokens=self.config.max_new_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                    repetition_penalty=self.config.repetition_penalty,
                    do_sample=True,
                    pad_token_id=self.qwen_tokenizer.pad_token_id,
                    eos_token_id=self.qwen_tokenizer.eos_token_id,
                )

            output_ids = generated[0][input_len:]
            raw_output = self.qwen_tokenizer.decode(output_ids, skip_special_tokens=True)

        finally:
            # 5. ALWAYS clear LoRA, even if generation threw
            self._clear_injections()

        t_end = time.time()

        # 6. Build diagnostics
        diag = TurnDiagnostics(
            turn_number=self.turn_count,
            mamba_state_mb=state_mb,
            context_vector_norm=context_norm,
            injection_norms=lora_norms,
            num_patched_layers=len(self._patched_layers),
            generation_time_s=t_end - t_start,
            input_tokens=input_len,
            output_tokens=len(output_ids),
            raw_output=raw_output,
        )
        self.diagnostics_history.append(diag)

        logger.info(
            "Turn %d | State: %.1f MB | CtxNorm: %.2f | "
            "Tokens: %d->%d | Time: %.1fs",
            diag.turn_number, diag.mamba_state_mb, diag.context_vector_norm,
            diag.input_tokens, diag.output_tokens, diag.generation_time_s,
        )

        return diag

    def _format_prompt(self, mud_text: str) -> str:
        """
        Format the prompt for a base model.

        No chat template. No system instructions. This is raw text that
        the base model will continue. The formatting mimics what game logs
        and MUD transcripts look like in pretraining data.

        The wolf doesn't need instructions. It needs context.
        """
        prompt = (
            f"[Game World]\n"
            f"{mud_text}\n\n"
            f"[Action]\n"
        )
        return prompt

    # --- State Persistence ---

    def save_state(self, path: Optional[str] = None) -> str:
        """
        Save the full cognitive state: Mamba SSM state + Hypernetwork weights.

        Returns the path to the saved state file.
        """
        if path is None:
            state_dir = Path(self.config.state_dir)
            path = str(state_dir / f"cognitive_state_turn_{self.turn_count}.pt")

        # Fix #1: Validate path stays within state_dir
        resolved = Path(path).resolve()
        allowed_dir = Path(self.config.state_dir).resolve()
        if not str(resolved).startswith(str(allowed_dir)):
            raise ValueError(
                f"State path {resolved} is outside allowed directory {allowed_dir}"
            )

        resolved.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "turn_count": self.turn_count,
            "mamba_history_ids": (
                self._mamba_history_ids.cpu()
                if self._mamba_history_ids is not None else None
            ),
            "hypernetwork_state_dict": self.hypernetwork.state_dict(),
            "compressor_state_dict": self.compressor.state_dict(),
            "config": {
                "qwen_model_id": self.config.qwen_model_id,
                "mamba_model_id": self.config.mamba_model_id,
                "context_dim": self.config.context_dim,
                "lora_rank": self.config.lora_rank,
                "bridge_mode": self.config.bridge_mode,
            },
        }

        # Save Mamba SSM state if available
        if self._mamba_cache is not None and hasattr(self._mamba_cache, 'ssm_states'):
            state["mamba_ssm_states"] = [s.cpu() for s in self._mamba_cache.ssm_states]

        torch.save(state, str(resolved))
        logger.info("Saved cognitive state to %s", resolved)
        return str(resolved)

    def load_state(self, path: str):
        """
        Load a previously saved cognitive state.

        Fix #1: Validates path is within state_dir.
        Fix #8: Uses map_location for cross-device compatibility.
        """
        resolved = Path(path).resolve()
        allowed_dir = Path(self.config.state_dir).resolve()
        if not str(resolved).startswith(str(allowed_dir)):
            raise ValueError(
                f"State path {resolved} is outside allowed directory {allowed_dir}"
            )
        if not resolved.exists():
            raise FileNotFoundError(f"State file not found: {resolved}")

        # Fix #8: map_location for cross-device loading
        map_loc = str(self._hyper_device) if self._hyper_device else "cpu"
        state = torch.load(str(resolved), map_location=map_loc, weights_only=True)

        saved_mode = state.get("config", {}).get("bridge_mode", "lora")
        if saved_mode != self.config.bridge_mode:
            raise ValueError(
                f"Checkpoint bridge_mode={saved_mode!r} does not match "
                f"config bridge_mode={self.config.bridge_mode!r}"
            )

        self.turn_count = state["turn_count"]
        history = state.get("mamba_history_ids")
        if history is not None and str(self._mamba_device) != "cpu":
            history = history.to(self._mamba_device)
        self._mamba_history_ids = history

        if "hypernetwork_state_dict" in state:
            self.hypernetwork.load_state_dict(state["hypernetwork_state_dict"])
        if "compressor_state_dict" in state:
            self.compressor.load_state_dict(state["compressor_state_dict"])

        logger.info("Loaded cognitive state from %s (turn %d)", resolved, self.turn_count)

    # --- Diagnostics ---

    def get_info(self) -> Dict[str, Any]:
        """Return a summary of the bridge's current state."""
        info = {
            "turn_count": self.turn_count,
            "patched_layers": len(self._patched_layers),
            "is_patched": self._is_patched,
            "qwen_model": self.config.qwen_model_id,
            "mamba_model": self.config.mamba_model_id,
            "lora_rank": self.config.lora_rank,
            "bridge_mode": self.config.bridge_mode,
            "context_dim": self.config.context_dim,
            "startup_validation": self.config.startup_validation,
            "devices": {
                "qwen": str(self._qwen_device),
                "mamba": str(self._mamba_device),
                "hyper": str(self._hyper_device),
            },
        }

        if self._mamba_history_ids is not None:
            info["mamba_history_tokens"] = self._mamba_history_ids.shape[1]

        if self.diagnostics_history:
            last = self.diagnostics_history[-1]
            info["last_turn"] = {
                "mamba_state_mb": last.mamba_state_mb,
                "context_norm": last.context_vector_norm,
                "generation_time_s": last.generation_time_s,
            }
        if self._last_context_vector is not None:
            info["last_context_vector_dim"] = int(self._last_context_vector.shape[-1])

        return info

    def get_last_context_vector(self) -> Optional[torch.Tensor]:
        """Return a detached CPU copy of the last context vector, if available."""
        if self._last_context_vector is None:
            return None
        return self._last_context_vector.clone()


# ===========================================================================
# Standalone smoke test
# ===========================================================================
if __name__ == "__main__":
    """
    Quick test: can the bridge load and process a single turn?
    Run with: python cognitive_bridge.py

    This will attempt to load the configured Mamba + Qwen base models.
    If you don't have the models cached, it will download them.
    If you don't have enough VRAM, set use_4bit=True and/or
    adjust device settings.
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 60)
    print("COGNITIVE BRIDGE - Smoke Test")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Standalone smoke test for CognitiveBridge.")
    parser.add_argument("--qwen-model-id", type=str, default=DEFAULT_QWEN_MODEL_ID)
    parser.add_argument("--mamba-model-id", type=str, default=DEFAULT_MAMBA_MODEL_ID)
    parser.add_argument("--bridge-mode", type=str, default="lora",
                        choices=["lora", "activation_bias"])
    args = parser.parse_args()

    config = BridgeConfig(
        qwen_model_id=args.qwen_model_id,
        mamba_model_id=args.mamba_model_id,
        bridge_mode=args.bridge_mode,
        use_4bit=True,
        hyper_device="cpu",
        max_new_tokens=100,
    )

    bridge = CognitiveBridge(config)

    try:
        bridge.load_models()
    except Exception as e:
        print(f"\nFailed to load models: {e}")
        print("This is expected if models aren't cached or VRAM is insufficient.")
        sys.exit(1)

    print("\nBridge info:", json.dumps(bridge.get_info(), indent=2))

    # Test turn
    test_input = (
        "You are standing in the Town Square. The cobblestones are worn smooth "
        "by centuries of foot traffic. To the north, warm light spills from the "
        "Tavern doorway. An old well stands in the center of the square. "
        "Thornwick waves at you."
    )

    print(f"\nInput: {test_input[:80]}...")
    diag = bridge.generate(test_input)
    print(f"\nOutput: {diag.raw_output}")
    print(f"\nDiagnostics:")
    print(f"  Mamba state:  {diag.mamba_state_mb:.1f} MB")
    print(f"  Context norm: {diag.context_vector_norm:.4f}")
    print(f"  Inject norms: {[f'{n:.4f}' for n in diag.injection_norms[:4]]}...")
    print(f"  Time:         {diag.generation_time_s:.2f}s")
    print(f"  Tokens:       {diag.input_tokens} -> {diag.output_tokens}")

    # Save state
    state_path = bridge.save_state()
    print(f"\nState saved to: {state_path}")
    print("\n--- Smoke Test Complete ---")
