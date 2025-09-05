from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from .base import Tool, ToolError, ToolResult


class WolframAlphaTool(Tool):
    """Wolfram|Alpha query tool.

    Configuration (constructor params or per-call kwargs):
      - app_id: Wolfram Alpha AppID (required). If not provided, tries $WOLFRAM_APP_ID.
      - units: "metric" | "imperial" (optional; defaults to "metric").

    Returns a ToolResult with:
      data: {
        "answer": str,                 # best-effort primary text answer
        "pods": [ {"title": str, "text": str}, ... ]
      }
      meta: {
        citations: [ wolfram URL ],
        provider: "wolfram",
        latency_ms: float,
      }
    """

    def _get_app_id(self, app_id: Optional[str]) -> str:
        app_id = app_id or self.params.get("app_id") or os.getenv("WOLFRAM_APP_ID")
        if not app_id or not isinstance(app_id, str):
            raise ToolError("WolframAlphaTool requires an 'app_id' (or env WOLFRAM_APP_ID)")
        return app_id

    def _make_client(self, app_id: str):
        try:
            import wolframalpha  # lazy import to avoid hard dep at import time
        except Exception as e:
            raise ToolError(f"wolframalpha package is not available: {e}") from e
        try:
            return wolframalpha.Client(app_id)
        except Exception as e:
            raise ToolError(f"failed to initialize wolframalpha client: {e}") from e

    def _extract_plaintext(self, result: Any) -> Dict[str, Any]:
        """Extract a best-effort primary answer and pods list from the client result.

        Supports both object-style access (attrs/pods) and dict-like results.
        """
        pods_out: List[Dict[str, str]] = []
        primary_text: Optional[str] = None

        # Try attribute-style (common in wolframalpha client)
        pods = getattr(result, "pods", None)
        if pods is None:
            pods = result.get("pods") if isinstance(result, dict) else None

        if pods and isinstance(pods, list):
            for pod in pods:
                # pod may be object or dict
                title = getattr(pod, "title", None) if not isinstance(pod, dict) else pod.get("title")
                subpods = getattr(pod, "subpods", None) if not isinstance(pod, dict) else pod.get("subpods")
                if subpods and isinstance(subpods, list):
                    # prefer first subpod with plaintext
                    for sp in subpods:
                        text = getattr(sp, "plaintext", None) if not isinstance(sp, dict) else sp.get("plaintext")
                        if isinstance(text, str) and text:
                            pods_out.append({"title": title or "", "text": text})
                            if primary_text is None:
                                primary_text = text
                            break
                else:
                    # sometimes pod has direct plaintext
                    text = getattr(pod, "plaintext", None) if not isinstance(pod, dict) else pod.get("plaintext")
                    if isinstance(text, str) and text:
                        pods_out.append({"title": title or "", "text": text})
                        if primary_text is None:
                            primary_text = text

        # Fallbacks: try a few common fields
        if primary_text is None:
            for key in ("answer", "output", "output_text", "text"):  # best-effort
                val = result.get(key) if isinstance(result, dict) else getattr(result, key, None)
                if isinstance(val, str) and val:
                    primary_text = val
                    break

        return {
            "answer": primary_text or "",
            "pods": pods_out,
        }

    def run(self, query: str, units: str = "metric", **kwargs: Any) -> ToolResult:
        if not query or not isinstance(query, str):
            raise ToolError("query must be a non-empty string")

        app_id = self._get_app_id(kwargs.get("app_id"))
        client = self._make_client(app_id)

        start = time.time()
        try:
            # The client typically accepts dict params via `params` kwarg or **kwargs.
            # We pass units if provided (some client versions accept it via "units").
            params: Dict[str, Any] = {}
            if units:
                params["units"] = units
            # Merge any extra kwargs as params while avoiding query text duplication
            for k, v in kwargs.items():
                if k not in ("app_id",):
                    params[k] = v

            # Some client versions use `client.query(input, params=params)`
            try:
                result = client.query(query, params=params)
            except TypeError:
                # Fallback for clients that accept **params directly
                result = client.query(query, **params)
        except Exception as e:
            raise ToolError(f"WolframAlpha query failed: {e}") from e

        latency_ms = (time.time() - start) * 1000.0

        data = self._extract_plaintext(result)
        citation_url = f"https://www.wolframalpha.com/input?i={urllib.parse.quote_plus(query)}"

        return ToolResult(  # type: ignore[call-arg]
            ok=True,
            data=data,
            meta={
                "citations": [citation_url],
                "provider": "wolfram",
                "latency_ms": latency_ms,
            },
        )
