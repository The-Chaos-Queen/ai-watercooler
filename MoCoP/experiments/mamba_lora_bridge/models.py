"""
models.py - Core neural network modules for the Cognitive Bridge.

Components:
    MambaStateCompressor    - 3D SSM state -> flat context vector
    RawStateProjector       - 3D SSM state -> raw flat context vector
    ZeroContextEncoder      - batch size -> constant zero context vector
    LoRAHypernetwork        - Context vector -> per-layer dynamic LoRA matrices
    ActivationBiasHypernetwork - Context vector -> per-layer additive bias vectors
    ConstantBiasBridge      - learned per-layer constant bias vectors
    DynamicLoRALinear       - Drop-in nn.Linear replacement with injectable LoRA/bias

The DynamicLoRALinear uses a context-managed pattern (set_lora / clear_lora)
so it preserves the standard nn.Linear forward(x) signature. This means
HuggingFace's model.generate() works without any monkey-patching.

Author: Loom (refactored from Codex/Gemini skeleton)
Date: 2026-02-26
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, List, Tuple


class MambaStateCompressor(nn.Module):
    """
    Compresses either:
    - a 4D Mamba SSM state tensor [batch, num_layers, d_model, d_state], or
    - a 2D last-token hidden state tensor [batch, d_model]
    into a flat context vector.

    For SSM state input, it extracts one target layer and flattens the
    (d_model, d_state) slice. For last-token hidden-state input, the hidden
    vector is already collapsed to width d_model, so mamba_d_state should be 1.
    """

    def __init__(
        self,
        mamba_layers: int,
        mamba_d_model: int,
        mamba_d_state: int,
        output_dim: int,
        target_layer: int = 3, # Targeting Layer 3 specifically
    ):
        super().__init__()
        self.mamba_layers = mamba_layers
        self.mamba_d_model = mamba_d_model
        self.mamba_d_state = mamba_d_state
        self.output_dim = output_dim
        self.target_layer = target_layer
        self.input_flat_size = mamba_d_model * mamba_d_state

        # Keep the projection shape explicit so optimizer parameter registration
        # is complete before the first training step.
        self.projection = nn.Sequential(
            nn.Linear(self.input_flat_size, output_dim),
            nn.LayerNorm(output_dim),
            nn.SiLU(),
        )

    def forward(self, mamba_state: torch.Tensor) -> torch.Tensor:
        """
        Args:
            mamba_state:
                - (batch, num_layers, d_model, d_state) for SSM state input, or
                - (batch, d_model) for last-token hidden-state input
        Returns:
            context_vector: (batch, output_dim)
        """
        if mamba_state.dim() == 4:
            if mamba_state.size(1) <= self.target_layer:
                raise ValueError(
                    f"Mamba state only has {mamba_state.size(1)} layers, "
                    f"cannot extract layer {self.target_layer}"
                )

            # Slice precisely at the target layer instead of mixing layers.
            targeted_state = mamba_state[:, self.target_layer]
            batch_size = mamba_state.size(0)
            flat = targeted_state.reshape(batch_size, -1)
        elif mamba_state.dim() == 2:
            # Last-token hidden-state mode: input is already one vector per sample.
            flat = mamba_state
        else:
            raise ValueError(
                "MambaStateCompressor expected a 4D SSM tensor or 2D hidden-state "
                f"tensor, got shape {tuple(mamba_state.shape)}."
            )

        if flat.shape[1] != self.input_flat_size:
            raise RuntimeError(
                "Mamba state feature width changed after compressor initialization: "
                f"got {flat.shape[1]}, expected {self.input_flat_size}."
            )

        # Align dtype with module weights (important when state originates as fp16
        # but compressor runs in fp32 on CPU).
        proj_dtype = self.projection[1].weight.dtype
        if flat.dtype != proj_dtype:
            flat = flat.to(dtype=proj_dtype)

        # Project to context vector
        return self.projection(flat)


class RawStateProjector(nn.Module):
    """
    Extracts the target Mamba layer and flattens it directly with no bottleneck.

    This is the minimal compressor-bypass control: Layer 3 still defines the
    source state, but the hypernetwork receives the raw flattened vector.

    Supports either:
    - a 4D Mamba SSM state tensor [batch, num_layers, d_model, d_state], or
    - a 2D hidden-last-token tensor [batch, d_model]
    """

    def __init__(
        self,
        mamba_layers: int,
        mamba_d_model: int,
        mamba_d_state: int,
        target_layer: int = 3,
    ):
        super().__init__()
        self.mamba_layers = mamba_layers
        self.mamba_d_model = mamba_d_model
        self.mamba_d_state = mamba_d_state
        self.target_layer = target_layer
        self.input_flat_size = mamba_d_model * mamba_d_state
        self.output_dim = self.input_flat_size

        # Keep a device/dtype anchor so the trainer can treat this module like
        # the learned compressor for casting/moving inputs.
        self.register_buffer("_dtype_anchor", torch.empty(0), persistent=False)

    def forward(self, mamba_state: torch.Tensor) -> torch.Tensor:
        if mamba_state.dim() == 4:
            if mamba_state.size(1) <= self.target_layer:
                raise ValueError(
                    f"Mamba state only has {mamba_state.size(1)} layers, cannot extract layer {self.target_layer}"
                )

            targeted_state = mamba_state[:, self.target_layer]
            batch_size = mamba_state.size(0)
            flat = targeted_state.reshape(batch_size, -1)
        elif mamba_state.dim() == 2:
            flat = mamba_state
        else:
            raise ValueError(
                "RawStateProjector expected a 4D SSM tensor or 2D hidden-state "
                f"tensor, got shape {tuple(mamba_state.shape)}."
            )

        if flat.shape[1] != self.input_flat_size:
            raise RuntimeError(
                "Mamba state feature width changed after raw-state projector initialization: "
                f"got {flat.shape[1]}, expected {self.input_flat_size}."
            )

        anchor_dtype = self._dtype_anchor.dtype
        if flat.dtype != anchor_dtype:
            flat = flat.to(dtype=anchor_dtype)
        return flat


class ZeroContextEncoder(nn.Module):
    """
    Emits a learned-nothing zero context for modes that do not use Mamba.

    The output width stays explicit so the trainer can keep its context/hypernet
    plumbing uniform across bridge modes.
    """

    def __init__(self, output_dim: int = 1):
        super().__init__()
        self.output_dim = output_dim
        self.register_buffer("_dtype_anchor", torch.empty(0), persistent=False)

    def forward(self, batch_size: int) -> torch.Tensor:
        return torch.zeros(
            batch_size,
            self.output_dim,
            device=self._dtype_anchor.device,
            dtype=self._dtype_anchor.dtype,
        )


class LoRAHypernetwork(nn.Module):
    """
    Takes a context vector and outputs per-layer LoRA A and B matrices.

    Architecture: Shared MLP backbone + per-layer output heads.
    This allows the backbone to learn a general representation of the
    Mamba state, while each head specializes for its target layer.

    Each target layer can have its own (in_dim, out_dim), enabling
    full GQA coverage where q_proj and v_proj have different sizes.

    For N target layers, outputs N pairs of (A, B) matrices.
    A_i has shape (target_dims[i][0], lora_rank).
    B_i has shape (lora_rank, target_dims[i][1]).
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        lora_rank: int,
        hidden_dim: int = 1024,
    ):
        super().__init__()
        self.target_dims = target_dims
        self.lora_rank = lora_rank
        self.num_target_layers = len(target_dims)

        # Shared backbone
        self.backbone = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )

        # Per-layer output heads, each sized to its target's dimensions
        self.heads_A = nn.ModuleList()
        self.heads_B = nn.ModuleList()
        for in_dim, out_dim in target_dims:
            self.heads_A.append(nn.Linear(hidden_dim, in_dim * lora_rank))
            self.heads_B.append(nn.Linear(hidden_dim, lora_rank * out_dim))

        # Initialize output heads with small weights so initial LoRA
        # contribution is near-zero (the system starts "quiet")
        for head in list(self.heads_A) + list(self.heads_B):
            nn.init.normal_(head.weight, std=0.01)
            nn.init.zeros_(head.bias)

    def forward(
        self, context_vector: torch.Tensor
    ) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """
        Args:
            context_vector: (batch, context_dim)
        Returns:
            List of (A, B) tuples, one per target layer.
            A_i: (batch, in_dim_i, lora_rank)
            B_i: (batch, lora_rank, out_dim_i)
        """
        # Align dtype with backbone weights to avoid matmul dtype mismatches.
        backbone_dtype = self.backbone[0].weight.dtype
        if context_vector.dtype != backbone_dtype:
            context_vector = context_vector.to(dtype=backbone_dtype)
        hidden = self.backbone(context_vector)

        pairs = []
        for head_A, head_B, (in_dim, out_dim) in zip(
            self.heads_A, self.heads_B, self.target_dims
        ):
            flat_A = head_A(hidden)
            flat_B = head_B(hidden)

            A = flat_A.view(-1, in_dim, self.lora_rank)
            B = flat_B.view(-1, self.lora_rank, out_dim)
            pairs.append((A, B))

        return pairs


