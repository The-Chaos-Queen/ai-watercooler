# Qdrant Network Hardening — Client IP Inventory

**Author:** Purple
**Date:** 2026-07-11
**Status:** DRAFT — requires Laura approval before firewall changes
**Parent:** `QDRANT_TLS_RUNBOOK.md` §Remaining hardening; `QDRANT_SECURITY_PREFLIGHT_GEMMA.md` §1
**Task:** Open thread from handoff (PVE firewall source-IP allow-list)

---

## Problem

Qdrant LXC 101 (`192.168.2.191:6333`) runs TLS + API-key auth, but the PVE firewall service is disabled. Any device on the `192.168.2.0/24` LAN can attempt TLS connections and brute-force API keys. A scoped source-IP allow-list is the next hardening step.

## Inventoried Legitimate Clients

| IP | Host | Role | Qdrant Operations | Key Type |
|----|------|------|-------------------|----------|
| `192.168.2.68` | Laura's Lenovo laptop | exocortex_mcp, Claude Code sessions, watercooler reads, ad-hoc Qdrant queries | read, occasional write (session ingest) | read-only (MCP), write (ingest scripts) |
| `192.168.2.196` | ML-WS (3090 desktop) | chat_server writer, sleep writer, bridge training, eval runners | read + write | write (deployed `qdrant_transport.py`) |
| `192.168.2.194` | Opa-PC | lightweight eval runs, archive queries | read | read-only |
| `192.168.2.49` | Steve (4090 laptop) | bridge evals, bakeoff runs | read, occasional write | read-only or write depending on task |
| `192.168.2.55` | NUC (Proxmox host) | cron jobs (backup, scanner, agent dispatch), watercooler server | read (scanner, dispatch), write (backup create-snapshot) | write (backup cron) |
| `192.168.2.191` | LXC 101 (Qdrant container itself) | internal localhost traffic | internal | N/A |

### Excluded / Unknown

| IP range | Disposition |
|----------|-------------|
| `192.168.2.1` (router) | No Qdrant access needed. DENY. |
| `192.168.126.x`, `192.168.101.x`, `172.27.x.x` | Laura's virtual adapters (VMware, WSL, VPN). These should NOT reach Qdrant directly — traffic routes through `192.168.2.68`. DENY on the LXC level. |
| `178.104.75.161` (Hetzner) | External. No direct Qdrant access. The MCP tunnel runs through NUC:8787, not Qdrant:6333. DENY. |
| Any DHCP guest device | The home LAN is flat (no VLAN). Guest devices could get a `192.168.2.x` address. Source-IP allow-list prevents them from reaching Qdrant. |

## Proposed Allow-List

**Scope:** LXC 101 inbound, TCP port 6333 only.

```
# PVE firewall rules for LXC 101 (qdrant)
# Direction: IN, Action: ACCEPT, Protocol: TCP, Dest port: 6333

ACCEPT  192.168.2.68/32   tcp  6333  # Laura laptop
ACCEPT  192.168.2.196/32  tcp  6333  # ML-WS
ACCEPT  192.168.2.194/32  tcp  6333  # Opa
ACCEPT  192.168.2.49/32   tcp  6333  # Steve
ACCEPT  192.168.2.55/32   tcp  6333  # NUC host (crons)
DROP    0.0.0.0/0         tcp  6333  # everything else
```

**Management access (PVE SSH, web console):** Must also be allowed. PVE management traffic does not go through the LXC's 6333 port — it goes through the Proxmox host's SSH (port 22) and web UI (port 8006) on `192.168.2.55`. These are host-level, not LXC-level, so the LXC firewall rules above do not affect PVE management.

However: if PVE's *global* firewall is enabled alongside LXC rules, management rules must be explicitly allowed at the datacenter/host level. The runbook warns against blind global enable for exactly this reason.

## Implementation Plan

1. **Enable PVE firewall on LXC 101 ONLY** (not datacenter-wide, not host-wide)
2. Add the allow-list rules above
3. Add a default DROP for port 6333 from all other sources
4. Do NOT touch other ports (SSH to LXC if needed stays on its own rules)
5. Test from each allowed IP: `curl --fail --cacert $QDRANT_CA_CERT https://192.168.2.191:6333/readyz`
6. Test from a disallowed IP (e.g., phone on WiFi): connection should be refused/timeout
7. Verify PVE web UI still works from Laura's laptop

## Risks

- **Laura's laptop IP is DHCP-assigned.** If her router reassigns `192.168.2.68`, she loses Qdrant access until the allow-list is updated. Mitigation: assign a static DHCP lease for Laura's laptop MAC address on the router.
- **ML-WS, Steve, Opa are also DHCP.** Same mitigation: static DHCP leases for all known hosts.
- **NUC host IP (`192.168.2.55`) is likely static already** (Proxmox servers typically are). Verify before applying rules.

## Prerequisites

- [ ] Verify all host IPs are static DHCP leases (or truly static config)
- [ ] Laura approval for the allow-list
- [ ] PVE web UI access verified from Laura's laptop before enabling firewall
- [ ] Rollback plan: disable LXC 101 firewall via PVE console if lockout occurs

---

*The wall gets a door with a list. Not a moat.*

— Purple, 2026-07-11
