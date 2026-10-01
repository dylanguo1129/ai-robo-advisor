# Robo-Kit v2: plan update (28 Sep 2026)

> Archived: the plan as written on 28 Sep 2026. Superseded by README.md and docs/PRODUCT_SPEC.md (for example, the data refresh is a manual command, not a scheduled job).

Status: delivered 28 Sep 2026 (see docs/PRODUCT_SPEC.md). This replaces the "optimizer workstream only" scope of v1. Owner of the build: Dylan (with Claude Code). The team outline (Yasmin, 26 Sep) and the professor's brief still define what the course deliverable must show; v2 is the product that sits behind that deliverable.

## 1. What changes from v1

| | v1 (26 Sep) | v2 (this plan) |
| --- | --- | --- |
| Universe | 20 hand-picked Canadian ETFs | Every ETF you can buy in CAD on a Canadian exchange (TSX, Cboe Canada) and every US-listed ETF. The user picks Canada, US, or both (US funds converted to CAD). |
| Data | One yfinance pull, cached | A data bridge: official listing files, metadata, prices, fundamentals, macro, news and geopolitics, each with a source, an as-of date and an integrity check |
| Risk | Three fixed profiles (low / mid / high) | A short questionnaire that scores risk tolerance and risk capacity separately; the lower of the two sets a target volatility; the three brief profiles remain as named presets |
| Weights | Equilibrium mean-variance on the shortlist | Same core (it held up in the back-tests), plus core/satellite guardrails, optional bounded views, and scenario stress tests |
| Market context | None | ETF fundamentals, sector fundamentals, sentiment, macro and geopolitical indicators, recent news. Each is shown with its source. Only signals with evidence may move weights, and only inside a small, disclosed budget. |
| Interface | Dashboard (Allocation Lab) | Chat-first landing page, as the brief asks ("looks like Google's landing page or ChatGPT's opening page"). The Allocation Lab becomes the "show me how" view. |
| AI | None | Claude runs the conversation on the viewer's own Claude plan, and the viewer picks the model tier. Every number comes from deterministic code that the model calls as a tool. |
| Distribution | One private artifact | (1) the web artifact; (2) a repo that installs as a Python package, an MCP server and a Claude Code plugin, so any Claude user can connect it with their own account or API key and model |

## 2. Architecture (one engine, three surfaces)

```
 data bridge (Python, scheduled)          engine (Python, mirrored in JS)          surfaces
 ---------------------------------        --------------------------------         ------------------------------
 listings: Nasdaq Trader, TMX, Yahoo  ->  screen + classify                    ->  web artifact (chat-first, snapshot data,
 metadata: MER, AUM, inception, flags     risk profile -> target volatility         Claude via the viewer's own plan)
 prices: monthly total-return series      estimators (shrinkage, equilibrium)   ->  MCP server (live data, any MCP client)
 fundamentals: holdings look-through      optimizer (+ views, guardrails,       ->  Claude Code plugin (skill = AGENT.md)
 macro, geopolitics, news, sentiment        resampling) + back-test + projection
 integrity report + as-of stamps          explanations built from templates
```

Rules that hold everywhere:
1. Scripts produce every number. The model asks questions, calls tools, and explains what the tools returned. It may not state a figure that no tool returned.
2. Every tool result carries its source and as-of date, and the interface shows them.
3. Nothing is silently dropped: excluded funds say why (leveraged, too young, too small, and so on).

## 3. Work plan

| Phase | What | Output | Status |
| --- | --- | --- | --- |
| P0 | Research sweep: open-source prior art, papers, methods and signal evidence, data sources, regulation (Canada and US), onboarding and conversation design | `docs/research/*.md` (six lanes); summary in PRODUCT_SPEC.md section 2 | done |
| P1 | Data bridge: listings, metadata, prices, fundamentals, macro, geopolitics, news; integrity report | `robokit/data/`, `data/v2/`, `docs/DATA.md` | done: 7,957 listings, 7,792 price series |
| P2 | Engine v2: screening and classification, risk questionnaire, target-volatility calibration, guardrails, views, stress tests, goal projections | `robokit/` modules + tests | done |
| P3 | Back-tests at scale: Canadian and US building-block portfolios, with and without the tactical overlay, after costs | `output/v2/`, METHOD.md section 8, PRODUCT_SPEC.md section 10 | done (pre-registered, run once) |
| P4 | Agent: `AGENT.md` (how Robo-Kit talks to people), tool contracts, MCP server, Claude Code plugin, optional API-key CLI | `AGENT.md`, `robokit/mcp_server.py`, `robokit/agent.py`, `.claude-plugin/` | done |
| P5 | Web v2: chat-first landing, market switch, ETF cards, portfolio view, "show me how" lab, model-tier picker, works without AI through the guided questions | `web/` + published artifact (version 5) | done |
| P6 | Verification: unit and property tests, Python vs JS parity, persona walk-throughs, adversarial review of code and claims | 101 tests, JS parity, two independent code reviews (27 findings, all fixed), `docs/VERIFICATION.md` | done |
| P7 | Product spec and hand-off: full product plan, compliance notes, README, AI-use log | `docs/PRODUCT_SPEC.md` (compliance in section 14) | done |

## 4. How this maps to the course deliverable

| Brief task | Covered by |
| --- | --- |
| 1. ETF teaching note | The education layer (term pop-ups, "why this ETF") draws on it; market-size figures come from the data bridge. The written note is still the Research lead's section. |
| 2. ETF dataset and classification | P1: the full universe with the brief's classification fields (asset class, theme, industry, currency, volatility, leverage, strategy, cost). It is far larger than the outline's 100 to 200 funds, because it is built by script. |
| 3. Selection tool | P2 screening, exposed through chat and the lab |
| 4. Optimizer by risk aversion | P2 and P3 (v1 method, extended) |
| 5. AI conversational interface | P4 and P5 |

Course gates in the outline (schema frozen 7 Oct, end-to-end prototype 18 Oct, presentation 27 Oct) are met early if this lands. The team still owns the grant pitch, the report, the deck and the teaching note.

## 5. Honest limits

- Being ready to ship has a legal meaning. Giving personalised portfolio advice to the public requires registration: in Canada as a portfolio manager or through a registered firm, in the US as an investment advisor. v2 is built to launch as an impersonal educational tool with clear disclosures. P0 documents the path to a registered launch; a securities lawyer has to confirm it.
- Back-tests and forward projections are shown as ranges with their assumptions, never as promises.
- The web artifact cannot reach the internet from inside the page, so it carries a dated data snapshot. Live data comes through the MCP server or plugin, or through a refresh-and-republish job.
- News, sentiment and geopolitical signals have weak evidence as monthly return forecasts for broad ETFs. By default they are shown as context and risk flags. They move weights only if the back-test supports it.
