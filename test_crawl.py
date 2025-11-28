"""Simple test script to verify the crawler works"""
import asyncio
import sys

sys.path.insert(0, '/home/user/seo-magic')

from backend.database import init_db, AsyncSessionLocal
from backend.models.crawl import Crawl
from backend.config import CrawlConfig
from backend.crawler.engine import CrawlEngine


async def test_crawl():
    """Test a simple crawl"""
    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create a test crawl
        crawl = Crawl(start_url="http://example.com")
        session.add(crawl)
        await session.commit()
        await session.refresh(crawl)

        print(f"Created crawl ID: {crawl.id}")
        print(f"Start URL: {crawl.start_url}")

        # Configure crawler for small test
        config = CrawlConfig(
            max_urls=5,  # Only crawl 5 URLs for testing
            max_depth=2,
            max_concurrent_requests=2,
            render_javascript=False,
            respect_robots_txt=True,
            request_delay_ms=500,  # Be polite
        )

        # Create and run engine
        engine = CrawlEngine(session, crawl, config)

        print("\nStarting crawl...")
        async for event in engine.run():
            if event['event'] == 'url_crawled':
                print(
                    f"  Crawled: {event['url']} (Status: {event['status_code']}, Depth: {event['depth']}, Progress: {event['progress']}/{event['total_discovered']})"
                )
            elif event['event'] == 'completed':
                print(f"\nCrawl completed!")
                print(f"  URLs crawled: {event['urls_crawled']}")
                print(f"  URLs failed: {event['urls_failed']}")

        # Refresh crawl to get updated stats
        await session.refresh(crawl)
        print(f"\nFinal stats:")
        print(f"  Status: {crawl.status.value}")
        print(f"  URLs discovered: {crawl.urls_discovered}")
        print(f"  URLs crawled: {crawl.urls_crawled}")
        print(f"  URLs failed: {crawl.urls_failed}")


if __name__ == "__main__":
    asyncio.run(test_crawl())
