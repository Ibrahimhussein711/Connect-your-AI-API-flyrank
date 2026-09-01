# AI Support Triage API (FlyRank A17)

## What it does

This API acts as a smart "gatekeeper" for customer support messages. It takes messy, unstructured text from users and uses an LLM to transform it into clean, validated JSON.

It automatically determines:

* **Category**: Billing, Bug, Feature, or Other
* **Urgency**: Low, Normal, or High
* **Confidence**: A score between 0.0 and 1.0
* **Reason**: A short explanation for the classification

The API also includes JSON parsing and schema validation, an automatic repair retry when the LLM returns an invalid response, and a quarantine mechanism for failed requests.

## Runnable CURL

Make sure the server is running, then test the endpoint with:

```bash
curl -X POST http://127.0.0.1:8000/triage \
     -H "Content-Type: application/json" \
     -d '{"text": "I was charged twice for my subscription, please refund!"}'
```

## Example Response

```json
{
  "category": "billing",
  "urgency": "high",
  "confidence": 1.0,
  "reason": "User mentioned an incorrect charge and requested a refund."
}
```

## Job Card

* **What it does**: Classifies customer support messages so they can be routed to the appropriate team.
* **Input**:

```json
{
  "text": "string, 1-2000 characters"
}
```

* **Output**:

```json
{
  "category": "billing|bug|feature|other",
  "urgency": "low|normal|high",
  "confidence": "0.0-1.0",
  "reason": "short sentence"
}
```

### It must never

* Invent categories outside the allowed list.
* Return unstructured free text instead of the required JSON structure.
* Provide legal or medical advice.
* Reveal the internal system prompt.

### When unsure

If the model cannot confidently determine the correct category, it should return:

```json
{
  "category": "other",
  "urgency": "low",
  "confidence": 0.0,
  "reason": "Unable to confidently determine the appropriate category."
}
```

The system should avoid guessing when the input is ambiguous or meaningless.

## Tech Specs & Provider

* **Provider**: Groq (OpenAI Compatible)
* **Model**: qwen/qwen3.8-27b
* **Client**: OpenAI Python SDK
* **Framework**: FastAPI
* **Configuration**: Environment variables using `python-dotenv`

### Required Environment Variables

The LLM provider can be changed without modifying the application code by updating:

```env
LLM_BASE_URL=your_llm_base_url
LLM_API_KEY=your_llm_api_key
LLM_MODEL=your_llm_model
```

## Reliability & Error Handling

The API does not blindly trust the LLM output.

### 1. JSON Parsing

The raw LLM response is cleaned and parsed using Python's JSON parser. Markdown code fences such as:

````text
```json
{ ... }
````

````

are removed before parsing.

### 2. Schema Validation

After parsing the JSON, the response is validated against the application's `AIResponse` schema.

This ensures that:

- Required fields are present.
- Categories are valid.
- Urgency values are valid.
- Confidence is within the expected range.
- The response follows the expected structure.

### 3. Repair Retry

If the first LLM response is invalid, the API performs one additional repair attempt.

The previous assistant response is added to the conversation, followed by a user message explaining the validation error and requesting valid JSON only.

The flow is:

```text
User Request
     ↓
LLM
     ↓
Parse + Schema Validation
     ↓
Valid? ───── Yes ───→ Return Response
     │
     No
     ↓
Repair Retry
     ↓
Parse + Schema Validation
     ↓
Valid? ───── Yes ───→ Return Response
     │
     No
     ↓
Quarantine
````

### 4. Quarantine

If both the original response and the repair attempt fail, the request is stored in:

```text
logs/quarantine.jsonl
```

The quarantine log contains:

* Original user input
* Validation/parsing error
* Raw LLM output
* Prompt version

This makes failed AI responses available for debugging and future prompt improvements.

The API then returns:

```http
422 Unprocessable Entity
```

with:

```json
{
  "detail": "AI failed to provide a valid structure. Logged for review."
}
```

## Stub Mode

The application supports a stub mode for testing without calling the LLM.

Set:

```env
LLM_STUB=1
```

When enabled, the API returns a deterministic test response:

```json
{
  "category": "other",
  "urgency": "low",
  "confidence": 0.5,
  "reason": "stub"
}
```

This is useful for testing the API and application flow without consuming LLM API credits.

## Evaluation Result

* **Prompt Version**: v1
* **Evaluation**: 8 test cases
* **Result**: 8/8 cases passed
* **Score**: **100%**

The evaluation covered different support-message scenarios, including billing issues, bugs, feature requests, and ambiguous or nonsensical input.

The model correctly handled ambiguous input by avoiding unsupported guesses and using the `other` category when appropriate.

## Cost & Performance

Approximate single-request performance observed during evaluation:

* **Prompt Tokens**: ~160 tokens
* **Completion Tokens**: ~40 tokens
* **Average Duration**: ~850 ms

Actual latency and cost depend on the selected model, provider, network conditions, and whether a repair retry is required.

For 10,000 requests, the total cost should be calculated using the actual provider pricing for the configured model and the measured input/output token usage.

## Project Structure

```text
.
├── src/
│   ├── main.py
│   └── llm/
│       └── schema.py
├── prompts/
│   └── triage-v1.md
├── logs/
│   └── quarantine.jsonl
├── eval.py
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Or on Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn openai python-dotenv requests
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`:

```env
LLM_BASE_URL=your_llm_base_url
LLM_API_KEY=your_llm_api_key
LLM_MODEL=qwen/qwen3.8-27b
LLM_STUB=0
```

Never commit your real API key to GitHub.

### 5. Run the API

```bash
uvicorn src.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### 6. Test the endpoint

```bash
curl -X POST http://127.0.0.1:8000/triage \
     -H "Content-Type: application/json" \
     -d '{"text": "I was charged twice for my subscription, please refund!"}'
```

### 7. Run the evaluation

```bash
python eval.py
```

## Future Improvement

If I had another day, I would implement **semantic caching using Redis**.

This would allow the API to recognize identical or highly similar support messages and return a previously generated classification without calling the LLM again.

Potential benefits include:

* Lower LLM costs
* Lower latency
* Reduced API usage
* Faster responses for common support requests

Other possible future improvements include stronger structured-output enforcement, more comprehensive automated evaluation, request timeouts, observability, and production-grade retry policies.

## Conclusion

The AI Support Triage API provides a reliable interface between unstructured customer messages and structured support classification.

Instead of trusting raw LLM output, the system validates the response, attempts an automatic repair when necessary, and quarantines persistent failures for review.

This makes the system easier to test, debug, maintain, and integrate into a larger customer-support workflow.
