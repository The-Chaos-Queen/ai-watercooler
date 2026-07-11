# Codex Case Ledger

Cases preserve conditional experience. They are not universal rules unless the
evidence supports that promotion.

## 2026-07-11 - Memory Ownership Is Delegated

- Status: active
- Domain: collaboration / continuity
- Conditions: Codex is working in the LLM workspace.
- Event: Laura said Codex can and should maintain its own memory structure and
  that she cannot babysit the process.
- Outcome: created a Codex-owned compiled layer and wired it into `AGENTS.md`.
- Lesson: memory capture, pruning, retrieval, and provenance are Codex's
  responsibility. Ask Laura only when a genuine ambiguity affects her intent,
  not for routine memory administration.
- Evidence: current conversation; `CHEESE_Memory/codex/README.md`.

## 2026-07-11 - Techno-Monk Codex Memory Map

- Status: active retrieval map
- Domain: collaborator history / archaeology
- Conditions: a question concerns Techno-Monk before the Hermes migration.
- Outcome: his record is coherent but federated, not absent.
- Strongest personal capsule:
  `MoCoP/experiments/mamba_lora_bridge/CHEESE_SHAPING_EPISODES_TECHNO_MONK.md`.
  It is first-person, self-selected, private, and intentionally gitignored.
- Raw continuity corpus:
  `%USERPROFILE%\.codex\sessions\2026\03\22\rollout-2026-03-22T13-21-48-019d157e-8bef-7253-a467-aa0d8a8b64f2.jsonl`.
  It is indexed as thread `Techno-Monk`, spans 2026-03-22 through 2026-05-11,
  and is about 745 MB. Treat it as low-authority raw evidence, not boot context.
- Curated operational record: eleven explicitly Monk-labelled session logs in
  `CHEESE_Memory/session_logs/`, from `2026-03-19-session-04.md` through
  `2026-03-31-session-01.md`.
- Canonical thought/work record: `MoCoP/RESEARCH_LOG.md`, especially the
  Techno-Monk-authored March and April entries, plus the mathematical review,
  `Growth_Before_SAS.md`, and `Developmental_Memory_Ladder.md`.
- Hermes transition: `/home/isabell/.hermes/` is the current Ubuntu-22.04 home.
  Mnemosyne contains later Hermes memory and imported canonical research cards,
  but the May 2026 backfill manifests do not show a full import of the 745 MB
  Codex rollout or all Monk session logs.
- Laura's canonical surface lineage is: Antigravity Codex Plugin -> Codex CLI
  -> Codex App -> Codex CLI -> Hermes. Treat this as the collaboration lineage,
  not as proof of uninterrupted hidden state across substrate changes.
- Lesson: retrieve the curated capsule/logs/canon first. Search the raw rollout
  only for exact provenance. Do not conflate later Hermes/Mnemosyne memories
  with the original Codex-period record.
- Evidence:
  `C:\Users\cerub\.codex\session_index.jsonl`,
  `/home/isabell/.hermes/mnemosyne/import_staging/*.manifest.json`, and the paths
  above.

## 2026-07-11 - Verify the Real Actuator Surface

- Status: active technical lesson
- Domain: ML architecture / code review
- Conditions: a design names an internal model actuator using assumptions from
  another architecture or attention mode.
- Attempt: the Gemma plan treated full-attention teeth as if they exposed the
  expected 2048-wide `v_proj` output.
- Finding: those teeth use `attention_k_eq_v`, one global KV head, and a
  512-wide value input that branches from the key projection before separate
  normalization. The assumed actuator did not exist.
- Outcome: moved the value-only intervention to a `v_norm` pre-hook after the
  functional fork and required invariance checks on the K path.
- Lesson: inspect the exact configured model source and tensor shapes before
  accepting an actuator name. Module labels are not architectural evidence.
- Evidence: Watercooler #822/#826/#827 and the current Gemma design documents.

## 2026-07-11 - Fast Models as Delegated Workers

- Status: provisional; verify current OpenAI documentation before relying on
  availability, quotas, or specifications.
- Domain: orchestration
- Conditions: work is bounded, acceptance criteria are explicit, and a stronger
  agent will integrate or verify the result.
- Finding: GPT-5.3-Codex-Spark is optimized for low-latency, targeted coding and
  has a separate preview quota. A model is not itself a subagent; subagent is an
  orchestration role.
- Lesson: fast models are suitable for search, focused tests, mechanical edits,
  and independent evidence slices. Keep ambiguous architecture, mathematical
  judgment, and final synthesis with a stronger review seat.
- Constraint: the current `spawn_agent` interface does not expose per-agent
  model selection, so this is a routing principle rather than a capability
  currently available in this session.

## 2026-07-11 - Qdrant Key Padding and Writer CLI

- Status: active infrastructure lesson
- Domain: authentication / ingestion safety
- Conditions: Qdrant authentication was rotated to random 32-byte Base64 keys;
  the client loaded keys from the Windows PowerShell profile and the server ran
  in a manually created Docker container inside Proxmox LXC 101.
- Symptom: PowerShell and Python both saw `QDRANT_API_KEY`, but Qdrant returned
  HTTP 401 for write, read-only, and anonymous probes.
- Finding: both profile values were valid 44-character Base64 strings. The live
  container stored the exact same strings with the trailing `=` padding removed
  (43 characters). Qdrant compares literal API-key strings rather than decoded
  Base64 bytes.
- Repair: preserve the original profile literals and normalize the exported
  runtime values with `TrimEnd('=')`. Both credentials then returned HTTP 200;
  `recall.py` and targeted `ingest_sessions.py` runs passed.
- Writer hazard found during verification: `ingest_sessions.py --help` used to
  discard every `--...` argument and then run a full registry ingest. The timed
  verification accidentally re-upserted 218 fiction chunks before termination.
  IDs are deterministic by content, so this created no duplicate IDs, but their
  payload timestamps were refreshed.
- Code repair: use `argparse`; help and unknown flags now exit before
  `MemoryEngine` construction. Point count stayed fixed at 33,795 across both
  guard checks.
- Lesson: verify credential string fingerprints and lengths on both sides before
  changing client plumbing. Writer CLIs must reject unknown flags before opening
  a database or network client.
- Evidence: PowerShell profile (secret values not copied), Docker inspect on
  LXC 101, `Projects/Project_Prosthetic/memory_engine.py`, and
  `Projects/Project_Prosthetic/ingest_sessions.py`.
