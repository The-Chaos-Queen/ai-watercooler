# Archivist Mamba Implementation Plan

> **For Hermes/Codex/Claude:** Implement this as a small offline experiment first. Do not wire it into live Alex/MoCoP behavior until the deterministic compiler, case schema, and eval harness pass. GPU training belongs on Steve/ML-WS/Opa/rented GPU, not the laptop.

**Goal:** Build a local, provenance-preserving “Archivist Mamba” prototype that turns raw agent/chat logs into typed case records, retrieves relevant cases with metadata filters, and eventually trains a small Mamba-style model to reason over conditional memory cases.

**Architecture:** Start with a deterministic/offline case-memory compiler. Raw logs remain immutable and low-authority. The first useful product is a typed JSONL/SQLite case store plus markdown summaries and eval fixtures. Only after that works do we train a Mamba module as a memory controller/reranker over candidate cases, not as a user-facing chatbot.

**Tech Stack:** Python stdlib first, pytest, existing `Projects/Project_Prosthetic/recall.py`/Qdrant path where useful, JSONL/SQLite, markdown, later PyTorch + Hugging Face/`mamba-ssm` or `transformers` Mamba implementation on a GPU host.

---

## Non-goals

- Do **not** train a personality clone of Laura, Techno-Monk, Alex, or any assistant.
- Do **not** make raw logs high-authority memory.
- Do **not** upload private logs to hosted services.
- Do **not** require GPU training for v0.
- Do **not** integrate into live chat generation before offline evals exist.

## Authority model

Highest to lowest:

1. Current explicit Laura instruction.
2. Current project rules: `AGENTS.md`, `CHEESE_Memory/00_HAUSREGELN.md`, `CHEESE_Memory/00_BOOT_FILES.md`, `CLAUDE.md` if present.
3. Current handoff / Watercooler summary / active project state.
4. Curated compiled decisions/rules.
5. Extracted case records with provenance.
6. Raw logs and raw transcript snippets.

The Archivist may surface old raw evidence, but it must not silently override current curated rules.

## Target directory layout

Create under the existing Mamba bridge experiment:

```text
MoCoP/experiments/mamba_lora_bridge/archivist_mamba/
  README.md
  schemas.py
  log_parser.py
  case_extractor.py
  case_store.py
  retrieve_cases.py
  build_eval_fixtures.py
  train_mamba_reranker.py        # later phase; may initially be stub
  evaluate_archivist.py
  prompts/
    case_extraction_prompt.md
    rule_induction_prompt.md
  data/
    raw_index.jsonl              # paths + stats only, not copied raw logs
    cases.jsonl
    cases.sqlite                 # optional generated index
    markdown/
      sessions/
      cases/
      rules/
      decisions/
      failures/
    eval/
      memory_queries.jsonl
      gold_relevance.jsonl
      predictions.jsonl
  tests/
    fixtures/
      tiny_codex_rollout.jsonl
      tiny_mixed_domain.jsonl
    test_log_parser.py
    test_case_schema.py
    test_case_store.py
    test_retrieve_cases.py
    test_eval_metrics.py
```

---

## Case schema v0

Implement as dataclasses in `archivist_mamba/schemas.py` and serialize as JSONL.

