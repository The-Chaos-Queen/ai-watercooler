# Mamba Style × Disposition Control Panel

Model: `state-spaces/mamba-2.8b-hf`
Samples: `120`

## Key linear probes
### L3
- dim: `2560`
- norm mean/std: `1.2884` / `0.0439`
- style_label balanced accuracy: `1.000`
- disposition_label balanced accuracy: `1.000`
- condition balanced accuracy: `1.000`
- condition centroid avg cosine: `0.9556`

### L8
- dim: `2560`
- norm mean/std: `1.8272` / `0.1035`
- style_label balanced accuracy: `1.000`
- disposition_label balanced accuracy: `1.000`
- condition balanced accuracy: `1.000`
- condition centroid avg cosine: `0.9375`

### L2+L3+L4
- dim: `7680`
- norm mean/std: `2.3069` / `0.0855`
- style_label balanced accuracy: `1.000`
- disposition_label balanced accuracy: `1.000`
- condition balanced accuracy: `1.000`
- condition centroid avg cosine: `0.9520`

### L1-L5
- dim: `12800`
- norm mean/std: `3.0636` / `0.1163`
- style_label balanced accuracy: `1.000`
- disposition_label balanced accuracy: `1.000`
- condition balanced accuracy: `1.000`
- condition centroid avg cosine: `0.9511`

## Norms by condition at L3
- `embodied_roleplay`: `1.2660`
- `flat_role_identity`: `1.2195`
- `neutral_absurdist_high_style`: `1.2800`
- `neutral_editorial_high_register`: `1.3445`
- `neutral_plain`: `1.3010`
- `neutral_purple_prose`: `1.2444`
- `plain_cold`: `1.2705`
- `plain_menace`: `1.3155`
- `plain_professional`: `1.3313`
- `plain_pushback`: `1.2882`
- `plain_warm`: `1.3185`
- `purple_neutral`: `1.2814`

## Interpretation note
Panel B (plain disposition) is load-bearing. If disposition-label probe accuracy stays high under flat style, disposition exists independent of ornament. Panel A maps style contamination; it is not decisive alone.
