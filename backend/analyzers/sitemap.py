"""Sitemap.xml analyzer"""
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.crawl import URL, Issue, Crawl
from ..crawler.url_utils import normalize_url


async def analyze_sitemap(db: AsyncSession, crawl_id: int, sitemap_urls: set[str] = None) -> list[Issue]:
    """
    Analyze sitemap.xml against crawled URLs.

    Checks for:
    - URLs in sitemap but not crawled
    - Crawled URLs not in sitemap
    - Non-200 URLs in sitemap
    - Non-indexable URLs in sitemap

    Args:
        db: Database session
        crawl_id: Crawl ID
        sitemap_urls: Pre-fetched set of URLs from sitemap (optional)

    Returns:
        List of sitemap-related issues
    """
    issues = []

    # Get sitemap URLs if not provided
    if sitemap_urls is None:
        sitemap_urls = await fetch_sitemap_urls(db, crawl_id)
        if not sitemap_urls:
            # No sitemap found or couldn't be parsed
            return issues

    # Normalize all sitemap URLs
    sitemap_urls_normalized = {normalize_url(url) for url in sitemap_urls}

    # Get all crawled URLs
    query = select(URL).where(URL.crawl_id == crawl_id)
    result = await db.execute(query)
    crawled_urls = result.scalars().all()

    # Create lookup dict by address
    crawled_by_address = {url.address: url for url in crawled_urls}
    crawled_addresses = set(crawled_by_address.keys())

    # Find URLs in sitemap but not crawled
    issues.extend(
        await analyze_sitemap_urls_not_crawled(
            db, crawl_id, sitemap_urls_normalized, crawled_addresses
        )
    )

    # Find crawled URLs not in sitemap
    issues.extend(
        await analyze_crawled_urls_not_in_sitemap(
            db, crawl_id, sitemap_urls_normalized, crawled_urls
        )
    )

    # Find non-200 URLs in sitemap
    issues.extend(
        await analyze_sitemap_non_200(
            db, crawl_id, sitemap_urls_normalized, crawled_by_address
        )
    )

    # Find non-indexable URLs in sitemap
    issues.extend(
        await analyze_sitemap_non_indexable(
            db, crawl_id, sitemap_urls_normalized, crawled_by_address
        )
    )

    return issues


async def fetch_sitemap_urls(db: AsyncSession, crawl_id: int) -> set[str]:
    """Fetch and parse sitemap.xml for a crawl"""
    # Get crawl to find start URL
    query = select(Crawl).where(Crawl.id == crawl_id)
    result = await db.execute(query)
    crawl = result.scalar_one_or_none()

    if not crawl:
        return set()

    # Determine sitemap URL
    parsed = urlparse(crawl.start_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

    try:
        # Fetch sitemap (using httpx)
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(sitemap_url)
            if response.status_code != 200:
                return set()

            # Parse XML
            urls = parse_sitemap_xml(response.text, sitemap_url)
            return urls

    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return set()


def parse_sitemap_xml(xml_content: str, base_url: str) -> set[str]:
    """Parse sitemap XML and extract URLs"""
    urls = set()

    try:
        root = ET.fromstring(xml_content)

        # Handle sitemap index files
        # Namespace handling for sitemap XML
        namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }

        # Check if it's a sitemap index
        sitemaps = root.findall('.//sm:sitemap/sm:loc', namespaces)
        if sitemaps:
            # This is a sitemap index - would need to fetch child sitemaps
            # For simplicity, we'll just note this
            print(f"Found sitemap index with {len(sitemaps)} child sitemaps")
            # In a full implementation, we'd recursively fetch these
            return urls

        # Extract URLs from regular sitemap
        url_elements = root.findall('.//sm:url/sm:loc', namespaces)
        for url_elem in url_elements:
            if url_elem.text:
                urls.add(url_elem.text.strip())

        # Also try without namespace (some sitemaps don't use it)
        if not urls:
            url_elements = root.findall('.//url/loc')
            for url_elem in url_elements:
                if url_elem.text:
                    urls.add(url_elem.text.strip())

    except ET.ParseError as e:
        print(f"Error parsing sitemap XML: {e}")

    return urls


async def analyze_sitemap_urls_not_crawled(
    db: AsyncSession,
    crawl_id: int,
    sitemap_urls: set[str],
    crawled_urls: set[str]
) -> list[Issue]:
    """Find URLs in sitemap but not in crawl"""
    issues = []

    # Find URLs in sitemap but not crawled
    not_crawled = sitemap_urls - crawled_urls

    # Note: We can't create issues for URLs not in our database since url_id is required
    # This would require either making url_id nullable or creating placeholder URL records
    # For now, we log this information
    if not_crawled:
        print(f"Found {len(not_crawled)} URLs in sitemap but not crawled")

    return issues


async def analyze_crawled_urls_not_in_sitemap(
    db: AsyncSession,
    crawl_id: int,
    sitemap_urls: set[str],
    crawled_urls: list[URL]
) -> list[Issue]:
    """Find important crawled URLs not in sitemap"""
    issues = []

    for url in crawled_urls:
        # Only check indexable 200 pages
        if url.status_code == 200 and url.indexability == "Indexable":
            if url.address not in sitemap_urls:
                issues.append(
                    Issue(
                        crawl_id=crawl_id,
                        url_id=url.id,
                        category='sitemap',
                        issue_type='not_in_sitemap',
                        severity='info',
                        description='Indexable page not found in sitemap.xml',
                        current_value=None
                    )
                )

    return issues


async def analyze_sitemap_non_200(
    db: AsyncSession,
    crawl_id: int,
    sitemap_urls: set[str],
    crawled_by_address: dict[str, URL]
) -> list[Issue]:
    """Find non-200 URLs in sitemap"""
    issues = []

    for sitemap_url in sitemap_urls:
        url_record = crawled_by_address.get(sitemap_url)
        if url_record and url_record.status_code != 200:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url_record.id,
                    category='sitemap',
                    issue_type='sitemap_non_200',
                    severity='error',
                    description=f'URL in sitemap.xml returns {url_record.status_code}',
                    current_value=str(url_record.status_code)
                )
            )

    return issues


async def analyze_sitemap_non_indexable(
    db: AsyncSession,
    crawl_id: int,
    sitemap_urls: set[str],
    crawled_by_address: dict[str, URL]
) -> list[Issue]:
    """Find non-indexable URLs in sitemap"""
    issues = []

    for sitemap_url in sitemap_urls:
        url_record = crawled_by_address.get(sitemap_url)
        if url_record and url_record.indexability != "Indexable":
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url_record.id,
                    category='sitemap',
                    issue_type='sitemap_non_indexable',
                    severity='warning',
                    description='Non-indexable URL in sitemap.xml',
                    current_value=url_record.indexability_status
                )
            )

    return issues
