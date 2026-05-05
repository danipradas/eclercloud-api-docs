# 01 — Platform Overview

## What Is EclerCLOUD?

EclerCLOUD is Ecler's cloud platform for **remote monitoring and control** of professional audio amplifiers (VIDA and HALO product lines). It provides:

- Device registration and approval workflow
- Firmware update scheduling and lifecycle tracking
- Group-based device organisation
- MQTT-based real-time device communication

The platform is designed for **system integrators and AV professionals** who manage distributed amplifier networks in venues, hotels, universities, or corporate campuses.

---

## API Architecture

```
Client (integrator / AI assistant)
        │
        │  HTTPS (REST/JSON)
        ▼
 api.cloud.ecler.com         ← This API
        │
        ├── Auth (OAuth2 Client Credentials)
        ├── Organization management
        ├── Device registry
        ├── Group management
        ├── Firmware update orchestration
        ├── MQTT credential broker
        └── Health / Status
```

The API does **not** expose real-time device state (no WebSocket / SSE). For real-time interaction the platform uses MQTT — this API issues the credentials to connect.

---

## Authentication Model

**OAuth2 Client Credentials flow:**

```
POST /auth/token
  body: { client_id, client_secret }
  → { access_token, expires_in: 3600, token_type: "Bearer" }
```

The returned token is a 256-character opaque string. It must be passed as `Authorization: Bearer <token>` on all protected endpoints.

**Observed token behavior:**
- Tokens expire after `3600` seconds (1 hour) — `expires_in` appears to be enforced
- `DELETE /auth/token` invalidates the token server-side
- No token refresh mechanism — clients must re-authenticate
- No token introspection endpoint

**Scope note:** OAuth2 scopes are always empty (`[]`). There is no role-based access control at the token level — all tokens have equal access to all resources.

---

## Endpoint Map

| Tag | Method | Path | Auth | Purpose |
|-----|--------|------|------|---------|
| Auth | POST | `/auth/token` | No | Obtain Bearer token |
| Auth | DELETE | `/auth/token` | Yes | Invalidate current token |
| Status | GET | `/health` | No | Platform health check |
| Organization | GET | `/organization` | Yes | Get org name + pairing token |
| Devices | GET | `/devices` | Yes | List devices (paginated) |
| Devices | GET | `/devices/{id}` | Yes | Get single device |
| Devices | PUT | `/devices/{id}` | Yes | Update device metadata |
| Devices | DELETE | `/devices/{id}` | Yes | Remove device |
| Devices | GET | `/devices/{id}/history` | Yes | Device telemetry history |
| Devices | GET | `/devices/{id}/networkInterfaces` | Yes | ⚠️ 404 — route not found |
| Devices | GET | `/devices/{id}/deepDive` | Yes | ⚠️ 404 — route not found |
| Groups | GET | `/groups` | Yes | List groups (paginated) |
| Groups | POST | `/groups` | Yes | Create group |
| Groups | GET | `/groups/{id}` | Yes | Get group + children |
| Groups | PUT | `/groups/{id}` | Yes | Update group |
| Groups | DELETE | `/groups/{id}` | Yes | Delete group |
| Groups | PUT | `/groups/{id}/devices` | Yes | Assign devices to group |
| Firmware | GET | `/firmwareUpdates` | Yes | List firmware update jobs |
| Firmware | POST | `/firmwareUpdates` | Yes | ⚠️ 404 — route not found |
| Firmware | GET | `/firmwareUpdates/{id}` | Yes | Get firmware update job |
| MQTT | POST | `/mqtt/auth` | No | Validate MQTT device token |

> ⚠️ = Declared in OpenAPI spec v0.1.0 but returns 404 in the live API.

---

## Pagination Model

All list endpoints share the same pagination structure:

**Request:**
```
GET /devices?startPos=0&pageSize=20
```

**Response:**
```json
{
  "startPos": 0,
  "pageSize": 100,
  "totalCount": 42,
  "items": [...]
}
```

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `startPos` | integer | 0 | Offset (not page number) |
| `pageSize` | integer | 100 | Max observed: 100 |

No `nextPage` cursor — clients must calculate `startPos + pageSize` for next page. No `Link` header.

---

## Error Formats

The API has **two distinct error formats** depending on the endpoint:

**JSON errors** (most endpoints):
```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": "Invalid access token"
}
```

**Plain-text errors** (auth endpoint):
```
"Invalid client credentials"
```

**Observed status code behavior (differs from spec):**

| Condition | Spec says | API returns |
|-----------|-----------|-------------|
| No `Authorization` header | 403 | **400** |
| Invalid/expired token | 403 | **400** |
| Bad `client_id`/`client_secret` | 400 | **403** |
| Route not found | — | 404 + JSON |

This inversion is consistent across all protected endpoints and is the most impactful spec accuracy issue. See [04-security.md#finding-6](04-security.md#finding-6).

---

## Filtering & Sorting

`GET /devices` supports `cloudStatus` filtering:
```
GET /devices?cloudStatus=approved
GET /devices?cloudStatus=unpaired
```

`GET /firmwareUpdates` supports status filtering:
```
GET /firmwareUpdates?status=pending
GET /firmwareUpdates?status=finished
GET /firmwareUpdates?status=finished_with_errors
```

No sorting parameters observed. Items appear to be sorted by creation date descending (firmware updates) or ID (devices).
