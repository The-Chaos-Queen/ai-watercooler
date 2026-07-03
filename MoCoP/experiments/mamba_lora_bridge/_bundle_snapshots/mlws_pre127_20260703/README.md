# ML-WS bundle snapshot, pre-#127 deploy (2026-07-03)

The models.py, chat_server.py, and reincarnated_inference.py that were live in the ML-WS
runtime bundle (/home/isabell/mocop/mamba_lora_bridge) BEFORE the OpenCLAW #127
(DC-removal + RMS-scaling) deploy overwrote them with the local versions.

Kept because the bundle copies had diverged from the local repo (models.py ~+180/-165
lines, chat_server.py ~+40, beyond the #127 edits; reincarnated_inference.py was in sync).
The divergence is unaccounted for and may hold ML-WS-only changes, so these are preserved
for a deliberate local-vs-bundle reconcile rather than being lost. Backups also remain on
ML-WS as <file>.pre127_20260703_201143.bak.
