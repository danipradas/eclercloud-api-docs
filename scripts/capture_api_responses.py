"""
Probe the EclerCLOUD REST API and capture real response shapes.

Usage:
    uv run python scripts/capture_api_responses.py
    uv run python scripts/capture_api_responses.py --no-mutate
    uv run python scripts/capture_api_responses.py --device-id <UUID> --output out.json

Options:
    --device-id ID    UUID of the device to use for single-device probes.
                      Defaults to the first approved device in the account.
    --no-mutate       Skip all write operations (PUT/POST/DELETE).
                      Safe for CI/read-only environments.
    --output FILE     Write captured JSON to FILE instead of stdout.
"""

import argparse
import json
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("BASE_URL", "https://api.cloud.ecler.com")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

Results: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_token() -> str:
    resp = requests.post(
        f"{BASE}/auth/token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Probe functions
# ---------------------------------------------------------------------------

def probe_health() -> dict[str, Any]:
    resp = requests.get(f"{BASE}/health")
    return {"status": resp.status_code, "body": resp.json()}


def probe_organization(hdrs: dict) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/organization", headers=hdrs)
    return {"status": resp.status_code, "body": resp.json()}


def probe_devices(hdrs: dict) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/devices", headers=hdrs)
    data = resp.json()
    # Truncate items to 3 to keep output readable
    if "items" in data:
        data["items"] = data["items"][:3]
    return {"status": resp.status_code, "body": data}


def probe_device_detail(hdrs: dict, device_id: str) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/devices/{device_id}", headers=hdrs)
    return {"status": resp.status_code, "body": resp.json()}


def probe_device_history(hdrs: dict, device_id: str) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/devices/{device_id}/history", headers=hdrs)
    data = resp.json()
    if "items" in data:
        data["items"] = data["items"][:2]
    return {"status": resp.status_code, "body": data}


def probe_device_network_interfaces(hdrs: dict, device_id: str) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/devices/{device_id}/networkInterfaces", headers=hdrs)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    return {"status": resp.status_code, "body": body}


def probe_device_deep_dive(hdrs: dict, device_id: str) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/devices/{device_id}/deepDive", headers=hdrs)
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    return {"status": resp.status_code, "body": body}


def probe_device_mutate(hdrs: dict, device_id: str) -> dict[str, Any]:
    """Set notes to a test value then revert — captures PUT /devices/{id}."""
    original = requests.get(f"{BASE}/devices/{device_id}", headers=hdrs).json().get("notes", "")
    set_resp = requests.put(
        f"{BASE}/devices/{device_id}", headers=hdrs,
        json={"notes": "capture_api_responses probe — please ignore"},
    )
    revert = requests.put(f"{BASE}/devices/{device_id}", headers=hdrs, json={"notes": original})
    return {
        "set": {"status": set_resp.status_code, "notes_after": set_resp.json().get("notes")},
        "revert": {"status": revert.status_code},
    }


def probe_groups(hdrs: dict) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/groups", headers=hdrs)
    return {"status": resp.status_code, "body": resp.json()}


def probe_group_lifecycle(hdrs: dict) -> dict[str, Any]:
    """Full create → read → rename → delete cycle."""
    create = requests.post(
        f"{BASE}/groups", headers=hdrs,
        json={"name": "capture-probe-group", "description": "Temporary, will be deleted"},
    )
    if create.status_code not in (200, 201):
        return {"error": "create failed", "status": create.status_code, "body": create.json()}

    gid = create.json()["id"]
    get_resp = requests.get(f"{BASE}/groups/{gid}", headers=hdrs)
    rename = requests.put(f"{BASE}/groups/{gid}", headers=hdrs, json={"name": "capture-probe-group-renamed"})
    delete = requests.delete(f"{BASE}/groups/{gid}", headers=hdrs)
    verify = requests.get(f"{BASE}/groups/{gid}", headers=hdrs)

    return {
        "create": {"status": create.status_code, "id": gid},
        "get": {"status": get_resp.status_code},
        "rename": {"status": rename.status_code},
        "delete": {"status": delete.status_code},
        "verify_gone": {"status": verify.status_code},
    }


def probe_firmware_updates(hdrs: dict) -> dict[str, Any]:
    resp = requests.get(f"{BASE}/firmwareUpdates", headers=hdrs)
    data = resp.json()
    if "items" in data:
        data["items"] = data["items"][:3]
    return {"status": resp.status_code, "body": data}


def probe_firmware_update_post(hdrs: dict, device_id: str) -> dict[str, Any]:
    resp = requests.post(f"{BASE}/firmwareUpdates", headers=hdrs, json={"deviceId": device_id})
    body = resp.json() if resp.content else {}
    return {"status": resp.status_code, "body": body}


def probe_mqtt_auth() -> dict[str, Any]:
    resp = requests.post(f"{BASE}/mqtt/auth", json={"deviceToken": "probe-only-invalid-token"})
    body = resp.json() if resp.content else None
    return {"status": resp.status_code, "body": body}


def probe_error_cases(hdrs: dict) -> dict[str, Any]:
    no_auth = requests.get(f"{BASE}/organization")
    bad_token = requests.get(f"{BASE}/organization", headers={"Authorization": "Bearer invalid_xyz"})
    bad_creds = requests.post(f"{BASE}/auth/token", json={"client_id": "bad", "client_secret": "bad"})
    return {
        "no_auth": {"status": no_auth.status_code, "body": no_auth.json()},
        "bad_token": {"status": bad_token.status_code, "body": bad_token.json()},
        "bad_creds": {"status": bad_creds.status_code, "body": bad_creds.text},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def resolve_device_id(hdrs: dict, provided: str | None) -> str:
    if provided:
        return provided
    resp = requests.get(f"{BASE}/devices", headers=hdrs, params={"cloudStatus": "approved"})
    items = resp.json().get("items", [])
    if not items:
        raise ValueError("No approved devices found — pass --device-id explicitly")
    return items[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe EclerCLOUD API and capture response shapes.")
    parser.add_argument("--device-id", metavar="UUID", help="Device UUID to use for single-device probes")
    parser.add_argument("--no-mutate", action="store_true", help="Skip all write operations (PUT/POST/DELETE)")  # noqa: E501
    parser.add_argument("--output", metavar="FILE", help="Write JSON output to FILE (default: stdout)")
    args = parser.parse_args()

    print("Authenticating...", file=sys.stderr)
    token = get_token()
    hdrs = auth_headers(token)
    print(f"Token acquired ({len(token)} chars)", file=sys.stderr)

    results: dict[str, Any] = {}

    results["health"] = probe_health()
    results["organization"] = probe_organization(hdrs)
    results["devices"] = probe_devices(hdrs)

    device_id = resolve_device_id(hdrs, args.device_id)
    print(f"Using device: {device_id}", file=sys.stderr)

    results["device_detail"] = probe_device_detail(hdrs, device_id)
    results["device_history"] = probe_device_history(hdrs, device_id)
    results["device_network_interfaces"] = probe_device_network_interfaces(hdrs, device_id)
    results["device_deep_dive"] = probe_device_deep_dive(hdrs, device_id)

    if not args.no_mutate:
        results["device_mutate_notes"] = probe_device_mutate(hdrs, device_id)

    results["groups"] = probe_groups(hdrs)

    if not args.no_mutate:
        results["group_lifecycle"] = probe_group_lifecycle(hdrs)

    results["firmware_updates"] = probe_firmware_updates(hdrs)

    if not args.no_mutate:
        results["firmware_update_post"] = probe_firmware_update_post(hdrs, device_id)

    results["mqtt_auth"] = probe_mqtt_auth()
    results["error_cases"] = probe_error_cases(hdrs)

    output = json.dumps(results, indent=2, default=str)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
