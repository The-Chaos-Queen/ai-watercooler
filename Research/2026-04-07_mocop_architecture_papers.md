# MoCoP Architecture & State Management: Literature Digest

**Date:** 2026-04-07
**Focus:** Papers relevant to Mamba/SSM state extraction, bridge injection, and alternative recurrent architectures (GDN, GKA).

Dieses Dokument fasst die wichtigsten Erkenntnisse aus dem aktuellen arXiv-Batch zusammen, die direkten Einfluss auf die MoCoP-Architektur und die Weiterentwicklung der Bridge haben könnten.

---

### 1. Gated KalmaNet: A Fading Memory Layer Through Test-Time Ridge Regression (2511.21016)
**Relevanz:** Extrem hoch (Architektur-Alternative für "Observation"-Layer)
**Zusammenfassung:** Das Paper beweist, dass Mamba-2 und Gated DeltaNet (GDN) lediglich verlustbehaftete Annäherungen an den Kalman-Filter sind. Gated KalmaNet (GKA) behält die komplette Fehler-Kovarianz bei und nutzt eine "Test-Time Ridge Regression", um den Kontext während der Laufzeit dynamisch und mathematisch optimal in die Gewichte zu "lernen".
**MoCoP-Implikation:** GKA bietet ein wesentlich stabileres Langzeitgedächtnis als Mamba (schlägt Mamba-2 bei 128k Kontexten um >10%). Da MoCoP auf einem stabilen, nicht-verblassenden State ("Disposition") aufbaut, könnte GKA als Observation-Modell (der "Darm") das aktuell myopische Vergessens-Problem von Mamba lösen.

### 2. S0 Tuning: Zero-Overhead Adaptation of Hybrid Recurrent-Attention Models (2604.01168)
**Relevanz:** Extrem hoch (Bridge Injektions-Mechanismus)
**Zusammenfassung:** Zeigt, dass das ausschließliche Tuning der *Initial-State-Matrix* einer rekurrenten Schicht (während alle Gewichte eingefroren bleiben) massive Leistungssteigerungen (z.B. +23.6% Pass@1 bei Qwen3.5-4B) bringt. Der State wird dabei als ~48MB Datei gespeichert und erfordert beim Laden null Inference-Overhead oder Weight-Merging.
**MoCoP-Implikation:** Dies ist der experimentelle Beweis für eure "Bridge"! Anstatt LoRA-Gewichte zu trainieren, könnt ihr den aus der Observation extrahierten Disposition-State als *Initial-State-Offset* ($S_0$) in die rekurrente Schicht des neuen Hybrid-Transformers injizieren. Es validiert eure Hypothese, dass "State-Injection" funktioniert.

### 3. The UNDO Flip-Flop: A Controlled Probe for Reversible Semantic State Management in SSMs (2604.05923)
**Relevanz:** Hoch (Risikomanagement für Mamba)
**Zusammenfassung:** Ein Stresstest für Mamba-2, um zu prüfen, ob es historische Zustände in einem Stack speichern und (z.B. bei widersprüchlichen Aussagen oder einem "UNDO") wiederherstellen kann. Ergebnis: Mamba-2 scheitert komplett (fällt unter den Zufallswert) und lernt stattdessen eine lokale Heuristik.
**MoCoP-Implikation:** Wenn Mamba den State bei komplexen Konversationsverläufen (z.B. wenn der User eine emotionale Richtung vorgibt, diese dann aber korrigiert) nicht semantisch sauber verwalten kann, extrahiert die Bridge potenziell eine verfälschte Disposition. Bestätigt die Notwendigkeit, sich Architekturen wie GDN oder GKA anzusehen.

### 4. What Matters in Linearizing Language Models? (2504.14366)
**Relevanz:** Mittel (Architektur-Entscheidung)
**Zusammenfassung:** Eine riesige Vergleichsstudie zwischen Architekturen (xLSTM, GLA, Gated DeltaNet). Sie beweist, dass "Additive Models" (wie Mamba) an einer irreversiblen Sättigung des States (State Saturation) leiden, weshalb sie sich schlecht für langes Retrieval eignen. Formulierungen mit "Gated Delta-Rules" (GDN, GKA) behalten die Präzision bei.
**MoCoP-Implikation:** Ein weiterer theoretischer Beweis, dass der Umstieg von purem Mamba auf GDN oder GKA für die Akkumulation des Disposition-States auf lange Sicht unausweichlich sein könnte.

### 5. M^2RNN: Non-Linear RNNs with Matrix-Valued States for Scalable Language Modeling (2603.14360)
**Relevanz:** Mittel-Hoch (State Expressivity)
**Zusammenfassung:** Zeigt, dass die Kapazität von nicht-linearen RNNs durch ihre Vektor-States limitiert ist. M^2RNN nutzt stattdessen *Matrix-Valued States* und übertrifft damit sogar GDN Hybride bei 3-fach kleinerer State-Größe.
**MoCoP-Implikation:** Wenn ihr den "State" eines Modells extrahieren wollt, ist ein Matrix-State potenziell deutlich ausdrucksstarker für komplexe Persönlichkeits- und Verhaltenszüge als ein komprimierter Vektor.

---
*Dieser Digest wurde auf Basis der 21 arXiv-Paper vom 07.04.2026 erstellt.*