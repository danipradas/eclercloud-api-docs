# Endpoints — Groups

Tag: **Groups** · 6 endpoints

---

## GET /groups — List all groups

**Auth required:** Yes (Bearer)

### Integrator use case

> "List all location groups we have configured."

**Assistant flow:**
1. Call `GET /groups`
2. Format the list of group names and device counts
3. Reply: "You have 3 groups: Lobby (2 devices), Backstage (0), Conference Room A (1 device)."

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `startPos` | query | integer | No |
| `pageSize` | query | integer | No |

### Request example

**Python:**
```python
resp = requests.get("https://api.cloud.ecler.com/groups", headers=headers)
groups = resp.json()["items"]
for g in groups:
    print(f"{g['name']}: {g['deviceConnectedCount']} online")
```

**curl:**
```bash
curl -H "Authorization: Bearer $TOKEN" https://api.cloud.ecler.com/groups
```

### Real captured response (200 OK — 0 groups in test account)

```json
{
  "startPos": 0,
  "pageSize": 100,
  "totalCount": 0,
  "items": []
}
```

### Tests

- [`tests/test_groups.py:38`](../tests/test_groups.py#L38) — `test_list_groups_success` ✅ PASS
- [`tests/test_groups.py:45`](../tests/test_groups.py#L45) — `test_list_groups_pagination_fields` ✅ PASS
- [`tests/test_groups.py:67`](../tests/test_groups.py#L67) — `test_list_groups_requires_auth` ❌ FAIL (400 not 403)

---

## POST /groups — Create a group

**Auth required:** Yes (Bearer)

### Integrator use case

> "Create a new group called 'Main Stage' for the concert hall."

**Assistant flow:**
1. Call `POST /groups` with `{"name": "Main Stage", "description": "Concert hall devices"}`
2. Capture the returned `id`
3. Reply: "Group 'Main Stage' created. You can now assign devices to it."

### Parameters

| Name | In | Type | Required | Notes |
|------|----|------|----------|-------|
| `name` | body | string | Yes | Group name |
| `description` | body | string | No | Free-text description |
| `notes` | body | string | No | Additional notes |
| `parentGroupId` | body | UUID | No | For nested groups |
| `tags` | body | array | No | String tags |

### Request example

**Python:**
```python
resp = requests.post(
    "https://api.cloud.ecler.com/groups",
    headers=headers,
    json={"name": "Main Stage", "description": "Concert hall devices"}
)
group = resp.json()
group_id = group["id"]
```

**curl:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Main Stage","description":"Concert hall devices"}' \
  https://api.cloud.ecler.com/groups
```

### Real captured response (200 OK)

```json
{
  "id": "grp-uuid-1",
  "name": "TFG-Test-Group",
  "notes": "",
  "description": "Temporary test group",
  "parentGroupId": null,
  "deviceConnectedCount": 0,
  "deviceDisconnectedCount": 0,
  "tags": []
}
```

> ⚠️ Returns **200**, not **201** as would be conventional for resource creation.

### Tests

- [`tests/test_groups.py:143`](../tests/test_groups.py#L143) — `test_create_and_delete_group` ✅ PASS (full lifecycle)

---

## GET /groups/{id} — Get group by ID

**Auth required:** Yes (Bearer)

### Integrator use case

> "How many devices are connected in the lobby group?"

**Assistant flow:**
1. Resolve "lobby" to group ID (via `GET /groups`, filter by name)
2. Call `GET /groups/{id}`
3. Reply: "Lobby group has 2 devices connected and 1 disconnected."

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID | Yes |

### Real captured response (200 OK — includes `childGroups`)

```json
{
  "id": "grp-uuid-1",
  "name": "TFG-Test-Group",
  "notes": "",
  "description": "Temporary test group",
  "parentGroupId": null,
  "deviceConnectedCount": 0,
  "deviceDisconnectedCount": 0,
  "tags": [],
  "childGroups": []
}
```

> Note: `GET /groups/{id}` returns an extra `childGroups` field not present in the list endpoint.

### Tests

- [`tests/test_groups.py:77`](../tests/test_groups.py#L77) — `test_get_group_not_found` ✅ PASS
- [`tests/test_groups.py:85`](../tests/test_groups.py#L85) — `test_get_group_by_id` ✅ PASS
- [`tests/test_groups.py:112`](../tests/test_groups.py#L112) — `test_group_schema_fields` ✅ PASS

---

## PUT /groups/{id} — Update group

**Auth required:** Yes (Bearer)

### Integrator use case

> "Rename the 'Main Stage' group to 'Stage A'."

**Assistant flow:**
1. Resolve "Main Stage" to group ID
2. `GET /groups/{id}` to capture current state
3. `PUT /groups/{id}` with `{"name": "Stage A"}`
4. Reply: "Group renamed to 'Stage A'."

### Request example

**Python:**
```python
resp = requests.put(
    f"https://api.cloud.ecler.com/groups/{group_id}",
    headers=headers,
    json={"name": "Stage A"}
)
```

### Real captured response (200 OK)

```json
{
  "id": "grp-uuid-1",
  "name": "TFG-Test-Group-Renamed",
  "description": "Temporary test group",
  "parentGroupId": null,
  "deviceConnectedCount": 0,
  "deviceDisconnectedCount": 0,
  "tags": []
}
```

> ✅ **Verified live:** Renamed from `TFG-Test-Group` to `TFG-Test-Group-Renamed`.

---

## DELETE /groups/{id} — Delete group

**Auth required:** Yes (Bearer)

### Integrator use case

> "Delete the 'Old Conference Room' group — that room no longer exists."

**Assistant flow:**
1. Resolve group name → ID
2. Check `deviceConnectedCount + deviceDisconnectedCount > 0` — if so, warn user that devices will be ungrouped
3. **Confirm with user**
4. `DELETE /groups/{id}`
5. Reply: "Group deleted. Devices in that group are now ungrouped."

### Real captured response

- `DELETE /groups/{id}` → **204 No Content**
- `GET /groups/{id}` after deletion → **404**

> ✅ **Verified live:** Group `grp-uuid-1` deleted, subsequent GET returns 404.

### Open questions

- [Q12](../05-open-questions.md#q12) — When a parent group is deleted, what happens to child groups?
- [Q13](../05-open-questions.md#q13) — What happens to devices assigned to a deleted group?

---

## PUT /groups/{id}/devices — Assign devices to group

**Auth required:** Yes (Bearer)

### Integrator use case

> "Assign VIVO-DP to the Main Stage group."

**Assistant flow:**
1. Resolve device name → device ID
2. Resolve group name → group ID
3. Call `PUT /groups/{id}/devices` with `{"deviceIds": ["dev-uuid-1"]}`
4. Reply: "VIVO-DP assigned to Main Stage."

### Parameters

| Name | In | Type | Required |
|------|----|------|----------|
| `id` | path | UUID | Yes — group ID |
| `deviceIds` | body | array of UUID | Yes |

### Request example

**Python:**
```python
resp = requests.put(
    f"https://api.cloud.ecler.com/groups/{group_id}/devices",
    headers=headers,
    json={"deviceIds": [device_id]}
)
```

### Open questions

- [Q14](../05-open-questions.md#q14) — Does this endpoint replace or append device assignments?
