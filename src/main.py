import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from openai import OpenAI  # المكتبة اللي جربناها في Stage 0
from .llm.schema import AIResponse, AIRequest

load_dotenv()

app = FastAPI()

# تجهيز الـ Client (زي ما عملت في hello.py)
client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY")
)

# وظيفة لقراءة ملف الـ Prompt
def get_prompt():
    with open("prompts/triage-v1.md", "r") as f:
        return f.read()

@app.post("/triage", response_model=AIResponse)
async def triage_message(request: AIRequest):
    # 1. Stub Mode
    if os.getenv("LLM_STUB") == "1":
        return {
            "category": "other", "urgency": "low", "confidence": 0.5, "reason": "Stub mode active"
        }

    # 2. Real AI Call (Stage 2)
    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=[
                {"role": "system", "content": get_prompt()},
                {"role": "user", "content": request.text}
            ],
            temperature=0, # مهم جداً عشان الإجابة تكون دقيقة مش إبداعية
        )
        
        # حالياً هنطبع النتيجة ونرجعها كـ JSON
        raw_content = response.choices[0].message.content
        print(f"AI Raw Answer: {raw_content}")
        
        # في Stage 3 هنتعلم إزاي ننظف الـ raw_content ده، حالياً هنرجعه كما هو (لو كان JSON سليم)
        import json
        return json.loads(raw_content)

    except Exception as e:
        print(f"Error calling AI: {e}")
        raise HTTPException(status_code=500, detail="AI Service Error")