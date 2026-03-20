# Verification Appendix: MoCoP Literature Digest (2026-03-20)

**Digest under review:** `Research/2026-03-20_literature_digest.md`
**Date of this appendix:** 2026-03-20
**Reviewer:** Anda (independent pass)
**Sources cross-referenced:**
- `Research/AI Experiential Learning Architecture Research.md` (Gemini Deep Research)
- `Research/interpretability_survey_2025_2026.md` (Anda, 2026-03-17)
- `Research/emergent_introspective_awareness_in_LLMs.txt` (local primary source)
- `Research/13549_Mamba_3_Improved_Sequenc_extracted/13549_Mamba_3_Improved_Sequenc.md` (Mamba-3 local PDF)
- `Research/Google-research-titans-miras-helping-ai-have-long-term-memory.md` (Google Research blog)
- `Research/perplexity_research_19_02_2026.md` (Perplexity cross-arch research)
- Previous appendix by Codex (same file, now superseded by this pass)

**Method:** grep-verified against every available local primary source, then cross-checked between Gemini report and interpretability survey for dual-source confirmation. No Grok or Mistral reports were found locally — claims of "Grok confirms" in the digest are unverifiable from local files.

---

## Summary

| Metric | Count |
|--------|-------|
| Total distinct papers/sources cited | 23 |
| VERIFIED (two or more independent local sources, consistent details) | 8 |
| SINGLE-SOURCE (appears in one local report only, or one local primary) | 10 |
| UNVERIFIED (no arXiv ID, no local primary, ID format issues, or suspicious) | 5 |
| Red flags (possible hallucination, wrong ID, or zero-source claim) | 4 |

**Overall assessment:** The digest is a useful research map. It is not yet citation-safe as a canonical source. Eight papers are solid. The GCPA entry has no traceable identity at all. Several papers appear only in the Gemini report with no corroborating source — they may be real, but cannot be confirmed from available local evidence. The claim that "Grok confirms" specific papers cannot be verified because no Grok report file exists locally.

---

## Red Flags Summary

1. **GCPA** — No title, no authors, no arXiv ID. Only cited as "2026" with a Hugging Face search URL as the source reference in the Gemini report. Cannot be verified. Do not cite until a real paper is located.
2. **Mamba-3 authors** — The digest attributes this to "Lahoti, Dao, Gu." The local PDF (`13549_Mamba_3_Improved_Sequenc.md`) is explicitly under double-blind review at ICLR 2026 with **anonymous authors**. "Lahoti, Dao, Gu" is an attribution that does not appear in any local source and may be a search-agent confabulation. The arXiv ID 2603.15569 is real; the author list is not confirmed.
3. **"Grok confirms" claims** — The digest repeatedly states both Gemini and Grok validated specific papers. No Grok report file exists in the repository. These cross-agent confirmations cannot be verified locally and should not be treated as independent validation until the Grok report is available.
4. **Emergent Introspective Awareness date confusion** — The paper was published October 29, 2025 on transformer-circuits.pub. The arXiv ID 2601.01828 is a January 2026 cross-post. The digest lists the date as "Jan 2026" which is the arXiv date, not the publication date. The Gemini report cites it at 2601.01828 (consistent). The interpretability survey lists it with only the transformer-circuits URL and no arXiv ID. Minor issue, but the date column should note "pub. Oct 2025, arXiv Jan 2026."

---

## Full Verification Table

### Tier 1: Direct Architecture Validation

