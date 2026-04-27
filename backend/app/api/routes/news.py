from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from app.services.news_service import get_top_headlines, search_news
from app.schemas.news import NewsResponse

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/trending", response_model=NewsResponse)
async def trending(
    category: str = Query("general", description="general|technology|science|business|health|sports"),
    country:  str = Query("us",      description="Country code: us, gb, pk, in, etc."),
    page_size: int = Query(10, ge=1, le=50),
    _=Depends(get_current_user),
):
    """
    Fetch top headlines from NewsAPI.
    Results are cached for 1 hour per category+country combination.
    """
    return await get_top_headlines(category=category, country=country, page_size=page_size)


@router.get("/search", response_model=NewsResponse)
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    page_size: int = Query(10, ge=1, le=50),
    _=Depends(get_current_user),
):
    """Search for news articles by keyword."""
    return await search_news(query=q, page_size=page_size)
