# Reasoning Scaffold

Path C v0 — probe-gated symbolic reasoning scaffold for Baby Qwen. Tests the first pieces of **teachability** without replacing the bridge backbone.

**Status:** spec drafted, awaiting pack review.

**Read first:** [`SPEC_V0.md`](SPEC_V0.md).

**Provenance:**
- Brainstorm: Laura + Dreizehn (active-inference inspired loop).
- Architecture review and v0 scoping: Scout (Path A/B/C decision, then v0 minimisation).
- Decision: keep the bridge (existing endocrine layer for disposition/continuity) and *layer* the reasoning scaffold on top. The two systems do different jobs and shouldn't compete.
- Review correction: v0 is not VFE minimisation and not yet general teachability. It is a narrow scaffold for German compound-word riddles. Teachability is only proven if correction improves later held-out related cases.

**What's here (planned):**

```
reasoning_scaffold/
├── SPEC_V0.md                     # Read this first
├── README.md                      # ← you are here
├── friction_probe.py              # Linear probe on Qwen hidden states
├── constraint_extractor.py        # Hand-coded rules for compound-word riddles
├── hypothesis_generator.py        # Lexicon enumeration + Qwen scoring
├── regeneration_loop.py           # Orchestration + explicit information-seeking heuristic
├── lesson_writer.py               # Qdrant integration via sleep_reconcile
├── morphological_lexicon/
│   ├── keks.yaml                  # ~80 -keks compounds
│   ├── mann.yaml                  # ~80 -mann compounds
│   ├── frau.yaml                  # ~80 -frau compounds
│   ├── wurst.yaml                 # ~60 -wurst compounds
│   ├── haus.yaml                  # ~120 -haus compounds
│   └── zeug.yaml                  # ~80 -zeug compounds
└── eval/
    ├── eval_scherzkeks.py         # Primary unit test
    ├── riddles_de_compound.json   # 50 curated riddles
    ├── factuals.json              # 20 sanity checks (should NOT engage)
    └── social.json                # 10 sanity checks (should NOT engage)
```

**Open for pack review.** Watercooler note posted; iterate before committing 2 weeks of build.

**Architecture target:** v0 = probe-gated symbolic scaffold for one domain; v0.5 = learned/assisted candidate generation and early-exit gating; v1 = latent candidate evaluation / broader learned fingerprints.
