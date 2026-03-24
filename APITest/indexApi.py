import requests
import json


port_num = 5801
BASE_URL = f"http://127.0.0.1:{port_num}"

index_url = f"{BASE_URL}/index-videos"
index_payload = {
    "data": [
        # {"filepath": "portuguese_news.mp4", "sourceId": "portuguese_news", "fps": 30, "useAudio": True},
         {"filepath": "tearsofsteel.mp4", "sourceId": "tos_6", "fps": 30, "useAudio": True},
        # {"filepath": "meridian.mp4", "sourceId": "mer", "fps": 30, "useAudio": False},
        # {"filepath": "CosmosLaundromat.mp4", "sourceId": "cos3", "fps": 30, "useAudio": True},
        # {"filepath": "Spring.mp4", "sourceId": "spr", "fps": 30, "useAudio": False},
        # {"filepath": "Sprite.mp4", "sourceId": "ite", "fps": 30, "useAudio": True},

     ],
    "isVideo": True,
    "dbName": "ei_vid"
}
index_resp = requests.post(index_url, json=index_payload)
print("Index Videos:", index_resp.json())