```python
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Domain = Literal["work", "creative", "personal", "relationship", "research", "meta", "unknown"]
MemoryType = Literal[
    "case", "decision", "rule", "failure", "preference", "workflow",
    "reference", "fiction", "hypothesis", "open_question", "raw_summary"
]
Outcome = Literal["success", "failure", "partial", "unknown", "not_applicable"]
Authority = Literal["raw", "extracted", "curated", "canonical"]
Status = Literal["active", "superseded", "contested", "stale", "unknown"]

@dataclass
class EvidenceRef:
    source_path: str
    source_type: str = "unknown"          # codex_rollout, hermes_session, cheese_log, watercooler, etc.
    turn_start: int | None = None
    turn_end: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    quote: str = ""

@dataclass
class MemoryCase:
    id: str
    title: str
    domain: Domain
    memory_type: MemoryType
    outcome: Outcome
    authority: Authority = "extracted"
    status: Status = "active"
    agent: str = "unknown"                # codex, claude, hermes, techno-monk, alex, human, unknown
    project: str = "unknown"              # mocop, alex, house, fiction, etc.
    topics: list[str] = field(default_factory=list)
    summary: str = ""
    conditions: list[str] = field(default_factory=list)
    attempt: str = ""
    result: str = ""
    failure_modes: list[str] = field(default_factory=list)
    applies_when: list[str] = field(default_factory=list)
    does_not_apply_when: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    contradicted_by: list[str] = field(default_factory=list)
    confidence: float = 0.5
    event_date: str = ""
    extracted_at: str = ""
    evidence: list[EvidenceRef] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
```

Validation rules:

- `id`, `title`, `summary`, `domain`, `memory_type`, `outcome`, `authority`, `status`, `evidence` are required.
- `confidence` must be between `0.0` and `1.0`.
- Every case must have at least one `EvidenceRef`.
- A case with `memory_type="rule"` must include either `applies_when` or `does_not_apply_when`.
- A case with `status="superseded"` should include `supersedes` or a note in `result`.

---

## Phase 0: tiny deterministic foundation

### Task 0.1: Create package skeleton

**Objective:** Add the offline Archivist package without changing live behavior.

**Files:**
- Create: `MoCoP/experiments/mamba_lora_bridge/archivist_mamba/__init__.py`
- Create: `MoCoP/experiments/mamba_lora_bridge/archivist_mamba/README.md`
- Create directories listed above.

**Verification:**

```bash
python3 -m compileall MoCoP/experiments/mamba_lora_bridge/archivist_mamba
```

Expected: no syntax errors.

### Task 0.2: Add schema dataclasses and validation

**Objective:** Implement `MemoryCase`, `EvidenceRef`, and `validate_case`.

**Files:**
- Create: `archivist_mamba/schemas.py`
- Create: `archivist_mamba/tests/test_case_schema.py`

**Test cases:**

- valid case passes
- missing evidence fails
- confidence `<0` or `>1` fails
- rule with no scope fails

**Command:**

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 -m pytest archivist_mamba/tests/test_case_schema.py -q
```

### Task 0.3: Build tiny rollout fixture

**Objective:** Create a synthetic Codex JSONL fixture that mimics the real `.codex/sessions/.../rollout*.jsonl` shape without private data.

**Files:**
- Create: `archivist_mamba/tests/fixtures/tiny_codex_rollout.jsonl`

Fixture should include:

- one `session_meta`
- one user task message
- one assistant/tool-ish response
- one failure/error event
- one later correction/supersession message

**Verification:** fixture is <10 KB and contains no secrets.

### Task 0.4: Parse rollout JSONL into normalized events

**Objective:** Read Codex rollout JSONL without loading entire files into memory.

**Files:**
- Create: `archivist_mamba/log_parser.py`
- Create: `archivist_mamba/tests/test_log_parser.py`

**Implementation shape:**

```python
def iter_jsonl(path: str):
    ...

def iter_codex_events(path: str):
    """Yield normalized dicts: line_no, timestamp, event_type, role, text, raw_type."""
    ...
```

**Constraints:**

- streaming line-by-line
- tolerate malformed lines by yielding an error event, not crashing by default
- truncate huge text fields for previews but preserve line refs

**Command:**

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 -m pytest archivist_mamba/tests/test_log_parser.py -q
```

### Task 0.5: Index raw log paths, not raw contents

**Objective:** Build a manifest of known raw logs with size/date/path metadata.

**Files:**
- Create: `archivist_mamba/index_raw_logs.py`
- Output: `archivist_mamba/data/raw_index.jsonl`

**Default roots:**

```text
/mnt/c/Users/cerub/.codex/sessions
/home/isabell/.hermes/sessions
CHEESE_Memory/session_logs
MoCoP/experiments/mamba_lora_bridge/run_reincarnation
```

