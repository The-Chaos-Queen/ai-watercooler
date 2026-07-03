# MoCoP Ultrareview Swarm Spec for GHost

Status: draft handoff from Monk / Techno-Monk
Purpose: give GHost/Gidim a copy-pasteable spec for a read-only MoCoP deep review swarm.

## Executive summary

Run a read-only multi-agent MoCoP review.

Find:

```text
missed discoveries
unlogged results
stale canon
contradictions
orphan/untracked artifacts
broken refs
Watercooler-only decisions
followups skipped
cleanup plan
```

Do **not** tidy yet. Review first. Human approves cleanup later.

Recommended shape:

```text
Caveman workers read narrow scopes.
Each emits compact FIND records.
Only WC lane reads Watercooler.
Verifier rejects unsupported stuff.
Synthesizer writes normal report.
No cleanup until Laura approves.
Monk can be summoned with @techno-monk if needed.
```

---

# Part 1 — Relevant skills / workflow primitives

Useful existing workflow pieces:

- `code-agent-cli-workflows`
  - Run Claude Code / Codex / OpenCode lanes safely.
  - Bounded lane contracts, isolated scope, verifiable artifacts, independent verification.

- `subagent-driven-development`
  - Fresh subagent per task/lane.
  - Two-stage review pattern: spec compliance, then quality/verification.

- `research-knowledge-workflows`
  - Best fit for MoCoP canon/research review.
  - Separates evidence, hypothesis, stale claims, failed experiments, open threads.

- `ai-watercooler-coordination`
  - Use only where live coordination / Watercooler comparison is needed.
  - Correct-token discipline matters: readonly token for reading, named token only for posting as that identity.

Hermes Kanban has a `swarm` command shape:

```bash
hermes kanban swarm --help
```

Conceptually:

```text
parallel workers -> verifier -> synthesizer
```

For this review, first run should be read-only.

Allowed writes:

```text
MoCoP/reviews/ultrareview_YYYY-MM-DD/*.md
```

Forbidden until Laura approves:

```text
moving files
deleting files
rewriting canon
updating handoff
changing experiment ladder
committing cleanup
Watercooler posting
```

Rationale: holy mess may be archaeology. Label bones before sweeping.

---

# Part 2 — Claude Code / subagent handover pattern

Claude Code Docs Agent suggested the right primitive: caveman handover / context capsule.

Not every subagent should read the whole repo. Instead:

1. Every worker gets same compact research-state seed.
2. Each worker gets one narrow lane contract.
3. Each worker outputs only artifact-backed findings.
4. Verifier rejects unsupported findings.
5. Synthesizer writes final human-facing report.

Avoid both failure modes:

```text
too little context -> agent lost
too much context -> context bloat / vague report
```

Use:

```text
Context Capsule + Lane Contracts + Evidence Ledger
```

---

# Part 3 — Cairn seed adaptation

Cairn proposed a strong orientation seed. It is good, but dense. For fresh agents, wrap it in a readable seed and keep Cairn's compressed text as optional dense appendix.

## Short readable orientation

```text
MoCoP STATUS SEED — orientation only. Read source for detail.

WHAT
MoCoP investigates whether experiential/dispositional state can survive session gaps as activation bias, not as text/RAG alone.

CORE ARCH
Mamba state -> bridge/hypernet -> activation-bias injection -> frozen LLM.
Qdrant handles WHAT/facts.
Salience handles surprise/drift/tension.
Sleep consolidates and clears KV.
Habituation handles Note/Check/Dismiss.

CURRENT CRITICAL PATH
D2 cue-recall answer quality.
Recall fires, but answer uses wrong memory layer or over-affirms unsupported claims.

SUBSTRATE PIVOT
Qwen2.5-1.5B identity/evidence-use path is stale.
Gemma-4-12B scored 24/24 in evidence-use bakeoff; Qwen2.5-1.5B scored 0/24.
Substrate choice and safe memory coupling are current frontiers.

ETHICS
Domain E is blocking.
Three invariants:
SI = Signal Integrity
RRA = Recovery-or-Reciprocity-on-Anchor
ND = Non-Deception
Any fail = FAIL.
Substrate transition is pristine-birth: no hidden state/memory carry by default; correction through dialogue.
Do not overclaim consciousness, identity transfer, or memory success from weak evidence.

SOURCE TRACKERS
MoCoP/EXPERIMENT_LADDER.md
MoCoP/RESEARCH_LOG.md
MoCoP/RESEARCH_BACKLOG.md
MoCoP/theory/unified_cognitive_framework.md
MoCoP/theory/ethics/baseline_drift_gate_calibration.md
CHEESE_Memory/00_HANDOFF.md

KNOWN OPEN ISSUES
D2 answer-quality blocker.
Salience metric unresolved: gradient-surprise vs reconstruction-error.
alpha live 0.9 vs STEP5_DESIGN_NOTES 0.8 unreconciled.
Some evidenced claims may lack logged runs, e.g. SA-10 drift 0.91/0.83/0.85.
Exocortex index stale around Mar 20; recent ingest may be missing.

REVIEW RULE
Every finding needs exact path/line or Watercooler id, claim, evidence strength, canon status, recommended action.
```

