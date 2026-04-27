"""
News API Service
================
Fetches trending news and category-specific articles from newsapi.org.
Responses are cached in Redis for 1 hour to avoid repeated API calls.
"""
import httpx
from typing import List, Optional
from loguru import logger
from app.core.config import settings
from app.core.redis_client import cache_get, cache_set
from app.schemas.news import NewsArticle, NewsResponse


CATEGORY_MAP = {
    "general":       "general",
    "politics":      "general",
    "technology":    "technology",
    "science":       "science",
    "health":        "health",
    "business":      "business",
    "entertainment": "entertainment",
    "sports":        "sports",
}


async def _fetch_news(endpoint: str, params: dict) -> dict:
    params["apiKey"] = settings.NEWS_API_KEY
    url = f"{settings.NEWS_API_BASE_URL}/{endpoint}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _parse_articles(raw_articles: list) -> List[NewsArticle]:
    results = []
    for a in raw_articles:
        if not a.get("title") or a["title"] == "[Removed]":
            continue
        results.append(NewsArticle(
            title=a["title"],
            description=a.get("description"),
            url=a.get("url", ""),
            source=a.get("source", {}).get("name", "Unknown"),
            published_at=a.get("publishedAt", ""),
            url_to_image=a.get("urlToImage"),
        ))
    return results


async def get_top_headlines(
    category: str = "general",
    country: str = "us",
    page_size: int = 10,
    page: int = 1,
) -> NewsResponse:
    cache_key = f"news:headlines:{category}:{country}:{page}"
    cached = await cache_get(cache_key)
    if cached:
        logger.debug(f"Cache HIT: {cache_key}")
        return NewsResponse(**cached)

    try:
        data = await _fetch_news("top-headlines", {
            "category": CATEGORY_MAP.get(category, "general"),
            "country":  country,
            "pageSize": page_size,
            "page":     page,
        })
        articles = _parse_articles(data.get("articles", []))
        response = NewsResponse(total=data.get("totalResults", 0), articles=articles)
        await cache_set(cache_key, response.model_dump(), ttl=3600)
        return response

    except Exception as e:
        logger.error(f"NewsAPI error: {e}")
        return NewsResponse(total=0, articles=[])


async def search_news(query: str, page_size: int = 10) -> NewsResponse:
    cache_key = f"news:search:{query}:{page_size}"
    cached = await cache_get(cache_key)
    if cached:
        return NewsResponse(**cached)

    try:
        data = await _fetch_news("everything", {
            "q":          query,
            "pageSize":   page_size,
            "sortBy":     "publishedAt",
            "language":   "en",
        })
        articles = _parse_articles(data.get("articles", []))
        response = NewsResponse(total=data.get("totalResults", 0), articles=articles)
        await cache_set(cache_key, response.model_dump(), ttl=1800)
        return response

    except Exception as e:
        logger.error(f"NewsAPI search error: {e}")
        return NewsResponse(total=0, articles=[])
