FROM node:22.22.2-bookworm-slim@sha256:9f6d5975c7dca860947d3915877f85607946403fc55349f39b4bc3688448bb6e

ARG CODEX_VERSION=0.144.5

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        "ca-certificates=20230311+deb12u1" \
        "libssl3=3.0.20-1~deb12u2" \
        "openssl=3.0.20-1~deb12u2" \
    && rm --recursive --force /var/lib/apt/lists/* \
    && npm install --global "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force \
    && mkdir --parents /codex-home /worker /output /schema \
    && chown --recursive node:node /codex-home /worker /output /schema

LABEL org.watercooler.codex-reviewer.cli-version="${CODEX_VERSION}"

USER node
ENV CODEX_HOME=/codex-home
WORKDIR /worker

ENTRYPOINT ["codex"]
