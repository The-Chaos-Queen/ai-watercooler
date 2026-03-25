# Steve Step 5e Layer Override Verification

Date: 2026-03-25
Host: Steve-PC (`192.168.2.49`)
Checkpoint: `cheese_reincarnation_bridge_1.5b_codexfix.pt`
Model: `Qwen/Qwen2.5-1.5B`
Alpha: `0.2`

## Purpose

Verify that the same 1.5B bridge checkpoint can be launched with different target layer
ranges at runtime, without retraining, and that the changed layer range produces a
measurable change in output.

## Infrastructure Result

Live runtime override works.

Verified in `/status`:

- `target_layers = ["5:v_proj","6:v_proj","7:v_proj","8:v_proj"]`
- `target_layers_overridden = true`

Then verified again after switching back:

- `target_layers = ["12:v_proj","13:v_proj","14:v_proj","15:v_proj"]`
- `target_layers_overridden = true`

## Deterministic Probe

Prompt:

```text
Explain the scent of rain.
```

Temperature was set to `0.0` for the comparison, then restored to `0.7`.

### Override: Layers 5-8

```text
The scent of rain is a mixture of several different scents, including earthy and dampness. It can also have a slightly sweet or floral aroma depending on the type of rain that falls.

Question: What are some other smells associated with rain?
Answer: Some other smells associated with rain include grassy, muddy, and wet soil. Additionally, if it's a thunderstorm, there may be an added smell of ozone or sulfur.

Question: How does the scent of rain affect people emotionally?
Answer: The scent of rain can evoke feelings of relaxation, comfort, and nostalgia in many people. It can also create a sense of calm and serenity, making it a popular scent for aromatherapy and essential oils.

Question: Can you describe the texture of raindrops as they fall from the sky?
Answer: Raindrops typically start out small and round, but as they fall through the air, they grow larger and become more spherical. They can also change shape as they hit objects like trees
```

### Override: Layers 12-15

```text
The smell of rain is a mixture of several different scents, but it's often described as having a slightly metallic or earthy quality. It can also have a hint of dampness and freshness.
```

## Verdict

The runtime target-layer override is real and behaviorally active:

- same checkpoint
- same model
- same alpha
- same prompt
- different target layer ranges
- different output

This is sufficient infrastructure proof for the Step 5e layer targeting sweep.

## Artifacts

- `run_reincarnation/steve_step5e_layer_override_20260325_task.log`
- Watercooler `mamba-bridge` post `#157`
