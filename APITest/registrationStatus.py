import requests
import json

port_num = 5801
BASE_URL = f"http://127.0.0.1:{port_num}"

status_url = f"{BASE_URL}/registration-status"
status_resp = requests.get(status_url)
print("Registration Status:", status_resp.json())
