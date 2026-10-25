# Changelog

## 3.3.2 (October 2026)

Fixes from a review of the whole repository in six lanes (documentation, links and commands, the Python engine and
tools, the web page, scripts and CI, data and outputs). Each finding was reproduced by running the code before it was
fixed, checked by a reviewer from another model family, and given a test; docs/VERIFICATION.md section 8.15 has the
record. The engine, the data and every published number are unchanged: `web/data/` differs only in the engine version.

- **The guided page reads answers more carefully.**
  - Months count as the horizon only when they say when the money is needed. "6 months of expenses" answers the
    emergency-fund question and "hold for 6 months" the drop question; neither sets the horizon to "less than 2 years"
    any more, which could lower the suggestion from 5 to 2. "In 6 months" still means less than 2 years.
  - An emergency fund below the question's 3-month bar ("I have 2 months of expenses", "less than 3 months") is
    "partly", not "yes", and "zero months" is "no". A bare "18 months" after the goal still answers the horizon,
    spelled-out months ("eighteen months") are read, and 24 months or more counts as two years or more.
  - A student loan or student credit card is debt: it no longer records "no regular income"; "I'm a student" still
    does.
  - Answers that end in "... for me" ("medium is ok for me") are recorded. Asked or requested ("is level 5 too risky
    for me?", "tell me the mix that is right for me") they still get the advice redirect, and so do three phrasings
    that never did: "what is the right mix for me?", "which level is good for my situation?" and "the best level for
    someone like me".
  - A number of years the person typed ("in about 25 years") is repeated later only while it matches the recorded
    horizon, not after a tap or a change.
  - With the assessment waiting and its window closed, a reply that is neither a question nor an answer opens the
    assessment again; before, it showed an empty question card.
  - On the mix, "remove XUS" for a fund that is not in it says so instead of claiming a removal and rebuilding, and
    "add SPY" explains why the fund is not available.
  - The assessment's asset-class shares and the session log use the fund rows' whole percents, so each adds to 100.
  - "Why we ask" about the goal now says the goal sets how the money is likely to come out, which feeds the risk
    capacity (it said the goal did not change the math).
  - The back-test sentence under Historicals names what was tested: Penguru's earlier rules (version 2, September
    2026, a 60-month window). Its figures are unchanged (DECISIONS P12).
- **Tools and the command line.**
  - `reference_shelf` was described as "the lowest-cost broad funds", but it is ordered by the published score, in
    which low fees weigh most; the first fund is not the cheapest of the five listed in 11 of 14 Canadian classes. The
    descriptions now say so, the default `sort_by` is `score` (the same order as before) and `cost` now sorts by fee
    (DECISIONS P13).
  - `compare_etfs` no longer fails on a fund without a price series or on two spellings of the same fund, and a
    missing first month is sent as null, so `etf_profile` works over MCP in local-data mode.
  - `backtest_summary` labels its result as the v2 engine's September 2026 run and names its settings.
  - `get_questions` says that the self-rating (C0) is asked with the tolerance questions.
  - `python -m robokit refresh --help` (and `bundle` and `status`) prints help instead of starting a download or
    rewriting `web/data/`.
  - Exclusion reasons round amounts down, so a fund just under a minimum never reads as having it. The shipped reasons
    keep the old rounding until the next data refresh.
- **Reproducing.** `replicate.py evaluation --full --code <folder>` refuses at once unless the folder is a git checkout
  of the registered commit (the registered script records its commit, so it failed after unpacking the data);
  REPRODUCE.md and the script say a ZIP download covers the quick part only.
- **Tooling.** `make check` also runs the conversation checks and the syntax check of every module, as CI does. The
  research URL check writes the date it ran. `/publish-robo-kit update` looks for copies titled "Penguru" as well as
  "Robo-Kit", and its sizes and model wording match the page.