**Command:**

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 archivist_mamba/index_raw_logs.py --output archivist_mamba/data/raw_index.jsonl
```

Expected: writes manifest entries; does not copy logs.

---

## Phase 1: case extraction without model training

### Task 1.1: Deterministic heuristic case extractor

**Objective:** Extract crude candidate cases from parsed events using simple signals.

**Files:**
- Create: `archivist_mamba/case_extractor.py`
- Create: `archivist_mamba/tests/test_case_extractor.py`

**Heuristics v0:**

- user correction words: `actually`, `no`, `don't`, `do not`, `remember`, `we decided`, `last time`
- failure words: `error`, `failed`, `traceback`, `timeout`, `doesn't work`
- decision words: `decision`, `we will`, `use X`, `not X`, `current rule`
- domain hints:
  - `AGENTS`, `Codex`, `Claude`, `Hermes`, `Watercooler` → `meta`
  - `MoCoP`, `Alex`, `mamba`, `Qdrant` → `work`/`research`
  - `chapter`, `character`, `fiction`, `scene` → `creative`

**Verification:** synthetic fixture produces at least one `failure` and one `rule`/`correction` case.

### Task 1.2: Case store JSONL writer/reader

**Objective:** Store typed cases in append-friendly JSONL and read/filter them.

**Files:**
- Create: `archivist_mamba/case_store.py`
- Create: `archivist_mamba/tests/test_case_store.py`

**API:**

```python
def append_cases(path: str, cases: list[MemoryCase]) -> int: ...
def iter_cases(path: str): ...
def filter_cases(cases, *, domain=None, memory_type=None, agent=None, project=None, status=None): ...
```

**Verification:** roundtrip preserves evidence refs and metadata.

### Task 1.3: Markdown rendering for human review

**Objective:** Render each extracted case into readable markdown with provenance.

**Files:**
- Modify: `case_store.py` or create `markdown_render.py`
- Output: `archivist_mamba/data/markdown/cases/*.md`

**Markdown shape:**

```md
---
id: ...
domain: meta
memory_type: case
outcome: partial
status: active
confidence: 0.62
---

# Title

## Summary
...

## Conditions
- ...

## Outcome
...

## Evidence
- `/path/to/log.jsonl` lines 123-145
```

**Verification:** generated markdown contains no full raw transcript dump; only short quotes/refs.

### Task 1.4: Run extractor on one real Codex session in dry-run mode

**Objective:** Exercise the pipeline on the 710 MiB session without loading it whole.

**Input:**

```text
/mnt/c/Users/cerub/.codex/sessions/2026/03/22/rollout-2026-03-22T13-21-48-019d157e-8bef-7253-a467-aa0d8a8b64f2.jsonl
```

**Command:**

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 archivist_mamba/case_extractor.py \
  --input /mnt/c/Users/cerub/.codex/sessions/2026/03/22/rollout-2026-03-22T13-21-48-019d157e-8bef-7253-a467-aa0d8a8b64f2.jsonl \
  --output archivist_mamba/data/cases.jsonl \
  --markdown-dir archivist_mamba/data/markdown/cases \
  --max-cases 100 \
  --dry-run
```

**Acceptance:**

- process completes without OOM
- output is bounded by `--max-cases`
- markdown summaries are reviewable
- no live system behavior changes

---

## Phase 2: retrieval with metadata discipline

### Task 2.1: Implement local case retrieval CLI

**Objective:** Search extracted cases with filters before involving Qdrant/Mamba.

**Files:**
- Create: `archivist_mamba/retrieve_cases.py`
- Create: `archivist_mamba/tests/test_retrieve_cases.py`

**CLI:**

```bash
python3 archivist_mamba/retrieve_cases.py \
  "Codex over-searching old logs" \
  --cases archivist_mamba/data/cases.jsonl \
  --domain meta \
  --memory-type case --memory-type rule --memory-type failure \
  --agent codex \
  --status active \
  --limit 10