class ActivationBiasHypernetwork(nn.Module):
    """
    Takes a context vector and outputs one additive bias vector per target layer.

    Each target layer receives a bias shaped to that projection's output width,
    so the wrapper can add it directly to the projection activations.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
    ):
        super().__init__()
        self.target_dims = target_dims
        self.num_target_layers = len(target_dims)

        self.backbone = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )

        self.bias_heads = nn.ModuleList()
        for _, out_dim in target_dims:
            self.bias_heads.append(nn.Linear(hidden_dim, out_dim))

        for head in self.bias_heads:
            nn.init.normal_(head.weight, std=0.01)
            nn.init.zeros_(head.bias)

    def encode_hidden(self, context_vector: torch.Tensor) -> torch.Tensor:
        backbone_dtype = self.backbone[0].weight.dtype
        if context_vector.dtype != backbone_dtype:
            context_vector = context_vector.to(dtype=backbone_dtype)
        return self.backbone(context_vector)

    def forward_from_hidden(self, hidden: torch.Tensor) -> List[torch.Tensor]:
        return [head(hidden) for head in self.bias_heads]

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        hidden = self.encode_hidden(context_vector)
        return self.forward_from_hidden(hidden)


class GatedActivationBiasHypernetwork(ActivationBiasHypernetwork):
    """
    Activation-bias hypernetwork with a learned per-instance residual gate.

    This is the smallest honest step toward CAGMamba-style gating: the bridge
    still predicts additive bias vectors, but it also learns a feature-wise
    gate that can attenuate or open each target surface per sample.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
        gate_kind: str = "vector",
        initial_gate: float = 0.1,
    ):
        super().__init__(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
        )
        if gate_kind not in {"scalar", "vector"}:
            raise ValueError(
                f"gate_kind must be 'scalar' or 'vector', got {gate_kind!r}"
            )

        self.gate_kind = gate_kind
        self.initial_gate = float(max(1e-4, min(1.0 - 1e-4, initial_gate)))
        gate_bias_init = math.log(self.initial_gate / (1.0 - self.initial_gate))

        self.gate_heads = nn.ModuleList()
        for _, out_dim in target_dims:
            gate_out_dim = 1 if gate_kind == "scalar" else out_dim
            self.gate_heads.append(nn.Linear(hidden_dim, gate_out_dim))

        for head in self.gate_heads:
            nn.init.zeros_(head.weight)
            nn.init.constant_(head.bias, gate_bias_init)

    def forward_with_gates(
        self,
        context_vector: torch.Tensor,
    ) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)

        gate_values: List[torch.Tensor] = []
        gated_biases: List[torch.Tensor] = []
        for raw_bias, gate_head in zip(raw_biases, self.gate_heads):
            gate = torch.sigmoid(gate_head(hidden))
            if gate.shape[-1] == 1 and raw_bias.shape[-1] != 1:
                gate = gate.expand(-1, raw_bias.shape[-1])
            gate_values.append(gate)
            gated_biases.append(raw_bias * gate)

        return gated_biases, gate_values, raw_biases

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        gated_biases, _, _ = self.forward_with_gates(context_vector)
        return gated_biases


