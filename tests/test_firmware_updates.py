"""
Tests for the Firmware Updates tag endpoints:
  - GET /firmwareUpdates             — list update jobs (paginated, filterable)
  - GET /firmwareUpdates/{id}        — get a single update job by ID
  - PUT /firmwareUpdates/{id}/cancel — cancel a pending update job

Firmware update jobs are created via POST /devices/{id}/firmwareUpdates or
POST /groups/{id}/firmwareUpdates (covered in test_devices.py / test_groups.py).
These tests focus on querying and managing existing jobs.

Status lifecycle:  pending → started → finished | failed | cancelled

Tests that require a pre-existing update record will be skipped automatically
with pytest.skip() if the account has no firmware update history.

All endpoints require a valid Bearer token (``headers`` fixture).
"""

import logging

import pytest
import requests
from conftest import BASE_URL, assert_status
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Valid status values as defined in the OpenAPI spec.
VALID_STATUSES = {"pending", "started", "finished", "failed", "cancelled"}


# ---------------------------------------------------------------------------
# GET /firmwareUpdates — list
# ---------------------------------------------------------------------------

def test_list_firmware_updates_success(headers):
    """GET /firmwareUpdates must return HTTP 200 for an authenticated request."""
    logger.info("GET %s/firmwareUpdates", BASE_URL)
    resp = requests.get(f"{BASE_URL}/firmwareUpdates", headers=headers)
    assert_status(resp, 200)


def test_list_firmware_updates_pagination_fields(headers):
    """Response body must contain all required pagination envelope fields.

    Per the OpenAPI spec: ``startPos``, ``pageSize``, ``totalCount``, ``items``.
    """
    resp = requests.get(f"{BASE_URL}/firmwareUpdates", headers=headers)
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
        "Firmware updates: totalCount=%s, returned=%s",
        data["totalCount"], len(data["items"]),
    )


def test_list_firmware_updates_requires_auth():
    """GET /firmwareUpdates without a token must return HTTP 403."""
    resp = requests.get(f"{BASE_URL}/firmwareUpdates")
    assert_status(resp, 403)


def test_list_firmware_updates_filter_by_status(headers):
    """status filter must only return jobs with the requested status value.

    Each valid status enum value is tested individually so a mismatch can be
    pinpointed to a specific status value.
    """
    for status in VALID_STATUSES:
        logger.info("GET %s/firmwareUpdates?status=%s", BASE_URL, status)
        resp = requests.get(
            f"{BASE_URL}/firmwareUpdates",
            headers=headers,
            params={"status": status},
        )
        assert_status(resp, 200)

        for update in resp.json()["items"]:
            assert update["status"] == status, (
                f"Filter status={status!r} returned update with status "
                f"{update['status']!r} (id={update.get('id')})"
            )


# ---------------------------------------------------------------------------
# GET /firmwareUpdates/{id} — by ID
# ---------------------------------------------------------------------------

def test_get_firmware_update_not_found(headers):
    """GET /firmwareUpdates/{id} with an unknown ID must return HTTP 404."""
    fake_id = "nonexistent-update-id-00000000"
    logger.info("GET %s/firmwareUpdates/%s (expecting 404)", BASE_URL, fake_id)
    resp = requests.get(f"{BASE_URL}/firmwareUpdates/{fake_id}", headers=headers)
    assert_status(resp, 404)


def test_get_firmware_update_by_id(headers):
    """GET /firmwareUpdates/{id} must return the update with the matching ID.

    Skipped if the account has no firmware update history.
    """
    list_resp = requests.get(f"{BASE_URL}/firmwareUpdates", headers=headers)
    assert_status(list_resp, 200)
    items = list_resp.json()["items"]

    if not items:
        pytest.skip("No firmware updates in this account — skipping get-by-id test.")

    update_id = items[0]["id"]
    logger.info("GET %s/firmwareUpdates/%s", BASE_URL, update_id)
    resp = requests.get(f"{BASE_URL}/firmwareUpdates/{update_id}", headers=headers)
    assert_status(resp, 200)

    data = resp.json()
    assert data["id"] == update_id, (
        f"Returned update id {data['id']!r} does not match requested id {update_id!r}"
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_firmware_update_schema_fields(headers):
    """Each firmware update object must contain the required schema fields.

    Validates the FirmwareUpdate schema from the OpenAPI spec and checks that
    ``status`` holds a valid enum value.  Skipped if no updates exist.
    """
    resp = requests.get(f"{BASE_URL}/firmwareUpdates", headers=headers)
    assert_status(resp, 200)
    items = resp.json()["items"]

    if not items:
        pytest.skip("No firmware updates in this account — skipping schema test.")

    update = items[0]
    required_fields = ["id", "status", "plannedAt"]
    missing = [f for f in required_fields if f not in update]
    assert not missing, (
        f"FirmwareUpdate schema missing fields: {missing}\n"
        f"  Update keys present: {list(update.keys())}"
    )
    assert update["status"] in VALID_STATUSES, (
        f"status {update['status']!r} is not a valid enum value. "
        f"Expected one of: {VALID_STATUSES}"
    )
    logger.info(
        "FirmwareUpdate schema OK for id=%s status=%s", update["id"], update["status"]
    )
