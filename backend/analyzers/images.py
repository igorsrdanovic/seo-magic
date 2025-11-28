"""Image analysis"""
from ..models.crawl import Image, Issue
from ..config import SEOThresholds


def analyze_images(images: list[Image], url_id: int, crawl_id: int, thresholds: SEOThresholds) -> list[Issue]:
    """
    Analyze image issues for a page.

    Args:
        images: List of images on the page
        url_id: URL ID the images belong to
        crawl_id: Crawl ID
        thresholds: SEO thresholds configuration

    Returns:
        List of issues found
    """
    issues = []

    for img in images:
        # Missing alt attribute
        if img.alt_text is None:
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="missing_alt_attribute",
                    severity="warning",
                    description="Image missing alt attribute",
                    current_value=img.src[:100],
                )
            )
        # Empty alt text (attribute exists but empty)
        elif img.alt_text == "":
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="missing_alt_text",
                    severity="warning",
                    description="Image has empty alt text",
                    current_value=img.src[:100],
                )
            )
        # Alt text too long
        elif len(img.alt_text) > thresholds.alt_text_max_chars:
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="alt_text_too_long",
                    severity="info",
                    description=f"Alt text is {len(img.alt_text)} chars (max {thresholds.alt_text_max_chars})",
                    current_value=img.alt_text[:100],
                )
            )

        # Image too large
        if img.size_bytes and img.size_bytes > thresholds.image_max_bytes:
            size_kb = img.size_bytes / 1024
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="over_100kb",
                    severity="warning",
                    description=f"Image is {size_kb:.1f}KB (max {thresholds.image_max_bytes/1024}KB)",
                    current_value=img.src[:100],
                )
            )

        # Missing size attributes (causes CLS)
        if not img.has_width_attr or not img.has_height_attr:
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="missing_size_attributes",
                    severity="warning",
                    description="Image missing width/height attributes (causes CLS)",
                    current_value=img.src[:100],
                )
            )

        # Broken image
        if img.status_code and img.status_code >= 400:
            issues.append(
                Issue(
                    url_id=url_id,
                    crawl_id=crawl_id,
                    category="images",
                    issue_type="broken",
                    severity="error",
                    description=f"Broken image (HTTP {img.status_code})",
                    current_value=img.src[:100],
                )
            )

    return issues
