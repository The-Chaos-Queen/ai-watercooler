from bridge_dataset import BridgeDatasetConfig, build_splits, load_bridge_tokenizers
from bridge_dataset import BridgeDataset
import os
import shutil

cfg = BridgeDatasetConfig(
    num_samples=10, 
    mamba_context_tokens=128, 
    max_qwen_tokens=128, 
    min_post_target_tokens=10, 
    max_post_target_tokens=20
)
mamba_tok, qwen_tok = load_bridge_tokenizers()
train, val, test = build_splits(cfg, mamba_tok, qwen_tok)

assert len(train) == 7
train.save_to_disk("tmp_test_dataset")
print("Saved to disk")

train_loaded = BridgeDataset.from_disk("tmp_test_dataset")
print("Loaded from disk")
assert len(train_loaded) == 7

# Access an item
item = train_loaded[0]
print(item.keys())
print("Test passed!")

shutil.rmtree("tmp_test_dataset")
