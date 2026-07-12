# World Model Phase 2b: LS20 Consistency Replication Preregistration

**Status:** reviewed with the pre-approved terminal-run amendment from Watercooler
`#935`; collection is authorized only after the amended immutable freeze binds that
review. No Phase 2b outcome existed at amendment time.

**OpenCLAW:** `#152`

**Primary reviewer:** Isegrim

**Scope:** offline LS20 transition prediction only. This document does not
authorize a learned observer, bridge loss, Gemma dose, online action selection,
Qdrant access, memory routing, or dynamic-alpha control.

## 1. Question and prior result

Phase 2 v1 ended at `NO_GO_RUN_INCONSISTENT`. Its LS20 aggregate and unweighted
run-macro effects passed, but only 2 of 3 held-out LS20 runs beat both frozen
nulls on both metrics. The tool domain passed 4 of 4 runs.

Phase 2b asks one confirmatory question:

> Does the exact Phase 2 v1 LS20 estimator beat its exact two frozen v1 nulls
> consistently on a larger set of independently seeded real LS20 rollouts?

The Phase 2 v1 bundle remains unchanged. Phase 2b will not pool, refit on, or
selectively compare against the v1 evaluation outcomes.

## 2. Frozen v1 inputs

The final freeze must fail closed unless every identity below matches:

| Input | Frozen identity |
|---|---|
| v1 internal manifest | `497acb5cbbea6f26afecfaf9c8f28d4bbd7cebba081e35d2f34d07ddef4facd2` |
| v1 manifest file | `6d1fb290b2a2c06c35cd709be71291b623a7ac241a6f009f7c50e5e2592a0304` |
| v1 train trace | `29b3f349d43f6ae29b3a8509d0513177198a38f5232346fae3e27b88e9f657ef` |
| v1 baseline bundle | `6e96fae900fa85a12ac638df6e33d652ae6398cc8648dd143d6934679097bc7a` |
| v1 baseline file | `4e0d2d39dfab75fcf68abe53ab97738eeaaa1653c6523aa95769e3f8e9cf780c` |
| v1 eval-freeze file | `5e14cce94743c74163170af42988cc7d5fb79abd93a2984e9bbb4d9673d130d0` |
| v1 report file | `0be026c1d5c834c9b4313c3d391ffb62936b98c2a23eb25d694657b15ebd9fdd` |
| LS20 tabular estimator | `dirichlet-tabular-v1:ls20:29b3f349d43f6ae2` |
| marginal null | `empirical-marginal-null-v1:ls20:29b3f349d43f6ae2` |
| action-shuffle null | `action-shuffle-null-v1:001b866749367806` |
| alpha | `1.0` |
| action-shuffle seed | `world-model-phase2-real-v1:ls20` |

Estimator policy is `reuse_exact_v1_frozen`. There is no Phase 2b training
split and no estimator refit. Reconstructing the same estimator from the
hash-bound v1 train trace is permitted only as a verifier cross-check; it may
not change the prediction commits or any fitted count.

## 3. Frozen environment

Phase 2b uses the same official local toolkit and game identity as v1:

| Component | Required value |
|---|---|
| operation mode | `OFFLINE` |
| `arc_agi` | version `0.9.8`, distribution SHA-256 `5332c0e7a71076577bfca080bfb72afca21cc23591cd95f29b9490f50faff153` |
| `arcengine` | version `0.9.3`, distribution SHA-256 `2feecf2979c5a7b1398f53696f17abb5fdaea21cba164228ac8278b3fb326b42` |
| LS20 game ID | `ls20-9607627b` |
| game file | SHA-256 `67cc85888eeef68f125cbb5f5fb158e9ca455d6bca46b171790f556fcabf934e` |
| game metadata | SHA-256 `b0c1518d6bb8542a59888dcdcd1469a3530da608d0a53dc746c73f13f1d0bf15` |
| state extractor | `ls20-avatar-mask-v1` |
| observation space | v1 five-label LS20 space, unchanged |
| action space | canonical `ACTION1` through `ACTION4`, unchanged |

Package, game, metadata, collector, scorer, trace-contract, baseline, and
capture code hashes must be recorded in the final pre-run artifact. Any
mismatch stops collection; it is not repaired by substituting a package or
silently refreshing the hash.

## 4. Independent rollout design

