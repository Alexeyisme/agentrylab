from agentrylab.runtime.nodes.agent import AgentNode
from agentrylab.runtime.nodes.moderator import ModeratorNode
from agentrylab.runtime.nodes.summarizer import SummarizerNode
from tests.fakes import FakeLLMProvider, FakeState
from tests.configs import AgentCfg, ModeratorCfg, SummarizerCfg

def test_engine_like_sequence():
    provider = FakeLLMProvider()
    state = FakeState()

    nodes = {
        "pro": AgentNode(cfg=AgentCfg(id="pro", role="agent"), provider=provider, tools={}),
        "con": AgentNode(cfg=AgentCfg(id="con", role="agent"), provider=provider, tools={}),
        "moderator": ModeratorNode(cfg=ModeratorCfg(id="moderator"), provider=provider, tools={}),
        "summarizer": SummarizerNode(cfg=SummarizerCfg(id="summarizer"), provider=provider, tools={}),
    }

    # emulate a simple round-robin tick
    for node_id in ["pro", "con", "moderator", "summarizer"]:
        out = nodes[node_id](state)
        state.append_message(agent_id=node_id, output=out)

    assert len(state.history) == 4
    assert any("Concise summary" in h["content"] for h in state.history)
