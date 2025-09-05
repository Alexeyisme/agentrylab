from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer

from agentrylab.config.loader import load_config, _env_interp_deep
from agentrylab.config.validate import validate_preset_dict
import yaml
from agentrylab.lab import init_lab
from agentrylab.persistence.store import Store
from agentrylab.logging import setup_logging
from agentrylab.presets import path as packaged_preset_path
from importlib.metadata import version as pkg_version, PackageNotFoundError

app = typer.Typer(add_completion=False, help="Agentry Lab CLI — minimal ceremony, maximum signal.")


def _version_callback(value: bool) -> None:
    if not value:
        return
    try:
        v = pkg_version("agentrylab")
    except PackageNotFoundError:
        v = "unknown"
    typer.echo(f"agentrylab {v}")
    raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
):
    """Agentry Lab CLI — minimal ceremony, maximum signal."""
    # No-op: options handled via callbacks
    return


def _resolve_preset(preset_arg: str) -> Path:
    """Resolve a preset argument to a real filesystem path.

    Accepts either a direct path (relative/absolute) or the name of a packaged
    preset (e.g., "solo_chat.yaml" or "solo_chat").
    """
    # 1) Direct path in filesystem
    p = Path(preset_arg)
    if p.exists() and p.is_file():
        return p

    # 2) Packaged preset by name (with or without .yaml)
    candidates = []
    name = p.name  # keep only the final component if path-like was given
    candidates.append(name)
    if not name.endswith(".yaml"):
        candidates.append(name + ".yaml")
    for cand in candidates:
        try:
            pkg_path = Path(packaged_preset_path(cand))
            if pkg_path.exists():
                return pkg_path
        except Exception:
            # If importlib resources resolution fails, continue trying others
            pass

    # 3) Not found — raise a helpful error
    msg = (
        f"Could not resolve preset '{preset_arg}'. Provide a valid file path or a "
        f"packaged preset name like 'solo_chat.yaml'."
    )
    raise typer.BadParameter(msg)


def _load_env_file(env_path: Path | None = None) -> None:
    """Best-effort .env loader so ${VAR} in YAML resolves without external tooling.

    Loads KEY=VALUE pairs from .env in CWD (or provided path) into os.environ
    if the key is not already set.
    """
    try:
        path = env_path or Path(".env")
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        # Silent best-effort; env can still be provided by the shell
        pass


def _load_env() -> None:
    """Load environment variables from .env using python-dotenv if available.

    Falls back to a minimal loader if python-dotenv is not installed.
    """
    try:
        from dotenv import load_dotenv  # type: ignore

        # Do not override existing env; load from project .env if present
        load_dotenv(dotenv_path=Path(".env"), override=False)
    except Exception:
        _load_env_file()

def _print_last_messages(lab, limit: int = 10) -> None:
    # Prefer the persistent transcript via Store when available
    try:
        history = lab.get_history(limit=limit)
    except Exception:
        state = getattr(lab, "state", None)
        history = getattr(state, "history", [])[-limit:] if state is not None else []
    if not history:
        typer.echo("(no messages)")
        return
    typer.echo("\n=== Last messages ===")
    for ev in history:
        role = ev.get("role", "?")
        agent = ev.get("agent_id", "?")
        if "error" in ev and ev.get("error"):
            text = str(ev.get("error"))
        else:
            content = ev.get("content")
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False)
            text = str(content) if content is not None else ""
        if len(text) > 1200:
            text = text[:1200] + "…"
        typer.echo(f"[{role}] {agent}: {text}")


@app.command("run")
def run_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    max_iters: int = typer.Option(8, help="Maximum scheduler ticks to run"),
    thread_id: Optional[str] = typer.Option(None, help="Logical thread/run id (used for transcript & checkpoints)"),
    show_last: int = typer.Option(10, help="How many last messages to print after run"),
    stream: bool = typer.Option(True, help="Stream new events after each iteration"),
    json_out: bool = typer.Option(False, "--json/--no-json", help="Emit events in JSON instead of text"),
    resume: bool = typer.Option(True, "--resume/--no-resume", help="Resume state from checkpoint if available"),
) -> None:
    """Run a preset once (stream by default)."""
    # Load .env before interpolation/validation so ${VARS} resolve
    _load_env()
    # Resolve preset
    preset_path = _resolve_preset(preset)

    # Lint: read raw YAML and run advisory checks
    try:
        raw = yaml.safe_load(preset_path.read_text(encoding="utf-8")) or {}
        raw = _env_interp_deep(raw)
        warnings = validate_preset_dict(raw) if isinstance(raw, dict) else []
        for msg in warnings:
            typer.echo(f"[lint] {msg}")
    except Exception:
        pass

    cfg = load_config(str(preset_path))

    # Initialize logging/tracing per runtime config
    try:
        rt = getattr(cfg, "runtime", None)
        logs_cfg = getattr(rt, "logs", None) if rt is not None else None
        trace_cfg = getattr(rt, "trace", None) if rt is not None else None
        setup_logging(logs_cfg, trace_cfg)
    except Exception:
        # Do not block run on logging issues
        pass

    lab = init_lab(cfg, thread_id=thread_id, resume=resume)

    if not stream:
        # Kick off the run in one go
        lab.start(max_iters=max_iters)
        _print_last_messages(lab, limit=show_last)
        return

    # Streaming loop: tick-by-tick, printing new events
    printed = 0
    for _ in range(max_iters):
        lab.engine.tick()
        # Read full transcript and print only new entries
        try:
            events = lab.store.read_transcript(lab.state.thread_id)
        except Exception:
            # Fallback to in-memory history (won't include errors)
            events = getattr(lab.state, "history", [])
        new = events[printed:]
        if new:
            if not json_out:
                typer.echo("\n=== New events ===")
            for ev in new:
                if json_out:
                    typer.echo(json.dumps(ev, ensure_ascii=False))
                else:
                    role = ev.get("role", "?")
                    agent = ev.get("agent_id", "?")
                    if "error" in ev and ev.get("error"):
                        text = str(ev.get("error"))
                    else:
                        content = ev.get("content")
                        if isinstance(content, dict):
                            content = json.dumps(content, ensure_ascii=False)
                        text = str(content) if content is not None else ""
                    if len(text) > 1200:
                        text = text[:1200] + "…"
                    typer.echo(f"[{role}] {agent}: {text}")
            printed += len(new)

    # Final tail for convenience
    _print_last_messages(lab, limit=show_last)


