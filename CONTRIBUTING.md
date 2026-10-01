# Contributing

## Set up (once)

```bash
git clone https://github.com/dylanguo1129/ai-robo-advisor.git
cd ai-robo-advisor
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
make setup        # = pip install -r requirements-dev.txt; pip install -e . --no-deps; pre-commit install
make check        # lint + Python tests + browser-engine tests: must pass before you push
```

Python 3.10+ and Node 18+ (Node is only needed for the browser-engine tests). Without `make` (Windows), run the
commands listed in the Makefile by hand.

## Workflow

1. Branch from `main`: `feature/<short-name>`, `fix/<short-name>` or `docs/<short-name>`.
2. Keep each change small and focused; commit messages in the imperative ("Add US bond proxy").
3. Run `make check`. The pre-commit hooks run ruff (lint + format) and block raw vendor data from being committed.
4. Push and open a pull request into `main`. CI (`.github/workflows/ci.yml`) must be green; ask a teammate to review.
5. Squash-merge. Don't push directly to `main` for anything beyond a typo.

## Rules of the codebase

- **Code computes every number.** The language model only asks, calls tools and explains. Any new figure a user can
  see must come from `robokit/` (Python) and its port `web/robokit.js`, never from a prompt.
- **Python is the reference; the browser engine must match it.** If you change `robokit/engine.py`, `profile.py`,
  `shelf.py`, `stress.py` or `projection.py`, mirror the change in `web/robokit.js`, then regenerate the reference cases and `web/test_profiles.json` with
  `python -m robokit bundle` and make `node web/test_robokit.mjs` pass. `bundle` needs the local data cache
  (`python -m robokit refresh` first, about 15-30 min); it refuses to run on a bare clone. If you cannot refresh,
  ask the owner to regenerate.
- **The page's assistant rules are a copy.** `AGENT.md` is read by the MCP server, the plugin and the terminal agent;
  the web page sends a condensed copy (`RULES` in `web/assistant.js`). Change both together.
- **Data never goes in git** except the dated snapshot in `web/data/`. See `data/README.md`.
- **Pinned environment.** `requirements.txt` / `requirements-dev.txt` are generated from `pyproject.toml` with
  `make lock` (uv). Change a dependency in `pyproject.toml`, re-lock, and run `make check`.
- **Versioning.** Semantic versioning in `robokit/__init__.py` (`__version__`); `pyproject.toml` reads it. Bump
  `.claude-plugin/plugin.json` and `marketplace.json` to the same version.
- **Style.** English only. Plain words, short sentences. Spell it "advisor" (keep "adviser" only inside quotations,
  legal names such as the Investment Advisers Act, and URLs such as adviserinfo.sec.gov).
- **Tests.** Every bug fix gets a regression test. Tests that need the local data cache (`data/v2/`, marked
  `needs_data`) or the v1 price file skip on a fresh clone and in CI. A bug in the web page gets a browser test in
  `tests/ui` (`make test-ui`, or `python -m pytest -m ui tests/ui`; once, `python -m playwright install chromium`
  unless Edge or Chrome is installed). These tests are opt-in locally and run in their own CI job.
- **The page's no-AI router is a table of rules** (`routeText` in `web/parse.js`). Add every phrasing you fix to
  `web/test_parse.mjs`, so a later rule cannot quietly undo it.

## Updating the published web page

The page is a claude.ai Artifact published from `web/` (the files `index.html`, `app.js`, `assistant.js`,
`strings.js`, `robokit.js`, `engine.js`, `parse.js`, `validate.js`, `icons.js`, `worker2.js` and `data/*.json`).
Only the owner of the artifact can republish it. After a merged change to `web/`: pull `main`, run
`make check`, then ask the owner (or Claude Code on the owner's machine) to republish to the same URL.
To try the page locally, run `make serve` (or `python scripts/serve_dev.py`) and open http://127.0.0.1:8765/index.html
(everything but the AI assistant). `python scripts/make_mock_page.py` writes `web/mock.html`, a test harness for the
chat path: it does not answer by itself; you play Claude from the devtools console with `window.__mock.view()`,
`window.__mock.call(name, args)` and `window.__mock.finish(text)`.
