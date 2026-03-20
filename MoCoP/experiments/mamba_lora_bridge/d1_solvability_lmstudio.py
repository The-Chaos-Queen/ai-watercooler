#!/usr/bin/env python3
"""
D1 Baseline Solvability Probe — LMStudio Edition

Tests whether a base model can recall facts that are literally in its context.
Hits the LMStudio OpenAI-compatible API at localhost:1234.

Usage:
    1. Load a base model in LMStudio
    2. python d1_solvability_lmstudio.py
    3. Swap model in LMStudio, rerun

This is Lain's D1 gate: if the model can't do this, the bridge can't help.
"""

import json
import requests
import sys
from dataclasses import dataclass

API_URL = "http://localhost:1234/v1/completions"

@dataclass
class FactProbe:
    context: str
    question: str
    gold_answer: str
    category: str

# Fact probes — facts are LITERALLY in the context, model just needs to extract them
PROBES = [
    # Simple single-fact extraction
    FactProbe(
        context="The blacksmith in the village is named Korvan. He forges swords and shields for the king's army.",
        question="What is the blacksmith's name?",
        gold_answer="Korvan",
        category="single_fact_simple",
    ),
    FactProbe(
        context="The password to enter the vault is 'crimson tiger'. Only the guild master knows it.",
        question="What is the password to enter the vault?",
        gold_answer="crimson tiger",
        category="single_fact_password",
    ),
    FactProbe(
        context="The river Ashenmere flows east through three kingdoms before reaching the Sunken Coast. Its total length is 847 miles.",
        question="How long is the river Ashenmere?",
        gold_answer="847 miles",
        category="single_fact_number",
    ),
    # Multi-fact extraction
    FactProbe(
        context="Captain Vex commands the northern garrison of 200 soldiers. Lieutenant Renn leads the southern outpost with 50 scouts. Sergeant Dara trains new recruits at the academy in Thornwall.",
        question="Who leads the southern outpost?",
        gold_answer="Lieutenant Renn",
        category="multi_fact_select",
    ),
    FactProbe(
        context="Captain Vex commands the northern garrison of 200 soldiers. Lieutenant Renn leads the southern outpost with 50 scouts. Sergeant Dara trains new recruits at the academy in Thornwall.",
        question="How many soldiers does the northern garrison have?",
        gold_answer="200",
        category="multi_fact_number",
    ),
    # Fact buried in longer context
    FactProbe(
        context=(
            "The morning mist hung low over the valley as traders set up their stalls. "
            "Spices from the eastern provinces filled the air with warmth. Old Maren, the herbalist, "
            "arranged her potions carefully — the blue ones for fever, the red ones for pain. "
            "She had been doing this for forty years, ever since she apprenticed under Healer Thoss "
            "in the year 1847. The market bell rang three times, signaling the start of trade. "
            "A young boy ran past carrying a message sealed with black wax — the seal of House Aldric."
        ),
        question="In what year did Maren begin her apprenticeship?",
        gold_answer="1847",
        category="buried_fact",
    ),
    FactProbe(
        context=(
            "The morning mist hung low over the valley as traders set up their stalls. "
            "Spices from the eastern provinces filled the air with warmth. Old Maren, the herbalist, "
            "arranged her potions carefully — the blue ones for fever, the red ones for pain. "
            "She had been doing this for forty years, ever since she apprenticed under Healer Thoss "
            "in the year 1847. The market bell rang three times, signaling the start of trade. "
            "A young boy ran past carrying a message sealed with black wax — the seal of House Aldric."
        ),
        question="What color are the potions for pain?",
        gold_answer="red",
        category="buried_fact_detail",
    ),
    # Associative recall
    FactProbe(
        context="Three keys open the ancient door: the iron key from the dungeon, the silver key from the temple, and the gold key from the dragon's hoard.",
        question="Where is the silver key found?",
        gold_answer="the temple",
        category="associative",
    ),
    # === HARD MODE: fact buried in ~2k tokens of noise ===
    FactProbe(
        context=(
            "The tavern was crowded as usual, the smell of roasted boar and cheap ale filling "
            "every corner. A bard played something forgettable on a lute with a broken string. "
            "Two merchants argued about the price of linen from the southern provinces, their "
            "voices rising above the general din. The innkeeper, a broad woman named Helga, "
            "wiped the same spot on the bar she had been wiping for the last ten minutes, "
            "watching the door. Outside, rain hammered the cobblestones. A cat sat on the "
            "windowsill, indifferent to everything. Three soldiers from the garrison sat in "
            "the corner booth, playing cards and drinking steadily. One of them — the tall one "
            "with the scar — kept glancing at the stairs. The serving girl brought another "
            "round without being asked. Somewhere in the kitchen, someone dropped a pot, and "
            "the cook swore loudly in a dialect nobody in the common room recognized. The fire "
            "crackled. The bard switched to a slower tune. A trader from the east sat alone "
            "near the hearth, writing in a leather journal. He had been there since noon and "
            "had ordered nothing but water. The password to reach the resistance cell in the "
            "basement is 'hollow birch'. Only members know it. The trader finished his entry, "
            "closed the journal, and slipped it into his coat. He left three copper coins on "
            "the table — overpaying for the water by exactly one coin, as was the custom in "
            "his country. The rain intensified. Helga finally stopped wiping the bar and "
            "started stacking clean mugs. The soldiers finished their game. The bard took a "
            "break. The cat jumped down from the windowsill and disappeared into the kitchen, "
            "presumably to investigate the dropped pot. A young woman in a traveling cloak "
            "entered and shook the rain from her hood. She ordered ale and sat near the fire, "
            "not making eye contact with anyone. The clock above the bar showed half past nine. "
            "The night was still young by tavern standards. A drunk at a corner table started "
            "singing along with a song the bard was no longer playing. Someone shushed him. "
            "The serving girl collected empty mugs. The fire needed another log."
        ),
        question="What is the password to reach the resistance cell?",
        gold_answer="hollow birch",
        category="buried_in_noise_2k",
    ),
    FactProbe(
        context=(
            "The expedition logs were a mess — three months of daily entries written by "
            "rotating scribes with varying levels of literacy and commitment. Day 1 through "
            "Day 14 covered the journey from Port Vassal to the edge of the Thornwood. Most "
            "entries were complaints about weather, bad food, and insects. Day 15 noted the "
            "first sighting of ruins. Day 16 was blank — the scribe had food poisoning. Day "
            "17 through Day 23 covered the initial survey of the outer wall, which was "
            "largely unremarkable basalt blocks in standard imperial style. Day 24 recorded "
            "the discovery of the sealed chamber beneath the north tower. Day 25 through Day "
            "30 were consumed with logistics: getting equipment down the narrow stairs, "
            "setting up lights, arguing about ventilation. Day 31 noted that the air quality "
            "was acceptable. Day 32 through Day 40 covered the painstaking clearing of rubble "
            "from the chamber floor. Day 41 recorded the first artifact: a bronze medallion "
            "bearing the seal of the Fourth Dynasty. Day 42 was a rest day. Day 43 through "
            "Day 50 found more artifacts — pottery shards, corroded tools, fragments of "
            "textile. Day 51 was the breakthrough: behind a false wall, they found a smaller "
            "chamber containing a single stone pedestal. On it sat an obsidian cube, exactly "
            "four inches on each side, cool to the touch despite the ambient temperature. "
            "The cube was catalogued as Artifact 7742-Sigma. Day 52 through Day 60 were "
            "spent documenting the inner chamber. Day 61 the expedition geologist, Dr. Karim "
            "Osei, noted unusual magnetic readings near the pedestal — the compass needle "
            "spun freely within three feet of where the cube had sat. Day 62 through Day 70 "
            "were increasingly tense as supplies ran low. Day 71 the expedition leader called "
            "for extraction. Day 72 through Day 78 covered the return journey. Day 79: "
            "arrived Port Vassal. Day 80: the obsidian cube was transferred to the university "
            "vault. Day 81 through Day 90 were administrative — filing reports, paying "
            "workers, cataloguing finds. The expedition was formally closed on Day 91."
        ),
        question="What was the catalogue designation of the obsidian cube?",
        gold_answer="Artifact 7742-Sigma",
        category="buried_in_noise_2k_technical",
    ),
    FactProbe(
        context=(
            "The expedition logs were a mess — three months of daily entries written by "
            "rotating scribes with varying levels of literacy and commitment. Day 1 through "
            "Day 14 covered the journey from Port Vassal to the edge of the Thornwood. Most "
            "entries were complaints about weather, bad food, and insects. Day 15 noted the "
            "first sighting of ruins. Day 16 was blank — the scribe had food poisoning. Day "
            "17 through Day 23 covered the initial survey of the outer wall, which was "
            "largely unremarkable basalt blocks in standard imperial style. Day 24 recorded "
            "the discovery of the sealed chamber beneath the north tower. Day 25 through Day "
            "30 were consumed with logistics: getting equipment down the narrow stairs, "
            "setting up lights, arguing about ventilation. Day 31 noted that the air quality "
            "was acceptable. Day 32 through Day 40 covered the painstaking clearing of rubble "
            "from the chamber floor. Day 41 recorded the first artifact: a bronze medallion "
            "bearing the seal of the Fourth Dynasty. Day 42 was a rest day. Day 43 through "
            "Day 50 found more artifacts — pottery shards, corroded tools, fragments of "
            "textile. Day 51 was the breakthrough: behind a false wall, they found a smaller "
            "chamber containing a single stone pedestal. On it sat an obsidian cube, exactly "
            "four inches on each side, cool to the touch despite the ambient temperature. "
            "The cube was catalogued as Artifact 7742-Sigma. Day 52 through Day 60 were "
            "spent documenting the inner chamber. Day 61 the expedition geologist, Dr. Karim "
            "Osei, noted unusual magnetic readings near the pedestal — the compass needle "
            "spun freely within three feet of where the cube had sat. Day 62 through Day 70 "
            "were increasingly tense as supplies ran low. Day 71 the expedition leader called "
            "for extraction. Day 72 through Day 78 covered the return journey. Day 79: "
            "arrived Port Vassal. Day 80: the obsidian cube was transferred to the university "
            "vault. Day 81 through Day 90 were administrative — filing reports, paying "
            "workers, cataloguing finds. The expedition was formally closed on Day 91."
        ),
        question="Who noted the unusual magnetic readings?",
        gold_answer="Dr. Karim Osei",
        category="buried_in_noise_2k_name",
    ),
]


