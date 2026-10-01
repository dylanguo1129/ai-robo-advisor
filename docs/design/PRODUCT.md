# Product

<!-- impeccable:product-schema 1 -->

## Platform

web (a Claude artifact), plus a Python package, MCP server and Claude Code plugin sharing one engine.

## Users

Primary: anyone who invests or is curious about ETFs, in Canada or the US, including first-time investors (almost half of Canadians have literacy challenges, so plain language is a requirement). Secondary: the MMAI 823 team and the grant panel (27 Oct 2026), who must understand the mechanism in minutes. Dylan (group head) owns the build. The audience is everyone who invests or is interested in investing in ETFs or stocks.

## Product Purpose

Robo-Kit v2 is a do-it-yourself ETF portfolio lab. A person searches every ETF they can buy in Canadian dollars in Canada (TSX, Cboe Canada) or every US-listed ETF, takes a short fixed self-check, chooses a risk level, fills each asset class with funds they pick, and sees what a transparent engine does with them: weights with uncertainty, dollar ranges, fees in dollars, stress tests and projections. Claude explains and routes on the viewer's own Claude plan; code produces every number. Success: a first-time investor can build and explain a mix in under ten minutes, and nothing on screen is a number no tool produced.

## Positioning

Robo-advisors hide the method; Robo-Kit shows it. Expected returns are equilibrium returns implied by a written policy prior (never historical averages), covariance is shrunk, weights are averaged over resampled histories, and every young fund's extended history, every guardrail and every assumption is listed. The assistant is Claude, but the numbers come from code (the same split Vanguard announced for its advice chat in September 2026).

## Operating Context

Launch path A (docs/research/regulation.md): an impersonal, free learning simulator. The person chooses the level and the funds; the page says "the mix at level N with the funds you chose", never "your portfolio" or "we recommend". No accounts, orders, fees, ads or affiliate links. AI disclosure at the start of each session (Anthropic Usage Policy). Prices and listings come from Yahoo, TMX and Nasdaq under personal-use terms, so the artifact stays private or team-shared until licensed data replaces them.

## Capabilities and Constraints

- Universe: 2,187 Canadian listings (CAD) and 5,770 US listings, every one classified with reasons; 2,610 eligible for the optimizer after written rules (no leverage, no single-stock, 36+ months, size and liquidity floors).
- Self-check: fixed items A0-D2, capacity and tolerance scored separately, lower wins, gates for short horizon, no emergency fund and heavy debt.
- Engine: reference shelf, spliced histories, equilibrium mean-variance with guardrails, resampling, optional bounded views, stress tests, projections on FP Canada 2026 planning assumptions, suitability-style checks, plain-language explanations. The JavaScript port matches the Python engine (web/test_robokit.mjs).
- Chat: `sample` capability (viewer pays, model tier quick / default / complex), page functions as tools, a number-provenance validator on every reply. The page works fully without AI.
- Not built: accounts, trading, rebalancing service, tax advice, single stocks.

## Brand Commitments

Name: Robo-Kit. Voice: plain, calm, second person, no hype, no fear. Never "AI financial advisor". Visual direction: Wealthsimple-style, minimal but information-complete. Craft bar: Wealthsimple managed-investing screens, Betterment portfolio pages. English.

## Evidence on Hand

- Data snapshot through 31 Aug 2026 (`data/v2/`, `web/data/`); research with verbatim sources (`docs/research/`); pre-registered back-test (`docs/RESEARCH_LOG.md` section 6, `output/v2/`).
- No customers and no performance claims beyond the labelled hypothetical back-test.

## Product Principles

1. Code decides the numbers; the person decides the choices; the AI explains.
2. Show the mechanism: every figure has a source, a date and a "why".
3. Ranges, not forecasts: dollars first, bad years shown as plainly as good ones.
4. Preferences are constraints, never return forecasts; news is context, never a signal.
5. Works without AI, and never behaves differently across model tiers.
