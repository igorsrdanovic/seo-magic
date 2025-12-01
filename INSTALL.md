# SEO Spider - Installation Guide

## Easy Installation (Recommended)

### Option 1: Using requirements.txt

```bash
cd /path/to/seo-magic
pip install -r requirements.txt
```

This installs all core dependencies. The tool will work without the optional dependencies.

### Option 2: Manual Installation (Minimal Core)

```bash
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite httpx selectolax lxml tldextract pydantic python-multipart aiofiles
```

### Option 3: Editable Install (For Development)

```bash
cd /path/to/seo-magic
pip install -e .
```

## Optional Dependencies

### JavaScript Rendering (Playwright)

Only install if you need to crawl JavaScript-heavy websites:

```bash
pip install playwright
playwright install chromium
```

**Warning:** Playwright requires ~500MB download and increases memory usage significantly.

### Advanced Duplicate Detection

Only install if you plan to use near-duplicate detection (not yet implemented):

```bash
pip install xxhash datasketch
```

### Image Processing

Only install if you need image dimension extraction (not yet implemented):

```bash
pip install Pillow
```

## Verify Installation

Test that everything is installed correctly:

```bash
python -c "import fastapi, sqlalchemy, httpx, selectolax; print('✅ All core dependencies installed!')"
```

## Running the Server

After installation:

```bash
cd /path/to/seo-magic
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the startup script:

```bash
./run_server.sh
```

Then open: http://localhost:8000/docs

## Common Installation Issues

### Issue: "No module named 'backend'"

**Solution:** Make sure you're in the correct directory and use one of these methods:

```bash
# Method 1: Add to PYTHONPATH
export PYTHONPATH=/path/to/seo-magic:$PYTHONPATH
python -m uvicorn backend.main:app --reload

# Method 2: Run from project root
cd /path/to/seo-magic
python -m uvicorn backend.main:app --reload

# Method 3: Install package
cd /path/to/seo-magic
pip install -e .
```

### Issue: "pip install -e ." fails

**Solution:** Use requirements.txt instead:

```bash
pip install -r requirements.txt
```

Then run with:

```bash
cd /path/to/seo-magic
python -m uvicorn backend.main:app --reload
```

### Issue: "Database is locked" errors during crawl

**Solution:** Reduce concurrency in your crawl config:

```python
config = CrawlConfig(
    max_concurrent_requests=2,  # Reduce from 5 to 2
    request_delay_ms=200,        # Increase delay
)
```

### Issue: Playwright installation fails

**Solution:** Playwright is optional. The crawler works fine without it unless you need JavaScript rendering:

```bash
# Skip Playwright and use the tool for static HTML sites
pip install -r requirements.txt
```

## System Requirements

- **Python:** 3.11 or higher
- **Memory:** 512MB minimum, 2GB recommended for large crawls
- **Disk Space:** 100MB for dependencies, additional space for crawl data
- **OS:** Linux, macOS, Windows (WSL recommended for Windows)

## Virtual Environment (Recommended)

Always use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# When done:
deactivate
```

## Docker Alternative

If you prefer Docker (not yet implemented):

```bash
# Coming soon
docker build -t seo-spider .
docker run -p 8000:8000 seo-spider
```

## Troubleshooting

If you encounter any issues:

1. **Check Python version**: `python --version` (should be 3.11+)
2. **Upgrade pip**: `pip install --upgrade pip`
3. **Install in clean environment**: Create a new virtual environment
4. **Check permissions**: Ensure you have write access to the directory
5. **Use requirements.txt**: Easier than editable install for most users

## Next Steps

After successful installation:

1. Start the server
2. Open http://localhost:8000/docs
3. Create your first crawl via the API
4. Read USAGE.md for examples

## Getting Help

- Check USAGE.md for usage examples
- Check IMPLEMENTATION_SUMMARY.md for technical details
- Review API docs at http://localhost:8000/docs
