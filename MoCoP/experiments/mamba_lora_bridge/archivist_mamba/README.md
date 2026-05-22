# Archivist Mamba Prototype

Offline prototype for compiling messy agent/session logs into typed, provenance-preserving memory cases.

This is **not** live Alex/MoCoP memory and does not change runtime behavior.

## First target

1. Stream-parse raw logs without OOM.
2. Extract bounded candidate `MemoryCase` records.
3. Store cases as JSONL with evidence refs.
4. Retrieve cases with metadata filters.
5. Build eval fixtures before training any Mamba-style model.

## Safety rules

- Raw logs remain immutable and low-authority.
- Case records must include provenance.
- Domain boundaries matter: work, creative, personal, relationship, research, meta.
- Mamba, if trained, is a reranker/controller over cases, not a personality clone.
