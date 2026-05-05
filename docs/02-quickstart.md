# 02 — Quickstart

## Prerequisites

- EclerCLOUD account with a registered application (provides `CLIENT_ID` + `CLIENT_SECRET`)
- Python 3.10+ with `requests` and `python-dotenv` (`uv add requests python-dotenv`)
- Or: any HTTP client that can issue `POST` with JSON body

## Step 1 — Obtain a Token

**Python:**
```python
import os, requests
from dotenv import load_dotenv

load_dotenv()

resp = requests.post(
    "https://api.cloud.ecler.com/auth/token",
    json={
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
    }
)
resp.raise_for_status()
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

**curl:**
```bash
TOKEN=$(curl -s -X POST https://api.cloud.ecler.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"<CLIENT_ID>","client_secret":"<CLIENT_SECRET>"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**Real response shape:**
```json
{
  "access_token": "<256-char-hex-string>",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

## Step 2 — Make an Authenticated Request

**Python:**
```python
resp = requests.get("https://api.cloud.ecler.com/devices", headers=headers)
devices = resp.json()["items"]
print(f"Found {len(devices)} device(s)")
```

**curl:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  https://api.cloud.ecler.com/devices | python -m json.tool
```

## Token Lifecycle

```
POST /auth/token
        │
        │  → access_token (valid 3600 s)
        │
        ├─ Use on all protected endpoints: Authorization: Bearer <token>
        │
        ├─ After 3600 s: token expires → re-call POST /auth/token
        │
        └─ DELETE /auth/token to invalidate early (e.g. logout)
```

**Notes:**
- No refresh token — must re-authenticate with credentials after expiry
- No token introspection endpoint (`/auth/introspect` or similar)
- After `DELETE /auth/token`, the token returns **400** (not 403 as spec says)

## Using as an MCP Server

If you expose this API as an MCP server for an AI assistant, the recommended pattern is:

```python
# mcp_server/eclercloud.py (pseudocode)
_token: str | None = None
_token_expires_at: float = 0

def get_token() -> str:
    global _token, _token_expires_at
    if _token and time.time() < _token_expires_at - 60:
        return _token
    resp = requests.post(".../auth/token", json={...})
    _token = resp.json()["access_token"]
    _token_expires_at = time.time() + resp.json()["expires_in"]
    return _token
```

The token should be cached in the MCP process (server-side). Do NOT ask the user for credentials — they should be in environment variables.

See [06-mcp-blueprint.md](06-mcp-blueprint.md) for the full MCP design.

## Environment Setup

Create a `.env` file in the project root (never commit it):
```
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
BASE_URL=https://api.cloud.ecler.com
```

See `.env.example` for the template. Load with `python-dotenv` in every script.

## Running the Test Suite

```bash
uv run pytest tests/ -v
```

Expected result with the TFG test account: **26 passed, 7 failed, 2 skipped**  
The 7 failures are all known spec-vs-API mismatches (status code `400` vs expected `403`).  
See [03-test-results.md](03-test-results.md) for details.
