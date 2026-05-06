# eclercloud-api-docs

Documentation, test suite, and AI-assistant integration guide for the **EclerCLOUD REST API** — Ecler's cloud platform for remote monitoring and control of professional audio amplifiers, matrices, and other devices.

> TFG project — Ecler & Pompeu Fabra University / Daniel Pradas · API version: v0.1.0 · Python 3.13

---

## Contents

- [Quickstart](#quickstart)
- [Project Layout](#project-layout)
- [Documentation](#documentation)
- [Running the Tests](#running-the-tests)
- [API Probe Script](#api-probe-script)
- [Development](#development)
- [Key Findings](#key-findings)

---

## Quickstart

```bash
git clone <repo-url>
cd eclercloud-api-docs
cp .env.example .env          # fill in CLIENT_ID and CLIENT_SECRET
uv sync
uv run pytest tests/test_status.py   # smoke test — no credentials needed
uv run pytest tests/ -v              # full suite
```

---

## Project Layout

```
.
├── spec/
│   └── openapi.json                   # OpenAPI 3.0.3 spec (source of truth)
├── docs/
│   ├── README.md                      # Documentation index
│   ├── 01-overview.md                 # Platform model, auth, pagination, error formats
│   ├── 02-quickstart.md               # Auth flow and MCP integration pattern
│   ├── endpoints/                     # Per-tag endpoint reference (7 files)
│   │   ├── auth.md
│   │   ├── devices.md
│   │   ├── firmware-updates.md
│   │   ├── groups.md
│   │   ├── mqtt.md
│   │   ├── organization.md
│   │   └── status.md
│   ├── 03-test-results.md             # All 35 tests: PASS / FAIL / SKIP
│   ├── 04-security.md                 # 14 security findings, severity-rated
│   ├── 05-open-questions.md           # 23 questions for API developers
│   ├── 06-mcp-blueprint.md            # Proposed MCP server design
│   └── 07-claude-setup-review.md      # Claude Code best-practice audit
├── tests/
│   ├── conftest.py                    # Session-scoped auth fixture
│   ├── test_auth.py
│   ├── test_devices.py
│   ├── test_firmware_updates.py
│   ├── test_groups.py
│   ├── test_organization.py
│   └── test_status.py
├── scripts/
│   └── capture_api_responses.py      # Live API probe CLI
├── .claude/
│   ├── agents/eclercloud-tester.md   # Subagent for delegated API testing
│   └── settings.json                 # MCP config + test-rerun hook
├── .env.example                      # Credential template
├── CLAUDE.md                         # Claude Code project instructions
└── pyproject.toml
```

---

## Documentation

**Start here:** [docs/README.md](docs/README.md)

Every endpoint has:
- A realistic **integrator use case** — e.g. *"Which devices in the lobby are offline?"*
- The **AI assistant flow**: tool call sequence + response formatting
- **Real captured response** from the live API
- **Test links** with line-number anchors into the test files

Quick links:
- [API Overview](docs/01-overview.md) — base URL, auth model, pagination, error formats
- [Endpoint Reference](docs/endpoints/) — all 22 endpoints
- [Security Findings](docs/04-security.md) — 14 findings (3 HIGH, 6 MEDIUM, 5 LOW)
- [MCP Blueprint](docs/06-mcp-blueprint.md) — how to build a natural-language interface on top of this API
- [Open Questions](docs/05-open-questions.md) — 23 questions for Ecler API developers

---

## Running the Tests

```bash
# Full suite
uv run pytest tests/ -v

# Single group
uv run pytest tests/test_devices.py -v

# No credentials needed (smoke test)
uv run pytest tests/test_status.py -v
```

All tests require credentials in `.env` except `test_status.py`.

**Expected result on the TFG account:**

| Result | Count | Notes |
|--------|-------|-------|
| PASS | 26 | |
| FAIL | 7 | All known spec vs. API status-code mismatches |
| SKIP | 2 | Conditional on account state |

The 7 failures are **not bugs in the test code** — they document real discrepancies between the OpenAPI spec and live API behaviour. See [docs/03-test-results.md](docs/03-test-results.md) for the full breakdown.

---

## API Probe Script

`scripts/capture_api_responses.py` calls every endpoint and captures real responses:

```bash
# Read-only — no mutations
uv run python scripts/capture_api_responses.py --no-mutate

# Full probe (creates + deletes a test group, mutates and reverts device notes)
uv run python scripts/capture_api_responses.py

# Specify a device and write output to a file
uv run python scripts/capture_api_responses.py \
  --device-id <UUID> \
  --output responses.json
```

---

## Development

```bash
# Install all deps (including dev group)
uv sync --all-groups

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

### Coding Agent setup

This project is configured for Claude Code or similar coding agents:

- **MCP server** — `dkmaker-mcp-rest-api` lets Claude call the API directly
- **Subagent** — `eclercloud-tester` handles delegated endpoint testing
- **Hook** — editing a `tests/test_*.py` file auto-runs that file's tests
- **Skills** — `api-testing`, `playwright-cli` available as slash commands

---

## Key Findings

Three endpoints declared in the OpenAPI spec **do not exist** in the live API (return 404):

| Endpoint | Spec says | Reality |
|----------|-----------|---------|
| `GET /devices/{id}/networkInterfaces` | Returns network interfaces | 404 |
| `GET /devices/{id}/deepDive` | Returns deep-dive URL | 404 |
| `POST /firmwareUpdates` | Creates update job | 404 |

HTTP status codes are **inverted** from the spec for error conditions: missing/invalid tokens return `400` (spec says `403`); bad credentials return `403` (spec says `400`).

Full security analysis: [docs/04-security.md](docs/04-security.md)