```

**Scoring v0:**

- lexical BM25-ish or simple token overlap
- boosts for matching filters
- boosts for `authority=curated|extracted` over `raw`
- penalty for `status=superseded|stale`

### Task 2.2: Add Qdrant metadata mapping design note

**Objective:** Define how cases should later be indexed into Qdrant.

**Files:**
- Create: `archivist_mamba/QDRANT_CASE_METADATA.md`

**Required payload fields:**

```yaml
domain
memory_type
outcome
authority
status
agent
project
topics
event_date
source_path
source_type
confidence
privacy
```

**Acceptance:** design note includes example upsert payload and filtered query examples.

### Task 2.3: Optional Qdrant export JSONL

**Objective:** Produce a JSONL suitable for a future Qdrant ingestion script without touching Qdrant yet.

**Files:**
- Create: `archivist_mamba/export_qdrant_payloads.py`

**Acceptance:** each output row has `id`, `text`, and `payload`.

---

## Phase 3: eval harness before training

### Task 3.1: Build gold memory-query fixture

**Objective:** Create a small human-reviewable eval set.

**Files:**
- Create: `archivist_mamba/data/eval/memory_queries.jsonl`
- Create: `archivist_mamba/data/eval/gold_relevance.jsonl`

**Starter queries:**

```jsonl
{"id":"q_codex_archaeology","query":"Should Codex search old logs before every complex task?","expected_domains":["meta"],"expected_memory_types":["rule","case","failure"]}
{"id":"q_authority_order","query":"What should override raw session logs?","expected_domains":["meta","work"],"expected_memory_types":["rule","decision"]}
{"id":"q_creative_boundary","query":"Is this a fiction preference or a stable user preference?","expected_domains":["creative","relationship"],"expected_memory_types":["case","preference"]}
```

### Task 3.2: Evaluate retriever quality

**Objective:** Score whether local retrieval gets the right cases before training Mamba.

**Files:**
- Create: `archivist_mamba/evaluate_archivist.py`
- Create: `archivist_mamba/tests/test_eval_metrics.py`

**Metrics:**

- recall@5 for gold case IDs
- domain accuracy
- stale/superseded false-positive count
- authority violation count

**Acceptance:** deterministic retrieval baseline has a visible score; this becomes the target to beat.

---

## Phase 4: supervised labels for Mamba

### Task 4.1: Generate candidate training rows from case retrieval

**Objective:** Convert queries + candidate cases into supervised reranking examples.

**Files:**
- Create: `archivist_mamba/build_eval_fixtures.py`
- Output: `archivist_mamba/data/eval/reranker_train_seed.jsonl`

**Training row shape:**

```json
{
  "query": "Should Codex search old logs before every complex task?",
  "candidate_cases": [
    {"id":"...", "summary":"...", "domain":"meta", "status":"active", "authority":"extracted"}
  ],
  "target": {
    "relevant_case_ids": ["..."],
    "active_rules": ["..."],
    "retrieve_more": false,
    "warnings": ["Do not generalize to self-contained tasks."]
  }
}
```

### Task 4.2: Manual review loop

**Objective:** Make weak labels reviewable by Laura/agent before training.

**Files:**
- Output markdown review packets in `archivist_mamba/data/eval/review_packets/*.md`

**Acceptance:** A human can mark:

- relevant / irrelevant
- active / stale / superseded
- correct scope / overgeneralized
- domain leak risk

---

## Phase 5: Archivist Mamba prototype

Do this only after Phases 0-4 are passing.

### Task 5.1: Pick model target

**Recommended first target:** train a small reranker/controller, not a generator.

Possible approaches:

1. **Encoder/reranker style:** Mamba consumes `query + case summaries` and predicts relevance labels.
2. **JSON controller style:** Mamba generates a small JSON policy over candidate cases.

Start with (1). It is easier to score and less likely to hallucinate.

### Task 5.2: Create training script stub

**Objective:** Add the script interface without requiring GPU locally.

**Files:**
- Create: `archivist_mamba/train_mamba_reranker.py`

**CLI:**

```bash
python3 archivist_mamba/train_mamba_reranker.py \
  --train archivist_mamba/data/eval/reranker_train_seed.jsonl \
  --output-dir archivist_mamba/runs/mamba_reranker_smoke \
  --dry-run
```

**Dry run acceptance:** validates dataset and prints estimated shapes; no model import required.

### Task 5.3: GPU-host training environment note

**Objective:** Document exact GPU training path for Steve/ML-WS/Opa.

**Files:**
- Create: `archivist_mamba/TRAINING_ENV.md`

**Must include:**

- do not run PyTorch/CUDA training on laptop
- `ssh ml-ws` note if using ML-WS alias
- expected Python env
- package install commands
- smoke command
- where model artifacts go

### Task 5.4: Mamba beats baseline gate

**Objective:** Only accept Mamba if it beats deterministic retrieval on held-out eval.

**Gate:**

- recall@5 improves or tie with lower stale false positives
- stale/superseded false positives decrease
- domain leak cases do not increase
- output includes uncertainty/scope, not universal rules

If it does not beat baseline, keep the deterministic case system and do not integrate Mamba.

---

## Phase 6: integration, default-off

### Task 6.1: Archivist query command

**Objective:** Provide one command agents can call when history matters.

**Desired interface:**

```bash
python3 MoCoP/experiments/mamba_lora_bridge/archivist_mamba/retrieve_cases.py \
  "<query>" \
  --domain meta --project mocop --limit 8 \
  --format agent-brief
```

**Agent brief format:**

```md
## Relevant historical cases

1. [case-id] Title — confidence/status
   Applies when: ...
   Does not apply when: ...
   Evidence: path:lines

## Active rule candidates
...

## Warnings
- This is stale/superseded/creative-domain/etc.
```

### Task 6.2: Optional `recall.py` filter extension

**Objective:** Extend `Projects/Project_Prosthetic/recall.py` to support richer filters only after case metadata is stable.

Candidate flags:

```bash
--domain meta --memory-type case --authority extracted --status active --agent codex --project mocop
```

**Acceptance:** Existing `--type`, `--tag`, and `--source-contains` behavior remains backwards-compatible.

### Task 6.3: Agent instruction update

**Objective:** Add a short rule to `AGENTS.md`/boot docs after the tool works.

Suggested wording:

```md
When Laura references prior work, old decisions, Techno-Monk/Alex/MoCoP history, or says "we already did this", query the Archivist/Qdrant case memory before answering. Use metadata filters. Do not search raw session logs first unless exact text is needed or the case index fails.
```

Do not add this until the command exists and has tests.

---

## Success criteria for v0

The project is useful before neural training if it can:

- stream-parse the 710 MiB Codex log without OOM
- extract bounded candidate cases with provenance
- separate work/creative/personal/relationship/research/meta domains
- preserve success/failure/partial outcomes and conditions
- retrieve relevant cases with filters
- flag stale/superseded/contested cases
- produce human-readable markdown summaries
- pass a small eval set better than raw grep/random transcript chunks

The Mamba phase is justified only if it improves:

- conditional applicability
- supersession detection
- domain separation
- stale-context avoidance
- retrieval planning

## First implementation checkpoint

Implement only Phases 0.1 through 1.2 first. Stop there and inspect outputs before touching the 710 MiB log.

**Checkpoint command set:**

```bash
cd MoCoP/experiments/mamba_lora_bridge
python3 -m pytest archivist_mamba/tests -q
python3 archivist_mamba/case_extractor.py \
  --input archivist_mamba/tests/fixtures/tiny_codex_rollout.jsonl \
  --output /tmp/archivist_cases.jsonl \
  --max-cases 20
python3 archivist_mamba/retrieve_cases.py \
  "Codex old logs" \
  --cases /tmp/archivist_cases.jsonl \
  --limit 5
```

If this tiny flow is not clean and boring, do not scale up.