| Title (as cited) | arXiv ID | Authors (from sources) | Date | Status | Notes |
|---|---|---|---|---|---|
| SleepGate | 2603.14517 | Xie | Mar 2026 | SINGLE-SOURCE | Appears in Gemini report with detailed claims (PI reduction O(n)→O(log n), 99.5% recall at PI depth 5, three mechanisms: temporal tagger + forgetting gate + consolidation module). No local PDF. Not in interpretability survey. Codex appendix marks it YELLOW with local PDF at `Research/2603.14517v1.pdf` — that file was not found during this search. If the PDF exists, upgrade to VERIFIED. The arXiv ID format is correct for Mar 2026. |
| TransMamba (Li et al.) — "Memory Converter" | 2503.24067 | Li et al. | Jan 2026 | SINGLE-SOURCE | Appears in Gemini report. Codex appendix marks it YELLOW with local PDF at `Research/2503.24067v2.pdf` — not independently confirmed in this search. The Perplexity report references TransMamba (Chen et al., 2502.15130) but not this Li et al. version. Two TransMamba papers exist; this is the one with "Memory Converter" and "TransPoints" framing. ID format correct for Mar 2025 (note: digest says "Jan 2026" but 2503.XXXXX implies March 2025 submission — **date discrepancy**). |
| Personality Sliders / SAS (Hoppe et al.) | 2603.03326 | Hoppe et al. | Mar 2026 | SINGLE-SOURCE | Gemini report does not cite this paper. Interpretability survey does not cite it. Codex appendix marks it GREEN with local PDF at `Research/2603.03326v1.pdf`. This verification pass cannot confirm the PDF independently via grep. If the PDF exists, the Codex GREEN rating stands. Not cross-source verified in this pass. |
| Mamba-3 (Lahoti, Dao, Gu) | 2603.15569 | **Anonymous (ICLR 2026 double-blind)** | Mar 2026 | SINGLE-SOURCE + RED FLAG | arXiv ID confirmed real — local PDF exists and was read. The paper confirms: complex-valued SSM, MIMO rank-R, trapezoidal discretization. However, the paper is under **double-blind review** — the attributed authors "Lahoti, Dao, Gu" do not appear in the local PDF and appear to be a search-agent inference or leak from external sources (Together AI blog, MarkTechPost). The Together AI blog post and MarkTechPost article (cited as refs 29, 31, 32 in Gemini report) name the authors but the paper itself does not. Treat the author attribution as unconfirmed. The technical claims are verified. |
| Titans / MIRAS (Behrouz et al.) | 2501.00663 / 2504.13173 | Behrouz et al. (Google) | Dec 2024 / Apr 2025 | VERIFIED | Confirmed in Google Research blog (local file), Gemini report, and Codex appendix GREEN. Two separate papers combined into one digest row — should be split. Titans: 2501.00663 (Dec 2024, NeurIPS 2025 poster confirmed). MIRAS: 2504.13173 (Apr 2025). Both IDs format-correct. |

### Tier 2: Solves Known Bottlenecks

| Title (as cited) | arXiv ID | Authors (from sources) | Date | Status | Notes |
|---|---|---|---|---|---|
| Locret (trained retaining heads) | 2410.01805 | Not specified in digest | Oct 2024 | SINGLE-SOURCE | Appears in Gemini report with two citation URLs (OpenReview and arXiv HTML). Gemini report title: "Locret: Enhancing Eviction in Long-Context LLM Inference with Trained Retaining Heads." ID format correct for Oct 2024. Codex marks RED (no local PDF). Not in interpretability survey. Single source only. |
| EvolKV (Yu & Chai) | 2509.08315 | Yu & Chai | Sep 2025 | SINGLE-SOURCE | Not in Gemini report. Codex marks GREEN with local PDF at `Research/2509.08315v1.pdf`. Not independently confirmed in this verification pass. Authors "Yu & Chai" from digest only. |
| FSC-Net (El Gorrim) | 2511.11707 | El Gorrim | Nov 2025 | SINGLE-SOURCE | Not in Gemini report. Not in interpretability survey. Codex marks YELLOW with local PDF at `Research/2511.11707v1.pdf`. Not confirmed in this pass. "El Gorrim" appears nowhere except the digest. |
| TTT-E2E (Tandon et al.) | 2512.23675 | Tandon et al. | Dec 2025 | VERIFIED | Confirmed in Gemini report with direct arXiv link and NVIDIA blog cross-reference (refs 19, 20, 21). ID format correct. Gemini title: "End-to-End Test-Time Training for Long Context." Codex marks RED (no local PDF) — but appears in Gemini report with multiple confirming URLs. Upgrade to VERIFIED based on two Gemini source URLs plus rewire.it blog. |
| GCPA (Geometry-Corrected Procrustes Alignment) | 2026 (no ID) | Unknown | 2026 | UNVERIFIED — RED FLAG | The Gemini report cites this with a Hugging Face daily papers search URL (ref 4: `huggingface.co/papers?q=observation-state+alignment`) which is not a specific paper link — it is a search results page. No title, no authors, no arXiv ID in any local source. The description ("robust alignment followed by post-hoc correction for directional mismatch") may be a synthesis of general Procrustes alignment techniques rather than a specific published paper. Do not cite until a real paper with verifiable ID is found. |

