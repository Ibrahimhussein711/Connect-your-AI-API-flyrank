import os, json, time # ضفنا time هنا
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from openai import OpenAI
from .llm.schema import AIResponse, AIRequest

load_dotenv()
app = FastAPI()

# 1. إعداد الـ Client بـ Timeout (30 ثانية) و Max Retries (مرتين)
client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY"),
    timeout=30.0, # لا ينتظر أكثر من 30 ثانية
    max_retries=2  # يحاول مرتين لو السيرفر وقع
)

# تأكد أن دالة parse_ai_json و log_quarantine موجودة (من Stage 3)
def parse_ai_json(raw_content: str):
    clean_content = raw_content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_content)

@app.post("/triage", response_model=AIResponse)
async def triage_message(request: AIRequest):
    # --- 2. KILL SWITCH ---
    # لو القيمة false، الـ API يرجع 503 فوراً من غير ما يكلم الـ AI
    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        raise HTTPException(status_code=503, detail="AI Service is currently disabled.")

    if os.getenv("LLM_STUB") == "1":
        return {"category": "other", "urgency": "low", "confidence": 0.5, "reason": "stub"}

    start_time = time.time() # بداية حساب الوقت
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=[
                {"role": "system", "content": open("prompts/triage-v1.md").read()},
                {"role": "user", "content": request.text}
            ],
            temperature=0
        )
        
        # --- 3. COST & PERFORMANCE LOGGING ---
        duration_ms = (time.time() - start_time) * 1000
        usage = response.usage # عدد الـ Tokens
        
        # بنطبع لوج منظم (Structured Log)
        print(f"PROMPT_VERSION: v1 | MODEL: {os.getenv('LLM_MODEL')} | "
              f"TOKENS: {usage.total_tokens} (In: {usage.prompt_tokens}, Out: {usage.completion_tokens}) | "
              f"DURATION: {duration_ms:.2f}ms")

        # بنكمل بقية الـ Logic بتاع Stage 3
        raw_content = response.choices[0].message.content
        data = parse_ai_json(raw_content)
        return AIResponse(**data)

    except Exception as e:
        # لو المشكلة كانت Timeout، رجع 504
        if "timeout" in str(e).lower():
            raise HTTPException(status_code=504, detail="AI provider took too long to respond.")
        raise HTTPException(status_code=500, detail=str(e))