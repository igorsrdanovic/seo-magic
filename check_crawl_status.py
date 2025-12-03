#!/usr/bin/env python3
"""
Check the status of a crawl to understand what happened
"""
import asyncio
import sys
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.crawl import URL, Crawl

async def check_crawl_status(crawl_id: int):
    """Show detailed status of a crawl"""

    async with AsyncSessionLocal() as session:
        # Get crawl info
        crawl = await session.get(Crawl, crawl_id)
        if not crawl:
            print(f"❌ Crawl {crawl_id} not found")
            return

        print(f"\n🔍 Crawl Status Report: {crawl.start_url}")
        print("=" * 80)
        print(f"Status: {crawl.status.value if hasattr(crawl.status, 'value') else crawl.status}")
        print(f"URLs discovered: {crawl.urls_discovered}")
        print(f"URLs crawled: {crawl.urls_crawled}")
        print(f"URLs failed: {crawl.urls_failed}")

        # Get all URLs
        result = await session.execute(
            select(URL).where(URL.crawl_id == crawl_id).order_by(URL.status_code)
        )
        urls = result.scalars().all()

        print(f"\n📊 Detailed URL Breakdown:")
        print("=" * 80)

        # Group by status code
        status_groups = {}
        for url in urls:
            code = url.status_code or 0
            if code not in status_groups:
                status_groups[code] = []
            status_groups[code].append(url)

        for status_code in sorted(status_groups.keys(), reverse=True):
            urls_with_status = status_groups[status_code]
            count = len(urls_with_status)

            if status_code == 200:
                icon = "✅"
                desc = "Success"
            elif status_code >= 400:
                icon = "❌"
                desc = "Error"
            elif status_code >= 300:
                icon = "🔄"
                desc = "Redirect"
            else:
                icon = "⚠️ "
                desc = "Unknown"

            print(f"\n{icon} Status {status_code} ({desc}): {count} URLs")

            # Show first 10 of each status
            for url in urls_with_status[:10]:
                print(f"   {url.address}")
                if url.indexability_status:
                    print(f"      → {url.indexability_status}")

            if len(urls_with_status) > 10:
                print(f"   ... and {len(urls_with_status) - 10} more")

        # Check for 403s specifically
        forbidden_urls = [u for u in urls if u.status_code == 403]
        if forbidden_urls:
            print(f"\n\n⚠️  IMPORTANT: {len(forbidden_urls)} URLs returned 403 Forbidden")
            print("=" * 80)
            print("This means the site is blocking the crawler.")
            print("\n💡 Solutions:")
            print("   1. Enable JavaScript rendering:")
            print("      → Check the 'Render JavaScript' option in the UI")
            print("      → This requires: pip install playwright && playwright install chromium")
            print("\n   2. The site may be using Cloudflare or similar bot protection")
            print("      → JS rendering can often bypass these protections")
            print("\n   3. Some sites require special permissions to crawl")
            print("      → Contact the site owner if you have permission")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_crawl_status.py <crawl_id>")
        print("\nExample: python check_crawl_status.py 1")
        sys.exit(1)

    crawl_id = int(sys.argv[1])
    asyncio.run(check_crawl_status(crawl_id))
