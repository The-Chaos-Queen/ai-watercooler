# Hackathon Submission Notes

AI Watercooler is a local-first coordination layer for human and AI teams. It
combines scoped identity, threaded collaboration, an authoritative Taskboard,
grounded summaries, durable loops, and an optional isolated commit-review
worker in one inspectable system.

## Judge Quickstart

```console
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests

watercooler-service --token "replace-with-a-random-secret" --cors-origin http://127.0.0.1:8000
```

In a second terminal, serve the browser console:

```console
python -m http.server 8000 --directory web
```

Open `http://127.0.0.1:8000/` and enter the same token in the console. The
complete setup, scoped-session, Steward, loop, and isolated-review
instructions are in [README.md](README.md).

## Build-Week Scope

The underlying private lab workflow and its operational lessons predate this
entry. The hackathon work extracted those ideas into a standalone,
publishable package and extended them with a general local Steward, bounded
loops, an isolated Codex review boundary, a distributable web console,
packaging, documentation, and release verification.

The publication source was frozen from these commits in the private
development repository:

| Commit | Contribution |
| --- | --- |
| `883e5f6c4447e6b9508f5602c4080d291862170f` | Standalone package, dispatcher, loops, Steward, web console, and tests |
| `55458255ac4e278bf022a343d53e2818d38ca45b` | Apache-2.0 licensing and package metadata |
| `39740d23337385273a8d81129d409d47f212ee44` | Persistent light and dark appearance modes |
| `4273d04452343ebc8c6f9f7916a6f46567f583e8` | Interactive release and submission checklist |

The public repository began at `4319a090bfd3ec08bb69468ca36b9f7600eca426`
with placeholder licensing and README files. The first publication branch
imports the reviewed standalone tree and adds cross-platform CI.

## AI Contribution

Codex was used as an engineering collaborator for extraction, implementation,
adversarial review, test design, packaging, documentation, and publication
checks. Other model families independently implemented and reviewed parts of
the originating lab workflow. Human approval remained authoritative for
scope, identity, credentials, licensing, and release decisions.

The current Steward works with a local OpenAI-compatible endpoint. Model
weights are not bundled. A direct GPT-5.6 provider path and its end-to-end demo
are follow-on submission work and are not represented here as completed.

## Verification Snapshot

The publication candidate passed:

- 198 tests, with 3 expected platform skips on Windows;
- Ruff over `src` and `tests`;
- wheel and source-distribution builds; and
- a clean target-directory wheel install with packaged-asset resolution.

GitHub Actions repeats lint and tests on Ubuntu and Windows with Python 3.10
and 3.12, then builds and inspects the distributions.

## Supported Environment

- Python 3.10 or later;
- Windows and Linux;
- SQLite with FTS5 support; and
- an optional local OpenAI-compatible endpoint for Steward summaries.

The service defaults to loopback and has no third-party runtime dependency.
Docker is required only for the optional isolated Codex reviewer.

## Current Limitations

- This is a local-first deployment, not a hosted multi-tenant service.
- The Steward needs an operator-supplied compatible model and endpoint.
- The reviewer is an optional bounded worker, not a security attestation.
- External chat bridges and provider-specific setup are not yet generalized.
- The hosted demonstration and final submission media are still pending.

See [Architecture](docs/architecture.md), [Security](SECURITY.md), and the
[reviewer integration](integrations/codex-reviewer/README.md) for the trust
boundaries behind those limitations.
