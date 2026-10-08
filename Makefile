# Robo-Kit developer tasks. On Windows without `make`, run the command lines under each target directly.
PY ?= python

.PHONY: help setup lock lint format test test-web test-ui check status build serve refresh backtest bundle data clean

help:  ## list the tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

setup:  ## install pinned dependencies, the package (editable) and the git hooks
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install -e . --no-deps
	pre-commit install

lock:  ## re-resolve the pinned dependency files from pyproject.toml (needs uv), then run `make check`
	uv pip compile pyproject.toml -o requirements.txt --python-version 3.10 --universal
	uv pip compile pyproject.toml --extra dev -o requirements-dev.txt --python-version 3.10 --universal

lint:  ## ruff lint + format check (what CI runs)
	ruff check .
	ruff format --check .

format:  ## auto-fix lint findings and format the Python code
	ruff check --fix .
	ruff format .

test:  ## Python tests
	$(PY) -m pytest -q

test-web:  ## browser-engine tests (node)
	node web/test_parse.mjs
	node web/test_assistant.mjs
	node web/test_engine.mjs
	node web/test_robokit.mjs
	node web/test_safety.mjs

test-ui:  ## browser regression tests (Playwright; needs a Chromium-based browser: python -m playwright install chromium)
	$(PY) -m pytest -m ui -q tests/ui

check: lint test test-web  ## lint, Python tests and browser-engine tests (CI also runs test-ui)

status:  ## which data the engine is using (local cache or the committed snapshot)
	$(PY) -m robokit status

build:  ## example: a level-3 Canadian mix for $25,000
	$(PY) -m robokit build --market CA --level 3 --amount 25000

serve:  ## serve web/ at http://127.0.0.1:8765 for local testing
	$(PY) scripts/serve_dev.py

refresh:  ## NETWORK: re-download every source into data/v2 (15-30 min; see data/README.md)
	$(PY) -m robokit refresh

backtest:  ## re-run the pre-registered v2 back-test into output/v2 (no network)
	$(PY) scripts/run_backtest_v2.py

bundle:  ## rebuild the web data snapshot (web/data/*.json) from the local cache (refuses without data/v2/)
	$(PY) -m robokit bundle

data: refresh bundle  ## refresh + bundle (then review the diff, run `make check`, republish the artifact)

clean:  ## remove caches and build files (never touches data/)
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
