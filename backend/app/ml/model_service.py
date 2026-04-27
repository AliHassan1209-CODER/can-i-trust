"""
ML Model Service
----------------
Loads a fine-tuned DistilBERT model for fake news classification.
Falls back to a rule-based heuristic scorer if model is unavailable.

Training: Fine-tune on LIAR + FakeNewsNet datasets (see /app/ml/train.py)
Output  : trust_score (0-100), verdict (REAL/FAKE/UNCERTAIN), confidence, factors
"""

import re
import math
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy globals — loaded once on first call
_tokenizer = None
_model = None
_model_loaded = False


def _load_model():
    """Load HuggingFace model (DistilBERT fine-tuned on fake news dataset)."""
    global _tokenizer, _model, _model_loaded

    if _model_loaded:
        return

    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        model_path = settings.MODEL_PATH if settings.USE_LOCAL_MODEL else settings.MODEL_NAME

        logger.info(f"Loading model from: {model_path}")
        _tokenizer = AutoTokenizer.from_pretrained(model_path)
        _model = AutoModelForSequenceClassification.from_pretrained(model_path)
        _model.eval()
        _model_loaded = True
        logger.info("Model loaded successfully")

    except Exception as e:
        logger.warning(f"Model load failed ({e}). Using heuristic fallback.")
        _model_loaded = True   # Mark as attempted so we don't retry every call


# ─────────────────────────────────────────
# Heuristic Scorer (fallback / enrichment)
# ─────────────────────────────────────────

CLICKBAIT_PATTERNS = [
    r'\b(shocking|unbelievable|you won\'t believe|secret|they don\'t want|conspiracy)\b',
    r'\b(miracle|cure|doctors hate|one weird trick)\b',
    r'[A-Z]{4,}',             # Excessive caps e.g. "BREAKING NEWS YOU MUST READ"
    r'!!+',                   # Multiple exclamation marks
    r'\b(100%|guaranteed|proven)\b',
]

CREDIBLE_SOURCE_DOMAINS = {
    "reuters.com", "bbc.com", "bbc.co.uk", "apnews.com", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "dawn.com", "geo.tv",
    "nature.com", "science.org", "who.int", "un.org",
}

SUSPICIOUS_DOMAINS = {
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "worldnewsdailyreport.com", "empirenews.net",
}


def _heuristic_scores(text: str, source: Optional[str] = None) -> dict:
    """Rule-based scoring — runs fast, no model needed."""
    text_lower = text.lower()
    word_count = len(text.split())

    # 1. Clickbait / sensationalism score
    clickbait_hits = sum(
        len(re.findall(p, text_lower, re.IGNORECASE))
        for p in CLICKBAIT_PATTERNS
    )
    sentiment_bias = min(clickbait_hits * 15, 90)

    # 2. Source credibility
    source_score = 50.0   # neutral default
    if source:
        source_lower = source.lower()
        if any(d in source_lower for d in CREDIBLE_SOURCE_DOMAINS):
            source_score = 85.0
        elif any(d in source_lower for d in SUSPICIOUS_DOMAINS):
            source_score = 10.0

    # 3. Language patterns (checks for normal article structure)
    has_quotes = '"' in text or "'" in text
    has_numbers = bool(re.search(r'\d+', text))
    has_attribution = bool(re.search(
        r'\b(said|according to|reported|announced|confirmed)\b', text_lower
    ))
    language_score = (
        (30 if has_quotes else 0) +
        (20 if has_numbers else 0) +
        (30 if has_attribution else 0) +
        (20 if word_count > 100 else 0)
    )

    # 4. Claim verifiability (rough proxy: presence of specifics)
    has_dates = bool(re.search(r'\b(january|february|march|2024|2025|2026)\b', text_lower))
    has_names = bool(re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text))
    verifiability = (
        (40 if has_dates else 0) +
        (35 if has_names else 0) +
        (25 if has_attribution else 0)
    )

    # 5. Headline / body consistency (simplified)
    headline_consistency = 70.0   # placeholder without separate headline

    return {
        "source_credibility": round(source_score, 1),
        "claim_verifiability": round(verifiability, 1),
        "sentiment_bias": round(sentiment_bias, 1),
        "language_patterns": round(language_score, 1),
        "headline_body_consistency": round(headline_consistency, 1),
    }


# ─────────────────────────────────────────
# BERT Inference
# ─────────────────────────────────────────

def _bert_predict(text: str) -> Optional[dict]:
    """Run DistilBERT inference. Returns raw probs or None if model unavailable."""
    if not _model or not _tokenizer:
        return None

    try:
        import torch

        inputs = _tokenizer(
            text[:512],          # BERT max token limit
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512,
        )

        with torch.no_grad():
            outputs = _model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]

        # Model classes: 0 = FAKE, 1 = REAL (adjust per your training)
        fake_prob = float(probs[0])
        real_prob = float(probs[1])

        return {"fake_prob": fake_prob, "real_prob": real_prob}

    except Exception as e:
        logger.error(f"BERT inference error: {e}")
        return None


# ─────────────────────────────────────────
# Main Analyze Function
# ─────────────────────────────────────────

class MLModelService:

    @staticmethod
    def analyze(text: str, source: Optional[str] = None) -> dict:
        """
        Analyze text and return:
          { verdict, trust_score, confidence, factors, summary }
        """
        # Ensure model is loaded (lazy)
        _load_model()

        # Run heuristic scores (always)
        factors = _heuristic_scores(text, source)

        # Try BERT prediction
        bert_result = _bert_predict(text)

        if bert_result:
            # Blend BERT + heuristics for final trust score
            bert_trust = bert_result["real_prob"] * 100
            heuristic_trust = (
                factors["source_credibility"] * 0.3 +
                factors["claim_verifiability"] * 0.2 +
                (100 - factors["sentiment_bias"]) * 0.25 +
                factors["language_patterns"] * 0.25
            )
            trust_score = bert_trust * 0.6 + heuristic_trust * 0.4
            confidence = max(bert_result["real_prob"], bert_result["fake_prob"])

        else:
            # Pure heuristic trust score
            trust_score = (
                factors["source_credibility"] * 0.30 +
                factors["claim_verifiability"] * 0.25 +
                (100 - factors["sentiment_bias"]) * 0.25 +
                factors["language_patterns"] * 0.20
            )
            confidence = 0.65   # Lower confidence without BERT

        trust_score = max(0.0, min(100.0, trust_score))

        # Determine verdict
        if trust_score >= 65:
            verdict = "REAL"
            summary = (
                f"This content appears credible with a trust score of {trust_score:.0f}/100. "
                f"Source signals and language patterns suggest legitimate reporting."
            )
        elif trust_score <= 35:
            verdict = "FAKE"
            summary = (
                f"This content shows strong indicators of misinformation (score: {trust_score:.0f}/100). "
                f"Sensationalist language, unverifiable claims, or suspicious source detected."
            )
        else:
            verdict = "UNCERTAIN"
            summary = (
                f"Mixed signals detected (score: {trust_score:.0f}/100). "
                f"Cross-check this news with trusted sources before sharing."
            )

        return {
            "verdict": verdict,
            "trust_score": round(trust_score, 1),
            "confidence": round(confidence, 2),
            "factors": factors,
            "summary": summary,
        }
