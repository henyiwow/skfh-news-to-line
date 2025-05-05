import requests
import os

def push_to_line(message):
    LINE_TOKEN = os.getenv("LINE_TOKEN")
    GROUP_ID = os.getenv("LINE_GROUP_ID")
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": GROUP_ID,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    response = requests.post("https://api.line.me/v2/bot/message/push", json=payload, headers=headers)
    return response.status_code, response.text
