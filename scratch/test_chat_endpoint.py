import requests

url = "http://127.0.0.1:8000/chat"
headers = {
    "Referer": "http://127.0.0.1:8000/ui"
}

payloads = [
    {"message": "Vos services", "user_id": "ui-user", "stream": False},
    {"message": "Nous contacter", "user_id": "ui-user", "stream": False},
    {"message": "Horaires", "user_id": "ui-user", "stream": False},
    {"message": "À propos de NAPS", "user_id": "ui-user", "stream": False},
]

for p in payloads:
    try:
        response = requests.post(url, json=p, headers=headers)
        print(f"Payload: {p['message']}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print("-" * 50)
    except Exception as e:
        print(f"Error for {p['message']}: {e}")
