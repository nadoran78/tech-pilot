"""Collection flows for approved Phase 3 news sources."""

from tech_pilot.collection.google_ai_blog import GoogleAiBlogFetcher, collect_google_ai_blog
from tech_pilot.collection.hugging_face_blog import (
    HuggingFaceBlogFetcher,
    collect_hugging_face_blog,
)
from tech_pilot.collection.models import CollectionStatus, CollectionSummary

__all__ = [
    "GoogleAiBlogFetcher",
    "collect_google_ai_blog",
    "CollectionStatus",
    "CollectionSummary",
    "HuggingFaceBlogFetcher",
    "collect_hugging_face_blog",
]
