"""Duplicate content detection analyzer"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from ..models.crawl import URL, Issue


async def analyze_duplicates(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Detect duplicate content issues.

    Checks for:
    - Exact duplicate titles
    - Exact duplicate meta descriptions
    - Exact duplicate content (by content hash)
    - Exact duplicate HTML (by html hash)

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of duplicate content issues
    """
    issues = []

    # Find duplicate titles
    issues.extend(await analyze_duplicate_titles(db, crawl_id))

    # Find duplicate meta descriptions
    issues.extend(await analyze_duplicate_meta_descriptions(db, crawl_id))

    # Find duplicate content (exact)
    issues.extend(await analyze_duplicate_content(db, crawl_id))

    # Find duplicate HTML
    issues.extend(await analyze_duplicate_html(db, crawl_id))

    return issues


async def analyze_duplicate_titles(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with duplicate titles"""
    issues = []

    # Find titles that appear more than once
    query = (
        select(URL.title_1, func.count(URL.id).label('count'))
        .where(
            URL.crawl_id == crawl_id,
            URL.title_1.isnot(None),
            URL.title_1 != '',
            URL.indexable == True
        )
        .group_by(URL.title_1)
        .having(func.count(URL.id) > 1)
    )

    result = await db.execute(query)
    duplicates = result.all()

    for title, count in duplicates:
        # Get all URLs with this title
        urls_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.title_1 == title
        )
        urls_result = await db.execute(urls_query)
        urls = urls_result.scalars().all()

        # Create an issue for each URL with duplicate title
        for url in urls:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url.id,
                    category='duplicates',
                    issue_type='duplicate_title',
                    severity='warning',
                    description=f'Title "{title[:50]}..." appears on {count} pages',
                    current_value=title if len(title) <= 500 else title[:497] + '...'
                )
            )

    return issues


async def analyze_duplicate_meta_descriptions(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with duplicate meta descriptions"""
    issues = []

    # Find meta descriptions that appear more than once
    query = (
        select(URL.meta_description_1, func.count(URL.id).label('count'))
        .where(
            URL.crawl_id == crawl_id,
            URL.meta_description_1.isnot(None),
            URL.meta_description_1 != '',
            URL.indexable == True
        )
        .group_by(URL.meta_description_1)
        .having(func.count(URL.id) > 1)
    )

    result = await db.execute(query)
    duplicates = result.all()

    for meta_desc, count in duplicates:
        # Get all URLs with this meta description
        urls_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.meta_description_1 == meta_desc
        )
        urls_result = await db.execute(urls_query)
        urls = urls_result.scalars().all()

        # Create an issue for each URL with duplicate meta description
        for url in urls:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url.id,
                    category='duplicates',
                    issue_type='duplicate_meta_description',
                    severity='warning',
                    description=f'Meta description appears on {count} pages',
                    current_value=meta_desc if len(meta_desc) <= 500 else meta_desc[:497] + '...'
                )
            )

    return issues


async def analyze_duplicate_content(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with duplicate content (same content hash)"""
    issues = []

    # Find content hashes that appear more than once
    query = (
        select(URL.content_hash, func.count(URL.id).label('count'))
        .where(
            URL.crawl_id == crawl_id,
            URL.content_hash.isnot(None),
            URL.indexable == True,
            URL.status_code == 200
        )
        .group_by(URL.content_hash)
        .having(func.count(URL.id) > 1)
    )

    result = await db.execute(query)
    duplicates = result.all()

    for content_hash, count in duplicates:
        # Get all URLs with this content hash
        urls_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.content_hash == content_hash
        )
        urls_result = await db.execute(urls_query)
        urls = urls_result.scalars().all()

        # Create an issue for each URL with duplicate content
        for url in urls:
            # Find the other URLs with the same content
            other_urls = [u.address for u in urls if u.id != url.id]

            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url.id,
                    category='duplicates',
                    issue_type='duplicate_content',
                    severity='error',
                    description=f'Exact duplicate content found on {count} pages',
                    current_value=', '.join(other_urls[:3])[:500] if other_urls else None
                )
            )

    return issues


async def analyze_duplicate_html(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with duplicate HTML (same HTML hash)"""
    issues = []

    # Find HTML hashes that appear more than once
    query = (
        select(URL.html_hash, func.count(URL.id).label('count'))
        .where(
            URL.crawl_id == crawl_id,
            URL.html_hash.isnot(None),
            URL.status_code == 200
        )
        .group_by(URL.html_hash)
        .having(func.count(URL.id) > 1)
    )

    result = await db.execute(query)
    duplicates = result.all()

    for html_hash, count in duplicates:
        # Get all URLs with this HTML hash
        urls_query = select(URL).where(
            URL.crawl_id == crawl_id,
            URL.html_hash == html_hash
        )
        urls_result = await db.execute(urls_query)
        urls = urls_result.scalars().all()

        # Only report if indexable (exact HTML duplicates are common for non-indexable pages)
        indexable_urls = [u for u in urls if u.indexable]
        if len(indexable_urls) > 1:
            for url in indexable_urls:
                # Find the other URLs with the same HTML
                other_urls = [u.address for u in indexable_urls if u.id != url.id]

                issues.append(
                    Issue(
                        crawl_id=crawl_id,
                        url_id=url.id,
                        category='duplicates',
                        issue_type='duplicate_html',
                        severity='warning',
                        description=f'Exact duplicate HTML found on {len(indexable_urls)} indexable pages',
                        current_value=', '.join(other_urls[:3])[:500] if other_urls else None
                    )
                )

    return issues
