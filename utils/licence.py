"""
utils/licence.py  –  Cloud-based license management
=====================================================
Replaces the on-premise hardware-UUID / local-file approach with calls to
our central license server hosted on Vercel.

All public function signatures are unchanged so the rest of the codebase
needs no modification.

Environment variables (set in Docker via --env or an .env file):
  LICENSE_KEY        – JWT license token issued to this customer
  LICENSE_SERVER_URL – Base URL of the Vercel license server
                       e.g. https://your-project.vercel.app
"""

import os
import json
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

from config import get_config

config = get_config()

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------
_HEARTBEAT_INTERVAL = 3600   # flush usage to server every hour
_VALIDATE_CACHE_TTL = 300    # re-validate at most every 5 minutes (avoids hammering Vercel free tier)
_OFFLINE_GRACE_SECONDS = 86400  # allow 24 h offline before failing validation

# ---------------------------------------------------------------------------
# Thread-safe in-memory state  (replaces local encrypted file)
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_state = {
    "valid": False,
    "remaining_credits": 0.0,
    "monthly_credits": 0.0,
    "expiry_date": None,          # datetime or None
    "last_validated_ts": 0.0,     # unix timestamp of last successful /validate
    "pending_hours": 0.0,         # hours accrued since last heartbeat
    "last_heartbeat_ts": 0.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _license_key() -> str:
    return os.environ.get("LICENSE_KEY", "").strip()


def _server_url() -> str:
    return os.environ.get("LICENSE_SERVER_URL", "").rstrip("/")


def _post(endpoint: str, payload: dict, timeout: int = 10) -> dict:
    """POST JSON to the license server. Returns parsed response dict or raises."""
    url = f"{_server_url()}{endpoint}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return json.loads(raw)
        except Exception:
            raise RuntimeError(f"HTTP {e.code}: {raw.decode(errors='replace')}")


# ---------------------------------------------------------------------------
# Background heartbeat thread
# ---------------------------------------------------------------------------

def _flush_heartbeat(extra_hours: float = 0.0):
    """Send accumulated hours to the server; refresh remaining_credits in state."""
    key = _license_key()
    if not key or not _server_url():
        return
    with _state_lock:
        hours = _state["pending_hours"] + extra_hours
        _state["pending_hours"] = 0.0
    try:
        resp = _post("/api/license/heartbeat", {
            "license_key": key,
            "hours_used": hours,
        })
        with _state_lock:
            if resp.get("valid"):
                _state["remaining_credits"] = float(resp.get("remaining_credits", 0))
                _state["monthly_credits"] = float(resp.get("monthly_credits", 0))
                _state["last_heartbeat_ts"] = time.time()
                config.OFFLINE_LICENSE_LIMIT_HOURS = _state["remaining_credits"]
                config.MONTHLY_RENEWAL_CREDITS = _state["monthly_credits"]
            else:
                _state["valid"] = False
    except Exception as e:
        # Non-fatal: keep operating with cached values
        print(f"[licence] Heartbeat failed: {e}")


def _heartbeat_worker():
    """Daemon thread: flush pending usage every _HEARTBEAT_INTERVAL seconds."""
    while True:
        time.sleep(_HEARTBEAT_INTERVAL)
        _flush_heartbeat()


# Start daemon heartbeat thread once at import time
_heartbeat_thread = threading.Thread(target=_heartbeat_worker, daemon=True)
_heartbeat_thread.start()


# ---------------------------------------------------------------------------
# Public API  (function names & signatures unchanged)
# ---------------------------------------------------------------------------

def encrypt_data_update(data, expiry_date, hourly_credits, renewal_credits, recent_date, password):  # used in base
    """
    No-op stub retained for import compatibility.
    Encryption is now handled server-side and is never called in cloud mode.
    """
    raise NotImplementedError(
        "encrypt_data_update is not used in cloud deployment mode."
    )


def update_usage_hours(hrs):  # used in index
    """
    Accumulate hours consumed locally; the background thread flushes them to
    the license server every hour (or immediately if overdue).
    """
    try:
        with _state_lock:
            _state["pending_hours"] += float(hrs)
        # Flush immediately if it has been more than _HEARTBEAT_INTERVAL since last sync
        with _state_lock:
            since_last = time.time() - _state["last_heartbeat_ts"]
        if since_last >= _HEARTBEAT_INTERVAL:
            _flush_heartbeat()
    except Exception as e:
        print(f"[licence] Error updating usage hours: {e}")


def get_recent_date():  # used in index
    """Return the most recently recorded datetime."""
    return config.RECENT_DATE


def set_recent_date(dt):  # used in index and licence
    """Persist the most recently seen datetime into config."""
    try:
        config.RECENT_DATE = dt
    except Exception as e:
        print(f"[licence] Error setting recent date: {e}")


def check_licence_validation() -> int:
    """
    Validate the license against the remote server.
    Returns 1 if valid, 0 otherwise.

    - Caches the result for _VALIDATE_CACHE_TTL seconds to stay within
      Vercel free-tier rate limits (~3000 req/day).
    - Grants a 24-hour offline grace period if the server is unreachable
      but the last known state was valid.
    """
    key = _license_key()
    server = _server_url()

    if not key:
        print("[licence] LICENSE_KEY environment variable is not set.")
        return 0
    if not server:
        print("[licence] LICENSE_SERVER_URL environment variable is not set.")
        return 0

    # Return cached result if still fresh
    with _state_lock:
        age = time.time() - _state["last_validated_ts"]
        cached_valid = _state["valid"]
    if _state["last_validated_ts"] > 0 and age < _VALIDATE_CACHE_TTL:
        return 1 if cached_valid else 0

    try:
        resp = _post("/api/license/validate", {"license_key": key})
    except Exception as e:
        print(f"[licence] Validation request failed: {e}")
        # Offline grace: allow operation for up to 24 h after last successful validation
        with _state_lock:
            still_in_grace = (
                _state["valid"]
                and (time.time() - _state["last_validated_ts"]) < _OFFLINE_GRACE_SECONDS
            )
        if still_in_grace:
            print("[licence] Using cached validation (offline grace period active).")
            return 1
        return 0

    with _state_lock:
        if resp.get("valid"):
            _state["valid"] = True
            _state["last_validated_ts"] = time.time()
            _state["remaining_credits"] = float(resp.get("remaining_credits", 0))
            _state["monthly_credits"] = float(resp.get("monthly_credits", 0))

            # Sync expiry into config
            expiry_str = resp.get("expiry_date")
            if expiry_str:
                try:
                    config.EXPIRYDATE = datetime.fromisoformat(expiry_str)
                except Exception:
                    pass

            config.OFFLINE_LICENSE_LIMIT_HOURS = _state["remaining_credits"]
            config.MONTHLY_RENEWAL_CREDITS = _state["monthly_credits"]

            now = datetime.now()
            if now > config.RECENT_DATE:
                config.RECENT_DATE = now

            return 1
        else:
            _state["valid"] = False
            _state["last_validated_ts"] = time.time()
            print(f"[licence] License invalid: {resp.get('error', 'unknown reason')}")
            return 0


def create_licence_requirement():  # used in app
    """
    In cloud mode there is no hardware UUID to capture.
    Returns guidance telling the customer to set their environment variables.
    """
    key = _license_key()
    if key:
        return {
            "success": False,
            "status": (
                "A LICENSE_KEY is set but validation failed. "
                "Please contact support to renew or replace your key."
            ),
        }, 403

    return {
        "success": False,
        "status": (
            "No LICENSE_KEY found. "
            "Please set the LICENSE_KEY and LICENSE_SERVER_URL environment "
            "variables in your Docker container and restart the service. "
            "Contact support if you need a new key."
        ),
    }, 402


def get_remaining_credit() -> float:  # used in app
    """Return remaining hourly credits from the last server response."""
    with _state_lock:
        return _state["remaining_credits"]