- **Documentation.** The pointers to the page's assistant rules name `web/guide.js` (the published page), not only
  the classic page's `web/assistant.js`. PRODUCT_SPEC's calibration, parity and test counts are current. data/README,
  docs/DATA.md and CONTRIBUTING describe the committed data of record and how to restore the cache offline instead of
  downloading new data. AGENT.md gives the engine's rebalancing band and asks the self-rating. optimizer/README and the
  model card carry the level-4 caveat, and "run once" is corrected where a run was made twice.

## Reproducibility kit (October 2026; no change to the engine or its numbers)

- **The data of record is in the repository.** `data/replication/` holds the local-cache files every published number was computed from (snapshot `00a560f4a6d3`, 4.3 MB as `.tar.xz`), with SHA-256 hashes in `MANIFEST.json`, and the optimizer tables as printed in our reports (`report_tables.json`).
- **`scripts/replicate.py`** re-runs our results offline and checks them value by value: `tables` (the reports' Tables 1, 4 and 7: 99 printed values), `snapshot` (`web/data/` rebuilt from the archived data), `evaluation` (the registered evaluation re-run with its own commit's code in a temporary worktree: a quick part, or `--full`), and `data` (unpacks the archive into `data/v2/` for the full test suite).
- **[REPRODUCE.md](REPRODUCE.md)** gives the steps, the times, what "the same" means and where each published number comes from; the README links it from the top and has a short "Reproduce our results" section.
- **[optimizer/README.md](optimizer/README.md)** explains how the optimizer works, from the fund list to the calibrated λ and the resampled weights, why we chose this method over the alternatives we tested, and what our evaluation does and does not show.
- **CI** runs the reproduction checks on Linux on every push (the "Reproduce" job); `tests/test_replication.py` checks the archive against its manifest and the engine against the reports' tables.
- Docstrings in `optimizer/` and `robokit/engine.py` that still described earlier versions (a bisection for λ, a 35% cap, "the lowest-cost fund") now match the code; the README's layout no longer calls the engine "v2", and its evidence paragraph says the reviewers were AI models.

## 3.3.1 (October 2026)

Fixes found by rehearsing the team's two demo personas ("Presentation click flow") on the published page, and one scoring change so the top level can be reached.

