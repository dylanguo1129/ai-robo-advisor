# Robo-Kit v2.1: round 2 ranked fix list

Status: COMPLETE

Sources:
- Seven persona runs: p1 Mei (first-time investor), p2 Jordan (level cap), p3 Priya (DIY), p4 Tyler (US, phone), p5 Linda (retiree), p6 Daniel (analyst), p7 Sam (accessibility). p7's JSON reached me cut off, so its findings and metrics come from its written report.
- Two code reviews: **R-E** (engine: `robokit/`, tests, scripts) and **R-W** (web: `web/`). Every R-E and R-W finding below was reproduced by running it.
- My own spot-checks against the code. Items marked *(code checked)* have the cited lines confirmed.

Order: anything that **shows a wrong number, loses the person's work, or breaks the level policy** comes first (Tier 1), sorted blocker, then major, then minor. The other majors, minors and polish follow.

---

## Tier 1: wrong numbers, lost work, level policy

### Blockers

**F01 · blocker · Tapping a tray level bypasses the savings/debt gate while the self-check is paused**
- Evidence: R-W. After answering A2 "No" (gate_cap 2), then "Continue later", tapping level 5 in the tray built a level-5 mix with no sheet. The button's aria-label said "Locked for now" and the tray read "Your choices, level 5". The chat path (toolPropose) does lock it, so the two paths disagree. *(code checked: `chooseLevel` checks gates only when `p.status !== 'incomplete'`.)*
- Fix: Enforce `gate_cap` as soon as A2 or A3 has an answer, whatever the profile status. Route the tray, chooser, chat preview and resume through one `levelStatus(level, profile)` function that returns `ok | explore | locked`.
- Files: `web/app.js` (chooseLevel ~744-751, toolPropose)

**F02 · blocker · A finished gated check leaves the build at a locked level the person never chose**
- Evidence: R-W. The default level is 3. The check finished with A2 "No" (suggested 2), then "Continue later". Result: st.level 3, the tray tags 3 "Locked for now", and the summary says "suggested 2 · chosen 3" although the person never chose 3.
- Fix: On every rescore (answer, close, resume), if `st.level > gate_cap`, move to gate_cap and add a visible note ("Level set to 2: your savings/debt answer caps the build at 2"). Never call an untouched default "chosen"; say "reference level 3".
- Files: `web/app.js` (answerQ, closeCheck ~520, summary line), `web/strings.js`

**F03 · blocker · The explore state drifts, so a level above capacity loses its "above your self-check" label and its sheet**
- Evidence:
  - R-W: With capacity 2, exploring 5 and then tapping 4 left `explore.level = 5` while st.level was 4. The tray read "Level 4 · your self-check suggested 2" with no label. "Copy summary" said "exploring 4" while pageState told the AI "explore level 5".
  - R-W: "Start over" sets explore=null but keeps level 5. After the same answers, level 5 shows with no label and no sheet.
- Fix: Stop storing the label; derive it on every render (`above = st.level > max(within_check)`). Record consent per (level, profile hash). On a profile change, Start over or resume, recompute: if the level is above the check and has no consent, show the label and reopen the sheet on the next build, or drop to the suggested level with a note.
- Files: `web/app.js` (chooseLevel/applyLevel 744-760, Start over ~740, resume, pageState, mixSummary)

**F04 · blocker · Holding BITO silently removes the 2008 and 2011 crisis replays and halves the headline loss**
- Evidence: p4. Holding at least 5% BITO removed the 2008 and 2011 rows from the crisis list and the one-fund table. The plain-words headline switched from 2008 (−53%, −$2,641) to 2022 (−24%, −$1,200) with no note, while the chooser still showed −$2,641. *(code checked: `web/robokit.js:386` `continue` skips any scenario with a non-estimable fund; `robokit/stress.py` does the same.)* This is the same class of bug as round 1's SCHD case.
- Fix: Never drop a scenario silently. Use a crypto stand-in series, or keep the row with the fund marked "not estimable" plus a note ("2008 and 2011 not shown: BITO has no data or stand-in for that period"). Keep the headline on the worst scenario ever shown for that level, or say why it changed.
- Files: `web/robokit.js:386`, `robokit/stress.py`, `web/app.js` (plain-words headline, one-fund table), `web/strings.js`

**F05 · blocker · "take out -1500 a month" becomes +$1,500 a month; an unreadable monthly amount becomes 0**
- Evidence:
  - p5: The setup card showed "+$1,500 CAD/mo" and PAGE STATE monthly:1500. The setup label never says that a minus sign means a withdrawal. *(code checked: `monthlyRx` at app.js:51 has no sign and no take-out verbs; app.js:575 always prints "+".)*
  - R-W: The setup Monthly field turns "500/month", "$500 a month" and "−500" (Unicode minus) into 0 with no message (app.js:600).
- Fix: Read a leading "-" or "−" and verbs such as take out / withdraw / draw as negative. Show "−$1,500 CAD/mo (taking out)". Relabel the field "Monthly add or take out (use − to take out)". Make parseAmount accept "/month", "a month" and "−". Show an error, never 0. Update the "From your message" chip when the field is edited (p5).
- Files: `web/app.js:49-56, 575, 600`, `web/strings.js:26`

