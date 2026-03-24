# Cloud License Management – Setup Guide

## Architecture Overview

```
┌─────────────────────────┐          HTTPS          ┌──────────────────────────┐
│  Customer Docker        │ ─────────────────────── │  License Server (Vercel) │
│  Container              │                          │  /api/license/*          │
│                         │  POST /validate          │                          │
│  utils/licence.py       │ ───────────────────────► │  Verifies JWT signature  │
│  (no local key file,    │ ◄─────────────────────── │  Returns credits / expiry│
│   no hardware UUID)     │                          │                          │
│                         │  POST /heartbeat (hourly)│                          │
│                         │ ───────────────────────► │  Increments usage in KV  │
│                         │ ◄─────────────────────── │  Returns remaining credits│
└─────────────────────────┘                          └──────────────────────────┘
```

A **license key** is a self-contained, HMAC-SHA256-signed JWT. The server is
**stateless for validation** (it only checks the signature + expiry) and uses
**Vercel KV** only to track per-customer monthly usage.

---

## 1. Deploy the License Server on Vercel

### 1.1 Prerequisites
- A [Vercel](https://vercel.com) account (free tier is sufficient)
- Vercel CLI: `npm i -g vercel`
- A [Vercel KV](https://vercel.com/docs/storage/vercel-kv) store (free: 256 MB, 3 000 req/day)

### 1.2 Environment variables to set in Vercel dashboard

| Variable            | Description                                       | Example                    |
|---------------------|---------------------------------------------------|----------------------------|
| `LICENSE_SECRET`    | Random string used to sign all JWT tokens         | `openssl rand -hex 32`     |
| `ADMIN_SECRET`      | Password protecting the `/generate` endpoint      | `openssl rand -hex 16`     |
| `KV_REST_API_URL`   | Vercel KV REST endpoint (auto-set if you link KV) | `https://xxx.kv.vercel-storage.com` |
| `KV_REST_API_TOKEN` | Vercel KV bearer token (auto-set if you link KV)  | `AXxx…`                    |

### 1.3 Deploy

```bash
cd license_server
vercel deploy --prod
# Note the deployment URL, e.g. https://your-project.vercel.app
```

### 1.4 Verify

```bash
curl https://your-project.vercel.app/api/license/status
# → {"status":"ok","ts":1234567890}
```

---

## 2. Issue a License Key to a Customer

Run the admin utility **from your machine** (not the customer's):

```bash
python generate_license_key.py \
  --server        https://your-project.vercel.app \
  --admin-secret  <ADMIN_SECRET>                   \
  --customer-id   acme-corp                        \
  --expiry        2027-01-01                        \
  --credits       1000
```

Output:
```
=== License Key (give this to the customer) ===
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

=== Customer Docker env vars ===
  LICENSE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  LICENSE_SERVER_URL=https://your-project.vercel.app
```

---

## 3. Customer Docker Deployment

The customer passes the two env vars at `docker run` time:

```bash
docker run -d \
  -e LICENSE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -e LICENSE_SERVER_URL="https://your-project.vercel.app" \
  -e DATABASE_URL="sqlite:////work_dir/video_search.db" \
  -v /host/work_dir:/work_dir \
  -p 5800:5800 \
  your-image-name
```

Or via an `.env` file:

```dotenv
LICENSE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
LICENSE_SERVER_URL=https://your-project.vercel.app
DATABASE_URL=sqlite:////work_dir/video_search.db
```

```bash
docker run -d --env-file .env -v /host/work_dir:/work_dir -p 5800:5800 your-image-name
```

---

## 4. How It Works at Runtime

| Event | Action |
|---|---|
| App starts | `check_licence_validation()` calls `/api/license/validate`; caches result for 5 min |
| Every hour | Background thread calls `/api/license/heartbeat` with hours consumed |
| Server unreachable | 24-hour offline grace period; operates with last-known valid state |
| Credits exhausted | `/heartbeat` returns `remaining_credits: 0`; subsequent `/validate` returns `valid: false` |
| Key expired (JWT `exp`) | `/validate` returns `valid: false` immediately |
| New calendar month | Server auto-resets usage counter in KV to 0 on next heartbeat |

---

## 5. License Server Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`  | `/api/license/status`    | None         | Health check |
| `POST` | `/api/license/validate`  | `license_key`| Validate key, return credits |
| `POST` | `/api/license/heartbeat` | `license_key`| Report usage, return remaining credits |
| `POST` | `/api/license/generate`  | `admin_secret`| Issue a new license key |

### Validate request / response

```json
// Request
{ "license_key": "<JWT>" }

// Response (valid)
{ "valid": true, "customer_id": "acme-corp", "expiry_date": "2027-01-01T00:00:00",
  "monthly_credits": 1000.0, "remaining_credits": 743.5 }

// Response (invalid)
{ "valid": false, "error": "Token expired" }
```

### Heartbeat request / response

```json
// Request
{ "license_key": "<JWT>", "hours_used": 1.0 }

// Response
{ "valid": true, "customer_id": "acme-corp", "remaining_credits": 742.5, "monthly_credits": 1000.0 }
```

---

## 6. Vercel Free Tier Limits

| Limit | Value | Our usage |
|-------|-------|-----------|
| Serverless function invocations | 100 000 / month | ≤ 2 req/h per customer (validate cache 5 min + 1 heartbeat/h) |
| KV requests | 3 000 / day | 1 write/h per customer heartbeat |
| KV storage | 256 MB | ~200 bytes per customer entry |

For up to ~50 active customers the free tier is comfortably sufficient.
