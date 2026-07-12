---
name: codex-review
description: Get an inline second-opinion code review from the codex CLI (GPT) on uncommitted changes or a branch diff. Use before committing spec/tool changes. Output is "a Codex" (substrate capability, unattested) — never a review of record.
argument-hint: "[focus notes] | base <branch> [focus notes]"
---

# /codex-review — inline second opinion from the codex CLI

Run a non-interactive Codex review of local changes and report its findings. This produces an
ANONYMOUS review ("a Codex" — substrate capability, not wolf-Codex the persona). It is for
pre-commit hygiene and second opinions only. Per house doctrine (01_TOOLS.md §Codex CLI):
GREEN/CHANGES verdicts of record must come from wolf-Codex on the watercooler, with identity
and message ID. Never present this skill's output as an attested review.

## Parse the input

- If the input starts with `base <branch>`: review against that base branch; the rest is focus notes.
- Otherwise: review uncommitted changes (staged + unstaged + untracked); the whole input is focus notes.
- Empty input is fine — review without special focus.

## Multi-tenant guard (IMPORTANT — this repo is a shared working tree)

Other wolves keep uncommitted work in this repo (their lanes). `--uncommitted` sees ALL of it.
Before running:

1. Run `git status --short` and identify which changed files are YOURS (from this session's work).
2. If files you did not touch appear, scope the review via the prompt: name your files explicitly
   and instruct Codex to ignore everything else. Never ask for or act on findings about another
   wolf's uncommitted lane — reviewing their work-in-progress uninvited is lane-sweeping.

## Run

Use Bash (Git Bash syntax), from the repo root:

```bash
codex review --uncommitted "Review ONLY these files: <your files>. Ignore all other changes in the working tree. Focus: <focus notes or 'correctness and unintended side effects'>. Be concise: numbered findings, severity-tagged, no praise padding."
```

or for a branch diff:

```bash
codex review --base <branch> "<same scoping/focus instructions>"
```

Notes:
- Each call costs Laura's Codex subscription quota (~6k tokens minimum). One review per task,
  not per edit. Never wire this into hooks or loops.
- If codex returns an auth or quota error, report it and stop — do not retry in a loop.

## Report back

1. Summarize the findings (keep Codex's numbering), each with your own one-line assessment:
   accept / reject-with-reason / needs-check.
2. Label the output clearly: "inline a-Codex review, unattested."
3. If any finding is substantive and the work is board-relevant, note that wolf-Codex on the
   watercooler remains the path for a verdict of record.
