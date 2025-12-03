# Troubleshooting Guide

## Issue: Crawler Only Finds 2-3 URLs When Hundreds Exist

### Symptoms
- Crawl shows "3 URLs crawled, 5 discovered"
- Other SEO tools (like Screaming Frog) find hundreds of URLs
- The "Stay within subdomain" option doesn't seem to help

### Diagnosis

Run the diagnostic script to see what's happening:

```bash
python check_crawl_status.py <crawl_id>
```

This will show you the status code breakdown for all URLs.

### Common Cause: 403 Forbidden Errors

If you see many URLs with **403 Forbidden** status, the site is blocking automated requests.

**Why This Happens:**
- Modern sites use bot protection (Cloudflare, Imperva, etc.)
- They detect automated crawlers and return 403 errors
- This prevents most URLs from being crawled

**The Crawler Behavior:**
1. ✅ Start URL loads successfully (200 OK)
2. ✅ Parser extracts all links (5+ URLs discovered)
3. ❌ When fetching those links → **403 Forbidden**
4. ⚠️  Crawler marks them as "failed"
5. Result: Only 1-3 URLs successfully crawled

### Solutions

#### Solution 1: Enable JavaScript Rendering (Recommended)

Many bot protection systems can be bypassed by using a real browser:

**Step 1 - Install Playwright:**
```bash
pip install playwright
playwright install chromium
```

**Step 2 - Enable in UI:**
When creating a crawl, check the **"Render JavaScript"** option in Advanced Settings.

**Or via API:**
```json
{
  "start_url": "https://www.passged.com/",
  "config": {
    "render_javascript": true,
    "stay_in_subdomain": false
  }
}
```

**How It Works:**
- Uses a real Chromium browser
- Executes JavaScript like a human visitor
- Can complete Cloudflare challenges
- Much slower but more reliable for protected sites

#### Solution 2: Test with an Unprotected Site First

Verify the crawler works by testing with a site without protection:

```json
{
  "start_url": "https://example.com/",
  "config": {
    "stay_in_subdomain": false,
    "max_urls": 100
  }
}
```

Or try a site you control where you can whitelist the crawler.

#### Solution 3: Check robots.txt

The site might be blocking crawlers via robots.txt:

**Option A - Respect it (default):**
```json
{
  "config": {
    "respect_robots_txt": true
  }
}
```

**Option B - Override (only if you have permission):**
```json
{
  "config": {
    "respect_robots_txt": false
  }
}
```

⚠️ **Warning:** Only bypass robots.txt if you have explicit permission from the site owner.

---

## Issue: www vs non-www Not Being Treated as Same Domain

### Symptoms
- Crawling `www.example.com` but links to `example.com` aren't followed
- Or vice versa

### Solution

**Uncheck "Stay within subdomain":**

This option controls whether www and non-www are treated as different domains:

- ☑️ **Checked (strict)**: `www.example.com` and `example.com` are DIFFERENT
- ☐ **Unchecked (relaxed)**: Both are treated as SAME domain

In the UI, this option is in the **Scope** section.

---

## Issue: Only Discovering 5 URLs When Site Has Thousands

### Possible Causes

#### 1. JavaScript-Based Navigation
The site uses JavaScript frameworks (React, Vue, Angular) for navigation:

**Solution:** Enable "Render JavaScript"

#### 2. Depth Limit Too Low
Default depth is 10 levels:

**Solution:** Increase max depth:
```json
{
  "config": {
    "max_depth": 20
  }
}
```

#### 3. URL Limit Reached
Default limit is 1000 URLs:

**Solution:** Increase max URLs:
```json
{
  "config": {
    "max_urls": 10000
  }
}
```

#### 4. Infinite Scroll or Pagination
Site uses infinite scroll or "Load More" buttons:

**Solution:** Enable JavaScript rendering to interact with dynamic content

---

## Diagnostic Commands

### Check Crawl Status
```bash
python check_crawl_status.py <crawl_id>
```

Shows detailed breakdown of all URLs and their status codes.

### Check Database Directly
```bash
sqlite3 backend/database.db

SELECT address, status_code, indexability
FROM urls
WHERE crawl_id = 1
ORDER BY status_code;
```

### Test Site Access
```bash
python diagnose_crawl.py https://www.example.com/
```

Tests if the site is accessible and shows what links are found.

---

## Performance Tips

### For Large Sites (10,000+ URLs)

```json
{
  "config": {
    "max_urls": 50000,
    "max_concurrent_requests": 10,
    "request_delay_ms": 50,
    "store_raw_html": false
  }
}
```

### For JavaScript-Heavy Sites

```json
{
  "config": {
    "render_javascript": true,
    "js_wait_ms": 3000,
    "max_concurrent_requests": 2
  }
}
```

Lower concurrency when rendering JavaScript to avoid overwhelming resources.

---

## Getting Help

If you're still having issues:

1. Run `python check_crawl_status.py <crawl_id>` and share the output
2. Check the backend logs for error messages
3. Verify the site is accessible in a regular browser
4. Try with JavaScript rendering enabled

**Common mistake:** Thinking the checkbox is unchecked when it's actually checked. The default is `stay_in_subdomain=true` (checked), which means www and non-www are separate.