**F06 · blocker · Any later chat message with a number is treated as the opener and rewrites the amount, market and check**
- Evidence:
  - R-W: `first = !this.st.opener` becomes true only after a message yields facts. "Is a fee of 0.2% on 1,500 a year a lot?" changed the amount from $50,000 to $1,500 and reopened the finished check. "How much would a US 401k fund of 20,000 have lost in 2008?" switched CA to US and set the amount to $401,000. *(code checked, app.js:307-329)*
  - p3: A comparison question containing the word "mix" opened the check uninvited (build regex, app.js:328).
- Fix: Mark the opener as consumed on the first user message, facts or not. Never apply opener facts once any answer exists or the user has changed anything. For an amount in a later message, offer a chip ("Use $1,500 as your amount?") instead.
- Files: `web/app.js:303-329`

**F07 · blocker · The "Every number checked" footer vouches for invented numbers**
- Evidence: p6 probe. "Dividend yield near 2.8%" and "the Bank of Canada will cut rates 2 times next year" were accepted and shown with "Every number checked against Robo-Kit's tools". Plain integers of 12 or less are skipped. Any number within tolerance of any of the 559 values in the result object passes: 4 of 14 random one-decimal percentages did. *(code checked: validate.js:45-64)* This is the mechanism behind "numbers only from code".
- Fix: Match only against this turn's tool results plus a short whitelist of page-state fields. A percentage must match a percentage field. Treat "N times / cuts / hikes" next to a future verb as unsupported. Drop the footer when the reply made no tool call, and reword it to "Numbers matched to Robo-Kit tool results".
- Files: `web/validate.js:45-64`, `web/assistant.js` (footer), `web/strings.js`

### Majors

**F08 · major · "Keep level N" on the explore sheet moves a person down to the suggested level**
- Evidence: p6. At level 4, tapping 5 opened the sheet with the primary button "Keep level 3"; pressing it moved the mix to 3. *(code checked: app.js:789-790 applies `s = p.suggested_level`.)*
- Fix: Label it "Stay at level {st.level}" and make it a no-op. Compare the target with the current level, and show the suggested level only as context.
- Files: `web/app.js` ~780-790, `web/strings.js:47,131`

**F09 · major · Reopening the chooser pre-selects the suggested level, not the current one**
- Evidence: p1, p2, p6 and p7 all hit this. On level 5, "Change level" or "Review 12 answers" showed row 4 pressed and a primary "Use level 4". One tap downgrades. `applyLevel` sets `check.pick = null`.
- Fix: Default the pick to st.level and tag it "Current" (keep the "Suggested" tag on its own row). The primary button reads "Keep level 5" or "Done" until another row is tapped.
- Files: `web/app.js` (applyLevel ~756, renderCheck result/ladder), `web/strings.js`

**F10 · major · The withdrawal-length (B2) answer is still scored after the goal changes to "Building wealth", and MCP never learns the skip rule**
- Evidence:
  - R-W: With goal Retirement and B2 "once", switching the goal to wealth left capacity at 4 instead of 5. The review still lists B2, and its Change link opens "0 of 9". *(code checked: cleanAnswers, app.js:506, ignores applicable().)*
  - R-E: `get_questions` strips `skip_if` and `optional` (tools.py:82). So the MCP chat asks B2 to wealth-goal users and gives them capacity 2 or 4 where the page gives 3.
- Fix: Filter cleanAnswers and the review list through applicable(). Pass skip_if and optional through get_questions and document them in AGENT.md S3.
- Files: `web/app.js:504-506`, `robokit/tools.py:82`, `AGENT.md`

**F11 · major · The chooser and sheet show a reference mix, not the mix that gets built**
- Evidence:
  - p6: The sheet said the level-5 bad year was $126,795; the built mix showed $123,060, a $3,735 gap at the moment of consent.
  - p1: 2008 −$19,220 vs −$19,291; 2022 −$6,335 vs −$6,455.
  - p2: −$15,376 vs −$15,433.
  - p5: Level-3 bad year $273,780 vs $277,860.
  - Cause (R-E, p6, *code checked*): `ladderRow` builds reference funds on $10,000 with nBoot 100 and no picks, swaps or minimums, then scales. No tool returns these rows, so the guide cannot reconcile them.
- Fix: Build ladder rows from the person's own request (picks, swaps, minimums, same nBoot and seed). Until then, label the rows "reference mix at level N; your mix may differ slightly", show the built figure next to the current row, and add `levels` to current_mix.
- Files: `web/robokit.js:440-441`, `web/app.js:682, 780-781`, `web/assistant.js` (current_mix), `web/strings.js`

