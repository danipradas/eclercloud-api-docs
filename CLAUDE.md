# EclerCLOUD API Documentation — CLAUDE.md

## Project Purpose

TFG project: document and test the EclerCLOUD REST API and provide an AI-assistant integration guide.
EclerCLOUD = Ecler's cloud platform for remote monitoring/control of professional audio equipment (VIDA/HALO series amplifiers).

## API

- **Base URL**: https://api.cloud.ecler.com
- **Spec**: `spec/openapi.json` (local copy) or https://api.cloud.ecler.com/documentation/json (live)
- **Auth**: OAuth2 Client Credentials → POST /auth/token → Bearer token (256 chars, 3600 s)
- **Endpoints**: 22 across 7 tags (Auth, Organization, Devices, Groups, Firmware Updates, MQTT, Status)
- **Known spec gaps**: 3 endpoints return 404 in live API: `GET /devices/{id}/networkInterfaces`, `GET /devices/{id}/deepDive`, `POST /firmwareUpdates`

## Credentials

Stored in `.env` (never commit). See `.env.example` for keys.
Load with `python-dotenv` in all scripts/tests.

## Project Structure

```
spec/openapi.json          — OpenAPI 3.0.3 spec (source of truth)
docs/README.md             — Documentation index
docs/01-overview.md        — Platform model, auth, pagination, error formats
docs/02-quickstart.md      — Auth flow, token lifecycle, MCP integration pattern
docs/endpoints/*.md        — Per-tag endpoint reference (NL use cases + real responses)
docs/03-test-results.md    — All 35 tests with PASS/FAIL/SKIP table
docs/04-security.md        — 14 security findings
docs/05-open-questions.md  — 23 questions for API developers
docs/06-mcp-blueprint.md   — Proposed MCP server design
docs/07-claude-setup-review.md — Claude Code best-practice audit
tests/                     — pytest suite (run: uv run pytest tests/ -v)
tests/conftest.py          — Session-scoped auth fixture
scripts/capture_api_responses.py — Live API probe CLI (--no-mutate for read-only)
```

## Installed Tools

### Skills (slash commands)
- `/api-testing` — generate or review Python test scripts
- `playwright-cli` — browser automation (scrape EclerCLOUD UI, take screenshots)

### Subagent: eclercloud-tester
`.claude/agents/eclercloud-tester.md` — pre-loaded with API surface + operating rules.
Use for: "test endpoint X with input Y", "capture real response for /groups", etc.

### MCP: rest-api (dkmaker-mcp-rest-api)
Lets Claude call API endpoints directly. Base URL pre-configured.
Auth: pass `Authorization: Bearer <token>` header.

### Hook: test-rerun
Defined in `.claude/settings.json` — runs `uv run pytest <file> -v --tb=short` automatically when a `tests/test_*.py` file is edited.

## Documentation Standards

- Endpoint docs live in `docs/endpoints/` — one file per tag group
- Every endpoint has: NL integrator use case, assistant flow, params table, Python + curl example, real captured response, test file links with line anchors
- Python examples use `requests` library + env vars from `.env`
- Never hardcode credentials

## Python Environment

- Runtime: uv + Python 3.13, venv at `.venv/`
- Install deps: `uv add <package>` (never pip)
- Run scripts: `uv run python scripts/capture_api_responses.py`
- Run tests: `uv run pytest tests/ -v`
- Lint: `uv run ruff check .`

## Testing Standards

- Framework: pytest + python-dotenv + requests
- Run all tests: `uv run pytest tests/ -v`
- Auth token shared via session-scoped fixture in `conftest.py`
- Test files: one per tag group
- Expected result on TFG account: 26 passed, 7 failed (spec mismatches), 2 skipped

## Platform UI

EclerCLOUD web app: https://cloud.ecler.com
Use `playwright-cli` skill to navigate and scrape the UI when needed.
