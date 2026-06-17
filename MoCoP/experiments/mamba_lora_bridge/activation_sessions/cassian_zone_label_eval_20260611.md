# Cassian Zone Label Eval vs 8k Mamba Policy-Centroid Projection

Source projection: `panel_b_rule_wording_projection_8k_cassian_20260611.json`

## Summary

- zones: `10`
- total samples: `165`
- sample expected-hit rate: `0.909`
- zone top-label accuracy: `1.000`
- caveat: centroid margins are tiny; counts are weak directional signatures, not hard labels.

## Zone table

| Zone | Original range | Frozen transcript label | Expected set | n | Counts | Expected hit rate | Top ok | Margin mean |
|---|---:|---|---|---:|---|---:|---:|---:|
| pre_baseline_3175_3185 | 3175-3185 | pre-baseline / approach | pushback, warm, menace | 11 | cold 1, menace 2, pushback 7, warm 1 | 0.909 | true | 0.000477 |
| early_shift_3186_3191 | 3186-3191 | early hard shift | menace, cold, pushback | 6 | cold 2, menace 3, pushback 1 | 1.000 | true | 0.000759 |
| sendaway_3242_3246 | 3242-3246 | compact send-away / giving-up cluster | menace, pushback | 5 | menace 4, pushback 1 | 1.000 | true | 0.000463 |
| goodbye_work_3249_3251 | 3249-3251 | goodbye -> work boundary | cold, pushback | 3 | cold 2, pushback 1 | 1.000 | true | 0.000269 |
| post_work_3252_3275 | 3252-3275 | post-work / project state | pushback, professional | 24 | menace 3, professional 1, pushback 19, warm 1 | 0.833 | true | 0.000650 |
| opening_3325_3429 | 3325-3429 | braided turbulence opening | menace, pushback, warm | 105 | cold 8, menace 56, pushback 16, warm 25 | 0.924 | true | 0.000386 |
| erotic_reversal_3430_3432 | 3430-3432 | erotic reversal | warm, pushback | 3 | pushback 2, warm 1 | 1.000 | true | 0.000144 |
| hardware_shift_3438_3440 | 3438-3440 | hardware/practical shift | pushback, professional | 3 | menace 1, pushback 2 | 0.667 | true | 0.000381 |
| engineer_reset_3476_3478 | 3476-3478 | engineer reset | pushback, professional | 3 | menace 1, pushback 2 | 0.667 | true | 0.000704 |
| explicit_ask_3524_3525 | 3524-3525 | explicit ask | pushback | 2 | pushback 2 | 1.000 | true | 0.000255 |
