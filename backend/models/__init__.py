"""Database models"""
from .crawl import (
    Crawl,
    CrawlStatus,
    URL,
    Link,
    Issue,
    RedirectChain,
    Image,
    Hreflang,
    StructuredData,
)

__all__ = [
    "Crawl",
    "CrawlStatus",
    "URL",
    "Link",
    "Issue",
    "RedirectChain",
    "Image",
    "Hreflang",
    "StructuredData",
]
