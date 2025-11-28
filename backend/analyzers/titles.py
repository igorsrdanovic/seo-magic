"""Title tag analysis"""
from ..models.crawl import URL, Issue
from ..config import SEOThresholds
from ..services.pixel_width import calculate_pixel_width


def analyze_titles(url: URL, thresholds: SEOThresholds) -> list[Issue]:
    """
    Analyze title tag issues for a single URL.

    Args:
        url: URL record to analyze
        thresholds: SEO thresholds configuration

    Returns:
        List of issues found
    """
    issues = []

    title = url.title_1

    # Missing title
    if not title or not title.strip():
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="missing",
                severity="error",
                description="Page has no title tag or title is empty",
            )
        )
        return issues  # No point checking other issues

    # Length checks
    title_length = len(title)

    if title_length > thresholds.title_max_chars:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="too_long",
                severity="warning",
                description=f"Title is {title_length} characters (max {thresholds.title_max_chars})",
                current_value=title[:100],
            )
        )

    if title_length < thresholds.title_min_chars:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="too_short",
                severity="warning",
                description=f"Title is {title_length} characters (min {thresholds.title_min_chars})",
                current_value=title,
            )
        )

    # Pixel width checks
    pixel_width = calculate_pixel_width(title)

    if pixel_width > thresholds.title_max_pixels:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="too_wide_pixels",
                severity="warning",
                description=f"Title is {pixel_width}px wide, will truncate in SERP (max {thresholds.title_max_pixels}px)",
                current_value=title[:100],
            )
        )

    # Multiple titles
    if url.title_2:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="multiple",
                severity="warning",
                description="Page has multiple title tags",
                current_value=f"1: {url.title_1[:50]} | 2: {url.title_2[:50]}",
            )
        )

    # Same as H1
    if url.h1_1 and title.strip().lower() == url.h1_1.strip().lower():
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="title",
                issue_type="same_as_h1",
                severity="info",
                description="Title is identical to H1",
                current_value=title[:100],
            )
        )

    return issues


def find_duplicate_titles(urls: list[URL], crawl_id: int) -> list[Issue]:
    """
    Find duplicate titles across crawl.

    Should be run after all URLs are processed.

    Args:
        urls: List of URL records from the crawl
        crawl_id: Crawl ID

    Returns:
        List of duplicate title issues
    """
    issues = []

    # Group by normalized title
    title_map: dict[str, list[URL]] = {}
    for url in urls:
        if url.title_1 and url.indexability == "Indexable":
            normalized = url.title_1.strip().lower()
            if normalized not in title_map:
                title_map[normalized] = []
            title_map[normalized].append(url)

    # Create issues for duplicates
    for title, url_list in title_map.items():
        if len(url_list) > 1:
            for url in url_list:
                issues.append(
                    Issue(
                        url_id=url.id,
                        crawl_id=crawl_id,
                        category="title",
                        issue_type="duplicate",
                        severity="warning",
                        description=f"Duplicate title found on {len(url_list)} pages",
                        current_value=url.title_1[:100],
                    )
                )

    return issues
