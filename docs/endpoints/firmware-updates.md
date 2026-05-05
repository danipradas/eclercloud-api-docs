# Endpoints — Firmware Updates

Tag: **Firmware Updates** · 3 endpoints (1 returns 404 in live API)

---

## GET /firmwareUpdates — List firmware update jobs

**Auth required:** Yes (Bearer)

### Integrator use case

> "Are there any pending firmware updates for our devices?"

**Assistant flow:**
1. Call `GET /firmwareUpdates?status=pending`
2. If items returned: "Yes, there is 1 pending update for VIVO-DP, scheduled for [date]."
3. If empty: "No pending firmware updates."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `startPos` | query | integer | No | |
| `pageSize` | query | integer | No | |
| `status` | query | string | No | `pending`, `started`, `finished`, `finished_with_errors` |
| `deviceId` | query | UUID | No | Filter by device |

### Request example

**Python:**
```python
resp = requests.get(
    "https://api.cloud.ecler.com/firmwareUpdates",
    headers=headers,
    params={"status": "finished_with_errors"}
)
updates = resp.json()["items"]
```

**curl:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.cloud.ecler.com/firmwareUpdates?status=pending"
```

### Real captured response (200 OK — 20 updates, sample shown)

```json
{
  "startPos": 0,
  "pageSize": 100,
  "totalCount": 20,
  "items": [
    {
      "id": "fw-uuid-1",
      "plannedAt": "2026-04-12T00:30:00.785Z",
      "status": "finished",
      "deviceId": "dev-uuid-1",
      "groupId": "",
      "parentId": "",
      "outputData": {}
    },
    {
      "id": "fw-uuid-2",
      "plannedAt": "2026-04-13T08:29:00.266Z",
      "status": "pending",
      "deviceId": "dev-uuid-1",
      "groupId": "",
      "parentId": "",
      "outputData": {}
    }
  ]
}
```

**Status distribution in test account:**

| Status | Count |
|--------|-------|
| `finished` | 15 |
| `finished_with_errors` | 4 |
| `pending` | 1 |

> ⚠️ `outputData` is always `{}` in all 20 records — content is undocumented. See [Open Question Q18](../05-open-questions.md#q18).

### Tests

- [`tests/test_firmware_updates.py:40`](../tests/test_firmware_updates.py#L40) — `test_list_firmware_updates_success` ✅ PASS
- [`tests/test_firmware_updates.py:47`](../tests/test_firmware_updates.py#L47) — `test_list_firmware_updates_pagination_fields` ✅ PASS
- [`tests/test_firmware_updates.py:69`](../tests/test_firmware_updates.py#L69) — `test_list_firmware_updates_requires_auth` ❌ FAIL (400 not 403)
- [`tests/test_firmware_updates.py:75`](../tests/test_firmware_updates.py#L75) — `test_list_firmware_updates_filter_by_status` ✅ PASS

---

## GET /firmwareUpdates/{id} — Get firmware update job by ID

**Auth required:** Yes (Bearer)

### Integrator use case

> "What's the result of the last firmware update on VIVO-DP?"

**Assistant flow:**
1. Call `GET /firmwareUpdates?deviceId={dev_id}&pageSize=1` to find latest
2. Call `GET /firmwareUpdates/{id}` for full detail
3. Reply: "Last update ran on 2026-04-13, status: finished."

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID | Yes |

### Request example

**Python:**
```python
resp = requests.get(
    f"https://api.cloud.ecler.com/firmwareUpdates/{update_id}",
    headers=headers
)
update = resp.json()
print(f"Status: {update['status']}")
```

### Observed behavior

| Scenario | Status |
|----------|--------|
| Valid ID | 200 — full update object |
| Non-existent ID | 404 |

### Tests

- [`tests/test_firmware_updates.py:101`](../tests/test_firmware_updates.py#L101) — `test_get_firmware_update_not_found` ✅ PASS
- [`tests/test_firmware_updates.py:109`](../tests/test_firmware_updates.py#L109) — `test_get_firmware_update_by_id` ⏭️ SKIP (no updates in test account at time)
- [`tests/test_firmware_updates.py:136`](../tests/test_firmware_updates.py#L136) — `test_firmware_update_schema_fields` ⏭️ SKIP

---

## POST /firmwareUpdates — ⚠️ ROUTE NOT FOUND

**Auth required:** Yes (declared)

> **Status: NOT AVAILABLE in live API**

**Real captured response (404):**
```json
{
  "message": "Route POST:/firmwareUpdates not found",
  "error": "Not Found",
  "statusCode": 404
}
```

The OpenAPI spec declares this endpoint should accept a `deviceId` (and optionally `groupId`, `plannedAt`) to schedule or trigger a firmware update. The live API returns 404.

**Implication:** Firmware updates cannot be created via the API. The 20 existing update records in the test account appear to have been created by the automated cron scheduler (`automaticUpdateCron` field on devices) rather than by this endpoint.

See [Security Finding #13](../04-security.md#finding-13) and [Open Question Q15](../05-open-questions.md#q15).

### Open questions

- [Q15](../05-open-questions.md#q15) — When will `POST /firmwareUpdates` be implemented?
- [Q16](../05-open-questions.md#q16) — What is the relationship between `automaticUpdateCron` and firmware update jobs?
- [Q17](../05-open-questions.md#q17) — What does `outputData` contain after a completed update?
- [Q18](../05-open-questions.md#q18) — Is there a webhook/push notification for update status changes?