- **Level 5 can be suggested.** The self-rating "High: I can live with big swings for more growth" now counts as 5 (it was 4). Before, tolerance could never reach 5, so no answers could suggest level 5. Level 5 now needs all three of: a long horizon spread over time, no cushion or emergency-fund/debt limit, and every comfort answer at its top. Money for a home taken out all at once stays at 4 at most (20+ years) or 3 (10 to 19 years), because of the capacity score. The brief's low / mid / high settings stay levels 2 / 3 / 4. A side effect: "High" next to a comfort answer of 2 now counts as inconsistent answers and lowers tolerance by one step (60 of the 2,160 answer combinations).
- **Questions are answered, not recorded.** "If I add $350 a month, would those funds be invested in the mix?" is read as a question. It has a saved answer (each month's amount goes into the same mix at its weights; it does not change the level), and it is no longer taken as the amount.
- **Typed answers.**
  - An option's label typed word for word ("New to this: explain as we go") is that answer.
  - "Yes, No" on the emergency-fund and debt card fills both in order.
  - A ready-made prompt typed instead of tapped ("I'm a longer term investor looking to learn more") sets the same goal.
  - A share of savings given as a range ("10-25%", "10 to 25", "between 10 and 25") is read by its upper end, and a bare number from 6 to 100 is a percent; 1 to 5 still pick an option.
  - A reply that opens with "Actually", "Well" or "Honestly" is read; "I do not have emergency savings" is a no (it was read as a yes); "I don't have much saved" is partly; "I don't have much debt" is a little.
  - A typed "Skip" on an optional question is shown once, and the fine-tune answer is shown in the person's wording.
- **Changes typed on the mix.** A sentence that changes answers ("Actually I don't have an emergency fund and I have a lot of credit card debt") goes through the conversation, so every answer in it is kept and the assessment is shown again.
- **The emergency-fund and debt limits are visible on the mix.** Their "first things first" notices are shown above the mix and in the summary. Levels above the limit are greyed out; tapping one says why it is not available, instead of doing nothing.
- **The recap.** When the limit holds the level, the recap says so instead of comparing the two scores; when both scores are the same it says "both point to N".
- **Whole percents agree.** The asset-class bar, its legend, the summary and the before-and-after table use the same whole percents as the fund rows, so each adds to 100.
- **Tickers.** A ticker already on the shortlist answers the ticker question, so the mix is built.
- **One fund's projection** (Learn more on a fund) uses the same horizon as the mix, not at least 10 years.
- **Wording.** The one-year question names the monthly amount when there is one.

## 3.3.0 (October 2026)

The team's second round of feedback on the guided page, as Yasmin consolidated it (prototype review, "cleaned up feedback v2"), and her Penguru brand kit. Only the listed changes were made.

- **The name and the brand.**
  - The guided page is now **Penguru**: the title, the header, every fixed sentence, Claude's instructions and the summary file. The engine (robokit.js, core.json, the Python package) keeps its name, so the page renames the engine's words as they come in.
  - The brand kit's colours: navy #12263F, ice blue #2F7FB0 for charts, gold #E8A33D for highlights, slate #4A5A6E for body text, and mist #F4F6F9 for the background. Dark mode has its own steps.
  - The kit's typeface, Sora, at weights 400, 600 and 700.
  - The kit's mark is redrawn as an SVG for the header, the greeting and the favicon. Below 32 px the chart line is dropped, as the kit says.
- **Removed or simplified.**
  - No shortlist preview: after the optional ticker question the mix is built at once. Funds can still be added or removed by typing on the mix.
  - No word definitions printed under messages: investing words are buttons that show their definition.
  - Question 3 ("Once you start, how long will you keep taking money out?") is no longer asked, since it repeated question 2. It still feeds the risk capacity, so the page fills it in from the goal:
    - a home: all at once;
    - education: 2 to 5 years;
    - retirement: more than 10 years;
    - anything else: the engine's middle setting;
    - building wealth: not used, as before.

    The filled-in answer is marked "assumed from your goal" in the checkpoint, the answers, the explanation of the level and the summary. Change asks the question; a typed answer replaces it. Money for a home needed within two years still gets no stock mix.
  - No market note in the middle of the questions; the Market context section stays on the mix. This also fixes the ticker question that appeared twice.
- **Fixed.**
  - A term, a "Learn more" or a suggested question tapped again points to the explanation already on screen and highlights it, instead of adding it again.
  - Words are linked to a term only in their investing sense:
    - "the biggest factor in" is no longer a factor fund;
    - a risk or price index is not a market index;
    - a distribution of outcomes is not a fund distribution;
    - "capacity" and "yields" on their own are not linked.
  - Nothing said before the assessment mentions a risk level; the assessment is where it is introduced. The careful-side messages for no emergency fund or high-interest debt, the fine-tune offer and "How this is scored" were reworded. A typed term question no longer shows the person's level figures before the assessment.
- **Engine.** `score()` in Python and `scoreProfile()` in the browser take an optional list of assumed answers. These score exactly as given answers and are worded as assumptions.
- **Found by the cross-family review and fixed.**
  - A ticker that adds nothing (such as the US-listed SPY) keeps the ticker question open, so the Canadian alternatives can be added.
  - A term tapped again on the mix highlights the copy on the mix, not the one on the hidden chat screen.

## 3.2.0 (October 2026)

The team's PRD v3 and Yasmin's cross-check. Her two main points were the open conversation flow and the explanation depth by experience. This release covers those plus the PRD's new data, filtering and output rules. docs/research/requirements_coverage_v32.md maps every requirement to its code and test.

- **Open conversation.**
  - Every answer in a message is read, in any order: a story typed up front fills the goal, timing, amount and debt.
  - Each turn says what it understood, with "Noted · Change" chips.
  - A vague reply gets a two-choice follow-up. A reply that isn't understood is put another way, then explained.
  - An answer is never recorded for the wrong question. Risk answers given in passing are checked on their own card, with the person's own numbers.
  - Questions still get an answer and "Back to building your portfolio?", which now names the next question.
- **Depth by experience (F1, E1).**
  - Depth is self-identified (the calibration, or words like "I'm new to this", "keep it brief", "I've been investing for 10 years"). Otherwise it is inferred from what the person types once the first questions are answered. It is never shown as a label.
  - Beginners get plain wording, an example under each option, and the reason for each question shown.
  - Experienced viewers get short questions, the scoring rule behind each one, and shortcuts. Their results show more: full reasons, per-fund risk, volatility against its target, the chance of a loss, the risk-rating scale, Sharpe, and an open "Under the hood" panel.
  - Steps, options and the math are the same at every depth; a browser test checks that the weights are identical.
- **Data (D2, D3).**
  - Categories outside the locked lists are flagged and excluded, in both the Python screen and the browser engine.
  - Missing fees show as "not in our data", and missing dates are blank.
- **Filtering (F2, F3).**
  - New preferences, read clause by clause: maximum fee, CAD-only, one stock region, active and factor style, hedged or unhedged.
  - Unknown tickers get the closest matches.
  - US-listed tickers are explained, with the Canadian-listed funds that follow the same index.
- **Changes (F4, O3, X3, X4).**
  - Back on every question, and typed changes for every answer.
  - The optimizer re-runs at once and shows a before-and-after table: weights, expected return and volatility.
  - Adjust keeps every fund except cash at 50% or less, and shows volatility.
- **Conversation rules (C2, C3, C6, C7, E4).**
  - A typed level waits for the questions and the assessment.
  - Leverage and derivatives notices also cover funds the data leaves blank.
  - More advice phrasings are caught, including levels and weights asked about as a personal decision.
  - Out-of-scope questions get the tool's scope; comparisons with other products get "only covers ETFs at this time", with a definition.
- **Output (X1, X2, X5, E3).**
  - The disclosure appears next to every projection.
  - The summary has three sections and includes the projection chart.
  - Market context shows Canadian readings with their sources, and links to approved news sources.
- **Claude.**
  - Instructions follow the person's depth.
  - No level is mentioned before the assessment.
  - Replies with a directive, a label, a guarantee or an unsupported number are held back.
- **Review.**
  - Five audit lanes drove the page, and an independent check re-tested each lane.
  - Three designs and a judge produced one specification.
  - A cross-family reading by Gemini 3.8 Flash High found five defects. Each was reproduced, fixed and covered by a test.
- **Tests.** web/test_converse.mjs: 511 checks. tests/ui/test_guided.py: 52 browser tests. tests/test_v32_prd.py: new.

## 3.1.0 (October 2026)

The guided page becomes the web page: Yasmin's six wireframes with the team's conversation script and Requirements
Plan (Phase 0), and the fixes from the team's prototype review. `web/yasmin.html` becomes `web/index.html`; the earlier
page stays as `web/classic.html`.

- **Conversation script.** Calibration ("How much do you already know about ETFs?"), goal and horizon, the basics
  (emergency savings, high-interest debt), money, income, a risk self-rating with the drop scenario and a second
  chance when the two disagree, the one-year range cards, optional fine-tuning, optional preferences, optional tickers,
  then the shortlist ("add or remove anything before I calculate"). Core questions are required; a "don't know" gets
  an explanation and "even a rough guess is fine"; optional steps skip cleanly. About ten taps instead of fourteen.
- **Explanation depth** follows the calibration for the whole session: beginners see why each question is asked,
  suggested questions and a definition the first time a term comes up; every term in the text explains itself on a tap.
- **Ask anything, then go back.** Typed text is read first as an answer (words, numbers, "within 2 years", "$20k and
  300 a month", several facts at once), then as a change ("actually change my risk to high"), a ticker ("add XEQT") or a
  question. Questions get an answer and "Back to building your portfolio?". Without Claude the page answers from its
  glossary, FAQ, fund facts and the issuers' top holdings of the ten default funds (data/fund_holdings.json, two
  independent lookups); with Claude connected ("Connect Claude for reasoning", on the viewer's own plan) answers come
  in Claude's words, with page tools and every number checked by validate.js.
- **Advice boundary.** "What should I buy?" and the like get the script's redirect and the disclosure every time,
  before any AI is asked.
- **Engine.** New optional tolerance item C0 (low / medium / high = levels 2 / 3 / 4, the brief's three settings) and
  flag F_self_vs_drop when it disagrees with the drop scenario (robokit/profile.py and web/robokit.js; 400 random
  profiles identical in both). Answers without C0 score as before.
- **Preferences and shortlist.** Theme focus adds the cheapest eligible index fund for it as an own pick; "avoid"
  leaves a default fund out; lowest-cost swaps each slot to the cheapest fund of its kind; hedging and ESG use the
  engine's switches. A zero match says which filter to drop and asks first. Own picks get at least a small share (5%,
  within the level's own-pick limit) so they stay in the mix. The page offers Canadian-listed ETFs only.
- **Results.** The assessment explains what the level means in dollars and names no label for the person; a level
  above the suggestion needs one look and a tick, and the mix then says it was not calculated from the answers; the
  same for adjusted weights, which now show the expected return before and after. One line of reasons per fund,
  market context with a question back, a closing recap, a session log, and a summary to copy or download after the
  person confirms the decisions are their own. "Past performance is not reflective of future performance." on every
  result.
- **Found by driving the page** (docs/research/requirements_coverage_v31.md lists all eighteen): amounts with
  thousands separators, facts read clause by clause, everyday words no longer taken for tickers, a typed question shown
  at once while Claude thinks, a chosen level kept when an answer changes (never above the emergency-fund cap), Adjust
  opening on the measured level of the built mix, and the summary carrying the "not calculated for you" sentence.
- Tests: tests/ui/test_guided.py (29 browser tests), web/test_converse.mjs (178 checks); the classic page's 70 browser
  tests now run against web/classic.html.

## 3.0.4 (October 2026)

The stored data checked against sources that do not share its code (docs/research/v304_data_verification.md,
scripts/dataverify/, tests in tests/test_v304_dataverify.py).

- Monthly returns of 707 series (every eligible Canadian fund, every stand-in, the US slots' first candidates and
  CAD=X) re-derived from daily prices: 704 agree within 0.5% in every month; the three exceptions are explained.
  The Bank of Canada series, the derived statistics of 7,792 funds and the eligibility screen are reproduced
  exactly; USD/CAD is within 0.21% of the Bank of Canada on average.
- The reference funds' MERs come from the issuers' own pages (data/issuer_mer.csv, each with URL, quote and as-of
  date). Seven were 0.01-0.02 points off on Yahoo (VFV 0.09% -> 0.08%, VEE 0.26% -> 0.24%, VBU 0.23% -> 0.21%,
  VALT 0.17% -> 0.18%). The default mixes do not change; the level-3 fee falls from $12 to $11 per $10,000.
- The team data layer's inception date (Yahoo's profile date, years late for about 100 funds) yields to TMX's
  listing date, and fund age is measured to the last price month. A bridge file without MER or AUM columns no
  longer fails the build.
- web/yasmin.html: the Yasmin edition, Yasmin's six wireframes (home, chat questions, assessment, mix, learn more,
  adjustments) on the same engine and data, published as a separate artifact for team feedback. The main page is
  unchanged; scripts/check_publish.py now counts only the main page's own scripts when it checks capabilities.

## 3.0.3 (October 2026)

Labels and fund facts from the team's Canadian ETF data layer (github.com/shreyajane23/robokit-data), which
cross-checked this universe fund by fund (docs/research/v303_crosscheck.md, docs/DECISIONS.md, docs/RESEARCH_LOG.md
section 14; tests in tests/test_v303_crosscheck.py).

- Region: "Global X" is read as the issuer's brand, not a region, so its S&P 500, Nasdaq-100, Russell 2000, Dow and
  US Treasury funds are US funds (HXS, HXQ, USCC, USCL, QQCC, HTB and DLR among the eligible ones); a Global X theme
  fund that names no region stays Global. "ex U.S." and "ex North Amer" read as International developed (VDU, VEF,
  VIU, VI, VBG); "Australian" reads as Asia-Pacific.
- Leverage: "(-3X)" keeps its minus sign (the four MegaShort funds were +3x); garbled multipliers and "2xLeveraged"
  are read; a TMX or Yahoo leverage category no longer makes a fund leveraged unless its name says so, so "Daily
  Inverse" funds are -1x (were +2x), "Inverse Leveraged" funds -2x, and "Enhanced", crypto and income funds 1x.
- 136 listings change a label; HDIF.TO and XUSP become eligible (637 Canadian and 1,998 US funds). No slot's
  reference fund changes; HXS.TO and VDU.TO join two slots' candidates. The default mixes and every reported number
  are unchanged.
- `robokit/universe.py:add_team_data` merges the data layer's bridge file when it is in `data/v2/`: inception date,
  fund age, a calculated (CSA-method) risk rating, distribution frequency and yield, secondary theme, and MER for
  blanks (eligible Canadian funds with an MER: 594 of 636 -> 622 of 637). MERs outside 0.05%-3% and zero AUMs are
  not used.
- Under these labels the strict point-in-time shelf (E2) gains HXS.TO in Canada's US-stock slot for December 2014,
  a year it had no fund old enough; E2 is not re-run.

## 3.0.2 (October 2026)

Currency-hedging labels, found while the team's optimizer report was reviewed (docs/research/v302_hedging_labels.md,
docs/DECISIONS.md, docs/RESEARCH_LOG.md section 13; tests in tests/test_v302_labels.py).

