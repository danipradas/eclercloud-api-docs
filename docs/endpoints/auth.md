# Endpoints — Auth

Tag: **Auth** · 2 endpoints

---

## POST /auth/token — Obtain Bearer token

**Auth required:** No

### Integrator use case

> "I need to connect to EclerCLOUD to check the equipment."

**Assistant flow:**
1. Call `POST /auth/token` with stored `CLIENT_ID` and `CLIENT_SECRET` (from env)
2. Cache the returned `access_token` for up to 3600 s
3. Reply: "Connected to EclerCLOUD. Token valid for 1 hour."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `client_id` | body | string | Yes | OAuth2 client ID |
| `client_secret` | body | string | Yes | OAuth2 client secret |

### Request example

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
data = resp.json()
token = data["access_token"]
```

**curl:**
```bash
curl -X POST https://api.cloud.ecler.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"<CLIENT_ID>","client_secret":"<CLIENT_SECRET>"}'
```

### Real captured response (200 OK)

```json
{
  "access_token": "<256-char-hex-string>",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Observed behavior

| Scenario | Status | Body |
|----------|--------|------|
| Valid credentials | 200 | `{ access_token, expires_in, token_type }` |
| Bad credentials | **403** | `"Invalid client credentials"` (plain text) |

> ⚠️ **Spec mismatch:** OpenAPI spec declares `400` for bad credentials. API returns `403`.  
> ⚠️ **Format mismatch:** Error body is plain text (no JSON wrapper), unlike all other endpoints.

### Tests

- [`tests/test_auth.py:30`](../tests/test_auth.py#L30) — `test_token_request_success` ✅ PASS
- [`tests/test_auth.py:47`](../tests/test_auth.py#L47) — `test_token_response_fields` ✅ PASS
- [`tests/test_auth.py:79`](../tests/test_auth.py#L79) — `test_invalid_credentials_returns_400` ❌ FAIL (API returns 403, not 400)
- [`tests/test_auth.py:93`](../tests/test_auth.py#L93) — `test_token_grants_api_access` ✅ PASS

### Security notes

- No rate limiting observed — [Security Finding #4](../04-security.md#finding-4)
- Credentials sent as JSON in request body (HTTPS only) — no credential in URL
- OAuth2 scopes always empty — [Security Finding #1](../04-security.md#finding-1)

### Open questions

- [Q1](../05-open-questions.md#q1) — Is `expires_in` enforced server-side or informational?
- [Q3](../05-open-questions.md#q3) — Is there a token refresh mechanism planned?
- [Q4](../05-open-questions.md#q4) — Is there rate limiting on this endpoint?

---

## DELETE /auth/token — Invalidate current token

**Auth required:** Yes (Bearer)

### Integrator use case

> "Log me out of EclerCLOUD."

**Assistant flow:**
1. Call `DELETE /auth/token` with current Bearer token
2. Clear the cached token from MCP server state
3. Reply: "Logged out. Next request will require re-authentication."

### Parameters

None. The token to invalidate is identified by the `Authorization: Bearer` header.

### Request example

**Python:**
```python
resp = requests.delete(
    "https://api.cloud.ecler.com/auth/token",
    headers={"Authorization": f"Bearer {token}"}
)
print(resp.status_code)  # 200 or 204
```

**curl:**
```bash
curl -X DELETE https://api.cloud.ecler.com/auth/token \
  -H "Authorization: Bearer <token>"
```

### Observed behavior

| Scenario | Status | Body |
|----------|--------|------|
| Valid token | 200 / 204 | Empty |
| Using token after deletion | **400** | `{"statusCode":400,"error":"Bad Request","message":"Invalid access token"}` |

> ⚠️ After deletion the invalidated token returns **400**, not **403** as the spec declares.  
> ⚠️ **Destructive:** No body or confirmation required — a single request with valid credentials permanently invalidates the token. See [Security Finding #8](../04-security.md#finding-8).

### Tests

- [`tests/test_auth.py:113`](../tests/test_auth.py#L113) — `test_token_delete_invalidates` ❌ FAIL  
  Test expects 403 on re-use after deletion; API returns 400. Token invalidation itself works correctly.
