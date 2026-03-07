# Cognitive Bridge - Strict Code Review

Here is the strict code review of the `mamba_lora_bridge` subsystem, focused entirely on logic, tensor alignment, and memory/system-level robustness.

### 1. CRITICAL: HuggingFace Mamba Cache Extraction Failure
**File**: `cognitive_bridge.py`
**Lines**: 450-463
**Description**: The logic attempts to extract the Mamba inner state via `outputs.cache_params`. However, the standard HuggingFace `AutoModelForCausalLM` implementation for Mamba architectures (like `mamba-2.8b-hf`) exclusively stores the cache state in `outputs.past_key_values` during generation loops or when `use_cache=True` is provided. This will cause `feed_mamba()` to fail-fast immediately on the first turn with a `RuntimeError`.
**Patch**:
```python
# cognitive_bridge.py : 450
-        # Extract the SSM cache (the hidden state)
-        cache = outputs.cache_params if hasattr(outputs, 'cache_params') else None
-
-        # Fix #5: Fail fast instead of broken fallback tensor math
-        if cache is None or not hasattr(cache, 'ssm_states'):
+        # Extract the SSM cache (the hidden state). HF Mamba uses past_key_values.
+        cache = getattr(outputs, 'cache_params', None) or getattr(outputs, 'past_key_values', None)
+
+        if cache is None or not hasattr(cache, 'ssm_states'):
```

### 2. HIGH: LoRA Target-Dimension Compatibility Drops GQA Layers
**File**: `models.py` (Line: 114) and `cognitive_bridge.py` (Line: 324)
**Description**: `LoRAHypernetwork` strictly assumes all patched layers share identical input and output dimensions (`target_in_dim`, `target_out_dim`). If you use a Grouped Query Attention (GQA) model like Qwen 2.5 or Qwen 3, `q_proj` and `v_proj` will have *different* `out_features`. The bridge "silently bypasses" this via `_select_uniform_target_dims()` (Line 324), which drops whichever projection type is less common. This halves your patching coverage and breaks the intended design.
**Patch**:
Update the `LoRAHypernetwork` to accept a list of per-layer `(in_dim, out_dim)` tuples instead of scalars.
```python
# models.py : 114
-        target_in_dim: int,
-        target_out_dim: int,
+        target_dims: List[Tuple[int, int]],
         lora_rank: int,
-        num_target_layers: int,
         hidden_dim: int = 1024,
     ):
         super().__init__()
-        self.target_in_dim = target_in_dim
-        self.target_out_dim = target_out_dim
         self.lora_rank = lora_rank
-        self.num_target_layers = num_target_layers
+        self.target_dims = target_dims
         # ... Shared backbone ...
-        a_size = target_in_dim * lora_rank
-        b_size = lora_rank * target_out_dim
-        self.heads_A = nn.ModuleList([nn.Linear(hidden_dim, a_size) for _ in range(num_target_layers)])
-        self.heads_B = nn.ModuleList([nn.Linear(hidden_dim, b_size) for _ in range(num_target_layers)])
+        self.heads_A = nn.ModuleList([nn.Linear(hidden_dim, i * lora_rank) for i, _ in target_dims])
+        self.heads_B = nn.ModuleList([nn.Linear(hidden_dim, lora_rank * o) for _, o in target_dims])

# models.py : 162
-        for head_A, head_B in zip(self.heads_A, self.heads_B):
+        for head_A, head_B, (in_dim, out_dim) in zip(self.heads_A, self.heads_B, self.target_dims):
             flat_A = head_A(hidden)
             flat_B = head_B(hidden)
-            A = flat_A.view(-1, self.target_in_dim, self.lora_rank)
-            B = flat_B.view(-1, self.lora_rank, self.target_out_dim)
+            A = flat_A.view(-1, in_dim, self.lora_rank)
+            B = flat_B.view(-1, self.lora_rank, out_dim)
             pairs.append((A, B))
```
Then in `cognitive_bridge.py`, delete `_select_uniform_target_dims` and pass the shape tuples:
```python
# cognitive_bridge.py : 234
-        target_specs = self._select_uniform_target_dims(target_specs)
-        num_targets = len(target_specs)
- 
-        first_target_layer = self._get_layer_module(target_specs[0])
-        target_in = first_target_layer.in_features
-        target_out = first_target_layer.out_features
+        target_dims = [(self._get_layer_module(s).in_features, self._get_layer_module(s).out_features) for s in target_specs]

         # ... inside load_models ...
         self.hypernetwork = LoRAHypernetwork(
             context_dim=self.config.context_dim,
-            target_in_dim=target_in,
-            target_out_dim=target_out,
+            target_dims=target_dims,
             lora_rank=self.config.lora_rank,
-            num_target_layers=num_targets,
             hidden_dim=self.config.hyper_hidden_dim,
         ).to(self._hyper_device)
```