- VALT, the Canadian gold fund, is CI's CAD-hedged unit but was labelled unhedged (its name has no hedging word), so
  it was extended before 2021 with unhedged gold. It now gets GLD in US dollars, unconverted, as the stand-in rule
  requires. This changes the Canadian default mixes slightly; a re-run of the Canadian walk-forward with the label
  corrected (output/v3_valt_check, scripts/v3_valt_check.py) leaves the risk readings unchanged and turns the level-4
  non-inferiority reading against the static mix to "inconclusive". The registered results stand as registered.
- The name rule reads "C$ Hedged Series" and "Currency Neutral" as hedged and "Non-Currency" or "Non-FX Hedged" as not
  hedged (it read the last two backwards). Plain-named hedged units get an issuer-sourced override shown in the fund's
  note: VALT, KILO, HUG (also futures-based), HHL, BASE, DGR, TXF, CESG and IQD. 37 labels change in all; no default
  fund, ranked candidate list or eligibility changes, but HUG leaves the gold slot's swap list.
- The strict point-in-time shelf (E2, robokit/research.py) now takes only funds the swap gate admits. HUG was its only
  Canadian gold fund with 36 months of history from 2012 to 2022, so E2 would now leave gold out in those years; the
  registered E2's level-3 mixes held HUG in 2012 to 2015. E2 is not re-run.