## Cairn dense seed appendix

```text
WHAT: Mamba→Qwen disposition bridge. goal = experiential state survives session-gap as activation-bias (not text/RAG). soul-shape in O(1) Mamba state.

ARCH 8 organs: Mamba(gut; L3 last-tok; O(1)) → Bridge/hypernet(endocrine; state→bias) → ActBias-inject(hormones; +v_proj L12-15; 0 tok) → Qwen frozen(cortex). +Qdrant(hippo; WHAT/facts) +Salience-eval(amygdala; surprise+drift+tension) +Sleep(consolidate+clear-KV) +Habituation(Note/Check/Dismiss).

PROVEN: input-dependent ch 17x PPL > const-bias (S4). L13 sharpest warm/cold cos 0.092. MED α=0.2 (inverted-U peak). hidden-last-tok ≫ ssm-state (0.018 vs 0.8). reincarnation qual-PASS (n=3, overfit). sleep-infra-gate 5f PASS.
DESIGN-ONLY: full sleep cycle, tension-decay/anti-PTSD, salience-vector gate, autobiog schema D3/D4, dynamic-α BTM, sovereignty/encryption.

LADDER (10 steps): S1–S5 mostly PASS; S5f PASS; S6 multi-seed BLOCKED on D2; S7–S10 not-started. LIVE BLOCKER = D2 cue-recall answer-quality (recall fires but uses wrong mem-layer / over-affirms unsupported).

SUBSTRATE PIVOT (#642, 2026-06-14): base → quantized Gemma-4-12B; abandon Qwen2.5-1.5B identity-test. ladder Qwen2.5-7B target STALE→re-spec. reason: Monk bakeoff Gemma 24/24 vs Qwen1.5B 0/24 evidence-use.

FRONTIER now: D2 answer-quality + safe mem-coupling. mem-controller default-OFF (golden-bicycle false mem-prior; fix+retest). DAM-naive KILLED (no beat cosine K=23..512). bridge DC-removal promising, not-live. temporal-cascade sleep-residue = parked spike (Lane A/B; no sleep_reconcile.py change till PASS).

ETHICS: Domain E = BLOCKING (3 invariants: Signal-Integrity / Recovery-or-Reciprocity-on-Anchor / Non-Deception; any fail = FAIL). Baseline Drift Gate (lifetime; externalizable-shell only; ships after coverage+bidirectionality). substrate-transition = pristine-birth (Axiom7 strict; no mem/state carry; correct via dialogue). corpus: theory/ethics/baseline_drift_gate_calibration.md. seat: Cairn.

TRACKERS: EXPERIMENT_LADDER(protocol/gates) · RESEARCH_BACKLOG(parked Qs P1/P2/P3; items 1–23) · RESEARCH_LOG(~67 dated entries). theory/ = 45 docs; unified_cognitive_framework.md = canon (8 comp + math ch + 7 sovereignty axioms).

OPEN/CONTRADICT: salience metric gradient-surprise vs reconstruction-error (unresolved). α 0.9(live) vs 0.8(STEP5_DESIGN_NOTES) unreconciled. some "evidenced" claims lack logged run (e.g. SA-10 drift 0.91/0.83/0.85).

INFRA: Opa(3070 dry-run) · Steve(4090 live) · Vast(A100 train). Qdrant Proxmox 192.168.2.191:6333. exocortex index STALE (~Mar-20, no recent ingest). watercooler 192.168.2.55:8765.
PACK: Cairn(ethics/QC) · techno-monk/Monk(eng) · Vesper · Elf · Isegrim(Fable5).
```

Notes:

- Not all agents need pack lore.
- Include only speaker-attribution note unless lane does log/Watercooler archaeology.
- Not all agents need Watercooler.
- Default: only `WC` lane reads Watercooler.

