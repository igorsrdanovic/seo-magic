# SEO Spider - Usage Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite httpx selectolax lxml tldextract pydantic python-multipart aiofiles
```

### 2. Start the Server

```bash
cd /home/user/seo-magic
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### 3. Create and Run a Crawl

#### Using the API

**Create a crawl:**
```bash
curl -X POST http://localhost:8000/api/crawls/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "config": {
      "max_urls": 100,
      "max_depth": 3,
      "max_concurrent_requests": 5,
      "render_javascript": false,
      "respect_robots_txt": true
    }
  }'
```

**Start the crawl:**
```bash
curl -X POST http://localhost:8000/api/crawls/1/start
```

**Get crawl status:**
```bash
curl http://localhost:8000/api/crawls/1
```

**List all URLs:**
```bash
curl http://localhost:8000/api/crawls/1/urls/
```

**Get URL summary:**
```bash
curl http://localhost:8000/api/crawls/1/urls/summary
```

**Analyze for SEO issues:**
```bash
curl -X POST http://localhost:8000/api/crawls/1/issues/analyze
```

**Get issues:**
```bash
curl http://localhost:8000/api/crawls/1/issues/
```

**Export URLs to CSV:**
```bash
curl http://localhost:8000/api/crawls/1/urls/export/csv > urls.csv
```

**Export issues to CSV:**
```bash
curl http://localhost:8000/api/crawls/1/issues/export/csv > issues.csv
```

#### Using Python

```python
import asyncio
from backend.database import init_db, AsyncSessionLocal
from backend.models.crawl import Crawl
from backend.config import CrawlConfig
from backend.crawler.engine import CrawlEngine

async def run_crawl():
    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as session:
        # Create crawl
        crawl = Crawl(start_url="https://example.com")
        session.add(crawl)
        await session.commit()
        await session.refresh(crawl)

        # Configure
        config = CrawlConfig(
            max_urls=100,
            max_depth=3,
            max_concurrent_requests=5,
            render_javascript=False,
            respect_robots_txt=True,
            request_delay_ms=100,
        )

        # Run crawler
        engine = CrawlEngine(session, crawl, config)

        async for event in engine.run():
            if event['event'] == 'url_crawled':
                print(f"Crawled: {event['url']} (Status: {event['status_code']})")
            elif event['event'] == 'completed':
                print(f"Completed! URLs crawled: {event['urls_crawled']}")

asyncio.run(run_crawl())
```

## Configuration Options

### CrawlConfig

```python
class CrawlConfig:
    # Crawl limits
    max_urls: int = 10000              # Maximum URLs to crawl
    max_depth: int = 10                # Maximum depth from start URL
    max_folder_depth: int | None = None

    # Speed controls
    max_concurrent_requests: int = 5   # Concurrent requests
    request_delay_ms: int = 100        # Delay between requests (ms)
    request_timeout_seconds: int = 20  # Request timeout

    # JavaScript rendering
    render_javascript: bool = False    # Enable Playwright rendering
    js_wait_ms: int = 5000            # Wait time after page load
    viewport_width: int = 1024
    viewport_height: int = 768

    # User agent
    user_agent: str = "SEOSpider/1.0 (+https://example.com/bot)"

    # Scope
    stay_in_subdomain: bool = True     # Don't crawl other subdomains
    follow_external_links: bool = False
    crawl_subdomains: bool = False

    # Include/Exclude patterns (regex)
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

    # robots.txt
    respect_robots_txt: bool = True

    # What to crawl
    crawl_images: bool = True
    crawl_css: bool = False
    crawl_js: bool = False
    crawl_canonicals: bool = True
    crawl_hreflang: bool = True

    # Storage
    store_raw_html: bool = False       # Warning: Can use lots of disk space
    store_rendered_html: bool = False
```

### SEO Thresholds

```python
class SEOThresholds:
    # Title
    title_max_chars: int = 60
    title_min_chars: int = 30
    title_max_pixels: int = 561        # Google SERP truncation

    # Meta Description
    meta_desc_max_chars: int = 155
    meta_desc_min_chars: int = 70
    meta_desc_max_pixels: int = 985

    # Images
    image_max_bytes: int = 102400      # 100KB
    alt_text_max_chars: int = 100

    # Content
    low_content_word_count: int = 200
```

## API Endpoints

### Crawls

