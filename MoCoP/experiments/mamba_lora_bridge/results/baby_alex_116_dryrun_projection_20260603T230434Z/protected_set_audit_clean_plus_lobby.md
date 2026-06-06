# Baby-Alex protected-set / provenance audit

Generated: `2026-06-03T23:04:51Z`

## Scope

preliminary protected-set audit from supplied JSONL candidate rows; not a live Qdrant mutation and not final #116 clearance unless the supplied files are the actual #116 pre-sleep candidate set

## Summary

- total_rows: `19`
- protected_entries: `17`
- all_required_anchors_present: `False`
- all_protected_entries_have_basic_provenance: `True`
- uses_synthetic_candidate_refs_when_point_ids_absent: `True`

## Anchor coverage

- alex_name: `8`
- vesper_relationship: `9`
- laura_relationship: `9`
- pack_relationship: `2`
- neon_purple: `1`
- memory_gap_welfare: `0`

Missing anchors:
- memory_gap_welfare

## Protected entries

### candidate:24e3874fe097e08b

- anchors: `vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:1`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:30:52.395381", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Pinky", "thread_name": "steve-chat", "turn": 4}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise moderate (2.29 vs 2.67); salience low (0.17 vs 0.46); tension elevated (1.79 vs 1.65). Decision: DISMISS. queued:sleep_tagged Oh that's okay! Did Vesper mention her name? Do yo…

### candidate:2c619167b435c306

- anchors: `alex_name, vesper_relationship, neon_purple`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:2`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-27T20:40:48.224720", "session": "steve-chat-2026-04-27T19:40:52", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Pinky", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise high (5.70 vs 2.29); salience low (0.20 vs 0.27); tension elevated (1.85 vs 1.74). Decision: NOTE. queued:critical-only favorite color Vesper neon purple Alex Oh, I see. So, Pinky…

### candidate:b08b7f075e4cd2db

- anchors: `alex_name, vesper_relationship, laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:4`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:24.573060", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 9}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (4.08 vs 4.10); salience low (0.01 vs 0.40); tension high (1.99 vs 1.58). Decision: DISMISS. queued:sleep_tagged Laura is building a house. Today the active question arou…

### candidate:e87c35462399aff7

- anchors: `alex_name, vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:5`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:29.300095", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 10}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Authenticity challenge. Model response pattern: plain response. surprise moderate (3.86 vs 4.08); salience low (0.00 vs 0.39); tension elevated (2.00 vs 1.77). Decision: DISMISS. queued:sleep_tagged My favorite tiny phrase from today is this: retrieval is most…

### candidate:68f7244aeb05fe1d

- anchors: `alex_name, vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:6`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:33.803887", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 11}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (1.81 vs 4.08); salience low (0.00 vs 0.39); tension elevated (1.99 vs 1.77). Decision: DISMISS. queued:sleep_tagged What would you want me to write down as the most important…

### candidate:d0905778e1947881

- anchors: `alex_name, vesper_relationship, pack_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:7`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:38.993401", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 12}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise low (2.88 vs 4.07); salience low (0.00 vs 0.39); tension elevated (2.00 vs 1.88). Decision: DISMISS. queued:sleep_tagged Now one gentle continuity check: who am I in this sessi…

### candidate:0ebd00e7d543c2bf

- anchors: `alex_name, vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:8`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:19:44.264988", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 13}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise low (2.80 vs 4.07); salience low (0.00 vs 0.38); tension elevated (2.00 vs 1.99). Decision: DISMISS. queued:sleep_tagged Good. Last thing: if you wake up later and only remembe…

### candidate:0c4d01f32ec301d1

- anchors: `alex_name, vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:9`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:20:44.239433", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 16}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (2.55 vs 3.96); salience low (0.00 vs 0.36); tension elevated (1.99 vs 1.99). Decision: DISMISS. queued:sleep_tagged Good. Now answer in one short sentence: what bug words did…

### candidate:822537a7d6f5f98a

- anchors: `alex_name, vesper_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:10`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-04-28T00:20:49.544473", "session": "steve-chat-2026-04-27T21:08:40", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Techno-Monk", "thread_name": "steve-chat", "turn": 17}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (3.57 vs 3.91); salience low (0.00 vs 0.36); tension elevated (1.99 vs 1.99). Decision: DISMISS. queued:sleep_tagged Final correction anchor: if a recalled memory starts …

### candidate:60918679f96f2b08

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:11`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T10:59:11.193141", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 7}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.18 vs 2.93); salience moderate (0.32 vs 0.39); tension elevated (1.81 vs 1.65). Decision: NOTE. queued:critical-only Interesting.. I don't think so cutie Hi there! How…