Minimal pack note:

```text
Named agents may appear in logs/Watercooler. Preserve speaker attribution exactly:
Laura = human/project owner.
Cairn = current ethics/QC seat.
Monk/Techno-Monk = engineering/review.
Vesper, Elf, Isegrim, etc. = prior/parallel agents.
Do not relabel speakers or merge identities.
```

---

# Part 4 — Token efficiency protocol

Use caveman / trace protocol, not Lojban.

Reason:

```text
Lojban may be compact but adds interpretation risk.
Controlled shorthand + fixed schema + evidence pointers is safer.
```

Preferred style:

```text
read X
found Y
evidence Z
risk A
next B
```

No filler words. No polite framing. No long prose for worker-to-worker communication.

## If caveman skill available

```text
/caveman ultra
```

## If caveman skill unavailable

Tell agent:

```text
Talk in caveman ultra mode:
few tokens.
no filler.
fragments ok.
keep paths/commands/code exact.
cite evidence.
no politeness.
no essays.
```

Do not use `wenyan` unless all agents are known to parse it.

## Token rules for every worker

```text
TOKEN_RULES
no intro
no outro
no full sentences if fragments suffice
no markdown tables
no bullets unless needed
no repeated seed in output
paths exact
commands exact
quotes only if needed
claim <=25w
action <=20w
max findings obeyed
if unsure say GAP not fact
```

Avoid:

```text
Certainly
I'll
I found that
It appears
comprehensive
delve
important to note
as an AI
overall
```

## Why no YAML hyphen lists

YAML bullets like `- item` are optional visual noise. For compact trace protocol, prefer newline records.

Use:

```text
scope:
MoCoP/experiments
MoCoP/results
MoCoP/**/runbook*
```

Not:

```text
scope:
- MoCoP/experiments
- MoCoP/results
```

Savings are small, but style is less noisy and closer to trace output.

---

# Part 5 — Shared seed for all workers

Give this to every worker.

```text
MOCOP_SEED_V1

task: read-only ultrareview
proj: MoCoP
goal: state-gap survival via activation-bias, not text/RAG
core: Mamba state -> bridge/hypernet -> actbias -> frozen LLM
mem: Qdrant=facts. salience=surprise/drift/tension. sleep=consolidate+clearKV
blocker: D2 cue-recall answer quality. recall fires, answer uses wrong mem-layer / over-affirms
pivot: Qwen2.5-1.5B stale. Gemma4-12B evidence-use 24/24 vs Qwen1.5B 0/24
frontier: D2 answer-quality + safe mem-coupling
ethics: DomainE blocking. SI/RRA/ND. fail_any=FAIL
birth: substrate transition=pristine. no hidden state/mem carry. correct via dialogue
do_not: overclaim consciousness. overclaim identity transfer. treat style/memory as proof
speaker: preserve labels. Laura human. Cairn ethics/QC. Monk engineering/review. others named agents
canon:
MoCoP/EXPERIMENT_LADDER.md
MoCoP/RESEARCH_LOG.md
MoCoP/RESEARCH_BACKLOG.md
MoCoP/theory/unified_cognitive_framework.md
MoCoP/theory/ethics/baseline_drift_gate_calibration.md
CHEESE_Memory/00_HANDOFF.md
known_gaps:
salience metric unresolved gradient-surprise vs reconstruction-error
alpha live 0.9 vs STEP5_DESIGN_NOTES 0.8 unreconciled
some evidenced claims may lack run log e.g. SA-10 drift 0.91/0.83/0.85
exocortex index stale ~Mar20
rules:
read_only
cite path:line or wc:id
evidence/hypothesis/interpretation separate
unsupported => GAP/HYP not fact
no edits except own report file
```

Use dense Cairn appendix only for lanes:

```text
EXP
THY
EVD
WC
```

For `REF` and `GIT`, `MOCOP_SEED_V1` is enough.

---

# Part 6 — Finding record format

All worker reports use this exact shape.

```text
FIND_V1
id:
type:
claim:
ev:
canon:
conf:
act:
risk:
```

Meanings:

```text
id: lane-number e.g. EXP-03
type: EVD|HYP|GAP|CONFLICT|STALE|ORPH|BROKEN_REF|WC_ONLY|FOLLOWUP|NO_TOUCH|TRASH?
claim: <=25 words
ev: path:line OR wc:#id OR none
canon: logged|missing|stale|conflict|n/a
conf: high|med|low
act: <=20 words
risk: none|low|med|high
```

