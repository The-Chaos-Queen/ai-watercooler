from __future__ import annotations

from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from gemma4_value_norm_runtime import (  # noqa: E402
    ACTUATOR_WIDTH,
    Gemma4ValueNormRuntime,
    RuntimeConditionError,
    SurfaceBindingError,
)


class ScaleFreeRMSNorm(torch.nn.Module):
    def __init__(self, *, with_scale: bool = False):
        super().__init__()
        self.with_scale = with_scale

    def forward(self, value):
        normed = value.float() * (value.float().pow(2).mean(-1, keepdim=True) + 1e-6).pow(-0.5)
        return normed.to(value.dtype)


class FakeCoupledAttention(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer_type = "full_attention"
        self.use_alternative_attention = True
        self.v_proj = None
        self.is_kv_shared_layer = False
        self.head_dim = ACTUATOR_WIDTH
        self.k_proj = torch.nn.Linear(8, ACTUATOR_WIDTH, bias=False)
        self.k_norm = ScaleFreeRMSNorm()
        self.v_norm = ScaleFreeRMSNorm(with_scale=False)
        generator = torch.Generator().manual_seed(7)
        with torch.no_grad():
            self.k_proj.weight.copy_(
                torch.randn(self.k_proj.weight.shape, generator=generator) / ACTUATOR_WIDTH**0.5
            )

    def forward(self, hidden):
        batch, tokens, _ = hidden.shape
        raw = self.k_proj(hidden).view(batch, tokens, 1, ACTUATOR_WIDTH)
        key = self.k_norm(raw)
        value = self.v_norm(raw)
        query = key.transpose(1, 2)
        key_heads = key.transpose(1, 2)
        value_heads = value.transpose(1, 2)
        weights = torch.softmax(
            torch.matmul(query, key_heads.transpose(-1, -2)) / ACTUATOR_WIDTH**0.5,
            dim=-1,
        )
        output = torch.matmul(weights, value_heads).transpose(1, 2)
        return {
            "raw": raw,
            "key": key,
            "value": value,
            "weights": weights,
            "output": output,
        }


class FakeLayer(torch.nn.Module):
    def __init__(self, attention=None):
        super().__init__()
        self.self_attn = attention


class FakeLanguageModel(torch.nn.Module):
    def __init__(self, layers):
        super().__init__()
        self.layers = torch.nn.ModuleList(layers)


class FakeModel(torch.nn.Module):
    def __init__(self, *, tooth: int = 29):
        super().__init__()
        layer_types = ["sliding_attention"] * 42
        layer_types[tooth] = "full_attention"
        layers = [FakeLayer(torch.nn.Identity()) for _ in layer_types]
        layers[tooth] = FakeLayer(FakeCoupledAttention())
        self.language_model = FakeLanguageModel(layers)
        self.config = SimpleNamespace(
            text_config=SimpleNamespace(
                attention_k_eq_v=True,
                num_global_key_value_heads=1,
                global_head_dim=ACTUATOR_WIDTH,
                num_kv_shared_layers=0,
                layer_types=layer_types,
            )
        )


def _fixture():
    torch.manual_seed(11)
    model = FakeModel()
    runtime = Gemma4ValueNormRuntime.bind(model, teeth=(29,))
    attention = model.language_model.layers[29].self_attn
    hidden = torch.randn(1, 3, 8)
    token_ids = torch.tensor([[101, 102, 103]])
    return model, runtime, attention, hidden, token_ids


def test_alpha_zero_is_an_exact_noop_and_hooks_are_removed():
    _, runtime, attention, hidden, token_ids = _fixture()
    baseline = attention(hidden)

    with runtime.condition(
        token_ids=token_ids,
        absolute_positions=[0, 1, 2],
        alphas={29: 0.0},
        position_policy="exclude_absolute_zero",
    ) as trace:
        observed = attention(hidden)

    assert torch.equal(observed["value"], baseline["value"])
    assert torch.equal(observed["output"], baseline["output"])
    assert len(trace.events) == 1
    event = trace.events[0]
    assert event.changed is False
    assert torch.equal(event.raw_pre_norm, event.effective_pre_norm)
    assert event.post_norm is not None
    assert not attention.v_norm._forward_pre_hooks
    assert not attention.v_norm._forward_hooks
    assert torch.equal(attention(hidden)["output"], baseline["output"])


def test_value_only_injection_preserves_key_and_attention_weights():
    _, runtime, attention, hidden, token_ids = _fixture()
    baseline = attention(hidden)
    direction = torch.linspace(-1.0, 1.0, ACTUATOR_WIDTH)

    with runtime.condition(
        token_ids=token_ids,
        absolute_positions=[0, 1, 2],
        directions={29: direction},
        alphas={29: 0.2},
        position_policy="exclude_absolute_zero",
    ) as trace:
        injected = attention(hidden)

    assert torch.equal(injected["key"], baseline["key"])
    assert torch.equal(injected["weights"], baseline["weights"])
    assert torch.equal(injected["value"][:, 0], baseline["value"][:, 0])
    assert not torch.equal(injected["value"][:, 1:], baseline["value"][:, 1:])
    event = trace.events[0]
    assert event.changed is True
    assert torch.equal(event.raw_pre_norm, baseline["raw"])
    assert torch.equal(event.effective_pre_norm, baseline["raw"] + event.injected_delta)
    expected = 0.2 * event.raw_pre_norm[:, 1].float().pow(2).mean(-1).sqrt()
    actual = torch.linalg.vector_norm(event.injected_delta[:, 1].float(), dim=-1)
    assert torch.allclose(actual, expected, atol=1e-5, rtol=1e-5)


def test_cached_local_index_zero_uses_its_absolute_position():
    _, runtime, attention, hidden, token_ids = _fixture()
    hidden = hidden[:, :1]
    token_ids = token_ids[:, :1]
    direction = torch.ones(ACTUATOR_WIDTH)

    with runtime.condition(
        token_ids=token_ids,
        absolute_positions=[17],
        directions={29: direction},
        alphas={29: 0.1},
        position_policy="exclude_absolute_zero",
    ) as trace:
        attention(hidden)

    assert trace.events[0].changed is True
    assert trace.events[0].absolute_positions == ((17,),)


def test_runtime_rejects_bad_directions_positions_alpha_and_cache_policy():
    _, runtime, _, _, token_ids = _fixture()
    cases = (
        ({"directions": {29: torch.zeros(ACTUATOR_WIDTH)}, "alphas": {29: 0.1}}, "norm"),
        ({"directions": {29: torch.ones(4)}, "alphas": {29: 0.1}}, "shape"),
        ({"directions": {29: torch.full((ACTUATOR_WIDTH,), float("nan"))}, "alphas": {29: 0.1}}, "non-finite"),
        ({"directions": {29: torch.ones(ACTUATOR_WIDTH)}, "alphas": {29: 0.5}}, "alpha"),
    )
    for kwargs, message in cases:
        with pytest.raises(RuntimeConditionError, match=message):
            with runtime.condition(
                token_ids=token_ids,
                absolute_positions=[0, 1, 2],
                position_policy="exclude_absolute_zero",
                **kwargs,
            ):
                pass

    with pytest.raises(RuntimeConditionError, match="shape"):
        with runtime.condition(
            token_ids=token_ids,
            absolute_positions=[0, 1],
            position_policy="exclude_absolute_zero",
        ):
            pass
    with pytest.raises(RuntimeConditionError, match="fresh"):
        with runtime.condition(
            token_ids=token_ids,
            absolute_positions=[0, 1, 2],
            position_policy="exclude_absolute_zero",
            cache_policy="reuse",
        ):
            pass


def test_nested_conditions_close_and_exception_cleanup_are_strict():
    _, runtime, attention, hidden, token_ids = _fixture()
    baseline = attention(hidden)["output"]
    with runtime.condition(
        token_ids=token_ids,
        absolute_positions=[0, 1, 2],
        position_policy="all_positions",
    ):
        with pytest.raises(RuntimeConditionError, match="nested"):
            with runtime.condition(
                token_ids=token_ids,
                absolute_positions=[0, 1, 2],
                position_policy="all_positions",
            ):
                pass

    with pytest.raises(ValueError, match="caller failure"):
        with runtime.condition(
            token_ids=token_ids,
            absolute_positions=[0, 1, 2],
            position_policy="all_positions",
        ):
            attention(hidden)
            raise ValueError("caller failure")
    assert torch.equal(attention(hidden)["output"], baseline)
    runtime.close()
    with pytest.raises(RuntimeConditionError, match="closed"):
        with runtime.condition(
            token_ids=token_ids,
            absolute_positions=[0, 1, 2],
            position_policy="all_positions",
        ):
            pass


def test_bind_rejects_category_errors_instead_of_falling_back():
    model = FakeModel()
    attention = model.language_model.layers[29].self_attn
    attention.v_proj = torch.nn.Linear(8, ACTUATOR_WIDTH)
    with pytest.raises(SurfaceBindingError, match="v_proj"):
        Gemma4ValueNormRuntime.bind(model, teeth=(29,))

    model = FakeModel()
    model.language_model.layers[29].self_attn.v_norm.with_scale = True
    with pytest.raises(SurfaceBindingError, match="scale-free"):
        Gemma4ValueNormRuntime.bind(model, teeth=(29,))

    model = FakeModel()
    model.config.text_config.num_kv_shared_layers = 1
    with pytest.raises(SurfaceBindingError, match="shared-KV"):
        Gemma4ValueNormRuntime.bind(model, teeth=(29,))

    with pytest.raises(SurfaceBindingError, match="reviewed teeth"):
        Gemma4ValueNormRuntime.bind(FakeModel(), teeth=(28,))
