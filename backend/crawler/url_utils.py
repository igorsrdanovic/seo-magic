"""URL normalization and utility functions"""
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import tldextract


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent comparison and storage.

    - Lowercases scheme and domain
    - Removes default ports (80, 443)
    - Removes fragments (#)
    - Sorts query parameters
    - Removes trailing slashes from paths (except root)
    - Handles www. normalization
    """
    if not url:
        return url

    parsed = urlparse(url)

    # Lowercase scheme and domain
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove default ports
    if ':80' in netloc and scheme == 'http':
        netloc = netloc.replace(':80', '')
    if ':443' in netloc and scheme == 'https':
        netloc = netloc.replace(':443', '')

    # Get path, removing trailing slash (except for root)
    path = parsed.path
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')

    # Sort query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    sorted_query = urlencode(sorted(query_params.items()), doseq=True)

    # Reconstruct URL without fragment
    normalized = urlunparse((
        scheme,
        netloc,
        path or '/',
        parsed.params,
        sorted_query,
        ''  # Remove fragment
    ))

    return normalized


def is_same_domain(url: str, base_domain: str, strict_subdomain: bool = False) -> bool:
    """
    Check if URL is on the same domain as base_domain.

    Args:
        url: URL to check
        base_domain: Base domain (e.g., "example.com" or "www.example.com")
        strict_subdomain: If True, subdomains must match exactly. If False, allows different subdomains

    Returns:
        True if same domain, False otherwise
    """
    url_parsed = urlparse(url)
    base_parsed = urlparse(base_domain) if '://' in base_domain else urlparse(f'http://{base_domain}')

    url_netloc = url_parsed.netloc.lower()
    base_netloc = base_parsed.netloc.lower()

    # Exact match
    if url_netloc == base_netloc:
        return True

    # If strict subdomain mode, no more checking needed
    if strict_subdomain:
        return False

    # Extract domains using tldextract (handles TLDs properly)
    url_ext = tldextract.extract(url_netloc)
    base_ext = tldextract.extract(base_netloc)

    # Compare registered domain (domain + suffix)
    url_domain = f"{url_ext.domain}.{url_ext.suffix}"
    base_domain = f"{base_ext.domain}.{base_ext.suffix}"

    return url_domain == base_domain


def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Returns: netloc (e.g., "www.example.com")
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_external_link(url: str, base_url: str) -> bool:
    """Check if a link is external (different domain)"""
    return not is_same_domain(url, get_domain(base_url), strict_subdomain=False)


def calculate_folder_depth(url: str) -> int:
    """
    Calculate folder depth of URL.

    Examples:
        https://example.com/ -> 0
        https://example.com/page -> 0
        https://example.com/folder/ -> 1
        https://example.com/folder/page -> 1
        https://example.com/a/b/c/page -> 3
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')

    if not path or path == '/':
        return 0

    # Count slashes (minus the leading one)
    parts = [p for p in path.split('/') if p]
    return max(0, len(parts) - 1)


def should_skip_url(url: str) -> bool:
    """
    Check if URL should be skipped based on scheme or patterns.

    Returns True if should skip, False otherwise.
    """
    if not url:
        return True

    url_lower = url.lower()

    # Skip non-HTTP(S) schemes
    skip_schemes = ['javascript:', 'mailto:', 'tel:', 'ftp:', 'file:', 'data:']
    for scheme in skip_schemes:
        if url_lower.startswith(scheme):
            return True

    # Skip fragments-only
    if url.startswith('#'):
        return True

    return False


def get_url_extension(url: str) -> str:
    """
    Get file extension from URL path.

    Returns: Extension without dot (e.g., 'html', 'pdf'), or empty string if none
    """
    parsed = urlparse(url)
    path = parsed.path

    if '.' in path:
        # Get last part after /
        filename = path.split('/')[-1]
        if '.' in filename:
            return filename.split('.')[-1].lower()

    return ''


def is_media_file(url: str) -> bool:
    """Check if URL points to a media file (image, video, audio)"""
    ext = get_url_extension(url)

    media_extensions = {
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico', 'tiff',
        # Videos
        'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',
        # Audio
        'mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a',
    }

    return ext in media_extensions


def is_document_file(url: str) -> bool:
    """Check if URL points to a document file"""
    ext = get_url_extension(url)

    document_extensions = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'csv', 'zip', 'rar', '7z', 'tar', 'gz',
    }

    return ext in document_extensions
