from agentrylab.runtime.nodes.agent import AgentNode
from agentrylab.runtime.nodes.moderator import ModeratorNode
from agentrylab.runtime.nodes.summarizer import SummarizerNode
from tests.fakes import FakeLLMProvider, FakeState
from tests.configs import AgentCfg, ModeratorCfg, SummarizerCfg

def test_agent_node_happy_path():
    cfg = AgentCfg(id="pro", role="agent")
    provider = FakeLLMProvider()
    state = FakeState()
    node = AgentNode(cfg=cfg, provider=provider, tools={})
    out = node(state)

    assert out.role == "agent"
    assert isinstance(out.content, str) and "Claim" in out.content
    assert out.metadata and out.metadata["citations"]

def test_moderator_node_json_and_actions():
    cfg = ModeratorCfg(id="moderator")
    provider = FakeLLMProvider()
    state = FakeState()
    node = ModeratorNode(cfg=cfg, provider=provider, tools={})
    out = node(state)

    assert out.role == "moderator"
    assert isinstance(out.content, dict)
    assert out.actions and out.actions["type"] == "CONTINUE"
    # required keys present
    for k in ("summary", "drift", "action", "rollback", "citations"):
        assert k in out.content

def test_summarizer_node_basic():
    cfg = SummarizerCfg(id="summarizer")
    provider = FakeLLMProvider()
    state = FakeState()
    node = SummarizerNode(cfg=cfg, provider=provider, tools={})
    out = node(state)

    assert out.role == "summarizer"
    assert isinstance(out.content, str)
    assert "summary" in out.content.lower()
