# 05 — Open Questions for API Developers

These questions arise from gaps between the OpenAPI spec, observed API behavior, and missing documentation. They are grouped by topic. Answers to these questions would significantly improve integration quality.

---

## Authentication & Session Management

### Q1 — Is `expires_in` enforced server-side? {#q1}

`POST /auth/token` returns `expires_in: 3600`. Is this enforced, or informational only? Can an expired token still be used?

### Q2 — Is there a token refresh mechanism? {#q2}

The OAuth2 Client Credentials flow as implemented requires a full re-authentication after expiry. Is a refresh token or sliding expiry planned?

### Q3 — Will an introspection endpoint be added? {#q3}

Without `POST /auth/introspect` (RFC 7662), integrations cannot validate token state without making a dummy API call. Is this planned?

### Q4 — Is there rate limiting on `POST /auth/token`? {#q4}

No `Retry-After` or `X-RateLimit-*` headers were observed. Is there a backend rate limit? What happens after N failed attempts?

---

## Organisation & Pairing

### Q19 — Is `pairingToken` accessible only to admin roles? {#q19}

`GET /organization` returns `pairingToken` to any authenticated client. Is this intentional? Will scoped tokens restrict access?

### Q20 — Can the `pairingToken` be rotated? {#q20}

Is there an endpoint to rotate the `pairingToken`? If it is leaked, how can it be invalidated?

---

## Devices

### Q5 — What is `additionalParameters`? {#q5}

The `additionalParameters` array contains entries like `alarm.errors` and `health`. Who populates these — the device firmware or the API? What do the values mean? Is there a schema?

### Q6 — What does `alarm.errors` value format mean? {#q6}

`"00000000000000000000000000000000000000"` — is this a bitmask? A hex string? How do integrators parse alarm states from this field?

### Q7 — Why does `GET /devices/{id}/networkInterfaces` return 404? {#q7}

The spec declares this endpoint, but the live API returns `404 Not Found`. Network interfaces are available in the device object. Is this endpoint planned, deprecated, or was it removed?

### Q8 — Why does `GET /devices/{id}/deepDive` return 404? {#q8}

Same question as Q7. The spec describes a URL returned by this endpoint. What was it intended to return? Is it planned?

### Q9 — What does `deepDive` link to? {#q9}

If/when implemented: what URL does `deepDive` return? Is it time-limited? What is the TTL? What platform does it link to?

### Q10 — What is `automaticUpdateCron` format and who sets it? {#q10}

Observed value: `"29 8 * * 1"` (Monday 08:29 UTC). Is this standard cron? UTC timezone assumed? Who creates these jobs — the platform, or the device? Can it be cleared?

### Q11 — What happens to device history when a device is deleted? {#q11}

If `DELETE /devices/{id}` is called, are the history records also deleted? Is there a soft-delete / archival mechanism?

---

## Groups

### Q12 — What happens to child groups when a parent is deleted? {#q12}

If a group with `childGroups` is deleted, do the children become root-level groups, or are they deleted too?

### Q13 — What happens to devices in a group when the group is deleted? {#q13}

Are devices automatically ungrouped (`group: {}`), or is it an error to delete a non-empty group?

### Q14 — Does `PUT /groups/{id}/devices` replace or append? {#q14}

If a group has devices [A, B] and `PUT /groups/{id}/devices` is called with `[C]`, does the group become [C] (replace) or [A, B, C] (append)?

---

## Firmware Updates

### Q15 — When will `POST /firmwareUpdates` be available? {#q15}

The spec declares this endpoint but it returns 404. This is the only way to trigger firmware updates via API. When is it planned?

### Q16 — How are existing firmware update records created? {#q16}

The test account has 20 update records despite `POST /firmwareUpdates` being unavailable. Are these created by the `automaticUpdateCron` scheduler? Is there another code path?

### Q17 — What does `outputData` contain after a completed update? {#q17}

All 20 records in the test account have `"outputData": {}`. What is the intended schema for `finished` vs `finished_with_errors` statuses?

### Q18 — Is there a push notification for firmware update status changes? {#q18}

Must integrators poll `GET /firmwareUpdates/{id}` to track progress, or is there a webhook or MQTT message when status changes?

---

## MQTT

### Q19 — What does a successful `POST /mqtt/auth` response look like? {#q19}

A probe with an invalid token returns `400 / null body`. What does a valid device token return? `200 {}` or some credential payload?

### Q20 — Is there rate limiting on `POST /mqtt/auth`? {#q20}

This is a public unauthenticated endpoint. Is there any protection against systematic MAC address probing?

### Q21 — Is `deviceToken` always the MAC address? {#q21}

Observed: `macAddress: "D8:3A:DD:BF:57:FF"`. Is the `deviceToken` always the primary MAC? Is this documented? Could it change after a NIC replacement?

---

## API Design

### Q22 — Is v0.1.0 the production API version? {#q22}

Is a stable v1.0 release planned with a different URL prefix (`/v1/`)? Will v0.1.0 remain supported after that?

### Q23 — Is there a sandbox or staging environment? {#q23}

Is there a staging URL (e.g. `api.staging.cloud.ecler.com`) for integration testing without affecting production data?
