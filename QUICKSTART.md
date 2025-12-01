# SEO Spider - Quick Start Guide

Get up and running in 2 minutes!

## Step 1: Install (30 seconds)

```bash
cd seo-magic
pip install -r requirements.txt
```

## Step 2: Start Server (10 seconds)

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: http://localhost:8000

## Step 3: Crawl a Website (1 minute)

### Option A: Using curl

```bash
# Create a crawl
curl -X POST http://localhost:8000/api/crawls/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "config": {
      "max_urls": 20,
      "max_depth": 2
    }
  }'
# Returns: {"id": 1, ...}

# Start the crawl
curl -X POST http://localhost:8000/api/crawls/1/start
# Returns: {"status": "started", "crawl_id": 1}

# Check status (wait a few seconds first)
curl http://localhost:8000/api/crawls/1
# Returns: {..., "status": "completed", "urls_crawled": 15, ...}
```

### Option B: Using Browser

1. Open: http://localhost:8000/docs
2. Click on **POST /api/crawls/**
3. Click **Try it out**
4. Paste this JSON:
   ```json
   {
     "start_url": "https://example.com",
     "config": {
       "max_urls": 20,
       "max_depth": 2
     }
   }
   ```
5. Click **Execute**
6. Note the `id` from the response
7. Go to **POST /api/crawls/{crawl_id}/start**
8. Enter the `id` and click **Execute**

### Option C: Using Python

```bash
python test_crawl.py
```

## Step 4: Analyze for SEO Issues

```bash
# Run SEO analysis
curl -X POST http://localhost:8000/api/crawls/1/issues/analyze

# Wait a few seconds, then get issues
curl http://localhost:8000/api/crawls/1/issues/
```

## Step 5: View Results

### Get URL List
```bash
curl http://localhost:8000/api/crawls/1/urls/ | python -m json.tool
```

### Get URL Summary
```bash
curl http://localhost:8000/api/crawls/1/urls/summary | python -m json.tool
```

### Get Issue Summary
```bash
curl http://localhost:8000/api/crawls/1/issues/summary | python -m json.tool
```

### Export to CSV
```bash
curl http://localhost:8000/api/crawls/1/urls/export/csv > urls.csv
curl http://localhost:8000/api/crawls/1/issues/export/csv > issues.csv
```

Open the CSV files in Excel or Google Sheets!

## Common Configuration Examples

### Small Website (Fast)
```json
{
  "start_url": "https://example.com",
  "config": {
    "max_urls": 50,
    "max_depth": 2,
    "max_concurrent_requests": 10,
    "request_delay_ms": 50
  }
}
```

### Medium Website (Balanced)
```json
{
  "start_url": "https://example.com",
  "config": {
    "max_urls": 500,
    "max_depth": 5,
    "max_concurrent_requests": 5,
    "request_delay_ms": 100
  }
}
```

### Large Website (Respectful)
```json
{
  "start_url": "https://example.com",
  "config": {
    "max_urls": 5000,
    "max_depth": 10,
    "max_concurrent_requests": 3,
    "request_delay_ms": 200,
    "respect_robots_txt": true
  }
}
```

### JavaScript-Heavy Site
```json
{
  "start_url": "https://example.com",
  "config": {
    "max_urls": 100,
    "render_javascript": true,
    "js_wait_ms": 3000
  }
}
```

**Note:** Requires Playwright: `pip install playwright && playwright install chromium`

## What You Get

After crawling, you'll have:

### URL Data (for each page):
- ✅ Title (with length and pixel width)
- ✅ Meta description (with length and pixel width)
- ✅ H1 and H2 headings
- ✅ Status code and indexability
- ✅ Canonical link
- ✅ Word count
- ✅ Inlink/outlink counts
- ✅ And 30+ more fields!

### SEO Issues Detected:
- ❌ Missing titles
- ❌ Titles too long/short
- ❌ Duplicate titles
- ❌ Missing meta descriptions
- ❌ Duplicate meta descriptions
- ❌ Missing H1
- ❌ Multiple H1s
- ❌ Missing alt text on images
- ❌ Images over 100KB
- ❌ And more!

## Troubleshooting

### Server won't start
```bash
# Check if port 8000 is already in use
lsof -ti:8000 | xargs kill -9  # macOS/Linux
# Then restart server
```

### "Module not found" error
```bash
# Make sure you're in the right directory
cd /path/to/seo-magic
python -m uvicorn backend.main:app --reload
```

### Crawl too slow
```bash
# Increase concurrency in your config
{
  "config": {
    "max_concurrent_requests": 10,  # Increase from 5
    "request_delay_ms": 50          # Decrease from 100
  }
}
```

### Database locked errors
```bash
# Reduce concurrency
{
  "config": {
    "max_concurrent_requests": 2,   # Reduce from 5
    "request_delay_ms": 200         # Increase from 100
  }
}
```

## Next Steps

1. **Read the full docs**: Check out [USAGE.md](USAGE.md) for detailed examples
2. **Try different sites**: Crawl your own website
3. **Explore the API**: Open http://localhost:8000/docs for interactive docs
4. **Filter results**: Use query parameters to filter URLs by status, indexability, etc.
5. **Build a frontend**: Create a UI using the REST API

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crawls/` | POST | Create new crawl |
| `/api/crawls/` | GET | List all crawls |
| `/api/crawls/{id}` | GET | Get crawl details |
| `/api/crawls/{id}/start` | POST | Start crawl |
| `/api/crawls/{id}/urls/` | GET | List URLs |
| `/api/crawls/{id}/urls/summary` | GET | URL statistics |
| `/api/crawls/{id}/urls/export/csv` | GET | Export URLs |
| `/api/crawls/{id}/issues/analyze` | POST | Analyze for issues |
| `/api/crawls/{id}/issues/` | GET | List issues |
| `/api/crawls/{id}/issues/summary` | GET | Issue statistics |
| `/api/crawls/{id}/issues/export/csv` | GET | Export issues |

## Tips

- Start with small crawls (max_urls: 20-50) to test
- Always respect robots.txt for production crawls
- Use request delays to be polite to servers
- Export to CSV for easy analysis in Excel
- Check `/docs` for full API documentation

That's it! You're now crawling and analyzing websites for SEO issues. 🚀
