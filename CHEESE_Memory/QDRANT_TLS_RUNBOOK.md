# Qdrant LAN TLS Runbook

**Status:** deployed and verified 2026-07-11
**Owner:** shared Exocortex / MoCoP infrastructure
**Scope:** Qdrant LXC 101 on the trusted PVE host (`watercooler`)

## Current service contract

| Item | Value |
|---|---|
| REST endpoint | `https://192.168.2.191:6333` |
| REST transport | TLS-only; plaintext HTTP is intentionally rejected |
| gRPC | Not published on the LAN; internal container port only |
| Authentication | Qdrant write and read-only API keys remain required |
| Certificate identity | `IP:192.168.2.191`, `DNS:qdrant` |
| Issuer | `Laura Qdrant LAN Root CA` |
| Public CA SHA-256 | `703bd5ce0c1a8f3ceef6c0548c2589e19c7f3faf849ae0229e3e2d1508d1dcf8` |
| Public CA PEM | `CHEESE_Memory/security/qdrant-lan-root-ca.crt` |

**Do not use** `http://192.168.2.191:6333`, `curl -k`, `verify=False`, or a plaintext fallback in normal operation.

## Client configuration

Every Qdrant client needs all of the following:

```text
QDRANT_HOST=192.168.2.191
QDRANT_PORT=6333
QDRANT_HTTPS=true
QDRANT_URL=https://192.168.2.191:6333
QDRANT_CA_CERT=<path to qdrant-lan-root-ca.crt>
QDRANT_READ_KEY=<read-only key>       # read paths
QDRANT_API_KEY=<write key>            # write paths only
```

- **Laura Windows profile:** `QDRANT_CA_CERT` points to
  `C:\Users\cerub\AppData\Local\Qdrant\qdrant-lan-root-ca.crt`; the root is
  also in the Current User certificate store.
- **WSL / remote clients:** install or explicitly pass the versioned public PEM.
  Do not copy the root private key. It lives outside Git and off the Qdrant LXC.
- **New code:** pass the CA as `verify=<path>` to `QdrantClient`, or rely on a
  trusted OS root store. HTTPS without `verify=False` is mandatory.

## Verified deployment evidence

The 2026-07-11 cutover produced all of these results:

| Check | Result |
|---|---|
| `GET /readyz` over HTTPS with the root CA | HTTP 200; TLS verification 0 |
| Plain HTTP to port 6333 | rejected (`curl` status 000) |
| External TCP port 6334 | closed |
| Authenticated `GET /collections` | HTTP 200 |
| Windows Anaconda `qdrant-client` with profile CA/read key | successful read; 24 collections |
| Nightwatch verified HTTPS health probe | HTTP 200 |

## Safe smoke test

```bash
curl --fail --cacert "$QDRANT_CA_CERT" \
  https://192.168.2.191:6333/readyz

curl --fail --cacert "$QDRANT_CA_CERT" \
  -H "api-key: $QDRANT_READ_KEY" \
  https://192.168.2.191:6333/collections
```

A normal `http://` request must fail. That failure is evidence the transport guard
is working, not a reason to set `QDRANT_ALLOW_INSECURE_HTTP` permanently.

## Deployment and rollback facts

- LXC: `101` (`qdrant`), Debian 12, Qdrant 1.16.3.
- Live container: `qdrant`, bound only as `192.168.2.191:6333->6333/tcp`.
- Immediate stopped rollback container:
  `qdrant-http-pre-tls-20260711T102422`.
- Root-owned migration backup inside LXC:
  `/root/qdrant-tls-migration-20260711T102422/`.
- Proxmox snapshot:
  `pre-qdrant-tls-20260711T122338`.

### Rollback discipline

1. Prefer the stopped container rollback for a transport-only failure; preserve
   logs and state before doing it.
2. A Proxmox snapshot rollback can discard writes made after the snapshot. It
   requires explicit operator approval and a maintenance window.
3. Never "fix" a trust issue by disabling TLS verification or reopening plaintext
   HTTP.

## Remaining hardening

TLS and API-key exposure are fixed. One distinct issue remains:

- PVE firewall service is currently **disabled**; LXC 101 has no effective
  source-IP allow-list. The Qdrant Docker binding is now limited to the LXC LAN
  address, but any LAN peer can still reach the TLS endpoint and attempt auth.

Treat firewall/source allow-list work as a separate controlled change. Do not
blindly enable PVE firewall globally; inventory management access and service
rules first.

## Provenance note

Older preflight documents contain `http://` examples because they record the
pre-deployment state. They are historical evidence, not current operational
instructions. `QDRANT_SECURITY_PREFLIGHT_GEMMA.md` is explicitly annotated.
