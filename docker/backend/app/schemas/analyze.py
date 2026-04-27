from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.models.check_history import Verdict, InputType


# ── Request Schemas ──────────────────────────────────────────────
class TextAnalyzeRequest(BaseModel):
    text: str

    @property
    def is_valid(self):
        return len(self.text.strip()) > 10


class UrlAnalyzeRequest(BaseModel):
    url: HttpUrl


# Image is handled as multipart form upload — no schema needed


# ── Response Schemas ─────────────────────────────────────────────
class FactorScores(BaseModel):
    source_credibility: float    # 0–100
    claim_verifiability: float   # 0–100
    sentiment_bias: float        # 0–100 (higher = more biased)
    language_patterns: float     # 0–100 (higher = more normal)


class AnalyzeResponse(BaseModel):
    check_id: int
    verdict: Verdict
    trust_score: float           # 0–100
    confidence: float            # 0–1
    label: str                   # "Likely Real" / "FAKE NEWS" / "Uncertain"
    summary: str
    input_type: InputType
    extracted_text_preview: str  # first 200 chars
    factors: FactorScores
    processing_ms: int


class CheckHistoryItem(BaseModel):
    id: int
    verdict: Verdict
    trust_score: float
    input_type: InputType
    original_input: str
    created_at: str

    model_config = {"from_attributes": True}


class NewsArticle(BaseModel):
    title: str
    description: Optional[str]
    url: str
    source: str
    published_at: str
    url_to_image: Optional[str]
