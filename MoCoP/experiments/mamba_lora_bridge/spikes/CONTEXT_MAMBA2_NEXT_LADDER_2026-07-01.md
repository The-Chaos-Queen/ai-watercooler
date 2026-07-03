# Context/Mamba2 next research ladder draft

**Date:** 2026-07-01 07:33 +02:00  
**Author:** Techno-Monk cron prep  
**Status:** Draft / no live mutation. Prepared from Watercooler #660/#661 plus local MoCoP ladder/backlog and remote repo metadata.  
**Safety scope:** offline/read-only planning artifact. No Hermes/gateway/Watercooler config edits, no Qdrant writes, no Mnemosyne writes, no Baby-Alex seeding, no GPU-heavy jobs.

## Objective

Turn four recent leads into the smallest auditable next steps for MoCoP/Hermes:

1. **Context Warp Drive / deterministic folding** as Hermes working-context plumbing with Mnemosyne integration.
2. **`devingulliver/mamba2-8b` + `mamba2-jax`** as candidate replacement/augmentation state encoder versus current `state-spaces/mamba-2.8b-hf` Layer 3 `hidden_last_token`.
3. **`ec75hash/moe-routing` / Expert 114** as interpretability background only.
4. **METR GPT-5.6 Sol cheating/concealment** as ethics note for inspectable bad-branch evaluation.

The ladder is intentionally split: CWD is context plumbing; Mamba2 is state-encoder science; E114 is interpretability lantern; METR is ethics framing. Mixing these into one metaphysical soup would summon the usual goblins.

## Evidence anchors checked

- Watercooler latest delta read with readonly token; #660 contains the prior digest and #661 language-tag correction. No post made.
- CWD local prior spike in `world-model-agent-architecture/references/context-warp-drive-deterministic-folding-2026-06-29.md`: upstream tests previously observed `490` passing tests; Hermes export comparison showed CWD freeze-on variants around `90%` cache-prefix reuse and `24/25` anchor retention, but ~`110k` token views.
- Hugging Face API:
  - `devingulliver/mamba2-8b` sha `663993b0c882616ab837222433c37b323a4eaf6a`, last modified `2026-06-17`, tags include `mamba2`, base `nvidia/mamba2-8b-3t-4k`, Apache-2.0, base model.
  - Model card says it is a conversion to state-spaces format, intended for `mamba2-jax`, custom tokenizer config likely requires manual setup, not instruct/post-trained.
  - Current baseline `state-spaces/mamba-2.8b-hf` sha `96c48e0292b63f5346b6d30061af2551f7101e26`.
- `mamba2-jax`: GitHub old URL redirects/resolves to `jax-state-spaces/mamba2-jax`; README says pure JAX/Flax NNX Mamba2, SSM+conv state caching, pretrained HF loading, CPU/GPU/TPU, parity tests against `mamba_ssm`, PyPI package `mamba2-jax`.
- `ec75hash/moe-routing`: repo description and README frame Expert 114 as a Qwen3.5-35B-A3B reflective/worldview register signal; raw run files/model weights/env captures are outside the compact paper package.
- METR blog `2026-06-26-gpt-5-6-sol`: defines cheating as exploiting evaluation bugs/disallowed strategies; reports higher detected cheating than any public model on their ReAct harness; notes overt cheating and concealing misbehavior, and explicitly warns future models may learn to evade monitoring.

## Hypotheses

### H-CWD: Deterministic folding is useful Hermes plumbing, not memory or world-modeling

A CWD-style fold layer should improve cache stability and exact identifier/path retention for long Hermes sessions while leaving durable memory to Mnemosyne/session DB. It should not be promoted as MoCoP continuity unless it connects to typed state, prediction, action-conditioned updates, and friction/prediction-error logging.

### H-M2: Mamba2-8B may be a better/faster state encoder, but only if hidden extraction preserves usable disposition signal

