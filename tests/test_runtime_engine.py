from agentrylab.runtime.engine import Engine
from agentrylab.runtime.state import State
from agentrylab.runtime.scheduler.round_robin import RoundRobinScheduler
from agentrylab.runtime.nodes.agent import AgentNode
from agentrylab.runtime.nodes.base import NodeOutput
from tests.fake_impls import TestProvider, EchoTool


class _StoreStub:
    def append_transcript(self, thread_id, entry):
        # Force engine to use in-memory fallback for easier assertions
        raise RuntimeError("no-op store in tests")

    def save_checkpoint(self, thread_id, state):
        pass


def _preset_cfg():
    # Minimal preset-like object for State contracts and Engine defaults
    from types import SimpleNamespace as NS
    message_contract = NS(require_metadata=True, min_citations=1)
    runtime = NS(message_contract=message_contract)
    return NS(id="test", runtime=runtime)


def test_single_tick_tool_call_and_metadata_contract():
    cfg = _preset_cfg()
    state = State(thread_id="t1", cfg=cfg)

    provider = TestProvider(model="test")
    tools = {"echo": EchoTool()}

    # Set up one agent node; engine will run it via round-robin with single entry
    node_cfg = type("NCfg", (), {"id": "pro", "role": "agent", "system_prompt": "You are the agent.", "temperature": 0})
    node = AgentNode(cfg=node_cfg, provider=provider, tools=tools)

    engine = Engine(
        preset_cfg=cfg,
        nodes={"pro": node},
        scheduler=RoundRobinScheduler(order=["pro"]),
        store=_StoreStub(),
        state=state,
    )

    # Execute one tick; provider asks for tool then finalizes
    engine.tick()

    # State iter increments
    assert state.iter == 1
    # In-memory history contains the transcript fallback with metadata
    assert len(state.history) >= 1
    last = state.history[-1]
    assert last["role"] == "agent"
    md = last.get("metadata")
    assert isinstance(md, dict)
    assert isinstance(md.get("citations"), list) and len(md["citations"]) >= 1