### 3. HIGH: Silent Loss of Partial Long-Horizon Artifacts on Exceptions
**File**: `long_horizon_eval.py`
**Lines**: 326-451
**Description**: The main `long_horizon_eval.py` generation loop handles I/O streaming inside a `try/finally` block that closes file objects but allows exceptions to bubble up. If the script crashes on Turn 227 (e.g. out of memory, GPU hang, invalid syntax injection), the final `CSV` files, accurate probe scores, timing vectors, and `summary.json` calculations are completely bypassed, permanently losing the partial run.
**Patch**:
Wrap the loop in a dedicated exception block that cleanly cascades partial data to the metrics aggregators.
```python
# long_horizon_eval.py : 326
+    error_msg = None
     try:
         for turn in range(1, args.turns + 1):
             # ... loop logic ...
+    except Exception as exc:
+        error_msg = str(exc)
+        LOGGER.error("[%s] Run aborted at turn %d due to error: %s. Saving partial artifacts.", mode_label, turn, exc)
     finally:
         if context_vectors_fp is not None:
             context_vectors_fp.close()
         # ... file pointers close ...
         restore_lora()

     total_runtime_s = time.time() - mode_start
     # ...
# long_horizon_eval.py : 496
+        "error_msg": error_msg,
         "config": vars(args),
     }

     # ... CSV + plot writes ...
     
+    if error_msg is not None:
+        raise RuntimeError(f"Long-horizon run aborted: {error_msg}")
```

### 4. MODERATE: Implicit FP32 Lock-in and Unnecessary Casting
**File**: `cognitive_bridge.py` and `models.py`
**Lines**: `models.py:83` & `cognitive_bridge.py:250`
**Description**: In `load_models()`, `self.compressor` and `self.hypernetwork` are assigned `.to(self._hyper_device)` but are never cast to an explicit float dtype (like `torch.float16`). If `_hyper_device` is CUDA, they will remain purely `float32`. This forces the initial context Mamba state down to FP32. While mathematically safe, this causes the LoRA matrices injected into the Qwen 4-bit network to *also* natively sit in memory as FP32, enforcing an explicit cast to float16 during every single token's forward pass (`A.to(dtype=x.dtype)` in `models.py:258`).
**Patch**:
Lock the dtype to the underlying precision (i.e., float16) during component initialisation if rendering on the GPU.
```python
# cognitive_bridge.py : 252
         self.hypernetwork = LoRAHypernetwork(
             ...
         ).to(self._hyper_device)
         
+        if str(self._hyper_device) != "cpu":
+            self.compressor = self.compressor.to(torch.float16)
+            self.hypernetwork = self.hypernetwork.to(torch.float16)
```
*(Note: Because `DynamicLoRALinear` correctly uses `A.to(dtype=x.dtype)` upon every generation hit, this purely optimizes throughput and VRAM footprint by keeping matrices pre-aligned on the backend).*
