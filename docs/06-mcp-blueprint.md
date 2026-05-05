# 06 — MCP Server Blueprint

> **Status:** Design only — implementation is a separate task.

This document describes how to build an MCP server that wraps the EclerCLOUD REST API so an AI assistant (Claude or another LLM) can control and monitor Ecler audio devices using natural language.

---

## What MCP Solves

The EclerCLOUD REST API requires:
- OAuth2 token management (obtain, cache, refresh)
- UUID resolution (human says "VIVO-DP", API needs `dev-uuid-1`)
- Pagination iteration
- Status polling (firmware updates have no webhook)

An MCP server abstracts all of this. The AI assistant calls `list_devices` and gets names — not UUIDs and pagination headers.

---

## Architecture

```
AI Assistant (Claude)
       │
       │  MCP protocol (stdio / SSE)
       ▼
  mcp-server/eclercloud.py
       │
       │  Cached token, name→ID resolution
       │  HTTPS REST calls
       ▼
  api.cloud.ecler.com
       │
       └── Devices / Groups / Firmware / MQTT
```

---

## Proposed Tool Table

| MCP Tool | Maps to | NL example |
|----------|---------|-----------|
| `health_check` | `GET /health` | "Is EclerCLOUD up?" |
| `get_organization` | `GET /organization` | "What's our account name?" |
| `list_devices` | `GET /devices` | "Show me all devices" |
| `get_device` | `GET /devices/{id}` | "Details for VIVO-DP" |
| `list_offline_devices` | `GET /devices` + filter | "Which devices are offline?" |
| `update_device_notes` | `PUT /devices/{id}` | "Add a note to VIVO-DP" |
| `list_groups` | `GET /groups` | "List all groups" |
| `create_group` | `POST /groups` | "Create a group called Lobby" |
| `get_group` | `GET /groups/{id}` | "How many devices in Lobby?" |
| `rename_group` | `PUT /groups/{id}` | "Rename Stage A to Stage B" |
| `delete_group` | `DELETE /groups/{id}` | "Delete the Lobby group" |
| `assign_devices_to_group` | `PUT /groups/{id}/devices` | "Add VIVO-DP to Lobby" |
| `list_firmware_updates` | `GET /firmwareUpdates` | "Any pending firmware updates?" |
| `get_firmware_update` | `GET /firmwareUpdates/{id}` | "Status of last firmware update?" |

> Note: `POST /firmwareUpdates`, `GET /devices/{id}/networkInterfaces`, `GET /devices/{id}/deepDive` are excluded until the API endpoints exist.

---

## Token Management Pattern

```python
import time, requests, os
from dotenv import load_dotenv

load_dotenv()

_token: str | None = None
_token_expires_at: float = 0

def _get_token() -> str:
    global _token, _token_expires_at
    # Refresh 60 s before expiry to avoid mid-request failures
    if _token and time.time() < _token_expires_at - 60:
        return _token
    resp = requests.post(
        f"{os.getenv('BASE_URL')}/auth/token",
        json={"client_id": os.getenv("CLIENT_ID"), "client_secret": os.getenv("CLIENT_SECRET")}
    )
    resp.raise_for_status()
    data = resp.json()
    _token = data["access_token"]
    _token_expires_at = time.time() + data["expires_in"]
    return _token

def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}
```

---

## Name → ID Resolution Pattern

Since AI users speak in names (not UUIDs), the MCP server needs resolution:

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def _resolve_device(name_or_id: str) -> str:
    """Return device UUID from name or passthrough if already UUID."""
    if len(name_or_id) == 36 and "-" in name_or_id:
        return name_or_id  # already a UUID
    devices = requests.get(f"{BASE}/devices", headers=_headers()).json()["items"]
    match = next((d for d in devices if d["name"].lower() == name_or_id.lower()), None)
    if not match:
        raise ValueError(f"No device named '{name_or_id}'")
    return match["id"]
```

Cache should be invalidated on mutations (device rename, group delete).

---

## Tool Description Writing Guidelines

MCP tool descriptions drive which tool the AI picks. Write them like natural-language trigger phrases:

```python
@mcp.tool(description="List all Ecler devices in EclerCLOUD. Use when the user asks about devices, equipment, amplifiers, what's online, what's offline, or wants to see all hardware.")
def list_devices(cloud_status: str = None) -> list[dict]: ...

@mcp.tool(description="Check if a specific device is online and get its details. Use when the user asks about a specific device by name or ID, wants firmware version, IP address, or last seen time.")
def get_device(name_or_id: str) -> dict: ...
```

---

## Recommended Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.13 | Matches existing test suite |
| MCP SDK | `mcp` (Anthropic) | First-party, actively maintained |
| HTTP client | `requests` or `httpx` | Matches existing tests |
| Config | `python-dotenv` | Already in use |
| Package manager | `uv` | Already in use |

**Install:**
```bash
uv add mcp requests python-dotenv
```

**Run:**
```bash
uv run python mcp-server/eclercloud.py
```

---

## Claude Code Integration

Add to `.claude/settings.json` under `mcpServers`:
```json
{
  "mcpServers": {
    "eclercloud": {
      "command": "uv",
      "args": ["run", "python", "mcp-server/eclercloud.py"],
      "env": {}
    }
  }
}
```

Credentials are loaded from `.env` by `python-dotenv` in the server process.

---

## File Structure (proposed)

```
mcp-server/
├── eclercloud.py       ← Main MCP server entry point
├── auth.py             ← Token cache + auth helper
├── resolve.py          ← Name→ID resolution
└── tools/
    ├── devices.py      ← Device tools
    ├── groups.py       ← Group tools
    ├── firmware.py     ← Firmware update tools
    └── status.py       ← Health + org tools
```
