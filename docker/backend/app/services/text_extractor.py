"""
Text Extractor Service
======================
Converts any input type (text / URL / image) into clean plain text
before passing it to the ML classifier.
"""
import re
import io
import httpx
from typing import Tuple
from loguru import logger
from fastapi import UploadFile, HTTPException


# ── URL Extractor ────────────────────────────────────────────────
async def extract_from_url(url: str) -> str:
    """
    Scrape article text from a URL using newspaper3k.
    Falls back to raw HTML text if newspaper3k fails.
    """
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
        if text and len(text.strip()) > 50:
            title = article.title or ""
            return f"{title}\n\n{text}".strip()
    except Exception as e:
        logger.warning(f"newspaper3k failed for {url}: {e}")

    # Fallback: raw httpx fetch + basic HTML strip
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            raw = resp.text

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "lxml")
        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text[:5000]  # cap at 5000 chars

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract text from URL: {e}")


# ── Image OCR Extractor ──────────────────────────────────────────
async def extract_from_image(file: UploadFile) -> str:
    """
    Use pytesseract to extract text from an uploaded image file.
    """
    try:
        import pytesseract
        from PIL import Image

        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Grayscale improves OCR accuracy
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang="eng+urd")
        text = text.strip()

        if not text or len(text) < 10:
            raise HTTPException(
                status_code=422,
                detail="Could not extract readable text from image. Try a clearer screenshot.",
            )
        return text

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="OCR service unavailable. Install pytesseract and tesseract-ocr.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Image processing failed: {e}")


# ── Text Cleaner ─────────────────────────────────────────────────
def clean_text(raw: str) -> str:
    """Normalize whitespace, remove junk characters."""
    text = re.sub(r"http\S+", "", raw)           # remove bare URLs
    text = re.sub(r"[^\w\s.,!?\"''-]", " ", text)  # strip weird chars
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
