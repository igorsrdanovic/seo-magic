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

**Backend:**
- Python 3.9+ (3.9, 3.10, 3.11, 3.12 all supported)
- FastAPI
- SQLAlchemy (async) + SQLite
- httpx
- selectolax (fast HTML parsing)

**Frontend:**
- React 18
- Vite
- TanStack Query & Table
- Tailwind CSS
- shadcn/ui

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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Start the backend server (default: http://localhost:8000)
2. Start the frontend dev server (default: http://localhost:5173)
3. Create a new crawl with a start URL
4. Configure crawl settings (depth, concurrency, JS rendering, etc.)
5. Start the crawl and monitor progress
6. Analyze results and export reports

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
