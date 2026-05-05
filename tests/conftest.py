"""
Shared pytest configuration and fixtures for the EclerCLOUD API test suite.

This module is automatically loaded by pytest before any test file runs.
It provides:
  - Session-scoped OAuth2 token + Authorization headers fixtures, shared
    across all test modules to avoid redundant auth requests.
  - A helper for rich assertion failure messages that include the full
    HTTP request URL, status code, and response body.
  - A session-start log line confirming which BASE_URL is under test.

Environment variables (loaded from .env):
    CLIENT_ID      OAuth2 client ID
    CLIENT_SECRET  OAuth2 client secret
    BASE_URL       API base URL (default: https://api.cloud.ecler.com)
"""

import logging
import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://api.cloud.ecler.com")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Print the target API base URL once at session start.

    Runs before any test collection so the URL is visible at the top of every
    test run, making it immediately obvious which environment is under test.
    """
    # Use print so it appears even when log_cli is disabled.
    print(f"\n[conftest] Testing against BASE_URL: {BASE_URL}\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_status(resp: requests.Response, expected: int) -> None:
    """Assert that an HTTP response has the expected status code.

    On failure, raises AssertionError with the full URL, actual status code,
    and response body so the cause is immediately visible in the test output.

    Args:
        resp: The ``requests.Response`` object to check.
        expected: The HTTP status code that the test expects.

    Raises:
        AssertionError: If ``resp.status_code != expected``, with a diagnostic
            message containing the URL, actual code, and response body.

    Example::

        resp = requests.get(f"{BASE_URL}/health")
        assert_status(resp, 200)
    """
    assert resp.status_code == expected, (
        f"Expected HTTP {expected}, got {resp.status_code}\n"
        f"  URL : {resp.request.method} {resp.url}\n"
        f"  Body: {resp.text[:500]}"  # cap at 500 chars to keep output readable
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def token() -> str:
    """Obtain a valid OAuth2 Bearer token for the test session.

    Performs a single ``POST /auth/token`` request using credentials from
    the environment and caches the resulting token for the entire session.
    All test modules that require authentication should depend on this fixture
    (directly or via ``headers``) rather than issuing their own auth requests.

    Returns:
        The ``access_token`` string from the API response.

    Raises:
        AssertionError: If the token request fails (non-200 response), with
            the full status code and response body to aid diagnosis.
    """
    logger.info("Requesting session OAuth2 token from %s/auth/token", BASE_URL)
    resp = requests.post(
        f"{BASE_URL}/auth/token",
        json={
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
        },
    )
    assert resp.status_code == 200, (
        f"Auth token request failed — cannot run authenticated tests.\n"
        f"  URL    : POST {resp.url}\n"
        f"  Status : {resp.status_code}\n"
        f"  Body   : {resp.text}\n"
        f"  Hint   : Check CLIENT_ID and CLIENT_SECRET in your .env file."
    )
    access_token = resp.json()["access_token"]
    logger.info("Session token obtained (length=%d)", len(access_token))
    return access_token


@pytest.fixture(scope="session")
def headers(token: str) -> dict:
    """Return an Authorization header dict for authenticated API requests.

    Depends on the ``token`` fixture so the token is requested only once per
    session.  Pass this fixture to any test function that calls a protected
    endpoint.

    Args:
        token: The Bearer token provided by the ``token`` fixture.

    Returns:
        A dict suitable for use as the ``headers`` argument of any
        ``requests`` call, e.g. ``{"Authorization": "Bearer <token>"}``.

    Example::

        def test_get_organization(headers):
            resp = requests.get(f"{BASE_URL}/organization", headers=headers)
            assert resp.status_code == 200
    """
    return {"Authorization": f"Bearer {token}"}
