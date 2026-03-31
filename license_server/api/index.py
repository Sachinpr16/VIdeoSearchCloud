"""
License Server – Vercel Serverless (Python)
============================================
All logic lives in a single file so Vercel's Python runtime can serve it.

Environment variables expected on Vercel:
  LICENSE_SECRET   – HMAC-SHA256 signing secret for JWT license tokens
  ADMIN_SECRET     – Shared secret to protect the /generate endpoint
  REDIS_URL        – Redis connection URL (e.g. redis://default:<password>@host:port)

KV key layout:
  usage:<customer_id>   → JSON  { "used_hours": float, "last_reset_month": "YYYY-MM" }

A license key is a signed JWT with payload:
  {
    "sub":             "<customer_id>",
    "exp":             <unix-ts expiry>,
    "monthly_credits": <float>,
    "iat":             <unix-ts issued-at>
  }

Vercel free-tier constraints respected:
  - No background workers; state is stored in Vercel KV (free: 256 MB, 3000 req/day).
  - Cold starts are fast because there are no heavy imports.
  - Each handler is a plain WSGI-compatible function (http.server style wrapped by Vercel).
"""

import json
import os
import time
import hmac
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
import redis

# ---------------------------------------------------------------------------
# JWT helpers (pure-stdlib, no PyJWT needed at runtime on Vercel)
# ---------------------------------------------------------------------------
import base64


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _jwt_sign(payload: dict, secret: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _jwt_verify(token: str, secret: str) -> dict:
    """Return decoded payload or raise ValueError."""
    try:
        header_b64, body_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("Malformed token")
    signing_input = f"{header_b64}.{body_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(body_b64))
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")
    return payload


# ---------------------------------------------------------------------------
# Redis helpers  (uses REDIS_URL env var)
# ---------------------------------------------------------------------------

_redis_client = None

def _get_redis():
    """Return a cached Redis client, connecting via REDIS_URL."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            os.environ["REDIS_URL"],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def _kv_get(key: str):
    """Return parsed JSON value or None."""
    try:
        raw = _get_redis().get(key)
        return raw  # None if key absent
    except Exception:
        return None


def _kv_set(key: str, value) -> bool:
    """Set key to JSON-encoded value. Returns True on success."""
    try:
        _get_redis().set(key, value)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def _get_or_init_usage(customer_id: str, monthly_credits: float) -> dict:
    raw = _kv_get(f"usage:{customer_id}")
    if raw:
        try:
            usage = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            usage = {}
    else:
        usage = {}

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if usage.get("last_reset_month") != current_month:
        # New month – reset credits
        usage = {"used_hours": 0.0, "last_reset_month": current_month}
    if "used_hours" not in usage:
        usage["used_hours"] = 0.0
    return usage


def _save_usage(customer_id: str, usage: dict):
    _kv_set(f"usage:{customer_id}", json.dumps(usage))


def _remaining_credits(usage: dict, monthly_credits: float) -> float:
    return max(0.0, monthly_credits - usage["used_hours"])


# ---------------------------------------------------------------------------
# Request / Response helpers
# ---------------------------------------------------------------------------

def _read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    try:
        return json.loads(handler.rfile.read(length))
    except Exception:
        return {}


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

LICENSE_SECRET_ENV = "LICENSE_SECRET"
ADMIN_SECRET_ENV = "ADMIN_SECRET"


def _handle_status(handler: BaseHTTPRequestHandler):
    """GET /api/license/status – health check"""
    _send_json(handler, 200, {"status": "ok", "ts": int(time.time())})


def _handle_generate(handler: BaseHTTPRequestHandler):
    """
    POST /api/license/generate
    Body: { "admin_secret": "...", "customer_id": "...", "expiry_date": "YYYY-MM-DD", "monthly_credits": 1000 }
    Returns: { "license_key": "<JWT>" }
    Protected by ADMIN_SECRET env var.
    """
    body = _read_body(handler)
    admin_secret = os.environ.get(ADMIN_SECRET_ENV, "")
    if not admin_secret or body.get("admin_secret") != admin_secret:
        _send_json(handler, 403, {"error": "Forbidden"})
        return

    customer_id = body.get("customer_id", "").strip()
    expiry_str = body.get("expiry_date", "")
    monthly_credits = float(body.get("monthly_credits", 1000))

    if not customer_id or not expiry_str:
        _send_json(handler, 400, {"error": "customer_id and expiry_date are required"})
        return

    try:
        expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        _send_json(handler, 400, {"error": "expiry_date must be YYYY-MM-DD"})
        return

    secret = os.environ.get(LICENSE_SECRET_ENV, "")
    if not secret:
        _send_json(handler, 500, {"error": "Server misconfigured: LICENSE_SECRET not set"})
        return

    payload = {
        "sub": customer_id,
        "exp": int(expiry_dt.timestamp()),
        "monthly_credits": monthly_credits,
        "iat": int(time.time()),
    }
    token = _jwt_sign(payload, secret)
    _send_json(handler, 200, {"license_key": token, "customer_id": customer_id,
                               "expiry_date": expiry_str, "monthly_credits": monthly_credits})


def _handle_validate(handler: BaseHTTPRequestHandler):
    """
    POST /api/license/validate
    Body: { "license_key": "<JWT>" }
    Returns: { "valid": true, "customer_id": "...", "expiry_date": "...",
               "monthly_credits": 1000, "remaining_credits": 750.5 }
    """
    body = _read_body(handler)
    license_key = body.get("license_key", "").strip()
    if not license_key:
        _send_json(handler, 400, {"error": "license_key is required"})
        return

    secret = os.environ.get(LICENSE_SECRET_ENV, "")
    try:
        payload = _jwt_verify(license_key, secret)
    except ValueError as e:
        _send_json(handler, 200, {"valid": False, "error": str(e)})
        return

    customer_id = payload["sub"]
    monthly_credits = float(payload.get("monthly_credits", 1000))
    usage = _get_or_init_usage(customer_id, monthly_credits)
    remaining = _remaining_credits(usage, monthly_credits)
    expiry_ts = payload.get("exp", 0)
    expiry_iso = datetime.fromtimestamp(expiry_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    _send_json(handler, 200, {
        "valid": True,
        "customer_id": customer_id,
        "expiry_date": expiry_iso,
        "monthly_credits": monthly_credits,
        "remaining_credits": remaining,
    })


def _handle_heartbeat(handler: BaseHTTPRequestHandler):
    """
    POST /api/license/heartbeat
    Body: { "license_key": "<JWT>", "hours_used": <float> }
    Increments the stored usage counter and returns remaining credits.
    Returns: { "valid": true, "remaining_credits": <float>, "monthly_credits": <float> }
    """
    body = _read_body(handler)
    license_key = body.get("license_key", "").strip()
    hours_used = float(body.get("hours_used", 0))
    hours_used = max(0.0, hours_used)

    if not license_key:
        _send_json(handler, 400, {"error": "license_key is required"})
        return

    secret = os.environ.get(LICENSE_SECRET_ENV, "")
    try:
        payload = _jwt_verify(license_key, secret)
    except ValueError as e:
        _send_json(handler, 200, {"valid": False, "error": str(e)})
        return

    customer_id = payload["sub"]
    monthly_credits = float(payload.get("monthly_credits", 1000))
    usage = _get_or_init_usage(customer_id, monthly_credits)
    usage["used_hours"] = usage.get("used_hours", 0.0) + hours_used
    _save_usage(customer_id, usage)
    remaining = _remaining_credits(usage, monthly_credits)

    _send_json(handler, 200, {
        "valid": True,
        "remaining_credits": remaining,
        "monthly_credits": monthly_credits,
        "customer_id": customer_id,
    })


# ---------------------------------------------------------------------------
# Vercel entry-point
# Vercel's Python runtime calls handler(request, response) where both are
# http.server.BaseHTTPRequestHandler-compatible objects.
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):
    """Single handler class that Vercel will instantiate per request."""

    def log_message(self, format, *args):
        pass  # Suppress default stderr logging; Vercel captures stdout

    def _route(self):
        path = self.path.split("?")[0].rstrip("/")
        method = self.command

        if path == "/api/license/status" and method == "GET":
            _handle_status(self)
        elif path == "/api/license/generate" and method == "POST":
            _handle_generate(self)
        elif path == "/api/license/validate" and method == "POST":
            _handle_validate(self)
        elif path == "/api/license/heartbeat" and method == "POST":
            _handle_heartbeat(self)
        else:
            _send_json(self, 404, {"error": "Not found"})

    def do_GET(self):
        self._route()

    def do_POST(self):
        self._route()
