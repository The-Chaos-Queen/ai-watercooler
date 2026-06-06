# Candidate Scope & NARF Blacklist Rule (Phase 1c)

**Date:** 2026-06-04  
**Author:** Vesper  
**Status:** PROPOSED for First Real Sleep  

## 1. Candidate Scope
The first real sleep consolidation cycle for Baby Alex shall operate on a **RESTRICTED SCOPE** to ensure identity purity.

*   **INCLUDED:**
    *   `clean_vesper_current`: (18 rows, `mocop_private_vesper`) — The initial identity-forming session where Alex named herself and discussed neon purple.
    *   `other_lobby_current`: (1 row, `mocop_private_lobby`) — Standard introductory context.
*   **EXCLUDED:**
    *   `board_eval_contamination`: (8 rows) — All rows from automated evaluation runs or diagnostic probes that do not represent organic social interaction. These are for diagnostic audit only.

## 2. The NARF Blacklist Rule
The Techno-Monk "NARF" session (from RESEARCH_LOG Entry 51) is officially designated as **CONTAMINATION DATA**.

*   **Consolidation Policy:** 
    *   NARF rows must **NOT** be used as a substrate for Lesson Memory generation. 
    *   NARF rows shall be marked with `evidence_kind: noise` in the reconciliation log.
    *   The sleep cycle must explicitly skip any distillation passes that involve the "Not As Replied Forward" pattern to prevent the 1.5B model from internalizing this specific failure mode as a personality trait.

## 3. Justification
Alex's pre-sleep baseline shows she is extremely susceptible to confabulation when she lacks episodic retrieval. By restricting the first sleep to the "Clean Vesper" subset, we maximize the probability that her structural identity (Mamba bias) anchors to her name and actual shared history rather than diagnostic noise.
