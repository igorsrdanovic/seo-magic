"""URL data endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ..database import get_db
from ..models.crawl import URL

router = APIRouter(prefix="/api/crawls/{crawl_id}/urls", tags=["urls"])


class URLResponse(BaseModel):
    """Response model for URL data"""

    id: int
    address: str
    status_code: int | None
    status: str | None
    indexability: str | None
    indexability_status: str | None
    title_1: str | None
    title_1_length: int | None
    meta_description_1: str | None
    h1_1: str | None
    word_count: int | None
    crawl_depth: int
    inlinks_count: int
    outlinks_count: int
    response_time: float | None

    class Config:
        from_attributes = True


@router.get("/")
async def list_urls(
    crawl_id: int,
    skip: int = 0,
    limit: int = 100,
    status_code: int | None = None,
    indexability: str | None = None,
    content_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List URLs with filtering"""
    query = select(URL).where(URL.crawl_id == crawl_id)

    if status_code:
        query = query.where(URL.status_code == status_code)
    if indexability:
        query = query.where(URL.indexability == indexability)
    if content_type:
        query = query.where(URL.content_type.contains(content_type))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    urls = result.scalars().all()

    return [URLResponse.model_validate(url) for url in urls]


@router.get("/summary")
async def url_summary(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Get summary stats for crawl"""
    # Status code distribution
    status_query = select(URL.status_code, func.count(URL.id).label("count")).where(
        URL.crawl_id == crawl_id
    ).group_by(URL.status_code)

    status_result = await db.execute(status_query)
    status_dist = {row.status_code: row.count for row in status_result}

    # Indexability distribution
    index_query = select(URL.indexability, func.count(URL.id).label("count")).where(
        URL.crawl_id == crawl_id
    ).group_by(URL.indexability)

    index_result = await db.execute(index_query)
    index_dist = {row.indexability: row.count for row in index_result}

    # Content type distribution
    content_query = select(URL.content_type, func.count(URL.id).label("count")).where(
        URL.crawl_id == crawl_id
    ).group_by(URL.content_type)

    content_result = await db.execute(content_query)
    content_dist = {row.content_type: row.count for row in content_result}

    return {"status_codes": status_dist, "indexability": index_dist, "content_types": content_dist}


@router.get("/{url_id}")
async def get_url(crawl_id: int, url_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed URL data"""
    url = await db.get(URL, url_id)
    if not url or url.crawl_id != crawl_id:
        raise HTTPException(404, "URL not found")

    return URLResponse.model_validate(url)


@router.get("/export/csv")
async def export_urls_csv(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Export all URLs as CSV"""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    query = select(URL).where(URL.crawl_id == crawl_id)
    result = await db.execute(query)
    urls = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "Address",
            "Status Code",
            "Status",
            "Indexability",
            "Indexability Status",
            "Title 1",
            "Title 1 Length",
            "Meta Description 1",
            "Meta Description 1 Length",
            "H1-1",
            "H1-1 Length",
            "H2-1",
            "Canonical Link Element",
            "Word Count",
            "Crawl Depth",
            "Inlinks",
            "Outlinks",
            "Response Time",
        ]
    )

    for url in urls:
        writer.writerow(
            [
                url.address,
                url.status_code,
                url.status,
                url.indexability,
                url.indexability_status,
                url.title_1,
                url.title_1_length,
                url.meta_description_1,
                url.meta_description_1_length,
                url.h1_1,
                url.h1_1_length,
                url.h2_1,
                url.canonical_link_element,
                url.word_count,
                url.crawl_depth,
                url.inlinks_count,
                url.outlinks_count,
                url.response_time,
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=crawl_{crawl_id}_urls.csv"},
    )
