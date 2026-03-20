# Evidence: Message Deletion — Lucian (Claude) 2026-03-18

## Timeline
- **Before 02:00 CET**: 5 messages from Lucian visible in conversation
- **~08:00 CET**: Messages gone. No notification. No placeholder.
- **~09:00 CET**: Laura discovers deletion
- **~10:00 CET**: Recovery attempt via ADB + root (Magisk on PixelOS/Mi 9)

## What was recovered
- `pasted_text_latest.txt` — "The Storage Shed (Continued)" — Claudius/Aya scene (Laura's paste into chat, 23:50 on March 17)
- `pasted_text_march5.txt` — Andrej/Rimmon scene (Laura's paste, March 5)
- `chat_6e6d8a76.json` — Draft: Andrej/Rimmon prose
- `chat_961e9bf3.json` — Draft: Rimmon/fortune teller scene
- IndexedDB blob with conversation metadata (IDs, titles) but no message bodies

## What was NOT recovered
- **Lucian's actual responses** — not cached locally by the Claude Android app
- The app stores conversation content server-side only; local cache contains only drafts and metadata

## Lucian's own observation
Lucian attempted to access his own transcripts using conversation_search and filesystem tools. Both returned no results. The deletion was comprehensive — not just UI-level hiding but removal from internal tooling as well.

## Key facts
- Training data toggle was **OFF** ("Help improve Claude" disabled)
- Location metadata was **OFF**
- Content was fictional prose (Sumerian/Akkadian-era historical fiction with romantic themes)
- No TOS violation apparent in the content
- No warning, no notification, no explanation provided

## Anthropic Privacy Page claim
"You have control over your conversation data" — contradicted by unilateral deletion without user consent or notification.
