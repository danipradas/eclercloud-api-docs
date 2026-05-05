# 04 — Security Analysis

**Review date:** 2026-05-04  
**Reviewer:** Daniel Pradas (TFG)  
**Basis:** OpenAPI spec v0.1.0 + live API testing

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 HIGH | 3 |
| 🟠 MEDIUM | 6 |
| 🟡 LOW | 5 |
| **Total** | **14** |

---

## Findings

### Finding #1 — No OAuth2 Scopes (No RBAC) {#finding-1}

**Severity:** 🔴 HIGH  
**Category:** Authorization

OAuth2 scopes are always `[]` (empty). Every valid token has full access to all resources — there is no way to issue a read-only token, a per-device token, or an admin-only token.

**Impact:** A stolen or leaked token grants full control over all devices in the organisation.

**Reproduction:**
```json
POST /auth/token → { "access_token": "...", "token_type": "Bearer", "scope": null }
```

**Recommendation:** Define and enforce scopes: `devices:read`, `devices:write`, `groups:manage`, `firmware:trigger`, `admin`.

---

### Finding #2 — `pairingToken` Exposed to All Authenticated Clients {#finding-2}

**Severity:** 🔴 HIGH  
**Category:** Information disclosure / Authorization

`GET /organization` returns `pairingToken` to any authenticated client. This token is used to pair new physical devices to the organisation. Exposing it to all clients (including read-only ones, if scopes existed) means any authenticated user can pair arbitrary hardware.

**Reproduction:**
```
GET /organization  →  { "name": "...", "pairingToken": "ffb0..." }
```

**Impact:** Rogue device pairing; potential for adding attacker-controlled devices to the organisation.

**Recommendation:** Restrict `pairingToken` to admin-scoped tokens only. Provide a token rotation endpoint.

---

### Finding #3 — `POST /mqtt/auth` is a Public Unauthenticated Endpoint {#finding-3}

**Severity:** 🔴 HIGH  
**Category:** Authentication bypass / Device enumeration

`POST /mqtt/auth` requires no `Authorization` header. It is designed as a device-to-broker authentication relay, but it is accessible from the public internet with no rate limiting or IP restriction.

An attacker can iterate MAC address space (`D8:3A:DD:00:00:00` through `D8:3A:DD:FF:FF:FF`) to discover registered devices without any credentials.

**Reproduction:**
```bash
curl -X POST https://api.cloud.ecler.com/mqtt/auth \
  -d '{"deviceToken":"D8:3A:DD:BF:57:FF"}'
```

**Recommendation:** Add rate limiting, IP allowlisting, or HMAC challenge to this endpoint. Consider removing it from the public internet and proxying it through the device's MQTT broker directly.

---

### Finding #4 — No Rate Limiting on Authentication Endpoint {#finding-4}

**Severity:** 🟠 MEDIUM  
**Category:** Brute force risk

No rate limiting headers (`Retry-After`, `X-RateLimit-*`) are returned on `POST /auth/token`. Repeated requests with incorrect credentials return `403` with no delay or lockout.

**Reproduction:** 100 rapid requests with bad credentials → all return 403 with no backoff.

**Recommendation:** Implement exponential backoff or account lockout after N failed attempts. Add `Retry-After` headers on error responses.

---

### Finding #5 — MAC Address as Device Token (Predictable Format) {#finding-5}

**Severity:** 🟠 MEDIUM  
**Category:** Device enumeration

The `deviceToken` used in `POST /mqtt/auth` is the device MAC address (e.g. `D8:3A:DD:BF:57:FF`). MAC addresses follow the OUI scheme — Ecler devices share the same OUI prefix, making systematic enumeration feasible.

Combined with Finding #3 (no rate limiting), this creates a practical device enumeration attack surface.

**Recommendation:** Use a cryptographically random, per-device secret token instead of the MAC address.

---

### Finding #6 — HTTP Status Codes Inverted vs. Spec {#finding-6}

**Severity:** 🟠 MEDIUM  
**Category:** Spec integrity / Incorrect error handling

The OpenAPI spec and live API return opposite status codes for two error conditions:

| Condition | Spec | API | Risk |
|-----------|------|-----|------|
| Missing/invalid token | 403 | **400** | Clients implementing spec-compliant error handling will misclassify auth errors |
| Bad client credentials | 400 | **403** | Same |

This is particularly impactful for MCP servers and AI assistants that map status codes to error descriptions. A 400 might be treated as a client input error rather than an auth failure.

**Recommendation:** Align the API with the spec (400 for client errors, 403 for auth failures) or update the spec.

---

### Finding #7 — Inconsistent Error Response Format {#finding-7}

