from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AgentCfg:
    id: str
    role: str
    provider: str = "fake"
    tools: List[str] = None
    system_prompt: Optional[str] = "You are the agent."

@dataclass
class ModeratorCfg:
    id: str
    role: str = "moderator"
    provider: str = "fake"
    tools: List[str] = None
    system_prompt: str = (
        'You are the Moderator. Respond ONLY with JSON using keys: '
        '{"summary","drift","action","rollback","citations","clear_summaries"}.'
    )

@dataclass
class SummarizerCfg:
    id: str
    role: str = "summarizer"
    provider: str = "fake"
    tools: List[str] = None
    system_prompt: str = "You are the Summarizer. Write a concise summary."