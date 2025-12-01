#!/usr/bin/env python3
"""
Diagnostic script to understand why a crawl discovered few links
"""
import asyncio
import sys
from backend.crawler.fetcher import Fetcher
from backend.crawler.parser import HTMLParser
from backend.crawler.robots import RobotsChecker
from backend.config import CrawlConfig

async def diagnose_site(url: str):
    """Diagnose why a site might not be crawling properly"""

    print(f"🔍 Diagnosing: {url}\n")
    print("=" * 80)

    config = CrawlConfig()

    # 1. Check robots.txt
    print("\n1️⃣  Checking robots.txt...")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    robots_checker = RobotsChecker(config.user_agent_for_robots)
    fetcher = Fetcher(config)
    await fetcher.initialize()

    try:
        await robots_checker.fetch(robots_url, fetcher)
        if robots_checker.can_fetch(url):
            print("   ✅ robots.txt allows crawling")
        else:
            print("   ❌ robots.txt BLOCKS this URL")
            print(f"   User-agent: {config.user_agent_for_robots}")
    except Exception as e:
        print(f"   ⚠️  Could not check robots.txt: {e}")

    # 2. Fetch the page (without JS)
    print("\n2️⃣  Fetching page (without JavaScript)...")

    try:
        result = await fetcher.fetch(url)
        print(f"   Status Code: {result.status_code}")
        print(f"   Content Type: {result.content_type}")
        print(f"   Size: {result.size_bytes} bytes")
        print(f"   Response Time: {result.response_time}ms")

        if result.redirect_chain:
            print(f"   Redirects: {len(result.redirect_chain)} hop(s)")
            for i, hop in enumerate(result.redirect_chain):
                print(f"      {i+1}. {hop.status_code} -> {hop.url}")

            # Check if domain changed due to redirect
            start_domain = parsed.netloc
            final_domain = urlparse(result.final_url).netloc
            if start_domain != final_domain:
                print(f"\n   ⚠️  DOMAIN CHANGED: {start_domain} → {final_domain}")
                print(f"      The crawler will use '{final_domain}' as the base domain")
                print(f"      This is automatic - you don't need to change anything!")

        # 3. Parse HTML and extract links
        if result.html and result.status_code == 200:
            print("\n3️⃣  Analyzing HTML content...")
            parser = HTMLParser()
            parsed = parser.parse(result.html, url)

            print(f"   Title: {parsed.title_1}")
            print(f"   Word Count: {parsed.word_count}")
            print(f"   Links Found: {len(parsed.links)}")
            print(f"   Images Found: {len(parsed.images)}")

            # Show sample links
            if parsed.links:
                print("\n   📎 Sample links found:")
                for link in parsed.links[:10]:
                    print(f"      - {link.href}")
                    print(f"        Type: {link.link_type}, Position: {link.position}")

                if len(parsed.links) > 10:
                    print(f"      ... and {len(parsed.links) - 10} more")

                # Analyze link domains
                from urllib.parse import urlparse
                from collections import Counter

                domains = Counter()
                for link in parsed.links:
                    if link.link_type == 'hyperlink':
                        domain = urlparse(link.href).netloc
                        domains[domain] += 1

                print("\n   🌐 Links by domain:")
                start_domain = urlparse(url).netloc
                internal_count = 0
                external_count = 0

                for domain, count in domains.most_common(10):
                    # Check if this is internal or external
                    from backend.crawler.url_utils import is_same_domain
                    is_internal = is_same_domain(f"https://{domain}", url, strict_subdomain=False)

                    marker = "✅ INTERNAL" if is_internal else "⚠️  EXTERNAL"
                    print(f"      {domain}: {count} links ({marker})")

                    if is_internal:
                        internal_count += count
                    else:
                        external_count += count

                print(f"\n   📊 Summary:")
                print(f"      Internal links (will be crawled): {internal_count}")
                print(f"      External links (will be stored but NOT crawled): {external_count}")

                if external_count > internal_count:
                    print(f"\n   ⚠️  ISSUE DETECTED: Most links are EXTERNAL!")
                    print(f"      The site has {external_count} external vs {internal_count} internal links")
                    print(f"      The crawler only follows internal links by design")
                    print(f"\n      💡 This is normal if:")
                    print(f"         - Site links to partner/related sites")
                    print(f"         - Site uses different domains for different sections")
                    print(f"         - Landing page that redirects to main site")
            else:
                print("\n   ⚠️  NO LINKS FOUND!")
                print("\n   💡 Possible reasons:")
                print("      1. Site uses JavaScript to render content")
                print("      2. Links are loaded dynamically (AJAX/fetch)")
                print("      3. Site uses non-standard navigation (e.g., onclick handlers)")
                print("\n   ✨ Solution: Enable JavaScript rendering")
                print("      Set render_javascript: true in crawl config")

            # Check for JavaScript frameworks
            html_lower = result.html[:5000].lower()
            frameworks = []
            if 'react' in html_lower or '_reactRoot' in result.html:
                frameworks.append('React')
            if 'vue' in html_lower or '__vue__' in result.html:
                frameworks.append('Vue')
            if 'angular' in html_lower or 'ng-' in html_lower:
                frameworks.append('Angular')
            if 'next' in html_lower or '__NEXT_DATA__' in result.html:
                frameworks.append('Next.js')

            if frameworks:
                print(f"\n   🎨 JavaScript frameworks detected: {', '.join(frameworks)}")
                print("      This site likely requires JavaScript rendering")

        elif result.status_code != 200:
            print(f"\n   ❌ Cannot parse: HTTP {result.status_code}")

    except Exception as e:
        print(f"   ❌ Error fetching page: {e}")

    finally:
        await fetcher.close()

    # 4. Configuration recommendations
    print("\n" + "=" * 80)
    print("\n📋 RECOMMENDATIONS:\n")

    print("1. If MOST LINKS ARE EXTERNAL (different domain):")
    print("   ℹ️  The crawler is working correctly!")
    print("   ℹ️  SEO crawlers only crawl within a single domain by design")
    print("   ℹ️  External links are stored in the database but not crawled")
    print()
    print("   If you need to crawl the other domain:")
    print("   → Create a separate crawl for that domain")
    print('     {"start_url": "https://other-domain.com"}')
    print()
    print("2. If the site has few/no links found:")
    print("   → Enable JavaScript rendering:")
    print('     {"config": {"render_javascript": true}}')
    print("   → Requires: pip install playwright && playwright install chromium")
    print()
    print("3. If you want to crawl www AND non-www versions:")
    print('   {"config": {"stay_in_subdomain": false}}')
    print()
    print("4. If robots.txt is blocking:")
    print('   {"config": {"respect_robots_txt": false}}')
    print("   (Only do this if you have permission!)")
    print()
    print("5. For large sites, increase limits:")
    print('   {"config": {"max_urls": 10000, "max_depth": 20}}')

    print("\n" + "=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_crawl.py <url>")
        print("Example: python diagnose_crawl.py https://passged.com")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(diagnose_site(url))