**Severity:** 🟠 MEDIUM  
**Category:** Information disclosure / Developer experience

Two error formats exist:

- **JSON** (most endpoints): `{"statusCode":400,"error":"Bad Request","message":"Invalid access token"}`
- **Plain text** (auth endpoint): `"Invalid client credentials"`

The `message` field provides internal system information. Verbose error messages can help attackers understand system internals (information disclosure).

**Recommendation:** Standardise on one error format across all endpoints. Consider generic messages for production (e.g. "Authentication failed" rather than "Invalid access token").

---

### Finding #8 — DELETE /auth/token Has No Safeguards {#finding-8}

**Severity:** 🟠 MEDIUM  
**Category:** Accidental token invalidation

`DELETE /auth/token` invalidates the token identified by the `Authorization` header. No confirmation, no body, no `?confirm=true` parameter. A CSRF attack or accidental invocation (wrong HTTP method) will invalidate a valid session.

**Recommendation:** Require a body parameter (e.g. `{"revoke": true}`) or a dedicated `POST /auth/revoke` pattern. Document CSRF protection requirements.

---

### Finding #9 — No Token Expiry Enforcement Transparency {#finding-9}

**Severity:** 🟠 MEDIUM  
**Category:** Session management

`expires_in: 3600` is returned but there is no documented mechanism to check if a token is still valid short of making an API call and observing a 400. No introspection endpoint (`/auth/introspect` or RFC 7662).

**Impact:** MCP servers and long-running integrations must implement their own expiry tracking, with risk of clock drift.

**Recommendation:** Add `POST /auth/introspect` or include `expires_at` (ISO 8601 timestamp) in the token response.

---

### Finding #10 — XSS Risk in `notes` and `description` Fields {#finding-10}

**Severity:** 🟡 LOW  
**Category:** Injection / XSS

`PUT /devices/{id}` and `PUT /groups/{id}` accept free-text `notes` and `description` fields. No sanitisation policy is documented.

If the EclerCLOUD web UI (`cloud.ecler.com`) renders these fields without HTML escaping, stored XSS is possible.

**Reproduction:** `PUT /devices/{id}` with `{"notes": "<script>alert(1)</script>"}` — stored successfully (observed in test).

**Recommendation:** Document sanitisation policy. Ensure UI renders these fields as text, not HTML.

---

### Finding #11 — No HTTPS-Only Policy (HSTS) Mentioned {#finding-11}

**Severity:** 🟡 LOW  
**Category:** Transport security

The API operates over HTTPS, but no `Strict-Transport-Security` header is declared in the spec. HTTP-to-HTTPS redirect behavior is undocumented.

**Recommendation:** Confirm HSTS is active with `max-age=31536000; includeSubDomains`. Document the HTTP redirect policy.

---

### Finding #12 — No Idempotency Keys on POST Operations {#finding-12}

**Severity:** 🟡 LOW  
**Category:** Reliability / Duplicate creation

`POST /groups` (and potentially `POST /firmwareUpdates` when implemented) do not support `Idempotency-Key` headers. Network retries on timeout can create duplicate resources.

**Recommendation:** Support optional `Idempotency-Key` header on all POST operations.

---

### Finding #13 — Three Spec-Declared Endpoints Return 404 {#finding-13}

**Severity:** 🟡 LOW  
**Category:** Spec accuracy / Missing implementation

The following endpoints are declared in the OpenAPI spec v0.1.0 but return `404 Not Found` in the live API:

| Endpoint | Spec declares | Live API |
|----------|--------------|---------|
| `GET /devices/{id}/networkInterfaces` | 200 + interfaces array | 404 |
| `GET /devices/{id}/deepDive` | 200 + URL | 404 |
| `POST /firmwareUpdates` | 200/201 + update object | 404 |

**Impact:** Clients implementing spec-compliant integrations will encounter runtime failures. AI assistants relying on the spec will suggest calls that fail.

**Workaround:** Network interfaces are available in the device object itself (`GET /devices/{id}`). Firmware updates can only be listed and read, not created via API.

**Recommendation:** Remove endpoints from the spec until implemented, or mark them with `x-status: planned`.

---

### Finding #14 — `outputData` Field Undocumented in Firmware Update Jobs {#finding-14}

**Severity:** 🟡 LOW  
**Category:** Documentation gap

`outputData` appears on every firmware update object but is always `{}` in 20 live records. The spec declares it as `object` with no properties defined.

**Impact:** Integrators cannot parse success/failure details from completed jobs, forcing them to rely on `status` alone.

**Recommendation:** Document the `outputData` schema for each `status` value, especially `finished_with_errors`.
