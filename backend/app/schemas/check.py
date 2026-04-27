from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


# ─────────────────────────────────────────
# Input Schemas
# ─────────────────────────────────────────

class TextCheckRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000,
                      description="News article text or headline to analyze")


class UrlCheckRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL of the news article to scrape and analyze")


# Image check uses multipart form — schema defined inline in route


# ─────────────────────────────────────────
# Sub-scores Breakdown
# ─────────────────────────────────────────

class AnalysisFactors(BaseModel):
    source_credibility: float = Field(..., ge=0, le=100, description="How credible the source is")
    claim_verifiability: float = Field(..., ge=0, le=100, description="How verifiable the claims are")
    sentiment_bias: float = Field(..., ge=0, le=100, description="Emotional manipulation score (higher = more biased)")
    language_patterns: float = Field(..., ge=0, le=100, description="Normal vs clickbait language patterns")
    headline_body_consistency: float = Field(..., ge=0, le=100, description="Match between headline and body")


# ─────────────────────────────────────────
# Result Schema
# ─────────────────────────────────────────

class CheckResult(BaseModel):
    verdict: Literal["REAL", "FAKE", "UNCERTAIN"]
    trust_score: float = Field(..., ge=0, le=100, description="Overall trust score 0-100")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence 0-1")
    factors: AnalysisFactors
    extracted_text: Optional[str] = Field(None, description="Text extracted from URL or image")
    summary: str = Field(..., description="Human-readable explanation of the verdict")
    input_type: Literal["text", "url", "image"]


# ─────────────────────────────────────────
# History Schema
# ─────────────────────────────────────────

class CheckHistoryOut(BaseModel):
    id: int
    input_type: str
    original_input: str
    verdict: str
    trust_score: float
    confidence: float
    factors: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedHistory(BaseModel):
    items: list[CheckHistoryOut]
    total: int
    page: int
    per_page: int