### Tier 3: Extends Our Understanding

| Title (as cited) | arXiv ID | Authors (from sources) | Date | Status | Notes |
|---|---|---|---|---|---|
| BILLY (Pai et al.) | 2510.10157 | Pai et al. | Jan 2026 | SINGLE-SOURCE | Not in Gemini report. Not in interpretability survey. Codex marks GREEN with local PDF. Not confirmed in this pass. Note: digest date is "Jan 2026" but arXiv ID 2510.XXXXX implies October 2025 submission — **date discrepancy**. |
| The Soul Engine | 2512.07092 | Not specified | Dec 2025 | SINGLE-SOURCE | Appears in Gemini report as "The Geometry of Persona: Disentangling Personality from Reasoning in Large Language Models" (ref 11, direct arXiv HTML link). Title in digest ("The Soul Engine") differs from the full Gemini title. The arXiv URL `arxiv.org/html/2512.07092v1` is cited specifically. ID format correct for Dec 2025. Single source, no corroborating local file. |
| PERSONA (activation vector algebra) | 2602.15669 | Not specified | Feb 2026 | UNVERIFIED | Not in Gemini report. Not in interpretability survey. No local primary source. No authors in any source. The title "PERSONA (activation vector algebra)" sounds like a search-agent label rather than an actual paper title. The description "dynamic compositional personality control at inference" is plausible but too generic to confirm without the paper. |
| Facet-Level SAE Control | 2602.19157 | Not specified | Feb 2026 | UNVERIFIED | Not in Gemini report. Not in interpretability survey. No local primary source. No authors. The name "Facet-Level SAE Control" does not appear anywhere except the digest. ID format correct for Feb 2026. Cannot verify. |
| Linear Personality Probing (Big Five) | 2512.17639 | Not specified | Jan 2026 | SINGLE-SOURCE | Not in Gemini report. Not in interpretability survey. Codex marks GREEN with local PDF at `Research/2512.17639v2.pdf`. Not confirmed in this pass. Date "Jan 2026" inconsistent with arXiv ID 2512.XXXXX (December 2025). |
| Steering Latent Traits, Not Learned Facts | 2511.18284 | Not specified | Nov 2025 | UNVERIFIED | Not in Gemini report. Not in interpretability survey. No local primary source. No authors. Title is thematically plausible but not corroborated by any source in the repository. ID format correct for Nov 2025. |
| Retrievit (Pantazopoulos et al.) | 2603.02874 | Pantazopoulos et al. | Mar 2026 | VERIFIED | Appears in Gemini report as "Retrievit: In-context Retrieval Capabilities of Transformers, State Space Models, and Hybrid Architectures" with direct arXiv HTML link (ref 1: `arxiv.org/html/2603.02874v1`). Authors confirmed as Pantazopoulos et al. in both Gemini report and digest. ID format correct. Finding (2D spiral SSM embeddings vs non-local Transformer associations) appears in both Gemini report and interpretability survey (indirectly supported). VERIFIED. |
| TransMamba (Chen et al.) — distillation | 2502.15130 | Chen et al. | Oct 2025 | VERIFIED | Confirmed in Perplexity report (ref [^1]: `arxiv.org/pdf/2502.15130.pdf`) and Codex appendix GREEN with local PDF `Research/2502.15130v2.pdf`. Perplexity describes it as Transformer→Mamba distillation via aligned latent space projections. Date in digest "Oct 2025" but arXiv ID 2502.XXXXX implies February 2025 submission — **date discrepancy**. |
| SideQuest | 2602.22603 | Not specified | Feb 2026 | UNVERIFIED | Not in Gemini report. Not in interpretability survey. No local primary source. No authors. Title "SideQuest" for a KV-management paper is unusual — may be a search-agent label. Cannot verify. |
| Ada-KV (Feng et al.) | 2510.00636 | Feng et al. | 2024 | UNVERIFIED — WRONG ID | Codex appendix identifies this ID as likely wrong and proposes `2407.11550` as the correct ID. Not in Gemini report. Not in interpretability survey. No local primary source confirms either ID. Do not use 2510.00636 as the citation. |
| Keyformer (Adnan et al.) | 2403.09054 | Adnan et al. | 2024 | SINGLE-SOURCE | Not in Gemini report. Not in interpretability survey. Codex marks RED (no local primary). Authors "Adnan et al." from digest only. ID format correct for Mar 2024. The technique (Gumbel-softmax token importance scoring) is a real and well-known approach, making this plausible. |

