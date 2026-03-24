#!/usr/bin/env python3
"""
generate_license_key.py  –  Admin utility
==========================================
Generates a signed JWT license key for a customer by calling the
license server's /api/license/generate endpoint.

Usage:
    python generate_license_key.py \
        --server  https://your-project.vercel.app \
        --admin-secret  <ADMIN_SECRET> \
        --customer-id   acme-corp \
        --expiry        2027-01-01 \
        --credits       1000

The printed license key should be given to the customer so they can set:
    LICENSE_KEY=<token>
    LICENSE_SERVER_URL=https://your-project.vercel.app
"""

import argparse
import json
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser(description="Generate a license key for a customer.")
    parser.add_argument("--server", required=True, help="License server base URL")
    parser.add_argument("--admin-secret", required=True, dest="admin_secret", help="ADMIN_SECRET value")
    parser.add_argument("--customer-id", required=True, dest="customer_id", help="Unique customer identifier")
    parser.add_argument("--expiry", required=True, help="Expiry date YYYY-MM-DD")
    parser.add_argument("--credits", type=float, default=1000, help="Monthly hourly credits (default: 1000)")
    args = parser.parse_args()

    url = args.server.rstrip("/") + "/api/license/generate"
    payload = json.dumps({
        "admin_secret": args.admin_secret,
        "customer_id": args.customer_id,
        "expiry_date": args.expiry,
        "monthly_credits": args.credits,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read())

    if "license_key" in data:
        print("\n=== License Key (give this to the customer) ===")
        print(data["license_key"])
        print("\n=== Details ===")
        print(f"  Customer ID    : {data.get('customer_id')}")
        print(f"  Expiry         : {data.get('expiry_date')}")
        print(f"  Monthly Credits: {data.get('monthly_credits')}")
        print("\n=== Customer Docker env vars ===")
        print(f"  LICENSE_KEY={data['license_key']}")
        print(f"  LICENSE_SERVER_URL={args.server.rstrip('/')}")
    else:
        print("Failed to generate key:")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
