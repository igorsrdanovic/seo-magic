"""Core database models for crawls, URLs, links, and related entities"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database import Base


class CrawlStatus(enum.Enum):
    """Crawl status enum"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Crawl(Base):
    """Main crawl record"""

    __tablename__ = "crawls"

    id = Column(Integer, primary_key=True)
    start_url = Column(String(2000), nullable=False)
    status = Column(SQLEnum(CrawlStatus), default=CrawlStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Configuration stored as JSON string
    config = Column(Text, nullable=True)

    # Stats
    urls_discovered = Column(Integer, default=0)
    urls_crawled = Column(Integer, default=0)
    urls_failed = Column(Integer, default=0)

    # Relationships
    urls = relationship("URL", back_populates="crawl", cascade="all, delete-orphan")
    links = relationship("Link", cascade="all, delete-orphan")
    issues = relationship("Issue", cascade="all, delete-orphan")
    images = relationship("Image", cascade="all, delete-orphan")
    hreflangs = relationship("Hreflang", cascade="all, delete-orphan")
    structured_data = relationship("StructuredData", cascade="all, delete-orphan")
    redirect_chains = relationship("RedirectChain", cascade="all, delete-orphan")


class URL(Base):
    """URL record with all extracted data"""

    __tablename__ = "urls"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)

    # Core URL data
    address = Column(String(2000), nullable=False, index=True)
    address_encoded = Column(String(2048), nullable=True)
    content_type = Column(String(100), nullable=True)
    status_code = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True)  # "OK", "Redirect", "Client Error", etc.

    # Indexability
    indexability = Column(String(20), nullable=True)  # "Indexable", "Non-Indexable"
    indexability_status = Column(String(100), nullable=True)  # Reason if non-indexable

    # Crawl metadata
    crawl_depth = Column(Integer, default=0)
    folder_depth = Column(Integer, default=0)
    crawled_at = Column(DateTime, nullable=True)
    response_time = Column(Float, nullable=True)  # seconds

    # Content hashes
    html_hash = Column(String(32), nullable=True)  # MD5 of raw HTML
    content_hash = Column(String(32), nullable=True)  # MD5 of text content

    # Size metrics
    size_bytes = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    text_ratio = Column(Float, nullable=True)  # text / total HTML

    # Title
    title_1 = Column(String(1000), nullable=True)
    title_1_length = Column(Integer, nullable=True)
    title_1_pixel_width = Column(Integer, nullable=True)
    title_2 = Column(String(1000), nullable=True)

    # Meta Description
    meta_description_1 = Column(String(2000), nullable=True)
    meta_description_1_length = Column(Integer, nullable=True)
    meta_description_1_pixel_width = Column(Integer, nullable=True)
    meta_description_2 = Column(String(2000), nullable=True)

    # Meta Keywords (legacy but still tracked)
    meta_keywords_1 = Column(String(2000), nullable=True)

    # Headings
    h1_1 = Column(String(1000), nullable=True)
    h1_1_length = Column(Integer, nullable=True)
    h1_2 = Column(String(1000), nullable=True)
    h2_1 = Column(String(500), nullable=True)
    h2_1_length = Column(Integer, nullable=True)
    h2_2 = Column(String(500), nullable=True)

    # Directives
    meta_robots_1 = Column(String(500), nullable=True)
    x_robots_tag = Column(String(500), nullable=True)
    canonical_link_element = Column(String(2000), nullable=True)
    canonical_http_header = Column(String(2000), nullable=True)
    rel_next = Column(String(2000), nullable=True)
    rel_prev = Column(String(2000), nullable=True)

    # Redirect data
    redirect_uri = Column(String(2000), nullable=True)
    redirect_type = Column(String(50), nullable=True)
    redirect_chain_count = Column(Integer, default=0)
    redirect_chain_has_loop = Column(Boolean, default=False)

    # Link metrics (calculated after crawl)
    inlinks_count = Column(Integer, default=0)
    unique_inlinks_count = Column(Integer, default=0)
    outlinks_count = Column(Integer, default=0)
    unique_outlinks_count = Column(Integer, default=0)
    external_outlinks_count = Column(Integer, default=0)
    link_score = Column(Float, nullable=True)  # 0-100

    # Duplicate detection
    near_duplicate_of_id = Column(Integer, ForeignKey("urls.id"), nullable=True)
    near_duplicate_similarity = Column(Float, nullable=True)

    # Raw content storage (optional, can be disabled for large crawls)
    raw_html = Column(Text, nullable=True)
    rendered_html = Column(Text, nullable=True)  # After JS rendering

    # Relationships
    crawl = relationship("Crawl", back_populates="urls")
    outgoing_links = relationship("Link", foreign_keys="Link.source_url_id", back_populates="source_url")
    incoming_links = relationship("Link", foreign_keys="Link.target_url_id", back_populates="target_url")
    issues = relationship("Issue", back_populates="url", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="url", cascade="all, delete-orphan")


