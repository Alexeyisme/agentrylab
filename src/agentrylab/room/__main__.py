"""``python -m agentrylab.room`` starts the web server."""

from __future__ import annotations

import argparse

from .server import serve


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentrylab.room", description="Run the AgentryLab Room web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev)")
    args = parser.parse_args()
    serve(args.host, args.port, reload=args.reload)


if __name__ == "__main__":
    main()
