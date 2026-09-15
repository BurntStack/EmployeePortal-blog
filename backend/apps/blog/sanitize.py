"""Sanitization for employee-authored rich text content.

Posts go through admin approval before they're public, but the content
itself is still user-supplied HTML from a browser rich text editor —
sanitize it the same as any other untrusted input rather than trusting the
approval step alone.
"""

import bleach
from django.utils.html import strip_tags

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "a", "ul", "ol", "li",
    "h1", "h2", "h3", "blockquote", "code", "pre", "img", "hr",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def clean_post_html(value):
    """Strip everything except a known-safe rich-text tag/attribute set."""
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def visible_text_length(html):
    """Length of the actual readable text, ignoring markup."""
    return len(strip_tags(html).strip())