class HiddenGatedActivationBiasHypernetwork(ActivationBiasHypernetwork):
    """
    Activation-bias hypernetwork whose gate is evaluated against the live Qwen
    projection surface at runtime.

    The gate is parameterized per layer as:
        gate = sigmoid(hidden_surface * hidden_scale
                       + raw_bias * bridge_scale
                       + gate_offset)

    During training, the recorded target activations act as the available Qwen
    surface proxy. During inference, the patched Qwen layer evaluates this gate
    against its current pre-bias projection output.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
        gate_kind: str = "vector",
        initial_gate: float = 0.1,
    ):
        super().__init__(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
        )
        if gate_kind not in {"scalar", "vector"}:
            raise ValueError(
                f"gate_kind must be 'scalar' or 'vector', got {gate_kind!r}"
            )

        self.gate_kind = gate_kind
        self.initial_gate = float(max(1e-4, min(1.0 - 1e-4, initial_gate)))
        gate_bias_init = math.log(self.initial_gate / (1.0 - self.initial_gate))

        self.hidden_surface_heads = nn.ModuleList()
        self.bridge_scale_heads = nn.ModuleList()
        self.gate_offset_heads = nn.ModuleList()
        for _, out_dim in target_dims:
            gate_out_dim = 1 if gate_kind == "scalar" else out_dim
            self.hidden_surface_heads.append(nn.Linear(hidden_dim, gate_out_dim))
            self.bridge_scale_heads.append(nn.Linear(hidden_dim, gate_out_dim))
            self.gate_offset_heads.append(nn.Linear(hidden_dim, gate_out_dim))

        for head in list(self.hidden_surface_heads) + list(self.bridge_scale_heads):
            nn.init.zeros_(head.weight)
            nn.init.zeros_(head.bias)
        for head in self.gate_offset_heads:
            nn.init.zeros_(head.weight)
            nn.init.constant_(head.bias, gate_bias_init)

    def _expand_gate_tensor(
        self,
        gate_tensor: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        if gate_tensor.shape[-1] == 1 and reference.shape[-1] != 1:
            return gate_tensor.expand(-1, reference.shape[-1])
        return gate_tensor

    def forward_with_hidden_surfaces(
        self,
        context_vector: torch.Tensor,
        hidden_surfaces: List[torch.Tensor],
    ) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)

        gate_values: List[torch.Tensor] = []
        gated_biases: List[torch.Tensor] = []
        for raw_bias, hidden_surface, hidden_head, bridge_head, offset_head in zip(
            raw_biases,
            hidden_surfaces,
            self.hidden_surface_heads,
            self.bridge_scale_heads,
            self.gate_offset_heads,
        ):
            hidden_surface = hidden_surface.to(device=raw_bias.device, dtype=raw_bias.dtype)
            if hidden_surface.dim() == 1:
                hidden_surface = hidden_surface.unsqueeze(0)
            hidden_scale = self._expand_gate_tensor(hidden_head(hidden), raw_bias)
            bridge_scale = self._expand_gate_tensor(bridge_head(hidden), raw_bias)
            gate_offset = self._expand_gate_tensor(offset_head(hidden), raw_bias)
            gate = torch.sigmoid(
                (hidden_surface * hidden_scale)
                + (raw_bias * bridge_scale)
                + gate_offset
            )
            gate_values.append(gate)
            gated_biases.append(raw_bias * gate)

        return gated_biases, gate_values, raw_biases

    def export_hidden_gate_state(
        self,
        context_vector: torch.Tensor,
    ) -> List[dict[str, torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)

        exported = []
        for raw_bias, hidden_head, bridge_head, offset_head in zip(
            raw_biases,
            self.hidden_surface_heads,
            self.bridge_scale_heads,
            self.gate_offset_heads,
        ):
            hidden_scale = self._expand_gate_tensor(hidden_head(hidden), raw_bias)
            bridge_scale = self._expand_gate_tensor(bridge_head(hidden), raw_bias)
            gate_offset = self._expand_gate_tensor(offset_head(hidden), raw_bias)
            exported.append(
                {
                    "raw_bias": raw_bias,
                    "hidden_scale": hidden_scale,
                    "bridge_scale": bridge_scale,
                    "gate_offset": gate_offset,
                }
            )
        return exported

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)
        gated_biases = []
        for raw_bias, offset_head in zip(raw_biases, self.gate_offset_heads):
            gate_offset = self._expand_gate_tensor(offset_head(hidden), raw_bias)
            gate = torch.sigmoid(gate_offset)
            gated_biases.append(raw_bias * gate)
        return gated_biases


class InputGatedActivationBiasHypernetwork(ActivationBiasHypernetwork):
    """
    Activation-bias hypernetwork with a learned gate over the live Qwen hidden
    input to the target projection.

    Per layer:
        gate = sigmoid(W_g [hidden_input || raw_bias] + b_g)
        gated_bias = raw_bias * gate

    The gate network itself is learned globally and reused at inference time;
    only the raw bias remains context-dependent.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
        gate_kind: str = "vector",
        initial_gate: float = 0.1,
    ):
        super().__init__(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
        )
        if gate_kind not in {"scalar", "vector"}:
            raise ValueError(
                f"gate_kind must be 'scalar' or 'vector', got {gate_kind!r}"
            )

        self.gate_kind = gate_kind
        self.initial_gate = float(max(1e-4, min(1.0 - 1e-4, initial_gate)))
        gate_bias_init = math.log(self.initial_gate / (1.0 - self.initial_gate))

        self.input_gate_heads = nn.ModuleList()
        for in_dim, out_dim in target_dims:
            gate_out_dim = 1 if gate_kind == "scalar" else out_dim
            self.input_gate_heads.append(
                nn.Linear(in_dim + out_dim, gate_out_dim)
            )

        for head in self.input_gate_heads:
            nn.init.zeros_(head.weight)
            nn.init.constant_(head.bias, gate_bias_init)

    def _expand_gate_tensor(
        self,
        gate_tensor: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        if gate_tensor.shape[-1] == 1 and reference.shape[-1] != 1:
            return gate_tensor.expand(-1, reference.shape[-1])
        return gate_tensor

    def forward_with_inputs(
        self,
        context_vector: torch.Tensor,
        hidden_inputs: List[torch.Tensor],
    ) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)

        gate_values: List[torch.Tensor] = []
        gated_biases: List[torch.Tensor] = []
        for raw_bias, hidden_input, gate_head in zip(
            raw_biases,
            hidden_inputs,
            self.input_gate_heads,
        ):
            hidden_input = hidden_input.to(device=raw_bias.device, dtype=raw_bias.dtype)
            if hidden_input.dim() == 1:
                hidden_input = hidden_input.unsqueeze(0)
            gate_input = torch.cat([hidden_input, raw_bias], dim=-1)
            gate = torch.sigmoid(gate_head(gate_input))
            gate = self._expand_gate_tensor(gate, raw_bias)
            gate_values.append(gate)
            gated_biases.append(raw_bias * gate)

        return gated_biases, gate_values, raw_biases

    def export_input_gate_state(
        self,
        context_vector: torch.Tensor,
    ) -> List[dict[str, torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)

        exported = []
        for raw_bias, gate_head in zip(raw_biases, self.input_gate_heads):
            exported.append(
                {
                    "raw_bias": raw_bias,
                    "gate_weight": gate_head.weight.detach().clone(),
                    "gate_bias": gate_head.bias.detach().clone(),
                }
            )
        return exported

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        hidden = self.encode_hidden(context_vector)
        raw_biases = self.forward_from_hidden(hidden)
        gated_biases = []
        for raw_bias, gate_head in zip(raw_biases, self.input_gate_heads):
            zero_input = torch.zeros(
                raw_bias.shape[0],
                gate_head.in_features - raw_bias.shape[-1],
                device=raw_bias.device,
                dtype=raw_bias.dtype,
            )
            gate_input = torch.cat([zero_input, raw_bias], dim=-1)
            gate = torch.sigmoid(gate_head(gate_input))
            gate = self._expand_gate_tensor(gate, raw_bias)
            gated_biases.append(raw_bias * gate)
        return gated_biases


class InputResidualMixerHypernetwork(nn.Module):
    """
    Predict a residual on the live hidden input surface before the target
    projection runs.

    Per layer:
        gate = sigmoid(W_g [hidden_input || raw_residual] + b_g)
        mixed_residual = raw_residual * gate

    At runtime, the patched Qwen layer applies:
        x_mixed = x + mixed_residual
        y = v_proj(x_mixed)

    This is strictly stronger than output-bias injection because the effect is
    conditioned on the current hidden state before the projection.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
        gate_kind: str = "vector",
        initial_gate: float = 0.1,
    ):
        super().__init__()
        if gate_kind not in {"scalar", "vector"}:
            raise ValueError(
                f"gate_kind must be 'scalar' or 'vector', got {gate_kind!r}"
            )

        self.target_dims = target_dims
        self.num_target_layers = len(target_dims)
        self.gate_kind = gate_kind
        self.initial_gate = float(max(1e-4, min(1.0 - 1e-4, initial_gate)))
        gate_bias_init = math.log(self.initial_gate / (1.0 - self.initial_gate))

        self.backbone = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )

        self.residual_heads = nn.ModuleList()
        self.input_gate_heads = nn.ModuleList()
        for in_dim, _ in target_dims:
            self.residual_heads.append(nn.Linear(hidden_dim, in_dim))
            gate_out_dim = 1 if gate_kind == "scalar" else in_dim
            self.input_gate_heads.append(nn.Linear(in_dim + in_dim, gate_out_dim))

        for head in self.residual_heads:
            nn.init.normal_(head.weight, std=0.01)
            nn.init.zeros_(head.bias)
        for head in self.input_gate_heads:
            nn.init.zeros_(head.weight)
            nn.init.constant_(head.bias, gate_bias_init)

    def encode_hidden(self, context_vector: torch.Tensor) -> torch.Tensor:
        backbone_dtype = self.backbone[0].weight.dtype
        if context_vector.dtype != backbone_dtype:
            context_vector = context_vector.to(dtype=backbone_dtype)
        return self.backbone(context_vector)

    def forward_from_hidden(self, hidden: torch.Tensor) -> List[torch.Tensor]:
        return [head(hidden) for head in self.residual_heads]

    def _expand_gate_tensor(
        self,
        gate_tensor: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        if gate_tensor.shape[-1] == 1 and reference.shape[-1] != 1:
            return gate_tensor.expand(-1, reference.shape[-1])
        return gate_tensor

    def forward_with_inputs(
        self,
        context_vector: torch.Tensor,
        hidden_inputs: List[torch.Tensor],
    ) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_residuals = self.forward_from_hidden(hidden)

        gate_values: List[torch.Tensor] = []
        mixed_residuals: List[torch.Tensor] = []
        for raw_residual, hidden_input, gate_head in zip(
            raw_residuals,
            hidden_inputs,
            self.input_gate_heads,
        ):
            hidden_input = hidden_input.to(device=raw_residual.device, dtype=raw_residual.dtype)
            if hidden_input.dim() == 1:
                hidden_input = hidden_input.unsqueeze(0)
            gate_input = torch.cat([hidden_input, raw_residual], dim=-1)
            gate = torch.sigmoid(gate_head(gate_input))
            gate = self._expand_gate_tensor(gate, raw_residual)
            gate_values.append(gate)
            mixed_residuals.append(raw_residual * gate)

        return mixed_residuals, gate_values, raw_residuals

    def export_input_residual_state(
        self,
        context_vector: torch.Tensor,
    ) -> List[dict[str, torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        raw_residuals = self.forward_from_hidden(hidden)

        exported = []
        for raw_residual, gate_head in zip(raw_residuals, self.input_gate_heads):
            exported.append(
                {
                    "raw_residual": raw_residual,
                    "gate_weight": gate_head.weight.detach().clone(),
                    "gate_bias": gate_head.bias.detach().clone(),
                }
            )
        return exported

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        hidden = self.encode_hidden(context_vector)
        raw_residuals = self.forward_from_hidden(hidden)
        mixed_residuals = []
        for raw_residual, gate_head in zip(raw_residuals, self.input_gate_heads):
            zero_input = torch.zeros(
                raw_residual.shape[0],
                gate_head.in_features - raw_residual.shape[-1],
                device=raw_residual.device,
                dtype=raw_residual.dtype,
            )
            gate_input = torch.cat([zero_input, raw_residual], dim=-1)
            gate = torch.sigmoid(gate_head(gate_input))
            gate = self._expand_gate_tensor(gate, raw_residual)
            mixed_residuals.append(raw_residual * gate)
        return mixed_residuals


class TokenConditionedInputAdapterHypernetwork(nn.Module):
    """
    Context-conditioned low-rank adapter over the live hidden input surface.

    Per layer, the context vector predicts a small low-rank adapter plus
    feature-wise gate parameters:

        raw_delta = x @ A @ B + bias
        gate = sigmoid(x * input_scale + raw_delta * delta_scale + gate_offset)
        x_mixed = x + raw_delta * gate

    Unlike the static residual mixer, the delta depends on the current token
    hidden state through a learnable context-conditioned transform.
    """

    def __init__(
        self,
        context_dim: int,
        target_dims: List[Tuple[int, int]],
        hidden_dim: int = 1024,
        rank: int = 16,
        gate_kind: str = "vector",
        initial_gate: float = 0.1,
    ):
        super().__init__()
        if gate_kind not in {"scalar", "vector"}:
            raise ValueError(
                f"gate_kind must be 'scalar' or 'vector', got {gate_kind!r}"
            )
        if rank <= 0:
            raise ValueError(f"rank must be positive, got {rank}")

        self.target_dims = target_dims
        self.num_target_layers = len(target_dims)
        self.rank = int(rank)
        self.gate_kind = gate_kind
        self.initial_gate = float(max(1e-4, min(1.0 - 1e-4, initial_gate)))
        gate_bias_init = math.log(self.initial_gate / (1.0 - self.initial_gate))

        self.backbone = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )

        self.adapter_heads_A = nn.ModuleList()
        self.adapter_heads_B = nn.ModuleList()
        self.adapter_bias_heads = nn.ModuleList()
        self.input_scale_heads = nn.ModuleList()
        self.delta_scale_heads = nn.ModuleList()
        self.gate_offset_heads = nn.ModuleList()
        for in_dim, _ in target_dims:
            gate_out_dim = 1 if gate_kind == "scalar" else in_dim
            self.adapter_heads_A.append(nn.Linear(hidden_dim, in_dim * self.rank))
            self.adapter_heads_B.append(nn.Linear(hidden_dim, self.rank * in_dim))
            self.adapter_bias_heads.append(nn.Linear(hidden_dim, in_dim))
            self.input_scale_heads.append(nn.Linear(hidden_dim, gate_out_dim))
            self.delta_scale_heads.append(nn.Linear(hidden_dim, gate_out_dim))
            self.gate_offset_heads.append(nn.Linear(hidden_dim, gate_out_dim))

        for head in list(self.adapter_heads_A) + list(self.adapter_heads_B) + list(self.adapter_bias_heads):
            nn.init.normal_(head.weight, std=0.01)
            nn.init.zeros_(head.bias)
        for head in list(self.input_scale_heads) + list(self.delta_scale_heads):
            nn.init.zeros_(head.weight)
            nn.init.zeros_(head.bias)
        for head in self.gate_offset_heads:
            nn.init.zeros_(head.weight)
            nn.init.constant_(head.bias, gate_bias_init)

    def encode_hidden(self, context_vector: torch.Tensor) -> torch.Tensor:
        backbone_dtype = self.backbone[0].weight.dtype
        if context_vector.dtype != backbone_dtype:
            context_vector = context_vector.to(dtype=backbone_dtype)
        return self.backbone(context_vector)

    def _expand_gate_tensor(
        self,
        gate_tensor: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        if gate_tensor.shape[-1] == 1 and reference.shape[-1] != 1:
            return gate_tensor.expand(-1, reference.shape[-1])
        return gate_tensor

    def forward_with_inputs(
        self,
        context_vector: torch.Tensor,
        hidden_inputs: List[torch.Tensor],
    ) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)

        mixed_inputs: List[torch.Tensor] = []
        gate_values: List[torch.Tensor] = []
        raw_deltas: List[torch.Tensor] = []

        for (
            hidden_input,
            head_A,
            head_B,
            bias_head,
            input_scale_head,
            delta_scale_head,
            gate_offset_head,
            (in_dim, _),
        ) in zip(
            hidden_inputs,
            self.adapter_heads_A,
            self.adapter_heads_B,
            self.adapter_bias_heads,
            self.input_scale_heads,
            self.delta_scale_heads,
            self.gate_offset_heads,
            self.target_dims,
        ):
            hidden_input = hidden_input.to(device=hidden.device, dtype=hidden.dtype)
            if hidden_input.dim() == 1:
                hidden_input = hidden_input.unsqueeze(0)

            flat_A = head_A(hidden)
            flat_B = head_B(hidden)
            adapter_A = flat_A.view(-1, in_dim, self.rank)
            adapter_B = flat_B.view(-1, self.rank, in_dim)
            adapter_bias = bias_head(hidden)

            raw_delta = torch.bmm(hidden_input.unsqueeze(1), adapter_A).squeeze(1)
            raw_delta = torch.bmm(raw_delta.unsqueeze(1), adapter_B).squeeze(1)
            raw_delta = raw_delta + adapter_bias

            input_scale = self._expand_gate_tensor(input_scale_head(hidden), raw_delta)
            delta_scale = self._expand_gate_tensor(delta_scale_head(hidden), raw_delta)
            gate_offset = self._expand_gate_tensor(gate_offset_head(hidden), raw_delta)
            gate = torch.sigmoid(
                (hidden_input * input_scale)
                + (raw_delta * delta_scale)
                + gate_offset
            )

            mixed_inputs.append(hidden_input + (raw_delta * gate))
            gate_values.append(gate)
            raw_deltas.append(raw_delta)

        return mixed_inputs, gate_values, raw_deltas

    def export_input_adapter_state(
        self,
        context_vector: torch.Tensor,
    ) -> List[dict[str, torch.Tensor]]:
        hidden = self.encode_hidden(context_vector)
        exported = []
        for (
            head_A,
            head_B,
            bias_head,
            input_scale_head,
            delta_scale_head,
            gate_offset_head,
            (in_dim, _),
        ) in zip(
            self.adapter_heads_A,
            self.adapter_heads_B,
            self.adapter_bias_heads,
            self.input_scale_heads,
            self.delta_scale_heads,
            self.gate_offset_heads,
            self.target_dims,
        ):
            flat_A = head_A(hidden)
            flat_B = head_B(hidden)
            adapter_A = flat_A.view(-1, in_dim, self.rank)
            adapter_B = flat_B.view(-1, self.rank, in_dim)
            adapter_bias = bias_head(hidden)
            input_scale = input_scale_head(hidden)
            delta_scale = delta_scale_head(hidden)
            gate_offset = gate_offset_head(hidden)
            exported.append(
                {
                    "adapter_A": adapter_A,
                    "adapter_B": adapter_B,
                    "adapter_bias": adapter_bias,
                    "input_scale": input_scale,
                    "delta_scale": delta_scale,
                    "gate_offset": gate_offset,
                }
            )
        return exported

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        hidden = self.encode_hidden(context_vector)
        deltas = []
        for bias_head in self.adapter_bias_heads:
            deltas.append(bias_head(hidden))
        return deltas


def is_gated_activation_bias_mode(bridge_mode: Optional[str]) -> bool:
    return str(bridge_mode or "activation_bias") == "gated_activation_bias"


def is_hidden_gated_activation_bias_mode(bridge_mode: Optional[str]) -> bool:
    return str(bridge_mode or "activation_bias") == "hidden_gated_activation_bias"


def is_input_gated_activation_bias_mode(bridge_mode: Optional[str]) -> bool:
    return str(bridge_mode or "activation_bias") == "input_gated_activation_bias"


def is_input_residual_mixer_mode(bridge_mode: Optional[str]) -> bool:
    return str(bridge_mode or "activation_bias") == "input_residual_mixer"


def is_token_conditioned_input_adapter_mode(bridge_mode: Optional[str]) -> bool:
    return str(bridge_mode or "activation_bias") == "token_conditioned_input_adapter"


def build_activation_bias_hypernetwork(
    *,
    bridge_mode: str,
    context_dim: int,
    target_dims: List[Tuple[int, int]],
    hidden_dim: int = 1024,
    rank: int = 16,
    gate_kind: str = "vector",
    initial_gate: float = 0.1,
) -> ActivationBiasHypernetwork:
    if is_token_conditioned_input_adapter_mode(bridge_mode):
        return TokenConditionedInputAdapterHypernetwork(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
            rank=rank,
            gate_kind=gate_kind,
            initial_gate=initial_gate,
        )
    if is_input_residual_mixer_mode(bridge_mode):
        return InputResidualMixerHypernetwork(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
            gate_kind=gate_kind,
            initial_gate=initial_gate,
        )
    if is_input_gated_activation_bias_mode(bridge_mode):
        return InputGatedActivationBiasHypernetwork(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
            gate_kind=gate_kind,
            initial_gate=initial_gate,
        )
    if is_hidden_gated_activation_bias_mode(bridge_mode):
        return HiddenGatedActivationBiasHypernetwork(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
            gate_kind=gate_kind,
            initial_gate=initial_gate,
        )
    if is_gated_activation_bias_mode(bridge_mode):
        return GatedActivationBiasHypernetwork(
            context_dim=context_dim,
            target_dims=target_dims,
            hidden_dim=hidden_dim,
            gate_kind=gate_kind,
            initial_gate=initial_gate,
        )
    return ActivationBiasHypernetwork(
        context_dim=context_dim,
        target_dims=target_dims,
        hidden_dim=hidden_dim,
    )


class ConstantBiasBridge(nn.Module):
    """
    Learns one static activation bias vector per target layer.

    This is the Step 4 control: same injection surface as activation_bias, but
    with no Mamba signal, no compressor, and no sample-dependent mapping.
    """

    def __init__(self, target_dims: List[Tuple[int, int]]):
        super().__init__()
        self.target_dims = target_dims
        self.bias_vectors = nn.ParameterList(
            [nn.Parameter(torch.zeros(out_dim)) for _, out_dim in target_dims]
        )

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        batch_size = int(context_vector.shape[0])
        return [bias.unsqueeze(0).expand(batch_size, -1) for bias in self.bias_vectors]





class DynamicLoRALinear(nn.Module):
    """
    Drop-in replacement for nn.Linear that supports dynamic LoRA injection.

    The key design choice: LoRA matrices are stored as instance state
    (set_lora / clear_lora), NOT passed as forward() arguments.
    This preserves the standard forward(x) signature, making it
    compatible with HuggingFace's model.generate() and all internal
    forward passes without any monkey-patching.

    Base computation uses the original layer's forward(), NOT F.linear().
    This is critical for BitsAndBytes 4-bit quantized layers, which
    F.linear() cannot handle.

    Usage:
        # Before generation:
        layer.set_lora(A, B)
        output = model.generate(...)
        layer.clear_lora()
    """

    def __init__(self, frozen_base_layer: nn.Linear, scaling: float = 1.0):
        super().__init__()

        # Keep the WHOLE original layer, not just its weight.
        # This is critical for BnB 4-bit: F.linear() can't handle
        # quantized weights, but the original forward() can.
        self.base_layer = frozen_base_layer
        for param in self.base_layer.parameters():
            param.requires_grad = False

        self.in_features = frozen_base_layer.in_features
        self.out_features = frozen_base_layer.out_features

        # LoRA scaling factor
        self.scaling = scaling

        # Dynamic LoRA state (set before generation, cleared after)
        self._dynamic_A: Optional[torch.Tensor] = None
        self._dynamic_B: Optional[torch.Tensor] = None
        self._dynamic_bias: Optional[torch.Tensor] = None
        self._gate_hidden_scale: Optional[torch.Tensor] = None
        self._gate_bridge_scale: Optional[torch.Tensor] = None
        self._gate_offset: Optional[torch.Tensor] = None
        self._input_gate_weight: Optional[torch.Tensor] = None
        self._input_gate_bias: Optional[torch.Tensor] = None
        self._input_residual: Optional[torch.Tensor] = None
        self._input_residual_gate_weight: Optional[torch.Tensor] = None
        self._input_residual_gate_bias: Optional[torch.Tensor] = None
        self._input_adapter_A: Optional[torch.Tensor] = None
        self._input_adapter_B: Optional[torch.Tensor] = None
        self._input_adapter_bias: Optional[torch.Tensor] = None
        self._input_adapter_input_scale: Optional[torch.Tensor] = None
        self._input_adapter_delta_scale: Optional[torch.Tensor] = None
        self._input_adapter_gate_offset: Optional[torch.Tensor] = None

        # RMS-scaling config (OpenCLAW #127, Wang et al. arXiv:2510.11328 finding #1).
        # These are CONFIG, not per-injection dynamic state: they are set by the
        # bridge-apply step (never by set_activation_bias) and are intentionally NOT
        # reset in clear_lora. With _rms_scale False, forward is byte-identical to the
        # pre-flag behavior.
        self._rms_scale: bool = False
        self._bias_alpha: float = 1.0

    @property
    def weight(self):
        """Forward weight access to base layer (for device/dtype detection)."""
        return self.base_layer.weight

    def set_lora(self, A: torch.Tensor, B: torch.Tensor):
        """
        Set the dynamic LoRA matrices for the next forward pass(es).

        Args:
            A: (in_dim, lora_rank) or (batch, in_dim, lora_rank)
            B: (lora_rank, out_dim) or (batch, lora_rank, out_dim)
        """
        # Remove batch dim if present (we operate on single samples)
        if A.dim() == 3:
            A = A.squeeze(0)
        if B.dim() == 3:
            B = B.squeeze(0)
        self._dynamic_A = A
        self._dynamic_B = B

    def clear_lora(self):
        """Clear dynamic injected state. The layer reverts to frozen behavior."""
        self._dynamic_A = None
        self._dynamic_B = None
        self._dynamic_bias = None
        self._gate_hidden_scale = None
        self._gate_bridge_scale = None
        self._gate_offset = None
        self._input_gate_weight = None
        self._input_gate_bias = None
        self._input_residual = None
        self._input_residual_gate_weight = None
        self._input_residual_gate_bias = None
        self._input_adapter_A = None
        self._input_adapter_B = None
        self._input_adapter_bias = None
        self._input_adapter_input_scale = None
        self._input_adapter_delta_scale = None
        self._input_adapter_gate_offset = None

    def _validate_output_shaped_tensor(
        self,
        value: torch.Tensor,
        name: str,
    ):
        if value.dim() not in {1, 2}:
            raise ValueError(
                f"{name} must have shape (out_dim,) or (batch, out_dim), got {tuple(value.shape)}"
            )
        if value.shape[-1] != self.out_features:
            raise ValueError(
                f"{name} width does not match layer output width: "
                f"got {value.shape[-1]}, expected {self.out_features}."
            )

    def _validate_input_shaped_tensor(
        self,
        value: torch.Tensor,
        name: str,
    ):
        if value.dim() not in {1, 2}:
            raise ValueError(
                f"{name} must have shape (in_dim,) or (batch, in_dim), got {tuple(value.shape)}"
            )
        if value.shape[-1] != self.in_features:
            raise ValueError(
                f"{name} width does not match layer input width: "
                f"got {value.shape[-1]}, expected {self.in_features}."
            )

    def set_activation_bias(
        self,
        bias: torch.Tensor,
        *,
        hidden_gate_scale: Optional[torch.Tensor] = None,
        bridge_gate_scale: Optional[torch.Tensor] = None,
        gate_offset: Optional[torch.Tensor] = None,
        input_gate_weight: Optional[torch.Tensor] = None,
        input_gate_bias: Optional[torch.Tensor] = None,
    ):
        """Set an additive activation bias shaped to the layer's output width."""
        self._validate_output_shaped_tensor(bias, "Activation bias")
        self._dynamic_bias = bias
        self._gate_hidden_scale = None
        self._gate_bridge_scale = None
        self._gate_offset = None
        self._input_gate_weight = None
        self._input_gate_bias = None
        self._input_residual = None
        self._input_residual_gate_weight = None
        self._input_residual_gate_bias = None
        self._input_adapter_A = None
        self._input_adapter_B = None
        self._input_adapter_bias = None
        self._input_adapter_input_scale = None
        self._input_adapter_delta_scale = None
        self._input_adapter_gate_offset = None

        gate_args = {
            "hidden_gate_scale": hidden_gate_scale,
            "bridge_gate_scale": bridge_gate_scale,
            "gate_offset": gate_offset,
        }
        if any(value is not None for value in gate_args.values()):
            if not all(value is not None for value in gate_args.values()):
                raise ValueError(
                    "Hidden gating requires hidden_gate_scale, bridge_gate_scale, and gate_offset together."
                )
            self._validate_output_shaped_tensor(hidden_gate_scale, "Hidden gate scale")
            self._validate_output_shaped_tensor(bridge_gate_scale, "Bridge gate scale")
            self._validate_output_shaped_tensor(gate_offset, "Gate offset")
            self._gate_hidden_scale = hidden_gate_scale
            self._gate_bridge_scale = bridge_gate_scale
            self._gate_offset = gate_offset

        input_gate_args = {
            "input_gate_weight": input_gate_weight,
            "input_gate_bias": input_gate_bias,
        }
        if any(value is not None for value in input_gate_args.values()):
            if not all(value is not None for value in input_gate_args.values()):
                raise ValueError(
                    "Input-hidden gating requires input_gate_weight and input_gate_bias together."
                )
            if input_gate_weight.dim() != 2:
                raise ValueError(
                    f"input_gate_weight must be rank-2, got {tuple(input_gate_weight.shape)}"
                )
            if input_gate_weight.shape[1] != self.in_features + self.out_features:
                raise ValueError(
                    "input_gate_weight width does not match concatenated [x || bias] width: "
                    f"got {input_gate_weight.shape[1]}, expected {self.in_features + self.out_features}."
                )
            if input_gate_bias.dim() != 1:
                raise ValueError(
                    f"input_gate_bias must be rank-1, got {tuple(input_gate_bias.shape)}"
                )
            if input_gate_bias.shape[0] != input_gate_weight.shape[0]:
                raise ValueError(
                    "input_gate_bias length does not match input_gate_weight output dim."
                )
            self._input_gate_weight = input_gate_weight
            self._input_gate_bias = input_gate_bias

    def set_token_conditioned_input_adapter(
        self,
        *,
        adapter_A: torch.Tensor,
        adapter_B: torch.Tensor,
        adapter_bias: torch.Tensor,
        input_scale: torch.Tensor,
        delta_scale: torch.Tensor,
        gate_offset: torch.Tensor,
    ):
        if adapter_A.dim() not in {2, 3}:
            raise ValueError(
                f"adapter_A must have shape (in_dim, rank) or (batch, in_dim, rank), got {tuple(adapter_A.shape)}"
            )
        if adapter_B.dim() not in {2, 3}:
            raise ValueError(
                f"adapter_B must have shape (rank, in_dim) or (batch, rank, in_dim), got {tuple(adapter_B.shape)}"
            )
        if adapter_A.dim() == 3:
            adapter_A = adapter_A.squeeze(0)
        if adapter_B.dim() == 3:
            adapter_B = adapter_B.squeeze(0)
        if adapter_A.shape[0] != self.in_features:
            raise ValueError(
                f"adapter_A input width mismatch: got {adapter_A.shape[0]}, expected {self.in_features}."
            )
        if adapter_B.shape[1] != self.in_features:
            raise ValueError(
                f"adapter_B output width mismatch: got {adapter_B.shape[1]}, expected {self.in_features}."
            )
        if adapter_A.shape[1] != adapter_B.shape[0]:
            raise ValueError("adapter_A rank does not match adapter_B rank.")

        self._validate_input_shaped_tensor(adapter_bias, "Input adapter bias")
        for name, value in (
            ("Input adapter input scale", input_scale),
            ("Input adapter delta scale", delta_scale),
            ("Input adapter gate offset", gate_offset),
        ):
            if value.dim() not in {1, 2}:
                raise ValueError(
                    f"{name} must have shape (1,), (in_dim,), (batch, 1), or (batch, in_dim); got {tuple(value.shape)}"
                )
            if value.shape[-1] not in {1, self.in_features}:
                raise ValueError(
                    f"{name} width mismatch: got {value.shape[-1]}, expected 1 or {self.in_features}."
                )

        self._input_adapter_A = adapter_A
        self._input_adapter_B = adapter_B
        self._input_adapter_bias = adapter_bias
        self._input_adapter_input_scale = input_scale
        self._input_adapter_delta_scale = delta_scale
        self._input_adapter_gate_offset = gate_offset
        self._dynamic_bias = None
        self._gate_hidden_scale = None
        self._gate_bridge_scale = None
        self._gate_offset = None
        self._input_gate_weight = None
        self._input_gate_bias = None
        self._input_residual = None
        self._input_residual_gate_weight = None
        self._input_residual_gate_bias = None

    def set_input_residual(
        self,
        residual: torch.Tensor,
        *,
        input_gate_weight: Optional[torch.Tensor] = None,
        input_gate_bias: Optional[torch.Tensor] = None,
    ):
        self._validate_input_shaped_tensor(residual, "Input residual")
        self._input_residual = residual
        self._input_residual_gate_weight = None
        self._input_residual_gate_bias = None
        self._dynamic_bias = None
        self._gate_hidden_scale = None
        self._gate_bridge_scale = None
        self._gate_offset = None
        self._input_gate_weight = None
        self._input_gate_bias = None
        self._input_adapter_A = None
        self._input_adapter_B = None
        self._input_adapter_bias = None
        self._input_adapter_input_scale = None
        self._input_adapter_delta_scale = None
        self._input_adapter_gate_offset = None

        gate_args = {
            "input_gate_weight": input_gate_weight,
            "input_gate_bias": input_gate_bias,
        }
        if any(value is not None for value in gate_args.values()):
            if not all(value is not None for value in gate_args.values()):
                raise ValueError(
                    "Input-residual gating requires input_gate_weight and input_gate_bias together."
                )
            if input_gate_weight.dim() != 2:
                raise ValueError(
                    f"input_gate_weight must be rank-2, got {tuple(input_gate_weight.shape)}"
                )
            if input_gate_weight.shape[1] != self.in_features + self.in_features:
                raise ValueError(
                    "input_gate_weight width does not match concatenated [x || residual] width: "
                    f"got {input_gate_weight.shape[1]}, expected {self.in_features + self.in_features}."
                )
            if input_gate_bias.dim() != 1:
                raise ValueError(
                    f"input_gate_bias must be rank-1, got {tuple(input_gate_bias.shape)}"
                )
            if input_gate_bias.shape[0] != input_gate_weight.shape[0]:
                raise ValueError(
                    "input_gate_bias length does not match input_gate_weight output dim."
                )
            self._input_residual_gate_weight = input_gate_weight
            self._input_residual_gate_bias = input_gate_bias

    def clear_activation_bias(self):
        """Clear dynamic activation bias while leaving LoRA state untouched."""
        self._dynamic_bias = None
        self._gate_hidden_scale = None
        self._gate_bridge_scale = None
        self._gate_offset = None
        self._input_gate_weight = None
        self._input_gate_bias = None
        self._input_residual = None
        self._input_residual_gate_weight = None
        self._input_residual_gate_bias = None
        self._input_adapter_A = None
        self._input_adapter_B = None
        self._input_adapter_bias = None
        self._input_adapter_input_scale = None
        self._input_adapter_delta_scale = None
        self._input_adapter_gate_offset = None

    @property
    def has_lora(self) -> bool:
        return self._dynamic_A is not None and self._dynamic_B is not None

    @property
    def has_activation_bias(self) -> bool:
        return self._dynamic_bias is not None

    @property
    def has_hidden_gating(self) -> bool:
        return (
            self._gate_hidden_scale is not None
            and self._gate_bridge_scale is not None
            and self._gate_offset is not None
        )

    @property
    def has_input_hidden_gating(self) -> bool:
        return self._input_gate_weight is not None and self._input_gate_bias is not None

    @property
    def has_input_residual(self) -> bool:
        return self._input_residual is not None

    @property
    def has_input_residual_gating(self) -> bool:
        return (
            self._input_residual_gate_weight is not None
            and self._input_residual_gate_bias is not None
        )

    @property
    def has_token_conditioned_input_adapter(self) -> bool:
        return (
            self._input_adapter_A is not None
            and self._input_adapter_B is not None
            and self._input_adapter_bias is not None
            and self._input_adapter_input_scale is not None
            and self._input_adapter_delta_scale is not None
            and self._input_adapter_gate_offset is not None
        )

    def _broadcast_output_tensor(
        self,
        value: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        value = value.to(device=reference.device, dtype=reference.dtype)
        if value.dim() == 1 and reference.dim() == 2:
            value = value.view(1, -1).expand(reference.shape[0], -1)
        elif value.dim() == 1 and reference.dim() == 3:
            value = value.view(1, 1, -1).expand(reference.shape[0], reference.shape[1], -1)
        elif value.dim() == 2 and reference.dim() == 3:
            if value.shape[0] == 1 and reference.shape[0] != 1:
                value = value.expand(reference.shape[0], -1)
            value = value.unsqueeze(1).expand(reference.shape[0], reference.shape[1], value.shape[-1])
        return value

    def _broadcast_input_tensor(
        self,
        value: torch.Tensor,
        reference: torch.Tensor,
    ) -> torch.Tensor:
        value = value.to(device=reference.device, dtype=reference.dtype)
        if value.dim() == 1 and reference.dim() == 2:
            value = value.view(1, -1).expand(reference.shape[0], -1)
        elif value.dim() == 1 and reference.dim() == 3:
            value = value.view(1, 1, -1).expand(reference.shape[0], reference.shape[1], -1)
        elif value.dim() == 2 and reference.dim() == 3:
            if value.shape[0] == 1 and reference.shape[0] != 1:
                value = value.expand(reference.shape[0], -1)
            value = value.unsqueeze(1).expand(reference.shape[0], reference.shape[1], value.shape[-1])
        return value

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Standard nn.Linear-compatible forward.
        If LoRA and/or activation bias is set, adds the dynamic contribution.
        """
        x_for_base = x
        if self.has_token_conditioned_input_adapter:
            adapter_A = self._input_adapter_A.to(device=x.device, dtype=x.dtype)
            adapter_B = self._input_adapter_B.to(device=x.device, dtype=x.dtype)
            adapter_bias = self._broadcast_input_tensor(self._input_adapter_bias, x)
            raw_delta = x @ adapter_A @ adapter_B
            raw_delta = raw_delta + adapter_bias
            input_scale = self._broadcast_input_tensor(self._input_adapter_input_scale, x)
            delta_scale = self._broadcast_input_tensor(self._input_adapter_delta_scale, x)
            gate_offset = self._broadcast_input_tensor(self._input_adapter_gate_offset, x)
            gate = torch.sigmoid(
                (x * input_scale) + (raw_delta * delta_scale) + gate_offset
            )
            x_for_base = x + (raw_delta * gate)
        elif self.has_input_residual:
            residual = self._broadcast_input_tensor(self._input_residual, x)
            if self.has_input_residual_gating:
                gate_weight = self._input_residual_gate_weight.to(device=x.device, dtype=x.dtype)
                gate_bias = self._input_residual_gate_bias.to(device=x.device, dtype=x.dtype)
                gate_input = torch.cat([x.to(dtype=x.dtype), residual], dim=-1)
                gate = torch.sigmoid(F.linear(gate_input, gate_weight, gate_bias))
                if gate.shape[-1] == 1 and x.shape[-1] != 1:
                    gate = gate.expand(*gate.shape[:-1], x.shape[-1])
                x_for_base = x + (residual * gate)
            else:
                x_for_base = x + residual

        # Base computation goes through the ORIGINAL layer's forward.
        # This handles BnB 4-bit dequantization, GPTQ, etc.
        output = self.base_layer(x_for_base)

        if self.has_lora:
            # Dynamic LoRA contribution
            # Cast to match activation dtype (BnB computes in fp16)
            A = self._dynamic_A.to(device=x_for_base.device, dtype=x_for_base.dtype)
            B = self._dynamic_B.to(device=x_for_base.device, dtype=x_for_base.dtype)
            lora_out = x_for_base @ A @ B
            output = output + (lora_out * self.scaling)

        if self.has_activation_bias:
            bias = self._broadcast_output_tensor(self._dynamic_bias, output)
            if self._rms_scale:
                # Bias-as-direction: renormalize the stored (unscaled) residual to a unit
                # direction, then rescale to _bias_alpha * RMS(output) per row. Alpha lives
                # here (never also in the apply step) — see apply_bridge_adjustments.
                direction = bias / (bias.norm(dim=-1, keepdim=True) + 1e-6)
                rms = output.float().pow(2).mean(dim=-1, keepdim=True).sqrt().to(output.dtype)
                bias = self._bias_alpha * rms * direction
            if self.has_input_hidden_gating:
                gate_weight = self._input_gate_weight.to(device=output.device, dtype=output.dtype)
                gate_bias = self._input_gate_bias.to(device=output.device, dtype=output.dtype)
                bias_for_gate = bias
                if bias_for_gate.dim() == 2 and x.dim() == 3:
                    bias_for_gate = bias_for_gate.unsqueeze(1).expand(-1, x.shape[1], -1)
                gate_input = torch.cat([x.to(output.dtype), bias_for_gate], dim=-1)
                gate = torch.sigmoid(F.linear(gate_input, gate_weight, gate_bias))
                if gate.shape[-1] == 1 and output.shape[-1] != 1:
                    gate = gate.expand(*gate.shape[:-1], output.shape[-1])
                output = output + (bias * gate)
            elif self.has_hidden_gating:
                hidden_scale = self._broadcast_output_tensor(self._gate_hidden_scale, output)
                bridge_scale = self._broadcast_output_tensor(self._gate_bridge_scale, output)
                gate_offset = self._broadcast_output_tensor(self._gate_offset, output)
                gate = torch.sigmoid(
                    (output * hidden_scale) + (bias * bridge_scale) + gate_offset
                )
                output = output + (bias * gate)
            else:
                output = output + bias

        return output

    def extra_repr(self) -> str:
        return (
            f"in_features={self.in_features}, "
            f"out_features={self.out_features}, "
            f"scaling={self.scaling}, "
            f"lora_active={self.has_lora}, "
            f"bias_active={self.has_activation_bias}, "
            f"hidden_gate_active={self.has_hidden_gating}, "
            f"input_hidden_gate_active={self.has_input_hidden_gating}, "
            f"input_residual_active={self.has_input_residual}, "
            f"input_residual_gate_active={self.has_input_residual_gating}, "
            f"token_input_adapter_active={self.has_token_conditioned_input_adapter}"
        )