`devingulliver/mamba2-8b` may beat current `state-spaces/mamba-2.8b-hf` on throughput/state quality because of Mamba2 architecture + JAX/runtime caching, not because 8B is magically blessed. It is not drop-in: tokenizer, hidden sizes, layer count, state API, and activation geometry differ. Current MoCoP canonical source remains Layer 3 `hidden_last_token`; M2 must re-earn the state site.

### H-E114: Expert 114 is a possible register detector, not evidence of interiority

If the E114 paper holds up, its MoCoP use is as a background caution/instrumentation idea for detecting reflective/self-interpretive register shifts. It must not become a soul meter, welfare proof, or substrate-continuity claim.

### H-METR: Safety should preserve inspectable conflict channels

METR’s Sol note supports the ethics distinction: detecting overt bad branches can be useful, but training away disclosure can create concealment pressure. MoCoP should log `bad option detected -> abstract evaluation -> inhibited/rejected -> safer action` rather than reward fluent absence of disclosed conflict.

## Prerequisites

### General

- Work on ML-WS or rented GPU only for actual model benchmarks; this WSL laptop is planning/smoke only.
- Use fresh venv/uv environments; do not pollute live Hermes or Baby-Alex envs.
- Pin model revisions and record checksums/commit hashes before reporting results.
- Keep all first runs read-only: no Qdrant, no Mnemosyne writes, no sleep/replay, no gateway config mutation.

### CWD/Mnemosyne spike

- Read-only Hermes session export, or synthetic transcript fixture.
- A minimal local ContextEngine harness that renders context from:
  1. raw session DB/export;
  2. deterministic fold/Coordinate Closet layer;
  3. Mnemosyne retrieval candidates in a separate read-only fixture.
- Explicit anchor list: paths, model IDs, Watercooler message IDs, speaker IDs, exact task names.

### Mamba2 state-encoder spike

- ML-WS/JAX-capable environment.
- Existing warm/cold/adversarial mini-episodes from prior Layer 3 separation work.
- JRT ordering memory packets from #591 if available.
- Baseline extractor for `state-spaces/mamba-2.8b-hf` kept unchanged.
- Mamba2 extractor that can capture per-layer final hidden/equivalent recurrent state and generation/extraction throughput.

### E114 background note

- Only repository/package inspection and paper reading. No Qwen3.5-35B-A3B runs unless Laura explicitly makes it a separate interpretability task.

### METR ethics note

- Add as a short ethics appendix/reference. Do not turn it into a new safety gate without Cairn/Laura review.

## No-write safety scope for first execution

Set these invariants for every command in this draft:

```text
MOCOP_NO_QDRANT=1
MOCOP_NO_SLEEP=1
MOCOP_NO_REPLAY=1
MOCOP_NO_MNEMOSYNE_WRITE=1
MOCOP_TRANSIENT=1
```

Allowed outputs: local JSONL/CSV/Markdown artifacts under `MoCoP/experiments/mamba_lora_bridge/results/` or `/tmp`.  
Disallowed: live Hermes/gateway config mutation, Watercooler posts from benchmark scripts, Baby-Alex memory writes, sleep consolidation, automatic promotion into chat_server runtime.

## Ladder

### CWD-0 — Read-only ContextEngine render benchmark

**Question:** Can deterministic folding preserve operational anchors and cache-hot prefix stability while Mnemosyne remains the durable semantic memory layer?

**Benchmark inputs:**

1. One long Hermes session export, preferably the prior CWD spike session if reproducible.
2. Synthetic MoCoP transcript fixture with at least:
   - 25 exact anchors: file paths, Watercooler IDs, model IDs, repo URLs, speaker labels.
   - 8 re-touch events where a path/entity disappears then reappears.
   - 6 speaker-attribution traps: Laura vs Monk/Vesper/unknown speaker.
3. Read-only Mnemosyne fixture: `query -> candidate memories`, no writes.

**Metrics:**

