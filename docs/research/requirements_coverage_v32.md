# Requirements coverage: PRD v3 (v3.2.0)

The team's PRD v3 (14 October 2026) added data rules (D1-D3), a fuller filtering and output section (F2, F3, X2-X5), the scope rule E4, and a cross-check of the prototype by Yasmin. Her summary was: "the UI flow and steps are good; it's just the open conversation flow and the explanation depth based on determined experience level which are the main things".

## How this was checked

1. **Audit.** Five audit lanes drove the current page headlessly, one per requirement group:
   - data and filtering;
   - depth;
   - conversation;
   - changes and the optimizer;
   - output, market context and responsible AI.

   An independent checker re-tested every "partly", "missing" or "untested" finding, plus a sample of "met" ones. The scripts and transcripts are in the session scratchpad.
2. **Design.** Three independent designs covered the two main points: a Claude-led interview, a local conversational flow, and depth by experience. A judge checked each design's claims against the code and wrote one specification.
3. **Build and test.** Everything was built from that specification and tested. The Node tests are in `web/test_converse.mjs`; the browser tests in `tests/ui/test_guided.py`.
4. **Cross-family review.** Gemini 3.8 Flash High read the three changed files and the PRD. It made five findings. Each was reproduced and then fixed, with a test.

**Note on Yasmin's cross-check.** She ran it on an older build. The "In this preview…" fallback she quotes is not in the current page, and several rows she marked "fails" were already fixed in v3.1. The last table below gives each row's state now.

## Requirements

