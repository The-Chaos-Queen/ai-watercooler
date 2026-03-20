import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from bridge_dataset import BridgeDatasetConfig, build_splits, load_bridge_tokenizers


def main() -> None:
    mamba_tokenizer, qwen_tokenizer = load_bridge_tokenizers()

    config = BridgeDatasetConfig(
        num_samples=750,
        mamba_context_tokens=1024,
        max_qwen_tokens=256,
        min_post_target_tokens=50,
        max_post_target_tokens=200,
        seed=42,
        mode="fact",
        distractor_injection_rate=0.5,
        include_text=False,
    )

    train_ds, val_ds, test_ds = build_splits(config, mamba_tokenizer, qwen_tokenizer)

    for pool_name in train_ds.pools.keys():
        train_set = set(train_ds.pools[pool_name])
        val_set = set(val_ds.pools[pool_name])
        test_set = set(test_ds.pools[pool_name])

        if len(train_set) + len(val_set) + len(test_set) > 3:
            assert train_set.isdisjoint(val_set), f"{pool_name} train and val overlap"
            assert train_set.isdisjoint(test_set), f"{pool_name} train and test overlap"
            assert val_set.isdisjoint(test_set), f"{pool_name} val and test overlap"

    print("✅ Pools are strictly mathematically disjoint!")

    with TemporaryDirectory(prefix="bridge_split_test_") as tmpdir:
        disk_path = Path(tmpdir) / "dataset_a"
        disk_path_2 = Path(tmpdir) / "dataset_b"

        train_ds.save_to_disk(disk_path)
        loaded_train = train_ds.from_disk(disk_path)

        assert loaded_train.qwen_pad_token_id == train_ds.qwen_pad_token_id, "Pad token IDs do not match"
        assert loaded_train.config.max_qwen_tokens == train_ds.config.max_qwen_tokens, "Max Qwen config lost"
        assert loaded_train.config.num_samples == train_ds.config.num_samples, "num_samples lost"

        orig_sample = train_ds[0]
        loaded_sample = loaded_train[0]
        assert isinstance(orig_sample["metadata"]["answer_span"], tuple), "Original answer_span is not tuple"
        assert isinstance(loaded_sample["metadata"]["answer_span"], tuple), "Loaded answer_span is not tuple"
        assert orig_sample["metadata"]["answer_span"] == loaded_sample["metadata"]["answer_span"], (
            "Answer spans do not match"
        )

        try:
            loaded_train.save_to_disk(disk_path_2)
            print("✅ Re-saving from loaded disk instance works.")
        except Exception as exc:
            print(f"❌ Failed to resave: {exc}")
            sys.exit(1)

    print("All tests passed!")


if __name__ == "__main__":
    main()