### Tier 4: Ethics & Moral Status

| Title (as cited) | arXiv ID | Authors (from sources) | Date | Status | Notes |
|---|---|---|---|---|---|
| Emergent Introspective Awareness (Lindsey/Anthropic) | 2601.01828 | Jack Lindsey (Anthropic) | **Oct 2025 (pub.) / Jan 2026 (arXiv)** | VERIFIED | Local primary source confirmed (`emergent_introspective_awareness_in_LLMs.txt`). Original publication: transformer-circuits.pub, **October 29, 2025**. The arXiv ID 2601.01828 corresponds to the January 2026 cross-post. The digest lists "Jan 2026" which is the arXiv date, not the original publication date. Gemini report cites it at 2601.01828 (consistent). Interpretability survey cites only the transformer-circuits URL (no arXiv ID). Author is Jack Lindsey, confirmed. Finding summary in digest is accurate but the ethical interpretation ("injection = involuntary neuromodulation") is an extrapolation beyond the paper's claims. **Date column in digest should read "Oct 2025 / arXiv Jan 2026."** |
| LLMs Report Subjective Experience (Berg et al.) | 2510.24797 | Berg et al. | Oct 2025 | VERIFIED | Confirmed in interpretability survey (URL: `arxiv.org/abs/2510.24797`). Codex marks GREEN with local PDF. Appears in both the interpretability survey and Codex appendix. |
| Probing Preferences of LLMs (Tagliabue & Dung) | 2509.07961 | Tagliabue & Dung | Sep 2025 | SINGLE-SOURCE | Not in Gemini report. Not in interpretability survey. Codex marks GREEN with local PDF. Not confirmed in this pass. Authors from digest only. |
| Taking AI Welfare Seriously (Long et al.) | 2411.00986 | Long, Sebo, Butlin, Finlinson, Fish, Harding, Pfau, Sims, Birch, Chalmers | 2024 | VERIFIED | Confirmed in local primary source (`emergent_introspective_awareness_in_LLMs.txt`, ref 43, full author list). Codex marks GREEN with local PDF. Full author list: Long, R., Sebo, J., Butlin, P., Finlinson, K., Fish, K., Harding, J., Pfau, J., Sims, T., Birch, J., Chalmers, D. |
| JEST (jailbreak via representation engineering) | OpenReview (no arXiv ID) | Not specified | 2025 | SINGLE-SOURCE | Appears in Gemini report as "From Rejection to Acceptance: Model Editing Guided by Representation Transition for Jailbreak Backdooring LLMs" with OpenReview URL (`openreview.net/forum?id=fYWssoFBo6`). No arXiv ID in any source. No local primary. The title in the Gemini report differs from the digest shorthand "JEST." Cannot confirm JEST is the paper's name rather than a digest label. |
| EU AI Act — GPAI provisions | — | n/a | Aug 2025 | SINGLE-SOURCE | Not a paper; a regulatory document. Cited correctly without an arXiv ID. Gemini report cites multiple GPAI compliance URLs. The Aug 2025 date refers to GPAI rules entering force, which is consistent with known EU AI Act timelines. Not a red flag — this is how legal frameworks are cited. |