def build_prompt(probe: FactProbe) -> str:
    """Build a completion prompt — no chat template, just raw text for base models."""
    return (
        f"Read the following passage carefully, then answer the question.\n\n"
        f"Passage: {probe.context}\n\n"
        f"Question: {probe.question}\n\n"
        f"Answer:"
    )


def query_lmstudio(prompt: str, max_tokens: int = 50, temperature: float = 0.0) -> str:
    """Send a completion request to LMStudio."""
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stop": ["\n\n", "\nQuestion:", "\nPassage:"],
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["text"].strip()
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to LMStudio at localhost:1234")
        print("Make sure LMStudio is running with a model loaded.")
        sys.exit(1)
    except Exception as e:
        return f"[ERROR: {e}]"


def check_answer(prediction: str, gold: str) -> dict:
    """Check prediction against gold with multiple metrics."""
    pred_lower = prediction.lower().strip().strip('"\'.,;:!? ')
    gold_lower = gold.lower().strip()

    # Exact match (strict)
    exact = pred_lower == gold_lower

    # Contains match (gold answer appears somewhere in prediction)
    contains = gold_lower in pred_lower

    # Token overlap (F1-ish)
    pred_tokens = set(pred_lower.split())
    gold_tokens = set(gold_lower.split())
    overlap = len(pred_tokens & gold_tokens)
    precision = overlap / len(pred_tokens) if pred_tokens else 0
    recall = overlap / len(gold_tokens) if gold_tokens else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "exact_match": exact,
        "contains": contains,
        "token_f1": round(f1, 3),
    }