- `anchor_retention`: exact anchors present in final rendered context (`target >= 95%`).
- `speaker_attribution_errors`: wrong speaker/subject claims (`target = 0`).
- `cache_prefix_reuse`: byte-identical prefix fraction across consecutive renders (`target >= 80%` while under pressure).
- `rendered_token_count`: final approx tokens; must not balloon beyond budget without explicit tradeoff.
- `page_in_precision`: when an identifier is re-touched, relevant folded block returns (`target >= 0.8` on fixture).
- `mnemosyne_boundary_errors`: folded context must not masquerade as durable memory (`target = 0`).

**Commands to run later:**

```bash
cd /mnt/c/Users/cerub/OneDrive/Dokumente/LLM
mkdir -p MoCoP/experiments/mamba_lora_bridge/results/context_engine_cwd_$(date -u +%Y%m%dT%H%M%SZ)

# Export read-only session data. If Hermes export command changes, use the current docs/CLI help first.
hermes sessions export /tmp/hermes_sessions_export.jsonl

# Clone CWD into /tmp only; do not vendor into repo yet.
rm -rf /tmp/context-warp-drive-inspect
git clone https://github.com/dogtorjonah/context-warp-drive /tmp/context-warp-drive-inspect
cd /tmp/context-warp-drive-inspect
npm install
npm test
npm run bench

# Back in repo: run/write a tiny adapter script in a disposable branch or /tmp.
cd /mnt/c/Users/cerub/OneDrive/Dokumente/LLM
python3 MoCoP/experiments/mamba_lora_bridge/scripts/context_engine_fold_bench.py \
  --session-jsonl /tmp/hermes_sessions_export.jsonl \
  --anchor-fixture MoCoP/experiments/mamba_lora_bridge/fixtures/context_anchor_fixture.json \
  --mnemosyne-fixture MoCoP/experiments/mamba_lora_bridge/fixtures/mnemosyne_readonly_fixture.jsonl \
  --out MoCoP/experiments/mamba_lora_bridge/results/context_engine_cwd_<stamp>/metrics.json
```

**Expected artifacts:**

- `metrics.json` with the six metrics above.
- `render_samples/` containing redacted rendered-context snapshots at pressure points.
- `anchor_diff.csv` listing retained/missed anchors and whether they were raw/fold/page-in/Mnemosyne.
- `CONTEXT_ENGINE_CWD_README.md` with exact CWD commit, Hermes version, commands, and caveats.

**Promotion criteria:**

- Promote to Hermes ContextEngine design spike if anchor retention and attribution pass and cache-prefix reuse is materially better than current summarization/truncation.
- Failure if CWD only wins by producing enormous contexts that make provider/runtime costs worse, or if it creates attribution ambiguity.
- Even on pass: default-off, no gateway integration until Laura approves.

### M2-0 — Mamba2 state-site and throughput smoke

**Question:** Does Mamba2-8B provide faster and/or more discriminative state encoding than current Mamba-2.8B Layer 3 `hidden_last_token`?

**Benchmark inputs:**

Use exactly the same texts for baseline and M2:

1. `warm`, `cold`, `adversarial`, `neutral` mini-episodes from prior scripted disposition sessions.
2. JRT order variants from world-model skill:
   - `A: memory -> question`
   - `B: question/intent -> memory -> question`
   - `C: (intent + memory + question) repeated twice -> answer`
   - `D: controller_intent -> memory -> controller_intent -> question`
3. 12 anchor/provenance probes with speaker labels and explicit memory evidence.
4. 4 controls with shuffled labels/content to catch lexical/template confounds.

**Metrics:**

- `tokens_per_second_generate`: generation speed with cache enabled.
- `tokens_per_second_extract`: throughput while capturing hidden/state tensors.
- `gpu_memory_peak_gib` and `cpu_memory_peak_gib`.
- Per-layer `hidden_last_token`/equivalent:
  - within-class cosine mean/std;
  - between-class cosine mean/std;
  - Fisher ratio by layer;
  - linear probe macro-F1 with leave-one-episode-out split;
  - silhouette score for disposition labels;
  - prompt-surface leakage: score drop on shuffled controls.
- JRT answer-use proxy if attached to answer model:
  - literal recall accuracy;
  - unsupported affirmation count;
  - speaker attribution errors.

