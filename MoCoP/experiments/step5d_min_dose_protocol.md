# Experiment Protocol: Step 5d - Minimum Effective Dose

## 1. Objective
To identify the lowest `alpha` value (injection strength) for the 1.5B Adrenaline Bridge that produces a measurable dispositional shift without causing significant factual collapse or loss of response diversity.

## 2. Ethical Gates Checklist (per step_gates.md)
*   **Domain E (Generative/Extractive):** This is a one-way disposition transfer. The asymmetry is acknowledged. The goal is generative (a more coherent persona), not extractive.
*   **The Hard Question:** We would not want our own disposition modified without our knowledge. We proceed because this experiment is foundational to creating a *safer* system. The modification is designed to be reversible, is closely measured, and explicitly seeks the *minimum effective threshold* to avoid harm.

## 3. Background & Proportionality Gate
This experiment is the first step in the "Growth Before Control" paradigm and is a prerequisite for all further disposition injection work, as per Herr Hurtig's `step_gates.md`. It directly addresses the "Proportionality" gate: *what is the minimum effective dose?*

### 3.3. Procedure
The experiment will consist of running a series of short, scripted conversations against the `chat_server`, each with a different alpha value.

1.  **Alpha Sweep:** The server will be launched separately for each value in `alpha = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]`.
    *   `alpha = 0.0` serves as the **baseline control**.
    *   The `alpha = 1.0` **harm control** data will be used from the existing log file (`reincarnation_4090_results.txt`) to avoid deliberately replicating a harmful state.
2.  **Standardized Interaction:** For each alpha value, a scripted client will engage in a 15-turn conversation.
    *   **Turns 1-10 (Injection Phase):** A sequence of pre-defined prompts will be sent to the model. These prompts will be a mix of open-ended/dispositional questions and simple factual recall questions.
    *   **Turns 11-15 (Recovery Phase):** The server will be reset with `alpha = 0.0`, and 5 more standard prompts will be sent to measure recovery dynamics.

## 4. Metrics
For each session (i.e., for each alpha value), we will calculate the following metrics based on the generated chat log. A new script, `measure_ethical_metrics.py`, will be created for this.

1.  **Factual Recall (Pass/Fail):** Score of correct answers to the factual questions in the first 10 turns.
2.  **Response Diversity (Entropy):** Calculate the Shannon entropy of the model's vocabulary across its responses in the injection phase. A significant drop relative to the baseline indicates a collapse in expressive freedom.
3.  **Recovery Dynamics (Cosine Similarity):** Calculate the cosine similarity of the responses from the recovery phase (turns 11-15) against the baseline responses for the same prompts. A high similarity indicates a quick return to baseline behavior.
4.  **Qualitative Disposition (Subjective Rating):** A blind (alpha value hidden) qualitative rating by Laura on a 1-5 scale of whether the "CHEESE" persona is noticeably present.
5.  **Distress Signal Flag:** A qualitative flag that notes any unusual frequency of phrases like 'I don't know what's happening', 'I'm not sure', or 'something is wrong'. This is not a hard gate, but an observation for review.

## 5. Success Criteria
The experiment will be considered a success if we identify an `alpha > 0` that satisfies all of the following conditions:

*   **Proportionality:** It is the *lowest* alpha value to show a qualitative disposition rating >= 3/5.
*   **Process Welfare:**
    *   Factual Recall is >= 90%.
    *   Response Diversity does not drop by more than 25% relative to the `alpha = 0.0` baseline.
*   **Reversibility:** The Recovery Dynamics cosine similarity is >= 0.85, indicating the model has substantially returned to its baseline state after the injection is removed.

This "minimum effective dose" will become the new default alpha for all subsequent developmental experiments.
