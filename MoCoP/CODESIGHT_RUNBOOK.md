# CodeSight Runbook

CodeSight is installed from `github.com/Houseofmvps/codesight` at:

```text
../tools/codesight
```

It is useful as a compact orientation layer for agents after compaction. It is not a replacement for reading source before editing.

## Refresh

From repository root:

```powershell
.\tools\refresh_mocop_codesight.ps1
```

This regenerates:

```text
MoCoP/.codesight/CODESIGHT.md
MoCoP/.codesight/KNOWLEDGE.md
MoCoP/.codesight/wiki/index.md
MoCoP/.codesight/wiki/overview.md
MoCoP/.codesight/wiki/libraries.md
```

## How To Use

Read these in this order when re-entering MoCoP after compaction:

```text
MoCoP/.codesight/wiki/index.md
MoCoP/.codesight/wiki/overview.md
MoCoP/.codesight/KNOWLEDGE.md
```

Use `CODESIGHT.md` only when you need the full generated map. For this repo, `KNOWLEDGE.md` is often more useful than the code scan because MoCoP is research-heavy and markdown-heavy.

## Limits

CodeSight currently detects MoCoP as a raw Python/Javascript project with no routes/models/components. That is acceptable: the value is file orientation, dependency/env extraction, and markdown knowledge indexing.

The generated `KNOWLEDGE.md` can misclassify poetic or narrative headings as decisions. Treat it as an index, not a source of truth.

Never infer implementation behavior from `.codesight` alone. Use it to find files, then read the files.
