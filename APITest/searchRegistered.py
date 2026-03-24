import requests
import json

port_num = 5801
BASE_URL = f"http://127.0.0.1:{port_num}"

# REST endpoint
search_url = f"{BASE_URL}/search-registered"

startIndex, limit, sourceIds, imageSimThreshold = 1, 10, ["mer"], 0.3

search_payload = {
    "character": "jimmy",
    "action": "standing near the beach",
    "startIndex": startIndex,
    "limit": limit,
    "dbName": "*",
    "imageSimThreshold": imageSimThreshold,
    "sourceIds": sourceIds,
}

# ---- REST CALL ----
response = requests.post(
    search_url,
    json=search_payload,
    headers={"Content-Type": "application/json"}
)

# Print result
if response.ok:
    print({"searchVideos": response.json()})
else:
    print("Error:", response.status_code, response.text)