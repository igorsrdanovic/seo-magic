"""Redirect analysis - chains, loops, temporary redirects"""
from typing import Dict, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.crawl import URL, RedirectChain, Issue
from ..crawler.url_utils import normalize_url


async def analyze_redirect_chains(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find redirect chains with more than 2 hops.

    Best practice is to have only 1 redirect hop (A -> B).
    Chains (A -> B -> C) should be avoided.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of redirect chain issues
    """
    issues = []

    # Find URLs with redirect chains > 1 hop
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.redirect_chain_count > 1
    )

    result = await db.execute(query)
    redirect_urls = result.scalars().all()

    for url in redirect_urls:
        # Get the full redirect chain for this URL
        chain_query = (
            select(RedirectChain)
            .where(RedirectChain.crawl_id == crawl_id, RedirectChain.initial_url_id == url.id)
            .order_by(RedirectChain.hop_number)
        )

        chain_result = await db.execute(chain_query)
        chain_hops = chain_result.scalars().all()

        if len(chain_hops) > 1:
            chain_description = " -> ".join([hop.url for hop in chain_hops[:3]])  # Show first 3 hops
            if len(chain_hops) > 3:
                chain_description += f" ... ({len(chain_hops)} total hops)"

            issues.append(
                Issue(
                    url_id=url.id,
                    crawl_id=crawl_id,
                    category="redirects",
                    issue_type="redirect_chain",
                    severity="warning",
                    description=f"Redirect chain with {url.redirect_chain_count} hops: {chain_description}",
                    current_value=str(url.redirect_chain_count),
                )
            )

    return issues


async def analyze_redirect_loops(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find redirect loops (A -> B -> A).

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of redirect loop issues
    """
    issues = []

    # URLs with loops have the flag set
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.redirect_chain_has_loop == True
    )

    result = await db.execute(query)
    loop_urls = result.scalars().all()

    for url in loop_urls:
        # Get the redirect chain to show the loop
        chain_query = (
            select(RedirectChain)
            .where(RedirectChain.crawl_id == crawl_id, RedirectChain.initial_url_id == url.id)
            .order_by(RedirectChain.hop_number)
        )

        chain_result = await db.execute(chain_query)
        chain_hops = chain_result.scalars().all()

        chain_description = " -> ".join([hop.url for hop in chain_hops[:5]])

        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=crawl_id,
                category="redirects",
                issue_type="redirect_loop",
                severity="error",
                description=f"Redirect loop detected: {chain_description}",
                current_value=url.redirect_uri,
            )
        )

    return issues


async def analyze_temporary_redirects(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find temporary redirects (302, 307).

    Temporary redirects don't pass PageRank and may not be appropriate
    for permanent content moves.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of temporary redirect issues
    """
    issues = []

    # Find URLs with temporary redirect status codes
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.status_code.in_([302, 307])
    )

    result = await db.execute(query)
    temp_redirect_urls = result.scalars().all()

    for url in temp_redirect_urls:
        redirect_type = "302 Found" if url.status_code == 302 else "307 Temporary"

        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=crawl_id,
                category="redirects",
                issue_type="temporary_redirect",
                severity="warning",
                description=f"Temporary redirect ({redirect_type}) - consider using 301 Permanent if content has moved permanently",
                current_value=f"{url.redirect_uri} ({url.status_code})",
            )
        )

    return issues


async def analyze_redirect_to_non_indexable(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find redirects that point to non-indexable pages (4xx, 5xx, etc.).

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of redirect to non-indexable issues
    """
    issues = []

    # Build URL mapping
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    # Find URLs that redirect
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.redirect_uri.isnot(None)
    )

    result = await db.execute(query)
    redirect_urls = result.scalars().all()

    for url in redirect_urls:
        redirect_normalized = normalize_url(url.redirect_uri)
        target = url_map.get(redirect_normalized)

        if target and target.indexability != "Indexable":
            issues.append(
                Issue(
                    url_id=url.id,
                    crawl_id=crawl_id,
                    category="redirects",
                    issue_type="redirect_to_non_indexable",
                    severity="error",
                    description=f"Redirect points to non-indexable page ({target.status_code} {target.indexability_status})",
                    current_value=f"{url.redirect_uri} ({target.status_code})",
                )
            )

    return issues


async def analyze_internal_links_to_redirects(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find internal links that point to URLs that redirect.

    Best practice is to update links to point directly to the final destination.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of internal links to redirect issues
    """
    issues = []

    # Build URL mapping
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    # Find URLs that redirect
    redirect_urls_query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.redirect_uri.isnot(None)
    )

    redirect_result = await db.execute(redirect_urls_query)
    redirect_urls_set = {normalize_url(url.address) for url in redirect_result.scalars()}

    # Find internal links to redirect URLs
    from ..models.crawl import Link

    links_query = select(Link).where(
        Link.crawl_id == crawl_id,
        Link.is_internal == True,
        Link.link_type == "hyperlink"
    )

    links_result = await db.execute(links_query)
    links = links_result.scalars().all()

    # Group by source URL to avoid too many issues
    source_redirect_counts: Dict[int, int] = {}

    for link in links:
        target_normalized = normalize_url(link.target_address)
        if target_normalized in redirect_urls_set:
            source_redirect_counts[link.source_url_id] = source_redirect_counts.get(link.source_url_id, 0) + 1

    # Create issues for pages with links to redirects
    for source_url_id, count in source_redirect_counts.items():
        if count > 0:
            issues.append(
                Issue(
                    url_id=source_url_id,
                    crawl_id=crawl_id,
                    category="redirects",
                    issue_type="links_to_redirects",
                    severity="info",
                    description=f"Page contains {count} internal link(s) to URLs that redirect - consider updating to point directly to final destination",
                    current_value=str(count),
                )
            )

    return issues


async def analyze_redirects(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Run all redirect analyses.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        Combined list of all redirect issues
    """
    issues = []

    issues.extend(await analyze_redirect_chains(db, crawl_id))
    issues.extend(await analyze_redirect_loops(db, crawl_id))
    issues.extend(await analyze_temporary_redirects(db, crawl_id))
    issues.extend(await analyze_redirect_to_non_indexable(db, crawl_id))
    issues.extend(await analyze_internal_links_to_redirects(db, crawl_id))

    return issues