- Documents: the issuer-return check is 14 of 17 funds within 0.05 points a year, not 15 (VALT 1.20 below, mostly
  the gap between market price and NAV); counts, test numbers and versions updated in README, PRODUCT_SPEC, METHOD,
  MODEL_CARD and data/README; the plugin manifests carry the engine version; the hand-off files regenerated; three
  paper sentences qualified (the 66% coverage figure is for 120 months, the deflated Sharpe ratio is if anything too
  favourable, the E5 cap test scaled the slot caps only).

## 3.0.1 (October 2026)

A second bug hunt after the registered run (docs/DECISIONS.md, 53 findings, regression tests in
tests/test_v3_bug_hunt.py). A verification re-run of the whole evaluation with this version (output/v3_verify,
scripts/v3_verify_rerun.py) leaves Robo-Kit's own results and every benchmark but the textbook optimizer unchanged.

- Requests: unknown MCP arguments refused; `level` and `relax_limits` on the MCP tool; contradictory inputs refused
  (a fund long and short against itself, own weights on an excluded fund); unmatched exclusions, unused minimums and
  inputs that own weights ignore are named in notes; strict types and bounds in both validators and every tool.
- Numerics: the zero-risk-aversion fill keeps the joint cap on own picks; dropping tiny weights never rescales a fund
  past its cap; QIS falls back to constant-correlation shrinkage on a rank-deficient sample; one-fund sample
  covariance; the calibration labels a proven jump correctly and, with a view, reports the delivered volatility.
