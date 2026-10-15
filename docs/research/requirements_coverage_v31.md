# Requirements coverage of the guided page (3.1.0)

The team's Requirements Plan (Phase 0), conversation script (draft v1) and prototype review (Robo-Kit Prototype
Review, sections 1 and 2) against the guided page: `web/index.html`, `web/guide.js` (screens and flow),
`web/converse.js` (typed text and answers without AI), `web/kb.js` (fixed wording), on the engine `web/robokit.js`.
Each row names where the requirement is met and the test that shows it. "Browser" tests are in
`tests/ui/test_guided.py`; "logic" checks in `web/test_converse.mjs`; "engine" tests in `tests/test_v31_guided.py`.

## Requirements Plan

| Id | Requirement | Where | Test | Status |
|---|---|---|---|---|
| F1 | The user states their investing experience, which sets how much each step explains | Calibration step EXP (the script's wording, kb.js CALIBRATION); depth drives the "Why we ask" line, suggested questions, first-time definitions and acknowledgements (guide.js stepCard, bot, ackFor, introFor) | Browser: typed answers; a beginner's mix shows reasons and definitions | met |
| F2 | Narrow the list by theme/region, cost limit, currency and strategy style | Preferences step (guide.js applyPrefs, themePick): theme focus adds an eligible fund, "avoid" leaves a default fund out, lowest cost swaps each slot, hedging, ESG, index-only or open to active, larger funds only | Browser: zero match | met |
| F3 | Name tickers directly, added without re-filtering | Ticker step and at any point ("add XEQT", a ticker typed in capitals); refused funds say why (guide.js addPicks, converse.js findTickers, parseCommand) | Browser: tickers; logic: tickers | met |
| F4 | Zero matches: loosen one filter at a time, explain which and why | guide.js themePick and zeroCard: names the filters, offers to drop one (fees, then size, then index-only), asks first | Browser: zero match | met |
| F5 | Change an earlier answer and re-filter live | "Your answers" with Change links on the mix and from the assessment; typed changes ("actually change my risk to high"); a changed answer rebuilds (guide.js goChange, applyCommand, advance) | Browser: changing an earlier answer | met |
| O1 | Shortlist + covariance + locked constants -> weights by risk profile | Engine buildPortfolio on the shortlist (default funds after preferences, plus own picks) at the suggested or chosen level | Engine tests (tests/test_v3_*.py), unchanged | met |
| O2 | Weights add to 100%, respect the cap, no shorting | Engine constraints; stated under "Why this mix" | Browser: weights add to 100% | met |
| O3 | Runs live on the user's filters and risk profile | build() calls the engine in the page (worker) on each change | Browser tests | met |
| O4 | If the optimizer can't solve it, say so clearly | renderMix error state: the engine's message, "Rather than show a number that might be wrong, Robo-Kit shows nothing", ways out | Engine tests of refusals | met |
| C1 | Opening, literacy check, goal/horizon, risk check with a second chance, preferences, ticker entry | kb.js OPENING; STEPS in guide.js; RECON uses the engine flag F_self_vs_drop | Browser: second chance; engine: F_self_vs_drop | met |
| C2 | Core questions required; preferences skippable | Required steps answer "don't know" with the script's "even a rough guess is fine"; optional steps (fine-tune, preferences, ticker) have Skip | Browser flows | met |
| C3 | Leverage/derivatives disclosure whenever a shortlisted fund uses them | converse.js leverageNote on the shortlist, own picks, refused tickers, the mix and Learn more | Logic: leverage note | met |
| C4 | Market context as information with a question back | Tagged-theme note after preferences and the market-context card on the mix, each with "Keep going as planned" | Visual check | met |
| C5 | "Learn more" at any point | "Learn more" chip on every step, suggested questions, terms that explain themselves, free-text questions with "Back to building your portfolio?", Learn more on every fund | Browser: question mid-flow | met |
| C6 | End with portfolio, reasoning and a recap | Mix screen: one line of reasons per fund, "Why this mix", "Before you go" (converse.js recap) | Browser: beginner flow | met |
| C7 | "What should I do?" always redirected to the disclosure | converse.js isAdvice before any answer or AI; the script's redirect plus the disclosure | Browser: advice with and without Claude; logic: 10 phrasings | met |
| E1 | Explanation depth matches the literacy check all session | Depth stored once, changeable, applied to every later message | Browser | met |
| E2 | Jargon defined the first time | Beginners: definition under the first message that uses a term (converse.js termsIn); everyone: terms are tappable | Visual check | met |
| E3 | Market context from pre-set sources, separate from the logic | core.json context (GDELT headlines, VIX, geopolitical index), read-only | Data tests | met |
| P1 | Disclosure on every result; confirm decisions are the person's own | Assessment checkbox; disclosure on the mix, adjust and summary; export needs the confirmation | Browser: export | met |
| P2 | Download or share the mix (text and visuals), reasoning and disclosure | Summary dialog: download as HTML (artifact downloads capability) or copy as text; includes the bar, table, reasons, session log, disclosure | Browser: export gate | met |
| P3 | Adjust the risk level, with a "not calculated for you" disclosure | Level picker on the mix; above the suggestion needs a tick first; banner on the chosen level | Browser: higher level | met |
| P4 | Adjust the mix, risk level updates, with a disclosure | Adjust screen: per fund and per class, behaves-like level, expected return before and after, warning and tick above the suggestion | Browser: adjust | met |
| P5 | Links to sources for market/industry trends | Industry news tab links each headline; holdings link the issuer source | Visual check | met |
| U1 | Consistent disclosures; re-confirm before export | as P1 | Browser: export | met |
| U2 | Click into ETFs, change answers with disclosures, ask freely, prompted to learn more | Learn more per fund, Change links, free text everywhere, chips | Browser | met |
| U3 | Beginner: chat interface, guided option, checkpoints | Chat with tap answers, suggested questions, acknowledgements, assessment checkpoint | Browser | met |
| U4 | Intermediate: free-text questions, more on request | "Why we ask" folded, Learn more on request | Browser | met |
| U5 | Experienced: tickers, immediate impact on expected return, free-text answers, filters, own pace | Several answers in one message, tickers anywhere, preferences, optional steps skippable, expected return on adjust | Browser: typed answers, adjust | met |
| U6 | The user sees each step (filtering, then optimizing) | Shortlist step before "Calculate my portfolio"; "Filtering done; optimizing your shortlist" while building | Visual check | met |
| U7 | Same flow for everyone; explanation and control differ | One STEPS list; depth changes wording only | Code review | met |
| NF | Fast for a demo; no personal data; no credentials; plain language; logging | No name asked; nothing stored; session log on the mix and in the summary | Browser | met |
| RAI | Non-directive, explainable, same rules, honest, past-performance line, privacy, fixed advice boundary, edge cases tested | Wording in kb.js; "Past performance is not reflective of future performance." on results; edge cases are browser tests | Browser and logic tests | met |

## Prototype review items

| Item | Fix |
|---|---|
| Yasmin: "$X is your inputted money" on the range cards; remove the crisis callout; "Note the differences across low and high points" | Cards note names the amount and what was put in; the ten-year cards no longer show the 2008 line; the note ends with that sentence |
| Yasmin: make the chat work on Learn more | Learn more answers from fund facts and issuer holdings without AI ("What's an example of a stock in this ETF?" on ZAG: it holds no stocks, its largest holdings are Government of Canada bonds) |
| Monamee: typed text on the start page ignored; 14 questions too long | Typed text is read for facts (goal, horizon, amounts, risk, experience) and acknowledged; the core is about ten taps |
| Monamee: "I'm just learning" acknowledged | Acknowledged, and the withdrawal question is skipped for it |
| Monamee: share of savings hard for beginners | Moved to the optional fine-tune |
| Monamee: range cards hard to understand | Plain note on how to read them; "Not sure, skip"; Learn more explains with the person's dollars |
| Monamee: no chance to ask or learn more | Learn more on every step, suggested questions, free text answered, then "Back to building your portfolio?" |
| Monamee: "Novice investor" tag; level not explained; no way back | No label; "What level N means" in dollars; "Change an answer" in the assessment and on the mix |
| Monamee: answer any question ("what is XIC") | Fund questions answered from facts; Claude when connected |
| Monamee: beginners don't know what to ask | Suggested questions and tappable terms |
| Anna: entry text ignored | as above |
| Anna: adjusting one fund raised another | Explained on the screen; the funds that made room are highlighted |
| Anna: only the first experience choice remembered | A changed calibration is acknowledged and applied to everything after it |

## Found by driving the page

A reviewer worked through the page as different people would (typing instead of tapping, changing answers late,
asking mid-step, a phone screen). Each item below was reproduced, fixed, and has a test.

| What happened | Fix | Test |
|---|---|---|
| "$15,000" was read as $15 | Thousands separators are part of the amount, in answers and in "change the amount to ..." | test_converse; browser: amounts with commas |
| "Low risk but a steady job" set both answers from the whole sentence | Each fact is read from its own clause; saving for retirement is a goal, not a pension | test_converse |
| Words like "mix", "rate", "tech" matched tickers | Everyday words count as tickers only in capitals or after add/remove, never after "my", "the", "this" | test_converse; browser: bare tickers |
| A typed question sat unseen until Claude replied; a message typed while waiting was lost | The question and the thinking dots show at once; the box keeps text typed while busy | browser: question shows at once |
| Two filters with no match showed one card | One card per filter | code review |
| Going back after a changed answer showed the old mix; acknowledging the assessment reset a chosen level | A changed answer offers the rebuild; a chosen level is kept (within the emergency-fund cap) and the message says so | browser: chosen level survives |
| "No fund is above 50%" next to a cash fund above 50% | "No fund except the cash fund is above 50%" | code review |
| The summary left out "not calculated for you" | The summary and its download carry the same sentence as the screen | browser: chosen level survives |
| Adding a fund already on the shortlist asked for a rebuild | Only a real change asks | browser: shortlist accepts "no" |
| "What is volatility?" inside a fund's Learn more answered about the fund | Definition questions get the term; questions about the fund stay on the fund | test_converse; browser: Learn more defines a term |
| "Yes" did not confirm a suggested horizon; "no" at the shortlist was not understood | Both understood | browser: shortlist accepts "no" |
| Tickers typed at an early step were ignored | Added at any step; the question is asked again | browser: bare tickers |
| "Yes, no debt" was read as one answer | Each half from its own clause | browser: amounts with commas |
| Adjust opened on the optimizer's estimate, not the measured mix | Adjust measures the built weights first, so an untouched mix never warns about itself | browser: adjust opens on the measured level |
| The engine's plural "dropped" note showed | Hidden like the singular one | code review |
| "Change an answer" from the assessment left no way back | Offers "Back to building your portfolio?" | browser: closing the assessment |
| The three tabs overflowed a 360-pixel screen | Tabs scroll and tighten on narrow screens | browser: tabs fit a phone |
| The log lower-cased "I" in answer labels | Only the first letter is lower-cased; the ticker step is labelled "Tickers" | code review |
