# Research Ingest Candidates

**Purpose:** a lightweight queue for interesting shards that deserve a shelf before they vanish.

Use this for:

- posts worth preserving
- architecture ideas worth checking
- model/runtime oddities
- papers or repos that probably matter but are not yet properly digested

Do not use this as a long essay file.  
Each item should be brief, status-marked, and easy to promote into a real note later.

---

## Queue

| Date | Item | Type | Why it matters | Next action | Status |
|---|---|---|---|---|---|
| 2026-04-05 | Karpathy personal knowledge bases workflow | post / workflow pattern | Names the `raw -> compiled wiki -> query` pattern cleanly; useful for the Research shelf | Keep as boundary + workflow note; no heavy implementation yet | parked |
| 2026-04-05 | HDBSCAN for sleep-time macro-memory consolidation | architecture idea | Promising offline clustering approach for scoped episodic memory without one global density threshold | Treat as sleep/exocortex experiment, not bridge replacement | documented |
| 2026-04-05 | batteryphil `mamba-2.8b-latent` / `mamba2backbonerecursion` | repo / runtime artifact | O(1)-VRAM latent loop reasoning on Mamba-2; relevant to local recurrent test-time compute | Keep archived as speculative runtime line; not canonical MoCoP path | archived |
| 2026-04-05 | batteryphil `mamba3-baremetal-rlf` | repo / oddity | Fresh custom bare-metal follow-on from the same line; interesting but not official Mamba-3 evidence | Link back to the latent reasoning line and do not unpark Mamba-3 on this basis | noted |
| 2026-04-05 | Amazon Mamba-2 / GDN / GKA hybrid artifacts | model family reality check | Real public hybrids may be useful for source geometry bake-offs or gate inspiration | Keep in artifact matrix; only escalate if runnable and relevant | active |

---

## Promotion rule

Promote an item out of this queue when one of these becomes true:

- it changes a live architectural decision
- it earns its own digest or comparison note
- it becomes an actual runnable experiment candidate
- it stops being a shard and becomes part of the map
