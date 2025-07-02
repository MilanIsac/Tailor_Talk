import json

with open("service_account.json", "r") as f:
    data = json.load(f)

print(json.dumps(data))  # ✅ this will print a compact, correct JSON string