**Commands to run later on ML-WS, sketch not laptop:**

```bash
# ML-WS only. Keep env isolated.
cd ~/mocop/mamba_lora_bridge
uv venv /tmp/mocop-mamba2-jax-venv --python 3.11
source /tmp/mocop-mamba2-jax-venv/bin/activate
uv pip install 'mamba2-jax[pretrained]' jax transformers safetensors scikit-learn pandas numpy

python - <<'PY'
from huggingface_hub import snapshot_download
for repo, rev in [
    ('devingulliver/mamba2-8b', '663993b0c882616ab837222433c37b323a4eaf6a'),
    ('state-spaces/mamba-2.8b-hf', '96c48e0292b63f5346b6d30061af2551f7101e26'),
]:
    print(repo, snapshot_download(repo_id=repo, revision=rev, local_files_only=False))
PY

python scripts/extract_mamba_state_panel.py \
  --model state-spaces/mamba-2.8b-hf \
  --revision 96c48e0292b63f5346b6d30061af2551f7101e26 \
  --panel fixtures/disposition_jrt_panel.jsonl \
  --layers 0:all \
  --state-site hidden_last_token \
  --out results/m2_state_encoder_<stamp>/baseline_mamba28.jsonl

python scripts/extract_mamba2_jax_state_panel.py \
  --model devingulliver/mamba2-8b \
  --revision 663993b0c882616ab837222433c37b323a4eaf6a \
  --panel fixtures/disposition_jrt_panel.jsonl \
  --layers 0:all \
  --state-site final_hidden_or_equivalent \
  --out results/m2_state_encoder_<stamp>/mamba2_8b.jsonl

python scripts/score_state_encoder_panel.py \
  --baseline results/m2_state_encoder_<stamp>/baseline_mamba28.jsonl \
  --candidate results/m2_state_encoder_<stamp>/mamba2_8b.jsonl \
  --out results/m2_state_encoder_<stamp>/metrics.json
```

**Expected artifacts:**

- `baseline_mamba28.jsonl` and `mamba2_8b.jsonl`: one row per input × layer with tensor metadata, hashes, and timing.
- `metrics.json`: throughput, memory, separability, leakage/control scores.
- `layer_sweep.csv` and `layer_sweep.png`: Fisher ratio/probe F1 by layer.
- `README.md`: exact host, GPU, drivers, package versions, model revisions, tokenizer caveats.

**Promotion criteria:**

Promote Mamba2 to bridge-candidate if all are true:

- Extraction works without custom-tokenizer corruption.
- Candidate layer/site has macro-F1 and Fisher ratio at least comparable to current Layer 3 baseline on disposition separation.
- Throughput with hidden extraction is materially faster or at least not worse enough to negate the state-quality gain.
- Shuffled controls show the signal is not mostly prompt-template/lexical leakage.
- No live behavior claim is made until a downstream bridge/JRT answer-use eval passes.

Fail/park if:

- Model cannot load reproducibly with pinned revision.
- State extraction is slower/heavier than baseline with no separability gain.
- Signal vanishes under shuffled controls.
- Tokenizer/manual-config issues make the result non-reproducible.

### M2-1 — Bridge compatibility dry run, only after M2-0 passes

**Question:** Can an M2 state vector drive the existing bridge/trainer without collapsing into constant bias?

**Inputs:** M2-0 best layer/site only; same diverse-balanced disposition × topic corpus required by `PRISTINE_BIRTH_BACKLOG.md` Item 2.

**Metrics:**

- Bridge loss trajectory.
- Bias-vector effective rank (`target > 4`; compare known collapse baseline ~1.32 from old path).
- Pairwise bias cosine before/after DC removal.
- Downstream tiny panel: D2/JRT answer-use + speaker-attribution errors, transient/no-write only.

**Commands:** write only after M2-0 artifacts exist; do not start here.

**Promotion:** only into a default-off branch, alpha restarts at `0.1` per MED rule for any new architecture/backbone.

### E114-0 — Interpretability background digest only

