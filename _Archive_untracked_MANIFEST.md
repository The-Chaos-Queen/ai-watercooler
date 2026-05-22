# _Archive_untracked Manifest

This is a local triage holding area for files that should leave the active git surface before committing.

The directory `_Archive_untracked/` is intentionally ignored by git. Move files there only when they are clearly generated, runtime-only, temporary, duplicated exports, or historical dumps that should not be part of the active repository.

Do not move active source code, tests, runbooks, specs, canonical memory files, or project documentation unless a human has explicitly reviewed the dependency risk.

Suggested first-pass candidates:

- one-off run outputs and probe JSON files
- raw transcripts or exported chat dumps
- temporary watercooler draft files
- converted research dumps and extraction scratch files
- rotated logs and local runtime artifacts

After moving files, run:

```powershell
git status --short
git ls-files --others --exclude-standard
```

If anything important disappears from the untracked list, move it back before committing.