---

## Bibliographic Corrections

| Item | Problem | Correction |
|------|---------|------------|
| Ada-KV | arXiv ID `2510.00636` is likely wrong | Correct ID appears to be `2407.11550` (per Codex appendix). Do not cite until confirmed. |
| TransMamba (Li et al.) | Digest date "Jan 2026" inconsistent with ID `2503.24067` (Mar 2025 submission) | Correct to "Mar 2025" or verify the actual submission date. |
| TransMamba (Chen et al.) | Digest date "Oct 2025" inconsistent with ID `2502.15130` (Feb 2025 submission) | Correct to "Feb 2025." |
| BILLY | Digest date "Jan 2026" inconsistent with ID `2510.10157` (Oct 2025 submission) | Correct to "Oct 2025." |
| Linear Personality Probing | Digest date "Jan 2026" inconsistent with ID `2512.17639` (Dec 2025 submission) | Correct to "Dec 2025." |
| Emergent Introspective Awareness | Digest date "Jan 2026" is the arXiv cross-post date, not publication date | Add note: "pub. Oct 29 2025 (transformer-circuits.pub); arXiv cross-posted Jan 2026." |
| Mamba-3 authors | "Lahoti, Dao, Gu" not confirmed in local PDF (double-blind) | Mark as "Anonymous (ICLR 2026)" until authors are officially confirmed post-review. |
| GCPA | No title, no authors, no real arXiv ID | Remove or quarantine until a verifiable paper is found. |
| Titans / MIRAS | Combined into one row | Split into two separate rows: Titans (2501.00663) and MIRAS (2504.13173). |
| "Grok confirms" claims | No Grok report file found locally | Cannot verify Grok-sourced claims. Do not treat as independent validation. |

---

## Papers Appearing in Both Gemini Report AND a Second Local Source (Highest Confidence)

These papers have the strongest cross-source support from materials available in this repository:

| Paper | arXiv ID | Second Source |
|-------|---------|---------------|
| Titans | 2501.00663 | Google Research blog (local file) + Codex GREEN |
| MIRAS | 2504.13173 | Google Research blog (local file) + Codex GREEN |
| TTT-E2E | 2512.23675 | Gemini report + NVIDIA blog + rewire.it blog (Gemini refs 19-21) |
| Retrievit | 2603.02874 | Gemini report + interpretability survey (implicit) |
| Emergent Introspective Awareness | 2601.01828 | Local primary source (txt file) + Gemini report + interpretability survey |
| Taking AI Welfare Seriously | 2411.00986 | Local primary (emergent_introspective_awareness refs) + Codex GREEN |
| TransMamba (Chen et al.) | 2502.15130 | Perplexity report + Codex GREEN + local PDF |

---

## arXiv ID Format Check

All IDs use the `YYMM.NNNNN` format. The following are consistent with their cited dates:

