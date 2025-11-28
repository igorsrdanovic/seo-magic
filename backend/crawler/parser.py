"""HTML parsing and content extraction"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional
from selectolax.parser import HTMLParser as SelectolaxParser
from urllib.parse import urljoin


@dataclass
class ExtractedLink:
    """A link extracted from HTML"""

    href: str
    anchor_text: Optional[str]
    link_type: str  # "hyperlink", "canonical", "image", etc.
    rel: Optional[str]
    position: Optional[str]  # "navigation", "content", etc.


@dataclass
class ExtractedImage:
    """An image extracted from HTML"""

    src: str
    alt: Optional[str]
    width: Optional[str]
    height: Optional[str]


@dataclass
class ExtractedHreflang:
    """Hreflang annotation"""

    hreflang: str
    href: str
    source: str = "html"


@dataclass
class ParsedHTML:
    """Complete parsed HTML data"""

    html_hash: str
    content_hash: str

    title_1: Optional[str]
    title_2: Optional[str]

    meta_description_1: Optional[str]
    meta_description_2: Optional[str]

    meta_keywords_1: Optional[str]
    meta_robots: Optional[str]
    canonical: Optional[str]

    h1_1: Optional[str]
    h1_2: Optional[str]
    h2_1: Optional[str]
    h2_2: Optional[str]

    word_count: int
    text_ratio: float

    links: list[ExtractedLink] = field(default_factory=list)
    images: list[ExtractedImage] = field(default_factory=list)
    hreflangs: list[ExtractedHreflang] = field(default_factory=list)
    structured_data: list[dict] = field(default_factory=list)


class HTMLParser:
    """Fast HTML parser using selectolax"""

    # Position detection patterns
    NAV_PATTERNS = re.compile(r'nav|menu|navigation', re.I)
    HEADER_PATTERNS = re.compile(r'header', re.I)
    FOOTER_PATTERNS = re.compile(r'footer', re.I)
    SIDEBAR_PATTERNS = re.compile(r'sidebar|aside', re.I)
    CONTENT_PATTERNS = re.compile(r'main|content|article|body', re.I)

    def parse(self, html: str, base_url: str) -> ParsedHTML:
        """
        Parse HTML and extract all SEO-relevant data.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            ParsedHTML with all extracted data
        """
        tree = SelectolaxParser(html)

        # Hashes
        html_hash = hashlib.md5(html.encode('utf-8', errors='ignore')).hexdigest()

        # Extract text content (excluding nav/footer for content hash)
        text_content = self._extract_text_content(tree)
        content_hash = hashlib.md5(text_content.encode('utf-8', errors='ignore')).hexdigest()

        # Word count
        words = re.findall(r'\w+', text_content)
        word_count = len(words)

        # Text ratio
        text_ratio = len(text_content) / len(html) if html else 0

        # Titles
        titles = []
        for node in tree.css('title'):
            text = node.text(strip=True)
            if text:
                titles.append(text)

        # Meta descriptions
        meta_descs = []
        for node in tree.css('meta[name="description" i]'):
            content = node.attributes.get('content', '')
            if content:
                meta_descs.append(content)

        # Meta keywords
        meta_keywords = None
        keywords_node = tree.css_first('meta[name="keywords" i]')
        if keywords_node:
            meta_keywords = keywords_node.attributes.get('content')

        # Meta robots
        meta_robots = None
        robots_node = tree.css_first('meta[name="robots" i]')
        if robots_node:
            meta_robots = robots_node.attributes.get('content')

        # Canonical
        canonical = None
        canonical_node = tree.css_first('link[rel="canonical" i]')
        if canonical_node:
            href = canonical_node.attributes.get('href')
            if href:
                canonical = urljoin(base_url, href)

        # Headings
        h1s = []
        for node in tree.css('h1'):
            text = node.text(strip=True)
            if text:
                h1s.append(text)

        h2s = []
        for node in tree.css('h2'):
            text = node.text(strip=True)
            if text:
                h2s.append(text)

        # Links
        links = self._extract_links(tree, base_url)

        # Images
        images = self._extract_images(tree, base_url)

        # Hreflang
        hreflangs = self._extract_hreflangs(tree, base_url)

        # Structured data (JSON-LD)
        structured_data = self._extract_structured_data(tree)

        return ParsedHTML(
            html_hash=html_hash,
            content_hash=content_hash,
            title_1=titles[0] if len(titles) > 0 else None,
            title_2=titles[1] if len(titles) > 1 else None,
            meta_description_1=meta_descs[0] if len(meta_descs) > 0 else None,
            meta_description_2=meta_descs[1] if len(meta_descs) > 1 else None,
            meta_keywords_1=meta_keywords,
            meta_robots=meta_robots,
            canonical=canonical,
            h1_1=h1s[0] if len(h1s) > 0 else None,
            h1_2=h1s[1] if len(h1s) > 1 else None,
            h2_1=h2s[0] if len(h2s) > 0 else None,
            h2_2=h2s[1] if len(h2s) > 1 else None,
            word_count=word_count,
            text_ratio=text_ratio,
            links=links,
            images=images,
            hreflangs=hreflangs,
            structured_data=structured_data,
        )

    def _extract_text_content(self, tree) -> str:
        """Extract visible text, excluding nav/footer"""
        # Clone tree to avoid modifying original
        # Remove script, style, nav, footer
        for tag in tree.css('script, style, nav, footer, noscript, header'):
            tag.decompose()

        body = tree.css_first('body')
        if body:
            return body.text(separator=' ', strip=True)
        return tree.text(separator=' ', strip=True)

    def _extract_links(self, tree, base_url: str) -> list[ExtractedLink]:
        """Extract all links from HTML"""
        links = []

        # Regular hyperlinks
        for node in tree.css('a[href]'):
            href = node.attributes.get('href', '')
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            anchor_text = node.text(strip=True)
            rel = node.attributes.get('rel')

            # Determine position based on parent elements
            position = self._determine_link_position(node)

            # Make absolute
            absolute_href = urljoin(base_url, href)

            links.append(
                ExtractedLink(
                    href=absolute_href, anchor_text=anchor_text, link_type="hyperlink", rel=rel, position=position
                )
            )

        # Canonical links (already extracted above, but include in links)
        for node in tree.css('link[rel="canonical" i]'):
            href = node.attributes.get('href')
            if href:
                absolute_href = urljoin(base_url, href)
                links.append(
                    ExtractedLink(
                        href=absolute_href, anchor_text=None, link_type="canonical", rel="canonical", position=None
                    )
                )

        return links

    def _determine_link_position(self, node) -> Optional[str]:
        """Walk up DOM to determine link position"""
        current = node.parent
        depth = 0

        while current and depth < 10:
            tag = current.tag
            classes = current.attributes.get('class', '')
            id_attr = current.attributes.get('id', '')

            check_str = f"{tag} {classes} {id_attr}"

            if self.NAV_PATTERNS.search(check_str):
                return "navigation"
            if self.HEADER_PATTERNS.search(check_str):
                return "header"
            if self.FOOTER_PATTERNS.search(check_str):
                return "footer"
            if self.SIDEBAR_PATTERNS.search(check_str):
                return "sidebar"
            if self.CONTENT_PATTERNS.search(check_str):
                return "content"

            current = current.parent
            depth += 1

        return "content"  # Default

    def _extract_images(self, tree, base_url: str) -> list[ExtractedImage]:
        """Extract all images"""
        images = []
        for node in tree.css('img'):
            src = node.attributes.get('src', '')
            if not src:
                continue

            # Make absolute
            absolute_src = urljoin(base_url, src)

            images.append(
                ExtractedImage(
                    src=absolute_src,
                    alt=node.attributes.get('alt'),
                    width=node.attributes.get('width'),
                    height=node.attributes.get('height'),
                )
            )
        return images

    def _extract_hreflangs(self, tree, base_url: str) -> list[ExtractedHreflang]:
        """Extract hreflang annotations"""
        hreflangs = []
        for node in tree.css('link[rel="alternate" i][hreflang]'):
            hreflang = node.attributes.get('hreflang')
            href = node.attributes.get('href')
            if hreflang and href:
                absolute_href = urljoin(base_url, href)
                hreflangs.append(ExtractedHreflang(hreflang=hreflang, href=absolute_href, source='html'))
        return hreflangs

    def _extract_structured_data(self, tree) -> list[dict]:
        """Extract JSON-LD structured data"""
        import json

        structured = []
        for node in tree.css('script[type="application/ld+json"]'):
            try:
                text = node.text()
                if text:
                    data = json.loads(text)
                    schema_type = data.get('@type', 'Unknown')
                    structured.append({'format': 'json-ld', 'type': schema_type, 'data': data})
            except json.JSONDecodeError:
                pass
        return structured
