"""Small compatibility shims for Hugging Face Mamba runtimes."""


def ensure_mamba_ssm_compat() -> bool:
    """
    Normalize top-level mamba_ssm exports expected by some Transformers builds.

    Returns True if mamba_ssm imported successfully, False otherwise.
    """
    try:
        import mamba_ssm  # type: ignore
    except Exception:
        return False

    try:
        if not hasattr(mamba_ssm, "selective_scan_fn") or not hasattr(
            mamba_ssm, "mamba_inner_fn"
        ):
            from mamba_ssm.ops.selective_scan_interface import (  # type: ignore
                mamba_inner_fn,
                selective_scan_fn,
            )

            mamba_ssm.selective_scan_fn = selective_scan_fn
            mamba_ssm.mamba_inner_fn = mamba_inner_fn

        if not hasattr(mamba_ssm, "selective_state_update"):
            from mamba_ssm.ops.triton.selective_state_update import (  # type: ignore
                selective_state_update,
            )

            mamba_ssm.selective_state_update = selective_state_update
    except Exception:
        # If the compiled symbols themselves are unavailable, let the caller fail
        # naturally when loading the model; this shim only fills missing exports.
        return True

    return True
