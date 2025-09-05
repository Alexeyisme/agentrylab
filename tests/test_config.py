import os
from agentrylab.config.loader import load_config


def test_env_interpolation_defaults_and_overrides(monkeypatch):
    cfg_dict = {
        "id": "demo",
        "providers": [],
        "tools": [],
        "agents": [],
        # interpolate both with default and with env-set
        "persistence": {
            "transcript_path": "${TRANSCRIPT_PATH:outputs/transcripts}",
            "sqlite_path": "${SQLITE_PATH:outputs/checkpoints.db}",
        },
        "objective": "Value is ${TEST_VALUE:defaulted}",
    }

    # Without env vars, defaults apply
    cfg1 = load_config(cfg_dict)
    assert cfg1.objective.endswith("defaulted")

    # With env vars, overrides apply
    monkeypatch.setenv("TEST_VALUE", "overridden")
    monkeypatch.setenv("TRANSCRIPT_PATH", "outputs/my_transcripts")
    monkeypatch.setenv("SQLITE_PATH", "outputs/my_checkpoints.db")
    cfg2 = load_config(cfg_dict)
    assert cfg2.objective.endswith("overridden")
    # Ensure strings were interpolated, not left as ${...}
    assert "${" not in cfg2.objective
