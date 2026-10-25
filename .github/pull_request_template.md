## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## Checks

- [ ] `make check` passes locally (lint, Python tests, browser-engine tests)
- [ ] If the engine changed: mirrored in `web/robokit.js`, `python -m robokit bundle` re-run (needs the local data cache), parity test passes
- [ ] If `AGENT.md` changed: `RULES` in `web/guide.js` (the published page) and in `web/assistant.js` (the classic page) updated to match
- [ ] No raw data added (only `web/data/` snapshot changes, from a real `refresh` + `bundle`; `data/replication/` changes only with its `MANIFEST.json`)
- [ ] Docs updated (README / docs/) if behaviour or commands changed
- [ ] The web page needs republishing after merge: yes / no
