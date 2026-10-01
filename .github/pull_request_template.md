## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## Checks

- [ ] `make check` passes locally (lint, Python tests, browser-engine tests)
- [ ] If the engine changed: mirrored in `web/robokit.js`, `python -m robokit bundle` re-run (needs the local data cache), parity test passes
- [ ] If `AGENT.md` changed: `RULES` in `web/assistant.js` updated to match
- [ ] No raw data added (only `web/data/` snapshot changes, and only from a real `refresh` + `bundle`)
- [ ] Docs updated (README / docs/) if behaviour or commands changed
- [ ] The web page needs republishing after merge: yes / no
