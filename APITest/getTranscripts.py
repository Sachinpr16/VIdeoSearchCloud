import requests
import json


port_num = 5801
BASE_URL = f"http://127.0.0.1:{port_num}"


get_transcripts_url = f"{BASE_URL}/get-transcripts"
get_transcripts_payload = {
    "sourceId": "cos3",
    # "dbName": "ei_vid"
}
get_transcripts_resp = requests.post(get_transcripts_url, json=get_transcripts_payload)
print("Get Transcripts:", get_transcripts_resp.json())

#save it to data.json
with open("data.json", "w") as f:
    json.dump(get_transcripts_resp.json(), f, indent=4)