"""Canonical link analysis - chains, conflicts, missing"""
from typing import Optional, Dict, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.crawl import URL, Issue
from ..crawler.url_utils import normalize_url


async def analyze_missing_canonicals(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find indexable pages without canonical tags.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of missing canonical issues
    """
    issues = []

    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.status_code == 200,
        URL.indexability == "Indexable",
        URL.canonical_link_element.is_(None)
    )

    result = await db.execute(query)
    urls_without_canonical = result.scalars().all()

    for url in urls_without_canonical:
        issues.append(
            Issue(
                url_id=url.id,
                crawl_id=crawl_id,
                category="canonical",
                issue_type="missing_canonical",
                severity="warning",
                description="Indexable page missing canonical tag",
                current_value=url.address,
            )
        )

    return issues


async def analyze_canonical_chains(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find canonical chains (A -> B -> C).

    A canonical chain occurs when page A canonicalizes to B,
    and B canonicalizes to C. This should be avoided.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of canonical chain issues
    """
    issues = []

    # Get all URLs with canonicals
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.canonical_link_element.isnot(None)
    )

    result = await db.execute(query)
    urls_with_canonicals = result.scalars().all()

    # Build mapping of address -> URL object
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    # Check for chains
    for url in urls_with_canonicals:
        canonical_normalized = normalize_url(url.canonical_link_element)
        self_normalized = normalize_url(url.address)

        # Skip self-referencing canonicals
        if canonical_normalized == self_normalized:
            continue

        # Check if canonical target also has a canonical (creating a chain)
        canonical_target = url_map.get(canonical_normalized)
        if canonical_target and canonical_target.canonical_link_element:
            target_canonical_normalized = normalize_url(canonical_target.canonical_link_element)

            # If target's canonical is different from itself, we have a chain
            if target_canonical_normalized != canonical_normalized:
                issues.append(
                    Issue(
                        url_id=url.id,
                        crawl_id=crawl_id,
                        category="canonical",
                        issue_type="canonical_chain",
                        severity="error",
                        description=f"Canonical chain detected: {url.address} -> {canonical_target.address} -> {canonical_target.canonical_link_element}",
                        current_value=url.canonical_link_element,
                    )
                )

    return issues


async def analyze_canonical_loops(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find canonical loops (A -> B -> A).

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of canonical loop issues
    """
    issues = []

    # Get all URLs with canonicals
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.canonical_link_element.isnot(None)
    )

    result = await db.execute(query)
    urls_with_canonicals = result.scalars().all()

    # Build mapping
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    # Check for loops
    checked: Set[int] = set()

    for url in urls_with_canonicals:
        if url.id in checked:
            continue

        visited = set()
        current = url

        while current:
            if current.id in visited:
                # Loop detected
                issues.append(
                    Issue(
                        url_id=url.id,
                        crawl_id=crawl_id,
                        category="canonical",
                        issue_type="canonical_loop",
                        severity="error",
                        description=f"Canonical loop detected involving {url.address}",
                        current_value=url.canonical_link_element,
                    )
                )
                break

            visited.add(current.id)
            checked.add(current.id)

            # Get next in chain
            if not current.canonical_link_element:
                break

            canonical_normalized = normalize_url(current.canonical_link_element)
            current_normalized = normalize_url(current.address)

            if canonical_normalized == current_normalized:
                # Self-referencing, stop
                break

            current = url_map.get(canonical_normalized)
            if not current:
                # Canonical points to un-crawled URL, stop
                break

    return issues


async def analyze_canonical_to_non_indexable(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find pages that canonicalize to non-indexable pages.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of canonical to non-indexable issues
    """
    issues = []

    # Get all URLs with canonicals
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.canonical_link_element.isnot(None)
    )

    result = await db.execute(query)
    urls_with_canonicals = result.scalars().all()

    # Build mapping
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    for url in urls_with_canonicals:
        canonical_normalized = normalize_url(url.canonical_link_element)
        self_normalized = normalize_url(url.address)

        # Skip self-referencing
        if canonical_normalized == self_normalized:
            continue

        # Check if canonical target is indexable
        canonical_target = url_map.get(canonical_normalized)
        if canonical_target and canonical_target.indexability != "Indexable":
            issues.append(
                Issue(
                    url_id=url.id,
                    crawl_id=crawl_id,
                    category="canonical",
                    issue_type="canonical_to_non_indexable",
                    severity="error",
                    description=f"Canonical points to non-indexable page ({canonical_target.indexability_status})",
                    current_value=url.canonical_link_element,
                )
            )

    return issues


async def analyze_multiple_canonicals_in_group(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Find groups of pages that canonicalize to each other
    but have conflicting canonical targets.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of conflicting canonical issues
    """
    issues = []

    # Get all URLs with canonicals
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.canonical_link_element.isnot(None)
    )

    result = await db.execute(query)
    urls_with_canonicals = result.scalars().all()

    # Group by canonical target
    canonical_groups: Dict[str, list[URL]] = {}

    for url in urls_with_canonicals:
        canonical_normalized = normalize_url(url.canonical_link_element)
        if canonical_normalized not in canonical_groups:
            canonical_groups[canonical_normalized] = []
        canonical_groups[canonical_normalized].append(url)

    # Check if canonical target itself has a different canonical
    url_map: Dict[str, URL] = {}
    all_urls_query = select(URL).where(URL.crawl_id == crawl_id)
    all_result = await db.execute(all_urls_query)
    for url in all_result.scalars():
        normalized = normalize_url(url.address)
        url_map[normalized] = url

    for canonical_target, urls in canonical_groups.items():
        target_url = url_map.get(canonical_target)

        if target_url and target_url.canonical_link_element:
            target_canonical = normalize_url(target_url.canonical_link_element)

            # If target canonicalizes somewhere else, conflict
            if target_canonical != canonical_target:
                for url in urls:
                    issues.append(
                        Issue(
                            url_id=url.id,
                            crawl_id=crawl_id,
                            category="canonical",
                            issue_type="canonical_conflict",
                            severity="error",
                            description=f"Canonical conflict: points to {target_url.address}, which canonicalizes to {target_url.canonical_link_element}",
                            current_value=url.canonical_link_element,
                        )
                    )

    return issues


async def analyze_canonicals(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Run all canonical analyses.

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        Combined list of all canonical issues
    """
    issues = []

    issues.extend(await analyze_missing_canonicals(db, crawl_id))
    issues.extend(await analyze_canonical_chains(db, crawl_id))
    issues.extend(await analyze_canonical_loops(db, crawl_id))
    issues.extend(await analyze_canonical_to_non_indexable(db, crawl_id))
    issues.extend(await analyze_multiple_canonicals_in_group(db, crawl_id))

    return issues
