import requests

url = "https://api.devinci.local/api/v1/npc/generate"
headers = {"Authorization": "Bearer dv_local_7a962daf35de4c3898a4ec62146c1c36"}
payload = {
    "template_id": "cyberpunk_merchant_01",
    "context": "Neon District market encounter",
    "personality_weight": 0.85
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())