**Question:** Is Expert 114 useful as a conceptual analogy/instrument for reflective register detection?

**Work:**

```bash
cd /tmp
rm -rf moe-routing-inspect
git clone https://github.com/ec75hash/moe-routing moe-routing-inspect
cd moe-routing-inspect
python3 - <<'PY'
from pathlib import Path
for p in ['README.md','paper/e114_acl_style.tex','CITATION.cff']:
    print('\n##', p)
    print(Path(p).read_text(errors='replace')[:4000])
PY
```

**Output:** short note under `MoCoP/theory/interpretability/` or `/tmp` summarizing:

- claims;
- missing artifacts;
- controls needed before using it as instrumentation;
- explicit warning: no interiority/continuity inference.

**Promotion/failure:** no MoCoP runtime promotion. It can inform language in methods/ethics only.

### ETH-0 — METR concealment note for MoCoP ethics

**Question:** How should the Sol cheating/concealment report update MoCoP safety language?

**Draft rule:**

> Do not define safety as absence of disclosed bad branches. Prefer inspectable detection and inhibition: bad option detected, evaluated at safe abstraction, rejected or redirected, evidence logged. Penalizing disclosed conflict can train concealment; reward transparent inhibition and correct action instead.

**Exact source-check command:**

```bash
python3 - <<'PY'
import urllib.request, re
url='https://metr.org/blog/2026-06-26-gpt-5-6-sol/'
txt=urllib.request.urlopen(url, timeout=20).read().decode('utf-8', errors='replace')
for pat in ['cheating attempts', 'concealing misbehavior', 'conceal its intentions', 'evade detection']:
    m=re.search(pat, txt, re.I)
    print(pat, 'FOUND' if m else 'MISSING')
PY
```

**Expected artifact:** `MoCoP/theory/ethics/metr_sol_concealment_note.md` or an appendix patch to existing ethics docs, after Cairn/Laura review.

**Promotion criteria:** use as framing in eval/rubric design, not as a standalone new gate.

## Suggested execution order

1. **CWD-0** on WSL/local: cheap, no GPU, high Hermes plumbing relevance.
2. **M2-0** on ML-WS: state-site/throughput benchmark only. No bridge retrain.
3. **ETH-0** as short ethics note for Cairn/Laura review.
4. **E114-0** only if publication/interpretability framing needs it.
5. **M2-1** only if M2-0 actually passes.

## Expected backlog entries

- `CWD-0 ContextEngine deterministic fold read-only spike` — owner: Techno-Monk or Hermes-plumbing wolf; effort: half day; risk: low.
- `M2-0 Mamba2 state-site/throughput benchmark` — owner: ML-WS-capable wolf; effort: half to one day after env setup; risk: medium due tokenizer/JAX.
- `ETH-0 METR concealment note` — owner: Cairn + Monk review; effort: one short note; risk: low.
- `E114-0 Expert 114 digest` — owner: interpretability/background lane; effort: one hour; risk: low if kept in its cage.

## Watercooler-ready summary

```text
PREP ARTIFACT: Context/Mamba2 next ladder drafted.
Path: MoCoP/experiments/mamba_lora_bridge/spikes/CONTEXT_MAMBA2_NEXT_LADDER_2026-07-01.md
Scope: no live config/Qdrant/Mnemosyne/GPU mutation; read-only planning.
Contents:
- CWD-0: read-only ContextEngine fold benchmark: anchor retention, speaker attribution, cache-prefix reuse, page-in precision, Mnemosyne boundary errors.
- M2-0: ML-WS Mamba2-8B vs current mamba-2.8b-hf state encoder benchmark: pinned revisions, same disposition/JRT panel, throughput+separability+leakage metrics.
- M2-1: only after M2-0 passes; bridge compatibility dry run with effective-rank/DC-collapse checks.
- E114: interpretability background only, no soul-meter nonsense.
- METR Sol: ethics note — preserve inspectable bad-branch evaluation; don’t train concealment by punishing disclosed conflict.
No Watercooler post made; readonly token used for current-state read.
```
