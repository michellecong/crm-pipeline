import re
from typing import Optional


# Regex patterns for markdown/HTML link cleanup
MD_IMAGE = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
MD_LINK = re.compile(r'\[([^\]]+)\]\((?:https?://|mailto:)[^)]+\)')
MD_REF_LINK = re.compile(r'\[([^\]]+)\]\[[^\]]+\]')
MD_REF_DEF = re.compile(r'^\s*\[[^\]]+\]:\s+\S+.*$', re.MULTILINE)
AUTO_LINK = re.compile(r'<https?://[^>]+>')
BARE_URL = re.compile(r'(?i)\bhttps?://[^\s)>\]]+')

A_TAG = re.compile(r'<a\b[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)


def strip_links(text: Optional[str], remove_bare_urls: bool = True) -> str:
    """
    Remove links from markdown-like text while keeping readable anchor text.
    - Converts "[text](url)" -> "text"
    - Converts reference links "[text][id]" -> "text" and drops definitions
    - Drops autolinks "<https://...>" and, optionally, bare URLs
    """
    if not text:
        return ""
    s = MD_IMAGE.sub(r'\1', text)
    s = MD_LINK.sub(r'\1', s)
    s = MD_REF_LINK.sub(r'\1', s)
    s = MD_REF_DEF.sub('', s)
    s = AUTO_LINK.sub('', s)
    if remove_bare_urls:
        s = BARE_URL.sub('', s)
    # Tidy leftovers like empty parentheses and extra spaces/newlines
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def strip_html_links(html: Optional[str]) -> str:
    """
    Remove <a> links from HTML while keeping inner text.
    """
    if not html:
        return ""
    return A_TAG.sub(r'\1', html)


