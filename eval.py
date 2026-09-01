import requests
import json

# تأكد إن السيرفر شغال قبل ما تشغل السكريبت ده
URL = "http://127.0.0.1:8000/triage"

with open("evals/cases.json", "r") as f:
    cases = json.load(f)

correct = 0
for case in cases:
    response = requests.post(URL, json={"text": case["input"]})
    if response.status_code == 200:
        result = response.json()
        if result["category"] == case["expected_category"]:
            correct += 1
            print(f"✅ Pass: {case['input'][:30]}... -> {result['category']}")
        else:
            print(f"❌ Fail: {case['input'][:30]}... (Expected {case['expected_category']}, got {result['category']})")
    else:
        print(f"⚠️ Error: {response.status_code}")

score = (correct / len(cases)) * 100
print(f"\nFinal Score: {score}% ({correct}/{len(cases)})")