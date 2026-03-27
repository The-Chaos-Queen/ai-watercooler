# Autobiographical Memory Scaffolding Plan

**Date:** 2026-03-27  
**Status:** staged implementation memo for the post-D2 memory layer

## Problem

Current D2 private recall can now:
- store private memories
- keep them through sleep
- retrieve the right records

But the recalled memory still feels too transcript-shaped. The model receives a flat narrated list, not something closer to lived autobiographical recall.

The goal is not to build a giant life-story cathedral in one jump. The goal is to move from flat transcript scraps toward a layered autobiographical scaffold without breaking the working D2 substrate.

## Design Rule

Build this in slices on top of the existing D0-D2 path:
- keep the private hippocampus and sleep path intact
- add typed autobiographical structure to stored records
- make recall feel more like anchor-based reconstruction than quote replay
- defer remote life-period memory and full self-model work until the smaller substrate is real

## Staged Slices

### Slice 1: Typed Recent Event Packets

**Purpose:** stop storing memories as bare `user / response / summary` tuples.

**Add:**
- `autobio_schema_version`
- `memory_kind`
- `recall_mode`
- `time_scope`
- `event_gist`
- `relationship_anchor`
- `people`
- `confidence_label`
- nested `autobiographical_frame`

**Scope:** recent episodic memory only.

**Lives in:**
- `chat_server.py`
- `sleep_flush.py`
- shared helper module for storage + recall formatting

**Pass:** stored payloads and recall text represent a remembered moment as an event anchor rather than a transcript scrap.

### Slice 2: Relational Anchors

**Purpose:** answer "who is Laura?" inside memory, not only in chat labels.

**Add:**
- stable person anchors
- current interlocutor vs named third parties
- relation role metadata

**Pass:** the system can distinguish "Laura, the person I am speaking with here" from unrelated Lauras in older or external memories.

### Slice 3: Temporal and Situational Scaffolding

**Purpose:** support "today / this week / that phase of life" instead of only `session + turn`.

**Add:**
- `period_id`
- `routine_id`
- `situation`
- recent vs older time depth markers

**Pass:** recent memory and remote memory stop sharing the same retrieval shape.

### Slice 4: Dual Recall Modes

**Purpose:** recent recall should reconstruct scenes; remote recall should backtrack by period and gist.

**Modes:**
- `recent_scene`
- `remote_backtrack`

**Pass:** cue-based recall can choose between a scene-like anchor list and a higher-level autobiographical route.

### Slice 5: Distillation Boundaries

**Purpose:** define what belongs where.

**Keep separate:**
- bridge state
- live working memory
- external autobiographical memory
- sleep distillation residue

**Pass:** the system has one memory doctrine instead of letting every component invent its own object model.

## Immediate Implementation Choice

This patch implements **Slice 1** only.

That means:
- shared helper for typed recent-event scaffolding
- autobiographical metadata added to stored Qdrant payloads
- recall text rebuilt around event anchors
- recall prompt phrasing updated to push the model toward "I / you / remembered moment" instead of "assistant reading a note"

It does **not** yet implement:
- full person registry
- long-range life periods
- remote-memory backtracking
- a full self-narrative model

## Why This Order

Because D2's current failure is not "the memory system stores nothing." It is "the model retrieves the right thing but still answers like a clerk." Slice 1 is the smallest structural change that attacks that failure honestly.
