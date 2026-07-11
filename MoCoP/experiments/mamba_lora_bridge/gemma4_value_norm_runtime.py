"""Strict Gemma-4 option-A value-branch runtime.

Gemma-4 full-attention teeth reuse the raw ``k_proj`` tensor as the value
tensor, then fork the paths: keys receive k-norm and RoPE while values enter a
dedicated scale-free ``v_norm``.  A forward pre-hook on that norm is therefore
the narrow value-only intervention surface.  This module binds and validates
that runtime topology; it never falls back to patching ``k_proj``.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterator, Mapping, Sequence

import torch


APPROVED_TEETH = (29, 35, 41)
ACTUATOR_WIDTH = 512
SURFACE_KIND = "full_attention_value_norm_pre"
CAPTURE_MODE = "pre_hook_input"
ACTUATOR_DECISION = "option_a_value_only_v_norm_pre"
POSITION_POLICIES = frozenset({"all_positions", "exclude_absolute_zero"})


class SurfaceBindingError(RuntimeError):
    """The loaded model does not expose the reviewed option-A topology."""


class RuntimeConditionError(RuntimeError):
    """A requested capture/intervention violates the bounded runtime contract."""


@dataclass(frozen=True)
class BoundValueSurface:
    layer: int
    module_path: str
    width: int
    module: torch.nn.Module = field(repr=False, compare=False)

    def report(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "module_path": self.module_path,
            "width": self.width,
            "surface_kind": SURFACE_KIND,
            "capture_mode": CAPTURE_MODE,
            "actuator_decision": ACTUATOR_DECISION,
        }


@dataclass
class ValueTraceEvent:
    layer: int
    call_index: int
    alpha: float
    position_policy: str
    absolute_positions: tuple[tuple[int, ...], ...]
    token_ids_sha256: str
    direction_sha256: str | None
    raw_pre_norm: torch.Tensor = field(repr=False)
    effective_pre_norm: torch.Tensor = field(repr=False)
    injected_delta: torch.Tensor = field(repr=False)
    post_norm: torch.Tensor | None = field(default=None, repr=False)

    @property
    def changed(self) -> bool:
        return bool(torch.count_nonzero(self.injected_delta).item())


@dataclass
class ValueTrace:
    surfaces: tuple[dict[str, Any], ...]
    token_ids_sha256: str
    position_policy: str
    cache_policy: str = "fresh_no_cache"
    events: list[ValueTraceEvent] = field(default_factory=list)

    def by_layer(self, layer: int) -> tuple[ValueTraceEvent, ...]:
        return tuple(event for event in self.events if event.layer == layer)


def _tensor_sha256(tensor: torch.Tensor, *, dtype: torch.dtype) -> str:
    value = tensor.detach().to(device="cpu", dtype=dtype).contiguous()
    return hashlib.sha256(value.numpy().tobytes()).hexdigest()


def _resolve_layers(model: Any) -> tuple[str, Sequence[Any]]:
    candidates = (
        ("model.language_model.layers", lambda: model.language_model.layers),
        ("model.model.language_model.layers", lambda: model.model.language_model.layers),
        ("model.language_model.model.layers", lambda: model.language_model.model.layers),
        ("model.model.language_model.model.layers", lambda: model.model.language_model.model.layers),
        ("model.model.layers", lambda: model.model.layers),
    )
    for path, getter in candidates:
        try:
            layers = getter()
        except AttributeError:
            continue
        if layers is not None:
            return path, layers
    raise SurfaceBindingError(
        f"could not locate Gemma text layers on {type(model).__name__}"
    )


def _resolve_text_config(model: Any) -> Any:
    config = getattr(model, "config", None)
    if config is None:
        raise SurfaceBindingError("loaded model has no config")
    return getattr(config, "text_config", config)


def _positions_matrix(
    absolute_positions: torch.Tensor | Sequence[int] | Sequence[Sequence[int]],
    *,
    batch: int,
    tokens: int,
) -> torch.Tensor:
    positions = torch.as_tensor(absolute_positions, dtype=torch.long, device="cpu")
    if positions.ndim == 1:
        if tuple(positions.shape) != (tokens,):
            raise RuntimeConditionError(
                f"absolute positions shape {tuple(positions.shape)} does not match token length {tokens}"
            )
        positions = positions.unsqueeze(0).expand(batch, -1).clone()
    elif positions.ndim == 2:
        if tuple(positions.shape) != (batch, tokens):
            raise RuntimeConditionError(
                "absolute positions must have shape [tokens] or [batch, tokens]; "
                f"got {tuple(positions.shape)}, expected [{batch}, {tokens}]"
            )
    else:
        raise RuntimeConditionError("absolute positions must be rank one or two")
    if torch.any(positions < 0):
        raise RuntimeConditionError("absolute positions must be non-negative")
    if tokens > 1 and torch.any(positions[:, 1:] <= positions[:, :-1]):
        raise RuntimeConditionError("absolute positions must increase strictly within each sequence")
    return positions


class Gemma4ValueNormRuntime:
    """Context-scoped capture/injection controller for reviewed Gemma teeth."""

    def __init__(
        self,
        model: Any,
        surfaces: tuple[BoundValueSurface, ...],
        *,
        max_alpha: float,
    ) -> None:
        self.model = model
        self.surfaces = surfaces
        self.max_alpha = float(max_alpha)
        self._active = False
        self._closed = False

    @classmethod
    def bind(
        cls,
        model: Any,
        teeth: Sequence[int] = APPROVED_TEETH,
        *,
        max_alpha: float = 0.4,
    ) -> "Gemma4ValueNormRuntime":
        requested = tuple(int(layer) for layer in teeth)
        if not requested or len(set(requested)) != len(requested):
            raise SurfaceBindingError("teeth must be a non-empty unique sequence")
        if any(layer not in APPROVED_TEETH for layer in requested):
            raise SurfaceBindingError(
                f"only reviewed teeth {APPROVED_TEETH} may bind, got {requested}"
            )
        if not isfinite(max_alpha) or max_alpha <= 0.0:
            raise SurfaceBindingError("max_alpha must be finite and positive")

        config = _resolve_text_config(model)
        if getattr(config, "attention_k_eq_v", None) is not True:
            raise SurfaceBindingError("Gemma option A requires attention_k_eq_v=true")
        if int(getattr(config, "num_global_key_value_heads", -1)) != 1:
            raise SurfaceBindingError("Gemma option A requires one global KV head")
        if int(getattr(config, "global_head_dim", -1)) != ACTUATOR_WIDTH:
            raise SurfaceBindingError(
                f"Gemma option A requires global_head_dim={ACTUATOR_WIDTH}"
            )
        if int(getattr(config, "num_kv_shared_layers", 0)) != 0:
            raise SurfaceBindingError("shared-KV layers are outside the reviewed option-A runtime")

        layer_types = getattr(config, "layer_types", None)
        if not isinstance(layer_types, (list, tuple)):
            raise SurfaceBindingError("Gemma text config must expose layer_types")
        layer_path, layers = _resolve_layers(model)
        surfaces: list[BoundValueSurface] = []
        for layer in requested:
            if layer >= len(layers) or layer >= len(layer_types):
                raise SurfaceBindingError(f"tooth {layer} is outside the loaded layer stack")
            if layer_types[layer] != "full_attention":
                raise SurfaceBindingError(f"tooth {layer} is not full_attention")
            attention = getattr(layers[layer], "self_attn", None)
            if attention is None:
                raise SurfaceBindingError(f"tooth {layer} has no self_attn module")
            if getattr(attention, "layer_type", None) != "full_attention":
                raise SurfaceBindingError(f"tooth {layer} runtime layer_type is not full_attention")
            if getattr(attention, "use_alternative_attention", None) is not True:
                raise SurfaceBindingError(f"tooth {layer} does not use the coupled K=V path")
            if getattr(attention, "v_proj", object()) is not None:
                raise SurfaceBindingError(f"tooth {layer} unexpectedly exposes v_proj")
            if getattr(attention, "is_kv_shared_layer", False):
                raise SurfaceBindingError(f"tooth {layer} is a shared-KV layer")
            if int(getattr(attention, "head_dim", -1)) != ACTUATOR_WIDTH:
                raise SurfaceBindingError(
                    f"tooth {layer} head width is not {ACTUATOR_WIDTH}"
                )
            k_proj = getattr(attention, "k_proj", None)
            if k_proj is None or int(getattr(k_proj, "out_features", -1)) != ACTUATOR_WIDTH:
                raise SurfaceBindingError(
                    f"tooth {layer} k_proj output width is not {ACTUATOR_WIDTH}"
                )
            v_norm = getattr(attention, "v_norm", None)
            if not isinstance(v_norm, torch.nn.Module):
                raise SurfaceBindingError(f"tooth {layer} has no v_norm module")
            if getattr(v_norm, "with_scale", None) is not False:
                raise SurfaceBindingError(f"tooth {layer} v_norm must be scale-free")
            surfaces.append(
                BoundValueSurface(
                    layer=layer,
                    module_path=f"{layer_path}.{layer}.self_attn.v_norm",
                    width=ACTUATOR_WIDTH,
                    module=v_norm,
                )
            )
        return cls(model, tuple(surfaces), max_alpha=max_alpha)

    def close(self) -> None:
        if self._active:
            raise RuntimeConditionError("cannot close an active value-norm condition")
        self._closed = True

    @contextmanager
    def condition(
        self,
        *,
        token_ids: torch.Tensor | Sequence[Sequence[int]],
        absolute_positions: torch.Tensor | Sequence[int] | Sequence[Sequence[int]],
        directions: Mapping[int, torch.Tensor | Sequence[float]] | None = None,
        alphas: Mapping[int, float] | None = None,
        position_policy: str,
        capture: bool = True,
        cache_policy: str = "fresh_no_cache",
    ) -> Iterator[ValueTrace]:
        """Arm reviewed tooth hooks for one fresh-cache teacher-forced condition.

        The caller must run the host with ``use_cache=False``.  This API refuses
        any other cache policy because removing a hook cannot undo injected KV
        cache entries.
        """

        if self._closed:
            raise RuntimeConditionError("value-norm runtime is closed")
        if self._active:
            raise RuntimeConditionError("nested value-norm conditions are forbidden")
        if position_policy not in POSITION_POLICIES:
            raise RuntimeConditionError(
                f"position_policy must be one of {sorted(POSITION_POLICIES)}"
            )
        if cache_policy != "fresh_no_cache":
            raise RuntimeConditionError("C1 conditions require a fresh forward with use_cache=False")

        tokens = torch.as_tensor(token_ids, dtype=torch.long, device="cpu")
        if tokens.ndim != 2 or not tokens.shape[0] or not tokens.shape[1]:
            raise RuntimeConditionError("token_ids must be a non-empty [batch, tokens] matrix")
        positions = _positions_matrix(
            absolute_positions, batch=int(tokens.shape[0]), tokens=int(tokens.shape[1])
        )
        token_hash = _tensor_sha256(tokens, dtype=torch.int64)
        directions = dict(directions or {})
        alphas = {int(layer): float(alpha) for layer, alpha in dict(alphas or {}).items()}
        surface_by_layer = {surface.layer: surface for surface in self.surfaces}
        unknown = (set(directions) | set(alphas)) - set(surface_by_layer)
        if unknown:
            raise RuntimeConditionError(f"condition names unbound teeth: {sorted(unknown)}")

        prepared: dict[int, tuple[torch.Tensor | None, str | None, float]] = {}
        for layer in surface_by_layer:
            alpha = alphas.get(layer, 0.0)
            if not isfinite(alpha) or not 0.0 <= alpha <= self.max_alpha:
                raise RuntimeConditionError(
                    f"tooth {layer} alpha must be finite and in [0, {self.max_alpha}]"
                )
            raw_direction = directions.get(layer)
            if alpha == 0.0 and raw_direction is None:
                prepared[layer] = (None, None, alpha)
                continue
            if raw_direction is None:
                raise RuntimeConditionError(f"tooth {layer} needs a direction for nonzero alpha")
            direction = torch.as_tensor(raw_direction, dtype=torch.float32, device="cpu")
            if tuple(direction.shape) != (ACTUATOR_WIDTH,):
                raise RuntimeConditionError(
                    f"tooth {layer} direction must have shape [{ACTUATOR_WIDTH}]"
                )
            if not torch.isfinite(direction).all():
                raise RuntimeConditionError(f"tooth {layer} direction contains non-finite values")
            norm = torch.linalg.vector_norm(direction)
            if not torch.isfinite(norm) or float(norm) <= 0.0:
                raise RuntimeConditionError(f"tooth {layer} direction norm must be finite and positive")
            unit = direction / norm
            prepared[layer] = (unit, _tensor_sha256(unit, dtype=torch.float32), alpha)

        trace = ValueTrace(
            surfaces=tuple(surface.report() for surface in self.surfaces),
            token_ids_sha256=token_hash,
            position_policy=position_policy,
            cache_policy=cache_policy,
        )
        pending: dict[int, list[ValueTraceEvent]] = {layer: [] for layer in surface_by_layer}
        handles: list[Any] = []

        def make_pre_hook(layer: int):
            def pre_hook(module: torch.nn.Module, module_in: tuple[Any, ...]):
                del module
                if not isinstance(module_in, tuple) or not module_in:
                    raise RuntimeConditionError(f"tooth {layer} v_norm input is not a tensor tuple")
                raw = module_in[0]
                if not isinstance(raw, torch.Tensor):
                    raise RuntimeConditionError(f"tooth {layer} v_norm input is not a tensor")
                expected_shape = (int(tokens.shape[0]), int(tokens.shape[1]), 1, ACTUATOR_WIDTH)
                if tuple(raw.shape) != expected_shape:
                    raise RuntimeConditionError(
                        f"tooth {layer} v_norm input shape {tuple(raw.shape)} != {expected_shape}"
                    )
                unit, direction_hash, alpha = prepared[layer]
                if alpha == 0.0:
                    effective = raw
                    delta = torch.zeros_like(raw)
                    replacement = None
                else:
                    assert unit is not None
                    rms = raw.float().pow(2).mean(dim=-1, keepdim=True).sqrt()
                    delta = alpha * rms * unit.to(device=raw.device).view(1, 1, 1, -1)
                    if position_policy == "exclude_absolute_zero":
                        mask = positions.ne(0).to(device=raw.device).view(
                            int(tokens.shape[0]), int(tokens.shape[1]), 1, 1
                        )
                        delta = delta * mask
                    delta = delta.to(dtype=raw.dtype)
                    effective = raw + delta
                    replacement = (effective, *module_in[1:])

                if capture:
                    event = ValueTraceEvent(
                        layer=layer,
                        call_index=len(pending[layer]),
                        alpha=alpha,
                        position_policy=position_policy,
                        absolute_positions=tuple(
                            tuple(int(value) for value in row) for row in positions.tolist()
                        ),
                        token_ids_sha256=token_hash,
                        direction_sha256=direction_hash,
                        raw_pre_norm=raw.detach().cpu().clone(),
                        effective_pre_norm=effective.detach().cpu().clone(),
                        injected_delta=delta.detach().cpu().clone(),
                    )
                    pending[layer].append(event)
                    trace.events.append(event)
                return replacement

            return pre_hook

        def make_post_hook(layer: int):
            def post_hook(module: torch.nn.Module, module_in: tuple[Any, ...], module_out: Any):
                del module, module_in
                if not capture:
                    return
                if not pending[layer]:
                    raise RuntimeConditionError(f"tooth {layer} v_norm output arrived without capture")
                if not isinstance(module_out, torch.Tensor):
                    raise RuntimeConditionError(f"tooth {layer} v_norm output is not a tensor")
                pending[layer][-1].post_norm = module_out.detach().cpu().clone()

            return post_hook

        self._active = True
        try:
            for surface in self.surfaces:
                handles.append(surface.module.register_forward_pre_hook(make_pre_hook(surface.layer)))
                handles.append(surface.module.register_forward_hook(make_post_hook(surface.layer)))
            yield trace
        finally:
            for handle in handles:
                handle.remove()
            self._active = False


__all__ = [
    "ACTUATOR_DECISION",
    "ACTUATOR_WIDTH",
    "APPROVED_TEETH",
    "BoundValueSurface",
    "CAPTURE_MODE",
    "Gemma4ValueNormRuntime",
    "POSITION_POLICIES",
    "RuntimeConditionError",
    "SURFACE_KIND",
    "SurfaceBindingError",
    "ValueTrace",
    "ValueTraceEvent",
]
