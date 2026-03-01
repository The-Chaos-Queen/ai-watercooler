# RustDesk Pro MCP Connector (Starter)

Minimal MCP server that exposes RustDesk Pro admin actions as tools for LLM clients (Claude Desktop, Cursor, etc.).

## What this gives you

- `rustdesk_healthcheck`
- `list_devices(query, status, limit)`
- `assign_device(device_id, user_id, group_id, note)`
- `disable_device(device_id, reason)`
- `audit_events(limit, actor, device_id)`
- `explain_connector_config`

## Why this is a starter

RustDesk Pro endpoint paths can vary by version and reverse-proxy setup. This connector keeps paths configurable via env vars, so you can adapt without code edits.

## Setup (Windows PowerShell)

1. Create and activate a virtual env:

```powershell
cd C:\Users\cerub\OneDrive\Dokumente\LLM\tools\rustdesk_mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy env file and fill values:

```powershell
Copy-Item .env.example .env
```

4. Set env vars for current shell (or load from `.env` with your preferred loader):

```powershell
$env:RUSTDESK_BASE_URL = "https://your-rustdesk-domain"
$env:RUSTDESK_API_TOKEN = "your_token_here"
```

5. Run MCP server over stdio:

```powershell
python server.py
```

## Claude Desktop MCP config example

Add an MCP server entry (adjust paths):

```json
{
  "mcpServers": {
    "rustdesk-pro": {
      "command": "C:\\Users\\cerub\\OneDrive\\Dokumente\\LLM\\tools\\rustdesk_mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\cerub\\OneDrive\\Dokumente\\LLM\\tools\\rustdesk_mcp\\server.py"
      ],
      "env": {
        "RUSTDESK_BASE_URL": "https://your-rustdesk-domain",
        "RUSTDESK_API_TOKEN": "your_token_here",
        "RUSTDESK_DEVICES_PATH": "/api/devices",
        "RUSTDESK_ASSIGN_PATH": "/api/devices/assign",
        "RUSTDESK_DISABLE_PATH_TEMPLATE": "/api/devices/{device_id}/disable",
        "RUSTDESK_AUDITS_PATH": "/api/audits"
      }
    }
  }
}
```

## Endpoint overrides

If your API differs, change these env vars:

- `RUSTDESK_DEVICES_PATH`
- `RUSTDESK_ASSIGN_PATH`
- `RUSTDESK_DISABLE_PATH_TEMPLATE`
- `RUSTDESK_AUDITS_PATH`

## Security notes

- Use least-privilege API tokens.
- Keep this MCP server local/private.
- Do not expose MCP stdio process directly to the public internet.
- Consider adding an allowlist in tool functions before enabling write actions.

## Troubleshooting

- `401/403`: token missing/invalid permissions.
- `404`: endpoint path mismatch; override path env vars.
- Empty lists with `200`: inspect raw payloads and adjust normalizers.
