# Isolated Codex Commit Reviewer

This optional integration consumes one strict Watercooler request containing one full lowercase Git SHA-1, builds a bounded packet from immutable Git objects, and asks Codex for a structured code-review second opinion. It is deliberately not a general remote command surface.

In a source checkout this directory is `integrations/codex-reviewer`. After a
wheel install, run `watercooler-assets reviewer` to print the installed
directory containing the Dockerfile, schemas, example policy, and Windows
scripts. Keep every operational copy of the policy and credentials outside that
read-only package asset tree.

The dispatcher accepts only this body, with no additional keys:

```json
{"version":1,"kind":"commit","commit":"0123456789abcdef0123456789abcdef01234567"}
```

Sender, recipient, thread, topic, and the single request tag must match the explicit policy. Short revisions, prose prompts, merge commits, broadcasts, and extra tags fail closed.

## Security Boundary

The worker container receives no host repository, home directory, Docker socket, Watercooler token, or caller-selected prompt. It uses a pinned image digest, read-only root filesystem, dropped capabilities, `no-new-privileges`, bounded resources, temporary filesystems, a read-only Codex auth mount, and one writable result directory.

Container isolation does not make review data local. The bounded commit message, diff, and eligible committed text files are sent to the model provider configured by `model`. There is no secret-redaction pass. Do not submit commits containing credentials or other data that the provider may not receive.

Dispatcher HTTP traffic rejects every redirect and ignores environment proxy settings. The policy supports exactly two transport modes:

- `loopback_http`: requires an `http://` origin using a literal loopback IP such as `127.0.0.1` or `[::1]`.
- `https`: requires an exact `https://` origin and normal platform CA verification.

## Policy Bootstrap

`dispatcher-policy.example.json` is intentionally non-operational. It contains a placeholder model and an all-zero image digest. Copy it to a private state/configuration directory, then set the exact principal, allowlisted senders, threads, model, and endpoint. Never add tokens or Codex credentials to policy JSON.

Keep the dispatcher Watercooler session config separate. Its token must be unexpired and have exactly `messages:read` and `messages:write`. Requester tokens need `messages:write` and must identify an allowlisted principal.

The direct `docker` backend works on Linux, macOS, and Windows with Docker on `PATH`. Windows users may instead select `wsl_docker` and set one explicit WSL distribution. The repository root is always a required argument and must equal Git's exact top-level working tree.

Build and inspect the reviewer image on Windows:

```powershell
.\windows\build-reviewer.ps1 -PolicyPath C:\path\to\private-policy.json -Bootstrap
```

Pin the printed image ID in the private policy, replace the placeholder model, then rerun without `-Bootstrap`. The shipped Codex CLI pin is `0.144.5`.

## Manual Run

Install the project, verify the runtime, and prime the cursor before scheduling normal polling:

```text
python -m watercooler.dispatcher.commit_review --config SESSION.json --policy POLICY.json --repo-root REPOSITORY --schema review-schema.json --codex-auth-file AUTH.json --check-runtime
python -m watercooler.dispatcher.commit_review --config SESSION.json --policy POLICY.json --repo-root REPOSITORY --schema review-schema.json --codex-auth-file AUTH.json --prime
python -m watercooler.dispatcher.commit_review --config SESSION.json --policy POLICY.json --repo-root REPOSITORY --schema review-schema.json --codex-auth-file AUTH.json
```

Create a request locally. The helper resolves `HEAD` or another local revision to the required full SHA before posting:

```text
python -m watercooler.dispatcher.request --config REQUESTER.json --policy POLICY.json --repo-root REPOSITORY --thread general --commit HEAD --dry-run
```

Remove `--dry-run` only after inspecting the exact envelope.

`windows/install-scheduled-task.ps1` is an optional silent Windows scheduler. It requires explicit policy, session, repository, schema, auth, and Python paths; it performs runtime validation and cursor priming before registration. It never searches for a credential or policy file.
