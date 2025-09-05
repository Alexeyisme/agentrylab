"""Preset validation helpers.

Lightweight checks beyond Pydantic shape validation, to surface:
- Unknown roles inside the `agents` list
- Duplicate moderator/summarizer specified both top-level and inside agents
- Presence of top-level `message_contract` (ignored by runtime)

These checks are advisory and do not mutate the config.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def validate_preset_dict(doc: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []

    def w(msg: str) -> None:
        warnings.append(msg)

    # 1) Unknown roles
    roles_ok = {"agent", "advisor", "moderator", "summarizer"}
    for item in list(doc.get("agents") or []):
        if isinstance(item, dict):
            r = item.get("role")
            if r not in roles_ok:
                w(f"Unknown or missing role in agents list: {item}")

    # 2) Duplicated moderator/summarizer
    has_top_mod = bool(doc.get("moderator"))
    has_top_sum = bool(doc.get("summarizer"))
    for item in list(doc.get("agents") or []):
        if not isinstance(item, dict):
            continue
        r = item.get("role")
        if r == "moderator" and has_top_mod:
            w("Duplicate moderator found both top-level and inside agents; top-level wins")
        if r == "summarizer" and has_top_sum:
            w("Duplicate summarizer found both top-level and inside agents; top-level wins")

    # 3) Top-level message_contract (ignored by runtime)
    if "message_contract" in doc and not (doc.get("runtime") and doc["runtime"].get("message_contract")):
        w("Top-level message_contract is ignored; use runtime.message_contract instead")

    return warnings