| Id | Requirement | Where | Test | Status |
|---|---|---|---|---|
| D1 | Locked schema: fixed categories, true/false flags, decimal values | `web/data/ca.json` (MER as a decimal, booleans for flags) | test_v32_prd | met |
| D2 | An entry outside the locked lists is flagged, not accepted | Python: `robokit/classify.py` `locked_category_problem`, used in the `universe.py` screen. Browser: `robokit.js` `LOCKED`/`lockedCategoryProblem` in the Market constructor | test_v32_prd; test_converse (`lockedCategoryProblem`) | met (no fund in the current data is outside the lists) |
| D3 | Missing values stay blank, are never estimated, are checked before use | A missing fee shows as "fee not in our data", never 0.00%. The engine's `fee_unknown` check is shown. Missing dates are written as blank, not "NaT" | test_v32_prd (no "NaT"); browser: mix | met |
| F1 | Experience inferred internally after the first questions, or self-identified; never a label; consistent all session | `converse.js` `selfDepth`, `depthCues`, `classifyDepth`; `guide.js` `noteDepth`, `maybeSettleDepth`. The calibration can be skipped. The answers row reads "Explanations: Step by step", never a label | test_converse (depth); browser: inferred depth never shown, just learning | met |
| F2 | Screen by theme/region, maximum fee, currency and strategy style | Preferences: theme chips; region avoid and "Canadian stocks only"; a maximum fee (0.10%/0.25%/0.50% or typed "under 0.15%"); hedged/unhedged; CAD-only; active and factor style. Each typed clause is read separately ("no active funds" turns active funds off) | test_converse (preferences); browser | met |
| F3 | Tickers validated; unknown ones rejected with the closest matches; non-Canadian ones explained | `converse.js` `tickerLike`, `closestTickers`; `kb.js` `US_LISTED`, `NOT_CANADIAN`. US-listed tickers name the Canadian-listed funds on the same index, with an Add button | test_converse; browser | met |
| F4 | Change any earlier answer by typing or by Back; the shortlist updates right away | "← Back" on every question. "Noted · Change" chips. Typed changes for every answer. Changes are confirmed unless the person signalled one | browser: Back, Noted chips, confirm | met |
| O1 | Shortlist, covariance and locked constants give the weights | engine (unchanged) | engine suites | met |
| O2 | Weights sum to 100%, within the position cap, no shorts | Optimizer, and the Adjust screen: no fund except the cash fund above 50%. Whole percents shown add to 100 | browser: Adjust cap | met |
| O3 | The optimizer re-runs live when filters or the risk profile change | `liveRebuild`: no rebuild button. A "What changed" table shows weights, expected return and volatility before and after | browser | met |
| O4 | No valid solution: say so, never a wrong result | "No mix fits these choices", in plain words, with what to try | browser | met |
| C1 | Script order; a second chance when the self-rating and the drop answer disagree | STEPS (unchanged); RECON | browser | met |
| C2 | Goal/horizon and risk required; preferences skippable | A typed level request waits for the questions and the assessment. A required question's own answer is never mistaken for a skip ("none" at income) | browser | met |
| C3 | Risk disclosure whenever a shortlisted fund uses leverage or derivatives | `converse.js` `derivativeKind`/`leverageNote`. The notice covers the data's flags plus Hamilton "Enhanced", Harvest "Leaders Income", alternative and swap funds. Theme picks never use them | test_converse | met |
| C4 | Questions about a question are answered | `localAnswer` (the open question's Learn more for "what does this mean") | test_converse | met |
| C5 | Learn more at any point | Every step (including the second chance and fine-tune), the Adjust screen, each fund | browser | met |
| C6 | The assessment and its acknowledged disclosure come before the mix | Level requests wait; a changed risk answer reopens the assessment | browser | met |
| C7 | Any request for a personal recommendation goes to the disclosure | `ADVICE` patterns (including levels and weights asked as a personal decision), before any AI call | test_converse; browser (no model call) | met |
| E1 | Simple for beginners, more in-depth for the experienced | Each question has three wordings: plain with an example under each option, the approved standard text, and a short form showing the scoring rule ("How this is scored"). Results: plain reasons for beginners; for experienced viewers, full reasons, per-fund risk lines, four more figures and an open "Under the hood" panel. Term answers at three depths | test_converse (wording, terms, provenance); browser: depth tests | met |
| E2 | Terms defined the first time they appear | Definitions until a depth says otherwise, including in Claude's replies | browser | met |
| E3 | Market context from approved sources | Canadian readings (Bank of Canada, Cboe VIX via Yahoo). News is linked to BNN Bloomberg, CNN Business and Nasdaq rather than copied | browser | met (the sources are the team's examples; the team confirms the list) |
| E4 | Any ETF question; scope for non-investing; ETFs only for comparisons, definitions still given | `kb.js` `SCOPE`, `ETF_ONLY`; `converse.js` `etfComparison`, `isOffTopic`; new terms (GIC, mutual fund, index, distributions, dollar-cost averaging) | test_converse | met |
| X1 | The disclosure on every result; the person confirms decisions are their own | Every projection, the level dialog, the mix, Adjust; the export confirmation | browser | met |
| X2 | Export with three sections (mix with text and charts; reasoning; disclosure), each clickable | `summaryHTML`: three `<details>` sections, the allocation bar and the projection chart | browser | met |
| X3 | Level override: re-run, before/after weights, expected return and volatility, disclosure, logged | The "What changed" table; the banner; the session log | browser | met |
| X4 | Allocation adjustment: proportional, within the cap, return, volatility and level shown, disclosure, logged | Adjust (50% cap, volatility, weights in the log) | browser | met |
| X5 | Links to approved sources on market and industry trends | Market context and the "Industry news" tab | browser | met |

## User experience and responsible AI

| Row | Status |
|---|---|
| Beginner: guided flow, free text, consistent checkpoints | Met. Examples are shown under every option, and "why we ask" is visible. A checkpoint after the situation questions says what the answers mean, with no level number. |
| Intermediate: more information on request | Met. The approved wording is shown, with "Why we ask", "Learn more" and "More detail". |
| Experienced: tickers, filters and free text; play with mixes; expected return and risk | Met. Shortcuts appear once. Several answers can be typed in one line. Each question shows the rule behind it. The extra figures and Under the hood are on the results. |
| Same flow for everyone; only explanation and control differ | Met. A browser test checks that the same answers give the same level and the same weights at every depth. |
| Non-directive; no labels; honest about uncertainty; human-reviewed boundary | Met. Claude's replies are held back if they contain a directive, a label, a guarantee, or a level before the assessment (`outputIssues`), or a number not on the page. |

## Yasmin's cross-check, now

| Her row (older page) | Now |
|---|---|
| Depth of Q&A varies with experience: partly | Met (E1 above). The options stay the same by design; the wording, examples, rules and results differ. |
| Name tickers directly: fails | Met (F3). |
| Zero matches loosen one filter and explain: not tested | Met. A typed "yes" or "no" works too. |
| Change an earlier answer and re-filter live: fails | Met (F4, O3). |
| Full script but open conversation: partly | Met. See the next section. |
| Core required, preferences skippable: fails | Met (C2). |
| Learn more at any point: partly | Met (C5). |
| "What should I actually do?" redirected: fails | Met (C7). |
| Explanation depth consistent all session: fails | Met (F1, E1, E4). |
| Click into ETF options and ask freely: fails | Met (Learn more answers from fund facts and holdings; Claude when connected). |
| Non-directive (no tag): partly | Met. |
| No guarantees; the past-performance line: fails | Met. |
| Edge cases tested: not tested | Met. Browser tests cover conflicting answers, zero matches and advice requests. |

## The open conversation (the reviewer's first point)

**Reading.** Each message is read as a whole, clause by clause (`readTurn`):

- Every answer in it is taken, in any order: a story typed on the home screen becomes the goal, timing, amount and debt.
- An answer is never given to the wrong question: "no debt" never answers the emergency fund, and a debt amount is never the amount to invest.

**Recording.** Every value goes through one gate (`admit`):

- Only option values are recorded.
- A risk answer said in passing is highlighted on its own card and checked there with the person's own numbers.

**Replying.** Each turn says back what it understood, with "Noted · Change" chips:

- A vague reply gets a two-choice follow-up ("long term": 10 to 19 years or 20+?).
- A reply that is not understood is put another way, then explained. "I didn't catch that" is gone.
- A side question is answered, then the page asks "Back to building your portfolio?" and names the next question.

**Without Claude.** All of this works for everyone.

**With Claude connected:**

- Claude answers in its own words, at the person's depth.
- Its replies are checked against the page's numbers and the fixed rules.
- Every answer is still recorded by the page's code.

The Claude-led interview (phase 3 of the specification) is not built. It needs a live rehearsal on the owner's account first.
