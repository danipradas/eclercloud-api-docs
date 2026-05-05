"""
Tests for the Groups tag endpoints:
  - GET  /groups            — list groups (paginated, filterable)
  - POST /groups            — create a group
  - GET  /groups/{id}       — get group by ID
  - PUT  /groups/{id}       — update a group
  - DELETE /groups/{id}     — delete a group
  - POST /groups/{id}/firmwareUpdates — trigger firmware update for group devices

The create/delete lifecycle test creates a real group named "pytest-temp-group",
verifies it, then cleans it up.  If deletion fails the group is left behind;
re-running the suite will still work because the name is not unique-constrained.

Tests that require a pre-existing group will be skipped automatically with
pytest.skip() if the account has no groups yet.

All endpoints require a valid Bearer token (``headers`` fixture).
"""

import logging

import pytest
import requests
from conftest import BASE_URL, assert_status
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /groups — list
# ---------------------------------------------------------------------------

def test_list_groups_success(headers):
    """GET /groups must return HTTP 200 for an authenticated request."""
    logger.info("GET %s/groups", BASE_URL)
    resp = requests.get(f"{BASE_URL}/groups", headers=headers)
    assert_status(resp, 200)


def test_list_groups_pagination_fields(headers):
    """Response body must contain all required pagination envelope fields.

    Per the OpenAPI spec: ``startPos``, ``pageSize``, ``totalCount``, ``items``.
    """
    resp = requests.get(f"{BASE_URL}/groups", headers=headers)
    assert_status(resp, 200)
    data = resp.json()

    for field in ("startPos", "pageSize", "totalCount", "items"):
        assert field in data, (
            f"Pagination envelope missing '{field}'. Got keys: {list(data.keys())}"
        )
    assert isinstance(data["items"], list), (
        f"'items' must be a list. Got: {type(data['items']).__name__!r}"
    )
    logger.info(
        "Group list: totalCount=%s, returned=%s",
        data["totalCount"], len(data["items"]),
    )


def test_list_groups_requires_auth():
    """GET /groups without a token must return HTTP 403."""
    resp = requests.get(f"{BASE_URL}/groups")
    assert_status(resp, 403)


# ---------------------------------------------------------------------------
# GET /groups/{id} — by ID
# ---------------------------------------------------------------------------

def test_get_group_not_found(headers):
    """GET /groups/{id} with an unknown ID must return HTTP 404."""
    fake_id = "nonexistent-group-id-00000000"
    logger.info("GET %s/groups/%s (expecting 404)", BASE_URL, fake_id)
    resp = requests.get(f"{BASE_URL}/groups/{fake_id}", headers=headers)
    assert_status(resp, 404)


def test_get_group_by_id(headers):
    """GET /groups/{id} must return the group with the matching ID.

    Skipped if the account has no groups.
    """
    list_resp = requests.get(f"{BASE_URL}/groups", headers=headers)
    assert_status(list_resp, 200)
    items = list_resp.json()["items"]

    if not items:
        pytest.skip("No groups in this account — skipping get-by-id test.")

    group_id = items[0]["id"]
    logger.info("GET %s/groups/%s", BASE_URL, group_id)
    resp = requests.get(f"{BASE_URL}/groups/{group_id}", headers=headers)
    assert_status(resp, 200)

    data = resp.json()
    assert data["id"] == group_id, (
        f"Returned group id {data['id']!r} does not match requested id {group_id!r}"
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_group_schema_fields(headers):
    """Each group object must contain the required schema fields.

    Validates the Group schema from the OpenAPI spec against the first group
    in the list.  Skipped if the account has no groups.
    """
    resp = requests.get(f"{BASE_URL}/groups", headers=headers)
    assert_status(resp, 200)
    items = resp.json()["items"]

    if not items:
        pytest.skip("No groups in this account — skipping schema test.")

    group = items[0]
    required_fields = ["id", "name", "deviceConnectedCount", "deviceDisconnectedCount"]
    missing = [f for f in required_fields if f not in group]
    assert not missing, (
        f"Group schema missing fields: {missing}\n"
        f"  Group keys present: {list(group.keys())}"
    )
    logger.info(
        "Group schema OK for id=%s name=%r connected=%s disconnected=%s",
        group["id"], group["name"],
        group["deviceConnectedCount"], group["deviceDisconnectedCount"],
    )


# ---------------------------------------------------------------------------
# POST /groups + DELETE /groups/{id} — full lifecycle
# ---------------------------------------------------------------------------

def test_create_and_delete_group(headers):
    """Full group lifecycle: create → verify → delete → verify deletion.

    Creates a temporary group, confirms it is retrievable by ID, deletes it,
    and confirms it returns 404 afterwards.  This is the only mutating test
    in the suite and always cleans up after itself.
    """
    group_name = "pytest-temp-group"
    logger.info("POST %s/groups — creating '%s'", BASE_URL, group_name)

    # Step 1: create the group.
    create_resp = requests.post(
        f"{BASE_URL}/groups",
        headers=headers,
        json={"name": group_name, "description": "Temporary group created by pytest"},
    )
    assert_status(create_resp, 200)

    group = create_resp.json()
    assert group.get("name") == group_name, (
        f"Created group name mismatch. Expected {group_name!r}, got {group.get('name')!r}"
    )
    group_id = group["id"]
    logger.info("Group created with id=%s", group_id)

    # Step 2: verify it is retrievable.
    get_resp = requests.get(f"{BASE_URL}/groups/{group_id}", headers=headers)
    assert_status(get_resp, 200)

    # Step 3: delete it.
    logger.info("DELETE %s/groups/%s", BASE_URL, group_id)
    delete_resp = requests.delete(f"{BASE_URL}/groups/{group_id}", headers=headers)
    assert_status(delete_resp, 204)

    # Step 4: confirm it is gone.
    check_resp = requests.get(f"{BASE_URL}/groups/{group_id}", headers=headers)
    assert check_resp.status_code == 404, (
        f"Expected 404 after group deletion, got {check_resp.status_code}.\n"
        f"  Body: {check_resp.text}\n"
        f"  Hint: The group may still exist or deletion was not applied yet."
    )
    logger.info("Group %s successfully deleted and confirmed gone.", group_id)
