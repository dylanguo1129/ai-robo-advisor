# p3_diy_pro: Priya, 41, Calgary, experienced DIY investor

Status: COMPLETE (real page at http://localhost:8765/mock.html, my own tab, 1440x900 viewport; I played the guide via window.__mock as a faithful model following the RULES).
Note: screenshots went blank whenever the document was scrolled (capture limitation in this pane, not reproduced as a page bug: elementFromPoint hit the right elements). Everything after the first two screenshots was read as text / DOM.

Who I am: I read Canadian Couch Potato, hold XEQT in my TFSA and VFV + XAW in my RRSP. I want to skip any questionnaire, build at level 4, swap each sleeve to my preferred iShares funds, add my own picks, compare against XEQT / VEQT / VGRO, see look-through exposure (regions, currencies, overlap), back-test my exact mix, compare fees with Wealthsimple, and leave with a trade list for $120,000 split TFSA / RRSP. My yardsticks: Portfolio Visualizer (exact weights, back-test, any ticker), Passiv (trade list, per-account, USD/CAD), one-ticket ETFs (0.20%, zero effort).

---

## 1. Landing (0:00)

Saw: "What would you like to build?" / "Search 2,187 Canadian and 5,770 US ETFs, ask a question, or build a diversified mix step by step." One input, five chips (Build a portfolio, What is an ETF?, Compare two ETFs, How risky is the mix?, Markets today). Right tray already shows "The mix · Reference funds, level 3 · Balanced. Change anything." with 9 funds (VFV 23%, ZAG 20%, XIC 16%, CASH 10%...).

Felt: good. A live mix before any questions is exactly what a DIY person wants. Clean, Wealthsimple-ish.

## 2. Straight to level 4, amount $120,000

Clicked "4" in the tray. For ~1 s the header still said "Your choices, level 3 · Balanced" with level-3 numbers under a highlighted 4, then it caught up: 71% equity / 20% FI / 6% real estate / 3% commodity; VFV 32%, XIC 20%, ZAG 20%, FLUR 13%, XRE 6%, VEE 5%, VALT 3%.
Typed 120000 into Amount (no $ or CAD shown in the field). Tray: "8 years in 10 $115,152 to $138,588 · Bad year (1 in 20) $110,544 · Fees a year $149 · Volatility 8.6%".

Clicked "Open the full mix". The report is rich: weights with resampling bands, "% of the risk" per fund, plain-words summary, projection fan, seven crisis replays, checks, "Show me how".
Things I noticed as a pro:
- Header says "Fees a year $149 (0.13%)" but Checks say "fund fees of 0.12% a year would cost about 2,540 on 120,000" (different % and no $).
- Checks: "1 fund(s) that would have held less than 2% were dropped and the rest re-optimised: VBU.NE." Internal Yahoo suffix and dev wording.
- "Range of yearly returns by how long you hold: 1 years" (grammar).
- "Level 4 of 5 (growth) aims for about 80% of the stock market's ups and downs. For these funds that is a volatility of about 8.6% a year." 8.6% for 71% equity looks low to me.

## 3. Trying to swap funds without the survey (stuck)

Clicked VFV in the report: a fund card appears (fee, size, 165 months history, 1y 21.3%, 5y 14.6%, worst drop -18.5%, yield, trend). Only button: "In the mix". No "swap", no alternatives, no holdings/region/currency breakdown.
Tray fund rows: same, they only open fund cards. There is no "Edit funds" anywhere outside the guided build.

Clicked the "Build a portfolio" chip hoping for the shelf: got "Are you 18 or older?" then "Question 1 of 15 · Which market do you want to build from?" (the header already says Canada CAD). No skip. I backed out.

Typed "XEQT" in the composer: a fund card appears instantly, no AI needed. Nice. Typed "XEF" -> card with "Add". Clicked Add: button turns into "In the mix". But the tray fund list does NOT contain XEF (still VFV, ZAG, XIC, FLUR, XRE, VEE, VALT). Evidence from state: st.result.notes = "2 fund(s) that would have held less than 2% were dropped and the rest re-optimised: VBU.NE, XEF.TO." The card lied to me.

## 4. Chat, because I am stuck

Me: "I clicked Add on XEF and the card says 'In the mix' but it isn't in the funds list. I want XEF instead of FLUR, and XUU instead of VFV. How do I swap without doing the 15 questions?"

As the guide I called current_mix (no sleeve keys in its output), etf_profile XUU (returned "mer": null), then propose_change with swap {"International stocks": "XEF.TO", "US stocks": "XUU.TO"} -> notes "There is no 'International stocks' slot in this mix, so the swap to XEF.TO was ignored." Tried tickers as keys -> same. The real keys (ca_us_equity, ca_intl_equity) are never exposed to the model. Then remove [FLUR, VFV] + add [XEF, XUU] -> after: XIC 49.1%, ZAG 15.15%, VEE 11.96%, XRE 10%, VALT 8.62%, XEF 2.83%, XUU 2.32%. Added funds are treated as satellites, so a like-for-like swap wrecks the regional mix.

What I (user) saw in the thread, in order: my message; the guide's text; then an XUU fund card; then FOUR "Proposed change" cards, three of them identical Now/After (no change) each with a live "Apply" button, and the fourth showing only "Funds XIC, ZAG, VEE, XRE, VALT, XEF, XUU" + "Volatility 9.2% · Fees a year $191" - no weights, so the 49% XIC is invisible on the card. The guide's text was honest ("tap Not now on them", "I would not apply the last card") but the transcript is a mess and the reply sits above the cards it talks about.

## 5. Giving in: the 15 questions

Went back up to the stranded Question 1 card (now far above my chat) and answered as myself: Canada, Retirement, emergency fund Yes, no high-interest debt, 20+ years, withdraw over 10+ years, $120,000 (pre-filled, good), share of savings 50% to 75%, income mostly steady, widest one-year range ($112,920 to $142,764), Buy more after a 20% drop, widest ten-year range, Missing out on gains, both quiz questions right. "Skip" only appears from Q13 on.

Two things bothered me as a quant-literate user:
- Q12 ten-year ranges: level 1 "$151,627 to $178,501" ... level 5 "$158,188 to $319,678". The riskiest option has the highest floor too, so there is no trade-off. Anyone picks the last one. Same in the ladder: 10-year floor $12,636 (level 1) vs $13,182 (level 5).
- Q10's widest one-year range (level 5) is only -5.9% at the 10th percentile. I own XEQT; that's not what a 95%-stock year looks like.

Result card "Here is what I heard": "Your situation allows Level 4 · Your comfort with ups and downs Level 5 · Suggested level 4 · Growth ... This money is most of your savings, so one step lower. ... We use the lower of the two: level 4." Level 5 button disabled, title only (hover) "Above what your situation supports".

This is exactly the level-cap bug: I already hold 100% equity (XEQT) and the tool now forbids its own 95%-stock level. 50-75% of savings in TFSA+RRSP is normal for a 41-year-old; registered accounts ARE most people's savings. There is no "I understand, use 5 anyway" and no explanation of what would unlock it. After "Use this level", the tray's 5 is disabled too. The ladder card's level-5 row still looks clickable, and clicking it silently does nothing (app.js:541 returns early; the row has no disabled state, app.js:532).
Later I reloaded the page: every answer, the level cap, the amount and my funds were gone and level 5 was enabled again. So the cap blocks honest users and is undone by F5.

## 6. The shelf (finally what I wanted)

"Fill each asset class" card: ten sleeves, each a dropdown of 6 options with fee, plus Remove, plus "Add your own fund" (datalist of 637 funds) and "Build the mix". This is the best part of the product. Changing a dropdown applies immediately to the tray.
- US stocks -> XUU (dropdown label "XUU · fee · iShares Core S&P U.S. Total Market..." - fee missing).
- International -> XEF, EM -> XEC. Removed REITs and Gold (buttons turn into "Keep", which reads like "keep it" rather than "add back").
- Added XAW as my own pick. Shelf now lists XEF twice (in its sleeve and as my earlier own pick).
- Other data smells in the shelf: XSTH / XSTP ("0-5 Year TIPS", US inflation bonds) listed under "Short-term Canadian bonds"; "ZUAG.F"; "ZMMK · fee · BMO Mutual Funds - BMO Money Market Fund"; "IShares".

"Build the mix": "The mix at level 4 with 5 funds · Growth": XUU 33.4% ("· 43% of the risk" with blank fee), ZAG 24.9%, XIC 22.5%, XEF 13.6%, XEC 5.6%. "Fees a year $149 (0.12%)". XAW silently dropped again ("2 fund(s) ... dropped ...: VBU.NE, XAW.TO"), and I cannot say "hold XAW at 20%". I cannot set any weight at all; the optimizer decides. Code shows the engine already supports per-fund `minimums` (app.js:171) but nothing in the UI or tools sets them.
Fee note: XUU has no MER in the data; the engine quietly averages known MERs over the known weights (robokit.js:558-559), so "$149" includes a guessed fee for a third of the money without saying so.

"Show me how": target vol "8.6% = 80% × 10.8% (Stock market volatility)", lambda, shrinkage, "Data window 2011-09 to 2026-08 (180 months)", extended-history proxies (e.g. "CASH: PSA.TO ... rate V80691344" - raw series ID), and "Hypothetical back-test, after costs · Level 4 · 2009-12 to 2026-08": Robo-Kit 10.4% / 9.0% vol / -15.9% worst vs Static stock/bond mix 10.5% / 8.9% / -15.4%. Honest, but it says the optimizer adds nothing over a static mix, and it is not my funds.

## 7. Compare with one-ticket ETFs

"Compare two ETFs" chip: posts a fake user bubble "Compare two ETFs" and a note "Type two or more tickers, for example: XEQT VEQT". I typed "XEQT VEQT VGRO" - this went to the AI (single tickers are local, multiple are not). Comparison card: fees 0.20/0.22/0.22%, 5y 13.2/13.2/10.4%, worst drop -17.6/-17.9/-16.1%, and "How closely they moved ... XEQT / VEQT: 1.00; XEQT / VGRO: 1.00" while the guide's text (from the same tool) says 0.999 / 0.997.
What I needed: my mix as a column next to XEQT (fee $, volatility, bad year, 2020/2022 drawdown on the same window). Not possible. And the fund "Worst drop -17.6%" (XEQT since 2019) sits next to my mix's "2008 financial crisis -27%": different windows, so XEQT looks safer than a 75/25 mix.

## 8. Look-through, back-test of my mix, fees vs Wealthsimple, trade list

Asked for region / currency look-through and XAW overlap. Tools have none. Guide (me) could only list sleeve weights and 5-year correlations (XAW/XUU 0.963, XAW/XEF 0.847, XAW/XEC 0.707). compare_etfs also returned XAW with "region": "Canada" - XAW is All-Country World ex Canada. The engine computes mix.region (robokit.js:561/578) but the UI never shows it.
Asked for a back-test of my exact five funds vs XEQT year by year: backtest_summary is the level-4 method on reference funds, "funds chosen with today's information", only 2020 and 2022 shown. No custom back-test.
Asked for a trade list ($50k TFSA / $70k RRSP), US-listed VTI in the RRSP for withholding tax, and fees vs Wealthsimple managed. No tool for units, prices, accounts, withholding tax (glossary has no such term), or provider fees. The validator even rejected my reply for echoing "VTI", the ticker the user typed ("Your reply contained numbers or tickers that are not in this turn's tool results or the page state: VTI"), so the guide had to say "the US-listed fund you named". A search card "0 funds match. Showing 0, lowest fee first." was added to the thread as noise.

## 9. Switching market (the USD question)

Clicked "US USD" to look at USD listings: tray became VOO 44%, VXUS 20%, BND 20%, VWO 8%, VNQ 6%, GLDM 3%, level 4 now "Volatility 11.0%" (Canada level 4 was 8.6%: same label, different risk). Clicked back to "Canada CAD": all my work was gone - st.mix reset to {swaps:{}, satellites:[], exclude:[]} (app.js:250), tray back to VFV/FLUR/VEE/XRE/VALT, no warning, no undo. Worse, the shelf card still showed XUU / XEF / XEC selected and REITs/Gold removed. I pressed "Build the mix" on it and got VFV 32.5%, FLUR 13.1%, VEE 4.9%, XRE 5.6%, VALT 3.1%: the shelf displays one mix and builds another.

## 10. Reload

Reloaded: amount back to 10000, level 3, answers {}, thread empty, level 5 enabled. Only market/tier persist (app.js:111-115, 203, 206, 249). As someone who rebalances quarterly, I'd have to redo everything each visit.

---

## Verdict as Priya

I'd use it for 10 minutes to sanity-check a sleeve choice (the shelf + "% of the risk" + crisis replays are genuinely good), then go back to Portfolio Visualizer for exact-weight back-tests, Passiv for the trade list, and honestly XEQT for the money. It cannot yet hold my own portfolio (fixed weights, my tickers, two accounts), and three separate things silently threw away my choices (Add -> dropped under 2%, market toggle, reload).

## Verdict as a designer

The engine is ahead of the interface. The gaps are mostly plumbing: expose sleeve keys and `minimums`, let users set weights, persist state, stop mutating/cluttering the transcript, and replace the hard level cap with an informed override. To compete with the leading portfolio builders it needs: my-mix-vs-one-ticket comparison on one card, look-through (the engine already has mix.region), account-aware trade list with USD/CAD listing choice, and custom back-test.
