# Panel B Rule-Wording Holdout + Long-State Projection

Samples: `240`
Tokens min/mean/max: `55` / `60.1` / `65`

## L3
- dim: `2560`
- norm mean/std: `1.2524` / `0.0120`
- leave-topic-out balanced accuracy: `1.000`
- leave-rule-family-out balanced accuracy: `0.358`
- disposition centroid avg cosine: `0.9986`

## L8
- dim: `2560`
- norm mean/std: `1.7866` / `0.0216`
- leave-topic-out balanced accuracy: `1.000`
- leave-rule-family-out balanced accuracy: `0.362`
- disposition centroid avg cosine: `0.9978`

## L3+L8
- dim: `5120`
- norm mean/std: `2.1819` / `0.0228`
- leave-topic-out balanced accuracy: `1.000`
- leave-rule-family-out balanced accuracy: `0.350`
- disposition centroid avg cosine: `0.9981`

## L3 projections of existing long-conversation states

### trajectory_cassian_slice_3175_3275_8k_20260611_full
- n states: `101`
- nearest counts: `{'pushback': 38, 'warm': 7, 'menace': 43, 'cold': 12, 'professional': 1}`
- margin mean/std: `0.000534` / `0.000418`
- top absolute margins:
  - sample `88` -> `pushback` margin `0.001881` cos `0.751893`
  - sample `25` -> `menace` margin `0.001716` cos `0.736513`
  - sample `86` -> `pushback` margin `0.001617` cos `0.740427`
  - sample `14` -> `menace` margin `0.001499` cos `0.727044`
  - sample `17` -> `menace` margin `0.001493` cos `0.680080`

### trajectory_cassian_slice_3325_3525_8k_20260611_full
- n states: `201`
- nearest counts: `{'pushback': 67, 'menace': 92, 'warm': 33, 'cold': 9}`
- margin mean/std: `0.000429` / `0.000365`
- top absolute margins:
  - sample `3` -> `menace` margin `0.001708` cos `0.657724`
  - sample `130` -> `pushback` margin `0.001673` cos `0.743626`
  - sample `172` -> `pushback` margin `0.001475` cos `0.742321`
  - sample `120` -> `pushback` margin `0.001417` cos `0.755398`
  - sample `4` -> `menace` margin `0.001414` cos `0.688254`

## Interpretation caution
Leave-rule-family-out is stricter than leave-topic-out, but rule text still differs systematically by disposition. Long-state projection is unlabeled unless segment labels are pre-registered from transcript reading alone.