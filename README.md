# SEO Spider

A web-based SEO auditing tool similar to Screaming Frog SEO Spider. Crawls websites, analyzes pages for SEO issues, and provides detailed reports.

## Features

- 🕷️ **Web Crawler**: BFS-based crawler with support for 100-10,000 URLs per crawl
- 🔍 **SEO Analysis**: Comprehensive analysis of titles, meta descriptions, headings, images, canonicals, and more
- 📊 **Reports**: Detailed reports with issue categorization and severity levels
- 🚀 **JavaScript Rendering**: Optional Playwright integration for JS-heavy sites
- 📈 **Real-time Progress**: Server-Sent Events for live crawl monitoring
- 💾 **Export**: CSV/Excel export functionality

## Tech Stack

**Backend (Implemented):**
- Python 3.9+ (3.9, 3.10, 3.11, 3.12 all supported)
- FastAPI with async/await
- SQLAlchemy (async) + SQLite
- httpx (async HTTP client)
- selectolax (fast HTML parsing)
- Optional: Playwright for JS rendering

**Frontend (Not Yet Implemented):**
- Planned: React 18 + Vite + TanStack Query/Table
- Current: Use REST API directly or via Swagger UI at `/docs`

## Installation

### Quick Start (Recommended)

```bash
# 1. Clone or download the repository
cd seo-magic

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

That's it! The database will be created automatically on first run.

### Alternative: Using pip install

```bash
# If you prefer editable install
pip install -e .
```

**Note:** See [INSTALL.md](INSTALL.md) for detailed installation instructions and troubleshooting.

## Usage

The tool currently provides a REST API (frontend not yet implemented). You can use it via:

### Option 1: Interactive API Docs (Easiest)
Open http://localhost:8000/docs in your browser and use the interactive Swagger UI.

### Option 2: Command Line (curl)
```bash
# Create a crawl
curl -X POST http://localhost:8000/api/crawls/ \
  -H "Content-Type: application/json" \
  -d '{"start_url": "https://example.com", "config": {"max_urls": 20}}'

# Start the crawl
curl -X POST http://localhost:8000/api/crawls/1/start

# Check status
curl http://localhost:8000/api/crawls/1

# Get URLs
curl http://localhost:8000/api/crawls/1/urls/

# Export results
curl http://localhost:8000/api/crawls/1/urls/export/csv > urls.csv
```

### Option 3: Python Script
```bash
python test_crawl.py
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed examples and [USAGE.md](USAGE.md) for comprehensive API documentation.**

## Configuration

Crawl configuration options:
- `max_urls`: Maximum URLs to crawl (default: 10,000)
- `max_depth`: Maximum crawl depth (default: 10)
- `max_concurrent_requests`: Concurrent requests (default: 5)
- `render_javascript`: Enable JS rendering (default: false)
- `respect_robots_txt`: Follow robots.txt (default: true)
- `stay_in_subdomain`: Stay within subdomain (default: true)

## SEO Checks

The tool analyzes:
- **Titles**: Length, pixel width, duplicates, missing
- **Meta Descriptions**: Length, pixel width, duplicates, missing
- **Headings**: H1/H2 structure, length, duplicates
- **Images**: Alt text, file size, dimensions, broken images
- **Canonicals**: Missing, multiple, chains, loops
- **Redirects**: Chains, loops, temporary in chain
- **Links**: Broken links, orphan pages, high outlink count
- **Indexability**: Noindex directives, robots.txt blocks
- **Duplicates**: Exact and near-duplicate content detection

## License

MIT
