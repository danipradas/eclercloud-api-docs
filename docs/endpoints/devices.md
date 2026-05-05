# Endpoints — Devices

Tag: **Devices** · 8 endpoints (3 return 404 in live API — see notes)

---

## GET /devices — List all devices

**Auth required:** Yes (Bearer)

### Integrator use case

> "Which devices are currently offline?"

**Assistant flow:**
1. Call `GET /devices` with optional `cloudStatus` or `isOnline` filters
2. Filter returned `items` by `isOnline: false`
3. Reply: "2 devices are offline: VIVO-DP and VIDA_DP."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `startPos` | query | integer | No | Offset, default 0 |
| `pageSize` | query | integer | No | Default 100 |
| `cloudStatus` | query | string | No | `approved`, `unpaired`, `pending` |

### Request example

**Python:**
```python
resp = requests.get(
    "https://api.cloud.ecler.com/devices",
    headers=headers,
    params={"cloudStatus": "approved"}
)
devices = resp.json()["items"]
offline = [d for d in devices if not d["isOnline"]]
```

**curl:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.cloud.ecler.com/devices?cloudStatus=approved"
```

### Real captured response (200 OK, 2 devices)

```json
{
  "startPos": 0,
  "pageSize": 100,
  "totalCount": 2,
  "items": [
    {
      "id": "dev-uuid-1",
      "name": "VIVO-DP",
      "model": "VIVO-X8D8",
      "notes": "",
      "uptime": 331848,
      "runtime": 6466361,
      "networkInterfaces": {
        "1": { "ip": "10.x.x.31", "mask": "255.0.0.0", "macAddress": "D8:3A:DD:XX:XX:XX", "gateway": "10.0.0.2" },
        "2": { "ip": "10.x.x.46", "mask": "255.0.0.0", "macAddress": "00:1A:96:XX:XX:XX", "gateway": "10.0.0.2" }
      },
      "firmwareVersion": "v1.01r1",
      "isOnline": false,
      "group": {},
      "cloudStatus": "approved",
      "macAddress": "D8:3A:DD:XX:XX:XX",
      "powered": true,
      "automaticUpdateCron": "29 8 * * 1",
      "lastUpdate": "2026-04-13T07:12:43.363Z",
      "createdAt": "2026-01-28T15:43:35.550Z",
      "additionalParameters": [
        { "name": "alarm.errors", "type": "string", "value": "00000000000000000000000000000000000000" },
        { "name": "alarm.errorsB", "type": "string", "value": "0000000000000000" },
        { "name": "health", "type": "object", "value": "" }
      ],
      "tags": []
    },
    {
      "id": "dev-uuid-2",
      "name": "VIDA_DP",
      "model": "",
      "cloudStatus": "unpaired",
      "isOnline": false,
      "powered": false,
      "networkInterfaces": {},
      "additionalParameters": [],
      "tags": []
    }
  ]
}
```

### Device schema fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Stable identifier |
| `name` | string | Human-readable name |
| `model` | string | Empty for unpaired devices |
| `notes` | string | User-editable free text |
| `uptime` | integer | Seconds since last boot |
| `runtime` | integer | Total lifetime seconds |
| `networkInterfaces` | object | Keyed `"1"`, `"2"` — see field notes below |
| `firmwareVersion` | string | e.g. `"v1.01r1"` |
| `isOnline` | boolean | Current connectivity |
| `cloudStatus` | string | `approved`, `unpaired`, `pending` |
| `macAddress` | string | Primary MAC — **predictable format** |
| `powered` | boolean | Device power state |
| `automaticUpdateCron` | string | Cron expression for scheduled FW updates |
| `lastUpdate` | ISO 8601 | Timestamp of last seen update |
| `createdAt` | ISO 8601 | Registration timestamp |
| `additionalParameters` | array | Device-specific key-value params |
| `tags` | array | User-assigned tags |
| `group` | object | `{}` if no group assigned |

### Security notes

- `macAddress` field uses a predictable format — [Security Finding #5](../04-security.md#finding-5)
- `additionalParameters` may include `alarm.errors` — error codes undocumented

### Tests

- [`tests/test_devices.py:37`](../tests/test_devices.py#L37) — `test_list_devices_success` ✅ PASS
- [`tests/test_devices.py:44`](../tests/test_devices.py#L44) — `test_list_devices_pagination_fields` ✅ PASS
- [`tests/test_devices.py:67`](../tests/test_devices.py#L67) — `test_list_devices_page_size_respected` ✅ PASS
- [`tests/test_devices.py:77`](../tests/test_devices.py#L77) — `test_list_devices_filter_by_cloud_status` ✅ PASS
- [`tests/test_devices.py:96`](../tests/test_devices.py#L96) — `test_list_devices_requires_auth` ❌ FAIL (400 not 403)

### Open questions

- [Q6](../05-open-questions.md#q6) — What populates `additionalParameters`?
- [Q10](../05-open-questions.md#q10) — What is the `automaticUpdateCron` format?

---

## GET /devices/{id} — Get single device

**Auth required:** Yes (Bearer)

### Integrator use case

> "Give me the details for the device named VIVO-DP."

**Assistant flow:**
1. Call `GET /devices` to resolve name → ID
2. Call `GET /devices/{id}` with the resolved ID
3. Format and return: model, firmware version, online status, last seen

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID string | Yes |

### Request example

**Python:**
```python
resp = requests.get(
    f"https://api.cloud.ecler.com/devices/{device_id}",
    headers=headers
)
device = resp.json()
```

**curl:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.cloud.ecler.com/devices/dev-uuid-1"
```

