# Endpoints — MQTT

Tag: **MQTT** · 1 endpoint

---

## POST /mqtt/auth — Validate MQTT device token

**Auth required:** No (public endpoint)

### Integrator use case

> "Can I check if this device token is valid for MQTT access?"

**Assistant flow:**
1. Call `POST /mqtt/auth` with `{"deviceToken": "<token>"}`
2. If 200 → "Token is valid for MQTT connection."
3. If 401 → "Token is invalid or expired."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `deviceToken` | body | string | Yes | MAC address of the device |

### Request example

**Python:**
```python
resp = requests.post(
    "https://api.cloud.ecler.com/mqtt/auth",
    json={"deviceToken": "D8:3A:DD:BF:57:FF"}  # MAC address format
)
print(resp.status_code)
```

**curl:**
```bash
curl -X POST https://api.cloud.ecler.com/mqtt/auth \
  -H "Content-Type: application/json" \
  -d '{"deviceToken":"D8:3A:DD:BF:57:FF"}'
```

### Observed behavior

**Live test with probe token:**
```
POST /mqtt/auth  {"deviceToken": "test-token-probe-only"}
→ 400 / null body
```

> ⚠️ Returns `400` with a `null` response body. Expected either a validation response (200/401) or a JSON error body.  
> ⚠️ `Content-Type: application/json` with a null body is an inconsistency — parsers may throw.

### Security notes

> 🔴 **PUBLIC ENDPOINT WITH DEVICE ENUMERATION RISK**  
> `POST /mqtt/auth` requires no authentication. An attacker can systematically probe MAC addresses (predictable format: `D8:3A:DD:xx:xx:xx`) to identify registered devices. See [Security Finding #3](../04-security.md#finding-3) and [Security Finding #5](../04-security.md#finding-5).

### Open questions

- [Q19](../05-open-questions.md#q19) — What does a successful MQTT auth response look like?
- [Q20](../05-open-questions.md#q20) — Is there rate limiting or IP allowlisting on this endpoint?
- [Q21](../05-open-questions.md#q21) — Is `deviceToken` always the MAC address? Is that documented?
