"""
Tests for GET /organization — Organization tag.

The organization endpoint returns details for the organization associated
with the authenticated client credentials.  There is exactly one organization
per client ID.

Covered scenarios:
  - Happy path: 200 response with correct schema fields.
  - Auth enforcement: missing or invalid token returns 403.
"""

import logging

import requests
from conftest import BASE_URL, assert_status
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def test_get_organization_success(headers):
    """GET /organization with a valid token must return HTTP 200.

    Basic smoke test for the organization endpoint.
    """
    logger.info("GET %s/organization", BASE_URL)
    resp = requests.get(f"{BASE_URL}/organization", headers=headers)
    assert_status(resp, 200)


def test_get_organization_fields(headers):
    """Response body must contain ``name`` and ``pairingToken`` as strings.

    Validates the Organization schema from the OpenAPI spec:
      - ``name``: display name of the organization.
      - ``pairingToken``: token used to pair physical devices.
    """
    resp = requests.get(f"{BASE_URL}/organization", headers=headers)
    assert_status(resp, 200)
    data = resp.json()

    assert "name" in data, (
        f"Response missing 'name' field. Got keys: {list(data.keys())}"
    )
    assert "pairingToken" in data, (
        f"Response missing 'pairingToken' field. Got keys: {list(data.keys())}"
    )
    assert isinstance(data["name"], str), (
        f"'name' must be a string. Got {type(data['name']).__name__!r}: {data['name']!r}"
    )
    assert isinstance(data["pairingToken"], str), (
        f"'pairingToken' must be a string. Got {type(data['pairingToken']).__name__!r}"
    )
    logger.info("Organization name: %r", data["name"])


def test_get_organization_requires_auth():
    """GET /organization without an Authorization header must return HTTP 403.

    Verifies that the endpoint is not publicly accessible.
    """
    logger.info("GET %s/organization with no auth (expecting 403)", BASE_URL)
    resp = requests.get(f"{BASE_URL}/organization")
    assert_status(resp, 403)


def test_get_organization_invalid_token():
    """GET /organization with a garbage token must return HTTP 403.

    Verifies that the API rejects malformed or expired tokens rather than
    silently accepting them.
    """
    logger.info("GET %s/organization with invalid token (expecting 403)", BASE_URL)
    resp = requests.get(
        f"{BASE_URL}/organization",
        headers={"Authorization": "Bearer this_is_not_a_valid_token"},
    )
    assert_status(resp, 403)
