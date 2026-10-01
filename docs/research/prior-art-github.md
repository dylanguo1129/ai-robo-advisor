STATUS: COMPLETE

# Prior art on GitHub and in open source (Robo-Kit v2)

*Lane: prior art. Retrieved 2026-09-28. This extends `docs/RESEARCH_NOTES.md`, which covers the methods literature and course materials but not open-source products. The rules match those notes: a quote appears only if the page or file was actually opened, and every repository number (stars, licence, last push) is the exact value `gh api repos/OWNER/REPO` returned on 2026-09-28. READMEs were read in full through `gh api repos/OWNER/REPO/readme`. Search is the GitHub search API. Star counts change daily and measure popularity, not quality.*

## 0. How the search was run

* `gh search repos` / `search/repositories`, sorted by stars, for these queries: robo-advisor, robo advisor etf, roboadvisor, robo-advisor llm, ai robo advisor, canadian etf, tsx etf, canada etf portfolio, couch potato portfolio, etf screener, etf holdings scraper, etf database, black-litterman, portfolio optimization python, llm portfolio management, llm financial advisor, financial agent llm (created after 2025-01-01), investment agent (created after 2025-01-01), portfolio agent llm, etf llm, etf chatbot, etf recommendation llm, robo-advisor claude, robo advisor mcp, black-litterman llm views, llm asset allocation, claude finance, claude portfolio, yfinance mcp, finance mcp server, sec edgar mcp, fred mcp, stock market mcp, financial data mcp, etf mcp, robo advisor canada, wealthsimple, questrade portfolio, tmx etf, etf portfolio optimizer, asset allocation etf. Also the topics `robo-advisor`, `portfolio-optimization`, `black-litterman`, `financial-agents` and `mcp-server finance`.
* Awesome-lists: the Finance & Fintech section of `punkpeye/awesome-mcp-servers` (432 entries, parsed with a script). `wilsonfreitas/awesome-quant` and `georgezouq/awesome-ai-in-finance` were located but not parsed (see Gaps).
* Papers with Code no longer exists. `paperswithcode.com/search?q=robo-advisor` returned HTTP 302 to `https://huggingface.co/papers/trending`. The Hugging Face papers search for "robo-advisor" turned up nothing relevant to this product. Two arXiv papers with code were opened directly (section F).
* GitHub code search for `window.claude.complete` (the in-artifact Claude call) returned 20 hits: design prompts, guides and one trading CLAUDE.md. None was a portfolio or ETF advisor.
* No external model CLI (agy, cursor-agent) was used. The raw metadata JSON and READMEs are in the session scratchpad, `priorart/`.

## 1. Bottom line

1. **I found no open-source Canadian + US ETF robo-advisor with an LLM chat on top.** The closest projects each cover one piece:
   * a TSX-only ETF *ranker* with a quiz: 1,680+ TSX ETFs, no optimizer, no LLM, placeholder fees, no licence, 0 stars;
   * two chat-first ETF advisors that keep the model away from the maths, each with a **25-ETF US universe**;
   * general LLM analyst frameworks that pick single stocks or trades, not risk-profiled ETF portfolios.

   Confidence is medium: this is absence of evidence from GitHub search and one awesome-list.
2. **Robo-Kit's core principle already exists in small repos** ("the LLM talks, deterministic code produces the numbers"). Three give concrete mechanisms worth re-implementing:
   * a *number fence* that refuses model-typed numerals;
   * a *feasibility gate* that returns `constraint_infeasible` instead of breaking a risk cap;
   * *schema-validated, bounded LLM views* fed into Black-Litterman, tested against shuffled and static controls.

   None of the three has more than 2 stars. Two have no licence and one is AGPL, so borrow the ideas and write the code fresh.
3. **The big LLM finance repos do something different from Robo-Kit:** TradingAgents (109,046 stars), ai-hedge-fund (63,782), FinRobot, dexter and ValueCell are research or trading agents that issue buy/sell calls on single names. Every one says it is not advice. The independent evidence (FINSABER, KDD 2026) says reported LLM trading gains shrink under longer, broader tests. Robo-Kit should not copy their design, where the LLM makes the decision.
4. **The portfolio maths is a solved open-source problem under permissive licences:**
   * PyPortfolioOpt (MIT) has Black-Litterman and Ledoit-Wolf constant-correlation;
   * Riskfolio-Lib (BSD-3) has three Black-Litterman variants;
   * skfolio (BSD-3) has Black-Litterman, entropy pooling and a WalkForward/CPCV splitter.

   Robo-Kit's advantage is not the optimizer. It is the Canada+US universe, profile-to-weights calibration, honest back-testing and the chat delivery. Use these libraries as test oracles, the way QIS was handled in `RESEARCH_NOTES.md`.
5. **Data is the weakest link for a shippable product.**
   * yfinance says the Yahoo API is "intended for personal use only".
   * A deployed chat ETF advisor reports that Yahoo blocks datacenter IPs.
   * The TSX ranker reports that Yahoo publishes no MER for TSX funds.
   * FinanceDatabase (MIT) lists 978 TOR + 89 NEO ETF rows. That is well short of the 2,038-entry Canadian universe in a separate, unlicensed holdings dataset.

   The data bridge needs official exchange and issuer lists as the source of truth. Open-source databases can only enrich.

## 2. Has anyone already built this? Closest analogues and how Robo-Kit differs

