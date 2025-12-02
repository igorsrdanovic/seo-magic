"""Structured data validation analyzer"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.crawl import URL, StructuredData, Issue


async def analyze_structured_data(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """
    Analyze structured data for issues.

    Checks for:
    - Invalid structured data (JSON-LD parse errors)
    - Multiple conflicting schema types on same page
    - Missing structured data on important pages

    Args:
        db: Database session
        crawl_id: Crawl ID

    Returns:
        List of structured data issues
    """
    issues = []

    # Find invalid structured data
    issues.extend(await analyze_invalid_structured_data(db, crawl_id))

    # Find pages with multiple conflicting schemas
    issues.extend(await analyze_conflicting_schemas(db, crawl_id))

    # Find important pages missing structured data
    issues.extend(await analyze_missing_structured_data(db, crawl_id))

    return issues


async def analyze_invalid_structured_data(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find structured data with validation errors"""
    issues = []

    # Get all invalid structured data
    query = (
        select(StructuredData, URL)
        .join(URL, StructuredData.url_id == URL.id)
        .where(
            StructuredData.crawl_id == crawl_id,
            StructuredData.is_valid == False
        )
    )
    result = await db.execute(query)
    invalid_data = result.all()

    for sd, url in invalid_data:
        issues.append(
            Issue(
                crawl_id=crawl_id,
                url_id=url.id,
                category='structured_data',
                issue_type='invalid_structured_data',
                severity='error',
                description=f'Invalid {sd.format_type} structured data ({sd.schema_type})',
                current_value=sd.schema_type
            )
        )

    return issues


async def analyze_conflicting_schemas(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find pages with multiple conflicting schema types"""
    issues = []

    # Get count of schema types per URL
    query = (
        select(
            StructuredData.url_id,
            URL.address,
            func.count(func.distinct(StructuredData.schema_type)).label('schema_count')
        )
        .join(URL, StructuredData.url_id == URL.id)
        .where(StructuredData.crawl_id == crawl_id)
        .group_by(StructuredData.url_id, URL.address)
        .having(func.count(func.distinct(StructuredData.schema_type)) > 2)
    )
    result = await db.execute(query)
    urls_with_multiple = result.all()

    for url_id, address, schema_count in urls_with_multiple:
        # Get all schema types for this URL
        schema_query = select(StructuredData.schema_type).where(
            StructuredData.crawl_id == crawl_id,
            StructuredData.url_id == url_id
        ).distinct()
        schema_result = await db.execute(schema_query)
        schema_types = [row[0] for row in schema_result.all()]

        issues.append(
            Issue(
                crawl_id=crawl_id,
                url_id=url_id,
                category='structured_data',
                issue_type='multiple_schema_types',
                severity='warning',
                description=f'Page has {schema_count} different schema types',
                current_value=', '.join(schema_types)[:500]
            )
        )

    return issues


async def analyze_missing_structured_data(db: AsyncSession, crawl_id: int) -> list[Issue]:
    """Find indexable pages that might benefit from structured data"""
    issues = []

    # Get indexable 200 pages without structured data
    query = (
        select(URL)
        .where(
            URL.crawl_id == crawl_id,
            URL.status_code == 200,
            URL.indexable == True,
            URL.word_count > 300,  # Only content pages
            ~URL.id.in_(
                select(StructuredData.url_id).where(StructuredData.crawl_id == crawl_id)
            )
        )
    )
    result = await db.execute(query)
    urls_without_sd = result.scalars().all()

    # Only report as warning for pages that look like articles/products
    # (heuristic: pages with substantial content)
    for url in urls_without_sd:
        # Only warn if it's a content page (not just navigation)
        if url.word_count and url.word_count > 500:
            issues.append(
                Issue(
                    crawl_id=crawl_id,
                    url_id=url.id,
                    category='structured_data',
                    issue_type='missing_structured_data',
                    severity='info',
                    description='Content page missing structured data',
                    current_value=f'{url.word_count} words'
                )
            )

    return issues