### Observed behavior

| Scenario | Status |
|----------|--------|
| Valid ID | 200 — full device object |
| Non-existent ID | 404 |

### Tests

- [`tests/test_devices.py:106`](../tests/test_devices.py#L106) — `test_get_device_not_found` ✅ PASS
- [`tests/test_devices.py:114`](../tests/test_devices.py#L114) — `test_get_device_by_id` ✅ PASS
- [`tests/test_devices.py:142`](../tests/test_devices.py#L142) — `test_device_schema_fields` ✅ PASS

---

## PUT /devices/{id} — Update device metadata

**Auth required:** Yes (Bearer)

### Integrator use case

> "Add a note to VIVO-DP saying it was serviced today."

**Assistant flow:**
1. Resolve device name → ID via `GET /devices`
2. `GET /devices/{id}` to capture current state (for revert reference)
3. Call `PUT /devices/{id}` with `{"notes": "Serviced 2026-05-04"}`
4. Confirm updated `notes` in response
5. Reply: "Note added to VIVO-DP."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `id` | path | UUID | Yes | |
| `name` | body | string | No | |
| `notes` | body | string | No | Free text, sanitisation unknown |
| `description` | body | string | No | |
| `automaticUpdateCron` | body | string | No | Cron expression |

### Request example

**Python:**
```python
resp = requests.put(
    f"https://api.cloud.ecler.com/devices/{device_id}",
    headers=headers,
    json={"notes": "Serviced 2026-05-04 — TFG test"}
)
print(resp.json()["notes"])
```

**curl:**
```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Serviced 2026-05-04"}' \
  "https://api.cloud.ecler.com/devices/dev-uuid-1"
```

### Real captured response (200 OK — full device object returned)

```json
{
  "id": "dev-uuid-1",
  "name": "VIVO-DP",
  "notes": "TFG test marker — please ignore",
  "model": "VIVO-X8D8",
  "isOnline": false,
  ...
}
```

> ✅ **Verified live:** `notes` set to test string, then reverted. PUT returns full updated device object.

### Observed behavior

- Returns 200 with the full updated device object
- Partial updates work (only include fields to change)
- Reverts work cleanly — setting `notes: ""` removes the note

### Security notes

- `notes` and `description` fields have no documented sanitisation — [Security Finding #10](../04-security.md#finding-10)

---

## DELETE /devices/{id} — Remove device

**Auth required:** Yes (Bearer)

### Integrator use case

> "Remove the device VIDA_DP from EclerCLOUD — it's been decommissioned."

**Assistant flow:**
1. Resolve device name → ID via `GET /devices`
2. **Confirm with user** before proceeding (destructive action)
3. Call `DELETE /devices/{id}`
4. Reply: "VIDA_DP has been removed from EclerCLOUD."

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID | Yes |

### Observed behavior

- Returns 200 or 204 on success
- No confirmation mechanism — a single authenticated request deletes the device

### Security notes

- No soft-delete or recovery mechanism documented
- History data fate after device deletion is undocumented — [Open Question Q11](../05-open-questions.md#q11)

> ⚠️ Not tested with live deletion to avoid data loss in the test account.

---

## GET /devices/{id}/history — Device telemetry history

**Auth required:** Yes (Bearer)

### Integrator use case

> "Show me the last 10 telemetry readings from VIVO-DP."

**Assistant flow:**
1. Resolve device name → ID
2. Call `GET /devices/{id}/history?pageSize=10`
3. Format the first few records and summarise trends if available

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID | Yes |
| `startPos` | query | integer | No |
| `pageSize` | query | integer | No |

### Real captured response (200 OK — 0 records in test account)

```json
{
  "startPos": 0,
  "pageSize": 100,
  "totalCount": 0,
  "items": []
}
```

> Note: History was empty for the test account at the time of capture (device was offline).

### Tests

- [`tests/test_devices.py:176`](../tests/test_devices.py#L176) — `test_get_device_history` ✅ PASS

---

## GET /devices/{id}/networkInterfaces — ⚠️ ROUTE NOT FOUND

**Auth required:** Yes (declared)

> **Status: NOT AVAILABLE in live API**

```json
{
  "message": "Route GET:/devices/{id}/networkInterfaces not found",
  "error": "Not Found",
  "statusCode": 404
}
```

The OpenAPI spec v0.1.0 declares this endpoint, but the live API returns 404. Network interface data **is** available as part of the `networkInterfaces` field in the device object returned by `GET /devices` and `GET /devices/{id}`.

**Workaround:** Read `networkInterfaces` directly from the device object.

```python
device = requests.get(f".../devices/{id}", headers=headers).json()
interfaces = device["networkInterfaces"]
# {"1": {"ip": "...", "macAddress": "...", ...}, "2": {...}}
```

See [Security Finding #13](../04-security.md#finding-13) and [Open Question Q7](../05-open-questions.md#q7).

---

## GET /devices/{id}/deepDive — ⚠️ ROUTE NOT FOUND

**Auth required:** Yes (declared)

> **Status: NOT AVAILABLE in live API**

```json
{
  "message": "Route GET:/devices/{id}/deepDive not found",
  "error": "Not Found",
  "statusCode": 404
}
```

The spec suggests this endpoint would return a URL for deeper device inspection. In practice the route does not exist.

See [Security Finding #13](../04-security.md#finding-13) and [Open Question Q8](../05-open-questions.md#q8).