**F12 · major · Self-check scenarios and the headline range ignore monthly adds and withdrawals**
- Evidence:
  - p5, at −$1,500/mo: the one-year question showed $300,990–$317,880 and the ten-year question $374,468–$452,466. The mix headline said the money "might end the year between $300,990 and $317,880", while the same card's 10-year middle was $201,276.
  - p4: The ten-year options covered $5,000 alone, while the mix with +$300/mo had a middle of $63,506.
  - p6: +$1,000/mo left out ($187k–$226k vs a median of $430,804).
- Fix: Include the monthly flow in the scenario ranges and the headline. If that is not possible, label them "for your $X alone, before monthly adds/withdrawals". For someone withdrawing, show the year-end value after 12 withdrawals.
- Files: `web/app.js:628-629` (scenario options), renderMix keynums, `web/robokit.js` (projection), `web/strings.js`

**F13 · major · For a retiree, the flow hides how long the money lasts, and the horizon defaults to 10 years**
- Evidence:
  - p5: The suggested level 1 lasted 25 years in 29% of paths, against 81% at level 3. None of the result, chooser, sheet or proposal preview shows this. The default Years=10 said "lasted all 10 years in 100% of paths". current_mix calls 25-year results `ten_year_outcomes`, and PAGE STATE has no years field.
  - p1: Retirement plus "20+ years" still gave a 10-year path, goal null, withdrawal null, and "Retirement" appears nowhere on the mix.
- Fix: Seed Years from B1/B2 (20plus or 10plus → 25). When monthly < 0, add a "money lasted N years in X% of paths" column to the chooser, sheet and proposal preview, and move the withdrawal line up near the headline. Add a goal line ("Goal: retirement, taking money out in about 20 years"). Rename the field `horizon_outcomes` with a `years` key, and add years, goal and withdrawal to PAGE STATE.
- Files: `web/app.js` (years default, renderMix, ladder, sheet, card-prop, pageState), `web/assistant.js`, `web/robokit.js` (ladderRow projection), `web/strings.js`

**F14 · major · The amount parser reads "401k" as $401,000 and takes the largest number, such as a salary**
- Evidence: R-W. `parseOpener('I have 25k in my 401k')` gives 401000. "I earn 90k a year and have 15k saved" gives 90000. `Math.max` wins (app.js:55). The same function already treats `\b401k\b` as a US signal.
- Fix: Exclude 401k/403b/457 tokens from the money patterns. Drop numbers next to earn / make / salary / a year. Prefer numbers near have / saved / invest / put in. If it is still ambiguous, leave the amount empty.
- Files: `web/app.js:45-56` (and add these cases to `web/test_robokit.mjs`)

**F15 · major · Whole-unit rounding leaves a pick at 0 units and a fifth of the money in cash, unflagged**
- Evidence: p4 ($5,000 US). QQQ "9.3% · $466 USD · 0 units", then 4.5% · $225 · 0 units. Cash left reached $1,025 (20%). The risk headline uses target weights, not what can actually be bought.
- Fix: Flag any row with units = 0, or where units × price is more than 10% away from the dollar amount ("below 1 unit at $X"). For US users, mention fractional shares or offer a toggle. State the cash share next to the headline.
- Files: `web/app.js` (renderMix funds table), `web/robokit.js` (units), `web/strings.js`

**F16 · major · In own-weights mode, a shelf swap shows the new fund but the mix keeps the old one**
- Evidence: p3. Swapping XIC for VCN: the dropdown shows VCN, but the holdings and copied list still read "XIC Equity 20.0% · $24,000 · 415 units". The row is relabelled "Equity" and moves into the collapsed "no weight at this level" section, with no message.
- Fix: When fixedWeights is set, move the old ticker's weight to the new ticker, keep the row in place, and say "VCN now holds XIC's 20%".
- Files: `web/app.js:961, 974`

**F17 · major · In own-weights mode, "Hold at least" for a not-held pick is stored and ignored, and the note blames the optimizer**
- Evidence: p3. XAW at 5% was stored in minimums; nothing changed and no message appeared. R-E confirms the engine note "the optimizer gave it no weight. You can set a minimum…" appears even though no optimizer runs (engine.py:390).
- Fix: In own-weights mode, replace the control with "Give XAW a weight", which opens the weights grid with XAW included, and reword the note in both engines.
- Files: `web/app.js:922`, `robokit/engine.py:390`, `web/robokit.js` (notes)

**F18 · major · "Let the model decide" wipes own weights with no undo**
- Evidence: p3. XUU 40 / XEF 20 / XIC 20 / ZAG 20 was replaced immediately. Reopening the grid prefilled model weights, so all 8 fields had to be retyped.
- Fix: Keep `st.mix.lastFixedWeights`, prefill from it, and offer an Undo toast.
- Files: `web/app.js:916`

**F19 · major · Applying an older chat proposal throws away manual edits made after it**
- Evidence: R-W. The AI proposed adding XEG.TO; the person then added ZEB.TO by hand and tapped Apply on the older card. Satellites became ['XEG.TO'], and ZEB.TO disappeared silently (`st.mix = change.mix`, app.js:1130).
- Fix: Store a proposal as a diff (add, remove, level) and apply it to the current st.mix. Alternatively, mark earlier cards "Out of date" whenever st.mix changes.
- Files: `web/app.js` ~1126-1136

