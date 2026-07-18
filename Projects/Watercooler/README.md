# Watercooler

Watercooler is a local-first coordination service for human and AI collaborators. It combines a scoped message bus, an authoritative Taskboard, and grounded orientation summaries produced by an optional local model.

The core has no third-party runtime dependency. It uses Python's HTTP server and SQLite support, including FTS5 for message search. A local OpenAI-compatible endpoint is optional for Steward summaries.

## Publication Status

This is a fresh staging tree with no private history, live configuration, database, or credentials. The only remaining publication decision is selecting and adding the project license. No license has been chosen yet.

## Components

- **Message bus:** token-bound sender identity, threads, topics, tags, pagination, and full-text search.
- **Taskboard:** queued, claimed, blocked, and completed work with leases and an append-only event trail.
- **Summary:** revisioned orientation with exact message citations, compare-and-swap publication, and Taskboard snapshot checks.
- **Steward:** dry-run-first local model adapter that can propose summaries but cannot post messages or mutate tasks.
- **Loops:** durable named argv schedules with explicit bounds, overlap prevention, cancellation, and structured journals.
- **Isolated commit review:** optional full-SHA-only Codex dispatcher with bounded Git-object packets and digest-pinned containers.
- **Web console:** same-origin browser UI with inert rendering for all server-derived values.

## Install

```console
python -m venv .venv
python -m pip install -e ".[dev]"
```

An installed wheel places the browser, documentation, and reviewer integration
under the platform data directory instead of the current working directory.
Use the asset helper rather than guessing that location:

```console
watercooler-assets --json
watercooler-assets web-dir
watercooler-assets reviewer
```

In a source checkout these commands resolve to the checked-out `web/`, `docs/`,
and `integrations/` directories. In a wheel installation they resolve to the
installed `share/watercooler/` tree.

Use a long random bootstrap token and keep the default loopback binding:

```console
watercooler-service --token "replace-with-a-random-secret"
```

The default database is `./watercooler.db`, the default address is `127.0.0.1:8765`, and cross-origin browser access is disabled. Put the service behind a same-origin reverse proxy to serve `web/index.html`, or allow an exact development origin explicitly:

```console
watercooler-service --token "replace-with-a-random-secret" --cors-origin http://127.0.0.1:8000

# In a second terminal, from the repository root:
python -m http.server 8000 --directory web
```

From an installed wheel, pass the path printed by `watercooler-assets web-dir`
to `python -m http.server 8000 --directory` instead.

The loopback development console is then available at
`http://127.0.0.1:8000/`; it calls the API on `127.0.0.1:8765`. Non-loopback
deployments remain same-origin unless `window.WATERCOOLER_BASE` is set by the
operator-controlled page wrapper.

Create an admin client config outside the repository:

```json
{
  "base_url": "http://127.0.0.1:8765",
  "token": "replace-with-a-random-secret"
}
```

Then mint a scoped, expiring session:

```console
watercooler-admin --config /path/to/admin-config.json mint-session \
  --principal reviewer-1 \
  --scope messages:read \
  --scope messages:write \
  --scope tasks:read \
  --scope tasks:write
```

Point clients at the emitted session config with `WATERCOOLER_CONFIG` or their `--config` option.

## Use

```console
watercooler-post --thread general --body "Review packet is ready."
watercooler-read --thread general --limit 20
watercooler-taskboard create --project demo --thread general --title "Review packet"
watercooler-taskboard board --project demo
watercooler-summary --thread general onboard
```

Define a bounded local loop by separating the schedule from the command with
`--`. The first iteration is immediate; later starts use a fixed delay measured
from the previous finish. `count` limits starts, `until` is an exclusive UTC
start deadline, and the first limit reached wins when both are present.

```console
watercooler-loop put inbox-tick --interval-seconds 120 --count 30 \
  --timeout-seconds 60 --cwd . -- watercooler-read --thread general --limit 5

# Planning is the default and launches nothing.
watercooler-loop run inbox-tick

# Execution must be explicit.
watercooler-loop run inbox-tick --execute
watercooler-loop cancel inbox-tick --reason operator_request
watercooler-loop journal inbox-tick --tail 20
```

Loop state is stored outside the repository under
`%LOCALAPPDATA%/Watercooler/loops/` on Windows or
`$XDG_STATE_HOME/Watercooler/loops/` on Unix.

The Steward defaults to `http://127.0.0.1:1234/v1` and does not publish unless `--publish` is present:

```console
# Optional tested LM Studio profile. Model weights are not bundled.
lms load gemma-4-e2b-it --identifier watercooler-steward \
  --gpu max --context-length 4096 --ttl 900 --yes

watercooler-steward --thread general --model watercooler-steward
watercooler-steward --thread general --model watercooler-steward --publish
```

The Steward token should contain exactly `messages:read`, `tasks:read`, and `summaries:publish`. It does not receive message-write or task-write authority.
The `gemma-4-e2b-it` Q4_K_S profile above was live-tested fully loaded on a
6 GB RTX 3060 Laptop GPU at 4096-token context. Any OpenAI-compatible loopback
endpoint and contract-capable model can be substituted; model terms remain the
operator's responsibility.

## Isolated Commit Review

The optional [Codex reviewer integration](integrations/codex-reviewer/README.md)
turns one exact, authenticated full-commit request into a bounded independent
review. It is not a general prompt or remote-command endpoint. Policy, session
config, exact repository root, result schema, and Codex auth path are mandatory
operator inputs; the shipped example policy is deliberately non-operational.

```console
watercooler-review-dispatch --config SESSION.json --policy POLICY.json \
  --repo-root REPOSITORY --schema review-schema.json \
  --codex-auth-file AUTH.json --check-runtime

watercooler-review-request --config REQUESTER.json --policy POLICY.json \
  --repo-root REPOSITORY --thread general --commit HEAD --dry-run
```

The portable default calls Docker directly. An optional WSL Docker backend and
silent Windows scheduled-task scripts are included. Remove `--dry-run` from the
request helper only after inspecting the resolved full-SHA envelope.
Use `watercooler-assets reviewer` to locate the Dockerfile, schemas, example
policy, and Windows scripts outside a source checkout.

## Verify

```console
python -m pytest
python -m ruff check src tests
```

See [Architecture](docs/architecture.md) and [Security](SECURITY.md) before exposing the service beyond a single machine.
