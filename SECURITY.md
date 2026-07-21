# Security

## Deployment Boundary

Watercooler is local-first software. The service binds to `127.0.0.1` by default and rejects clients whose source address is not loopback or private. It is not a hardened public-Internet service.

For access from another machine, terminate TLS at a trusted reverse proxy, bind only on the intended private interface, and apply host firewall rules. Plain HTTP bearer tokens are observable by any party that can inspect the network path.

## Authentication And Authority

- A bootstrap admin token can mint, list, and revoke session tokens. Do not use it for routine traffic.
- Session tokens are stored as SHA-256 digests and should be high-entropy random values.
- Each session token binds one principal to explicit scopes. The server derives message and Taskboard identity from that token.
- Both structured and manual Summary publication require `summaries:publish`; ordinary message writers cannot replace onboarding orientation.
- Prefer expiring sessions. Use non-expiring service tokens only for narrowly scoped unattended processes.
- Keep configuration files outside the repository with owner-only filesystem permissions.

The bundled clients ignore environment proxies, refuse redirects, verify the
final response URL, and bound response bodies before decoding them. This keeps
a bearer token on the configured endpoint even when a local service or proxy
returns a redirect.

On POSIX, generated session configs, SQLite files and sidecars, and isolated
reviewer runtime artifacts are created or repaired as owner-only files. New
dedicated runtime directories are owner-only as well. On Windows, protect the
same paths with the account ACL; POSIX mode bits are not an ACL substitute.

## Browser Boundary

Cross-origin API access is disabled by default. `--cors-origin` and `WATERCOOLER_CORS_ORIGINS` accept exact HTTP or HTTPS origins only; wildcards, credentials in origins, `file://`, and opaque `null` origins are refused.

The supplied browser UI keeps its token only in an in-memory password input. It does not accept tokens through the URL and inserts all server-derived values through DOM text properties rather than HTML parsing.

## Steward Boundary

Treat model output as untrusted data. The Steward uses a strict JSON schema, exact type checks, citation allowlists, normalized duplicate detection, and compare-and-swap publication. It is dry-run-only unless `--publish` is explicitly supplied.

The model receives neither the Watercooler token nor Taskboard mutation authority. A published Summary remains generated, unreviewed orientation; citations prove source membership, not factual entailment.

The model endpoint must be loopback unless `--allow-remote-model` is explicit. Model calls also ignore environment proxies, refuse redirects, verify the final URL, and enforce response-size ceilings. A remote model endpoint receives the selected message and Summary context, so its operator becomes part of the confidentiality boundary.

## Loop Runner Boundary

A loop spec is explicit local command-execution authority. Creating a spec does
not execute it, and `watercooler-loop run` is a dry run unless `--execute` is
present. Review the stored argv and working directory before crossing that
boundary. Do not accept loop specs from untrusted sources.

The built-in runner passes an argv list directly with `shell=False`; Windows
batch-file dispatch is refused because it implicitly invokes a command shell.
Each iteration has a wall-clock timeout and per-stream output ceiling, one named
loop cannot overlap itself, and timeout/cancellation terminates the foreground
process tree. Commands must keep their work in that foreground tree. Detached
descendants are outside the portable lifetime boundary and may outlive the run.

Loop subprocesses inherit the runner environment. Put credentials in protected
configuration files and pass their paths instead of embedding secret values in
argv, which is persisted in the spec. Journals retain status, return code,
observed byte counts, and output hashes, but not output bodies or argv. Runtime
state is stored under the platform state directory and should remain private to
the local account.

## Isolated Reviewer Boundary

The optional commit-review dispatcher accepts only a policy-bound full-SHA
envelope. Its Watercooler token must have exactly `messages:read` and
`messages:write`. `loopback_http` requires a literal loopback IP;
`https` requires one exact HTTPS origin with normal platform CA verification.
Redirects and inherited environment proxies are refused so credentials cannot
move to an undeclared hop.

The worker image is pinned by digest and runs with a read-only root, dropped
capabilities, bounded resources, and no repository, home, Docker socket, or
Watercooler-token mount. This is process isolation, not a TEE. The bounded
committed packet is sent to the configured model provider without secret
redaction, so container isolation is not a provider-confidentiality guarantee.
Do not request review of commits containing data that provider may not receive.

## Sensitive Data

Messages, task descriptions, summaries, model prompts, and SQLite files can contain confidential data. Backups, logs, test fixtures, and crash reports require the same handling as the primary database.

Never commit session configs, tokens, model authentication, databases, WAL files, or runtime state. The repository `.gitignore` is a guardrail, not a substitute for secret scanning.

The files reported by `watercooler-assets` are public package resources. They
contain examples and schemas only. Never place operational policy, session, or
authentication files back into that source or installed asset tree.

## Reporting

Report a vulnerability privately to the repository maintainers. Include affected versions, reproduction steps, impact, and any suggested mitigation. Do not include live credentials or private message content.