class Link(Base):
    """Link between two URLs"""

    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    source_url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)
    target_url_id = Column(Integer, ForeignKey("urls.id"), nullable=True)  # NULL if external/not crawled

    target_address = Column(String(2000), nullable=False)
    anchor_text = Column(String(1000), nullable=True)
    alt_text = Column(String(1000), nullable=True)  # For image links

    link_type = Column(String(20), nullable=False)  # "hyperlink", "canonical", "hreflang", etc.
    is_internal = Column(Boolean, default=True)
    is_follow = Column(Boolean, default=True)
    rel_attributes = Column(String(200), nullable=True)  # "nofollow,sponsored"

    # Position classification
    link_position = Column(String(20), nullable=True)  # "navigation", "header", "footer", "sidebar", "content"

    # JS-only detection
    found_in_js_render = Column(Boolean, default=False)

    # Relationships
    source_url = relationship("URL", foreign_keys=[source_url_id], back_populates="outgoing_links")
    target_url = relationship("URL", foreign_keys=[target_url_id], back_populates="incoming_links")


class Issue(Base):
    """SEO issue found on a URL"""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)

    category = Column(String(50), nullable=False)  # "title", "meta_description", "h1", "images", etc.
    issue_type = Column(String(100), nullable=False)  # "missing", "duplicate", "too_long", etc.
    severity = Column(String(20), nullable=False)  # "error", "warning", "info"

    description = Column(String(500), nullable=True)
    current_value = Column(String(500), nullable=True)  # The problematic value

    # Relationships
    url = relationship("URL", back_populates="issues")


class RedirectChain(Base):
    """Stores full redirect chain for analysis"""

    __tablename__ = "redirect_chains"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    initial_url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)

    hop_number = Column(Integer, nullable=False)
    url = Column(String(2000), nullable=False)
    status_code = Column(Integer, nullable=False)
    redirect_type = Column(String(50), nullable=True)


class Image(Base):
    """Separate table for image assets"""

    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)  # Page containing image

    src = Column(String(2000), nullable=False)
    alt_text = Column(String(1000), nullable=True)
    alt_text_length = Column(Integer, nullable=True)

    size_bytes = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # HTML attributes
    has_width_attr = Column(Boolean, default=False)
    has_height_attr = Column(Boolean, default=False)
    html_width = Column(Integer, nullable=True)
    html_height = Column(Integer, nullable=True)

    status_code = Column(Integer, nullable=True)

    # Relationships
    url = relationship("URL", back_populates="images")


class Hreflang(Base):
    """Hreflang annotations"""

    __tablename__ = "hreflangs"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    source_url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)

    language = Column(String(10), nullable=False)  # "en", "en-US", "x-default"
    region = Column(String(10), nullable=True)
    href = Column(String(2000), nullable=False)
    source_type = Column(String(20), nullable=False)  # "html", "http_header", "sitemap"

    # Validation flags
    has_return_link = Column(Boolean, nullable=True)
    target_status_code = Column(Integer, nullable=True)


class StructuredData(Base):
    """JSON-LD, Microdata, RDFa detected"""

    __tablename__ = "structured_data"

    id = Column(Integer, primary_key=True)
    crawl_id = Column(Integer, ForeignKey("crawls.id"), nullable=False)
    url_id = Column(Integer, ForeignKey("urls.id"), nullable=False)

    format_type = Column(String(20), nullable=False)  # "json-ld", "microdata", "rdfa"
    schema_type = Column(String(100), nullable=False)  # "Article", "Product", "FAQPage", etc.
    raw_data = Column(Text, nullable=True)  # JSON string

    is_valid = Column(Boolean, nullable=True)
    validation_errors = Column(Text, nullable=True)  # JSON array of errors
