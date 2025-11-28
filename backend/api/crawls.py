"""Crawl management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl
import json
from datetime import datetime

from ..database import get_db
from ..models.crawl import Crawl, CrawlStatus
from ..config import CrawlConfig
from ..crawler.engine import CrawlEngine

router = APIRouter(prefix="/api/crawls", tags=["crawls"])


class CreateCrawlRequest(BaseModel):
    """Request model for creating a new crawl"""

    start_url: str
    config: CrawlConfig = CrawlConfig()


class CrawlResponse(BaseModel):
    """Response model for crawl data"""

    id: int
    start_url: str
    status: str
    urls_discovered: int
    urls_crawled: int
    urls_failed: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, crawl: Crawl):
        """Convert Crawl model to response"""
        return cls(
            id=crawl.id,
            start_url=crawl.start_url,
            status=crawl.status.value if isinstance(crawl.status, CrawlStatus) else crawl.status,
            urls_discovered=crawl.urls_discovered or 0,
            urls_crawled=crawl.urls_crawled or 0,
            urls_failed=crawl.urls_failed or 0,
            created_at=crawl.created_at.isoformat() if crawl.created_at else "",
            started_at=crawl.started_at.isoformat() if crawl.started_at else None,
            completed_at=crawl.completed_at.isoformat() if crawl.completed_at else None,
        )


@router.post("/", response_model=CrawlResponse)
async def create_crawl(request: CreateCrawlRequest, db: AsyncSession = Depends(get_db)):
    """Create a new crawl"""
    crawl = Crawl(start_url=request.start_url, config=request.config.model_dump_json())
    db.add(crawl)
    await db.commit()
    await db.refresh(crawl)
    return CrawlResponse.from_orm(crawl)


@router.post("/{crawl_id}/start")
async def start_crawl(crawl_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Start a crawl (runs in background)"""
    result = await db.execute(select(Crawl).where(Crawl.id == crawl_id))
    crawl = result.scalar_one_or_none()

    if not crawl:
        raise HTTPException(404, "Crawl not found")

    if crawl.status != CrawlStatus.PENDING:
        raise HTTPException(400, f"Crawl is {crawl.status.value}, cannot start")

    # Start crawl in background
    config = CrawlConfig.model_validate_json(crawl.config) if crawl.config else CrawlConfig()

    async def run_crawl():
        # Create new database session for background task
        from ..database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Refresh crawl object in new session
            bg_crawl = await session.get(Crawl, crawl_id)
            if bg_crawl:
                engine = CrawlEngine(session, bg_crawl, config)
                async for _ in engine.run():
                    pass  # Background task just runs to completion

    background_tasks.add_task(run_crawl)

    return {"status": "started", "crawl_id": crawl_id}


@router.get("/{crawl_id}/stream")
async def stream_crawl(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Stream crawl progress via Server-Sent Events"""
    result = await db.execute(select(Crawl).where(Crawl.id == crawl_id))
    crawl = result.scalar_one_or_none()

    if not crawl:
        raise HTTPException(404, "Crawl not found")

    # Create new session for streaming
    from ..database import AsyncSessionLocal

    config = CrawlConfig.model_validate_json(crawl.config) if crawl.config else CrawlConfig()

    async def event_stream():
        async with AsyncSessionLocal() as session:
            stream_crawl = await session.get(Crawl, crawl_id)
            if stream_crawl:
                engine = CrawlEngine(session, stream_crawl, config)
                async for event in engine.run():
                    yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{crawl_id}", response_model=CrawlResponse)
async def get_crawl(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Get crawl details"""
    crawl = await db.get(Crawl, crawl_id)
    if not crawl:
        raise HTTPException(404, "Crawl not found")
    return CrawlResponse.from_orm(crawl)


@router.get("/")
async def list_crawls(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List all crawls"""
    result = await db.execute(select(Crawl).order_by(Crawl.created_at.desc()).offset(skip).limit(limit))
    crawls = result.scalars().all()
    return [CrawlResponse.from_orm(c) for c in crawls]


@router.delete("/{crawl_id}")
async def delete_crawl(crawl_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a crawl"""
    crawl = await db.get(Crawl, crawl_id)
    if not crawl:
        raise HTTPException(404, "Crawl not found")

    await db.delete(crawl)
    await db.commit()

    return {"status": "deleted", "crawl_id": crawl_id}