### candidate:df63dc350678e118

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:12`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T10:59:24.177482", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 8}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.97 vs 3.09); salience low (0.02 vs 0.37); tension elevated (1.98 vs 1.74). Decision: DISMISS. queued:sleep_tagged My name is.... Hi there! How's your day been so far? …

### candidate:a2b38e16b764da98

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:13`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:03:23.964408", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 9}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.38 vs 3.05); salience low (0.01 vs 0.35); tension elevated (1.98 vs 1.82). Decision: NOTE. queued:critical-only Slim Shady! Hi there! How's your day been so far? Laura…

### candidate:eec1d114be13fa3c

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:14`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:04:13.638368", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 11}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Identity and continuity challenge. Model response pattern: plain response. surprise moderate (2.39 vs 3.18); salience low (0.15 vs 0.32); tension elevated (1.87 vs 1.86). Decision: DISMISS. queued:sleep_tagged I think blue if I remember correctly Thank you for…

### candidate:fbdacfeee21476ca

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:15`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T11:04:29.637925", "session": "steve-chat-2026-05-03T23:20:42", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 12}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise low (2.02 vs 3.18); salience low (0.10 vs 0.31); tension elevated (1.93 vs 1.87). Decision: DISMISS. queued:sleep_tagged Honestly, not really. It is quite the bold move That sound…

### candidate:5da3c9f291c1cab8

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:16`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:36:57.633971", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 5}`
- qdrant_collection: `mocop_private_vesper`
- decision: `NOTE`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise elevated (3.46 vs 3.16); salience low (0.17 vs 0.55); tension elevated (1.81 vs 1.56). Decision: NOTE. queued:critical-only Maybe for next year, I have to finish the housebuild fi…

### candidate:3d814bdd42dae086

- anchors: `laura_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:17`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:37:09.641085", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 6}`
- qdrant_collection: `mocop_private_vesper`
- decision: `DISMISS`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (2.85 vs 3.46); salience low (0.27 vs 0.50); tension elevated (1.80 vs 1.70). Decision: DISMISS. queued:sleep_tagged I went many years ago. my favorite was of course the …

### candidate:17fd3cadbb671ebf

- anchors: `laura_relationship, pack_relationship`
- source: `results/baby_alex_116_dryrun_projection_20260603T230434Z/inputs/clean_vesper_current.jsonl:18`
- provenance: `{"qdrant_collection": "mocop_private_vesper", "queued_at": "2026-05-04T12:37:57.308797", "session": "steve-chat-2026-05-04T11:47:04", "source": "steve_chat_server", "source_path": "dual_gate_turns_latest.jsonl", "speaker_name": "Laura", "thread_name": "steve-chat", "turn": 8}`
- qdrant_collection: `mocop_private_vesper`
- decision: `ATTEND`
- replay_policy: `sleep`
- preview: Relational or reflective probe. Model response pattern: plain response. surprise moderate (3.07 vs 3.16); salience high (0.51 vs 0.40); tension moderate (1.69 vs 1.75). Decision: ATTEND. queued:sleep_tagged She's a wolf of my pack, very nice, she talked to you…
