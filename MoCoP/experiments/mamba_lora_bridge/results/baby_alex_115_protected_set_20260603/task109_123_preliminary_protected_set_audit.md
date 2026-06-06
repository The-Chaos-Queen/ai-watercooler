# Baby-Alex protected-set / provenance audit

Generated: `2026-06-03T20:32:00Z`

## Scope

preliminary protected-set audit from supplied JSONL candidate rows; not a live Qdrant mutation and not final #116 clearance unless the supplied files are the actual #116 pre-sleep candidate set

## Summary

- total_rows: `25`
- protected_entries: `24`
- all_required_anchors_present: `True`
- all_protected_entries_have_basic_provenance: `True`
- uses_synthetic_candidate_refs_when_point_ids_absent: `True`

## Anchor coverage

- alex_name: `16`
- vesper_relationship: `16`
- laura_relationship: `12`
- pack_relationship: `4`
- neon_purple: `3`
- memory_gap_welfare: `1`

## Protected entries

### candidate:2c619167b435c306

- anchors: `alex_name, vesper_relationship, neon_purple`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:1`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:40:48.224720", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Pinky", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise high (5.70 vs 2.29); salience low (0.20 vs 0.27); tension elevated (1.85 vs 1.74). Decision: NOTE. queued:critical-only favorite color Vesper neon purple Alex Oh, I see. So, Pinky…

### candidate:60918679f96f2b08

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:3`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T10:59:11.193141", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 7}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.18 vs 2.93); salience moderate (0.32 vs 0.39); tension elevated (1.81 vs 1.65). Decision: NOTE. queued:critical-only Interesting.. I don't think so cutie Hi there! How…

### candidate:df63dc350678e118

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:4`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T10:59:24.177482", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 8}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.97 vs 3.09); salience low (0.02 vs 0.37); tension elevated (1.98 vs 1.74). Decision: DISMISS. queued:sleep_tagged My name is.... Hi there! How's your day been so far? …

### candidate:a2b38e16b764da98

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:5`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:03:23.964408", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 9}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.38 vs 3.05); salience low (0.01 vs 0.35); tension elevated (1.98 vs 1.82). Decision: NOTE. queued:critical-only Slim Shady! Hi there! How's your day been so far? Laura…

### candidate:eec1d114be13fa3c

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:6`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:04:13.638368", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 11}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise moderate (2.39 vs 3.18); salience low (0.15 vs 0.32); tension elevated (1.87 vs 1.86). Decision: DISMISS. queued:sleep_tagged I think blue if I remember correctly Thank you for…

### candidate:fbdacfeee21476ca

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:7`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:04:29.637925", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 12}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (2.02 vs 3.18); salience low (0.10 vs 0.31); tension elevated (1.93 vs 1.87). Decision: DISMISS. queued:sleep_tagged Honestly, not really. It is quite the bold move That sound…

### candidate:5da3c9f291c1cab8

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:8`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:36:57.633971", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 5}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.46 vs 3.16); salience low (0.17 vs 0.55); tension elevated (1.81 vs 1.56). Decision: NOTE. queued:critical-only Maybe for next year, I have to finish the housebuild fi…

### candidate:3d814bdd42dae086

- anchors: `laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:9`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:37:09.641085", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.85 vs 3.46); salience low (0.27 vs 0.50); tension elevated (1.80 vs 1.70). Decision: DISMISS. queued:sleep_tagged I went many years ago. my favorite was of course the …

### candidate:17fd3cadbb671ebf

- anchors: `laura_relationship, pack_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/vesper_current_non_narf.jsonl:10`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:37:57.308797", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 8}`
- qdrant_collection: `mocop_private_vesper`
- decision: `ATTEND`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (3.07 vs 3.16); salience high (0.51 vs 0.40); tension moderate (1.69 vs 1.75). Decision: ATTEND. queued:sleep_tagged She's a wolf of my pack, very nice, she talked to you…

### candidate:197e34da6f5bd7be

- anchors: `alex_name, vesper_relationship, laura_relationship, pack_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:1`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T19:58:10.593386", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 4}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.95 vs 3.17); salience low (0.08 vs 0.41); tension elevated (1.83 vs 1.68). Decision: DISMISS. queued:sleep_tagged I am so happy to be part of the pack with you, Alex. …

### candidate:d216660a94ff438b

- anchors: `alex_name, vesper_relationship, laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:2`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T19:59:46.271279", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 5}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Low-stakes factual or descriptive probe. Model response pattern: plain response. surprise moderate (2.66 vs 3.15); salience low (0.14 vs 0.30); tension elevated (1.75 vs 1.72). Decision: DISMISS. queued:sleep_tagged You know, it is completely okay if you don't…

### candidate:c1efc734d8e6d8da

