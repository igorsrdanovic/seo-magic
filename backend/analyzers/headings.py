"""Heading (H1/H2) analysis"""
from ..models.crawl import URL, Issue
from ..config import SEOThresholds


def analyze_headings(url: URL, thresholds: SEOThresholds) -> list[Issue]:
    """
    Analyze heading issues for a single URL.

    Args:
        url: URL record to analyze
        thresholds: SEO thresholds configuration

    Returns:
        List of issues found
    """
    issues = []

    # H1 analysis
    h1 = url.h1_1

    if not h1 or not h1.strip():
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="h1",
                issue_type="missing",
                severity="error",
                description="Page has no H1 heading",
            )
        )
    else:
        # H1 length check
        h1_length = len(h1)
        if h1_length > thresholds.h1_max_chars:
            issues.append(
                Issue(
                    url_id=url.id,
                    crawl_id=url.crawl_id,
                    category="h1",
                    issue_type="too_long",
                    severity="warning",
                    description=f"H1 is {h1_length} characters (max {thresholds.h1_max_chars})",
                    current_value=h1[:100],
                )
            )

    # Multiple H1s
    if url.h1_2:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="h1",
                issue_type="multiple",
                severity="warning",
                description="Page has multiple H1 headings",
                current_value=f"1: {url.h1_1[:50]} | 2: {url.h1_2[:50]}",
            )
        )

    # H2 analysis
    h2 = url.h2_1

    if h2 and len(h2) > thresholds.h2_max_chars:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=url.crawl_id,
                category="h2",
                issue_type="too_long",
                severity="info",
                description=f"H2 is {len(h2)} characters (max {thresholds.h2_max_chars})",
                current_value=h2[:100],
            )
        )

    return issues


def find_duplicate_h1s(urls: list[URL], crawl_id: int) -> list[Issue]:
    """
    Find duplicate H1s across crawl.

    Args:
        urls: List of URL records from the crawl
        crawl_id: Crawl ID

    Returns:
        List of duplicate H1 issues
    """
    issues = []

    # Group by normalized H1
    h1_map: dict[str, list[URL]] = {}
    for url in urls:
        if url.h1_1 and url.indexability == "Indexable":
            normalized = url.h1_1.strip().lower()
            if normalized not in h1_map:
                h1_map[normalized] = []
            h1_map[normalized].append(url)

    # Create issues for duplicates
    for h1, url_list in h1_map.items():
        if len(url_list) > 1:
            for url in url_list:
                issues.append(
                    Issue(
                        url_id=url.id,
                        crawl_id=crawl_id,
                        category="h1",
                        issue_type="duplicate",
                        severity="info",
                        description=f"Duplicate H1 found on {len(url_list)} pages",
                        current_value=url.h1_1[:100],
                    )
                )

    return issues
