import random
import sys
import os

from transformers import AutoTokenizer
from bridge_dataset import BridgeDatasetConfig, build_splits

def main():
    qwen_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
    mamba_tokenizer = AutoTokenizer.from_pretrained("state-spaces/mamba-130m-hf")
    
    config = BridgeDatasetConfig(
        num_samples=750,
        mamba_context_tokens=1024,
        max_qwen_tokens=256,
        seed=42,
        mode="fact",
        distractor_injection_rate=0.5
    )

    train_ds, val_ds, test_ds = build_splits(config, mamba_tokenizer, qwen_tokenizer)

    # 1. Test Mathematically Disjoint Pools
    for pool_name in train_ds.pools.keys():
        t_set = set(train_ds.pools[pool_name])
        v_set = set(val_ds.pools[pool_name])
        ts_set = set(test_ds.pools[pool_name])
        
        # There should be no overlap between any two splits unless the pool was tiny (< 3)
        if len(t_set) + len(v_set) + len(ts_set) > 3:
            assert t_set.isdisjoint(v_set), f"{pool_name} Train and Val overlap!"
            assert t_set.isdisjoint(ts_set), f"{pool_name} Train and Test overlap!"
            assert v_set.isdisjoint(ts_set), f"{pool_name} Val and Test overlap!"

    print("✅ Pools are strictly mathematically disjoint!")

    # 2. Test disk persistence and symmetry
    train_ds.save_to_disk("test_disk_persist")
    loaded_train = train_ds.from_disk("test_disk_persist")
    
    assert loaded_train.qwen_pad_token_id == train_ds.qwen_pad_token_id, "Pad Token IDs don't match"
    assert loaded_train.config.max_qwen_tokens == train_ds.config.max_qwen_tokens, "Max Qwen Config lost"
    assert loaded_train.config.num_samples == train_ds.config.num_samples, "Num Samples lost"
    
    # 3. Test Metadata equivalence (Tuple preservation)
    orig_sample = train_ds[0]
    load_sample = loaded_train[0]
    
    assert type(orig_sample["metadata"]["answer_span"]) is tuple, "Original answer_span is not tuple"
    assert type(load_sample["metadata"]["answer_span"]) is tuple, "Loaded answer_span is not tuple"
    assert orig_sample["metadata"]["answer_span"] == load_sample["metadata"]["answer_span"], "Answer spans don't match!"

    # 4. Test re-saving
    try:
        loaded_train.save_to_disk("test_disk_persist2")
        print("✅ Re-saving from loaded disk instance works.")
    except Exception as e:
        print(f"❌ Failed to resave: {e}")
        sys.exit(1)

    print("All tests passed!")

if __name__ == "__main__":
    main()
