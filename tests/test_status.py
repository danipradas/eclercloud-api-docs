"""
Tests for GET /health — Status tag.

The health endpoint is the simplest endpoint in the API: it requires no
authentication and always returns {"result": "ok"} when the service is up.
It is a useful smoke test to run before anything else to confirm basic
connectivity to the API.

Covered scenarios:
  - Happy path: 200 response with correct body.
  - No-auth: endpoint works without an Authorization header.
"""

import logging
import os

import requests
from conftest import assert_status
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://api.cloud.ecler.com")

logger = logging.getLogger(__name__)


def test_health_returns_200():
    """GET /health must respond with HTTP 200.

    This is the primary connectivity check. If this test fails the API is
    either unreachable or returning an unexpected error.
    """
    logger.info("GET %s/health", BASE_URL)
    resp = requests.get(f"{BASE_URL}/health")
    assert_status(resp, 200)


def test_health_body_contains_result_ok():
    """Response body must be {"result": "ok"}.

    Validates that:
      - The JSON body contains the ``result`` key.
      - The value of ``result`` is exactly the string ``"ok"``.
    """
    resp = requests.get(f"{BASE_URL}/health")
    assert_status(resp, 200)

    data = resp.json()
    assert "result" in data, (
        f"Response body missing 'result' key. Got: {data}"
    )
    assert data["result"] == "ok", (
        f"Expected result='ok', got result={data['result']!r}. Full body: {data}"
    )


def test_health_no_auth_required():
    """GET /health must succeed without an Authorization header.

    The health endpoint is intentionally public so it can be used for
    uptime monitoring without needing credentials.
    """
    # Explicitly pass an empty headers dict to confirm no token is sent.
    resp = requests.get(f"{BASE_URL}/health", headers={})
    assert_status(resp, 200)
    logger.info("Health check passed without auth — body: %s", resp.json())
