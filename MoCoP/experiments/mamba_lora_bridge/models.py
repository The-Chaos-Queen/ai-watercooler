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
        if mamba_state.size(1) <= self.target_layer:
            raise ValueError(
                f"Mamba state only has {mamba_state.size(1)} layers, cannot extract layer {self.target_layer}"
            )

        targeted_state = mamba_state[:, self.target_layer]
        batch_size = mamba_state.size(0)
        flat = targeted_state.reshape(batch_size, -1)

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

    def forward(self, context_vector: torch.Tensor) -> List[torch.Tensor]:
        backbone_dtype = self.backbone[0].weight.dtype
        if context_vector.dtype != backbone_dtype:
            context_vector = context_vector.to(dtype=backbone_dtype)
        hidden = self.backbone(context_vector)
        return [head(hidden) for head in self.bias_heads]


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

    def set_activation_bias(self, bias: torch.Tensor):
        """Set an additive activation bias shaped to the layer's output width."""
        if bias.dim() not in {1, 2}:
            raise ValueError(
                f"Activation bias must have shape (out_dim,) or (batch, out_dim), got {tuple(bias.shape)}"
            )
        self._dynamic_bias = bias

    def clear_activation_bias(self):
        """Clear dynamic activation bias while leaving LoRA state untouched."""
        self._dynamic_bias = None

    @property
    def has_lora(self) -> bool:
        return self._dynamic_A is not None and self._dynamic_B is not None

    @property
    def has_activation_bias(self) -> bool:
        return self._dynamic_bias is not None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Standard nn.Linear-compatible forward.
        If LoRA and/or activation bias is set, adds the dynamic contribution.
        """
        # Base computation goes through the ORIGINAL layer's forward.
        # This handles BnB 4-bit dequantization, GPTQ, etc.
        output = self.base_layer(x)

        if self.has_lora:
            # Dynamic LoRA contribution
            # Cast to match activation dtype (BnB computes in fp16)
            A = self._dynamic_A.to(device=x.device, dtype=x.dtype)
            B = self._dynamic_B.to(device=x.device, dtype=x.dtype)
            lora_out = x @ A @ B
            output = output + (lora_out * self.scaling)

        if self.has_activation_bias:
            bias = self._dynamic_bias.to(device=output.device, dtype=output.dtype)
            if bias.dim() == 2 and output.dim() == 3:
                bias = bias.unsqueeze(1)
            output = output + bias

        return output

    def extra_repr(self) -> str:
        return (
            f"in_features={self.in_features}, "
            f"out_features={self.out_features}, "
            f"scaling={self.scaling}, "
            f"lora_active={self.has_lora}, "
            f"bias_active={self.has_activation_bias}"
        )


