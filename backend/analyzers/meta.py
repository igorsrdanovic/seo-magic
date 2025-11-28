"""Meta description analysis"""
from ..models.crawl import URL, Issue
from ..config import SEOThresholds
from ..services.pixel_width import calculate_pixel_width


def analyze_meta_descriptions(url: URL, thresholds: SEOThresholds) -> list[Issue]:
    """
    Analyze meta description issues for a single URL.

    Args:
        url: URL record to analyze
        thresholds: SEO thresholds configuration

    Returns:
        List of issues found
    """
    issues = []

    meta_desc = url.meta_description_1

    # Missing meta description
    if not meta_desc or not meta_desc.strip():
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="meta_description",
                issue_type="missing",
                severity="warning",
                description="Page has no meta description or it's empty",
            )
        )
        return issues

    # Length checks
    desc_length = len(meta_desc)

    if desc_length > thresholds.meta_desc_max_chars:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="meta_description",
                issue_type="too_long",
                severity="warning",
                description=f"Meta description is {desc_length} characters (max {thresholds.meta_desc_max_chars})",
                current_value=meta_desc[:100],
            )
        )

    if desc_length < thresholds.meta_desc_min_chars:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="meta_description",
                issue_type="too_short",
                severity="warning",
                description=f"Meta description is {desc_length} characters (min {thresholds.meta_desc_min_chars})",
                current_value=meta_desc,
            )
        )

    # Pixel width checks
    pixel_width = calculate_pixel_width(meta_desc)

    if pixel_width > thresholds.meta_desc_max_pixels:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="meta_description",
                issue_type="too_wide_pixels",
                severity="warning",
                description=f"Meta description is {pixel_width}px wide (max {thresholds.meta_desc_max_pixels}px)",
                current_value=meta_desc[:100],
            )
        )

    # Multiple meta descriptions
    if url.meta_description_2:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="meta_description",
                issue_type="multiple",
                severity="warning",
                description="Page has multiple meta description tags",
                current_value=f"1: {url.meta_description_1[:50]} | 2: {url.meta_description_2[:50]}",
            )
        )

    return issues


def find_duplicate_meta_descriptions(urls: list[URL], crawl_id: int) -> list[Issue]:
    """
    Find duplicate meta descriptions across crawl.

    Args:
        urls: List of URL records from the crawl
        crawl_id: Crawl ID

    Returns:
        List of duplicate meta description issues
    """
    issues = []

    # Group by normalized meta description
    desc_map: dict[str, list[URL]] = {}
    for url in urls:
        if url.meta_description_1 and url.indexability == "Indexable":
            normalized = url.meta_description_1.strip().lower()
            if normalized not in desc_map:
                desc_map[normalized] = []
            desc_map[normalized].append(url)

    # Create issues for duplicates
    for desc, url_list in desc_map.items():
        if len(url_list) > 1:
            for url in url_list:
                issues.append(
                    Issue(
                        url_id=url.id,
                        crawl_id=crawl_id,
                        category="meta_description",
                        issue_type="duplicate",
                        severity="warning",
                        description=f"Duplicate meta description found on {len(url_list)} pages",
                        current_value=url.meta_description_1[:100],
                    )
                )

    return issues
