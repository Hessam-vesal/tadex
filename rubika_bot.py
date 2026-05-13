# import requests
# import time

# TOKEN = "BDGJJF0RVIZAXQCHSEEJWKRJMRURUACGHWEUXSCDSKRAEJBMOJQXYZTSQQXQIZZG"
# BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}"

# while True:
#     response = requests.post(f"{BASE_URL}/getUpdates")
#     print(response.text)
#     time.sleep(2)


import requests

TOKEN = "BDGJJF0RVIZAXQCHSEEJWKRJMRURUACGHWEUXSCDSKRAEJBMOJQXYZTSQQXQIZZG"
CHAT_ID = "c0DbBcN0c351a1ed7c5da284065d7ef5"

url = f"https://botapi.rubika.ir/v3/{TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": "✅ ربات با موفقیت به گروه وصل شد"
}

response = requests.post(url, json=payload)

print(response.text)
