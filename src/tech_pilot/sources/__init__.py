"""Source adapters for approved Phase 3 news feeds."""

from tech_pilot.sources.hugging_face_blog import (
    SOURCE_ENDPOINT,
    SOURCE_ID,
    normalize_hugging_face_blog_feed,
)
from tech_pilot.sources.models import RssNormalizationResult, SkippedRssEntry

__all__ = [
    "SOURCE_ENDPOINT",
    "SOURCE_ID",
    "RssNormalizationResult",
    "SkippedRssEntry",
    "normalize_hugging_face_blog_feed",
]
