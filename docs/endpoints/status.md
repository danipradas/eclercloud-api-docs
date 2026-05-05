# Endpoints — Status

Tag: **Status** · 1 endpoint

---

## GET /health — Platform health check

**Auth required:** No

### Integrator use case

> "Is EclerCLOUD up right now?"

**Assistant flow:**
1. Call `GET /health` (no auth needed)
2. If `result == "ok"` → "EclerCLOUD is online and responding."
3. If any other status or error → "EclerCLOUD appears to be down. Please try again later."

### Parameters

None.

### Request example

**Python:**
```python
import requests

resp = requests.get("https://api.cloud.ecler.com/health")
data = resp.json()
print(data)  # {"result": "ok"}
```

**curl:**
```bash
curl https://api.cloud.ecler.com/health
```

### Real captured response (200 OK)

```json
{
  "result": "ok"
}
```

### Observed behavior

| Scenario | Status | Body |
|----------|--------|------|
| Platform healthy | 200 | `{"result": "ok"}` |
| No auth header needed | 200 | Same — no auth required |

### Tests

- [`tests/test_status.py:29`](../tests/test_status.py#L29) — `test_health_returns_200` ✅ PASS
- [`tests/test_status.py:40`](../tests/test_status.py#L40) — `test_health_body_contains_result_ok` ✅ PASS
- [`tests/test_status.py:59`](../tests/test_status.py#L59) — `test_health_no_auth_required` ✅ PASS

### Notes

- Ideal as a connectivity probe from an MCP server startup routine
- Only endpoint (along with `POST /mqtt/auth`) that does not require authentication
- No degraded state is documented in the spec — unknown what happens during partial outages

### Open questions

- [Q22](../05-open-questions.md#q22) — Is there a staging/sandbox endpoint for integration testing?
