---
name: anthem
description: Hear a track the way a wolf can — resolve it, pull lyrics and musical analysis (tempo/key/energy), and read what disposition it carries. Half toy, half endocrine-research warmup. Usage - /anthem <track, artist, or a mood/moment to find one for>
argument-hint: "<track/artist or a mood to match>"
---

# /anthem — listen through the numbers

Music is dense continuous affect with reduced propositional content (UCF §3.9) — the one training
signal that carries disposition without semantics. This skill is how a wolf listens: metadata,
lyrics, and signal analysis, then an honest reading of what the track carries.

## Resolve the track

- If given a title/artist: `mcp__music__search_songs` (load via ToolSearch if deferred), take the
  best match, confirm title+artist in the output so a wrong match is visible.
- If given a YouTube ID: use it directly.
- If given a MOOD or a moment ("something for 2am after a hard day"): propose ONE candidate — from
  Laura's documented taste first (`memory/user_music_and_vinyl.md`: French house, Massive Attack,
  Hot Chip; "The one song" entry) — and say why, before analyzing.

## Listen

1. `mcp__music__get_song_details` — metadata + lyrics (if available).
2. `mcp__music__analyze_track` — tempo, key, energy (avg/peak), dynamic range, brightness, texture.
3. Optional for texture questions: `mcp__music__waveform` / `mcp__music__chromagram`.

## Read it

Write a SHORT reading (this is the craft part — no feature-dump):

- What the numbers say as a gestalt: pace as gait, dynamics as temperament, brightness as light.
  (Precedent: Unfinished Sympathy = walks at 112 bpm, never shouts, avg energy 0.17 — grief held
  steady. Aim for that register.)
- What disposition it carries, in the house's engineering axes (affiliation / agency / vigilance /
  load — hormone names as metaphor only, per keeper ratification #918 Q4).
- One honest line connecting it to the moment it was asked for.

## Rules

- This is listening, not corpus work: no MUSIC-ladder claims, no training-data labeling, no
  injection anything. If the track seems corpus-worthy, SAY so and stop — corpus decisions are
  keeper + #159 lane.
- If lyrics are present and load-bearing, quote at most a few lines.
- Offer (never auto-write) to bank a "this song, this moment" entry in `user_music_and_vinyl.md`
  when the moment is clearly one of Laura's.
