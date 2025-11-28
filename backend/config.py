"""Configuration system for SEO Spider"""
from pydantic import BaseModel
from typing import Optional


class CrawlConfig(BaseModel):
    """Per-crawl configuration"""

    # Crawl limits
    max_urls: int = 10000
    max_depth: int = 10
    max_folder_depth: Optional[int] = None

    # Speed controls
    max_concurrent_requests: int = 5
    request_delay_ms: int = 100  # Delay between requests to same host
    request_timeout_seconds: int = 20

    # Rendering
    render_javascript: bool = False
    js_wait_ms: int = 5000  # Wait after DOMContentLoaded
    viewport_width: int = 1024
    viewport_height: int = 768

    # User agent
    user_agent: str = "SEOSpider/1.0 (+https://example.com/bot)"
    user_agent_for_robots: str = "SEOSpider"

    # Scope
    stay_in_subdomain: bool = True
    follow_external_links: bool = False  # Store but don't crawl
    crawl_subdomains: bool = False

    # Include/Exclude
    include_patterns: list[str] = []  # Regex patterns
    exclude_patterns: list[str] = []

    # robots.txt
    respect_robots_txt: bool = True

    # What to crawl
    crawl_images: bool = True
    crawl_css: bool = False
    crawl_js: bool = False
    crawl_canonicals: bool = True
    crawl_hreflang: bool = True

    # Storage
    store_raw_html: bool = False
    store_rendered_html: bool = False


class SEOThresholds(BaseModel):
    """SEO analysis thresholds"""

    # Title
    title_max_chars: int = 60
    title_min_chars: int = 30
    title_max_pixels: int = 561
    title_min_pixels: int = 200

    # Meta Description
    meta_desc_max_chars: int = 155
    meta_desc_min_chars: int = 70
    meta_desc_max_pixels: int = 985
    meta_desc_min_pixels: int = 400

    # Headings
    h1_max_chars: int = 70
    h2_max_chars: int = 70

    # URL
    url_max_chars: int = 115

    # Images
    image_max_bytes: int = 102400  # 100KB
    alt_text_max_chars: int = 100

    # Content
    low_content_word_count: int = 200

    # Duplicates
    near_duplicate_threshold: float = 0.90

    # Links
    high_outlinks_count: int = 1000

    # Crawl depth
    high_crawl_depth: int = 3


# Global defaults
DEFAULT_THRESHOLDS = SEOThresholds()
