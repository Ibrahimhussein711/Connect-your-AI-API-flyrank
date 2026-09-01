import os, json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from openai import OpenAI
from .llm.schema import AIResponse, AIRequest

load_dotenv()
app = FastAPI()
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))

def get_prompt():
    with open("prompts/triage-v1.md", "r") as f:
        return f.read()

# 1. وظيفة لتنظيف رد الـ AI (بنشيل الـ Markdown Markdown fences)
def parse_ai_json(raw_content: str):
    try:
        # بنشيل أي كلام قبل أو بعد الـ JSON (زي ```json ... ```)
        clean_content = raw_content.strip()
        if "```json" in clean_content:
            clean_content = clean_content.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_content:
            clean_content = clean_content.split("```")[1].split("```")[0].strip()
        
        return json.loads(clean_content)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {str(e)}")

# 2. وظيفة تسجيل الأخطاء (Quarantine)
def log_quarantine(input_text, error, raw_output):
    log_entry = {
        "input": input_text,
        "error": str(error),
        "raw_output": raw_output,
        "prompt_version": "v1"
    }
    with open("logs/quarantine.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

@app.post("/triage", response_model=AIResponse)
async def triage_message(request: AIRequest):
    if os.getenv("LLM_STUB") == "1":
        return {"category": "other", "urgency": "low", "confidence": 0.5, "reason": "stub"}

    system_prompt = get_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.text}
    ]

    raw_content = ""
    try:
        # المحاولة الأولى
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=messages,
            temperature=0
        )
        raw_content = response.choices[0].message.content
        
        try:
            # محاولة التنظيف والتحقق من الـ Schema
            data = parse_ai_json(raw_content)
            return AIResponse(**data) 
            
        except Exception as validation_error:
            # --- REPAIR RETRY (المحاولة الثانية) ---
            print(f"Validation failed: {validation_error}. Attempting repair...")
            
            repair_messages = messages + [
                {"role": "assistant", "content": raw_content},
                {"role": "user", "content": f"Your response was invalid: {validation_error}. Return ONLY valid JSON."}
            ]
            
            repair_res = client.chat.completions.create(
                model=os.getenv("LLM_MODEL"),
                messages=repair_messages,
                temperature=0
            )
            raw_content = repair_res.choices[0].message.content
            data = parse_ai_json(raw_content)
            return AIResponse(**data)

    except Exception as final_error:
        # لو فشل في المرتين بنرميه في الـ Quarantine
        log_quarantine(request.text, final_error, raw_content)
        raise HTTPException(
            status_code=422, 
            detail="AI failed to provide a valid structure. Logged for review."
        )