"""
Input Processor Service
-----------------------
Handles all three input types:
  - text   : returned as-is (cleaned)
  - url    : scrapes article text using newspaper3k
  - image  : extracts text via Tesseract OCR
"""

import re
import pytesseract
from PIL import Image
import io
from typing import Optional

import httpx
from newspaper import Article
from app.core.config import settings

# Set Tesseract path (important on Windows)
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH


class InputProcessorService:

    # ─────────────────────────────────────────
    # Text Cleaning
    # ─────────────────────────────────────────

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove extra whitespace, special chars, normalize text."""
        text = re.sub(r'\s+', ' ', text)              # collapse whitespace
        text = re.sub(r'[^\w\s.,!?\'\"()\-:]', ' ', text)  # keep readable punctuation
        text = text.strip()
        return text

    # ─────────────────────────────────────────
    # URL → Text
    # ─────────────────────────────────────────

    @staticmethod
    async def extract_from_url(url: str) -> dict:
        """
        Fetch a news article from a URL and extract its text.
        Returns: { text, title, authors, publish_date, source }
        """
        try:
            article = Article(str(url))
            article.download()
            article.parse()
            article.nlp()    # Extracts keywords and summary

            extracted_text = article.text
            if not extracted_text:
                raise ValueError("Could not extract text from URL")

            return {
                "text": InputProcessorService.clean_text(extracted_text),
                "title": article.title or "",
                "authors": article.authors or [],
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "source": article.source_url or str(url),
                "summary": article.summary or "",
                "keywords": article.keywords or [],
            }

        except Exception as e:
            # Fallback: simple httpx + BeautifulSoup scrape
            return await InputProcessorService._fallback_scrape(str(url))

    @staticmethod
    async def _fallback_scrape(url: str) -> dict:
        """Simple HTML scrape if newspaper3k fails."""
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; CanITrust/1.0)"
            })
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Get main content
        body_text = soup.get_text(separator=" ", strip=True)
        title = soup.title.string if soup.title else ""

        return {
            "text": InputProcessorService.clean_text(body_text[:5000]),
            "title": title,
            "authors": [],
            "publish_date": None,
            "source": url,
            "summary": "",
            "keywords": [],
        }

    # ─────────────────────────────────────────
    # Image → Text (OCR)
    # ─────────────────────────────────────────

    @staticmethod
    async def extract_from_image(image_bytes: bytes) -> dict:
        """
        Run Tesseract OCR on an uploaded image.
        Returns: { text, word_count, confidence }
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))

            # Preprocess for better OCR accuracy
            image = image.convert("L")   # Grayscale

            # OCR with confidence data
            ocr_data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config="--psm 1 --oem 3"  # Auto page segmentation
            )

            # Filter high-confidence words
            words = [
                word for word, conf in zip(ocr_data["text"], ocr_data["conf"])
                if word.strip() and int(conf) > 30
            ]
            extracted_text = " ".join(words)

            if not extracted_text.strip():
                raise ValueError("No text found in image")

            avg_confidence = sum(
                int(c) for c in ocr_data["conf"] if int(c) > 0
            ) / max(len([c for c in ocr_data["conf"] if int(c) > 0]), 1)

            return {
                "text": InputProcessorService.clean_text(extracted_text),
                "word_count": len(words),
                "confidence": round(avg_confidence / 100, 2),
            }

        except Exception as e:
            raise ValueError(f"OCR failed: {str(e)}")

    # ─────────────────────────────────────────
    # Unified Processor Entry Point
    # ─────────────────────────────────────────

    @staticmethod
    async def process(
        input_type: str,
        text: Optional[str] = None,
        url: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
    ) -> dict:
        """
        Main entry point. Routes input to the right extractor.
        Returns: { text, metadata }
        """
        if input_type == "text":
            if not text:
                raise ValueError("Text input is required")
            return {
                "text": InputProcessorService.clean_text(text),
                "metadata": {}
            }

        elif input_type == "url":
            if not url:
                raise ValueError("URL is required")
            result = await InputProcessorService.extract_from_url(url)
            text_content = result.pop("text")
            return {"text": text_content, "metadata": result}

        elif input_type == "image":
            if not image_bytes:
                raise ValueError("Image data is required")
            result = await InputProcessorService.extract_from_image(image_bytes)
            text_content = result.pop("text")
            return {"text": text_content, "metadata": result}

        else:
            raise ValueError(f"Unknown input type: {input_type}")
