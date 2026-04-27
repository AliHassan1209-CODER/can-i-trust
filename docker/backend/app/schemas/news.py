from pydantic import BaseModel
from typing import Optional, List


class NewsArticle(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    source: str
    published_at: str
    url_to_image: Optional[str] = None


class NewsResponse(BaseModel):
    total: int
    articles: List[NewsArticle]


class TrendingTopic(BaseModel):
    rank: int
    topic: str
    mentions: str
    category: str
