# Third-Party Notices

## Core Runtime

The Watercooler core uses only the Python standard library and the SQLite library supplied by the Python distribution. The Python build must provide SQLite FTS5 support.

## Development Tools

The optional `dev` dependency group uses:

- `pytest` for tests
- `ruff` for linting and formatting checks

Their licenses and notices are distributed by their respective packages.

## Model Runtime

The Steward speaks an OpenAI-compatible HTTP API but does not bundle a model server, SDK, model weights, or model license. Operators are responsible for the terms attached to their selected endpoint and model. Do not redistribute model weights through this repository.

## Browser Assets

The web console bundles no third-party JavaScript, fonts, images, or style sheets. It uses local system fonts and browser APIs.

## Optional Codex Reviewer

The isolated-review integration builds from the pinned Node/Debian container
image declared in its Dockerfile and installs `@openai/codex` version `0.144.5`.
Those components retain their own licenses and notices. The repository bundles
no Codex credential, model service, or model weights.

The wheel includes the Dockerfile, schemas, and launch scripts as inert package
assets. Installing the Python package does not install Docker, Node, Codex, or a
model-provider client dependency on the host.
