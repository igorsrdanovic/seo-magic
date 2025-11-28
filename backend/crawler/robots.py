"""Robots.txt parsing and checking"""
from typing import Optional


class RobotsChecker:
    """Handles robots.txt fetching and checking"""

    def __init__(self, user_agent: str = "SEOSpider"):
        self.user_agent = user_agent
        self.robots_content: Optional[str] = None
        self.robots_url: Optional[str] = None
        self.fetched = False
        self.disallowed_paths: list[str] = []
        self.allowed_paths: list[str] = []

    async def fetch(self, robots_url: str, fetcher):
        """
        Fetch and parse robots.txt.

        Args:
            robots_url: URL to robots.txt (e.g., https://example.com/robots.txt)
            fetcher: Fetcher instance to use for HTTP request
        """
        self.robots_url = robots_url
        self.fetched = True

        try:
            result = await fetcher.fetch(robots_url)

            if result.status_code == 200 and result.html:
                # Parse robots.txt content
                self.robots_content = result.html
                self._parse_robots_txt(result.html)
            elif result.status_code == 404:
                # No robots.txt = allow all
                pass
            else:
                # Other errors = assume allow all
                pass

        except Exception as e:
            # If we can't fetch robots.txt, assume allow all
            print(f"Warning: Could not fetch robots.txt from {robots_url}: {e}")

    def _parse_robots_txt(self, content: str):
        """Simple robots.txt parser"""
        current_user_agent = None
        applies_to_us = False

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Split on first :
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'user-agent':
                current_user_agent = value.lower()
                # Check if this applies to us
                applies_to_us = current_user_agent == '*' or current_user_agent == self.user_agent.lower()

            elif applies_to_us:
                if key == 'disallow':
                    if value and value != '':
                        self.disallowed_paths.append(value)
                elif key == 'allow':
                    if value and value != '':
                        self.allowed_paths.append(value)

    def is_allowed(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed, False if disallowed
        """
        if not self.fetched:
            # If we haven't fetched robots.txt yet, allow by default
            return True

        if not self.disallowed_paths and not self.allowed_paths:
            # No rules = allow all
            return True

        # Extract path from URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path

        # Check explicit allows first (takes precedence)
        for allowed_path in self.allowed_paths:
            if path.startswith(allowed_path):
                return True

        # Check disallows
        for disallowed_path in self.disallowed_paths:
            if path.startswith(disallowed_path):
                return False

        # Default to allow
        return True

    def get_crawl_delay(self) -> Optional[float]:
        """
        Get crawl delay from robots.txt for our user agent.

        Returns:
            Delay in seconds, or None if not specified
        """
        if not self.fetched or not self.robots_content:
            return None

        # Simple crawl-delay parsing
        for line in self.robots_content.split('\n'):
            line = line.strip().lower()
            if line.startswith('crawl-delay:'):
                try:
                    delay = float(line.split(':', 1)[1].strip())
                    return delay
                except:
                    pass

        return None