@app.command("status")
def status_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    thread_id: str = typer.Argument(..., help="Thread id to inspect"),
) -> None:
    """Print iter and history length for a thread from the checkpoint DB."""
    _load_env()
    preset_path = _resolve_preset(preset)
    cfg = load_config(str(preset_path))
    store = Store(cfg)
    snap = store.load_checkpoint(thread_id)
    if not snap:
        typer.echo(f"No checkpoint for thread '{thread_id}'.")
        return
    if isinstance(snap, dict) and "_pickled" not in snap:
        it = snap.get("iter")
        hist = snap.get("history")
        hlen = len(hist) if isinstance(hist, list) else 0
        typer.echo(f"thread={thread_id} iter={it} history_len={hlen}")
    else:
        typer.echo(f"thread={thread_id} checkpoint stored as opaque pickle; cannot introspect fields.")


@app.command("validate")
def validate_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    strict: bool = typer.Option(False, "--strict/--no-strict", help="Exit non-zero when issues are found"),
) -> None:
    """Lint a preset file and print advisory warnings (be nice to future you)."""
    _load_env()
    try:
        preset_path = _resolve_preset(preset)
        raw = yaml.safe_load(preset_path.read_text(encoding="utf-8")) or {}
        raw = _env_interp_deep(raw)
    except Exception as e:
        typer.echo(f"Failed to read YAML: {e}")
        raise typer.Exit(code=1)

    if not isinstance(raw, dict):
        typer.echo("Preset must be a YAML mapping at the root.")
        raise typer.Exit(code=1)

    warnings = validate_preset_dict(raw)
    if not warnings:
        typer.echo("No issues found.")
        return
    typer.echo(f"Found {len(warnings)} issue(s):")
    for msg in warnings:
        typer.echo(f" - {msg}")
    if strict:
        raise typer.Exit(code=1)


@app.command("extend")
def extend_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    thread_id: str = typer.Argument(..., help="Thread id to extend"),
    add_iters: int = typer.Option(1, help="Additional iterations to run"),
) -> None:
    """Extend an existing thread by N iterations (resumes state)."""
    _load_env()
    preset_path = _resolve_preset(preset)
    cfg = load_config(str(preset_path))
    lab = init_lab(cfg, thread_id=thread_id, resume=True)
    lab.extend(add_iters=add_iters)
    typer.echo(f"Extended thread {thread_id} by {add_iters} iterations.")


@app.command("reset")
def reset_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    thread_id: str = typer.Argument(..., help="Thread id to reset"),
    delete_transcript: bool = typer.Option(False, help="Also delete transcript JSONL"),
) -> None:
    """Delete the checkpoint (and optionally transcript) for a thread (fresh start)."""
    _load_env()
    preset_path = _resolve_preset(preset)
    cfg = load_config(str(preset_path))
    store = Store(cfg)
    store.delete_checkpoint(thread_id)
    if delete_transcript:
        store.delete_transcript(thread_id)
    typer.echo(f"Reset thread {thread_id} (deleted checkpoint{' and transcript' if delete_transcript else ''}).")


@app.command("ls")
def list_threads_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
) -> None:
    """List known threads from the checkpoint store (what stories we’ve saved)."""
    _load_env()
    preset_path = _resolve_preset(preset)
    cfg = load_config(str(preset_path))
    store = Store(cfg)
    rows = store.list_threads()
    if not rows:
        typer.echo("(no threads)")
        return
    for tid, ts in rows:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        typer.echo(f"{tid}\t{dt}")


@app.command("say")
def say_cmd(
    preset: str = typer.Argument(..., help="Path to YAML preset or packaged preset name"),
    thread_id: str = typer.Argument(..., help="Thread id to post into"),
    message: str = typer.Argument(..., help="User message to append"),
    user_id: str = typer.Option("user", help="Logical user id (default: 'user')"),
) -> None:
    """Append a user message into a thread's history (and transcript)."""
    _load_env()
    preset_path = _resolve_preset(preset)
    cfg = load_config(str(preset_path))
    lab = init_lab(cfg, thread_id=thread_id, resume=True)
    lab.post_user_message(message, user_id=user_id)
    typer.echo(f"Appended user message to thread '{thread_id}' as {user_id}.")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
