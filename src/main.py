import os
from fastapi import FastAPI, HTTPException, Body
from dotenv import load_dotenv
from .llm.schema import AIResponse, AIRequest

# 1. تحميل الملف (تأكد إن مكتبة python-dotenv متسطبة)
load_dotenv() 

app = FastAPI()

@app.post("/triage", response_model=AIResponse)
async def triage_message(request: AIRequest):
    # 2. نطبع القيمة عشان نعرف السيرفر شايف إيه
    stub_value = os.getenv("LLM_STUB")
    print(f"--- DEBUG: LLM_STUB is '{stub_value}' ---")

    # 3. التأكد من النوع (string) والقيمة
    if stub_value == "1":
        return {
            "category": "other",
            "urgency": "low",
            "confidence": 0.5,
            "reason": "Stub mode is active. No real AI call was made."
        }

    # 4. لو مش 1، لازم نطلع Error بدل ما نسيب الـ function ترجع None
    raise HTTPException(
        status_code=503, 
        detail=f"Stub mode is off (Value: {stub_value}). AI logic not implemented yet."
    )