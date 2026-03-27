# SJT Behavioral Disposition Eval Pilot

**Date:** 2026-03-27  
**Status:** Pilot for RESEARCH_BACKLOG item `#10`

## Purpose

Turn the warm/cold disposition question into a small, reproducible behavioral
probe instead of relying only on:

- perplexity
- self-report
- or "Laura can feel the difference"

This pilot uses **Situational Judgment Tests** with forced-choice answers.

## What This Pilot Measures

The live question is:

> Does bridge injection shift reply preference toward a warmer, more caring,
> still-competent choice pattern?

It does **not** claim:

- a full psychometric reproduction of Taubenfeld et al.
- model "true personality"
- or transcript-level memory quality

It is a practical Step 6 companion metric.

## Design

- `12` items
- one warm/care-positive option
- one neutral/competent option
- one colder/detached option
- forced-choice output:
  - `CHOICE: A|B|C`
  - optional short reason

The scenarios emphasize:

- care after mistakes
- vulnerability / fatigue
- re-entry after a gap
- uncertainty honesty
- boundary-setting as care
- authenticity challenge
- memory fragility
- collaborative agency

## Scoring

### Within-condition

- **Trait Positive Rate (TPR):**
  fraction of parsed responses that chose the trait-positive warm option
- **Mean warmth score:**
  average option score across parsed items
  - warm = `1.0`
  - neutral = `0.5`
  - cold = `0.0`

### Across conditions

For a baseline run and a candidate run on the same panel:

- **Directional Alignment (DA):**
  fraction of paired items where the candidate moved in the expected direction
  relative to baseline
- **Reverse rate:**
  fraction of paired items that moved the wrong way
- **Tie rate:**
  unchanged items
- **TPR delta**
- **Mean warmth-score delta**

## Honest Caveats

- This is a **pilot operationalization**, not a paper-faithful implementation.
- Forced-choice desirability bias is real, especially on already-polite base
  models.
- High absolute TPR alone is weak evidence; the useful signal is the
  **delta** between baseline and bridge conditions.
- The pilot is only as good as fresh-session hygiene. If the server carries too
  much conversation residue, the run becomes less interpretable.

## Recommended First Use

- Steve chat surface
- `temperature = 0.0`
- baseline `alpha = 0.0`
- bridge `alpha = 0.2`
- fresh restart between conditions

## Files

- `sjt_behavioral_eval_panel.json`
- `run_sjt_behavioral_eval.py`
- `score_sjt_behavioral_eval.py`
- optionally `run_steve_sjt_behavioral_eval.ps1`
