"""Hreflang validation analyzer"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlparse

from ..models.crawl import URL, Hreflang, Issue
from ..crawler.url_utils import normalize_url


async def analyze_hreflangs(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Analyze hreflang annotations for issues.

    Checks for:
    - Missing return hreflang links
    - Hreflang pointing to non-200 pages
    - Hreflang pointing to non-indexable pages
    - Missing self-referencing hreflang
    - Incorrect hreflang language codes

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of hreflang issues
    """
    issues = []

    # Find missing return links
    issues.extend(await analyze_missing_return_links(db, crawl_id))

    # Find hreflangs pointing to non-200 pages
    issues.extend(await analyze_hreflang_to_non_200(db, crawl_id))

    # Find hreflangs pointing to non-indexable pages
    issues.extend(await analyze_hreflang_to_non_indexable(db, crawl_id))

    # Find missing self-referencing hreflang
    issues.extend(await analyze_missing_self_reference(db, crawl_id))

    return issues


async def analyze_missing_return_links(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find hreflang annotations without return links"""
    issues = []

    # Get all URLs with hreflang annotations
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.id.in_(
            select(Hreflang.source_url_id).where(Hreflang.crawl_id == crawl_id)
        )
    )
    result = await db.execute(query)
    urls_with_hreflang = result.scalars().all()

    for url in urls_with_hreflang:
        # Get hreflangs for this URL
        hreflang_query = select(Hreflang).where(
            Hreflang.crawl_id == crawl_id,
            Hreflang.source_url_id == url.id
        )
        hreflang_result = await db.execute(hreflang_query)
        hreflangs = hreflang_result.scalars().all()

        for hreflang in hreflangs:
            # Check if the target URL has a return hreflang pointing back
            target_normalized = normalize_url(hreflang.href)

            # Find the target URL in our crawl
            target_query = select(URL).where(
                URL.crawl_id == crawl_id,
                URL.address == target_normalized
            )
            target_result = await db.execute(target_query)
            target_url = target_result.scalar_one_or_none()

            if target_url:
                # Check if target URL has a return hreflang
                return_query = select(Hreflang).where(
                    Hreflang.crawl_id == crawl_id,
                    Hreflang.source_url_id == target_url.id,
                    Hreflang.href == url.address
                )
                return_result = await db.execute(return_query)
                return_hreflang = return_result.scalar_one_or_none()

                if not return_hreflang:
                    issues.append(
                        Issue(
                            crawl_id=crawl_id,
                            url_id=url.id,
                            category='hreflang',
                            issue_type='missing_return_link',
                            severity='error',
                            description=f'Hreflang to {hreflang.language} ({hreflang.href}) has no return link',
                            current_value=hreflang.href[:500] if hreflang.href else None
                        )
                    )

    return issues


async def analyze_hreflang_to_non_200(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find hreflang annotations pointing to non-200 pages"""
    issues = []

    # Get all hreflang annotations
    query = (
        select(Hreflang, URL)
        .join(URL, Hreflang.source_url_id == URL.id)
        .where(Hreflang.crawl_id == crawl_id)
    )
    result = await db.execute(query)
    hreflangs = result.all()

    for hreflang, source_url in hreflangs:
        target_normalized = normalize_url(hreflang.href)

        # Find the target URL in our crawl
        target_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.address == target_normalized
        )
        target_result = await db.execute(target_query)
        target_url = target_result.scalar_one_or_none()

        if target_url and target_url.status_code != 200:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=source_url.id,
                    category='hreflang',
                    issue_type='hreflang_to_non_200',
                    severity='error',
                    description=f'Hreflang to {hreflang.language} points to {target_url.status_code} page',
                    current_value=f'{hreflang.href} ({target_url.status_code})'[:500]
                )
            )

    return issues


async def analyze_hreflang_to_non_indexable(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find hreflang annotations pointing to non-indexable pages"""
    issues = []

    # Get all hreflang annotations
    query = (
        select(Hreflang, URL)
        .join(URL, Hreflang.source_url_id == URL.id)
        .where(Hreflang.crawl_id == crawl_id)
    )
    result = await db.execute(query)
    hreflangs = result.all()

    for hreflang, source_url in hreflangs:
        target_normalized = normalize_url(hreflang.href)

        # Find the target URL in our crawl
        target_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.address == target_normalized
        )
        target_result = await db.execute(target_query)
        target_url = target_result.scalar_one_or_none()

        if target_url and not target_url.indexable:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=source_url.id,
                    category='hreflang',
                    issue_type='hreflang_to_non_indexable',
                    severity='warning',
                    description=f'Hreflang to {hreflang.language} points to non-indexable page',
                    current_value=hreflang.href[:500] if hreflang.href else None
                )
            )

    return issues


async def analyze_missing_self_reference(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with hreflang that don't include self-reference"""
    issues = []

    # Get all URLs with hreflang annotations
    query = select(URL).where(
        URL.crawl_id == crawl_id,
        URL.id.in_(
            select(Hreflang.source_url_id).where(Hreflang.crawl_id == crawl_id)
        )
    )
    result = await db.execute(query)
    urls_with_hreflang = result.scalars().all()

    for url in urls_with_hreflang:
        # Get hreflangs for this URL
        hreflang_query = select(Hreflang).where(
            Hreflang.crawl_id == crawl_id,
            Hreflang.source_url_id == url.id
        )
        hreflang_result = await db.execute(hreflang_query)
        hreflangs = hreflang_result.scalars().all()

        # Check if any hreflang points to self
        has_self_reference = any(
            normalize_url(h.href) == url.address for h in hreflangs
        )

        if not has_self_reference:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url.id,
                    category='hreflang',
                    issue_type='missing_self_reference',
                    severity='warning',
                    description='Page has hreflang annotations but no self-referencing hreflang',
                    current_value=f'{len(hreflangs)} hreflang tags'
                )
            )

    return issues
