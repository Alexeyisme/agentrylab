.PHONY: test coverage lint web web-dev web-bundle serve

test:
	.venv/bin/pytest -q

coverage:
	.venv/bin/pytest --cov=src/agentrylab --cov-branch --cov-report=term-missing --cov-fail-under=$${COV_FAIL_UNDER:-40} -q

lint:
	.venv/bin/ruff check .

# ---- Room web UI ----
web:            ## build the frontend into web/dist
	cd web && npm install && npm run build

web-dev:        ## frontend dev server with hot reload (expects API on :8000)
	cd web && npm run dev

web-bundle: web ## copy the build into the Python package so wheels ship the UI
	rm -rf src/agentrylab/room/static
	cp -r web/dist src/agentrylab/room/static

serve:          ## run the Room server
	.venv/bin/agentrylab serve
