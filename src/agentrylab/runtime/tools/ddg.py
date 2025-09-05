
from __future__ import annotations

import time
from typing import Any, Dict, List

try:
    # Preferred modern package
    from ddgs import DDGS  # type: ignore
except Exception:  # pragma: no cover - fallback for older envs
    from duckduckgo_search import DDGS  # type: ignore

from .base import Tool, ToolError, ToolResult


class DuckDuckGoSearchTool(Tool):
    """
    Simple wrapper around duckduckgo-search.
    """
    def run(
        self,
        query: str,
        max_results: int = 5,
        safesearch: str = "moderate",
        **kwargs: Any,
    ) -> ToolResult:
        if not query or not isinstance(query, str):
            raise ToolError("query must be a non-empty string")

        start = time.time()
        try:
            results: List[Dict[str, Any]] = []
            with DDGS() as ddgs:
                for r in ddgs.text(
                    query,
                    max_results=max_results,
                    safesearch=safesearch,
                ):
                    results.append(r)
        except Exception as e:
            raise ToolError(f"DuckDuckGo search failed: {e}") from e

        latency_ms = (time.time() - start) * 1000.0

        citations: List[str] = []
        data: List[Dict[str, Any]] = []
        for r in results:
            url = r.get("href") or r.get("url")
            title = r.get("title")
            body = r.get("body") or r.get("snippet")
            if url:
                citations.append(url)
            data.append({"title": title, "url": url, "snippet": body})

        return ToolResult(  # type: ignore[call-arg]
            ok=True,
            data=data,
            meta={
                "citations": citations,
                "provider": "ddg",
                "latency_ms": latency_ms,
            },
        )
