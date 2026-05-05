# EclerCLOUD API — Integration Report

**API version:** v0.1.0 · **Spec:** OpenAPI 3.0.3 · **Base URL:** `https://api.cloud.ecler.com`  
**Date:** 2026-05-04 · **Author:** Daniel Pradas (TFG — Neec Audio Barcelona)

---

## Purpose

This report documents the EclerCLOUD REST API from the perspective of a **system integrator building an AI assistant** (MCP server) that lets users control and monitor Ecler professional audio devices using natural language.

Every endpoint includes:
- A realistic integrator prompt ("*Show me offline devices in the lobby*")
- The assistant's tool-call flow
- A real captured response
- Test coverage links

---

## Quick Navigation

| Section | What it covers |
|---------|---------------|
| [01 — Overview](01-overview.md) | Platform model, auth, pagination, error formats |
| [02 — Quickstart](02-quickstart.md) | Auth flow in Python & curl, token lifecycle |
| **Endpoints** | |
| [Auth](endpoints/auth.md) | `POST /auth/token`, `DELETE /auth/token` |
| [Status](endpoints/status.md) | `GET /health` |
| [Organization](endpoints/organization.md) | `GET /organization` |
| [Devices](endpoints/devices.md) | 8 endpoints — list, get, history, network, deepDive, PUT |
| [Groups](endpoints/groups.md) | 6 endpoints — full CRUD |
| [Firmware Updates](endpoints/firmware-updates.md) | 3 endpoints — list, get, create |
| [MQTT](endpoints/mqtt.md) | `POST /mqtt/auth` |
| [03 — Test Results](03-test-results.md) | All 35 tests: PASS/FAIL/SKIP with notes |
| [04 — Security](04-security.md) | 14 findings, severity-rated |
| [05 — Open Questions](05-open-questions.md) | 22 questions for API developers |
| [06 — MCP Blueprint](06-mcp-blueprint.md) | Proposed MCP server design for AI assistant |
| [07 — Claude Setup Review](07-claude-setup-review.md) | Best-practice review of this project's Claude Code setup |

---

## Executive Summary

The EclerCLOUD API provides **remote monitoring and control** of Ecler VIDA/HALO professional amplifiers through a cloud platform. It exposes 22 endpoints across 7 functional groups.

### Overall Assessment: ⚠️ Early-stage / Pre-production

| Dimension | Score | Summary |
|-----------|-------|---------|
| Functionality | 3/5 | Core read flows work well; several spec-declared endpoints return 404 |
| Spec accuracy | 2/5 | Multiple discrepancies between OpenAPI spec and real behavior |
| Security | 2/5 | No RBAC, public pairing token, public MQTT auth endpoint |
| Developer ergonomics | 3/5 | Consistent pagination; inconsistent error formats |
| AI-assistant readiness | 3/5 | Read operations are reliable; mutations and firmware endpoints need more coverage |

### Top 3 Findings

1. **Three spec-declared endpoints return 404** — `GET /devices/{id}/networkInterfaces`, `GET /devices/{id}/deepDive`, and `POST /firmwareUpdates` are documented in the OpenAPI spec but do not exist in the live API. See [Security Finding #13](04-security.md#finding-13).

2. **HTTP status codes are inverted vs. the spec** — Missing/invalid tokens return `400` (spec says `403`); bad client credentials return `403` (spec says `400`). This is a consistent discrepancy across all protected endpoints. See [Security Finding #6](04-security.md#finding-6).

3. **`pairingToken` is publicly readable by any valid client** — `GET /organization` returns the org pairing token in cleartext. Any authenticated user can use it to pair arbitrary devices. See [Security Finding #2](04-security.md#finding-2).

### Test Results Summary

| Result | Count |
|--------|-------|
| PASS | 26 |
| FAIL | 7 (all known spec vs. real API mismatches) |
| SKIP | 2 (no firmware updates in account at the time) |
| **Total** | **35** |

See [03-test-results.md](03-test-results.md) for the full table.

---

## Tested Account

Tests ran against a real account with:
- 2 devices: `VIVO-DP` (model VIVO-X8D8, approved, offline) and `VIDA_DP` (unpaired, no model)
- 0 groups (at test start; group lifecycle tests create and delete)
- 20 firmware update records (various statuses: `finished`, `finished_with_errors`, `pending`)
- Organization: "Dániel Pradas's Organisatión"

Device IDs and tokens are redacted in this report (`dev-uuid-1`, `dev-uuid-2`, `<token>`).