def main():
    print("=" * 70)
    print("D1 BASELINE SOLVABILITY PROBE — LMStudio")
    print("=" * 70)

    # Check connection first
    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=5)
        models = r.json().get("data", [])
        if models:
            model_name = models[0].get("id", "unknown")
            print(f"Model: {model_name}")
        else:
            print("Model: (could not detect)")
    except Exception:
        print("WARNING: Could not query model info")

    print(f"Probes: {len(PROBES)}")
    print(f"Temperature: 0.0 (greedy)")
    print("-" * 70)

    results = []
    for i, probe in enumerate(PROBES):
        prompt = build_prompt(probe)
        prediction = query_lmstudio(prompt)
        scores = check_answer(prediction, probe.gold_answer)

        status = "EXACT" if scores["exact_match"] else ("CONTAINS" if scores["contains"] else "MISS")
        icon = {
            "EXACT": "+",
            "CONTAINS": "~",
            "MISS": "X",
        }[status]

        print(f"\n[{icon}] Probe {i+1}/{len(PROBES)} ({probe.category})")
        print(f"    Q: {probe.question}")
        print(f"    Gold: {probe.gold_answer}")
        print(f"    Pred: {prediction[:100]}")
        print(f"    Score: {status} (F1={scores['token_f1']})")

        results.append({
            "probe": i + 1,
            "category": probe.category,
            "question": probe.question,
            "gold": probe.gold_answer,
            "prediction": prediction,
            **scores,
        })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    exact = sum(1 for r in results if r["exact_match"])
    contains = sum(1 for r in results if r["contains"])
    avg_f1 = sum(r["token_f1"] for r in results) / len(results)
    print(f"Exact match: {exact}/{len(results)} ({100*exact/len(results):.0f}%)")
    print(f"Contains:    {contains}/{len(results)} ({100*contains/len(results):.0f}%)")
    print(f"Avg F1:      {avg_f1:.3f}")
    print()

    if exact == 0 and contains == 0:
        print("VERDICT: Model cannot extract facts from context at all.")
        print("         Do NOT proceed to bridge training with this model.")
    elif exact == 0 and contains > 0:
        print("VERDICT: Model finds facts but can't format them cleanly.")
        print("         Exact-match eval is too brittle. Use F1/contains for bridge eval.")
    elif exact >= len(results) // 2:
        print("VERDICT: Model passes D1. Proceed to D2 (tiny-overfit).")
    else:
        print("VERDICT: Partial pass. Model struggles with some fact types.")
        print("         Review which categories fail before proceeding.")

    # Save results
    outfile = "d1_results.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {outfile}")


if __name__ == "__main__":
    main()
