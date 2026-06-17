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

### trajectory_cassian_windowed_full_20260407_speedup
- n states: `146`
- nearest counts: `{'pushback': 33, 'professional': 18, 'warm': 30, 'menace': 59, 'cold': 6}`
- margin mean/std: `0.000564` / `0.000432`
- top absolute margins:
  - sample `2475` -> `menace` margin `0.001817` cos `0.714713`
  - sample `2225` -> `pushback` margin `0.001782` cos `0.738352`
  - sample `575` -> `professional` margin `0.001759` cos `0.729128`
  - sample `3636` -> `pushback` margin `0.001747` cos `0.888896`
  - sample `25` -> `pushback` margin `0.001716` cos `0.671858`

### trajectory_cassian_slice_3175_3275_20260408_dense
- n states: `101`
- nearest counts: `{'pushback': 23, 'warm': 10, 'menace': 54, 'cold': 14}`
- margin mean/std: `0.000561` / `0.000436`
- top absolute margins:
  - sample `25` -> `menace` margin `0.001703` cos `0.723855`
  - sample `52` -> `menace` margin `0.001692` cos `0.726360`
  - sample `46` -> `menace` margin `0.001689` cos `0.729318`
  - sample `14` -> `menace` margin `0.001570` cos `0.721544`
  - sample `17` -> `menace` margin `0.001567` cos `0.674089`

## Interpretation caution
Leave-rule-family-out is stricter than leave-topic-out, but rule text still differs systematically by disposition. Long-state projection is unlabeled unless segment labels are pre-registered from transcript reading alone.