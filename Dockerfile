FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY . .
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="AI Watercooler" \
      org.opencontainers.image.description="Local-first coordination for human and AI teams" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/The-Chaos-Queen/ai-watercooler"

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --gid 10001 watercooler \
    && adduser --disabled-password --gecos "" --uid 10001 --gid 10001 watercooler

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-deps /wheels/*.whl \
    && rm -rf /wheels

USER 10001:10001
WORKDIR /data
EXPOSE 8765

CMD ["watercooler-service", "--host", "0.0.0.0", "--port", "8765", "--db-path", "/data/watercooler.db"]
