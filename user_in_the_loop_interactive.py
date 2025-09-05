"""
Interactive chat loop with a scheduled user node.

Each line you type is appended as a user message, then one engine round runs
to consume that message on the scheduled user turn and produce agent output.

Usage:
  python user_in_the_loop_interactive.py \
    --preset src/agentrylab/presets/user_in_the_loop.yaml \
    --thread chat-1 --user-id user:alice

Type 'quit' or an empty line to exit.
"""

from __future__ import annotations

import argparse
from typing import Any

from agentrylab import init


def main() -> None:
    ap = argparse.ArgumentParser(description="Interactive user-in-the-loop demo")
    ap.add_argument("--preset", default="src/agentrylab/presets/user_in_the_loop.yaml")
    ap.add_argument("--thread", default="chat-1")
    ap.add_argument("--user-id", default="user:alice")
    args = ap.parse_args()

    lab = init(args.preset, experiment_id=args.thread, resume=True)

    print("Interactive chat. Type 'quit' to exit.\n")
    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line or line.lower() in {"quit", "exit"}:
            break

        # Append and run one round so the scheduled user node consumes it
        lab.post_user_message(line, user_id=args.user_id)
        for ev in lab.stream(rounds=1):
            # Print only fresh events from this round
            role = ev.get("role")
            aid = ev.get("agent_id")
            content: Any = ev.get("content")
            if isinstance(content, dict):
                content = str(content)
            print(f"[{role}] {aid}: {content}")

    print("Bye!")


if __name__ == "__main__":
    main()

