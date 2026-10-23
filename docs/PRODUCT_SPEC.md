# Robo-Kit v2: product plan and specification

28 Sep 2026. Status: built and verified (see section 15). This document is the complete plan: what the product is, how each part works, why it is built that way, what ships now, and what has to happen before a public launch. Research behind every decision is in `docs/research/` (six lanes, every claim with a source and a verbatim quote).

## 0. The product in one minute

Robo-Kit is a do-it-yourself ETF portfolio lab. A person can:

1. **Search every ETF they can buy.** That covers 2,187 Canadian listings in Canadian dollars (TSX and Cboe Canada) and 5,770 US listings. Every fund is classified, and every exclusion comes with a reason.
2. **Take a short self-check.** The questions are fixed. It scores risk capacity (what their situation can absorb) and risk tolerance (what they are comfortable with) separately, and suggests the lower of the two.
3. **Choose a level and fill each asset class with funds.** The page starts from the lowest-cost broad fund in each class, and the person keeps, swaps or adds funds.
4. **See what a transparent engine does with those choices.** The result shows weights with uncertainty bands, ranges in dollars, fees in dollars, past-crisis replays, ten-year paths, plain-language reasons and the full mechanism.
5. **Ask Claude anything along the way.** Claude runs on the viewing account, where Anthropic allows it (the owner, or the owner's Team/Enterprise organization; see section 2), and the person chooses how powerful a model to use. Claude calls Robo-Kit's tools for every number, and a checker rejects any reply that contains a number no tool produced.

It ships three ways, all built on one engine:
- a web page (a Claude artifact);
- a Python package with an MCP server, which works in Claude Desktop, Claude Code or any MCP client;
- a Claude Code plugin.

What ships now is the impersonal learning simulator the law allows without registration (section 14). The version that tells a specific person "this is your portfolio" needs a registered firm, a human reviewer and licensed data. Section 14 lays out that path.

## 1. Who it is for

| User | What they need | How Robo-Kit serves them |
| --- | --- | --- |
| First-time investor (Canada or US) | Understand ETFs and build a diversified mix without jargon or a sales pitch | Chat-first page, fixed questions shown as tappable cards, answers in dollars, a glossary, plain English |
| DIY investor | Compare funds, test changes, see the maths | Search across the whole market, side-by-side comparisons, swaps and what-ifs, a "Show me how" layer |
| Course panel and teammates | See the mechanism and the evidence in minutes | The same page with the mechanism layer, the pre-registered back-test and method docs |
| Developers and Claude power users | Use their own tokens and models, and live data | MCP server, Claude Code plugin, a command-line agent on an API key |

The design follows plain-language rules. Almost half of Canadians have literacy challenges (Canada.ca style guide), so sentences stay under 20 words and figures are shown in dollars first (`research/ux-conversation.md` section 8).

## 2. What exists already, and how Robo-Kit differs

Full survey: `research/prior-art-github.md`.
- **No open-source Canadian + US ETF robo-advisor with an LLM chat was found** (GitHub search across 25 queries, plus the awesome-mcp-servers finance list).
- **The closest projects each cover one piece.** One is a TSX ETF ranker with a quiz but no optimizer. Two are chat-first ETF advisors limited to 25 US ETFs. One is a German Claude finance plugin.
- **The big LLM finance repos solve a different problem.** TradingAgents (109k stars) and ai-hedge-fund (64k) let the model make trading calls on single names. Robo-Kit forbids that.
- **Portfolio maths is a solved open-source problem.** PyPortfolioOpt (MIT) and Riskfolio-Lib and skfolio (both BSD-3) cover it, so Robo-Kit uses them as test oracles, not dependencies.
- **Robo-Kit's edge is elsewhere:**
  - the full Canada + US universe with reasons for every exclusion;
  - a written, auditable engine;
  - calibrated risk levels;
  - honest, pre-registered back-tests;
  - a Claude chat whose numbers are enforced by code.
- **Big firms are moving the same way.** Vanguard announced the same split for its advice chat in September 2026: "deterministic design" behind a conversational layer.

## 3. Surfaces and "bring your own Claude"

| Surface | Who runs Claude | Model choice | Data | How to use |
| --- | --- | --- | --- | --- |
| Web page (Claude artifact) | The viewer's own Claude plan (artifact `sample` capability; the viewer approves the first call and pays with their own usage) | Quick, Standard or Deep in the Assistant menu (`modelTier` quick / default / complex) | Dated snapshot bundled with the page (the page cannot reach the internet) | Open the link |
| MCP server (`python -m robokit mcp`) | The user's Claude Desktop or Claude Code session, on their own subscription | Whatever model they pick in their Claude app | The committed snapshot at once; fresh data after `python -m robokit refresh` on their machine | Add to `claude_desktop_config.json`, or `claude mcp add robokit -- python -m robokit.mcp_server` |
| Claude Code plugin (`.claude-plugin/`) | Their Claude Code session | Their model setting | As above | `/plugin marketplace add dylanguo1129/ai-robo-advisor` then `/plugin install robo-kit@robo-kit` |
| Command-line agent (`python -m robokit chat`) | Their own `ANTHROPIC_API_KEY` | `--tier quick|default|complex` (Haiku 4.5, Sonnet 5.5, Opus 5.5) or any `--model` | Live | Terminal |

**Who can use which surface.** Anthropic's sharing rules for artifacts that call Claude matter here (`research/gap-artifact-runtime-and-distribution.md`):
- Such an artifact cannot be shared by public link, and people invited from outside your organization cannot use its Claude features.
- On a Pro or Max account, the web page's assistant therefore works for the owner. On a Team or Enterprise account it works for members of that organization.
- Everyone else can still open a shared page and use every non-AI feature: search, the self-check, the mix and the mechanism.
- Any other Claude user who wants the assistant uses the plugin or the MCP server in Claude Code or Claude Desktop, on their own plan and with their own model choice, or the terminal agent with their own API key.
- claude.ai chat itself can reach only remote MCP servers. A public Robo-Kit connector for chat would re-serve data, so it waits for licensed data.

**Where replies are checked.**
- **Web page:** before the text settles. The page validates it and triggers one rewrite.
- **Terminal agent:** before display.
- **Claude Code plugin:** just after display. A Stop hook (`hooks/check_reply.py`) runs the same checker on the last reply against that turn's Robo-Kit tool results, and blocks with a correction request if a number or ticker has no source.
- **Claude Desktop (MCP only):** no runtime check. The rules and the tool design carry it.

The rules are identical on every surface. The same `AGENT.md` governs all of them: the web page condenses it into its standing instructions, the MCP server serves it as a prompt and a resource, the plugin uses it as its skill, and the CLI sends it as the system prompt. The tools are the same everywhere too: the web page mirrors them in JavaScript, and `web/test_robokit.mjs` checks that it matches the Python engine.

## 4. Architecture and the anti-hallucination design

```
 data bridge (Python)            engine (Python; mirrored in JS)          tools (one contract)        surfaces
 listings, metadata, prices  ->  classify -> universe (eligibility) ->   get_questions, score_profile, -> web artifact (sample capability)
 macro, geopolitics, news        shelf -> histories -> estimates ->       scenario_cards, risk_ladder,     MCP server / plugin
 integrity + as-of stamps        risk calibration -> weights ->           reference_shelf, search_etfs,    CLI agent (API key)
                                 stress, projections, checks, text        etf_profile, compare_etfs,
                                                                          build_portfolio, market_context,
                                                                          explain_term, backtest_summary,
                                                                          data_status
```

Hard-coded scripts are used wherever they can reduce hallucination. Here is where each kind of error is stopped:

| Risk | Control |
| --- | --- |
| The model invents a figure | Every figure comes from a tool. `validate.check_reply` (Python and JS) pulls every number and ticker out of each reply and rejects any that is not a rounding of a tool value. The web page and terminal agent get one rewrite, then highlight anything still unsupported; the Claude Code plugin's Stop hook forces a correction. |
| The model invents a fund | Tickers are checked against the 7,957-listing universe and the tool results |
| The model scores risk itself or rewords questions | The questions are fixed items (`robokit/profile.py`) shown as buttons; `score_profile` is deterministic |
| The model writes an allocation | Only `build_portfolio` produces weights; the rules forbid text allocations |
| Explanations drift | Explanation sentences are generated from computed numbers by templates (`robokit/explain.py`) |
| Definitions drift | A fixed glossary (`robokit/glossary.py`) |
| Different models give different answers | The numbers come from tools, so every tier gets the same figures; only the wording varies |
| Headlines steer advice | News is labelled untrusted context; the rules forbid acting on it, and no signal moves weights by default |
| A stale or failed source | Every result carries `as_of` and a data snapshot hash; a failed source is recorded, never hidden (`context_meta.json`) |

Every portfolio result also carries a reproducibility record: engine version, data snapshot and the full request.

## 5. Data bridge

All sources were tested on 28 Sep 2026 (`research/data-sources.md`; `robokit/data/`).

| Need | Source | Access | Status |
| --- | --- | --- | --- |
| US ETF list | Nasdaq Trader `nasdaqlisted.txt`, `otherlisted.txt` (ETF flag) | HTTPS, no key | 5,738 ETF symbols |
| Canadian ETF list and metadata | TMX Money GraphQL `getETFs` (AUM, inception, sectors, regions, top-10 holdings, P/E, P/B, beta) | HTTPS, no key | 1,805 TSX instruments |
| Cboe Canada, fees, size, first trade | Yahoo Finance screener (bulk; `netExpenseRatio`, `netAssets`) | yfinance | fee coverage for eligible funds: 93% Canada, 98% US |
| US categories and fund families | Yahoo screener, one query per category | yfinance | 3,362 US funds categorised |
| Prices | Yahoo monthly adjusted closes (total return), chunked and resumable | yfinance | 7,792 series, 1986 to Aug 2026 |
| FX | Yahoo `CAD=X` | yfinance | US funds converted to CAD for Canadian portfolios |
| Canada rates, CPI | Bank of Canada Valet (policy rate, 3-month bill, 2- and 10-year, CPI) | JSON, no key | ok |
| US rates, VIX | Yahoo `^IRX`, `^FVX`, `^TNX`, `^VIX` | yfinance | ok (FRED times out from some networks; credit spread is best-effort) |
| Geopolitics | Caldara-Iacoviello GPR (monthly file) | HTTPS | ok |
| Policy uncertainty | Baker-Bloom-Davis EPU, US and Canada | HTTPS | ok |
| News | GDELT DOC 2.0 (tone, volume, headlines with links) | no key; rate-limited | partial in this snapshot (1 of 6 topics); retries with backoff |

**Integrity.**
- Duplicate listings are removed (a TSX fund also quoted on Cboe Canada is one fund).
- Canadian Depositary Receipts are detected and excluded.
- Partial months are dropped.
- Duplicate month rows from Yahoo are collapsed.
- Gaps are left as gaps, never filled.
- Every fetch writes its raw payload with a timestamp to `data/v2/raw/`.

**Refresh.** Run `python -m robokit refresh` (15-30 minutes), then `python -m robokit bundle` to rebuild the web snapshot. A monthly refresh matches the monthly data.

**Licensing (a launch gate).** Findings from `research/gap-public-data-licensing.md`:
- A full monthly return series can be turned back into a price history, so vendors treat it as price data. The published page's bundle therefore stays private or team-shared.
- **US, free and licence-clean:** SEC Form N-PORT filings carry each fund's monthly total returns from mid-2019. Gaps: grantor trusts and commodity pools such as GLD.
- **US, cheapest paid:** Tiingo's commercial plan with a "Derived Products" clause (volatilities, correlations and model outputs may be published; return series may not).
- **Canada:** no vendor with a published price that allows public display. It takes a negotiated licence (EODHD, Intrinio, Barchart, TMX Datalinx), or Canadian computations stay on the user's machine through the MCP server.
- **Canadian MER and risk ratings:** issuer fund lists are the working source (about 38% direct MER coverage, 46% with a tested route to both fields). Their terms are personal-use, so a product needs issuer permission or a licensed feed such as Fundata (`research/gap-canadian-mer-and-etf-facts.md`).

Yahoo, TMX and Nasdaq allow personal use only. The bundled snapshot is fine for a private or team artifact. A public launch needs licensed prices and listings, or a "bring your own data" design where the MCP server fetches on the user's machine (already how the MCP path works). Bank of Canada, GDELT, GPR and EPU can be redistributed with attribution.

## 6. Universe and classification

`robokit/classify.py` and `robokit/universe.py` classify every listing using written rules. The rules draw on hard evidence in the name, then the provider's category, then the look-through holdings. The fields are the ones the brief lists: asset class, region, theme, sector, leverage (signed multiple), inverse, single-stock, derivatives (options, futures, swaps), strategy (market-cap index, factor, active, options-based, leveraged), currency, hedging, crypto, target-date, ESG, issuer, fee, size, inception, history, 3- and 5-year volatility, 1/3/5/10-year returns, maximum drawdown, traded value and dividend yield. Each fund carries a `why` note with the rule that fired.

**Eligibility for the optimizer.** A fund must meet all of these; otherwise the reason is recorded in plain language:
- not leveraged or inverse;
- not single-stock;
- not a CDR;
- in CAD (for the Canadian market);
- at least 36 months of history;
- current prices;
- at least $20M (Canada) or $50M (US) in assets;
- at least $50K / $250K traded per day.

Result: 637 eligible Canadian funds and 1,998 eligible US funds (version 3.0.3; the registered evaluation used the earlier labels, under which 630 and 1,966 passed). The leading exclusion reasons are short history, small size and thin trading.

**The reference shelf (`robokit/shelf.py`).** Each asset class is defined by a written rule: asset class, region, a name pattern, exclusions and a hedging requirement. The fund shown first is chosen by a published score (low fee, large, liquid, long history), and the runners-up are listed so the person can swap. Current picks:

| Canada (CAD) | US (USD) |
| --- | --- |
| Canadian stocks: XIC | US stocks: VOO |
| US stocks: VFV | International: VXUS |
| International: FLUR | Emerging markets: VWO |
| Emerging markets: VEE | US bonds: BND |
| Canadian bonds: ZAG | Short Treasuries: VGSH |
| Short-term bonds: XSB | TIPS: SCHP |
| Global bonds, hedged: VBU | International bonds: BNDX |
| REITs: XRE | REITs: VNQ |
| Gold: VALT | Gold: GLDM |
| Cash: CASH | Cash: SGOV |

Optional classes are also on the shelf: long-term bonds, real-return bonds, hedged US equity and high yield in Canada; small caps, long Treasuries, corporate bonds and high yield in the US.

## 7. Risk profile: how answers become a level

Rules come from `research/ux-conversation.md` section 6 and `research/methods-signals.md` section 1; the code is `robokit/profile.py`.

1. **Readiness gates first.** Money needed within 2 years and all at once means no stock portfolio; the person is offered the learning path. No emergency fund, or a lot of high-interest debt, caps the level at 2 and shows a "first things first" card (FCAC wording).
2. **Capacity (1-5)** comes from the time horizon: when withdrawals start plus how long they last, a score from 0 to 15. It drops one step for each cushion (this money is most of their savings, income is uneven, the emergency fund is partial), by at most two steps in total (one when the horizon score is 13 or more).
3. **Tolerance (1-5)** comes from questions with outcomes in the person's own dollars: a one-year range, a sharp drop, a ten-year range, and loss versus missing out. The ranges come from the engine's own portfolios at each level. Since 3.1.0 a self-rating (C0) is asked as well: low / medium / high = levels 2 / 3 / 4 until 3.3.0, and 2 / 3 / 5 since 3.3.1 so that level 5 can be reached (DECISIONS P9), because the team's conversation script pairs it with the drop scenario; when the two point different ways (flag F_self_vs_drop) the page asks which fits better and sets the other aside. The guided page asks the self-rating, the drop and the one-year range; the ten-year range, loss versus missing out and the share of savings are an optional fine-tune. Inconsistent answers lower tolerance by one step and trigger a clarifying card (the Wealthfront rule).
4. **Suggested level = min(capacity, tolerance).** This is what Joint CSA/CIRO Staff Notice 31-368 (Dec 2025) asks for. It is a suggestion, not a ceiling (v2.1, RESEARCH_LOG section 7). The person may choose any lower level freely. A level above the suggestion but within capacity is labelled "above your comfort answers". A level above capacity opens an in-page sheet with that level's bad year and crisis replays in the person's dollars, the answers that set the limit with Change links, and three buttons: keep the suggestion, change that answer, or explore anyway. Exploring is recorded and labelled everywhere ("level 5 · above your self-check"). Only the gates cap the build: G2/G3 at level 2, and G1 (all of the money within 2 years) means no stock mix. Evidence: docs/qa/ux/SYNTHESIS.md section 3 (Betterment, Vanguard, CFR FAQ, CSRC Art. 19; Path A in docs/research/regulation.md section 7).
5. **Knowledge** (two quiz items) is never scored for risk. It only sets how much is explained.
6. **Mapping to the portfolio.** Level L targets L x 20% of the stock market's volatility. The stock market's volatility is measured on the stock part of the market anchor over the data window. Anchoring to the stock market keeps every level reachable and gives people a picture they recognise: "level 3 takes on about 60% of the stock market's ups and downs".

The brief's low / mid / high risk appetites are levels 2 / 3 / 4 (Cautious, Balanced, Growth).

## 8. How each ETF's weight is set

This is `robokit/engine.py`, mirrored in `web/robokit.js`.

1. **Funds.** The shelf funds (with the person's swaps) plus their own picks ("satellites"). The engine never adds a fund on its own.
2. **Returns in one currency.** A US-listed fund in a Canadian portfolio is converted to Canadian dollars.
3. **Longer histories for young funds.** Otherwise five years of data would decide everything.
   - Core funds are spliced with a written proxy for the months before they existed. For example, VFV before Nov 2012 uses SPY converted to CAD, and CASH before 2021 uses PSA and then the Bank of Canada T-bill yield. A proxy is used only if it correlates at 0.8 or more with the fund over their overlap.
   - Satellites are back-filled from their measured relationship with the core funds (regression plus their own residuals; Stambaugh 1997).
   - Every splice is listed in the result.
4. **Estimates.**
   - Covariance: Ledoit-Wolf shrinkage over up to 15 years of monthly data.
   - Expected returns: equilibrium returns implied by a written market anchor (equity 60 / bonds 35 / real estate 3 / gold 2, with 30% of equity in Canada for Canadian investors and market-cap shares for US investors). Never historical averages. This is the v1 finding: history-based expected returns chase noise.
5. **Risk calibration.** Bisection on the risk-aversion parameter (lambda) until the portfolio's volatility equals the level's target.
6. **Guardrails** (the ones a human advisor would apply):
   - 50% per fund;
   - REITs and gold 10% each;
   - emerging markets 15%;
   - cash at most 30% at levels 2 and 15% above (only level 1 may be mostly cash);
   - the person's own picks 10% each (crypto 5%) and 10/20/30% in total by level.
7. **Resampling.** The weights are averaged over 200 resampled histories (stationary block bootstrap). The 5-95% band per weight shows how firmly the data pins it down. Positions under 2% are dropped and the rest re-optimised.
8. **Optional views.** A person's own view ("gold beats bonds by 2% a year, 60% sure") enters through Black-Litterman with Idzorek-style 0-100% confidence. The tilt is capped at 1% tracking error and 5 points per fund, and it is shown next to the no-view mix. Views are off by default.

Parity: the JavaScript engine reproduces the Python weights and crisis replays to within 0.002 (largest observed gap 0.0002), with identical notes and checks, on 13 reference cases, including satellites, the hedged sleeve, a hedged swap and refused swaps (`web/test_robokit.mjs`). The view case names IAUM, which is no longer the shelf's default gold fund (GLDM is), so the view is not applied and the Black-Litterman path is not yet parity-tested.

## 9. Market context: fundamentals, sentiment, news, geopolitics

The inputs considered are fundamentals, sector fundamentals, sentiment, market news and geopolitics, past performance, the current story and future possibilities. The research (`research/methods-signals.md`) grades each one:

| Input | Evidence for monthly asset-class returns | Robo-Kit use |
| --- | --- | --- |
| Past performance | Not a forecast; the v1 back-tests showed that chasing it hurts | Shown with the standard warning; never used as an expected return |
| Fund fundamentals (fee, size, liquidity, holdings, P/E, P/B, yield) | Fees and liquidity matter reliably; valuation is weak for timing | Filters, shelf score, fee drag in dollars, fund cards |
| Sector fundamentals (look-through sectors and regions) | Descriptive | Classification and concentration checks |
| Trend (12-month) | Mixed: long history, contested for single assets | Shown per fund; an opt-in tilt was pre-registered and did not pass (section 10) |
| Valuation | Weak for timing; useful as a long-run anchor | Built into the planning assumptions (FP Canada uses earnings yield) |
| News tone (GDELT), sentiment | Weak at monthly horizons | Context and headlines with links; never a weight input |
| Geopolitical Risk index, policy uncertainty, VIX | Weak for returns; where they predict anything, high fear has come before higher returns | Risk flags with their percentile in history, plus stress scenarios |
| LLM-scored news | Weak, and cannot be back-tested honestly inside the model's training window | Not used |

Forward-looking possibilities are covered by bootstrap projections re-centred on published planning assumptions, and by replays of seven real crises. The seven are 2008, 2011, 2014-16 oil, late 2018, 2020, 2022 and the 2025 tariff shock.

When someone brings a headline, the assistant must follow a fixed pattern (`AGENT.md` section 6):
1. show the relevant flag with its date;
2. state the research finding without promising anything;
3. show the mix's bad-year range and the closest stress test;
4. ask whether their situation, not their mood, changed.

## 10. Back-testing

The protocol was pre-registered before any v2 run (`docs/RESEARCH_LOG.md` section 6) and run once (`scripts/run_backtest_v2.py`, `output/v2/`). It uses a 60-month rolling window, re-estimation every year, monthly rebalancing and a 10 bps trading cost; fund fees are included in the returns. All results are hypothetical.

| Level 3 (Balanced) | Canada, Dec 2009 to Aug 2026 | US, Jul 2018 to Aug 2026 |
| --- | --- | --- |
| Robo-Kit | 8.3% a year, volatility 6.9% (target 6.8%), worst drop -13.8% | 8.5%, volatility 10.3% (target 8.7%), worst drop -19.6% |
| Static 60/40 of the same funds | 8.5%, 7.2%, -14.4% | 8.7%, 10.5%, -19.9% |
| Textbook (history-based) optimizer | 8.2%, 6.8%, -15.4% | 10.2%, 10.3%, -18.2% |
| Equal weights | 7.5%, 6.9%, -14.8% | 7.4%, 8.8%, -17.8% |

What it shows:
- **Canada:** the levels delivered almost exactly the volatility they promised. Robo-Kit, the static mix and the textbook optimizer are statistically tied; no difference has a t-statistic above 2 at level 3.
- **US:** the shorter 2018-2026 window was dominated by US large caps. The textbook optimizer did better there (+1.5% a year at level 3, t = -2.1). Realised volatility ran above target in the 2020 and 2022 shocks.
- **Trend tilt:** the pre-registered rule required a t-statistic above 2 in both markets at level 3. It got 2.6 in the US but 1.3 in Canada, so it stays off.

The product labels every back-test "hypothetical" and says that volatility is a target, not a guarantee. Known biases:
- funds were chosen with today's information;
- proxies extend young funds;
- no delisted funds are included.

## 11. Projections and stress tests

- **Projections** (`robokit/projection.py`): each fund's monthly history is re-centred on its planning assumption after fees, then 5,000 paths are drawn by stationary bootstrap.
  - The planning assumptions come from the FP Canada 2026 Projection Assumption Guidelines. For US bonds and cash, today's Treasury yields are used.
  - Outputs: a 10-90 and 25-75 percentile fan, the one-year range, ranges by holding period (1, 3, 5, 10 years) and, when a goal is set, the "chance you would need to adjust" and the typical shortfall. There is no "success %".
  - The fixed disclosure uses FINRA 2214 language.
- **Stress tests** (`robokit/stress.py`): buy-and-hold replays of seven crises on the current weights. Missing history is filled with the median fund of the same class and region, and those stand-ins are listed.

## 12. Conversation design

The guided page (3.1.0) follows the team's conversation script: opening, calibration ("How much do you already know about ETFs?", which sets explanation depth for the session and never the risk disclosure), goal and horizon, the basics, money, income, the risk check with its second chance, the one-year range cards, an optional fine-tune, optional preferences and tickers, the shortlist, the assessment, the mix and a closing recap. Typed text is read as an answer, a change, a ticker or a question (web/converse.js); questions are answered (by Claude when the viewer connects it, else from the page's glossary, FAQ and fund facts) and followed by "Back to building your portfolio?". Advice requests get the script's fixed redirect and the disclosure before any AI is asked. The fixed wording is in web/kb.js; the coverage of the Requirements Plan is in docs/research/requirements_coverage_v31.md.

The assistant rules for the other surfaces are in `AGENT.md`. Its essentials:
- **Disclosure.** An AI disclosure in the first message of every session (Anthropic Usage Policy). Never "AI financial advisor" (AI washing).
- **Hard rules.** Numbers and funds come only from tools, questions use fixed wording, the level is the lower of capacity and tolerance, and the person chooses. No buy/sell/hold instructions, no forecasts, no text allocations, and no changes because someone sounds insistent.
- **Flow.** S1 market and goal, S2 readiness, S3 horizon and capacity, S4 tolerance, S5 clarify, S6 knowledge, S7 preferences, S8 profile card, S9 asset-class ladder, S10 fill with funds, S11 the mix, S12 what-if, S13 next steps. Learn and Compare paths branch off.
- **Playbook for risky requests.** Leverage, "just tell me what to buy", "guaranteed?", pushback, crash panic, vulnerability cues, tax questions, prompt injection, and a request for a human.
- **Voice.** Plain words, dollars first, ranges not forecasts, calm, neutral about issuers. Replies are in English.
- **Help links.** CSA registration search, SEC IAPD, FINRA BrokerCheck, FCAC, non-profit credit counselling, and 988.

## 13. Interface

Visual system: `docs/design/DESIGN.md` (Wealthsimple-style minimal). Mode: operate a task.

Since 3.1.0 the web page is the guided page (web/index.html), built from Yasmin's six wireframes: 1 homepage (a type box, three prompts, "Connect Claude for reasoning"), 2 the conversation, 3 the assessment and disclaimer, 4 the portfolio mix (level picker, one line of reasons per fund, market context, recap, summary export, session log), 5 Learn more (expected returns, historicals, industry news, what the fund holds, questions), 6 adjustments (expected return before and after, the risk-level warning). It offers Canadian-listed ETFs only, as the Requirements Plan scopes. The earlier page described below is kept as web/classic.html. The earlier page's structure:
- **Landing.** One large input box (the brief asks for a Google- or ChatGPT-style opening page), five chips, the AI disclosure and the data date. A docked tray on the right shows the reference mix working from the first second.
- **Thread.** Every answer is a card: question cards with dollar scenario ranges, the profile card, the five-level ladder, the shelf, the mix report, fund cards, comparisons, market context, definitions, proposals with an Apply button, and assistant replies with a verification footer.
- **Tray.** The live mix: level control, asset-class bar, one-year range, bad year, fees in dollars, volatility, funds, and "Open the full mix". On phones it becomes a bottom sheet.
- **Mix report.** Weights with 5-95% bands, key numbers in dollars, plain-language reasons, ranges by holding period, a projection fan with amount / monthly / years inputs, stress tests, checks, and "Show me how". That last section shows the target volatility formula, lambda, shrinkage, draws, window, a per-fund table (market anchor, model return, planning return after fees, volatility, risk share), the spliced histories and the hypothetical back-test.
- **Without AI** (outside Claude, or when the viewer declines), every chip, search, card and calculation still works. Typed text is routed by fixed rules: tickers open fund cards, two tickers open a comparison, known terms open definitions, anything else searches.

Accessibility: keyboard focus rings, labelled controls, `aria-live` replies, reduced-motion support, and light and dark themes.

## 14. Compliance and launch path

Source: `research/regulation.md`. This is not legal advice; section 9 of that file lists what a lawyer must confirm.

**Path A (what ships now): an impersonal, free learning simulator.**
- No fees, ads, affiliate links, issuer sponsorship or data sales.
- No accounts, orders, custody or rebalancing.
- The impersonal view (the ladder) comes first; named funds come only from the person's own choices, starting from a clearly labelled reference.
- Copy never says "recommended for you" or "your portfolio".
- AI disclosure at the start of each session. Hypothetical labels and methodology next to the numbers. Data provenance on every figure. A written legal opinion before any public launch.

**Path B: a registered, personal robo-advisor.**
- Canada: register as a portfolio manager under NI 31-103 using the CSA 31-342 hybrid model, or license Robo-Kit to a registered online advisor.
- US: SEC registration under the internet adviser exemption, or license the engine to an RIA or broker-dealer.
- Both countries: Anthropic's Usage Policy requires a qualified human to review personalised advice before it reaches consumers.
- The engine, the records (`record` in every result) and the disclosures were built to Path B standards so they carry over.

Requirement checklist (R-numbers from `research/regulation.md`):

| Requirement | Status |
| --- | --- |
| R1 impersonal output, user-driven filters, no order entry | Done |
| R2 disclosures (AI at session start, method, hypothetical, universe, conflicts, provenance) | Done in the page and tools; lawyer to approve wording |
| R3 back-test presentation rules | Done: labelled, after costs, full period with fixed sub-periods, configurations disclosed |
| R4 questionnaire rules (separate blocks, lower of the two, inconsistency checks, cash outcome, plain language, 18+ before the build) | Done |
| R5 suitability-style checks | Done: concentration, near-duplicates, liquidity, fee drag at 10 and 25 years, complex products, reference comparison |
| R6 product data | Partial: facts, reasons and dates are in place; monitoring of issuer changes (mergers, fee changes) is a remaining item |
| R7 AI guardrails | Done: rules, validator, escalation links, tier logged |
| R8 records | Done for Path A (version, snapshot, parameters in every result); Path B needs retention and KYC records |
| R9 model governance | Done: 120 Python tests, JS parity test, pre-registered back-test, supplier list in docs/DATA.md |
| R10 no monetisation without sign-off | Policy stated |

## 15. Quality and verification

- `python -m pytest tests -q`: 639 tests (552 run on a fresh clone and in CI; the 87 others need the local data cache in `data/v2/` or the v1 price file). They cover the v1 solver and estimators, the classification rules, profile scoring (gates, flags, the lower-of rule, rejection of unknown answers), the group-capped solver against SLSQP, bounded views, the provenance validator, engine invariants (weights sum to 1, caps hold, volatility rises with level, the cash cap), exclusion of leveraged funds with a reason, the satellite cap, the claim that explanations use only computed numbers, the tool contract, and 18 regressions from the code review (docs/VERIFICATION.md section 3).
- `node web/test_robokit.mjs`: the browser engine against the Python engine.
- MCP end-to-end: a stdio client lists all 15 tools and the `robo_kit_guide` prompt, and calls them.
- The API-key agent loop was tested with a stub model. The validator caught an invented return and an invented ticker, and forced a rewrite.
- An independent review workflow ran two reviewers (engine, web) and six persona tests of `AGENT.md`, scored by the deterministic validator. Results are in `docs/VERIFICATION.md`.

## 16. Roadmap and decisions for the team

| When | Item | Owner |
| --- | --- | --- |
| Before 7 Oct (gate 1) | Adopt this universe and schema as the course dataset (it is far beyond the outline's 100-200 funds) | Data lead |
| Before 18 Oct (gate 2) | Persona walk-throughs by teammates on the live page; pilot the questionnaire (timing, test-retest) | All |
| Before 27 Oct | Teaching note (Task 1) using the market figures; deck; record a backup demo video | Research lead, Lead |
| After the course | Licensed data (prices, Canadian listings); issuer-change monitoring; legal opinion (Path A) | Product |
| Later | Registered partner or registration (Path B); human review for personalised output; retention of records | Product, counsel |

Open decisions:
1. Share the artifact beyond the team only after the data licence question is settled.
2. Whether the course presents the product as Path A (recommended) or discusses Path B as the business plan.
3. Whether to add Cboe Canada's own listing API for the roughly 250 Canadian funds that only Yahoo lists.

## 17. How this maps to the course brief

| Brief task | Where it lives |
| --- | --- |
| 1. ETF teaching note | Glossary and education layer; market figures from the data bridge. The written note is still the Research lead's section. |
| 2. ETF dataset and classification | Section 6: 7,957 listings, every brief field, `data/v2/universe.csv` |
| 3. Selection tool with custom filters | Search, filters, shelf swaps and own picks (web page, `search_etfs`, `reference_shelf`) |
| 4. Optimizer by risk aversion | Sections 7-8; low / mid / high = levels 2 / 3 / 4; lambda shown in "Show me how" |
| 5. AI conversation like Google or ChatGPT | Sections 3, 12, 13: the chat-first page and the Claude guide |