- The two engines agree on the hedge for a caller's slot list, crisis peers (real histories only), rounding in
  checks, explanations and fees, and unit counts.
- Rebalancer: no sale of more units than held, reserve funding, no orders under the minimum after trimming, notes
  that match the orders, drift reported with band trades off, null inputs and costs of 100% refused.
- Fund labels and the swap gate: option- and futures-based funds kept out of core slots, word-stem theme rules,
  long listing names for generic or damaged ones, 'Ultra' short-term bond funds no longer read as leveraged (37
  funds eligible), PEY, BITW and VI.TO labelled correctly, the ESG shelf keeps every slot.
- Evaluation code: the symmetric studentised interval beside the registered equal-tailed one; the textbook
  benchmark aims at the common target; the static mix fails closed; E7(b) in portfolio currency. The paper
  discloses the registered intervals, the textbook target and the one-sided 5% non-inferiority test.

## 3.0.0 (October 2026)

Engine
- Risk aversion is calibrated on the mix the client receives (resampled, minimum position applied, the same draws at
  every step): bracket, then Illinois regula falsi; every result is within 0.005 percentage points of the target, a
  proven jump of the minimum-position rule, or a bound, with its evidence recorded (both engines).
- Exact projection onto the capped simplex and the exact largest eigenvalue for the step size; solvers fail closed
  without a convergence certificate.
