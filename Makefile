.PHONY: test coverage lint

test:
	.venv/bin/pytest -q

coverage:
	.venv/bin/pytest --cov=src/agentrylab --cov-branch --cov-report=term-missing --cov-fail-under=$${COV_FAIL_UNDER:-40} -q

lint:
	.venv/bin/ruff check .

