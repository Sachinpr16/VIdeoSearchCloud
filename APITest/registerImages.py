import os
import cv2
import requests
import json

port_num = 5801
url = f"http://127.0.0.1:{port_num}/register-images"   # REST endpoint

register_images_payload = {"data": []}

for name in os.listdir("work_dir/registered_images")[:]:
    paths = []

    for img in os.listdir(f"work_dir/registered_images/{name}"):
        image = cv2.imread(f"work_dir/registered_images/{name}/{img}")

        width, height = image.shape[1], image.shape[0]

        x1 = int(0.1 * width)
        y1 = int(0.1 * height)
        x2 = int(0.9 * width)
        y2 = int(0.9 * height)

        roi = [x1, y1, x2, y2]

        paths.append({
            "filepath": f"registered_images/{name}/{img}",
            "roi": roi
        })

    register_images_payload["data"].append({
        "paths": paths,
        "name": name
    })

response = requests.post(url, json=register_images_payload)

print(response.json())