- Domain: LS20 only. The already-passing tool rows are not recollected.
- Inferential consistency unit: one complete run/episode/source group.
- Run count: 16.
- Planned steps per run: 48, unchanged from v1.
- Maximum transitions: 768.
- Every run uses a new environment seed, policy seed, run ID, episode ID,
  source-group ID, and journal.
- No v1 train or evaluation seed may recur.
- Forecasts are durably committed before their corresponding environment step.
- A terminal outcome ends that run and remains in the analysis.
- A run with fewer than 16 transitions remains in the 16-run denominator and is
  automatically non-positive, regardless of its metric deltas.
- More than four runs with fewer than 16 transitions triggers
  `NO_GO_LS20_INSUFFICIENT_EVIDENCE` as a mass-termination anomaly.
- A failed or short run is never replaced with a newly chosen seed. Crash recovery
  may resume the same hash-bound journal only.

Sixteen runs make the unchanged `0.75` consistency threshold resolve to
`12/16`, rather than the fragile `3/3` implied by only three runs. Under a
simple independent Bernoulli sensitivity calculation, the probability of
meeting `>=12/16` is `0.339` when the true positive-run probability is `2/3`
and `0.798` when it is `0.8`. These are design diagnostics, not a calibrated
hypothesis test and not inferential claims about LS20 independence.

## 5. Seed derivation and bound run identities

Seed namespace:

```text
mocop/openclaw/152/world-model-phase2b/497acb5cbbea6f26afecfaf9c8f28d4bbd7cebba081e35d2f34d07ddef4facd2
```

For label `environment` or `policy` and zero-based run index `i`:

```text
d = SHA256(namespace + "|" + label + "|" + format(i, "03d"))
seed = 100000 + int.from_bytes(d[0:8], "big") % (2147483647 - 100000)
```

The action list is 48 repeated `random.Random(policy_seed).choice(action_space)`
draws in Python 3.13. The final JSON freeze must contain each canonical action,
so execution does not depend on regenerating the PRNG stream. The hashes below
are SHA-256 over compact sorted-key JSON arrays of those canonical action
strings.

| Run suffix | Environment seed | Policy seed | Action-sequence SHA-256 |
|---:|---:|---:|---|
| 000 | 663853963 | 1120306188 | `7a34ddb5c8e25d951a240434c6115458289e5ceb07af9a165984d83ccf6c130d` |
| 001 | 342603561 | 1104629519 | `febac5748a23abe764e2c1ba3dd9c33f255aa5b3d95334ee4434a919c06ea553` |
| 002 | 1452481763 | 1592785511 | `91616910c509c1e42f149262064b7cac9b36971a4abf1b8de1eeb970932126dc` |
| 003 | 100230173 | 2114433152 | `2b3c8eaa402fff61dbc5400f5b14718add19a4f7a232895d146d6be9ee96c76c` |
| 004 | 1284496178 | 786784880 | `796b2be53327ebc4153de70a934d8956946101979c38318fc8af8e32ba96b6b4` |
| 005 | 680752213 | 1220568084 | `380b87f7d637e4c0c10bb92260a7497eb1011aeae11404c2b7260cfd9f5b9ba5` |
| 006 | 1903736118 | 531631310 | `9cc39de5931bb333e1de533e261abc4bb4ccbbd08b2b7f275dfdf4e55f6aa920` |
| 007 | 872584740 | 7032487 | `5ca4e7d50ed0a50989153e62c05e941357fb7ca1535acc1d688ed9c6d066da62` |
| 008 | 151858101 | 290213239 | `b4ce440019e88fbcfb04bfa2d5a7738752e12a333c2f99d0774e62165aa54a1a` |
| 009 | 616800855 | 44282696 | `3cb5c095bf6f9c0703892334926f88dc85c45278c8d9351bd4c24fe6cb41bd85` |
| 010 | 1177659801 | 1652426167 | `a451f0f7c83f7cdd69eca67cbad607e5dbe2e14f7b1413dd82ba1963dac4f51b` |
| 011 | 1304179695 | 2048896671 | `aa3fb1246744564c68dc15e1e7847a56800d09c90eeaaff3bd8f90c53e0ac2e4` |
| 012 | 1453866843 | 720493848 | `dbb42e4fa2222764ebab1909cd93a00e2751ef3cb3d0be5adf075346c8fb84ec` |
| 013 | 1723930695 | 1023268716 | `22fff563b777c6f64d442e775c578ca001b1e487b7e41d7dddb258524c3beca1` |
| 014 | 1390947184 | 875214149 | `9db3f5ced3088a2f3fd1809b1601778cc4e7cf5de29f7c6c0035521dc4218a1a` |
| 015 | 324471933 | 367951703 | `90678a0d1adbb25bb0b2ed5b0dc8293610dbad4fee3f035966b2a35c9d6af5c7` |

