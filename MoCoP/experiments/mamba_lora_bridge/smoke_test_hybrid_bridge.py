import torch
from hybrid_bridge import HybridBridge

def run_smoke_test():
    print("Starting HybridBridge Smoke Test...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Initializing HybridBridge (loading Qwen2.5-0.5B core)...")
    try:
        model = HybridBridge(
            hybrid_model_id="Qwen/Qwen2.5-0.5B",
            mamba_hidden_dim=2560,
            target_hidden_dim=3584,
            num_virtual_tokens=16
        )
        # Cast the newly initialized parameters to match the core model's dtype
        model = model.to(dtype=model.hybrid_core.dtype, device=device)
        print(f"Model initialized successfully. Dtype: {model.hybrid_core.dtype}")
    except Exception as e:
        print(f"Failed to initialize model: {e}")
        return

    # Simulate a batch of Mamba state sequences
    # [batch_size, sequence_length, mamba_hidden_dim]
    batch_size = 2
    seq_len = 8  # Passing 8 tokens as suggested by the literature
    print(f"Generating dummy Mamba input sequence of shape [{batch_size}, {seq_len}, 2560]...")
    dummy_input = torch.randn(batch_size, seq_len, 2560, device=device, dtype=model.input_proj.weight.dtype)

    print("Running forward pass...")
    try:
        virtual_tokens = model(dummy_input)
        print(f"Forward pass successful. Output shape: {virtual_tokens.shape}")
        
        expected_shape = (batch_size, 16, 3584)
        if virtual_tokens.shape == expected_shape:
            print(f"SUCCESS: Output shape matches expected {expected_shape}.")
        else:
            print(f"ERROR: Output shape {virtual_tokens.shape} does not match expected {expected_shape}.")
    except Exception as e:
        print(f"Forward pass failed: {e}")
        return

    print("Testing backward pass...")
    try:
        loss = virtual_tokens.sum()
        loss.backward()
        print("Backward pass successful. Gradients computed.")
    except Exception as e:
        print(f"Backward pass failed: {e}")
        return

    print("\nSmoke test COMPLETE. HybridBridge is structurally sound.")

if __name__ == "__main__":
    run_smoke_test()
