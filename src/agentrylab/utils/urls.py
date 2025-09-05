from __future__ import annotations

import re
from typing import List

URL_RE = re.compile(r"https?://[^\s\]\)\}\>\"]+", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    if not isinstance(text, str) or not text:
        return []
    return URL_RE.findall(text)


def merge_citations(existing: List[str], *lists: List[str]) -> List[str]:
    merged: List[str] = []
    seen = set()
    for url in list(existing or []):
        if isinstance(url, str) and url not in seen:
            seen.add(url)
            merged.append(url)
    for lst in lists:
        for url in lst or []:
            if isinstance(url, str) and url not in seen:
                seen.add(url)
                merged.append(url)
    return merged