Run identities are `phase2b-ls20-eval-NNN`,
`episode:phase2b-ls20-eval-NNN`, and
`source-group:phase2b-ls20-eval-NNN`.

## 6. Analysis and decision rule

Metrics retain their v1 definitions:

- categorical NLL in nats, lower is better;
- class-summed multiclass Brier in `[0, 2]`, lower is better;
- positive deltas mean the frozen tabular estimator beats the named null.

Both transition-micro and unweighted run-macro deltas must satisfy, against
both the frozen empirical-marginal null and frozen action-shuffle null:

- NLL improvement `>= 0.02` nats;
- class-summed Brier improvement `>= 0.01`.

A run is positive only when it has at least 16 transitions and all four within-run
deltas are strictly greater than zero. At least 12 of 16 runs must be positive.

Support gates are:

| Gate | Frozen requirement |
|---|---:|
| v1 LS20 train transitions | `>= 192` |
| minimum v1 action count | `>= 8` |
| v1 state-action cells | `>= 4` |
| Phase 2b evaluation runs | `16` hash-bound runs present |
| Phase 2b evaluation transitions | `>= 512` |
| short-run anomaly gate | at most `4` runs with `< 16` transitions |

The `512` total is the v1 preregistered average minimum of 32 transitions per
run scaled to 16 runs. A short run is retained and automatically non-positive; it
does not kill the study unless more than four runs are short. All effect and
consistency thresholds remain unchanged from v1.

Decision precedence is:

1. Any custody, source, protocol, prediction-commit, or reproducibility failure:
   `INVALID_PROTOCOL` (no scientific decision).
2. Any support gate failure: `NO_GO_LS20_INSUFFICIENT_EVIDENCE`.
3. Support passes and every micro/macro delta against both nulls is non-positive:
   `NO_GO_LS20_PREDICTIVE_FAILURE`.
4. Micro and macro effect gates pass but fewer than 12 runs are positive:
   `NO_GO_LS20_RUN_INCONSISTENT`.
5. Any other effect-gate failure: `NO_GO_LS20_EFFECT_GATE_FAILED`.
6. All gates pass: `GO_LS20_CONSISTENCY_REPLICATED`.

The scoped GO confirms only the stated LS20 consistency claim. It does not by
itself convert v1's overall decision or authorize a downstream integration.

## 7. Freeze, review, and reporting contract

Before the first Phase 2b environment reset:

1. Isegrim's review must be captured durably with message ID and disposition.
2. Any accepted change must be incorporated while the study remains outcome-free.
3. A machine-readable preregistration and eval-freeze must bind the complete
   run specs, identities above, decision rule, exact v1 artifacts, environment
   provenance, and execution-code hashes.
4. Both JSON artifacts must be self-hashed, sidecar-hashed, published without
   overwrite, and posted to Watercooler/OpenCLAW `#152`.
5. The runner must refuse collection without the approved review attestation
   and exact preregistration/eval-freeze hashes.

After collection, the verifier must reproduce journal ordering, hash custody,
source continuity, action legality, pre-action prediction identity, labels,
scores, run buckets, and decision from the frozen artifacts. The report must
show every run, not only aggregate rows. Phase 2 v1 may appear as clearly
separate historical context but may not enter any Phase 2b metric or gate.

## 8. Reviewer disposition

Watercooler `#935` records Isegrim as primary reviewer of the superseded candidate
digest `df44982b90f239787957be728eee65f2d3e7fe7ee2e60a7a152ce6e4e112a4f5`:

1. Sixteen runs and the `>= 12/16` gate are accepted as the floor of adequate.
2. The terminal-run policy is amended exactly as specified above: short runs are
   automatic non-positives; more than four short runs fail support.
3. `GO_LS20_CONSISTENCY_REPLICATED` is cosigned as a condition-scoped result with
   no downstream authorization.

The reviewer pre-approved this amendment without a second review round and required
the amended document digest plus Watercooler message ID `935` in the final attestation.