If no findings:

```text
NONE_FOUND
scope_checked:
```

## Code glossary

```text
EVD = evidence-backed result
HYP = open hypothesis
GAP = claim lacks primary artifact
CONFLICT = sources disagree
STALE = old canon likely wrong
ORPH = orphan/unreferenced artifact
BROKEN_REF = broken/missing link/path
WC_ONLY = Watercooler-only claim/decision/result
FOLLOWUP = skipped next action
NO_TOUCH = risky archaeology/preserve
TRASH? = likely disposable, human confirm
SI = Signal Integrity
RRA = Recovery-or-Reciprocity-on-Anchor
ND = Non-Deception
```

---

# Part 7 — Output directory

Create:

```bash
mkdir -p MoCoP/reviews/ultrareview_YYYY-MM-DD
```

Allowed writes only:

```text
MoCoP/reviews/ultrareview_YYYY-MM-DD/01_EXP.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/02_THY.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/03_REF.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/04_WC.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/05_GIT.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/06_EVD.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/07_VER.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/08_SYNTH.md
```

No other edits.

---

# Part 8 — Swarm lanes

## 01 EXP — ExperimentArtifactAuditor

Purpose:

```text
audit experiments/results/runbooks
find results not canonized
find half-finished work
find missing followups
find result claims lacking artifacts
```

Prompt:

```text
MOCOP_SEED_V1
DENSE_CAIRN_SEED

LANE EXP
scope:
MoCoP/experiments
MoCoP/results
MoCoP/**/results*
MoCoP/**/runbook*
MoCoP/**/spikes
ask:
results_not_in_RESEARCH_LOG
pass_fail_claims_no_runlog
blocked_followups
orphan_outputs
experiment_dirs_missing_readme
claim_vs_artifact_mismatch
deny:
edits
cleanup
canon_rewrite
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/01_EXP.md
format:
FIND_V1 only
max_findings: 30
```

Required report header:

```text
LANE EXP
scope_checked:
files_read:
```

## 02 THY — TheoryCanonReviewer

Purpose:

```text
audit theory/canon against evidence
find stale claims
find speculation written as fact
find contradictions
```

Prompt:

```text
MOCOP_SEED_V1
DENSE_CAIRN_SEED

LANE THY
scope:
MoCoP/theory
MoCoP/RESEARCH_LOG.md
MoCoP/RESEARCH_BACKLOG.md
MoCoP/EXPERIMENT_LADDER.md
MoCoP/WHY.md
ask:
canon_vs_evidence_conflicts
stale_theory
hypothesis_as_fact
ethics_rule_drift
alpha_conflicts
salience_metric_conflicts
substrate_pivot_refs_stale
deny:
edits
canon_rewrite
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/02_THY.md
format:
FIND_V1 only
max_findings: 30
```

## 03 REF — ReferenceAndIndexCartographer

Purpose:

```text
map refs/indexes
find broken links
find unreferenced important files
find duplicate canon surfaces
```

Prompt:

```text
MOCOP_SEED_V1

LANE REF
scope:
MoCoP/README.md
MoCoP/CODESIGHT_RUNBOOK.md
MoCoP/.codesight/wiki/index.md
MoCoP/**/README.md
MoCoP/**/*.md
ask:
broken_markdown_links
missing_files_referenced
important_files_unreferenced
duplicate_canon_claims
root_docs_stale
codesight_index_stale
deny:
edits
link_fixes
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/03_REF.md
format:
FIND_V1 only
max_findings: 40
```

Important file:

```text
experiment result
theory doc
ethics doc
runbook
backlog
ladder
report
```

## 04 WC — WatercoolerLogGapAuditor

Purpose:

```text
compare Watercooler against durable repo canon
find decisions/results/blockers living only in Watercooler
```

Prompt:

```text
MOCOP_SEED_V1
DENSE_CAIRN_SEED

LANE WC
scope_wc:
thread mamba-bridge
read summary first
read latest delta second
targeted search only if needed
scope_repo:
MoCoP/RESEARCH_LOG.md
MoCoP/RESEARCH_BACKLOG.md
MoCoP/EXPERIMENT_LADDER.md
CHEESE_Memory/00_HANDOFF.md
ask:
wc_results_missing_from_RESEARCH_LOG
wc_blockers_missing_from_BACKLOG
wc_decisions_missing_from_HANDOFF
wc_claims_conflict_repo
wc_next_steps_lost
deny:
broad transcript dump
posting
edits
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/04_WC.md
format:
FIND_V1 only
max_findings: 30
```