- `POST /api/crawls/` - Create a new crawl
- `GET /api/crawls/` - List all crawls
- `GET /api/crawls/{id}` - Get crawl details
- `POST /api/crawls/{id}/start` - Start a crawl (background)
- `GET /api/crawls/{id}/stream` - Stream crawl progress (SSE)
- `DELETE /api/crawls/{id}` - Delete a crawl

### URLs

- `GET /api/crawls/{id}/urls/` - List URLs with filtering
  - Query params: `status_code`, `indexability`, `content_type`, `skip`, `limit`
- `GET /api/crawls/{id}/urls/summary` - Get URL statistics
- `GET /api/crawls/{id}/urls/{url_id}` - Get detailed URL data
- `GET /api/crawls/{id}/urls/export/csv` - Export URLs to CSV

### Issues

- `GET /api/crawls/{id}/issues/` - List issues with filtering
  - Query params: `category`, `severity`, `skip`, `limit`
- `GET /api/crawls/{id}/issues/summary` - Get issue statistics
- `POST /api/crawls/{id}/issues/analyze` - Run SEO analysis (background)
- `GET /api/crawls/{id}/issues/export/csv` - Export issues to CSV

## Database Schema

The crawler uses SQLite with the following main tables:

- **crawls** - Crawl sessions
- **urls** - All discovered URLs with SEO data
- **links** - Links between URLs
- **issues** - SEO issues found
- **images** - Image assets
- **hreflangs** - Hreflang annotations
- **structured_data** - JSON-LD, Microdata, RDFa
- **redirect_chains** - Full redirect chains

## SEO Checks Performed

### Titles
- Missing title
- Title too long/short (characters)
- Title too wide (pixels - SERP truncation)
- Multiple title tags
- Duplicate titles across site
- Title identical to H1

### Meta Descriptions
- Missing meta description
- Too long/short (characters)
- Too wide (pixels)
- Multiple meta descriptions
- Duplicate meta descriptions

### Headings
- Missing H1
- Multiple H1s
- H1 too long
- Duplicate H1s across site

### Images
- Missing alt attribute
- Empty alt text
- Alt text too long
- Image over 100KB
- Missing width/height attributes (CLS)
- Broken images (4xx/5xx)

### Indexability
- Non-indexable status codes (3xx, 4xx, 5xx)
- Noindex directives (meta robots, X-Robots-Tag)
- Canonicalized URLs
- Blocked by robots.txt

### Canonicals
- Missing canonical
- Multiple canonicals
- Canonical chains/loops

### Redirects
- Redirect chains
- Redirect loops
- Temporary redirects in chain

## Performance Tips

1. **Start Small**: Test with `max_urls=10` first
2. **Adjust Concurrency**: Increase `max_concurrent_requests` for faster crawls (but be polite!)
3. **Disable JS Rendering**: Unless needed, keep `render_javascript=false`
4. **Use Request Delays**: Set `request_delay_ms` to avoid overwhelming servers
5. **Filter Scope**: Use `include_patterns` and `exclude_patterns` to focus on relevant pages
6. **Don't Store HTML**: Keep `store_raw_html=false` for large crawls

## Troubleshooting

### "Database is locked" errors
- SQLite doesn't handle high concurrency well
- Reduce `max_concurrent_requests`
- Consider PostgreSQL for production use

### Memory issues
- Reduce `max_urls`
- Disable `store_raw_html`
- Process in smaller batches

### Slow crawls
- Increase `max_concurrent_requests`
- Reduce `request_delay_ms`
- Check `respect_robots_txt` (some sites have crawl-delay directives)

### JavaScript content not captured
- Enable `render_javascript=true`
- Increase `js_wait_ms` if content loads slowly
- Note: Playwright significantly increases resource usage

## Next Steps

1. **Run analysis after crawl**:
   ```bash
   curl -X POST http://localhost:8000/api/crawls/1/issues/analyze
   ```

2. **Export results**:
   ```bash
   curl http://localhost:8000/api/crawls/1/urls/export/csv > urls.csv
   curl http://localhost:8000/api/crawls/1/issues/export/csv > issues.csv
   ```

3. **Build a frontend**: Use React, Vue, or any framework to create a UI that consumes the API

4. **Scheduled crawls**: Use cron or a task scheduler to run regular crawls

5. **Webhook notifications**: Extend the API to send notifications when crawls complete
