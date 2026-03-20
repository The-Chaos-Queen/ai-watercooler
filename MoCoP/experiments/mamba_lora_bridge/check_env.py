"""Phase 2 preflight for bridge training."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

from model_defaults import DEFAULT_MAMBA_MODEL_ID, DEFAULT_QWEN_MODEL_ID

DEFAULT_QWEN_MODEL = DEFAULT_QWEN_MODEL_ID
DEFAULT_MAMBA_MODEL = DEFAULT_MAMBA_MODEL_ID
DEFAULT_MIN_FREE_GIB = 30.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Phase 2 training runtime.")
    parser.add_argument("--qwen-model", "--qwen-model-id", dest="qwen_model", default=DEFAULT_QWEN_MODEL)
    parser.add_argument("--mamba-model", "--mamba-model-id", dest="mamba_model", default=DEFAULT_MAMBA_MODEL)
    parser.add_argument("--output-dir", default="bridge_train_runs")
    parser.add_argument(
        "--checkpoint-dir",
        default="",
        help="Directory for resumable checkpoints. Defaults to --output-dir.",
    )
    parser.add_argument(
        "--hf-token-path",
        default="",
        help="Optional explicit Hugging Face token file path.",
    )
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="Fail if CUDA is not available.",
    )
    parser.add_argument(
        "--skip-model-access",
        action="store_true",
        help="Skip Hugging Face model access checks.",
    )
    parser.add_argument(
        "--min-free-gib",
        type=float,
        default=DEFAULT_MIN_FREE_GIB,
        help="Minimum free disk space required for HF cache and artifact paths.",
    )
    return parser.parse_args()


def pass_line(message: str) -> None:
    print(f"[PASS] {message}")


def fail_line(message: str) -> None:
    print(f"[FAIL] {message}")


def warn_line(message: str) -> None:
    print(f"[WARN] {message}")


def iter_token_candidates(explicit_path: str) -> Iterable[Path]:
    seen = set()
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())

    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        candidates.append(Path(hf_home).expanduser() / "token")

    candidates.append(Path.home() / ".cache" / "huggingface" / "token")
    candidates.append(Path.home() / ".huggingface" / "token")

    userprofile = os.environ.get("USERPROFILE", "").strip()
    if userprofile:
        candidates.append(Path(userprofile) / ".cache" / "huggingface" / "token")

    windows_users_root = Path("/mnt/c/Users")
    if windows_users_root.is_dir():
        candidates.extend(sorted(windows_users_root.glob("*/.cache/huggingface/token")))

    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        yield candidate


def resolve_hf_token(explicit_path: str) -> Tuple[Optional[str], Optional[str]]:
    env_token = os.environ.get("HF_TOKEN", "").strip()
    if env_token:
        return env_token, "env:HF_TOKEN"

    for candidate in iter_token_candidates(explicit_path):
        try:
            if candidate.is_file():
                token = candidate.read_text(encoding="utf-8").strip()
                if token:
                    return token, str(candidate)
        except OSError:
            continue
    return None, None


def ensure_writable_dir(path_text: str, label: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".preflight_write_test"
    probe.write_text("ok\n", encoding="utf-8")
    probe.unlink()
    pass_line(f"{label} writable: {path}")
    return path


def resolve_hf_home() -> Path:
    hf_home = os.environ.get("HF_HOME", "").strip()
    if hf_home:
        return Path(hf_home).expanduser().resolve()
    return (Path.home() / ".cache" / "huggingface").resolve()


def is_under_path(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def check_free_space(path: Path, label: str, min_free_gib: float) -> int:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        fail_line(f"{label} disk check failed for {path}: {exc}")
        return 1

    free_gib = usage.free / float(1024 ** 3)
    total_gib = usage.total / float(1024 ** 3)
    pass_line(f"{label} free space: {path} | free={free_gib:.1f} GiB | total={total_gib:.1f} GiB")

    failures = 0
    if free_gib < min_free_gib:
        fail_line(
            f"{label} free space below {min_free_gib:.1f} GiB at {path} "
            f"(free={free_gib:.1f} GiB)."
        )
        failures += 1

    shm_root = Path("/dev/shm")
    if shm_root.exists() and is_under_path(path, shm_root):
        warn_line(f"{label} is under /dev/shm ({path}); artifacts are volatile on instance stop.")

    return failures


def main() -> int:
    args = parse_args()
    failures = 0

    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")

    try:
        import torch

        pass_line(f"PyTorch: {torch.__version__}")
        cuda_available = torch.cuda.is_available()
        print(f"CUDA available: {cuda_available}")
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_gib = torch.cuda.get_device_properties(0).total_memory / float(1024 ** 3)
            pass_line(f"GPU: {gpu_name} ({vram_gib:.1f} GiB)")
        elif args.require_cuda:
            fail_line("CUDA is required for this run but is not available.")
            failures += 1
    except ImportError as exc:
        fail_line(f"PyTorch import failed: {exc}")
        return 1

    try:
        import transformers

        pass_line(f"Transformers: {transformers.__version__}")
    except ImportError as exc:
        fail_line(f"Transformers import failed: {exc}")
        return 1

    try:
        import accelerate

        pass_line(f"accelerate: {accelerate.__version__}")
    except ImportError as exc:
        fail_line(f"accelerate import failed: {exc}")
        failures += 1

    try:
        import bitsandbytes

        pass_line(f"bitsandbytes: {bitsandbytes.__version__}")
    except ImportError as exc:
        fail_line(f"bitsandbytes import failed: {exc}")
        failures += 1

    try:
        from fastapi import FastAPI  # noqa: F401

        pass_line("FastAPI: installed")
    except ImportError as exc:
        fail_line(f"FastAPI import failed: {exc}")
        failures += 1

    checkpoint_dir = args.checkpoint_dir or args.output_dir
    try:
        output_dir = ensure_writable_dir(args.output_dir, "Output dir")
        checkpoint_dir_path = ensure_writable_dir(checkpoint_dir, "Checkpoint dir")
        hf_home = ensure_writable_dir(str(resolve_hf_home()), "HF_HOME")
    except OSError as exc:
        fail_line(f"Directory write check failed: {exc}")
        failures += 1
    else:
        checked_paths = []
        for label, path in (
            ("Output dir", output_dir),
            ("Checkpoint dir", checkpoint_dir_path),
            ("HF_HOME", hf_home),
        ):
            if path in checked_paths:
                continue
            failures += check_free_space(path, label, args.min_free_gib)
            checked_paths.append(path)

    token, token_source = resolve_hf_token(args.hf_token_path)
    if token is None:
        fail_line("Hugging Face token not found in HF_TOKEN or token file.")
        failures += 1
    else:
        pass_line(f"Hugging Face token resolved from {token_source}")

    if (token is not None) and (not args.skip_model_access):
        try:
            from huggingface_hub import HfApi
            from transformers import AutoConfig

            api = HfApi(token=token)
            for model_id in (args.qwen_model, args.mamba_model):
                info = api.model_info(model_id, token=token)
                config = AutoConfig.from_pretrained(model_id, token=token)
                config_name = config.__class__.__name__
                sha = (info.sha or "")[:8] or "unknown"
                pass_line(f"Model access ok: {model_id} | config={config_name} | sha={sha}")
        except Exception as exc:
            fail_line(f"Model access check failed: {exc}")
            failures += 1

    if failures:
        print(f"Preflight failed with {failures} issue(s).")
        return 1

    print("All preflight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