| Project (exact API values) | What it is | Overlap with Robo-Kit | Gap vs Robo-Kit |
| --- | --- | --- | --- |
| [ariadruker1/etf_recommendation_tool](https://github.com/ariadruker1/etf_recommendation_tool): 0 stars, licence None, pushed 2026-07-15T02:28:17Z | "TSX ETF Ranker". Five-question quiz feeds percentile ranking on yield, fees, performance and risk. FastAPI + DuckDB + yfinance. | Canadian universe, questionnaire-driven profile, plain-English metrics. | Ranks rather than builds a portfolio (no covariance, no optimizer). No US market, no LLM. Fees are a placeholder. No licence, so the code cannot be reused. |
| [Luis-Rong/investment-bot-neu](https://github.com/Luis-Rong/investment-bot-neu): 0 stars, MIT, pushed 2026-07-17T16:01:48Z | Chat-based ETF robo-advisor: LangGraph agent, deterministic `logic/` package, RAG over generated fund profiles, MCP server, bring-your-own key (Google, Anthropic, OpenAI). | Closest architecture: chat-first, deterministic maths, MCP tools, BYOK, eval harness. | `data/universe.json` holds **25** mostly US-listed ETFs (IVV, URTH, VEA, …). No Canadian market, no Black-Litterman prior, no resampling or walk-forward, Streamlit/Gradio rather than a Claude artifact. |
| [Sail-high/FinPilot](https://github.com/Sail-high/FinPilot): 2 stars, licence None, pushed 2026-08-06T04:36:59Z | Natural-language to `InvestorProfile` (Qwen), then Ledoit-Wolf + risk parity, hard constraints, capped EMA250 tilt, locked walk-forward test. | Same philosophy (LLM parses, maths allocates), feasibility gate, frozen out-of-sample test. | **25** US ETFs. Risk parity core, not an equilibrium prior. No licence. |
| [Michelia-L/AI-WealthPilot](https://github.com/Michelia-L/AI-WealthPilot): 2 stars, MIT, pushed 2026-09-28T09:32:54Z | Advisor workstation: CME building blocks, MVO / resampled MVO / Black-Litterman, LangGraph IPS generation and review. | Similar quant menu (Black-Litterman, resampling, Ledoit-Wolf/OAS). | Aimed at an advisor, not a retail user. **The LLM proposes the allocation**, which Robo-Kit forbids. Tushare / China data paths. |
| [disin7c9/asset-management](https://github.com/disin7c9/asset-management): 1 star, AGPL-3.0, pushed 2026-07-30T07:56:36Z | Portfolio *tracker* with a read-only Claude MCP add-on and a "number fence". | Deterministic numbers, AI only narrates, Claude integration. | Tracks existing holdings in USD only. It does not construct portfolios. AGPL. |
| [matvix90/ai-robo-advisor](https://github.com/matvix90/ai-robo-advisor): 48 stars, MIT, pushed 2025-10-31T20:02:38Z | LangGraph multi-agent: questionnaire, strategy, then an ETF portfolio of at most 4 ETFs, plus analyst agents. | Questionnaire-to-ETF flow. | "max 4 ETFs" and "2 years of data" (Polygon free tier). Agents choose the portfolio. |
| [AliJaffri/ai-robo-advisor](https://github.com/AliJaffri/ai-robo-advisor): 0 stars, licence None, pushed 2026-09-22T03:40:51Z | Classroom Streamlit app: tolerance vs capacity, SciPy optimizer, Monte Carlo, deterministic explanation layer. | Separates tolerance from capacity. Explanations are deterministic. | Teaching tool with no chat model and a small Yahoo universe. No licence. |
| [phrankson/claude--finance](https://github.com/phrankson/claude--finance): 3 stars, NOASSERTION, pushed 2026-06-26T17:28:47Z | Claude Code skill system for German personal finance, UCITS-only ETFs. | A jurisdiction-specific Claude plugin, the same packaging idea as Robo-Kit's plugin. | Germany-only, planning rather than optimization. |

**How Robo-Kit differs** (claims about Robo-Kit come from the project brief and `docs/METHOD.md`, not from this search):
* **Universe:** every CAD-buyable ETF on TSX and Cboe Canada *and* every US-listed ETF, with the user choosing the market. No project found covers either full universe with an optimizer.
* **Method:** an equilibrium (reverse-optimized) prior with bounded views, shrinkage, bootstrap resampling, and risk-matched walk-forward tests with costs. The analogues use 25-ETF risk parity or sample means.
* **Delivery:** a Claude artifact whose chat runs on the viewer's own Claude plan and calls deterministic page functions, plus an MCP server / Claude Code plugin. No artifact-based robo-advisor was found.
* **Claims discipline:** results are published with t-statistics and sub-periods. None of the chat analogues reports statistical uncertainty on its back-test, with one exception (kylekapoor, section F).

## 3. Portfolio-construction and back-test libraries

| Repo (stars / licence / last push, exact) | Relevant features (verbatim) | Borrow / avoid | MIT-compatible? |
| --- | --- | --- | --- |
| [PyPortfolio/PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt): 6060 / MIT / 2026-07-07T21:18:14Z (the old `robertmartin8/PyPortfolioOpt` path redirects here) | "Pyportfolioopt supports Black-Litterman asset allocation, which allows you to combine a prior estimate of returns (e.g the market-implied returns) with your own views to form a posterior estimate." Also "Ledoit Wolf shrinkage … three shrinkage targets: `constant_variance`, `single_factor`, and `constant_correlation`." | **Borrow as a test oracle.** Its BL posterior and constant-correlation Ledoit-Wolf should match Robo-Kit's to tolerance. Do not swap it in: Robo-Kit's FISTA solver already handles capped-simplex constraints. | Yes (MIT). |
| [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib): 4519 / BSD-3-Clause / 2026-09-24T05:23:00Z | "Portfolio optimization with Black Litterman model." Also Bayesian and Augmented BL, and "26 convex risk measures". | Borrow for **reporting** CVaR/drawdown risk measures and as a second BL oracle. A heavy dependency (C++ core), so keep it in dev/test extras. | Yes (BSD-3, keep the notice). |
| [skfolio/skfolio](https://github.com/skfolio/skfolio): 2443 / BSD-3-Clause / 2026-09-28T12:39:33Z | "tools compatible with scikit-learn to build, fine-tune, cross-validate, and stress-test portfolio models." Includes `BlackLitterman(views=...)`, `EntropyPooling`, `WalkForward`, `CombinatorialPurgedCV`. | Borrow `WalkForward`/`CombinatorialPurgedCV` as an **independent check of back-test splits** (catches look-ahead bugs). The views-as-strings API (`"AAPL - BBY == 0.03"`) is a good model for the schema Robo-Kit's signals layer emits. | Yes (BSD-3). |
| [fortitudo-tech/entropy-pooling](https://github.com/fortitudo-tech/entropy-pooling): 41 / BSD-3-Clause / 2026-01-23T13:22:36Z | "this package contains the Entropy Pooling implementation from the fortitudo.tech Python package with a more permissive BSD 3-Clause license." | Optional: scenario views ("rates +100 bp") as a later extension of bounded BL views. Use this BSD package, **not** the GPL parent. | Yes. The parent `fortitudo-tech/fortitudo.tech` (310 / GPL-3.0) is **not**. |
| [cvxgrp/cvxportfolio](https://github.com/cvxgrp/cvxportfolio): 1291 / GPL-3.0 / 2026-04-27T14:11:17Z | "Cvxportfolio is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License". | Read its cost and holding-cost modelling for ideas only. **Do not import it into the shipped package.** | No: GPL-3.0 would force GPL on the combined distribution. |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats): 7663 / Apache-2.0 / 2026-09-27T19:40:19Z | API description: "Portfolio analytics for quants, written in Python". | Optional cross-check of drawdown, Sharpe and Sortino in the back-test report. | Yes (Apache-2.0, keep NOTICE). |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt): 9206 / NOASSERTION / 2026-09-26T11:27:49Z | LICENSE.md: "the License does not grant to you, the right to Sell the Software." (Commons Clause) | **Avoid** in a product meant to ship commercially. | No: Commons Clause bars selling. |
| [pald22/covShrinkage](https://github.com/pald22/covShrinkage): 39 / MIT / 2024-05-26T01:36:26Z | Already ported (see RESEARCH_NOTES: QIS). The repo LICENSE is MIT, but the `QIS.py` header says "This file is released under the BSD 2-clause license." | Both are permissive. Keep both notices next to the ported QIS code. | Yes. |
| [hudson-and-thames/mlfinlab](https://github.com/hudson-and-thames/mlfinlab): 4935 / NOASSERTION / 2023-10-02T03:05:19Z | LICENSE.txt: "Copyright Protection Notice and Licensing Agreement". | **Avoid** (proprietary terms). | No. |
| [tradytics/eiten](https://github.com/tradytics/eiten): 3303 / GPL-3.0 / 2022-07-30T19:01:18Z | Topic hit for portfolio optimization. | Stale and GPL. Skip. | No. |

Not relevant to an ETF allocator (alpha research / RL trading): [microsoft/qlib](https://github.com/microsoft/qlib) (49009 / MIT / 2026-09-22T05:57:23Z), [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) (16420 / MIT / 2026-09-28T03:59:35Z). `RESEARCH_NOTES.md` already explains why learned allocators are out of scope.

## 4. Open-source robo-advisors (end-to-end or partial)

| Repo (exact) | Status | Verdict |
| --- | --- | --- |
| [highwire-ai/open-robo-advisor](https://github.com/highwire-ai/open-robo-advisor): 46 / BSD-3-Clause / 2022-03-19T18:23:03Z | "Open Robo-Advisor is a flexible robo-advisor library written in Python." Double-entry ledger, "Handles multiple currencies" (USD, CAD, …). | Stale since 2022. Its **ledger/rebalancing-trade idea** (target weights to share orders across multi-currency accounts) is a model for a later "rebalance my account" feature. BSD, so the code is reusable. |
| [VanAurum/robo-advisor](https://github.com/VanAurum/robo-advisor): 67 / BSD-2-Clause / 2019-05-20T18:59:17Z | Markowitz plus rebalancing with transaction costs (API description). | Stale. Nothing to add beyond METHOD.md. |
| [PacktPublishing/Robo-Advisor-with-Python](https://github.com/PacktPublishing/Robo-Advisor-with-Python): 59 / MIT / 2026-03-02T11:03:54Z | Book code: goals, risk questionnaires, KYC, orders, rebalancing, fees. | Useful as a checklist of what a *licensed* robo does operationally (KYC, accounts, orders). Robo-Kit is educational/decision-support and should say it does none of these. |
| [alpacahq/roboadvisor](https://github.com/alpacahq/roboadvisor): 46 / None / 2018-07-23T23:58:12Z, **archived: true** | Archived. | Skip. |
| [eleow/roboadvisorSystem](https://github.com/eleow/roboadvisorSystem): 43 / MIT / 2024-02-07T19:18:29Z | Notebook project. | Skip. |
| [C9290778laraSteele/Robo-Advisor](https://github.com/C9290778laraSteele/Robo-Advisor): 226 / NOASSERTION / 2025-03-29T12:15:42Z | Its only description is an x.com link (`https://x.com/robodotai`). | **Red flag.** A star count out of line with an empty description, no licence, created and abandoned within a month. Do not clone or link it. |

## 5. Canadian-specific open-source assets

| Asset (exact) | What was observed | Implication |
| --- | --- | --- |
| [JerBouma/FinanceDatabase](https://github.com/JerBouma/FinanceDatabase): 9369 / MIT / 2026-09-27T12:04:25Z. The `database/etfs` folder was last committed 2026-09-11T11:27:29Z. | README: "It features 300,000+ symbols containing Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies, and Money Markets." Per-exchange ETF CSVs were read in memory on 2026-09-28: **TOR 978 rows (890 CAD, 88 USD); NEO 89 (76 CAD, 13 USD)**. US: PCX 1699, BTS 484, NMS 219, NGM 205, NYQ 19, ASE 5 (total 2,631). Columns: `symbol, name, currency, summary, category_group, category, family, exchange, mic, isin`. | Good MIT **seed for classification** (category, family, summary). It is **not complete** enough to be "every ETF". Use official lists (TMX, Cboe Canada, Nasdaq Trader) as the source of truth and join FinanceDatabase for categories, recording coverage. Its "NEO" code is presumably the former NEO Exchange, now Cboe Canada (background knowledge, not sourced in this lane). |
| [jiahualihuanahuan/canadian-etf-holdings](https://github.com/jiahualihuanahuan/canadian-etf-holdings): 0 / None / 2026-09-20T03:42:31Z | "Coverage: 1,424 of 2,038 universe entries (69.9%) have complete holdings from issuer-published sources." Also: "We never invent tickers." | Evidence that Canadian look-through holdings are collectible from issuer downloads (Vanguard XLSX, iShares CSV, BMO, …). **No licence**, so the data cannot be redistributed. Re-implement issuer parsers with provenance and as-of dates, and copy the "never invent tickers" rule into the integrity checks. |
| [ariadruker1/etf_recommendation_tool](https://github.com/ariadruker1/etf_recommendation_tool) (above) | "Yahoo publishes no expense-ratio data for TSX-listed funds, so a 0.50% placeholder is used for all ETFs". It also notes `.U` (USD) and `.B` unit classes return 404 from Yahoo. | MER for Canadian ETFs must come from issuer pages or fund facts, not Yahoo. The universe builder must handle `.U` USD-unit and `.B` class tickers explicitly (CAD-buyable filter). |
| [haiiibin/acb-tax-mcp](https://github.com/haiiibin/acb-tax-mcp): 0 / MIT / 2026-09-21T05:58:37Z | API description: "MCP server for Canadian adjusted cost base (ACB) and capital gains: average-cost, superficial-loss detection, for LLM agents." | Out of v2 scope. A candidate optional companion for Canadian users later. MIT, but 0 stars and unvetted, so review the code before recommending it. |
| Wealthsimple / Questrade community wrappers (e.g. `gboudreau/ws-api-python` GPL-3.0; `EmilMaric/ws-rebalancer` MIT; several Questrade rebalancers) | Search hits only; READMEs not opened. | Account-linking is out of scope. Robo-Kit should not touch brokerage credentials. Listed only to show the Canadian open-source ecosystem is rebalancing calculators, not advisors. |

awesome-mcp-servers, Finance & Fintech section (432 entries): the only Canada-specific entries matching the filter were `haiiibin/acb-tax-mcp` and an accounting-skills repo. **No Canadian ETF data or allocation MCP server is listed.**

## 6. LLM and multi-agent financial analysts / advisors

| Repo (exact) | What it does (verbatim) | Borrow / avoid |
| --- | --- | --- |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents): 109046 / Apache-2.0 / 2026-09-25T06:36:11Z | "TradingAgents framework is designed for research purposes." v0.5.0 note: "point-in-time integrity across every dated path, SEC EDGAR fundamentals served as filed". | **Borrow:** the point-in-time data discipline and the multi-provider model registry (Anthropic effort control, OpenAI-compatible endpoints). **Avoid:** LLM analysts debating and deciding trades. That is the opposite of "scripts produce every number". |
| [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund): 63782 / MIT / 2026-09-26T14:10:46Z | "An LLM trained after your backtest window may remember how those companies did, and that memory would score as skill." It anonymizes ticker, industry and dates in back-tests. | **Borrow this control** for any back-test of LLM-derived views: anonymize, and prefer windows after the model's training cutoff. Its README says it is for educational purposes only. |
| [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot): 8100 / Apache-2.0 / 2026-09-28T11:24:54Z | "It combines foundation models with financial tools, quantitative models, deterministic computation, and multi-agent workflows to build decision-grade financial applications." Seven data providers with failover. | Equity-research focus. **Borrow** the provider-failover idea for the data bridge. Not an allocator. |
| [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT): 21298 / MIT / 2026-09-23T01:59:08Z | "FinGPT v3 series are LLMs finetuned with the LoRA method on the News and Tweets sentiment analysis dataset". | Open sentiment models (Llama-2-era LoRA) are a possible **offline sentiment scorer**. A scored number from a fixed model is more reproducible than asking a chat model. Check the model licence separately (Llama 2 terms). |
| [pipiku915/FinMem-LLM-StockTrading](https://github.com/pipiku915/FinMem-LLM-StockTrading): 962 / MIT / 2024-08-18T01:58:13Z | "FINMEM: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design". | Stale (last push 2024). Single-stock trading. Skip. |
| [virattt/dexter](https://github.com/virattt/dexter): 27628 / API licence **None** / 2026-09-23T19:56:36Z | "Think Claude Code, but built specifically for financial research." README says "This project is licensed under the MIT License." but the API finds no LICENSE file (`/license` returned 404). | Treat as unlicensed until a LICENSE file exists. Research agent, not an allocator. |
| [HKUDS/AI-Trader](https://github.com/HKUDS/AI-Trader): 22618 / None / 2026-06-11T09:26:03Z | API description: "AI-Trader: 100% Fully-Automated Agent-Native Trading". | Autonomous trading. **Avoid** (no licence; not Robo-Kit's use case). |
| [ValueCell-ai/valuecell](https://github.com/ValueCell-ai/valuecell): 11027 / Apache-2.0 / 2026-03-09T08:30:21Z | "It provides a team of TOP investment Agents to help you with stock selection, research, tracking, and even trading." | Stock-picking and trading. Skip. |
| [Alpha-Dojo/DojoAgents](https://github.com/Alpha-Dojo/DojoAgents): 3219 / Apache-2.0 / 2026-09-24T02:55:14Z | "DojoAgents is a full-market AI agent framework designed specifically for personal investment." | Retail-oriented agent loop, but it reasons toward strategies. Skip for allocation. The UX is worth a look (not assessed here). |
| [ginlix-ai/LangAlpha](https://github.com/ginlix-ai/LangAlpha): 1786 / Apache-2.0 / 2026-09-28T11:27:06Z | "Programmatic Tool Calling (PTC) — The agent writes and executes Python to process financial data from mcp servers instead of pouring raw data into the LLM context window". | **Borrow the principle:** bulk data (price panels, holdings) never enters the model's context. The model calls functions that return compact results. This matches Robo-Kit's artifact design. |
| [hsliuping/TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN): 32048 / NOASSERTION / 2026-09-22T12:11:05Z | LICENSE (translated): "this project uses hybrid licensing; different directories carry different licences". | Avoid (mixed licence, A-share focus). |
| [komako-workshop/digital-oracle](https://github.com/komako-workshop/digital-oracle): 845 / MIT / 2026-07-26T22:44:52Z | "It plugs into 13 authoritative financial data sources — from prediction markets like Polymarket and Kalshi, to US Treasury yield curves, CFTC institutional positioning". It "doesn't read newspapers". | **Borrow the idea for the geopolitics/macro layer:** use *market-implied* probabilities (yield curve, prediction-market prices) as sourced numbers instead of having the LLM read news and guess. Access to prediction markets from Canada, and their data terms, still need checking. |
| [RUC-NLPIR/FinSight](https://github.com/RUC-NLPIR/FinSight): 272 / GPL-3.0; [HKUSTDial/DeepFund](https://github.com/HKUSTDial/DeepFund): 297 / MIT; [FreedomIntelligence/TwinMarket](https://github.com/FreedomIntelligence/TwinMarket) (search hit, not opened) | Research systems (deep research reports; fund-investment benchmark; market simulation). | Not product components. DeepFund (MIT) could be read later as an evaluation design. |
| [ManuCabido/robo-advisor-multi-agent](https://github.com/ManuCabido/robo-advisor-multi-agent): 1 / None / 2026-03-05T21:19:12Z | API description: "Multi-Agent AI Robo-Advisor that generates institutional investment memos in minutes. Built with Cre[wAI] + Anthropic Claude". | Memo generator. Nothing to borrow. |

## 7. Evidence on LLM-generated views and signals (repos with papers)

| Source | Verbatim | What it means for the signals layer |
| --- | --- | --- |
| arXiv 2504.14345, "LLM-Enhanced Black-Litterman Portfolio Optimization" (CIKM 2025 Workshop on Financial AI). Code: [youngandbin/LLM-BLM](https://github.com/youngandbin/LLM-BLM), 41 / licence None / 2025-10-21T12:41:42Z | Abstract: "This study proposes and validates a systematic framework that translates return forecasts and predictive uncertainty from Large Language Models (LLMs) into the core inputs for the Black-Litterman model: investor views and their confidence levels." README: "Processes data monthly from June 2024 to February 2025". | The *mechanism* (LLM forecast → view; predictive dispersion → Ω confidence) is directly relevant to bounded views. The evidence covers a **9-month** window, which is too short to rely on. No licence: ideas only. |
| arXiv 2505.07078, FINSABER (KDD 2026 Datasets & Benchmarks, oral). Code: [waylonli/FINSABER](https://github.com/waylonli/FINSABER), 146 / Apache-2.0 / 2026-09-17T18:13:51Z | "Systematic backtests over two decades and 100+ symbols reveal that previously reported LLM advantages deteriorate significantly under broader cross-section and over a longer-term evaluation." | The strongest independent evidence that LLM *timing* signals do not survive broad, long tests. It supports Robo-Kit's defaults: equilibrium prior, LLM views off by default, any view capped and disclosed. |
| [kylekapoor/bl-robo-advisor](https://github.com/kylekapoor/bl-robo-advisor): 0 / None / 2026-08-24T00:14:16Z (self-reported, not peer-reviewed) | "The LLM never picks a weight." / "Every interval contains zero, on the full period and on the holdout" / "Views are untrusted input, validated against a Pydantic schema, a 15% magnitude ceiling and duplicate comparisons". | **Borrow the test design:** LLM-view arm vs `equilibrium` (no views), `shuffled` (views permuted across assets) and `static` (modal views replayed), with block-bootstrapped Sharpe differences. Also its bug list: a reversed pair counted twice doubles the confidence, so views must be de-duplicated on the *unordered* pair. |

## 8. Finance MCP servers and Claude integrations

| Server (exact) | Scope (verbatim) | Borrow / avoid | Licence note |
| --- | --- | --- | --- |
| [anthropics/financial-services](https://github.com/anthropics/financial-services): 38010 / Apache-2.0 / 2026-09-21T21:10:41Z (`anthropics/financial-services-plugins` redirects here) | "They do not make investment recommendations, execute transactions, bind risk, post to a ledger, or approve onboarding; every output is staged for human sign-off." Installed with `claude plugin marketplace add anthropics/financial-services`. Connectors to Morningstar, FactSet, S&P, LSEG and others: "MCP access may require a subscription or API key from the provider." | **Borrow the packaging:** a plugin marketplace with self-contained agent plugins (system prompt + skills + commands + `.mcp.json`). Robo-Kit's Claude Code plugin should use the same layout so `claude plugin install` works. **Borrow the disclaimer structure.** Its linked `claude-for-financial-advisors` directory returned 404 through the API, so its contents were not checked. | Apache-2.0: fine to follow. Copy text only with attribution. |
| [narumiruna/yfinance-mcp](https://github.com/narumiruna/yfinance-mcp): 196 / MIT / 2026-09-27T15:20:42Z | "Fund Look-Through — ETF and mutual-fund holdings, asset classes, sectors, ratings, and operating details". Also ETF screeners and news. | A good *personal-use* companion users can add themselves. Inherits Yahoo's personal-use terms, so do not bundle it as Robo-Kit's production data source. | MIT |
| [Alex2Yang97/yahoo-finance-mcp](https://github.com/Alex2Yang97/yahoo-finance-mcp): 356 / MIT / 2026-09-19T13:00:47Z; [gadicc/yahoo-finance2](https://github.com/gadicc/yahoo-finance2): 801 / MIT / 2026-08-09T16:52:02Z | Yahoo wrappers. yahoo-finance2 is JS ("Unofficial API for Yahoo Finance with CLI, MCP and Agent Skill"). | Same Yahoo caveat. yahoo-finance2 matters only if a Node MCP server is chosen. | MIT |
| [wshobson/maverick-mcp](https://github.com/wshobson/maverick-mcp): 678 / MIT / 2026-09-27T16:04:03Z | "**MaverickMCP** is a personal-use FastMCP server that provides financial data analysis, technical indicators, stock screening, and portfolio tracking tools to any MCP client". Installed with `uvx --from … maverick-mcp`. | **Borrow the distribution pattern** (FastMCP + `uvx` one-liner + optional extras). Its VectorBT backtesting extra carries the Commons Clause issue. | MIT (but see vectorbt) |
| [ebrandler/mcportfolio](https://github.com/ebrandler/mcportfolio): 6 / Apache-2.0 / 2025-06-11T13:49:19Z | PyPortfolioOpt behind MCP. "The LLM's ability to pick the right solver, parameters, and variables for an optimization problem is a judgment call. It is affected by the non-deterministic nature of LLMs." | **The anti-pattern Robo-Kit avoids.** A generic optimizer tool lets the model choose objective and parameters. Robo-Kit's MCP tools should take *profile + universe choices* and run a fixed, pre-registered method. | Apache-2.0 |
| [stefanoamorelli/sec-edgar-mcp](https://github.com/stefanoamorelli/sec-edgar-mcp): 359 / AGPL-3.0 / 2026-09-19T02:28:31Z | "Connects AI assistants to company filings, financial statements, and insider trading data with exact numeric precision." | Useful for US fundamentals. **Recommend it as a separately installed server. Do not vendor it.** | AGPL-3.0: do not copy code into the MIT repo |
| [stefanoamorelli/fred-mcp-server](https://github.com/stefanoamorelli/fred-mcp-server): 122 / AGPL-3.0 / 2026-08-22T18:34:49Z | "…universal access to all 800,000+ Federal Reserve Economic Data (FRED®) time series through three powerful tools." Needs a FRED API key. | Same as above. Robo-Kit's own macro scripts can call FRED's public API directly (FRED terms are a data-bridge question). | AGPL-3.0 |
| [daniel3303/Equibles](https://github.com/daniel3303/Equibles): 231 / AGPL-3.0 / 2026-09-28T15:07:39Z | API description: "Self-hosted, open-source financial data MCP server for AI agents — SEC filings, XBRL financials, 13F holdings…" | Same as above. | AGPL-3.0 |
| [financial-datasets/mcp-server](https://github.com/financial-datasets/mcp-server): 2300 / MIT / 2025-06-05T19:50:38Z | "It allows Claude and other AI assistants to retrieve income statements, balance sheets, cash flow statements, stock prices, and market news directly through the MCP interface." | Paid API. Last push June 2025. Stock-level, no ETF focus. Low priority. | MIT |
| [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server): 995 / MIT / 2026-09-25T12:52:26Z | API description: "Alpaca's official MCP Server lets you trade stocks, ETFs, crypto, and options". README: "`ALPACA_PAPER_TRADE` … Set to `false` for live trading". | **Avoid.** Order execution puts a product into dealer territory and is outside Robo-Kit's educational/decision-support scope. | MIT |
| [LLMQuant/data-mcp](https://github.com/LLMQuant/data-mcp): 79 / MIT; [tickerdb/tickerdb-mcp](https://github.com/tickerdb/tickerdb-mcp): 5 / MIT | Vendor-specific data MCPs (not opened beyond metadata). | Not assessed. |

## 9. Data-access libraries

| Library (exact) | Verbatim | Implication |
| --- | --- | --- |
| [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance): 25386 / Apache-2.0 / 2026-09-27T15:55:21Z | "Remember - the Yahoo! finance API is intended for personal use only." | The code licence (Apache) is fine. **The data terms are the problem for a shippable product.** Yahoo can stay the prototype and personal-use path, behind a data-provider interface that can be switched to a licensed feed. |
| [Luis-Rong/investment-bot-neu](https://github.com/Luis-Rong/investment-bot-neu) (deployment note) | "Yahoo blocks datacenter IPs, so the deployed app reads `data/universe_snapshot.json`". | Robo-Kit's artifact already ships precomputed JSON. Keep that design: the published page never calls Yahoo live, and snapshots carry an as-of date. |
| [dpguthrie/yahooquery](https://github.com/dpguthrie/yahooquery): 920 / MIT / 2025-05-15T15:07:59Z | Wrapper for the same unofficial Yahoo API (API description). | Same caveat. Last push May 2025. |
| [OpenBB-finance/OpenBB](https://github.com/OpenBB-finance/OpenBB): 73585 / NOASSERTION / 2026-09-28T17:36:18Z | LICENSE: "All files in this repository are licensed under the GNU Affero General Public License v3.0." | A useful multi-provider data platform, but **AGPL**. Do not import it into the MIT package. A user may run it separately. |
| [JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit): 5389 / MIT / 2026-09-10T16:10:58Z | API description: "Transparent and Efficient Financial Analysis". The FinanceDatabase README says its FMP-backed free plan only "features companies listed on US exchanges". | Ratio formulas are MIT and reusable for ETF/sector fundamentals. The data behind them is an FMP key question. |
| [ghostfolio/ghostfolio](https://github.com/ghostfolio/ghostfolio): 9370 / AGPL-3.0 / 2026-09-28T16:31:03Z | "The software is designed for personal use in continuous operation." | A tracker, not an allocator. AGPL. Useful only as a UX reference. |

## 10. Licence compatibility for an MIT-licensed Robo-Kit

| Class | Repos here | Can Robo-Kit depend on it? | Can Robo-Kit copy code into its repo? |
| --- | --- | --- | --- |
| MIT / BSD-2 / BSD-3 | PyPortfolioOpt, Riskfolio-Lib, skfolio, entropy-pooling, covShrinkage, FinanceDatabase, FinanceToolkit, yahooquery, investment-bot-neu, AI-WealthPilot, yfinance-mcp, maverick-mcp, FinGPT (code), open-robo-advisor | Yes | Yes, keeping the copyright notice |
| Apache-2.0 | yfinance, quantstats, TradingAgents, FinRobot, anthropics/financial-services, mcportfolio, FINSABER, LangAlpha | Yes | Yes, keeping the LICENSE and NOTICE and marking changes |
| GPL-3.0 | cvxportfolio, fortitudo.tech, eiten, FinSight, ws-api-python | Not in the distributed package (the combined work would have to be GPL) | No |
| AGPL-3.0 | OpenBB, sec-edgar-mcp, fred-mcp-server, Equibles, ghostfolio, disin7c9/asset-management | Not bundled. It can be *recommended* as a separate server the user installs. | No. Re-implement ideas (e.g. the number fence) from scratch. |
| Commons Clause / proprietary / hybrid | vectorbt, mlfinlab, TradingAgents-CN | No, for a commercial product | No |
| **No licence (all rights reserved)** | LLM-BLM, FinPilot, bl-robo-advisor, etf_recommendation_tool, canadian-etf-holdings, AliJaffri/ai-robo-advisor, AI-Trader, dexter (no LICENSE file), cardiel, etfdb | No | No. Ideas and published facts only, with a citation. |

Also note that model weights (e.g. FinGPT LoRA on Llama 2) and data (Yahoo, FMP, prediction markets) carry their own terms, separate from the code licence. That is a data-bridge and compliance question, not settled here.

## 11. What Robo-Kit should borrow, build, avoid and disclose

**Build (ideas re-implemented from scratch, with a credit in docs):**
1. **Number fence** in the chat layer, from disin7c9/asset-management: "Python computes every number; the optional AI narrates — it never receives the figures, and every value it quotes is substituted from the computed result." In the artifact, the model's reply can contain `{{weight.XIC}}`-style tokens that the page fills from the optimizer output, and a reply with raw numerals in numeric claims is rejected or regenerated. That turns the "scripts produce every number" principle into a checkable property.
2. **Status codes instead of silent compromise**, from FinPilot's `ok | needs_clarification | constraint_infeasible`. When the user's caps, exclusions or target volatility cannot all hold, the engine returns `constraint_infeasible` with the binding constraint named, and the chat explains it.
3. **Views pipeline with controls**, from kylekapoor, LLM-BLM and FINSABER:
   * views are JSON validated against a schema (asset or pair, magnitude cap, confidence), de-duplicated on unordered pairs, and dated before the rebalance;
   * every back-test of views reports `no views`, `shuffled views` and `static views` arms, with block-bootstrap intervals, alongside the existing t-statistics;
   * views are off by default until they beat these controls.
4. **Look-ahead and memorization controls**, from TradingAgents v0.5.0 point-in-time data and ai-hedge-fund's anonymized back-tests. Any LLM-derived signal back-test must use only as-filed data and should anonymize tickers and dates or use periods after the model's training cutoff.
5. **Market-implied macro and geopolitics numbers** (yield-curve slope, breakevens, where available and licensed prediction-market prices), after digital-oracle. These go in the signals layer instead of free-text news judgments by the LLM.
6. **Narrow deterministic MCP tools**, after investment-bot-neu (`get_prices`, `compute_risk_metrics`, `list_universe`, `target_volatility`, …) and contrasted with mcportfolio. Expose `list_universe(market)`, `screen(filters)`, `profile_to_lambda(answers)`, `optimize(profile, universe, constraints)`, `backtest(profile)` and `explain(weights)`, each returning provenance (data as-of date, method version). The model should never choose objective functions or estimator parameters.
7. **Plugin packaging** that mirrors anthropics/financial-services: marketplace, self-contained plugin, skills, commands, `.mcp.json`. Server distribution uses FastMCP + `uvx`, as in maverick-mcp.

**Borrow (dependencies or test oracles, permissive licences):**
* PyPortfolioOpt (MIT) and skfolio (BSD-3) as **oracles in the test suite** for the BL posterior, Ledoit-Wolf constant-correlation, and walk-forward split boundaries. Riskfolio-Lib (BSD-3) as an optional oracle and reporting source for CVaR/drawdown.
* FinanceDatabase (MIT) for ETF category, family and summary enrichment, joined onto official exchange lists, with a coverage report showing how many listed ETFs lack a category.
* entropy-pooling (BSD-3) only if scenario views are added later.

**Avoid:**
* Designs where the LLM decides (TradingAgents, ai-hedge-fund, AI-Trader, ValueCell, the AI-WealthPilot IPS proposal, mcportfolio parameter choice).
* Order execution (alpaca-mcp) and brokerage credential handling (Wealthsimple/Questrade wrappers).
* GPL/AGPL/Commons-Clause code inside the MIT package: cvxportfolio, fortitudo.tech, OpenBB, vectorbt, the EDGAR/FRED MCPs (recommend those separately instead).
* Copying code or data from unlicensed repos (canadian-etf-holdings, TSX ranker, FinPilot, LLM-BLM, kylekapoor).
* Yahoo as the production data source for a shipped product (personal-use terms, datacenter IP blocks, missing TSX MERs).
* The suspicious `C9290778laraSteele/Robo-Advisor` repo.

**Disclose (in the product and README):**
* Educational / decision-support, not advice. No orders, no KYC, no account linking. Every major project here carries this language, and Anthropic's own repo says outputs are "staged for human sign-off".
* The data source, as-of date and coverage of each universe (e.g. "N of M listed ETFs have category and MER data").
* That LLM-derived views have weak independent evidence (FINSABER), and whether views are on.
* Third-party licences (NOTICE file for Apache dependencies, BSD notices).

## 12. Gaps and caveats

* **Absence of evidence.** The "nobody has built it" conclusion rests on GitHub search (about 45 queries), GitHub topics, the awesome-mcp-servers finance section and a code search. GitLab, Hugging Face Spaces, closed-source products (Wealthsimple, Questrade Portfolio IQ and other commercial robo-advisors) and most non-English repos were not searched systematically.
* `wilsonfreitas/awesome-quant` (29839 stars, licence None) and `georgezouq/awesome-ai-in-finance` (6629, CC0-1.0) were identified but not parsed.
* Performance numbers quoted from READMEs (FinPilot, kylekapoor, investment-bot-neu's eval table) are **self-reported** and were not reproduced.
* The TradingAgents star count (109046) is the exact API value but looks unusually high for a December 2024 repo. The API reported it and no inflation was verified. Stars are not used as a quality signal here.
* FinanceDatabase counts come from its per-exchange CSVs on 2026-09-28. The true number of listed ETFs per exchange was not established in this lane; that belongs to the data-bridge lane (official TMX / Cboe Canada / Nasdaq Trader lists).
* The contents of `anthropics/financial-services/claude-for-financial-advisors` could not be retrieved (API 404).
* Data licences (Yahoo, FRED, prediction markets, issuer holdings files) are flagged but not analysed. That is a separate compliance and data-bridge task.
* `pald22/covShrinkage`: the repo LICENSE is MIT, while the `QIS.py` file header is BSD 2-clause, which is what `RESEARCH_NOTES.md` cites. Both are permissive. The ported file should carry the BSD 2-clause notice.
