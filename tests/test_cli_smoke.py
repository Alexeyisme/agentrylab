from __future__ import annotations

import yaml
from typer.testing import CliRunner

from agentrylab.cli.app import app


def _preset_dict():
    return {
        "id": "cli-smoke",
        "providers": [{"id": "p1", "impl": "tests.fake_impls.TestProvider", "model": "test"}],
        "agents": [{"id": "pro", "role": "agent", "provider": "p1", "system_prompt": "You are the agent."}],
        "runtime": {
            "scheduler": {
                "impl": "agentrylab.runtime.scheduler.round_robin.RoundRobinScheduler",
                "params": {"order": ["pro"]},
            }
        },
    }


def test_cli_run_status_ls_reset(tmp_path):
    runner = CliRunner()
    preset_path = tmp_path / "preset.yaml"
    preset_path.write_text(yaml.safe_dump(_preset_dict()))

    # run
    r = runner.invoke(app, ["run", str(preset_path), "--max-iters", "1", "--thread-id", "cli-demo", "--no-stream"])
    assert r.exit_code == 0

    # status
    r2 = runner.invoke(app, ["status", str(preset_path), "cli-demo"])
    assert r2.exit_code == 0

    # ls
    r3 = runner.invoke(app, ["ls", str(preset_path)])
    assert r3.exit_code == 0
    assert "cli-demo" in r3.stdout

    # reset (delete checkpoint and transcript)
    r4 = runner.invoke(app, ["reset", str(preset_path), "cli-demo", "--delete-transcript"])
    assert r4.exit_code == 0

    # validate
    r5 = runner.invoke(app, ["validate", str(preset_path)])
    assert r5.exit_code == 0

    # extend: run another iteration on a new thread
    r6 = runner.invoke(app, ["run", str(preset_path), "--max-iters", "1", "--thread-id", "cli-ext", "--no-stream"])
    assert r6.exit_code == 0
    r7 = runner.invoke(app, ["extend", str(preset_path), "cli-ext", "--add-iters", "1"])
    assert r7.exit_code == 0


def test_cli_error_paths(tmp_path):
    runner = CliRunner()
    bad_path = tmp_path / "bad.yaml"
    # invalid root type triggers non-zero with --strict
    bad_path.write_text(yaml.safe_dump([1, 2, 3]))
    r = runner.invoke(app, ["validate", str(bad_path), "--strict"])
    assert r.exit_code != 0

    # status on missing thread prints message
    preset_path = tmp_path / "preset.yaml"
    preset_path.write_text(yaml.safe_dump(_preset_dict()))
    r2 = runner.invoke(app, ["status", str(preset_path), "missing-thread"])
    assert r2.exit_code == 0
    assert "No checkpoint" in r2.stdout