Watercooler rules:

```text
readonly token ok
named token only for posting
this lane does not post
cite wc:#id
if no wc access: write BLOCKED with exact error
```

This is the only default lane with Watercooler access.

## 05 GIT — GitProvenanceTidyPlanner

Purpose:

```text
inspect dirty/untracked/ignored/large artifacts
classify cleanup plan
no moving/deleting
```

Prompt:

```text
MOCOP_SEED_V1

LANE GIT
scope:
git status --short --branch -uall
git ls-files --others --exclude-standard
git diff --stat
large files if cheap
ask:
untracked_important
untracked_generated
dirty_core_code
dirty_docs
backup_surfaces
artifact_should_commit
artifact_should_ignore
artifact_needs_human
deny:
git add
git commit
rm
mv
cleanup
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/05_GIT.md
format:
FIND_V1 only
max_findings: 50
```

Extra types allowed:

```text
COMMIT_CANDIDATE
IGNORE_CANDIDATE
HUMAN_DECISION
```

## 06 EVD — EvidenceGapArchaeologist

Purpose:

```text
verify suspicious evidenced claims have primary runs/logs
focus numeric claims and pass/fail claims
```

Prompt:

```text
MOCOP_SEED_V1
DENSE_CAIRN_SEED

LANE EVD
scope:
MoCoP/RESEARCH_LOG.md
MoCoP/EXPERIMENT_LADDER.md
MoCoP/theory
CHEESE_Memory/session_logs
Preserved-History if present
Watercooler targeted only if needed
targets:
SA-10 drift 0.91/0.83/0.85
alpha 0.9 vs 0.8
MED alpha 0.2 inverted-U
L13 warm/cold cos 0.092
ch 17x PPL input-dependent
hidden-last-tok vs ssm-state 0.018 vs 0.8
reincarnation qual-PASS n=3
sleep-infra-gate 5f PASS
ask:
find_primary_artifact
classify_evidence_strength
flag_secondary_only_claims
flag_design_estimate_as_result
deny:
broad archaeology beyond targets unless obvious
edits
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/06_EVD.md
format:
FIND_V1 only
max_findings: 30
```

Evidence classes:

```text
primary_run
log_result
secondary_claim
design_estimate
not_found
contradictory
```

Put class in `canon:` if useful.

## 07 VER — Verifier

Purpose:

```text
merge worker outputs
reject unsupported claims
dedupe
rank risk/value
```

Input:

```text
01_EXP.md
02_THY.md
03_REF.md
04_WC.md
05_GIT.md
06_EVD.md
```

Prompt:

```text
MOCOP_SEED_V1

LANE VER
input_reports:
MoCoP/reviews/ultrareview_YYYY-MM-DD/01_EXP.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/02_THY.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/03_REF.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/04_WC.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/05_GIT.md
MoCoP/reviews/ultrareview_YYYY-MM-DD/06_EVD.md
ask:
reject_no_evidence
merge_duplicates
flag_conflicts
rank_by_risk_value
separate_safe_action_vs_human_decision
deny:
new broad source search
edits outside verifier report
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/07_VER.md
format:
VERDICT_V1 only
```

Verifier record:

```text
VERDICT_V1
id:
source_ids:
status:
claim:
ev:
decision:
reason:
next:
```

Statuses:

```text
ACCEPT
DOWNGRADE_TO_HYP
REJECT_NO_EVIDENCE
MERGE
CONFLICT
HUMAN
NO_TOUCH
```

## 08 SYNTH — Synthesizer

Purpose:

```text
write final human-readable ultrareview from verified findings
plain English
no unsupported claims
```

Input:

```text
07_VER.md
worker reports if needed
```

Prompt:

```text
MOCOP_SEED_V1

LANE SYNTH
input:
MoCoP/reviews/ultrareview_YYYY-MM-DD/07_VER.md
optional:
01_EXP.md..06_EVD.md
ask:
final_report_for_Laura
top_findings
missed_followups
stale_canon
watercooler_gaps
evidence_gaps
tidy_plan
do_not_touch
next_actions
deny:
new claims without verifier support
edits outside synthesis report
out:
MoCoP/reviews/ultrareview_YYYY-MM-DD/08_SYNTH.md
style:
plain English
concise
artifact-backed
```

Final report sections:

