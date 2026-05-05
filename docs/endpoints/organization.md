# Endpoints — Organization

Tag: **Organization** · 1 endpoint

---

## GET /organization — Get organization details

**Auth required:** Yes (Bearer)

### Integrator use case

> "What's the name of our EclerCLOUD account?"

**Assistant flow:**
1. Call `GET /organization` with Bearer token
2. Return `name` from response
3. Reply: "Your EclerCLOUD organisation is named 'Dániel Pradas's Organisatión'."

### Parameters

None.

### Request example

**Python:**
```python
resp = requests.get(
    "https://api.cloud.ecler.com/organization",
    headers=headers
)
data = resp.json()
print(data["name"])
```

**curl:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.cloud.ecler.com/organization
```

### Real captured response (200 OK)

```json
{
  "name": "Dániel Pradas's Organisatión",
  "pairingToken": "<pairing-token-redacted>"
}
```

### Observed behavior

| Scenario | Status | Body |
|----------|--------|------|
| Valid token | 200 | `{ name, pairingToken }` |
| No auth header | **400** | `{"statusCode":400,"error":"Bad Request","message":"Invalid access token"}` |
| Invalid token | **400** | Same as above |

> ⚠️ **Spec mismatch:** Spec declares `403` for unauthorized access; API returns `400`.

### Tests

- [`tests/test_organization.py:26`](../tests/test_organization.py#L26) — `test_get_organization_success` ✅ PASS
- [`tests/test_organization.py:36`](../tests/test_organization.py#L36) — `test_get_organization_fields` ✅ PASS
- [`tests/test_organization.py:62`](../tests/test_organization.py#L62) — `test_get_organization_requires_auth` ❌ FAIL (400 not 403)
- [`tests/test_organization.py:72`](../tests/test_organization.py#L72) — `test_get_organization_invalid_token` ❌ FAIL (400 not 403)

### Security notes

> 🔴 **HIGH — `pairingToken` exposed to all clients**  
> The `pairingToken` is returned to any authenticated client. It can be used to pair new devices to the organisation. There is no documented way to rotate it. See [Security Finding #2](../04-security.md#finding-2).

### Open questions

- [Q19](../05-open-questions.md#q19) — Is there any scoping planned so only admin clients can see `pairingToken`?
- [Q20](../05-open-questions.md#q20) — Can the `pairingToken` be rotated?
