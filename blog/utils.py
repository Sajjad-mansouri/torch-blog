# blog/utils.py
import math
import re

import bleach
from django.utils.html import strip_tags

# ============================================================
# HTML sanitization
# ============================================================

ALLOWED_TAGS = [
    # Text
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "del",
    "ins",
    "sub",
    "sup",
    "mark",
    "small",
    "span",
    # Headings
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # Lists
    "ul",
    "ol",
    "li",
    # Quotes and code
    "blockquote",
    "pre",
    "code",
    "kbd",
    "samp",
    # Links and images
    "a",
    "img",
    # Tables
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    # Media
    "figure",
    "figcaption",
    # Divider
    "hr",
    "div",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "dir", "lang"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "th": ["colspan", "rowspan", "scope"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]


def sanitize_html(html: str) -> str:
    """
    Clean an HTML string by removing every tag, attribute, and URL
    protocol that is not on the allow list.

    Returns the cleaned HTML string, or an empty string if input is empty.
    """
    if not html:
        return ""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,  # remove disallowed tags entirely, don't escape them
        strip_comments=True,  # remove HTML comments
    )


# ============================================================
# clean_text — HTML → plain text
# ============================================================


def clean_text(html: str) -> str:
    """
    Convert an HTML string into plain text.

    Steps:
    1. Strip all HTML tags (keep the text they wrapped).
    2. Decode HTML entities (&amp; → &, &nbsp; → space, etc.).
    3. Collapse whitespace (newlines, tabs, repeated spaces) into single spaces.
    4. Trim leading and trailing whitespace.

    Used for:
    - Computing reading time.
    - Auto-generating `meta_description`.
    - Anywhere you need the text content without markup.

    Returns an empty string if input is empty or None.
    """
    if not html:
        return ""

    # Step 1: remove HTML tags but keep their text content
    text = strip_tags(html)

    # Step 2: decode HTML entities
    #   bleach.clean with no allowed tags will decode entities and strip
    #   anything left (which shouldn't be anything, since step 1 already
    #   removed the tags).
    text = bleach.clean(text, tags=[], strip=True)

    # Step 3: collapse all whitespace (spaces, tabs, newlines) into one space
    text = re.sub(r"\s+", " ", text)

    # Step 4: trim
    return text.strip()


# ============================================================
# calculate_reading_time — words per minute
# ============================================================

# Reading speed in words per minute.
#   English:  ~200 wpm is the commonly used average.
#   Persian:  ~180 wpm, since Persian words tend to be longer on screen.
WORDS_PER_MINUTE_EN = 200
WORDS_PER_MINUTE_FA = 180

# Regex to detect Persian characters (Arabic script range).
PERSIAN_CHAR_RE = re.compile(r"[\u0600-\u06FF]")


def calculate_reading_time(html: str) -> int:
    """
    Estimate reading time in whole minutes from an HTML string.

    - Strips HTML to plain text first (via clean_text).
    - Detects whether the text is mostly Persian or English.
    - Divides word count by the appropriate words-per-minute rate.
    - Rounds up, with a minimum of 1 minute.

    Returns 1 if the input is empty, so the UI never shows "0 min read".
    """
    text = clean_text(html)
    if not text:
        return 1

    word_count = len(text.split())
    if word_count == 0:
        return 1

    # Count Persian characters vs. total non-space characters.
    # If more than 30% are Persian, treat the text as Persian.
    persian_chars = len(PERSIAN_CHAR_RE.findall(text))
    total_chars = len(re.sub(r"\s", "", text)) or 1
    is_persian = (persian_chars / total_chars) > 0.3

    wpm = WORDS_PER_MINUTE_FA if is_persian else WORDS_PER_MINUTE_EN
    return max(1, math.ceil(word_count / wpm))