**F20 · major · Cancelling the explore sheet from a chat proposal still writes the proposed funds, and the card goes dead**
- Evidence:
  - R-W: After Explore level 5 and then Escape, st.mix.satellites held XEG.TO while the visible mix was unchanged. The next rebuild brings in the declined fund. *(code checked, app.js:1134)*
  - p2: The card is disabled with no outcome line.
  - p5: "Not now" also leaves no status line.
- Fix: Apply `change.mix` only inside the sheet's "Explore anyway" callback. Keep the card live until the sheet resolves, then add a status line ("Kept level 4" / "Exploring level 5" / "Not applied").
- Files: `web/app.js:1134`, `web/strings.js`

**F21 · major · The setup screen re-renders and wipes a typed amount and monthly, and focus drops to the page**
- Evidence: R-W. Typing 75000 / 800 and then tapping US reset the amount to 10000 and cleared Monthly. A background "ladder" event about 1.65 s after load wiped a value typed at 0.4 s. document.activeElement became BODY.
- Fix: Copy the field values into st before any re-render, or patch only the ladder area. Restore focus to the same field.
- Files: `web/app.js:212, 274`

**F22 · major · The own-weights editor rejects its own prefill, leaves out added picks, and fails nearly silently**
- Evidence:
  - R-W: The unedited prefill totals 99% or 101% (CA levels 1 and 4, US levels 2-5) and is refused.
  - p3: Added picks such as XAW have no input.
  - p6: At 105% the button stays enabled and only recolours text. At 100% it still says "It must add up to 100%".
- Fix: Include satellites and picks at 0. Round the prefill so it sums to 100 (largest remainder). Disable the button until the total is 100, put the total in an aria-live region, and word it "Adds up to 100%" when valid or "Total 105%: take off 5 points" when not.
- Files: `web/app.js:917, 971-974`, `web/strings.js:61`

**F23 · major · Own weights that are almost all cash crash the Python engine and report "level 0.5" in JS**
- Evidence: R-E. `fixed_weights={'CASH.TO':1.0}` gives lvl5 = 0.5. Python rounds that to 0 and raises KeyError at `LEVELS[0]`, which escapes tools.call into the CLI and the MCP server. JS says "like level 0.5 of 5".
- Fix: Clamp the implied level to [1, 5] in both engines, and catch KeyError in tools.call.
- Files: `robokit/engine.py:386, 462-469`, `web/robokit.js` (the same step), `robokit/tools.py`

### Minors

| ID | Title | Evidence | Fix | Files |
|---|---|---|---|---|
| F24 | One card shows the fee rate as both 0.13% and 0.12% | p1, p2 (fee_rate 0.00125); p3 and p6 saw agreement at other amounts. *Code checked:* the headline formats the 5-dp-rounded `weighted_mer` and the fee-drag check formats raw `wmer`, so it is double rounding at 0.125% | Format one stored value everywhere (or show 0.125%) | `web/app.js:883`, `web/robokit.js:692`, `robokit/engine.py:600` |
| F25 | The fee total quietly guesses a missing fee, and the note describes it wrongly | p3: $152 = 0.127% × $120k including XUU's $48k; the known funds alone are about $91; the note says "cover the other funds only" | Add XUU's MER to the data; say "assumes XUU costs the average of the others" or show the known-funds total | fund data (universe build), `web/robokit.js` fee averaging, `robokit/engine.py` weighted_mer |
| F26 | Switching market relabels the amount from CAD to USD without converting it | p3: $120,000 CAD became "$120,000 USD" with no note; the untouched US mix is headed "Your choices" | Note "Amount kept as 120,000; now shown in USD (not converted)"; head an untouched market "Reference mix" | `web/app.js:264-275` |
| F27 | The withdrawal "lasted" count includes the month that came up short | R-E: amount 1195, −10/mo, zero returns gives chance_lasts 1.0 and p10 120, where 0.0 and 119 are correct; JS agrees with Python | Count a month only when its withdrawal was fully paid | `robokit/projection.py:91`, `web/robokit.js` project |
| F28 | Withdrawal plans report negative "invested" and a 0% chance of ending below it | R-E: invested −2,390,000 and prob_below_invested 0.0 while every path runs out | Leave these fields out for withdrawal plans, or define them properly | `robokit/projection.py:97, 118`, JS twin |
| F29 | A fund whose data starts in an episode's first month is marked "estimated" | R-E: VBU.NE in the default CA level-3 oil-crash row has 19 of 19 real months; 92 funds are affected | Compare against the first month inside the window (`>` vs `>=` on the return month) | `robokit/stress.py:84`, `web/robokit.js:388` |
| F30 | compare_one_fund drops the "estimated" and "stand_ins" flags | R-E: ZGRO's 2008 −$14,805 is a back-fill with no marker, on the page too | Carry the flags through and mark the row on the page | `robokit/engine.py:662`, `web/robokit.js` oneFund, `web/app.js` one-fund table |
| F31 | The crypto warning says "capped at a small weight" while own weights hold 50% | R-E: FBTC.TO at 50% | In own-weights mode, state the actual weight | `robokit/engine.py:611`, `web/robokit.js` checks |
| F32 | Headline volatility and the ranges use different windows under one label | p6: headline 8.6% / 10.5% from 2011-2026; ranges from 2004-2026 give 8.9% / 11.3% | Show the long-history figure, or label it "(2011-2026)" | `web/app.js` tray/mix/one-fund rows, `web/robokit.js` stats |
| F33 | An all-in-one ETF is counted as 100% global and 100% foreign currency | p6: XEQT gives "About 57% exposed", with no overlap note next to VFV/XIC | Split by stated allocation, or flag it "counted as global, not looked through"; add an overlap note | `web/app.js` (where-the-money-is, currency line) |
| F34 | Fund cards keep stale mix figures and actions | p6: ZAG card still says "In the mix · 21.1%" (now 20.4%); p7: "Add" on a held XEQT flips to "In the mix" and does nothing | Update the badge from the live mix, or timestamp it; disable Add when held | `web/app.js` cardFund |
| F35 | Changing Years reshuffles the one-year range, bad year and losing-year odds with no message | p5: $300,990–$317,880 became $301,680–$318,030; bad year $296,100 became $296,880; 1 in 12 became 1 in 13 | Fix the resampling seed per mix, independent of horizon, or show "ranges re-simulated" | `web/robokit.js` projection seed, `web/app.js` |
| F36 | The market context card mislabels data (unchanged since round 1) | p5: "USD in CAD, 12-month change" shows the rate 1.4164; flags dated 2026-09-30, after today; raw ISO fetch stamp; war question answered with tech headlines | Show the 12-month % change; clamp as_of to data dates; friendly fetch time; add a world/geopolitics headline topic | `robokit/data/context.py`, `robokit/signals.py`, `web/app.js` cardContext |