- One random generator (mulberry32) in Python and the browser; QIS in the browser; resampled weights now match.
- One request validator; limits that cannot all hold are refused, or relaxed on request in a fixed, recorded order.
- Fund swaps must pass the slot's own rule (hedged or not) and a like-for-like label: no option- or futures-based
  fund, and no fund labelled narrow when the slot's fund is broad. A stock fund is labelled broad only when its name
  names a whole-market index and nothing narrower (after the run; docs/research/e7e_taxonomy.md). The page offers
  only alternatives the gate accepts.
- Data-integrity screen: 14 funds whose monthly return doubled or halved while their peers did not are not eligible.
- Projections use 5,000 paths (raised from 2,000 by the evaluation's registered precision rule).

Implementation layer
- Rebalancer: cash flows first, tolerance bands with a destination, whole units, minimum order, residual cash,
  estimated cost and a liquidity flag (both engines).
- NI 81-102 Appendix F risk rating of every mix.
- Opt-in suitability checks; the level policy is unchanged.

Evaluation and documentation
- A pre-registered evaluation (scripts/run_v3_evaluation.py; plan in docs/RESEARCH_LOG.md sections 9-11), examined
  in eighteen rounds before it ran; results in output/v3/results.json, the first run archived in output/v3_run1/.
- docs/DECISIONS.md: every design decision with its source, proof or test, and every examiner finding with its ruling.
- docs/paper: the research paper, built from the results by scripts/paper.
- docs/MODEL_CARD.md.
