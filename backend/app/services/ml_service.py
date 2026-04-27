"""
ML Classifier Service
=====================
Loads the trained BERT/DistilBERT model and returns a structured
verdict for any given text input.

Model Training Note:
  - Dataset : LIAR dataset + FakeNewsNet + ISOT
  - Base     : distilbert-base-uncased (fine-tuned)
  - Output   : Binary (real/fake) + confidence score
  - Training script: see /scripts/train_model.py
"""
import time
from typing import Optional
from loguru import logger
from app.core.config import settings
from app.schemas.analyze import FactorScores


# ── Singleton Model Container ────────────────────────────────────
class ModelContainer:
    tokenizer = None
    model = None
    is_loaded: bool = False

    @classmethod
    def load(cls):
        if cls.is_loaded:
            return
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            path = settings.MODEL_PATH if settings.USE_LOCAL_MODEL else settings.HF_MODEL_NAME
            logger.info(f"Loading model from: {path}")

            cls.tokenizer = AutoTokenizer.from_pretrained(path)
            cls.model = AutoModelForSequenceClassification.from_pretrained(path)
            cls.model.eval()
            cls.is_loaded = True
            logger.success("ML model loaded successfully")

        except Exception as e:
            logger.error(f"Model load failed: {e} — falling back to rule-based classifier")
            cls.is_loaded = False


ml = ModelContainer()


# ── Main Analysis Function ───────────────────────────────────────
async def analyze_text(text: str) -> dict:
    """
    Accepts cleaned text, returns verdict dict.
    Falls back to a lightweight rule-based scorer if model is unavailable.
    """
    start = time.time()

    if ml.is_loaded:
        result = _model_predict(text)
    else:
        result = _rule_based_fallback(text)

    result["processing_ms"] = int((time.time() - start) * 1000)
    return result


# ── Neural Model Prediction ──────────────────────────────────────
def _model_predict(text: str) -> dict:
    import torch

    # Truncate to model max length
    inputs = ml.tokenizer(
        text,
        return_tensors="pt",
        max_length=512,
        truncation=True,
        padding=True,
    )

    with torch.no_grad():
        outputs = ml.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1).squeeze()

    # Label 0 = fake, Label 1 = real (adjust if your model differs)
    fake_prob  = float(probs[0])
    real_prob  = float(probs[1])
    confidence = max(fake_prob, real_prob)

    if real_prob >= 0.65:
        verdict    = "real"
        trust_score = round(real_prob * 100, 1)
    elif fake_prob >= 0.65:
        verdict    = "fake"
        trust_score = round(real_prob * 100, 1)
    else:
        verdict    = "uncertain"
        trust_score = round(real_prob * 100, 1)

    factors = _compute_factors(text, real_prob, fake_prob)

    return {
        "verdict": verdict,
        "trust_score": trust_score,
        "confidence": round(confidence, 3),
        "factors": factors,
    }


# ── Rule-Based Fallback ──────────────────────────────────────────
# Used when ML model is not yet trained or unavailable.
# Based on known fake-news linguistic patterns.
SENSATIONAL_WORDS = {
    "shocking", "unbelievable", "you won't believe", "breaking", "exposed",
    "secret", "they don't want you to know", "miracle", "hoax", "conspiracy",
    "banned", "censored", "urgent", "exclusive", "bombshell", "scandal",
    "fake", "lie", "fraud", "satire", "not real", "debunked",
}

CREDIBLE_SOURCES = {
    "reuters.com", "apnews.com", "bbc.com", "theguardian.com", "nytimes.com",
    "dawn.com", "geo.tv", "thenews.com.pk", "nature.com", "who.int",
    "aljazeera.com", "bloomberg.com", "ft.com",
}


def _rule_based_fallback(text: str) -> dict:
    """Simple heuristic scorer — replace with trained model ASAP."""
    import re
    lower = text.lower()

    # Sensational language check
    sensational_hits = sum(1 for w in SENSATIONAL_WORDS if w in lower)
    sensational_score = min(sensational_hits / 3, 1.0)

    # Excessive capitalization
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

    # Excessive punctuation
    punct_count = len(re.findall(r"[!?]{2,}", text))

    # Compute fake probability
    fake_prob = (
        sensational_score * 0.5
        + min(caps_ratio * 5, 1.0) * 0.25
        + min(punct_count / 3, 1.0) * 0.25
    )
    real_prob = 1.0 - fake_prob

    if real_prob >= 0.65:
        verdict     = "real"
        trust_score = round(real_prob * 100, 1)
    elif fake_prob >= 0.65:
        verdict     = "fake"
        trust_score = round(real_prob * 100, 1)
    else:
        verdict     = "uncertain"
        trust_score = round(real_prob * 100, 1)

    factors = _compute_factors(text, real_prob, fake_prob)

    return {
        "verdict": verdict,
        "trust_score": trust_score,
        "confidence": round(max(real_prob, fake_prob), 3),
        "factors": factors,
    }


# ── Factor Score Computation ─────────────────────────────────────
def _compute_factors(text: str, real_prob: float, fake_prob: float) -> FactorScores:
    """
    Compute the 4 sub-scores shown in the UI.
    Rough heuristics — replace with trained sub-classifiers later.
    """
    import re, math
    lower = text.lower()

    # Source credibility (proxy: does text mention credible sources?)
    cred_hits = sum(1 for s in CREDIBLE_SOURCES if s in lower)
    source_score = min(50 + cred_hits * 15, 100.0)

    # Claim verifiability (proxy: does text have numbers, dates, names?)
    has_numbers = bool(re.search(r"\d{4}|\d+%|\$\d+", text))
    has_names   = bool(re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", text))
    claim_score = 50.0 + (20 if has_numbers else 0) + (15 if has_names else 0)
    claim_score = min(claim_score, 100.0)

    # Sentiment bias (higher = more biased/emotional)
    sensational_hits = sum(1 for w in SENSATIONAL_WORDS if w in lower)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    sentiment_score = min((sensational_hits * 15 + caps_ratio * 200), 100.0)

    # Language patterns (normal writing = high score)
    avg_word_len = (
        sum(len(w) for w in text.split()) / max(len(text.split()), 1)
    )
    lang_score = min(max((avg_word_len - 2) * 15, 0), 100.0)

    return FactorScores(
        source_credibility=round(source_score, 1),
        claim_verifiability=round(claim_score, 1),
        sentiment_bias=round(sentiment_score, 1),
        language_patterns=round(lang_score, 1),
    )


# ── Verdict Label ────────────────────────────────────────────────
def get_verdict_label(verdict: str, trust_score: float) -> str:
    labels = {
        "real":      "Likely Real" if trust_score >= 75 else "Possibly Real",
        "fake":      "FAKE NEWS"   if trust_score <= 25 else "Likely Fake",
        "uncertain": "Unverified",
    }
    return labels.get(verdict, "Unknown")


def get_verdict_summary(verdict: str, trust_score: float) -> str:
    if verdict == "real":
        return (
            "This content shows characteristics of credible reporting — "
            "verifiable claims, neutral language, and traceable sources."
        )
    elif verdict == "fake":
        return (
            "Multiple red flags detected — sensational language, unverifiable claims, "
            "and patterns consistent with misinformation."
        )
    else:
        return (
            "Mixed signals found. The content could not be clearly verified. "
            "Cross-check with trusted sources before sharing."
        )
