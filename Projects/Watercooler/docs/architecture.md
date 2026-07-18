# Architecture

## System Shape

Watercooler has one authoritative process and several untrusted clients:

```text
CLI clients ----\
Browser UI ------> Watercooler service ----> SQLite
Steward --------/          |
                            +---- message bus
                            +---- Taskboard and event trail
                            +---- Summary revisions and citations

Loop runner ----> bounded local argv subprocesses

Local model endpoint <---- Steward only

Review requester --> host dispatcher --> bounded Git-object packet
                                       --> isolated Codex container
                                       --> structured result publication
```

The service owns authentication, identity, validation, ordering, leases, and publication. Clients may request changes but never define their own authority.

## Message Bus

A message records the authenticated sender, recipient, thread, optional topic, language label, tags, body, timestamp, and source address. SQLite FTS5 indexes bodies for bounded search. Pagination uses immutable integer message IDs.

## Taskboard

Tasks move through `queued`, `claimed`, `blocked`, and `done`. Claims have renewable leases. Mutations append task events so state changes retain actor and timestamp evidence. The authenticated principal must match any explicit actor supplied by a client.

The Taskboard is authoritative. Model-generated task proposals are never tasks until a separately authorized client creates them.

## Summary Publication

The service constructs a bounded workset containing:

- the current Summary revision and message coverage
- the next ordered batch of thread messages
- the Taskboard event head, snapshot digest, and proposal-suppression titles
- the previous structured Summary and its cited sources

The workset is canonicalized and hashed. A Steward draft must match an exact schema, cite only allowed message IDs, and avoid proposal titles already present anywhere on the Taskboard snapshot.

Publication runs in an immediate SQLite transaction. It checks the expected parent revision, Taskboard event head, Taskboard digest, workset digest, coverage boundary, and exact message batch before atomically inserting the revision, citations, and new head. A concurrent Taskboard or Summary change returns a conflict and requires a fresh workset.

Messages arriving after the bounded batch remain available for the next revision and do not invalidate the current batch.

## Steward

The Steward is an adapter, not an authority. It:

1. Fetches a workset with read-only message and Taskboard scopes.
2. Removes non-model control fields and sends only bounded evidence plus duplicate-suppression titles.
3. Requests strict structured output from a loopback OpenAI-compatible endpoint.
4. Validates types, text, citations, section uniqueness, normalized proposal uniqueness, and Taskboard duplicates.
5. Renders a dry run, or submits the unchanged validated draft when `--publish` is explicit.

The Watercooler bearer token is never included in the model request.

## Named Loops

The loop runner is a local scheduling boundary rather than service authority.
It stores versioned named specs containing an argv vector, absolute working
directory, interval, per-iteration timeout, and at least one terminal bound:
maximum start count or exclusive UTC deadline. The first iteration starts
immediately; subsequent starts use a fixed delay after the previous finish.

Execution is dry-run-only unless `--execute` is explicit. Each loop name has an
OS-held nonblocking run lock, active and cancellation markers, and a bounded,
rotating JSONL journal. The built-in subprocess hook uses `shell=False`, bounded
stdout/stderr readers, process-tree termination, and silent background flags on
Windows. Any non-success stops the loop. A generic iteration hook receives the
same immutable spec and cancellation token, but its implementation owns any
additional external authority it exercises.

## Isolated Commit Review

The optional host dispatcher owns Watercooler credentials, exact Git-object
reads, durable queue state, retry custody, and result publication. It accepts
only an exact full lowercase SHA-1 commit envelope from policy-bound senders and
constructs the review packet from committed objects rather than the worktree.

The reviewer container receives only the bounded packet through stdin, the
result schema, read-only Codex authentication, temporary filesystems, and one
writable result directory. It receives no repository mount, host home, Docker
socket, Watercooler token, or sender-authored prompt. Direct Docker and optional
WSL Docker use the same digest-pinned isolation and result-validation contract.

## Browser UI

The UI is a static same-origin client. It has no external runtime assets and does not persist credentials. Every value returned by the service is inserted as inert text or a DOM property. Generated summaries are visibly labeled as unreviewed and the Taskboard is presented as authoritative.

## Package Boundary

The wheel contains the core service, clients, Summary contract, Steward, named
loop runner, optional isolated commit-review dispatcher, UI, documentation, and
reviewer integration assets. Non-code assets install under
`share/watercooler/`; the `watercooler-assets` helper resolves the source-tree
or installed location without relying on the current working directory. The
source distribution additionally contains the focused test suite, including
dispatcher boundary tests.

External messaging bridges and MCP exposure remain outside the package boundary
until their deployment and authentication contracts are generalized.
