# Public Demo Deployment

This deployment runs a disposable synthetic Watercooler behind two boundaries:

1. nginx serves the static browser and proxies only `/v1/*` and `/healthz` to
   the API on an internal Docker network;
2. the host reverse proxy terminates public TLS and reaches nginx only through
   `127.0.0.1:8876`.

The browser never receives the admin token. `initialize.sh` mints one 30-day
`demo-judge` session with message and Taskboard read/write scopes, but without
token administration, roster administration, or Summary publication.

## Initialize

Run as an operator who can use Docker and create files owned by UID 10001:

```console
cd deploy/demo
./initialize.sh
```

The script creates ignored, owner-only files:

- `.env`: the API bootstrap admin token;
- `data/watercooler.db`: the mutable demonstration database;
- `data/seed.db`: the golden synthetic snapshot; and
- `data/demo-access.json`: the judge URL, thread, scoped token, and expiry.

Add the block from `Caddyfile.example` to the host Caddyfile, validate it with
`caddy validate --config /etc/caddy/Caddyfile`, and reload Caddy.

## Reset

```console
cd deploy/demo
./reset-demo.sh
```

Reset stops the API before atomically restoring the golden database. The
frontend may return a temporary 502 while the API restarts. The judge token is
part of the snapshot, so it remains stable until its recorded expiry.

A host cron or systemd timer can call `reset-demo.sh` periodically. Do not run
the restore command against a live API process.

## Update

After checking out a reviewed commit:

```console
cd deploy/demo
docker compose build
docker compose up -d
docker compose ps
```

Never commit `.env`, `data/`, or the contents of `demo-access.json`.