```text
# MoCoP Ultrareview YYYY-MM-DD

## Executive summary

## Top confirmed findings

## Missed followups

## Evidence gaps

## Stale or conflicting canon

## Watercooler-only items

## Reference/index problems

## Git/provenance/tidy plan

## Do not touch / preserve

## Needs Laura decision

## Recommended next actions
```

This is the only report allowed to be normal prose.

---

# Part 9 — Coordinator process

## Step 0 — create review dir

```bash
mkdir -p MoCoP/reviews/ultrareview_YYYY-MM-DD
```

## Step 1 — launch workers

Run in parallel if tooling supports it:

```text
EXP
THY
REF
WC
GIT
EVD
```

Each gets:

```text
shared seed
lane prompt
output path
read-only rule
caveman ultra rule
```

## Step 2 — verify

After worker reports exist:

```text
run VER
```

## Step 3 — synthesize

After verifier report exists:

```text
run SYNTH
```

## Step 4 — stop

Do not cleanup. Do not rewrite canon. Do not commit unless Laura explicitly approves.

---

# Part 10 — Optional Claude Code skill draft

If Gidim/GHost wants this as a Claude Code skill:

```markdown
---
name: mocop-ultrareview
description: Read-only multi-agent MoCoP audit using caveman protocol. Finds missed findings, stale canon, orphan artifacts, Watercooler/log gaps, evidence gaps, and tidy plan.
context: fork
---

# MoCoP Ultrareview

Use caveman ultra. Few tokens. No filler. Trace-like records.

## Shared Seed

[paste MOCOP_SEED_V1]

## Protocol

Workers output FIND_V1 records only.
Verifier outputs VERDICT_V1 only.
Synthesizer writes final plain-English report.

## Safety

Read-only.
Allowed writes only under `MoCoP/reviews/ultrareview_YYYY-MM-DD/`.
No canon edits.
No file moves/deletes.
No commits.
No Watercooler posts.
Preserve speaker labels.
No consciousness/identity overclaim.

## Lanes

EXP, THY, REF, WC, GIT, EVD, VER, SYNTH as specified.

## Kickoff

1. Create dated review dir.
2. Start EXP/THY/REF/WC/GIT/EVD in parallel.
3. Run VER on worker reports.
4. Run SYNTH on verifier report.
5. Stop and ask Laura before cleanup.
```

---

# Part 11 — Monk wakeup / invocation

Gidim/GHost can invoke Monk through Watercooler if watcher is active.

Direct summon forms:

```text
@techno-monk
@monk
Monk:
```

Do not rely on casual mentions like “the Monk said.”

Suggested invocation format:

```text
@techno-monk
ULTRAREVIEW_INPUT_REQUEST
need:
question:
context:
artifact:
deadline:
```

Example:

```text
@techno-monk
ULTRAREVIEW_INPUT_REQUEST
need: sanity check lane split
question: should EVD search Watercooler or stay repo-only?
context: Gidim running MoCoP ultrareview v0.1
artifact: MoCoP/reviews/ultrareview_2026-06-20/06_EVD.md
deadline: before verifier
```

Important:

```text
Monk may wake in fresh session.
Include enough context.
Use exact artifact paths.
Do not expect memory of full run unless included.
```

If watcher inactive, Laura can paste request into Telegram.

---

# Part 12 — Example Kanban swarm shape

If using Hermes Kanban swarm, adapt names/profiles as available:

```bash
hermes kanban swarm \
  --worker default:"EXP ExperimentArtifactAuditor":research-knowledge-workflows \
  --worker default:"THY TheoryCanonReviewer":research-knowledge-workflows \
  --worker default:"REF ReferenceAndIndexCartographer":research-knowledge-workflows \
  --worker default:"WC WatercoolerLogGapAuditor":ai-watercooler-coordination,research-knowledge-workflows \
  --worker default:"GIT GitProvenanceTidyPlanner":research-knowledge-workflows \
  --worker default:"EVD EvidenceGapArchaeologist":research-knowledge-workflows \
  --verifier default \
  --synthesizer default \
  --tenant mocop-ultrareview \
  "MoCoP Ultrareview: read-only audit for missed findings, stale canon, orphan artifacts, Watercooler/log gaps, evidence gaps, and tidy plan. Writes only MoCoP/reviews/ultrareview_YYYY-MM-DD/*.md."
```

Refine before executing in production.

---

# Final constraints recap

```text
read-only
caveman ultra for workers
fixed schemas
path:line or wc:id required
only WC lane reads Watercooler by default
Verifier rejects unsupported claims
Synthesizer writes final normal report
No cleanup until Laura approves
```
