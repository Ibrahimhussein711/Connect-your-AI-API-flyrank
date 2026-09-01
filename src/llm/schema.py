from pydantic import BaseModel, Field
from enum import Enum

class Category(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"

class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

# موديل المدخلات (حسب الـ Job Card)
class AIRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

# موديل المخرجات
class AIResponse(BaseModel):
    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0, le=1)
    reason: str