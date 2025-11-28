"""Main crawl engine with BFS traversal"""
import asyncio
from collections import deque
from datetime import datetime
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from .fetcher import Fetcher, FetchResult
from .parser import HTMLParser
from .robots import RobotsChecker
from .url_utils import normalize_url, is_same_domain, calculate_folder_depth, should_skip_url
from ..config import CrawlConfig
from ..models.crawl import Crawl, URL, Link, CrawlStatus, RedirectChain


class CrawlEngine:
    """Main crawl orchestrator using BFS traversal"""

    def __init__(self, db: AsyncSession, crawl: Crawl, config: CrawlConfig):
        self.db = db
        self.crawl = crawl
        self.config = config

        self.fetcher = Fetcher(config)
        self.parser = HTMLParser()
        self.robots_checker = RobotsChecker(config.user_agent_for_robots)

        # URL frontier (BFS queue)
        self.queue: deque[tuple[str, int]] = deque()  # (url, depth)

        # Tracking sets
        self.seen_urls: set[str] = set()
        self.crawled_urls: set[str] = set()

        # URL ID mapping (for creating links)
        self.url_id_map: dict[str, int] = {}

        # Domain extraction
        self.start_domain = ""

        # Semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)

        # Stats
        self.urls_discovered = 0
        self.urls_crawled = 0
        self.urls_failed = 0

    async def initialize(self):
        """Setup before crawling"""
        await self.fetcher.initialize()

        # Parse start URL
        parsed = urlparse(self.crawl.start_url)
        self.start_domain = parsed.netloc

        # Fetch and parse robots.txt
        if self.config.respect_robots_txt:
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            await self.robots_checker.fetch(robots_url, self.fetcher)

        # Add start URL to queue
        normalized = normalize_url(self.crawl.start_url)
        self.queue.append((normalized, 0))
        self.seen_urls.add(normalized)
        self.urls_discovered = 1

    async def run(self) -> AsyncGenerator[dict, None]:
        """
        Main crawl loop. Yields progress updates.

        Yields:
            dict: Progress events with crawl status
        """
        await self.initialize()

        self.crawl.status = CrawlStatus.RUNNING
        self.crawl.started_at = datetime.utcnow()
        await self.db.commit()

        yield {"event": "started", "crawl_id": self.crawl.id, "start_url": self.crawl.start_url}

        active_tasks: set[asyncio.Task] = set()

        while self.queue or active_tasks:
            # Fill up concurrent slots
            while self.queue and len(active_tasks) < self.config.max_concurrent_requests:
                url, depth = self.queue.popleft()

                if depth > self.config.max_depth:
                    continue
                if url in self.crawled_urls:
                    continue
                if len(self.crawled_urls) >= self.config.max_urls:
                    break

                # Check robots.txt
                if self.config.respect_robots_txt and not self.robots_checker.is_allowed(url):
                    # Store as blocked
                    await self._store_blocked_url(url, depth)
                    continue

                task = asyncio.create_task(self._crawl_url(url, depth))
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)

            if active_tasks:
                # Wait for at least one to complete
                done, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    try:
                        result = task.result()
                        if result:
                            yield result
                    except Exception as e:
                        print(f"Task error: {e}")

            # Small delay to prevent tight loop
            await asyncio.sleep(0.01)

        # Crawl complete
        self.crawl.status = CrawlStatus.COMPLETED
        self.crawl.completed_at = datetime.utcnow()
        self.crawl.urls_discovered = self.urls_discovered
        self.crawl.urls_crawled = self.urls_crawled
        self.crawl.urls_failed = self.urls_failed
        await self.db.commit()

        await self.fetcher.close()

        yield {
            "event": "completed",
            "crawl_id": self.crawl.id,
            "urls_crawled": self.urls_crawled,
            "urls_failed": self.urls_failed,
        }

    async def _crawl_url(self, url: str, depth: int) -> dict:
        """Fetch and process single URL"""
        async with self.semaphore:
            self.crawled_urls.add(url)

            # Add delay between requests
            if self.config.request_delay_ms > 0:
                await asyncio.sleep(self.config.request_delay_ms / 1000)

            # Fetch
            result = await self.fetcher.fetch(url)

            # Create URL record
            url_record = URL(
                crawl_id=self.crawl.id,
                address=url,
                address_encoded=result.final_url,
                content_type=result.content_type,
                status_code=result.status_code,
                status=self._status_text(result.status_code),
                crawl_depth=depth,
                folder_depth=calculate_folder_depth(url),
                crawled_at=datetime.utcnow(),
                response_time=result.response_time,
                size_bytes=result.size_bytes,
            )

            # Store X-Robots-Tag if present
            if "x-robots-tag" in result.headers:
                url_record.x_robots_tag = result.headers["x-robots-tag"]

            # Handle redirects
            if result.redirect_chain:
                final_hop = result.redirect_chain[-1]
                url_record.redirect_uri = result.final_url
                url_record.redirect_type = final_hop.redirect_type
                url_record.redirect_chain_count = len(result.redirect_chain)

                # Store redirect chain details
                for hop_num, hop in enumerate(result.redirect_chain):
                    chain_record = RedirectChain(
                        crawl_id=self.crawl.id,
                        initial_url_id=None,  # Will update after URL is saved
                        hop_number=hop_num,
                        url=hop.url,
                        status_code=hop.status_code,
                        redirect_type=hop.redirect_type,
                    )
                    self.db.add(chain_record)

            # Parse HTML content
            if result.html and result.status_code == 200:
                parsed = self.parser.parse(result.html, url)

                url_record.html_hash = parsed.html_hash
                url_record.content_hash = parsed.content_hash
                url_record.word_count = parsed.word_count
                url_record.text_ratio = parsed.text_ratio

                url_record.title_1 = parsed.title_1
                url_record.title_1_length = len(parsed.title_1) if parsed.title_1 else None
                url_record.title_2 = parsed.title_2

                url_record.meta_description_1 = parsed.meta_description_1
                url_record.meta_description_1_length = (
                    len(parsed.meta_description_1) if parsed.meta_description_1 else None
                )
                url_record.meta_description_2 = parsed.meta_description_2

                url_record.meta_keywords_1 = parsed.meta_keywords_1
                url_record.meta_robots_1 = parsed.meta_robots
                url_record.canonical_link_element = parsed.canonical

                url_record.h1_1 = parsed.h1_1
                url_record.h1_1_length = len(parsed.h1_1) if parsed.h1_1 else None
                url_record.h1_2 = parsed.h1_2
                url_record.h2_1 = parsed.h2_1
                url_record.h2_1_length = len(parsed.h2_1) if parsed.h2_1 else None
                url_record.h2_2 = parsed.h2_2

                if self.config.store_raw_html:
                    url_record.raw_html = result.html

            # Determine indexability
            url_record.indexability, url_record.indexability_status = self._determine_indexability(url_record)

            # Save URL record first
            self.db.add(url_record)
            await self.db.flush()  # Get ID without committing

            # Store URL ID for link creation
            self.url_id_map[url] = url_record.id

            # Extract and process links (only if HTML was parsed successfully)
            if result.html and result.status_code == 200:
                parsed = self.parser.parse(result.html, url)

                outlinks_count = 0
                for link in parsed.links:
                    if should_skip_url(link.href):
                        continue

                    normalized_href = normalize_url(link.href)
                    is_internal = is_same_domain(normalized_href, self.start_domain, self.config.stay_in_subdomain)

                    # Create link record
                    link_record = Link(
                        crawl_id=self.crawl.id,
                        source_url_id=url_record.id,
                        target_url_id=self.url_id_map.get(normalized_href),  # May be None
                        target_address=normalized_href,
                        anchor_text=link.anchor_text,
                        link_type=link.link_type,
                        is_internal=is_internal,
                        is_follow="nofollow" not in (link.rel or "").lower(),
                        rel_attributes=link.rel,
                        link_position=link.position,
                    )
                    self.db.add(link_record)
                    outlinks_count += 1

                    # Queue internal links for crawling
                    if is_internal and normalized_href not in self.seen_urls:
                        self.seen_urls.add(normalized_href)
                        self.queue.append((normalized_href, depth + 1))
                        self.urls_discovered += 1

                url_record.outlinks_count = outlinks_count

                # Process images
                from ..models.crawl import Image

                for img in parsed.images:
                    image_record = Image(
                        crawl_id=self.crawl.id,
                        url_id=url_record.id,
                        src=img.src,
                        alt_text=img.alt,
                        alt_text_length=len(img.alt) if img.alt else None,
                        has_width_attr=img.width is not None,
                        has_height_attr=img.height is not None,
                        html_width=int(img.width) if img.width and img.width.isdigit() else None,
                        html_height=int(img.height) if img.height and img.height.isdigit() else None,
                    )
                    self.db.add(image_record)

            await self.db.commit()

            if result.status_code == 200:
                self.urls_crawled += 1
            else:
                self.urls_failed += 1

            return {
                "event": "url_crawled",
                "url": url,
                "status_code": result.status_code,
                "depth": depth,
                "progress": self.urls_crawled,
                "total_discovered": self.urls_discovered,
            }

    def _status_text(self, code: int) -> str:
        """Convert status code to human-readable text"""
        if code == 0:
            return "No Response"
        elif 200 <= code < 300:
            return "OK"
        elif 300 <= code < 400:
            return "Redirect"
        elif 400 <= code < 500:
            return "Client Error"
        elif 500 <= code < 600:
            return "Server Error"
        return "Unknown"

    def _determine_indexability(self, url_record: URL) -> tuple[str, str]:
        """
        Determine if URL is indexable.

        Returns:
            (indexability, reason) tuple
        """
        # Check status code first
        if url_record.status_code is None or url_record.status_code == 0:
            return "Non-Indexable", "No Response"
        if 300 <= url_record.status_code < 400:
            return "Non-Indexable", "Redirect"
        if 400 <= url_record.status_code < 500:
            return "Non-Indexable", "Client Error"
        if 500 <= url_record.status_code < 600:
            return "Non-Indexable", "Server Error"

        # Check meta robots
        if url_record.meta_robots_1:
            robots = url_record.meta_robots_1.lower()
            if "noindex" in robots:
                return "Non-Indexable", "Noindex"

        # Check X-Robots-Tag
        if url_record.x_robots_tag:
            if "noindex" in url_record.x_robots_tag.lower():
                return "Non-Indexable", "Noindex"

        # Check canonical (if pointing elsewhere)
        if url_record.canonical_link_element:
            canonical = normalize_url(url_record.canonical_link_element)
            if canonical != normalize_url(url_record.address):
                return "Non-Indexable", "Canonicalised"

        return "Indexable", ""

    async def _store_blocked_url(self, url: str, depth: int):
        """Store URL blocked by robots.txt"""
        url_record = URL(
            crawl_id=self.crawl.id,
            address=url,
            status_code=0,
            status="Blocked by robots.txt",
            crawl_depth=depth,
            folder_depth=calculate_folder_depth(url),
            indexability="Non-Indexable",
            indexability_status="Blocked by robots.txt",
        )
        self.db.add(url_record)
        await self.db.commit()

        self.urls_failed += 1
