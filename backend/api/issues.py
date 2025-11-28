"""Issue reporting endpoints"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from ..database import get_db
from ..models.crawl import Issue, URL, Crawl, Image
from ..config import DEFAULT_THRESHOLDS
from ..analyzers import titles, meta, headings, images

router = APIRouter(prefix="/api/crawls/{crawl_id}/issues", tags=["issues"])


class IssueResponse(BaseModel):
    """Response model for issue data"""

    id: int
    url_id: int
    category: str
    issue_type: str
    severity: str
    description: str | None
    current_value: str | None

    class Config:
        from_attributes = True


@router.get("/")
async def list_issues(
    crawl_id: int,
    category: str | None = None,
    severity: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List issues with filtering"""
    query = select(Issue).where(Issue.crawl_id == crawl_id)

    if category:
        query = query.where(Issue.category == category)
    if severity:
        query = query.where(Issue.severity == severity)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    issues_list = result.scalars().all()

    return [IssueResponse.model_validate(issue) for issue in issues_list]


@router.get("/summary")
async def issue_summary(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Get issue counts by category and type"""
    query = select(Issue.category, Issue.issue_type, Issue.severity, func.count(Issue.id).label("count")).where(
        Issue.crawl_id == crawl_id
    ).group_by(Issue.category, Issue.issue_type, Issue.severity)

    result = await db.execute(query)

    summary = {}
    for row in result:
        if row.category not in summary:
            summary[row.category] = {}
        summary[row.category][row.issue_type] = {"count": row.count, "severity": row.severity}

    return summary


@router.post("/analyze")
async def analyze_crawl(crawl_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Analyze crawl and generate SEO issues.

    This should be run after a crawl completes.
    """
    # Verify crawl exists
    crawl = await db.get(Crawl, crawl_id)
    if not crawl:
        raise HTTPException(404, "Crawl not found")

    async def run_analysis():
        from ..database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Get all URLs for this crawl
            result = await session.execute(select(URL).where(URL.crawl_id == crawl_id))
            urls = result.scalars().all()

            thresholds = DEFAULT_THRESHOLDS

            # Analyze each URL
            for url in urls:
                # Skip non-indexable pages for most checks
                if url.status_code != 200:
                    continue

                # Title analysis
                title_issues = titles.analyze_titles(url, thresholds)
                for issue in title_issues:
                    session.add(issue)

                # Meta description analysis
                meta_issues = meta.analyze_meta_descriptions(url, thresholds)
                for issue in meta_issues:
                    session.add(issue)

                # Heading analysis
                heading_issues = headings.analyze_headings(url, thresholds)
                for issue in heading_issues:
                    session.add(issue)

                # Image analysis
                img_result = await session.execute(select(Image).where(Image.url_id == url.id))
                url_images = img_result.scalars().all()
                image_issues = images.analyze_images(url_images, url.id, crawl_id, thresholds)
                for issue in image_issues:
                    session.add(issue)

                await session.commit()

            # Run duplicate detection (cross-URL analysis)
            # Re-fetch URLs for duplicate analysis
            result = await session.execute(select(URL).where(URL.crawl_id == crawl_id))
            urls = result.scalars().all()

            # Find duplicate titles
            dup_title_issues = titles.find_duplicate_titles(urls, crawl_id)
            for issue in dup_title_issues:
                session.add(issue)

            # Find duplicate meta descriptions
            dup_meta_issues = meta.find_duplicate_meta_descriptions(urls, crawl_id)
            for issue in dup_meta_issues:
                session.add(issue)

            # Find duplicate H1s
            dup_h1_issues = headings.find_duplicate_h1s(urls, crawl_id)
            for issue in dup_h1_issues:
                session.add(issue)

            await session.commit()

    background_tasks.add_task(run_analysis)

    return {"status": "analysis_started", "crawl_id": crawl_id}


@router.get("/export/csv")
async def export_issues_csv(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Export all issues as CSV"""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    query = select(Issue, URL.address).join(URL).where(Issue.crawl_id == crawl_id)
    result = await db.execute(query)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["URL", "Category", "Issue Type", "Severity", "Description", "Current Value"])

    for issue, address in result:
        writer.writerow([address, issue.category, issue.issue_type, issue.severity, issue.description, issue.current_value])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=crawl_{crawl_id}_issues.csv"},
    )
