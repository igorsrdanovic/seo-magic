"""HTTP fetching with optional JavaScript rendering"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx


@dataclass
class RedirectHop:
    """Single redirect in a chain"""

    url: str
    status_code: int
    redirect_type: str


@dataclass
class FetchResult:
    """Result of fetching a URL"""

    url: str
    final_url: str
    status_code: int
    content_type: Optional[str]
    html: Optional[str]
    response_time: float
    size_bytes: int
    headers: dict = field(default_factory=dict)
    redirect_chain: list[RedirectHop] = field(default_factory=list)
    js_rendered: bool = False
    js_console_errors: list[str] = field(default_factory=list)


class Fetcher:
    """HTTP fetcher with optional Playwright rendering"""

    def __init__(self, config):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.browser = None
        self.playwright = None

    async def initialize(self):
        """Setup HTTP client and optionally browser"""
        self.client = httpx.AsyncClient(
            timeout=self.config.request_timeout_seconds,
            follow_redirects=False,  # We track redirects manually
            headers={"User-Agent": self.config.user_agent},
        )

        if self.config.render_javascript:
            try:
                from playwright.async_api import async_playwright

                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=True)
            except Exception as e:
                print(f"Warning: Could not initialize Playwright: {e}")
                print("JavaScript rendering will be disabled")
                self.config.render_javascript = False

    async def close(self):
        """Cleanup resources"""
        if self.client:
            await self.client.aclose()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def fetch(self, url: str) -> FetchResult:
        """
        Fetch URL, optionally with JS rendering.

        Follows redirects manually to track the chain.
        """
        start_time = time.time()

        # First, do HTTP fetch to get status and follow redirects
        redirect_chain = []
        current_url = url
        final_response = None

        for hop_num in range(10):  # Max 10 redirects
            try:
                response = await self.client.get(current_url)

                if 300 <= response.status_code < 400:
                    location = response.headers.get("location")
                    if location:
                        # Handle relative redirects
                        if not location.startswith('http'):
                            from urllib.parse import urljoin

                            location = urljoin(current_url, location)

                        redirect_type = self._redirect_type(response.status_code)
                        redirect_chain.append(
                            RedirectHop(url=current_url, status_code=response.status_code, redirect_type=redirect_type)
                        )
                        current_url = location

                        # Add delay between redirect hops
                        if self.config.request_delay_ms > 0:
                            await asyncio.sleep(self.config.request_delay_ms / 1000)

                        continue

                final_response = response
                break

            except httpx.TimeoutException:
                return FetchResult(
                    url=url,
                    final_url=current_url,
                    status_code=0,
                    content_type=None,
                    html=None,
                    response_time=time.time() - start_time,
                    size_bytes=0,
                    redirect_chain=redirect_chain,
                )
            except httpx.RequestError as e:
                return FetchResult(
                    url=url,
                    final_url=current_url,
                    status_code=0,
                    content_type=None,
                    html=None,
                    response_time=time.time() - start_time,
                    size_bytes=0,
                    redirect_chain=redirect_chain,
                )

        if not final_response:
            return FetchResult(
                url=url,
                final_url=current_url,
                status_code=0,
                content_type=None,
                html=None,
                response_time=time.time() - start_time,
                size_bytes=0,
                redirect_chain=redirect_chain,
            )

        content_type = final_response.headers.get("content-type", "")
        html = None
        size_bytes = len(final_response.content)

        # Only parse HTML content
        if "text/html" in content_type:
            try:
                html = final_response.text
            except UnicodeDecodeError:
                # Try with errors='replace'
                html = final_response.content.decode('utf-8', errors='replace')

            # JS rendering if enabled
            if self.config.render_javascript and self.browser and html:
                rendered = await self._render_with_playwright(current_url)
                if rendered:
                    html = rendered
                    # Update size if rendered HTML is larger
                    size_bytes = max(size_bytes, len(html))

        # Get X-Robots-Tag header
        x_robots_tag = final_response.headers.get("x-robots-tag")

        return FetchResult(
            url=url,
            final_url=current_url,
            status_code=final_response.status_code,
            content_type=content_type,
            html=html,
            response_time=time.time() - start_time,
            size_bytes=size_bytes,
            headers=dict(final_response.headers),
            redirect_chain=redirect_chain,
            js_rendered=self.config.render_javascript and html is not None,
        )

    async def _render_with_playwright(self, url: str) -> Optional[str]:
        """Render page with headless Chrome"""
        try:
            page = await self.browser.new_page(
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
                user_agent=self.config.user_agent,
            )

            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            await page.goto(url, wait_until="networkidle", timeout=self.config.request_timeout_seconds * 1000)

            # Additional wait for JS
            await asyncio.sleep(self.config.js_wait_ms / 1000)

            html = await page.content()

            await page.close()

            return html

        except Exception as e:
            print(f"Playwright rendering error for {url}: {e}")
            return None

    def _redirect_type(self, status_code: int) -> str:
        """Get human-readable redirect type"""
        return {
            301: "301 Permanent",
            302: "302 Found",
            303: "303 See Other",
            307: "307 Temporary",
            308: "308 Permanent",
        }.get(status_code, f"{status_code} Redirect")