---

## Tier 2: other majors (flow, phone, accessibility)

**F37 · major · The phone tray is wider than the screen, so level 5 is off screen**
- Evidence: p2, p4 and p5 all hit this at 375 px. The tray measures 449-488 px, and the level-5 segment and the chevron sit past the right edge. The × overlaps the peek text, and the sheet opens scrolled 87 px sideways. It is worse at A+.
- Fix: Use `minmax(0,1fr)` for the tray grid. Give the fieldset and `.tray-two` children `min-width:0`. Ellipsize or wrap `#tray-toggle` and set overflow-x:hidden. Test that scrollWidth equals clientWidth at 320-375 px and at A+.
- Files: `web/index.html` (#tray rules 361-402, .tray-two 395)

**F38 · major · The "why this level" list contradicts the level it explains**
- Evidence:
  - p1 and p2: Answers that "allow up to level 5" are listed under "these answers set that", next to a "points to level 3" row, for a level-4 result.
  - p2: The cushion wording mentions "other cushions" when none are listed, and "the lower of the two" appears when both are equal.
  - p4 and p5: Rows are circular ("Range for level 1 points to level 1") and do not echo the tapped option.
  - p1: The sheet has one "Change that answer" button for four listed answers.
- Fix: Split the list into "set your limit" (only the answers that lowered the level, each with its own Change link) and a muted "also considered" line. Echo the tapped option ("You picked $300,990 to $317,880 → level 1"). Choose the cushion wording by count. Say "Both point to level 5" when the two are equal.
- Files: `web/app.js` (bindingHTML, sheet ~785), `web/strings.js` (binding and effect strings)

**F40 · major · The collapsed phone tray keeps 15 invisible tab stops, and the open tray does not hold focus**
- Evidence: p7 at 640 px. Tab runs through levels 1-5, the amount, monthly, 5 fund rows, Show the full mix, Edit funds and Reset, all off screen (WCAG 2.4.11). A focused Return could change the level unseen. When the tray is open, Tab escapes to the header behind it.
- Fix: Make the tray body `inert` while collapsed on narrow screens, leaving only #tray-toggle focusable. When it is open, trap focus or make main inert.
- Files: `web/index.html:495-506`, `web/app.js:216` (toggleTray)

**F41 · major · Focus falls to the page body after 7 actions, and only self-check steps are announced**
- Evidence: p7. Focus is lost after Start over, Explore anyway, Use level, Apply minimum, Edit funds, Add, and the note link. After "Use level 4", the next Tab lands 40 stops above the mix. The #announcer still read "Question 10 of 10" after the mix appeared (also seen by p4, p5 and p6).
- Fix: After an in-place re-render, refocus the same control by data attribute. After Explore or Use level, focus the mix heading (tabindex=-1). Announce mix, level and edit changes ("Mix updated: level 5, bad year $41,020 CAD"). Clear the announcer when the check ends.
- Files: `web/app.js:294, 561, 758-761`, renderMix

**F42 · major · At 640 px or narrower, the level chooser hides the stock share and bad-year columns while its caption promises them**
- Evidence: p7 (fails WCAG 1.4.10) and p4 (375 px). *Code checked:* `index.html:421` sets `display:none` on lad-num 3 and 4.
- Fix: Wrap the numbers onto a second line instead of hiding them. At the very least keep the bad-year dollars and make the caption match what is shown.
- Files: `web/index.html:421`, `web/strings.js` (caption)

**F43 · major · The thread reads out of order and contradicts itself**
- Evidence: p2. The change note "suggestion went from 4 to 5" and the summary "suggested 5 · chosen 5" sit above two older guide replies that say "suggested 4". Exploring from the tray left no trace in the thread, and the mix updated 3,234 px above the viewport.
- Fix: Append change notes at the bottom. Move a reopened check card to the bottom, as the mix card already moves. Add a one-line note when a level above the self-check is chosen.
- Files: `web/app.js` (change-note insertion, review/Change-level reopen)

**F44 · major · The first message auto-opens the check and pre-ticks every named ticker as a pick**
- Evidence:
  - p3: "How does my mix … compare with XEQT, which I hold" opened the check with XEQT pre-ticked as a pick.
  - p6: "I currently hold XEQT and ZAG" pre-ticked both. The page then reported "You changed the reference fund list", listed ZAG twice in Edit funds, and added a VBU/XEQT dropped note.
- Fix: Make the picks box opt-in, labelled "Include funds I mentioned". Exclude tickers named after "compare with" or "hold". Do not open the check when the message is a question or a custom mix exists (see F06). Do not list a pick that is already the reference fund for its slot.
- Files: `web/app.js:320-329`, setup checkline, Edit funds shelf

**F45 · major · US tickers in the first message are dropped silently and the market is not inferred**
- Evidence: p4. From "qqq schd bito, max risk. 5k + 300/mo", st.picks=[] and the market stayed CA with "$5,000 CAD". Nothing mentioned the tickers. etf_profile('QQQ') returned found:false, because only the CA list was loaded.
- Fix: Resolve tickers across both markets. If every named ticker belongs to one market, infer it or show a "These are US funds: switch to US?" chip. List the recognized tickers in "From your message", and keep picks across a market switch.
- Files: `web/app.js:43-45, 326, 346-354`

**F46 · major · Adding picks moves other weights without saying so**
- Evidence: p4. The proposal to add QQQ/SCHD/BITO listed only QQQ; the zero-weight picks had no rows. "Hold at least 5%" BITO then re-optimized everything with no before/after: QQQ 9.3→4.5%, VWO 4.5→12.1%, VOO 47.1→40.1%, cash $848→$1,025, bad year $4,010→$4,256.
- Fix: List every requested fund in the proposal, showing "0% (no room at this level)" where needed. Send "Hold at least" through the same Now/After preview, or add a diff note naming the funds that moved.
- Files: `web/app.js` (card-prop, minimum apply ~922), `web/assistant.js` (propose_change)

---

## Tier 3: minors

| ID | Title | Evidence | Fix | Files |
|---|---|---|---|---|
| F47 | The 18+ warning repeats the hint and never says what to do | p1, p2: identical sentence twice, no role=alert, stays visible after ticking | "Tick 'I am 18 or older' to continue", role=alert, focus the box, clear it on tick | `web/app.js` setup, `web/strings.js` |
| F48 | The result screen still looks like question 10, and the counts disagree | p1, p2, p4, p5, p6: "10 of 10" with Back on the result; "Review 12 answers" vs "10 questions"; setup says 10, then "1 of 9" | Header "Your result"; "Review your answers (with setup)"; update the count once the goal is known | `web/app.js` renderCheck, `web/strings.js` |
| F49 | Answer changes that do not move the suggestion give no feedback | p2: Emergency savings and Share of savings changes returned an identical result | Note every change: "suggestion stays at 4 because income still varies a lot" | `web/app.js` change-note logic |
| F50 | Unnamed buttons | p5, p7: unnamed 18+ button, tray fund rows, peek toggle, Remove buttons, focusable table wrappers | Name each control ("Remove XEQT") | `web/index.html:447, 484, 495`, `web/app.js` |
| F51 | Tray level tap in own-weights mode moves the highlight and nothing else | p3: Level 3 pressed next to "behave like level 4.2"; tapping 4 set st.level only | Show the level as a read-out (4.2); a tap asks "Switch back to the model at level 4? Your weights are kept" (with F18) | `web/app.js` renderTray ~1180 |
| F52 | The one-fund comparison cannot use the fund the person holds | p3: always auto-picks ZGRO; the compare_one_fund tool takes no ticker | Add a ticker choice (asset-allocation ETFs only) to the block and to the tool | `web/app.js:837` oneFundFor, `web/assistant.js:79-80`, `robokit/engine.py` |
| F53 | New cards land under the sticky header or tray | p4 (checked by hand; the rAF scroll could not be observed by p3 or p7): Apply at y=747 under the tray bar; the mix opens on the one-fund block | `scroll-margin-top:72px; scroll-margin-bottom:200px` on thread cards; `block:'start'` for the mix | `web/app.js:288`, `web/index.html` |
| F54 | The copy fallback lands at the bottom of the thread and stacks on retry | p1, p4, p7: about 4,000 px below the button; 2 taps give 2 cards | Show it inline under the button and reuse one; label the button "Could not copy, see below" | `web/app.js` copy handlers |
| F55 | The phone tray is hard to dismiss one-handed; touch targets are small | p4: no tap-outside, no swipe; × is 33×34; Back/Skip/Change 20 px, ticker buttons 18 px, minimum input 40×26 | Scrim tap-out, swipe-down, 44 px targets, a bottom "Done" | `web/index.html`, `web/app.js` toggleTray |
| F56 | The explore sheet's first focus is wrong | p7 (from code; rAF blocked): `querySelector('.btn.primary, button')` hits the first Change link; p1: focus stayed behind the modal | Focus the sheet heading (tabindex=-1) or the primary button | `web/app.js:775` |
| F57 | Dark-mode edges are near-invisible | p7: unselected option borders 1.25:1; pre-selection shown only by a 0.87 px dashed line; sheet edge about 1.2:1 | Borders of at least 3:1, a thicker pre-select outline, a visible sheet border | `web/index.html` dark tokens |
| F58 | A+ is one small step with no state | p2, p5: zoom 1.15 only, no aria-pressed or label change; the phone header wraps ("Robo-/Kit") | Two steps (1.15, 1.3), aria-pressed, a label change, shorter header controls when narrow | `web/index.html:39`, `web/app.js` #textsize |
| F59 | "Show me how" clips tables and shows a raw series ID | p7: two tables overflow at 640 px; p5, p6, p7: "rate V80691344" | Scroll or stack the tables; map series IDs to names ("BoC 3-month T-bill") | `web/app.js` show-how, `web/strings.js` |
| F60 | A set minimum cannot be edited | p6: after "Hold at least 10%" XEQT, the control disappears; the only way back is Remove | Keep "Minimum 10% · change · remove" on the row | `web/app.js` not-held picks control |
| F61 | Without the assistant, chat is swallowed while a question is open | R-W: "VFV", "what is an ETF?" and "compare XEQT VEQT" gave only the hint "Tap one of the answers below" | If there is no local match, fall through to route() | `web/app.js:827` |
| F62 | The chooser compares a balance with a loss, and "bad year" vs "2008" is never explained | p1, p6: bad year $130,035 (a balance) next to 2008 −$39,810 (a loss); −13% vs −26% with no reason given | Show both as losses; add "Bad year = a 12-month result seen about 1 year in 20; 2008 = the full fall from peak to low over 15 months" | `web/app.js` ladder, one-fund table, `web/strings.js` |
| F63 | Mix copy assumes choices the person never made | p1, p2, p3: "What the model does with the funds you chose" with no picks, or in own-weights mode; the resume line says "Level 3" for own weights; the list has no unit price; satellites labelled "Equity" | Branch the copy (default funds / own weights); resume "Your own weights, 4 funds"; add price and date per line; name satellites by region | `web/strings.js` (mixSub, listHead, resumeLine), `web/app.js` listText |
| F64 | Own weights with no usable ticker return an opaque error | R-E: `{'error': 'attempt to get argmin of an empty sequence'}`; the notes saying why each fund was dropped are thrown away | Refuse before the maths, naming the dropped tickers | `robokit/engine.py:353`, `robokit/stress.py:82` |

---

## Tier 4: polish

| ID | Title | Evidence | Fix | Files |
|---|---|---|---|---|
| F67 | Option sub-labels run together | p2, p4, p5: "$8,979 USDworst crisis replay"; Q9 says "worst crisis replay", the chooser says "2008 replay" | `.scen-range small {display:block}`; one crisis label | `web/index.html`, `web/strings.js` |
| F68 | A typed answer used locally leaves an unanswered user message | p2: the "60%" message got no reply; its confirmation vanished with the card | Add a page note under the user turn ("Pre-selected 50% to 75% on the self-check") | `web/app.js` matchTyped |
| F69 | Identical proposal previews stack | p5: two propose_change(level 1) calls gave two cards | Replace in place when the arguments match | `web/app.js` card-prop |
| F70 | Re-adding a held fund does nothing, silently | p3: XEF plus Enter, no message, text left in the field | "XEF is already in the mix (International stocks, 20%)"; clear the field | `web/app.js:1007` |
| F71 | Editors open below the fold | p3, p7: the Edit funds shelf and weights grid open under the 9-row table, about 500 px below the button | Scroll to the editor and focus its first control, or place it above the table | `web/app.js:889` renderMix slots |
| F72 | Small copy and precision slips | p4, p5, p6: "1 funds match"; excluded reason hidden; "39%" next to "10.0%"; anchor column sums to 87% with no note; "40% of the money but 40% of the risk"; "Above your comfort answers" vs "Above your self-check"; composer keeps a 60 px height | Pluralise; show excluded_because; one precision per column; add "rest: funds not held"; branch the "but" sentence; one tag; reset the composer height | `web/strings.js:81`, `web/app.js` |
| F73 | Retirement gaps | p5: projections are nominal with no inflation note; the income question has no pension option | "Nominal dollars, not adjusted for inflation" note (or a toggle); a guaranteed-income option | `web/strings.js`, question bank (`robokit/` items, `web/robokit.js`) |

---

## Metrics against targets

| Persona | Blocks before chat (≤4) | Taps to first mix (≤12) | Time to first mix (≤2 min) | Duplicates (0) | Silent changes (0) |
|---|---|---|---|---|---|
| p1 Mei, first-time investor | 0 (1 stale resume card from shared storage) | 18 (direct path about 16) | 234 s harness; human estimate 100-120 s | Check/mix: none. 2 identical copy-fallback cards | 4 |
| p2 Jordan, level cap | 0 | 20 (shortest 14) | 207 s harness | None | 6 |
| p3 Priya, DIY | 1 | **2** (skipped the check) | **26 s** | None | 7 |
| p4 Tyler, US phone | 0 | 16 | 340 s harness; human estimate 70-90 s | None | 4 |
| p5 Linda, retiree | 0 | 18 | 219 s harness | 2 identical proposal previews (older one disabled) | 3, plus 1 wrong change (−1500 → +1500) |
| p6 Daniel, analyst | 0 | 15 (minimal 14) | 180 s harness | None (1 stale fund card) | 3 |
| p7 Sam, keyboard/a11y | 0 (1 stale resume card) | 26 total; 18 essential (plus about 169 Tab presses) | 516 s harness (keyboard; not a human estimate) | None (stale "Add") | About 5 kinds (focus lost after 7 actions, no mix announcement, stale Change-level pick, …) |

| Target | Result | Notes |
|---|---|---|
| Blocks before chat ≤ 4 | **Met, 7/7** | 0 to 1 blocks. The only block is a resume card left in shared test storage. |
| Taps to first mix ≤ 12 | **Missed on every guided path** (14 to 20). Met only by p3, who skipped the check. | This is structural. With prefilled setup, the minimum is 18+ tick, Continue, 10 answers and Use level = 13 (12 for the wealth goal). Folding the 18+ tick into a single "I'm 18 or older, start" button gives 12 (11 for wealth). Explore detours (F09, F08) and rejected Continues (F47) add the rest. |
| Time to first mix ≤ 2 min | **Not measurable in this harness** | Wall-clock was 180-516 s, inflated by tool round trips. The only human estimates (p1 100-120 s, p4 70-90 s) and p3's measured 26 s are within target. p2, p5, p6 and p7 need a timed human run. |
| Zero duplicates | **Met for the self-check and mix cards, 7/7** (1 each throughout, including start_self_check, compare_one_fund, resume and market round trips) | Remaining: stacked copy-fallback cards (F54), identical proposal previews (F69), stale-but-live controls (F34). |
| Zero silent changes | **Missed, 7/7** (3 to 7 each) | The reviews add more that no persona hit: opener rewrites (F06), gate bypass (F01), stale B2 scoring (F10), wiped setup fields (F21), older proposal overwriting edits (F19). |

## Fix batches (suggested order)

1. **Level state machine** (F01, F02, F03, F08, F09, F10, F20): one derived `levelStatus()` and one consent record, used by the tray, chooser, sheet, chat preview, resume and pageState.
2. **Input parsing** (F05, F06, F14, F44, F45, F21): parse the opener once, handle signs and withdrawal verbs, cross-market tickers, opt-in picks, keep typed input.
3. **Numbers the person sees** (F04, F07, F11, F12, F13, F15, F24-F36): no silently dropped scenarios, a turn-scoped validator, ladder rows built from the real request, monthly flows and horizon carried into every range.
4. **Own-weights mode** (F16, F17, F18, F19, F22, F23, F51, F63): weights follow swaps, minimums become weights, undo, a grid that accepts its own prefill.
5. **Phone and accessibility** (F37, F40, F41, F42, F53, F55-F58).
6. **Control names** (F50), then explanation copy (F38, F43, F47-F49, F62).

## Working in v2.1 (do not regress)

- One self-check card and one mix card, updated in place, across every persona.
- The first message prefills the setup.
- Chat is inserted above an open check, and typed answers are pre-selected but recorded only on tap.
- The explore sheet shows risk in dollars and cannot be applied from chat.
- The tray, mix card, current_mix and compare_one_fund tie out exactly (p6).
- Resume restores own weights, swaps and picks (p3), and a CA↔US round trip keeps the work.
- Every string passes through esc() (no XSS found), and every localStorage call is wrapped.
- Python and JS parity passes (103 pytest, 12 reference cases plus 400 profiles).

## Test limits to close in round 3

- Testers shared localStorage, so p1's own resume and p3's saved state could not be tested cleanly.
- requestAnimationFrame never fired in the hidden panes, so scroll-into-view and the sheet's first focus (p1, p3, p7) were judged from code.
- All times include tool latency. Run a timed human pass for the ≤ 2 min target.
