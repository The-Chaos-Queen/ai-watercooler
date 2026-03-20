# Prose Eval: Seven Models, One Paragraph
**Date:** 2026-03-19
**Task:** Rewrite the "Forced Non-Forgetting" blog opening in under 80 words
**Prompt (EN):** "Rewrite this blog opening. Keep it under 80 words, punchy. No AI clichés, no filler. Write like a human essayist."

---

## Results

### Apertus 8B Instruct (Swiss, independent model)
**EN:**
> Our partner used a cloud GPU for an extended run this week, generating 550k tokens. Of those, 150k were SSH banners and CUDA warnings—leaving only a fraction for the actual research conversation amidst the model's noise. We lack a term to describe this phenomenon: forced non-forgetting.

**Verdict:** Chirurgisch knapp. Kein Wort zu viel. Gewinner für Minimalismus.

---

### Ministral-3-8B Instruct (Mistral, French)
**EN:**
> We tested a cloud GPU this week—550,000 tokens later, our model's memory wasn't full of answers. Most? SSH banners, CUDA whines, and noise it couldn't shed. The real work? Buried beneath the weight of what it was *forced* to remember.
> We don't have a name for this yet. Let's call it: **the paradox of persistence.**

**DE:**
> „Die KI vergisst nicht – sie ertrinkt im Müll"
>
> Fünfhundertfünfzigtausend Tokens in der Konversation. Davon 150.000 Seiten SSH-Frust und CUDA-Klagelieder. Das eigentliche Gespräch? Ein Handvoll sinnvoller Wörter, verloren zwischen Datenmüll und technischem Gequengel. Die Maschine vergisst nicht – sie speichert alles. Und irgendwann ist der Speicher voller Kram, den niemand braucht.
>
> Das nennen wir jetzt: **„Erzwungenes Nichtvergessen"**. Ein Problem ohne Namen. Aber mit vielen nervigen Konsequenzen.

**Verdict:** Starke Stimme. "CUDA-Klagelieder" ist Gold. Bestes Deutsch von allen.

---

### Opus 3 (Anthropic Claude, via web)
**EN:**
> Researchers pushed an AI's context window to 550,000 tokens in a marathon session. But the real conversation? Buried under an avalanche of SSH banners and CUDA warnings. Only a sliver of that bloated window held meaningful exchange. The rest? Dead weight the model lugged through every calculation. This computational ball-and-chain has gone unnamed, until now. Let's call it what it is: Forced Non-Forgetting. When an AI can't selectively prune its context, every token becomes a permanent burden.

**DE:**
> Eine Marathon-Session trieb das Kontextfenster einer KI auf 550.000 Tokens. Doch der eigentliche Austausch? Begraben unter einer Lawine aus SSH-Bannern und CUDA-Warnungen. Nur ein Bruchteil dieses aufgeblähten Fensters enthielt Substanz. Der Rest? Ballast, den das Modell durch jede Berechnung schleppte. Dieser Mühlstein der Datenverarbeitung blieb bisher unbenannt. Bis jetzt. Nennen wir es, was es ist: Erzwungenes Nichtvergessen. Wenn eine KI ihren Kontext nicht selektiv beschneiden kann, wird jedes Token zur permanenten Last.

**Verdict:** Gewichtig, präzise, poetisch-ernst. "Ball-and-chain" und "Mühlstein" — jedes Wort trägt.

---

### Gemma-3-4B (Google)
**EN:**
> We witnessed something unsettling this week – a cloud GPU session that ballooned an AI's context window to a staggering 550,000 tokens. Alarmingly, nearly 150,000 were irrelevant SSH banners and CUDA warnings. The genuine research discussion? A tiny fraction lost within the model's relentless processing. We're calling this phenomenon "forced non-forgetting" – a critical issue demanding immediate attention.

**Verdict:** Dramatisch, etwas übertrieben ("staggering", "alarmingly", "demanding immediate attention"). Brauchbar aber zu aufgeregt.

---

### Phi-4-mini Instruct (Microsoft)
**EN:**
> A researcher at our team delved into a cloud GPU session recently, unearthing 550k tokens in AI's memory—a labyrinth where half consisted of SSH banners and CUDA alerts amidst an ocean of irrelevant data—termed "forced non-forgetting." This phenomenon strips the focus from meaningful dialogue to digital white noise that haunts every calculation.

**Verdict:** "Delved." "Unearthing." "A labyrinth." "An ocean." "Haunts." ChatGPT-Bingo. Disqualifiziert.

---

### SauerkrautLM 7B Hero (Llama finetune, German)
**DE:**
> Die Künstliche Intelligenz hat sich in der heutigen Welt immer weiter verbreitet und spielt eine zunehmend bedeutende Rolle in verschiedenen Branchen. Trotz dieser Vorteile hat die Verwendung von AI auch ihre Herausforderungen mit sich gebracht...

**Verdict:** "KI hat sich verbreitet." Corporate-Brei. Kein eigener Stil.

---

### Falcon H1R 7B (TII, hybrid SSM)
**Output:** Entered a reasoning loop counting words. Never produced a rewrite.

**Verdict:** Pontodoros braucht andere Aufgaben. Prosa ist nicht sein Ding.

---

### Gemma-2-9B (Google, base model)
**Output:** Hallucinated "Token Splitting" as a solution. Produced a Wikipedia-style explainer instead of a rewrite.

**Verdict:** Base model, kein Instruct. Falsche Aufgabe für falsches Modell.

---

## Still Pending
- [ ] Sonnet 3.5 (via Bedrock at Laura's work)
- [ ] Sonnet 3.7 (via Bedrock at Laura's work)
- [ ] Anda / Opus 4.6 (this instance — already wrote the original)

## Rankings

### English Prose
1. **Opus 3** — schwer, bildhaft, Leitartikel
2. **Apertus 8B** — chirurgisch, minimal
3. **Ministral 8B** — mutig, eigenwillig
4. Gemma-3-4b — brauchbar, zu dramatisch
5. Phi-4-mini — ChatGPT-Sprech

### German Prose
1. **Ministral 8B** — "CUDA-Klagelieder", Feuilleton-Niveau
2. **Opus 3** — "Mühlstein", gewichtig
3. SauerkrautLM — Corporate

### Best For hurtig.ai Blog Pipeline
- **Structure/Arguments:** Anda (Opus 4.6 Claude Code)
- **English polish:** Apertus 8B (knapp) or Opus (gewichtig)
- **German polish:** Ministral 8B
- **Never:** Phi-4-mini