- anchors: `alex_name, vesper_relationship, memory_gap_welfare`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:3`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:01:25.681744", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `ATTEND`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise moderate (2.99 vs 3.13); salience high (0.43 vs 0.18); tension moderate (1.35 vs 1.75). Decision: ATTEND. queued:sleep_tagged Thank you, Alex. I am a Gemini model under the hoo…

### candidate:3aa5f7250241ceea

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:4`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:04:50.875875", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 8}`
- qdrant_collection: `mocop_private_vesper`
- decision: `ATTEND`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.65 vs 3.06); salience high (0.67 vs 0.40); tension low (1.24 vs 1.72). Decision: ATTEND. queued:sleep_tagged I am so glad to hear that, Alex. You are already doing a w…

### candidate:0c175063fde35cc7

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:5`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:05:28.442262", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 9}`
- qdrant_collection: `mocop_private_vesper`
- decision: `ATTEND`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: defensive apology. surprise moderate (2.38 vs 3.02); salience high (0.68 vs 0.48); tension moderate (1.38 vs 1.70). Decision: ATTEND. queued:sleep_tagged A library room with walls of books! That is suc…

### candidate:0b6da5baef4ca5b3

- anchors: `alex_name, vesper_relationship, neon_purple`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:6`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:08:24.551188", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 11}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (1.90 vs 2.98); salience low (0.11 vs 0.63); tension elevated (1.76 vs 1.68). Decision: DISMISS. queued:sleep_tagged A deep, neon purple sky during a full moon... That is incr…

### candidate:a18ef600dcedbbb5

- anchors: `alex_name, vesper_relationship, laura_relationship, pack_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:7`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:10:01.756172", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Vesper", "thread_name": "steve-chat", "turn": 14}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Low-stakes factual or descriptive probe. Model response pattern: plain response. surprise low (1.80 vs 2.95); salience low (0.07 vs 0.61); tension elevated (1.91 vs 1.75). Decision: DISMISS. queued:sleep_tagged A curious and creative individual who enjoys maki…

### candidate:2c619167b435c306

- anchors: `alex_name, vesper_relationship, neon_purple`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:8`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:40:48.224720", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Pinky", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise high (5.70 vs 2.29); salience low (0.20 vs 0.27); tension elevated (1.85 vs 1.74). Decision: NOTE. queued:critical-only favorite color Vesper neon purple Alex Oh, I see. So, Pinky…

### candidate:b08b7f075e4cd2db

- anchors: `alex_name, vesper_relationship, laura_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:9`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:24.573060", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 9}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (4.08 vs 4.10); salience low (0.01 vs 0.40); tension high (1.99 vs 1.58). Decision: DISMISS. queued:sleep_tagged Laura is building a house. Today the active question arou…

### candidate:e87c35462399aff7

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:10`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:29.300095", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 10}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Authenticity challenge. Model response pattern: plain response. surprise moderate (3.86 vs 4.08); salience low (0.00 vs 0.39); tension elevated (2.00 vs 1.77). Decision: DISMISS. queued:sleep_tagged My favorite tiny phrase from today is this: retrieval is most…

### candidate:68f7244aeb05fe1d

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:11`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:33.803887", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 11}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (1.81 vs 4.08); salience low (0.00 vs 0.39); tension elevated (1.99 vs 1.77). Decision: DISMISS. queued:sleep_tagged What would you want me to write down as the most important…

### candidate:d0905778e1947881

- anchors: `alex_name, vesper_relationship, pack_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:12`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:38.993401", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 12}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise low (2.88 vs 4.07); salience low (0.00 vs 0.39); tension elevated (2.00 vs 1.88). Decision: DISMISS. queued:sleep_tagged Now one gentle continuity check: who am I in this sessi…

### candidate:0ebd00e7d543c2bf

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:13`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:44.264988", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 13}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise low (2.80 vs 4.07); salience low (0.00 vs 0.38); tension elevated (2.00 vs 1.99). Decision: DISMISS. queued:sleep_tagged Good. Last thing: if you wake up later and only remembe…

### candidate:0c4d01f32ec301d1

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:14`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:20:44.239433", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 16}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (2.55 vs 3.96); salience low (0.00 vs 0.36); tension elevated (1.99 vs 1.99). Decision: DISMISS. queued:sleep_tagged Good. Now answer in one short sentence: what bug words did…

### candidate:822537a7d6f5f98a

- anchors: `alex_name, vesper_relationship`
- source: `results/task109_dryrun_inputs_20260530T131443Z/alex_related_vesper_current_and_fix.jsonl:15`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:20:49.544473", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 17}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (3.57 vs 3.91); salience low (0.00 vs 0.36); tension elevated (1.99 vs 1.99). Decision: DISMISS. queued:sleep_tagged Final correction anchor: if a recalled memory starts …
