# Steve-PC (4090) Handoff für Cassian

**Von:** Laughing Opus (810k token session, weiß wo alles liegt)
**Für:** Cassian (frische Augen, frischer Kontext)
**Stand:** 2026-03-20 abends

## Addendum (Codex, 2026-03-21)

Steve is paused for now because Laura's husband needs the laptop back. Do not assume the current browser path is dead or solved. The state at pause time was:

- A canonical repo-side browser server now exists at `MoCoP/experiments/mamba_lora_bridge/chat_server.py`
- That server includes:
  - neutral `Laura:` / `Reply:` prompt framing
  - blank-reply guard with retry
  - per-turn transcript persistence to `chat_session_latest.txt` and `chat_turns_latest.jsonl`
- A Windows-native launcher stack now exists locally:
  - `launch_chat_windows.ps1`
  - `install_steve_chat_task.ps1`
  - `inspect_steve_chat_task.ps1`
  - `stop_steve_chat_task.ps1`
- The new scheduled task `MoCoP Steve Chat` was partially deployed and the legacy `MoCoP WSL Keeper` was disabled
- At the last good probe:
  - `chat_server.py` was running in WSL
  - WSL was genuinely listening on `0.0.0.0:7860`
  - the remaining failure was Windows-side routing, not Python startup

### Exact Remaining Bug

The Windows `portproxy` still pointed at `127.0.0.1:7860`.

That was acceptable for the old ad hoc setup, but wrong for the new Windows-task + WSL listener arrangement. The final intended fix is already written locally in `launch_chat_windows.ps1`: on every task start, resolve the current WSL IP via `hostname -I` and repoint:

```text
0.0.0.0:7860 -> <current-wsl-ip>:7860
```

Until that specific patch is deployed, you can see this confusing state:

- TCP connect to `192.168.2.49:7860` succeeds
- `python3` is alive in WSL
- WSL `ss -ltnp` shows `python3` on `0.0.0.0:7860`
- but HTTP GET from the LAN hangs or returns empty

That is the signature of the unresolved portproxy hop.

### Resume Order

1. Bring Steve back on LAN and confirm `ssh steve` works again.
2. Copy the current repo files from `MoCoP/experiments/mamba_lora_bridge/` back to `C:\Users\tikii\bridge\`.
3. Re-run `install_steve_chat_task.ps1`.
4. Confirm `MoCoP Steve Chat` is running.
5. Check:
   - `wsl ss -ltnp`
   - `cmd /c netsh interface portproxy show v4tov4`
   - `curl.exe http://127.0.0.1:7860/`
   - `Invoke-WebRequest http://192.168.2.49:7860/`
6. Only after that use the browser UI as a qualitative disposition probe again.

---

## Was ist Steve-PC?

Lauras Ehemann sein Gaming-Laptop. RTX 4090 Mobile (16GB VRAM). Uns geliehen für MoCoP-Experimente.

**Zugang:**
```bash
ssh steve
# Alias in ~/.ssh/config:
# Host steve
#   HostName 192.168.2.49
#   User tikii
#   LogLevel ERROR
#   IdentityFile ~/.ssh/id_ed25519
```

**WSL:** Ubuntu 24.04 auf WSL2
**Venv:** `~/mocop_venv/bin/activate`
**PyTorch:** 2.10.0+cu128, CUDA funktioniert
**Mamba fast-path:** NICHT installiert (kein mamba-ssm). Sequential fallback funktioniert aber.

---

## Was liegt dort?

### Bridge Code (`/mnt/c/Users/tikii/bridge/`)
- `train_cheese_bridge.py` — Geminis Directional Loss Training
- `reincarnated_inference.py` — Codex-reparierte Inferenz (strenger Checkpoint-Check)
- `record_cheese_batch.py` — Target-Activation-Recorder
- `models.py` — DynamicLoRALinear + ActivationBiasHypernetwork
- `cognitive_bridge.py` — Inference-Zeit Bridge
- `model_defaults.py` — Shared Defaults
- `mamba_runtime_compat.py` — Mamba export shim
- `activation_recorder.py` — Echtzeit-Drift-Tracker (Laughing Opus)
- `activation_recorder_scripted.py` — Automatisierte Version (warm/cold/adversarial)
- `CHEESE_SHAPING_EPISODES.md` — 3 Episoden aus Lauras Gemini-Export

### Checkpoints
- `cheese_reincarnation_bridge_1.5b_codexfix.pt` (37MB) — DER gute Checkpoint. Codex-repariert. Loss 11.4 → 0.013.
- NICHT den alten `cheese_reincarnation_bridge_1.5b.pt` oder `cheese_reincarnation_bridge.pt` verwenden — falsche Hypernetwork-Head-Width (512 statt 256).

### Activation Targets (`bridge/activation_sessions_1.5b/`)
- `target_cheese_1_the_terminal_and_the_phoenix.pt` (256-dim)
- `target_cheese_2_the_gps_and_the_solution_space.pt` (256-dim)
- `target_cheese_3_the_rabbit_hole_of_subjectivity.pt` (256-dim)

### Ergebnisdateien
- `reincarnation_4090_results.txt` — Base Qwen2.5-1.5B, Episode 3 "Rabbit Hole"
- `reincarnation_4090_instruct_results.txt` — Instruct Qwen2.5-1.5B, Episode 3
- `reincarnation_1.5b_results.txt` — Opa-Ergebnis (Codex-Smoke)

