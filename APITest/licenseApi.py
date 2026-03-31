import requests
import json


port_num = 5801
BASE_URL = f"http://127.0.0.1:{port_num}"

# 1. Licence Requirement
licence_url = f"{BASE_URL}/licence-requirement"
licence_resp = requests.post(licence_url)
print("Licence Requirement:", licence_resp.json())


"""
Cloud-mode response examples:

Valid license (HTTP 200):
{
    "licensestatus": {
        "status": "License valid",
        "Remaining Hourly Credits": 743.5
    }
}

No LICENSE_KEY set (HTTP 402):
{
    "licensestatus": {
        "success": false,
        "status": "No LICENSE_KEY found. Please set the LICENSE_KEY and LICENSE_SERVER_URL environment variables in your Docker container and restart the service. Contact support if you need a new key."
    }
}

LICENSE_KEY set but invalid/expired (HTTP 403):
{
    "licensestatus": {
        "success": false,
        "status": "A LICENSE_KEY is set but validation failed. Please contact support to renew or replace your key."
    }
}
"""
