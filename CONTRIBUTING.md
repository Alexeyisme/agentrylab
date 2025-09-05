Contributing to Agentry Lab

Thanks for your interest in improving Agentry Lab! PRs are welcome — from quick bug fixes and docs edits to new features.

Quick Start
- Fork the repo and create a feature branch
- Python 3.11/3.12 recommended
- Create a venv and install dev deps:
  - `python -m venv .venv && . .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install -e '.[dev]'`
- Run lint and tests:
  - `ruff check .`
  - `pytest -q`

Project Philosophy
- Lightweight and readable — prefer clarity over cleverness
- Minimal ceremony — keep APIs small, docs helpful, examples runnable
- Solid tests — prioritize deterministic tests without network access

Before You Open a PR
- Add or update tests to cover your change
- Keep changes focused — smaller PRs are easier to review
- Update README / docs when changing public APIs or behavior

Commit Style
- Conventional and descriptive is great:
  - `fix: correct tool budget counter update`
  - `feat: add Lab.clean() API`
  - `docs: expand Python API examples`

Running Examples
- Some examples and presets may require API keys. Put secrets in a local `.env` (see README)

Release Flow (maintainers)
- We release via GitHub Actions on tag push (see `.github/workflows/release.yml`)
- Bump version in `pyproject.toml`, update `CHANGELOG.md`, then tag: `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`

Questions?
- Open a discussion or issue on GitHub

