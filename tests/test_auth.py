"""
Tests for the Auth tag endpoints:
  - POST /auth/token  — request a new Bearer token
  - DELETE /auth/token — invalidate the current token

Authentication is the entry point for every other API operation.
These tests validate both the happy path and key error cases (bad credentials,
post-invalidation access).

Note on session fixture interaction:
    ``test_token_invalidation`` uses the shared ``token`` fixture but does NOT
    call DELETE /auth/token, to avoid breaking the session token relied on by
    other test modules.  A separate dedicated token is used for the full
    create→use→delete→verify cycle in ``test_token_delete_invalidates``.
"""

import logging
import os

import requests
from conftest import BASE_URL, assert_status
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def test_token_request_success():
    """POST /auth/token with valid credentials must return HTTP 200.

    This is the primary authentication smoke test.  A failure here means no
    other authenticated test will work.
    """
    logger.info("POST %s/auth/token with valid credentials", BASE_URL)
    resp = requests.post(
        f"{BASE_URL}/auth/token",
        json={
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
        },
    )
    assert_status(resp, 200)


def test_token_response_fields():
    """Token response body must contain ``access_token`` and ``expires_in``.

    Validates the response schema defined in the OpenAPI spec:
      - ``access_token``: non-empty string (the JWT Bearer token).
      - ``expires_in``: numeric value (seconds until expiry).
    """
    resp = requests.post(
        f"{BASE_URL}/auth/token",
        json={
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
        },
    )
    assert_status(resp, 200)
    data = resp.json()

    assert "access_token" in data, (
        f"Response missing 'access_token'. Body: {data}"
    )
    assert "expires_in" in data, (
        f"Response missing 'expires_in'. Body: {data}"
    )
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0, (
        f"'access_token' must be a non-empty string. Got: {data['access_token']!r}"
    )
    assert isinstance(data["expires_in"], (int, float)), (
        f"'expires_in' must be numeric. Got: {type(data['expires_in']).__name__!r}"
    )
    logger.info("Token expires_in=%s seconds", data["expires_in"])


def test_invalid_credentials_returns_400():
    """POST /auth/token with bad credentials must return HTTP 400.

    The API should reject obviously wrong credentials with a 400 Bad Request
    rather than a 401/403, per the OpenAPI spec.
    """
    logger.info("POST %s/auth/token with invalid credentials (expecting 400)", BASE_URL)
    resp = requests.post(
        f"{BASE_URL}/auth/token",
        json={"client_id": "invalid_id", "client_secret": "invalid_secret"},
    )
    assert_status(resp, 400)


def test_token_grants_api_access(token):
    """A valid token must grant access to authenticated endpoints.

    Uses the session token to call GET /organization and verifies that the
    response is not a 403 Forbidden — i.e., the token is accepted.

    Note: 404 is allowed here because the organization may legitimately not
    exist for this client; what matters is that auth was accepted (not 403).
    """
    headers = {"Authorization": f"Bearer {token}"}
    logger.info("Verifying token grants access to GET /organization")
    resp = requests.get(f"{BASE_URL}/organization", headers=headers)

    assert resp.status_code in (200, 404), (
        f"Expected 200 or 404 (auth accepted), got {resp.status_code}.\n"
        f"  URL : {resp.url}\n"
        f"  Body: {resp.text}"
    )


def test_token_delete_invalidates():
    """DELETE /auth/token must invalidate the token immediately.

    Full lifecycle test:
      1. Request a dedicated short-lived token.
      2. Call DELETE /auth/token to invalidate it.
      3. Confirm that using the invalidated token returns 403.

    A separate token is used (not the session fixture) so that invalidation
    does not affect other test modules.
    """
    # Step 1: obtain a fresh, dedicated token.
    logger.info("Requesting a dedicated token for invalidation test")
    create_resp = requests.post(
        f"{BASE_URL}/auth/token",
        json={
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
        },
    )
    assert_status(create_resp, 200)
    temp_token = create_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {temp_token}"}

    # Step 2: invalidate the token.
    logger.info("DELETE %s/auth/token — invalidating token", BASE_URL)
    delete_resp = requests.delete(f"{BASE_URL}/auth/token", headers=headers)
    assert_status(delete_resp, 204)

    # Step 3: confirm the token is now rejected.
    logger.info("Verifying invalidated token is rejected")
    check_resp = requests.get(f"{BASE_URL}/organization", headers=headers)
    assert check_resp.status_code == 403, (
        f"Expected 403 after token deletion, got {check_resp.status_code}.\n"
        f"  Body: {check_resp.text}\n"
        f"  Hint: The token may still be valid (caching?) or deletion failed silently."
    )
