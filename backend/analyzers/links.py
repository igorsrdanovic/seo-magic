"""Link analysis - broken links, orphan pages, high outlink count"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.crawl import URL, Link, Issue
from ..config import SEOThresholds


async def analyze_broken_links(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find broken internal links (links to 4xx/5xx pages).

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of broken link issues
    """
    issues = []

    # Find all internal links where target has 4xx or 5xx status
    query = (
        select(Link, URL)
        .join(URL, Link.target_url_id == URL.id)
        .where(
            Link.crawl_id == crawl_id,
            Link.is_internal == True,
            URL.status_code >= 400
        )
    )

    result = await db.execute(query)
    broken_links = result.all()

    # Group by source URL to avoid duplicate issues
    source_url_map = {}
    for link, target_url in broken_links:
        if link.source_url_id not in source_url_map:
            source_url_map[link.source_url_id] = []
        source_url_map[link.source_url_id].append((link, target_url))

    # Create issues for each source URL with broken links
    for source_url_id, broken in source_url_map.items():
        count = len(broken)
        sample_target = broken[0][1]

        issues.append(
            Issue(
                url_id=source_url_id,
                crawl_id=crawl_id,
                category="links",
                issue_type="broken_links",
                severity="error",
                description=f"Page contains {count} broken internal link(s)",
                current_value=f"{sample_target.address} ({sample_target.status_code})",
            )
        )

    return issues


async def analyze_orphan_pages(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find orphan pages (pages with no internal inlinks).

    Excludes the start URL and pages blocked by robots.txt.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of orphan page issues
    """
    issues = []

    # Get start URL for this crawl
    crawl_query = select(URL).where(URL.crawl_id == crawl_id, URL.crawl_depth == 0)
    crawl_result = await db.execute(crawl_query)
    start_url = crawl_result.scalar_one_or_none()

    # Find URLs with no internal inlinks
    query = (
        select(URL)
        .outerjoin(Link, (Link.target_url_id == URL.id) & (Link.is_internal == True))
        .where(
            URL.crawl_id == crawl_id,
            URL.status_code == 200,  # Only indexable pages
            URL.indexability == "Indexable"
        )
        .group_by(URL.id)
        .having(func.count(Link.id) == 0)
    )

    result = await db.execute(query)
    orphan_urls = result.scalars().all()

    for url in orphan_urls:
        # Skip start URL
        if start_url and url.id == start_url.id:
            continue

        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=crawl_id,
                category="links",
                issue_type="orphan_page",
                severity="warning",
                description="Page has no internal inlinks (orphan page)",
                current_value=url.address,
            )
        )

    return issues


async def analyze_high_outlink_count(
    db: AsyncSession, crawl_id: int, thresholds: SEOThresholds
) -> list[Issue]:
    """
    Find pages with excessive outlinks.

    Args:
        db: Database session
        crawl_id: Crawl ID
        thresholds: SEO thresholds

    Returns:
        List of high outlink count issues
    """
    issues = []

    # Find URLs with high outlink count
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.outlinks_count > thresholds.high_outlinks_count
    )

    result = await db.execute(query)
    high_outlink_urls = result.scalars().all()

    for url in high_outlink_urls:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=crawl_id,
                category="links",
                issue_type="high_outlink_count",
                severity="warning",
                description=f"Page has {url.outlinks_count} outlinks (recommended max: {thresholds.high_outlinks_count})",
                current_value=str(url.outlinks_count),
            )
        )

    return issues


async def analyze_external_links_without_nofollow(
    db: AsyncSession, crawl_id: int
) -> list[Issue]:
    """
    Find external links without nofollow (may pass PageRank).

    This is informational - not necessarily an issue.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of external link issues
    """
    issues = []

    # Count external follow links per page
    query = (
        select(Link.source_url_id, func.count(Link.id).label('count'))
        .where(
            Link.crawl_id == crawl_id,
            Link.is_internal == False,
            Link.is_follow == True
        )
        .group_by(Link.source_url_id)
        .having(func.count(Link.id) > 0)
    )

    result = await db.execute(query)
    external_link_counts = result.all()

    for source_url_id, count in external_link_counts:
        issues.append(
            Issue(
                url_id=source_url_id,
                crawl_id=crawl_id,
                category="links",
                issue_type="external_follow_links",
                severity="info",
                description=f"Page has {count} external follow link(s) that pass PageRank",
                current_value=str(count),
            )
        )

    return issues


async def analyze_links(db: AsyncSession, crawl_id: int, thresholds: SEOThresholds) -> list[Issue]:
    """
    Run all link analyses.

    Args:
        db: Database session
        crawl_id: Crawl ID
        thresholds: SEO thresholds

    Returns:
        Combined list of all link issues
    """
    issues = []

    # Run all link analyses
    issues.extend(await analyze_broken_links(db, crawl_id))
    issues.extend(await analyze_orphan_pages(db, crawl_id))
    issues.extend(await analyze_high_outlink_count(db, crawl_id, thresholds))
    issues.extend(await analyze_external_links_without_nofollow(db, crawl_id))

    return issues