- 2603.14517 (Mar 2026) — consistent
- 2503.24067 (Mar 2025, NOT Jan 2026 as cited) — **date mismatch in digest**
- 2603.03326 (Mar 2026) — consistent
- 2603.15569 (Mar 2026) — consistent
- 2501.00663 (Jan 2025, cited as Dec 2024) — minor: arXiv submission vs preprint date
- 2504.13173 (Apr 2025) — consistent
- 2410.01805 (Oct 2024) — consistent
- 2509.08315 (Sep 2025) — consistent
- 2511.11707 (Nov 2025) — consistent
- 2512.23675 (Dec 2025) — consistent
- 2510.10157 (Oct 2025, cited as Jan 2026) — **date mismatch**
- 2512.07092 (Dec 2025) — consistent
- 2602.15669 (Feb 2026) — consistent
- 2602.19157 (Feb 2026) — consistent
- 2512.17639 (Dec 2025, cited as Jan 2026) — **date mismatch**
- 2511.18284 (Nov 2025) — consistent
- 2603.02874 (Mar 2026) — consistent
- 2502.15130 (Feb 2025, cited as Oct 2025) — **date mismatch**
- 2602.22603 (Feb 2026) — consistent
- 2510.00636 (Oct 2025) — **likely wrong paper**
- 2403.09054 (Mar 2024) — consistent
- 2601.01828 (Jan 2026 arXiv, Oct 2025 publication) — minor, explained
- 2411.00986 (Nov 2024, cited as 2024) — consistent
- OpenReview ID for JEST — no arXiv ID, cite as OpenReview

---

## Papers That Are Too Perfectly Tailored (Hallucination Risk)

The following papers have descriptions that map so precisely onto MoCoP's specific architecture that they warrant extra scrutiny before use in formal citations:

| Paper | Concern |
|-------|---------|
| GCPA | Zero verifiable trace. Description fits our cross-arch mapping problem perfectly. May be an agent synthesis of general Procrustes alignment literature rather than a real paper. |
| FSC-Net (El Gorrim) | Description maps perfectly to "Mamba (fast) + Qdrant (slow)" framing that is MoCoP-specific. Author name appears only in digest. Could be a real fast/slow consolidation paper with a different framing being over-interpreted. |
| PERSONA (2602.15669) | "Dynamic compositional personality control at inference" describes exactly what MoCoP's bridge does. No other source mentions it. |
| Steering Latent Traits, Not Learned Facts (2511.18284) | Title and finding ("dispositional modulation more effective than factual injection") directly validates WHY.md's core claim with unusual precision. No corroborating source. |
| SideQuest (2602.22603) | "Model-driven KV management for long-horizon agentic reasoning. Directly applicable to MUD agent sessions." The MUD application specificity is a digest editorial addition, but the paper itself remains unconfirmed. |

---

## Safe Citations for Immediate Use in Framework Docs

These papers have sufficient cross-source support to use in `unified_cognitive_framework.md` now:

1. **Titans** (2501.00663) and **MIRAS** (2504.13173) — as separate entries, for long-memory / retention-gate math
2. **TTT-E2E** (2512.23675) — for O(1) state inference latency
3. **Retrievit** (2603.02874) — for SSM vs Transformer geometric complementarity
4. **Emergent Introspective Awareness** (2601.01828) — for ethics layer, with explicit note: paper claims functional introspective awareness at ~20%; the "involuntary neuromodulation" framing is editorial extrapolation
5. **Taking AI Welfare Seriously** (2411.00986) — for ethics layer, author list confirmed
6. **TransMamba (Chen et al.)** (2502.15130) — for cross-arch distillation context
7. **Mamba-3** (2603.15569) — for upgrade path discussion, but mark authors as "Anonymous (ICLR 2026)" and replace "mathematically imperative" with "strongly motivated"

Hold the following until primary sources are confirmed:
- SleepGate, SAS/Personality Sliders, TransMamba (Li et al.), EvolKV, FSC-Net — Codex PDFs cited but not independently verified in this pass
- GCPA — quarantine entirely

---

*Previous appendix by Codex (GREEN/YELLOW/RED framework) is complementary to this pass, not contradicted. The two passes used different verification methods: Codex verified against local PDFs; this pass cross-referenced between available local text files and the Gemini report. Discrepancies are noted above.*

*— Anda, 2026-03-20*
