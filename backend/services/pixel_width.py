"""
Calculate SERP pixel width using Arial 18px font metrics.
These values approximate Google's desktop SERP rendering.
"""

# Character width map for Arial 18px (approximate)
# Based on reverse-engineering Google SERP rendering
CHAR_WIDTHS = {
    # Uppercase
    'A': 12,
    'B': 12,
    'C': 13,
    'D': 13,
    'E': 12,
    'F': 11,
    'G': 14,
    'H': 13,
    'I': 5,
    'J': 9,
    'K': 12,
    'L': 10,
    'M': 15,
    'N': 13,
    'O': 14,
    'P': 12,
    'Q': 14,
    'R': 13,
    'S': 12,
    'T': 11,
    'U': 13,
    'V': 12,
    'W': 17,
    'X': 12,
    'Y': 12,
    'Z': 11,
    # Lowercase
    'a': 10,
    'b': 10,
    'c': 9,
    'd': 10,
    'e': 10,
    'f': 5,
    'g': 10,
    'h': 10,
    'i': 4,
    'j': 4,
    'k': 9,
    'l': 4,
    'm': 15,
    'n': 10,
    'o': 10,
    'p': 10,
    'q': 10,
    'r': 6,
    's': 9,
    't': 6,
    'u': 10,
    'v': 9,
    'w': 13,
    'x': 9,
    'y': 9,
    'z': 9,
    # Numbers
    '0': 10,
    '1': 10,
    '2': 10,
    '3': 10,
    '4': 10,
    '5': 10,
    '6': 10,
    '7': 10,
    '8': 10,
    '9': 10,
    # Common punctuation
    ' ': 5,
    '.': 5,
    ',': 5,
    '!': 5,
    '?': 10,
    '-': 6,
    '_': 10,
    "'": 4,
    '"': 7,
    ':': 5,
    ';': 5,
    '(': 6,
    ')': 6,
    '/': 5,
    '&': 12,
    '@': 18,
    '#': 10,
    '$': 10,
    '%': 16,
    '+': 11,
    '=': 11,
    '*': 7,
    '|': 5,
}

DEFAULT_CHAR_WIDTH = 10  # Fallback for unknown characters


def calculate_pixel_width(text: str) -> int:
    """
    Calculate approximate pixel width of text as rendered in Google SERPs.
    Uses Arial 18px font metrics.

    Args:
        text: Text to measure

    Returns:
        Approximate pixel width
    """
    if not text:
        return 0

    total_width = 0
    for char in text:
        total_width += CHAR_WIDTHS.get(char, DEFAULT_CHAR_WIDTH)

    return total_width


def will_truncate_title(text: str, max_pixels: int = 561) -> bool:
    """
    Check if title will be truncated in desktop SERP.

    Args:
        text: Title text
        max_pixels: Maximum pixel width (default: 561 for desktop)

    Returns:
        True if will truncate, False otherwise
    """
    return calculate_pixel_width(text) > max_pixels


def will_truncate_description(text: str, max_pixels: int = 985) -> bool:
    """
    Check if meta description will be truncated in desktop SERP.

    Args:
        text: Meta description text
        max_pixels: Maximum pixel width (default: 985 for desktop)

    Returns:
        True if will truncate, False otherwise
    """
    return calculate_pixel_width(text) > max_pixels