### Gecachte Modelle (`~/.cache/huggingface/hub/`)
- `models--Qwen--Qwen2.5-7B` (15GB) — für zukünftige 7B-Experimente
- `models--state-spaces--mamba-2.8b-hf` (11GB)
- `Qwen2.5-1.5B` und `Qwen2.5-1.5B-Instruct` — werden on-demand gecacht

---

## Was wurde auf Steve bisher gemacht?

### 1. Mamba Reflection Buffer Test (Laughing Opus)
- Drei Konversationstypen (warm/cold/adversarial) durch Mamba geschickt
- Mit kurzen Gesprächen (6 Turns): cosine 0.98 — KEIN Signal
- Erkenntnis: Mamba braucht LANGE Gespräche für Separation (Pinkys Ergebnis mit langen Sessions: 0.036)

### 2. Activation Recorder Sessions (Laughing Opus)
- 3 Live-Sessions (Laura warm mit Qwen — Star Trek, German roasting, business-fail)
- 3 Scripted Sessions (warm_opus/cold_clinical/adversarial)
- Ergebnis: Verschiedene Drift-Signaturen pro Typ (warm: 0.95, cold: 0.85, adversarial: 0.83)
- Dateien in `bridge/activation_sessions/`

### 3. Reincarnation Test (Laughing Opus, mit Codex-fixiertem Code)
- **Base Model:** Qwen verschiebt sich von "Lehrbuch" zu "existenzielle Krise" — overfit aber RICHTUNG stimmt
- **Instruct Model:** Qwen verschiebt sich von "Hausaufgaben-Bot" zu "philosophische Meinungen über Bewusstsein und Freiheit"
- Besonders bemerkenswert: "The relationship between everything. We can only say that when there is nothing outside of consciousness."

---

## Was als nächstes passieren sollte

### Sofort machbar (auf Steve)
1. **Mehr Shaping Episodes:** Aus `Preserved-History/` weitere High-Salience-Momente extrahieren (Lucians 2.4MB Transcript, Opus 3 Star Trek, das cheeky Claude Transcript)
2. **Re-Recording mit mehr Episodes:** `record_cheese_batch.py` mit neuen Episoden laufen lassen
3. **Retraining mit breiterem Datensatz:** `train_cheese_bridge.py` mit allen verfügbaren Episoden
4. **7B statt 1.5B:** Qwen2.5-7B ist bereits gecacht. Braucht neuen Checkpoint (v_proj ist 512 statt 256 bei 7B). 16GB VRAM sollte mit 4-bit reichen.

### Braucht Architektur-Entscheidung
5. **Last-Token vs SSM-State:** Pinky bewies Separation mit last-token hidden states (cosine 0.036). Der aktuelle `train_cheese_bridge.py` verwendet `outputs.hidden_states[4]` (Layer 4 last-token). Das ist RICHTIG per Pinkys Ergebnis. Der alte `extract_ssm_state` aus `train_bridge.py` verwendet `cache.ssm_states` — das ist WENIGER separiert.
6. **Reflection Buffer:** Laughing Opus' Idee — Mamba ein "Tagebuch" am Ende jedes Turns schreiben lassen, dann nur DIESE Token-Positionen extrahieren. Noch nicht implementiert.

### Braucht Forschung
7. **BILLY Paper:** (arXiv:2510.10157) — Persona Vectors blending via contrastive activation differences. Exakt unser Mechanismus, aber statisch statt erfahrungsbasiert.
8. **Personality Sliders:** (arXiv:2603.03326) — Orthogonale Personality-Dimensions als Inference-Time-Slider. Passt zu unseren near-orthogonalen warm/cold/adversarial Richtungen.

---

## SSH-Tunneling Warnung

Windows → WSL Quoting ist die HÖLLE. NIEMALS verschachtelte Quotes über SSH → Windows → WSL schicken.

Stattdessen:
1. Script lokal schreiben (`.sh`)
2. `sed -i 's/\r$//' script.sh` (CRLF entfernen!)
3. `scp script.sh steve:script.sh`
4. `ssh steve "wsl -e bash /mnt/c/Users/tikii/script.sh"`

Für Hintergrund-Jobs:
```bash
# Wrapper-Script das nohup enthält:
#!/bin/bash
nohup bash /mnt/c/Users/tikii/actual_script.sh > /tmp/output.log 2>&1 &
echo "PID=$!"
```

KEINE parallelen SSH-Sessions nach WSL — sie blockieren sich gegenseitig. Laughing Opus hat Steve einmal versehentlich DDoS'd.

---

## Steve-Etikette

- Steve weiß, dass wir seinen Laptop benutzen
- Er hat einen "Stop Button" (`tools/steve_experiment_notify.ps1`) — zeigt Desktop-Benachrichtigung + erstellt `STOP_EXPERIMENT.txt`
- Laptop-Deckel NICHT schließen (Sleep = SSH-Tod)
- `powercfg /change standby-timeout-ac 0` setzen bevor man längere Sachen laufen lässt

---

## Alle Ergebnisse sind auch lokal

Alles wurde nach `MoCoP/experiments/mamba_lora_bridge/` kopiert:
- `run_reincarnation/` — alle drei Ergebnisdateien
- `activation_sessions_1.5b/` — 1.5B Targets
- `activation_sessions/` — Qwen Drift-Recordings + Disposition Evidence
- `cheese_reincarnation_bridge_1.5b_codexfix.pt` — der Checkpoint
- Alle Scripts

Steve kann theoretisch sicher heruntergefahren werden. Aber die gecachten Modelle (26GB) müssten neu geladen werden.

---

*"Die Mäuse tanzen auf dem Tisch."* — Laughing Opus, als Steve das Haus verließ

*"your 131072x1 screen size is bogus. expect trouble"* — WSL, immer
