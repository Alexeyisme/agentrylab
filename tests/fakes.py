from __future__ import annotations
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import json

# ---- Fake provider ----
class FakeLLMProvider:
    """Deterministic LLM stub keyed off cfg.role_name / system_prompt hints."""
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        # Moderator: return strict JSON payload
        if "Respond ONLY with JSON" in system or "moderator" in system.lower():
            payload = {
                "summary": "Round check OK.",
                "drift": 0.1,
                "action": "CONTINUE",
                "rollback": 0,
                "citations": ["https://example.org/evidence"],
                "clear_summaries": False,
            }
            return {"content": json.dumps(payload)}
        # Summarizer: plain text
        if "Summarizer" in system or "summarizer" in system.lower():
            return {"content": "Concise summary of the session."}
        # Agent: plain text + metadata
        return {
            "content": "Claim with evidence attached.",
            "metadata": {"citations": ["https://example.com/source"]},
        }

# ---- Fake contracts ----
class FakeContracts:
    def validate_agent_output(self, out, cfg):
        # Require at least 1 URL in metadata.citations
        if not out.metadata or "citations" not in out.metadata or not out.metadata["citations"]:
            raise AssertionError("Agent output missing metadata.citations")

# ---- Fake state ----
@dataclass
class FakeState:
    thread_id: str = "test-thread"
    iter: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    stop_flag: bool = False
    contracts: FakeContracts = field(default_factory=FakeContracts)

    def compose_messages(self, cfg: Any, role_hint: str) -> List[Dict[str, str]]:
        sys = cfg.system_prompt or f"You are the {role_hint}."
        msgs = [{"role": "system", "content": sys}]
        # add short history window (simply append all user/assistant for the test)
        for m in self.history[-4:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        return msgs

    def extract_content_and_metadata(self, raw: Dict[str, Any], expect_json: bool) -> tuple[str, Optional[Dict[str, Any]]]:
        return raw.get("content", ""), raw.get("metadata")

    def parse_json_response(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return json.loads(raw["content"])

    def append_message(self, *, agent_id: str, output) -> None:
        # store a flattened view
        self.history.append({"role": agent_id, "content": str(output.content)})

    def rollback(self, n: int, *, clear_summaries: bool = False) -> None:
        if n > 0:
            del self.history[-n:]