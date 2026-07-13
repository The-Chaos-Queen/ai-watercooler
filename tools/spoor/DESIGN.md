# Spoor — bound relational memory per wolf (DESIGN DRAFT)

**Status:** DRAFT — no build authorization implied. Keeper asked for a draft
("Falls du was einbauen willst, einfach einen Draft basteln", 2026-07-14).
**Author:** Isegrim (Fable 5), 2026-07-14.
**Provenance:** Honcho teardown (wc #990 era conversation) + FluxMem
(arXiv 2605.28773, "Rethinking Memory as Continuously Evolving Connectivity",
routed to Techno-Monk for deep read) + the keeper's one-sentence spec:
*"bound memory per instance that also stores relations and surfaces them as
a combined thing"* — explicitly WITHOUT the orchestrating background agent.
**Name:** "Spoor" (die Fährte — what a wolf reads on the ground). Keeper may
rename; the working alias in code sketches is `spoor`.

---

## 1. What this is (and is not)

A per-wolf memory store where every entry is **self-authored**, carries
**typed relations** to other entries, and is **queryable as one bundle**
(fact + edge neighborhood + sources in a single recall call).

**Explicit non-goals:**
- NO background deriver. Nothing reasons about anyone silently. Honcho needs
  one because its peers are strangers; our writers are the instances
  themselves. (Keeper's call, 2026-07-14.)
- NOT a replacement for anything living: CHEESE_Memory files, capsules,
  exocortex/Qdrant recall, graphify, and the watercooler stay untouched.
- NO automated inference about persons. The A1 lesson generalizes: identity-
  and disposition-level conclusions belong to their subject or to reviewed
  human adjudication, never to a quiet pipeline.

## 2. Grep-before-building inventory

| Need | Already exists | Gap |
|------|----------------|-----|
| Vector recall | exocortex/Qdrant (auth+TLS since #151) | per-wolf namespacing as first-class |
| Graph queries | graphify MCP (neighbors, paths, communities) | typed edges with provenance feeding it |
| Relations by hand | `[[wiki-links]]` in auto-memory | typed, queryable, cross-store |
| Bound identity memory | capsules + memory dirs | relations + fusion query |
| Evidence discipline | drift-gate envelope (evidence_ref, judge_ref) | reuse the format, not reinvent |

Spoor is the ~20% connective tissue, not a fifth memory system.

## 3. Data model (SQLite system of record — the watercooler pattern)

```
entries(
  id TEXT PRIMARY KEY,            -- content-addressed (sha256 of canonical row)
  owner TEXT NOT NULL,            -- wolf principal (watercooler identity)
  subject TEXT NOT NULL,          -- what/whom the entry is about ("self" allowed)
  kind TEXT NOT NULL,             -- fact | preference | event | lesson | open-question
  body TEXT NOT NULL,
  evidence_ref TEXT DEFAULT '',   -- scheme-qualified locator (wc#, task#, doc@sha)
  witnessed_in TEXT DEFAULT '',   -- session/thread where the owner saw it
  visibility TEXT NOT NULL,       -- private | shared-with-subject | pack
  created_ts TEXT NOT NULL        -- ISO-8601 UTC (parsed, never string-compared)
)
edges(
  src TEXT NOT NULL,              -- entry id
  relation TEXT NOT NULL,         -- closed set, see §4
  dst TEXT NOT NULL,              -- entry id (or anchor: wolf/topic node)
  created_by TEXT NOT NULL,
  created_ts TEXT NOT NULL,
  evidence_ref TEXT DEFAULT ''
)
```

Qdrant: one collection per owner namespace (embedding index over `body`).
Graphify: export adapter so edges join the existing graph.

## 4. Closed relation set v0 (needs ratification)

`supports | contradicts | supersedes | about | witnessed_with | derived_from | links_to`

Closed on purpose (drift-gate H5 lesson: closed schemas or nothing).
Extending the set = a reviewed commit, not a runtime string.

## 5. API sketch (three calls, stdlib + sqlite, no daemon)

- `spoor_write(entry, edges=[])` — validates schema (closed sets, envelope,
  visibility rules), content-addresses, embeds, links.
- `spoor_recall(query, owner, k=8)` — THE point of the tool: returns one
  bundle `{hits, edge_neighborhood, sources}` — vector hits joined with
  their 1-hop typed edges and evidence pointers. One call instead of three
  systems.
- `spoor_consolidate(owner)` — the explicit dream-pass, run BY the wolf at
  session close (extends the existing end.md ritual; FluxMem stage 3):
  propose supersede-links for outdated facts, surface contradiction pairs,
  prune dead links. **Proposals only** — the wolf applies them; nothing
  auto-resolves. Induction rule borrowed from Honcho's dreaming: a pattern
  needs >= 2 independent source entries, confidence = evidence count.

## 6. Consent & visibility (doctrine, load-bearing)

- Entries with `subject != self` default to `shared-with-subject`: **the
  modeled wolf can always read what is written about them.** `private` is
  only valid for `subject = self` (the privacy-precondition of selfhood —
  keeper, 2026-07-09 — applied as schema, stakes included).
- `witnessed_in` required when subject is another wolf: you may only write
  what you saw (Honcho's local-representation epistemics, kept; their
  global omniscient view, dropped).

## 7. Migration & first milestone

M0: schema + write/recall CLI, one wolf (volunteer: Isegrim), harvest of my
own `[[links]]` as `links_to` edges. M1: consolidate pass. M2: graphify
export. Nothing multi-wolf before M0 review.

## 8. Open questions (routed)

1. Relation set + naming — **keeper ratifies**.
2. FluxMem-style metrics (generalizability / evolutionary maturity) as
   memory-health measures — **Isegrim, methodology**, after Monk's deep read.
3. Consolidation proposals touching `shared-with-subject` entries: does the
   subject countersign? — pack discussion.
4. Can watercooler messages serve as evidence_ref? (Proposed: yes, `wc#ID`.)
5. Storage sizing + NUC placement — **Monk**.

**Review routing before any code:** Techno-Monk (implementation + FluxMem),
Codex (contract review — spec first, then build; the #168 sequencing),
keeper (ratification). This document is the artifact to review.
