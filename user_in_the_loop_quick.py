"""
Quick demo: scheduled user-in-the-loop.

Usage:
  python user_in_the_loop_quick.py --message "Hello from Alice!" --rounds 1 \
    --preset src/agentrylab/presets/user_in_the_loop.yaml --thread demo

Requires: a model provider configured in the preset (e.g., Ollama llama3).
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from agentrylab import init


def main() -> None:
    ap = argparse.ArgumentParser(description="User-in-the-loop quick demo")
    ap.add_argument("--preset", default="src/agentrylab/presets/user_in_the_loop.yaml")
    ap.add_argument("--thread", default="demo")
    ap.add_argument("--message", default="Hello from Alice!")
    ap.add_argument("--user-id", default="user:alice")
    ap.add_argument("--rounds", type=int, default=1)
    args = ap.parse_args()

    lab = init(args.preset, experiment_id=args.thread, resume=True)

    # Append a user message for the scheduled user node to consume
    lab.post_user_message(args.message, user_id=args.user_id)

    # Run N rounds (user turn, then assistant in the preset)
    lab.run(rounds=args.rounds)

    # Print the last few transcript events
    for ev in lab.history(limit=10):
        role = ev.get("role")
        aid = ev.get("agent_id")
        content: Any = ev.get("content")
        if isinstance(content, dict):
            content = str(content)
        print(f"[{role}] {aid}: {content}")


if __name__ == "__main__":
    main()

