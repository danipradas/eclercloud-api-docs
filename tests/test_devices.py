"""
Tests for the Devices tag endpoints:
  - GET  /devices                     — list devices (paginated, filterable)
  - POST /devices                     — create a device
  - GET  /devices/{id}                — get device by ID
  - PUT  /devices/{id}                — update a device
  - DELETE /devices/{id}              — delete a device
  - GET  /devices/{id}/history        — historical data for a device
  - POST /devices/{id}/deepDive       — request a deep-dive URL
  - POST /devices/{id}/firmwareUpdates — trigger a firmware update

Tests that require a pre-existing device (e.g. get-by-id, history) will be
skipped automatically with pytest.skip() if the account has no registered
devices, rather than failing or passing vacuously.

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
# GET /devices — list
# ---------------------------------------------------------------------------

def test_list_devices_success(headers):
    """GET /devices must return HTTP 200 for an authenticated request."""
    logger.info("GET %s/devices", BASE_URL)
    resp = requests.get(f"{BASE_URL}/devices", headers=headers)
    assert_status(resp, 200)


def test_list_devices_pagination_fields(headers):
    """Response body must contain all required pagination envelope fields.

    Per the OpenAPI spec the response is a paginated envelope with:
      ``startPos``, ``pageSize``, ``totalCount``, ``items`` (array).
    """
    resp = requests.get(f"{BASE_URL}/devices", headers=headers)
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
        "Device list: totalCount=%s, returned=%s",
        data["totalCount"], len(data["items"]),
    )


def test_list_devices_page_size_respected(headers):
    """pageSize=10 must return at most 10 items."""
    resp = requests.get(f"{BASE_URL}/devices", headers=headers, params={"pageSize": 10})
    assert_status(resp, 200)
    items = resp.json()["items"]
    assert len(items) <= 10, (
        f"Expected at most 10 items with pageSize=10, got {len(items)}"
    )


def test_list_devices_filter_by_cloud_status(headers):
    """cloudStatus filter must only return devices with the requested status.

    Each item in the response is checked individually so that a mixed-status
    response is immediately identifiable.
    """
    resp = requests.get(
        f"{BASE_URL}/devices",
        headers=headers,
        params={"cloudStatus": "approved"},
    )
    assert_status(resp, 200)
    for device in resp.json()["items"]:
        assert device["cloudStatus"] == "approved", (
            f"Filter cloudStatus=approved returned device with status "
            f"{device['cloudStatus']!r} (id={device.get('id')})"
        )


def test_list_devices_requires_auth():
    """GET /devices without a token must return HTTP 403."""
    resp = requests.get(f"{BASE_URL}/devices")
    assert_status(resp, 403)


# ---------------------------------------------------------------------------
# GET /devices/{id} — by ID
# ---------------------------------------------------------------------------

def test_get_device_not_found(headers):
    """GET /devices/{id} with an unknown ID must return HTTP 404."""
    fake_id = "nonexistent-device-id-00000000"
    logger.info("GET %s/devices/%s (expecting 404)", BASE_URL, fake_id)
    resp = requests.get(f"{BASE_URL}/devices/{fake_id}", headers=headers)
    assert_status(resp, 404)


def test_get_device_by_id(headers):
    """GET /devices/{id} must return the device with the matching ID.

    Skipped if the account has no registered devices.
    """
    # Fetch the list first to obtain a real ID.
    list_resp = requests.get(f"{BASE_URL}/devices", headers=headers)
    assert_status(list_resp, 200)
    items = list_resp.json()["items"]

    if not items:
        pytest.skip("No devices registered in this account — skipping get-by-id test.")

    device_id = items[0]["id"]
    logger.info("GET %s/devices/%s", BASE_URL, device_id)
    resp = requests.get(f"{BASE_URL}/devices/{device_id}", headers=headers)
    assert_status(resp, 200)

    data = resp.json()
    assert data["id"] == device_id, (
        f"Returned device id {data['id']!r} does not match requested id {device_id!r}"
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_device_schema_fields(headers):
    """Each device object must contain the required schema fields.

    Validates the Device schema from the OpenAPI spec against the first
    device in the list.  Skipped if the account has no devices.
    """
    resp = requests.get(f"{BASE_URL}/devices", headers=headers)
    assert_status(resp, 200)
    items = resp.json()["items"]

    if not items:
        pytest.skip("No devices registered in this account — skipping schema test.")

    device = items[0]
    required_fields = ["id", "name", "model", "isOnline", "cloudStatus", "macAddress"]
    missing = [f for f in required_fields if f not in device]
    assert not missing, (
        f"Device schema missing fields: {missing}\n"
        f"  Device keys present: {list(device.keys())}"
    )

    # cloudStatus must be one of the enum values defined in the spec.
    valid_statuses = {"approved", "quarantined", "unapproved", "unpaired"}
    assert device["cloudStatus"] in valid_statuses, (
        f"cloudStatus {device['cloudStatus']!r} is not a valid enum value. "
        f"Expected one of: {valid_statuses}"
    )
    logger.info("Device schema OK for id=%s model=%s", device["id"], device.get("model"))


# ---------------------------------------------------------------------------
# GET /devices/{id}/history
# ---------------------------------------------------------------------------

def test_get_device_history(headers):
    """GET /devices/{id}/history must return a paginated history envelope.

    Skipped if the account has no registered devices.
    """
    list_resp = requests.get(f"{BASE_URL}/devices", headers=headers)
    assert_status(list_resp, 200)
    items = list_resp.json()["items"]

    if not items:
        pytest.skip("No devices registered in this account — skipping history test.")

    device_id = items[0]["id"]
    logger.info("GET %s/devices/%s/history", BASE_URL, device_id)
    resp = requests.get(f"{BASE_URL}/devices/{device_id}/history", headers=headers)
    assert_status(resp, 200)

    data = resp.json()
    for field in ("items", "totalCount"):
        assert field in data, (
            f"History envelope missing '{field}'. Got keys: {list(data.keys())}"
        )
    assert isinstance(data["items"], list), (
        f"'items' must be a list. Got: {type(data['items']).__name__!r}"
    )
    logger.info(
        "History for device %s: totalCount=%s", device_id, data["totalCount"]
    )
