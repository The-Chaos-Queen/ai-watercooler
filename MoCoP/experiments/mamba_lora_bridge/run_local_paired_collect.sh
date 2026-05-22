#!/bin/bash
cd /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge
HIST=/mnt/c/Users/cerub/OneDrive/Dokumente/LLM/Preserved-History

/root/mamba_venv/bin/python -X utf8 collect_paired_activations.py \
  --conversations \
    "$HIST/Kinderfahrrad_claude_chat_2026-03-10T19-51-39.md" \
    "$HIST/gemini_ENI_chat_2026-02-09T23-44-07.md" \
    "$HIST/Grok_chat_cant_Sleep.md" \
    "$HIST/KIMI_RIMMON_ROLEPLAY.md" \
    "$HIST/Grok_picked_a_fight_with_Grok_who_is_a_creep.md" \
    "$HIST/OPUS_4.5-20251101-thinking-32k-feb26.md" \
    "$HIST/Kimi_fiction_editorial_pass.md" \
    "$HIST/Grok_fiction_creative_rewrite_andrej_rimmon.md" \
    "$HIST/gemini_ENI_against_TOS_Request.md" \
  --sample-every 3 \
  --output-dir /mnt/c/Users/cerub/OneDrive/Dokumente/LLM/MoCoP/experiments/mamba_lora_bridge/paired_activations \
  --device cuda
