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

Other wolves keep uncommitted work in this repo (their lanes). Before running:

1. Run `git status --short` and identify which changed files are YOURS (from this session's work).
   Include files you deleted this session — the snapshot below handles deletions.
2. Only YOUR files go into the snapshot. Never include or act on findings about another wolf's
   uncommitted lane — reviewing their work-in-progress uninvited is lane-sweeping.

## Run (uncommitted changes): scoped ephemeral snapshot

codex 0.144.5 rejects custom instructions alongside `--uncommitted`, and bare `--uncommitted`
sees every wolf's lane. Do NOT commit first to work around this (that turns a pre-commit pass
into a post-commit one). Instead, build an **ephemeral commit object** whose diff against HEAD
is exactly your session's files, and review that. It uses a temporary index — HEAD, the real
index, the working tree, branches, and other wolves' lanes are untouched; the object is
unreachable, never pushed, and git gc prunes it automatically (~2 weeks).

Use Bash (Git Bash syntax), quoting each path:

```bash
cd "$(git rev-parse --show-toplevel)"
tmpidx=$(mktemp)
GIT_INDEX_FILE="$tmpidx" git read-tree HEAD
GIT_INDEX_FILE="$tmpidx" git update-index --add --remove -- "path/to/file1" "path/to/file2"
tree=$(GIT_INDEX_FILE="$tmpidx" git write-tree)
snap=$(git commit-tree "$tree" -p HEAD -m "ephemeral codex-review snapshot (unreferenced)")
rm -f "$tmpidx"
echo "$snap"
```

Then review the snapshot — the commit IS the scope, no scoping prompt needed:

```bash
codex review --commit "$snap" --title "scoped session review" "Focus: <focus notes or 'correctness and unintended side effects'>. Be concise: numbered findings, severity-tagged, no praise padding."
```

If this codex version rejects a prompt alongside `--commit` (client-side argument error — it
costs no quota), rerun without the prompt and apply the focus notes yourself during report-back:

```bash
codex review --commit "$snap" --title "scoped session review"
```

## Run (branch diff)

```bash
codex review --base <branch> "<focus instructions>"
```

(Same prompt-rejection fallback applies: if the CLI refuses the prompt, rerun bare.)

Notes:
- Each call costs Laura's Codex subscription quota (~6k tokens minimum). One review per task,
  not per edit. Never wire this into hooks or loops. A CLI argument error costs nothing;
  retrying after one is fine. Do not retry auth/quota errors — report and stop.
- The snapshot sha is your receipt: it pins exactly what was reviewed. Never create a ref to
  it, never push it.

## Report back

1. Summarize the findings (keep Codex's numbering), each with your own one-line assessment:
   accept / reject-with-reason / needs-check.
2. Label the output clearly: "inline a-Codex review, unattested." For snapshot reviews, cite
   the snapshot sha so the reviewed state is re-derivable (until gc prunes it).
3. If any finding is substantive and the work is board-relevant, note that wolf-Codex on the
   watercooler remains the path for a verdict of record.
