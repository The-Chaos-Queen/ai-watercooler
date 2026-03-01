"""Quick environment check. Run this to see what we're working with."""
import sys
print("Python:", sys.version)
print("Platform:", sys.platform)

try:
    import torch
    print("PyTorch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        print("VRAM:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), "GB")
    else:
        print("GPU: None (CPU only)")
except ImportError:
    print("PyTorch: NOT INSTALLED")

try:
    import transformers
    print("Transformers:", transformers.__version__)
except ImportError:
    print("Transformers: NOT INSTALLED")

try:
    import bitsandbytes
    print("bitsandbytes:", bitsandbytes.__version__)
except ImportError:
    print("bitsandbytes: NOT INSTALLED")

try:
    from fastapi import FastAPI
    print("FastAPI: installed")
except ImportError:
    print("FastAPI: NOT INSTALLED")
