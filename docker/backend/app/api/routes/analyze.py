"""
Analyze Routes
==============
Three endpoints — one per input type — all returning the same AnalyzeResponse.
Pipeline:  input → extract text → clean → ML model → store history → return result
"""
import time
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.check_history import CheckHistory, InputType, Verdict
from app.schemas.analyze import (
    TextAnalyzeRequest, UrlAnalyzeRequest, AnalyzeResponse, CheckHistoryItem
)
from app.services.text_extractor import extract_from_url, extract_from_image, clean_text
from app.services.ml_service import analyze_text, get_verdict_label, get_verdict_summary

router = APIRouter(prefix="/analyze", tags=["Analysis"])


# ── Shared: Save to DB and build response ────────────────────────
async def _run_and_save(
    db: AsyncSession,
    user: User,
    input_type: InputType,
    original_input: str,
    raw_text: str,
) -> AnalyzeResponse:
    cleaned = clean_text(raw_text)
    if len(cleaned) < 10:
        raise HTTPException(status_code=422, detail="Not enough text to analyze")

    result = await analyze_text(cleaned)

    # Persist to database
    record = CheckHistory(
        user_id        = user.id,
        input_type     = input_type,
        original_input = original_input[:1000],
        extracted_text = cleaned[:5000],
        verdict        = Verdict(result["verdict"]),
        trust_score    = result["trust_score"],
        confidence     = result["confidence"],
        source_score   = result["factors"].source_credibility,
        sentiment_score= result["factors"].sentiment_bias,
        language_score = result["factors"].language_patterns,
        claim_score    = result["factors"].claim_verifiability,
        processing_ms  = result["processing_ms"],
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    return AnalyzeResponse(
        check_id              = record.id,
        verdict               = result["verdict"],
        trust_score           = result["trust_score"],
        confidence            = result["confidence"],
        label                 = get_verdict_label(result["verdict"], result["trust_score"]),
        summary               = get_verdict_summary(result["verdict"], result["trust_score"]),
        input_type            = input_type,
        extracted_text_preview= cleaned[:200],
        factors               = result["factors"],
        processing_ms         = result["processing_ms"],
    )


# ── Endpoint 1: Plain Text ───────────────────────────────────────
@router.post("/text", response_model=AnalyzeResponse)
async def analyze_text_endpoint(
    data: TextAnalyzeRequest,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a news headline or article provided as plain text.
    """
    return await _run_and_save(
        db, current_user,
        InputType.text,
        data.text,
        data.text,
    )


# ── Endpoint 2: URL ──────────────────────────────────────────────
@router.post("/url", response_model=AnalyzeResponse)
async def analyze_url_endpoint(
    data: UrlAnalyzeRequest,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scrape an article from a URL, extract its text, then analyze.
    """
    url_str  = str(data.url)
    raw_text = await extract_from_url(url_str)
    return await _run_and_save(
        db, current_user,
        InputType.url,
        url_str,
        raw_text,
    )


# ── Endpoint 3: Image Upload ─────────────────────────────────────
@router.post("/image", response_model=AnalyzeResponse)
async def analyze_image_endpoint(
    file: UploadFile        = File(..., description="Screenshot or news image (PNG/JPG)"),
    db: AsyncSession        = Depends(get_db),
    current_user: User      = Depends(get_current_user),
):
    """
    Extract text from an uploaded screenshot via OCR, then analyze.
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files are accepted (PNG/JPG/WEBP)")

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    raw_text = await extract_from_image(file)
    return await _run_and_save(
        db, current_user,
        InputType.image,
        file.filename or "uploaded_image",
        raw_text,
    )


# ── History ──────────────────────────────────────────────────────
@router.get("/history", response_model=list[CheckHistoryItem])
async def get_history(
    limit: int         = 20,
    offset: int        = 0,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's analysis history (latest first)."""
    from sqlalchemy import select
    result = await db.execute(
        select(CheckHistory)
        .where(CheckHistory.user_id == current_user.id)
        .order_by(CheckHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = result.scalars().all()
    return [
        CheckHistoryItem(
            id=r.id,
            verdict=r.verdict,
            trust_score=r.trust_score,
            input_type=r.input_type,
            original_input=r.original_input,
            created_at=str(r.created_at),
        )
        for r in records
    ]


@router.get("/history/{check_id}", response_model=AnalyzeResponse)
async def get_single_check(
    check_id: int,
    db: AsyncSession   = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single past check by ID."""
    from sqlalchemy import select
    result = await db.execute(
        select(CheckHistory).where(
            CheckHistory.id == check_id,
            CheckHistory.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Check not found")

    from app.schemas.analyze import FactorScores
    return AnalyzeResponse(
        check_id=record.id,
        verdict=record.verdict.value,
        trust_score=record.trust_score,
        confidence=record.confidence,
        label=get_verdict_label(record.verdict.value, record.trust_score),
        summary=get_verdict_summary(record.verdict.value, record.trust_score),
        input_type=record.input_type,
        extracted_text_preview=record.extracted_text[:200],
        factors=FactorScores(
            source_credibility=record.source_score or 50,
            claim_verifiability=record.claim_score or 50,
            sentiment_bias=record.sentiment_score or 50,
            language_patterns=record.language_score or 50,
        ),
        processing_ms=record.processing_ms or 0,
    )
