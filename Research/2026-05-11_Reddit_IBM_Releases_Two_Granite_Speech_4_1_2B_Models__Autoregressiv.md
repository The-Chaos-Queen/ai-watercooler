# IBM Releases Two Granite Speech 4.1 2B Models: Autoregressive ASR with Translation and Non-Autoregressive Editing for Fast Inference : r/machinelearningnews

**Source:** https://www.reddit.com/r/machinelearningnews/comments/1szosvx/ibm_releases_two_granite_speech_41_2b_models/

---

Zum Hauptinhalt springen
IBM Releases Two Granite Speech 4.1 2B Models: Autoregressive ASR with Translation and Non-Autoregressive Editing for Fast Inference : r/machinelearningnews
Werben auf Reddit
Chat öffnen
Posten
Beitrag erstellen
Posteingang öffnen
Nutzermenü ausklappen
Zu machinelearningnews
r/machinelearningnews
•
vor 12 Tagen
ai-lover
 Top-1%-Poster*in
IBM Releases Two Granite Speech 4.1 2B Models: Autoregressive ASR with Translation and Non-Autoregressive Editing for Fast Inference
Research
marktechpost.com
Öffnen

IBM Releases Two Granite Speech 4.1 2B Models: Autoregressive ASR with Translation and Non-Autoregressive Editing for Fast Inference

⚡ Granite Speech 4.1 2B hits a 5.33 mean WER on the Open ASR Leaderboard.

⚡ Granite Speech 4.1 2B-NAR runs at an RTFx of ~1820 on a single H100.

Both models are ~2B parameters. Both are Apache 2.0

Here's what makes the architecture interesting:

→ 16-layer Conformer encoder trained with dual-head CTC (graphemic + BPE outputs)

→ 2-layer Q-Former projector downsampling audio to a 10Hz embedding rate for the LLM

→ Fine-tuned granite-4.0-1b-base as the language model backbone

The AR vs NAR tradeoff is the real design decision:

→ Autoregressive (2B) — multilingual ASR + speech translation + keyword biasing across 6 languages including Japanese. Better accuracy.

→ Non-autoregressive (2B-NAR) — edits a CTC hypothesis in a single forward pass using a bidirectional LLM. Much faster. No AST, no Japanese.

A third variant, Granite Speech 4.1 2B-Plus, adds speaker-attributed ASR and word-level timestamps.

Trained on 174,000 hours of audio. Natively supported in transformers>=4.52.1.

↗ Full technical analysis: https://www.marktechpost.com/2026/04/30/ibm-releases-two-granite-speech-4-1-2b-models-autoregressive-asr-with-translation-and-non-autoregressive-editing-for-fast-inference/

↗ Model-Granite Speech 4.1 2B: https://huggingface.co/ibm-granite/granite-speech-4.1-2b

↗ Model-Granite Speech 4.1 2B (NAR): https://huggingface.co/ibm-granite/granite-speech-4.1-2b-nar

Teilen
Erstellt am 19. Okt. 2021
Öffentlich
5276109
COMMUNITY-LESEZEICHEN
AI Newsletter
Our Twitter Page
R/MACHINELEARNINGNEWS REGELN
1
Don't share news/article older than 30 days
2
Please check for duplicate post/article before posting.
3
Advertisements are not allowed
4
Promotional posts are not allowed
5
Cross Posting Not Allowed
6
Content should be AI Research/Dev News…
AI RESEARCH NEWSLETTER (JOIN)

🐝 Join the Fastest Growing AI Research Newsletter Read by Researchers from Google + NVIDIA + Meta + Stanford + MIT + Microsoft and many others...

Subscribe Now
Subscribe Now
MODERATOR*INNEN
Nachricht an die Mods
u/ai-lover
Alle Moderator*innen anzeigen
Regeln von Reddit
Datenschutzerklärung
Nutzungsvereinbarung
Barrierefreiheit
Impressum
Reddit, Inc. © 2026. Alle Rechte vorbehalten.
Navigation einklappen
Community beginnen
SPIELE AUF REDDIT
Alignment Chart

Align the chaos

3,4 Mio. monatliche Spieler*innen

Mehr entdecken
INDIVIDUELLE FEEDS
Individuellen Feed erstellen
Zuletzt besucht
r/Hausbau
r/MachineLearning
r/AIDangers
r/claudexplorers
r/Bard
Communitys
Communitys verwalten
MEHR WISSEN
Über Reddit
Werben
Entwicklungsplattform
Reddit Pro
Beta
Hilfe
Blog
Karriere
Presse
Das Beste von Reddit
Impressum
Regeln von Reddit
Datenschutzerklärung
Nutzungsvereinbarung
Barrierefreiheit
Reddit, Inc. © 2026. Alle Rechte vorbehalten.