# p4_us_mobile (round 2): Tyler, 23, Austin, on a phone

Status: COMPLETE. Own tab (tab-13) at http://localhost:8765/mock.html, emulated 375x812 (Android UA), reloaded after resizing. I played Tyler in the UI and, separately, the Robo-Kit guide through `window.__mock`, following the RULES. The validator accepted both guide replies on the first try. No project file was edited.

Environment caveats (so nobody chases ghosts):
- The pane was not compositing frames: `requestAnimationFrame` never fired (checked: a rAF callback did not run in 500 ms) and CSS transitions sat at currentTime 0. So the page's own `push()` auto-scroll (app.js:288, wrapped in rAF) never ran in my session. Every scroll finding below was re-checked by calling the same `scrollIntoView({block:'nearest'})` by hand, and I dropped the ones that did not survive that check. I finished the tray transition with `getAnimations().finish()` before measuring it.
- `computer.left_click` by ref was unreliable after a scaled screenshot: one click landed at half the reported coordinates on an empty span. From question 9 on I tapped by checking with `elementFromPoint` that the button was visible and on top, then clicking it. Screenshots came back offset and mostly blank, so layout evidence is from `getBoundingClientRect`.
- Shared localStorage showed a "Resume where you left off? Level 2 · $300,000 CAD" card from another tester's session. I tapped Start over.
- Timing is wall clock through the harness. Each tool round trip took 5 to 20 s, and I also spent time writing the guide's reply, so the seconds figure overstates what a human would take.

---

## Metrics

| Metric | Value |
|---|---|
| (a) #thread blocks before first chat message | **0** (1 before Start over: the shared Resume card) |
| (a) #thread blocks after the self-check finished | **4**: user message, guide reply, one-line self-check summary, mix card |
| (b) taps from landing to first full mix | **16** for a fresh visitor, 17 counting the forced Start over. Composer 1, Send 1, 18+ 1, US 1, goal 1, Continue 1, 9 answers, Use level 5 1. Scrolling not counted. Round 1 was about 26 interactions. |
| (c) seconds from landing to first full mix | **340 s** measured (t0 → mix card rendered, 340,467 ms), mostly harness overhead. My estimate for a real thumb: about 70 to 90 s. |
| (d) duplicated live cards | **None.** Exactly one `.card-check` the whole time (setup → 9 questions → result → summary → reopened in place by "Change level" → collapsed again) and one `.card-mix`, updated in place 3 times. After Apply, the proposal card showed "Applied" and "Not now" disabled. |
| (e) silent changes | 4 real ones, listed below (E1–E4) |

---

## Walkthrough

### 0. Landing
- Viewport meta now exists (`width=device-width, initial-scale=1, viewport-fit=cover`) and innerWidth is 375 at load. Header: Robo-Kit | Canada | US | A+ | Assistant. The header is sticky (60 px).
- The default market is Canada. The tray bar at the bottom reads "Level 3 · Bad year (1 in 20) $9,126 CAD · Fees a year $12 CAD".

### 1. "qqq schd bito, max risk. 5k + 300/mo"
- The page parsed **$5,000 and $300/mo** and opened the self-check card by itself: "From your message: $5,000 CAD · +$300 CAD/mo". This is good.
- **The tickers were dropped.** `st.opener = {amount:5000, monthly:300}`, `st.picks = []`, and PAGE STATE `picks_not_held: []`. Nothing on screen mentions QQQ, SCHD or BITO, or "max risk". The market stayed Canada and the amounts were labelled CAD, although all three tickers exist only in the US list.
  - Root cause: `applyOpener` keeps only picks whose market equals `f.market || st.market` (app.js:326). `parseOpener` never infers a market from tickers (app.js:43-45). While on CA the US file isn't loaded, so `resolveFund('QQQ')` returns null (app.js:346-354).
  - The same gap reaches the guide: `etf_profile({ticker:'QQQ'})` returned `{"found":false}`. The honest reply was "QQQ isn't in the Canadian fund list. Tap US USD in the self-check card below."
- The guide reply was inserted **above** the open self-check card, as designed.

### 2. Setup screen
- 18+ checkline, Market (Canada CAD / **US USD**), goal chips, Amount 5000, Monthly 300 (both prefilled, `inputmode=decimal`). Tapping **US USD** switched everything: header pill, tray ("$4,641 USD"), the labels "Amount (USD)", and "From your message: $5,000 USD · +$300 USD/mo". Nothing was lost.
- Goal: "Building wealth, no fixed date". Continue.
- The header said "10 questions" and the next screen said "1 of 9", because the withdrawal-length question is skipped for this goal. That is correct but a little jumpy.

### 3. Nine questions
- Savings Yes, debt No, horizon "20 years or more", share "25% to 50%", income "Mostly steady", one-year range: the widest ("$4,390 USD to $6,339 USD"), "Buy more", ten-year: the widest ("$4,832 USD to $17,568 USD · worst crisis replay −$2,641 USD"), "Missing out on gains".
- Option buttons are 46 to 78 px tall, which is thumb-friendly. "Back" and "Skip" are 20 px tall text links.
- The ten-year question shows outcomes of the $5,000 **alone**: "$6,977 to $8,979 … $4,832 to $17,568". Tyler said +$300/mo, and the mix card later projects a middle of $63,506. The question doesn't say it leaves out the monthly add.
- The range text and its sub-label run together: `<span class="scen-range">$6,977 USD to $8,979 USD<small>worst crisis replay…` with no space or margin. It renders, and reads aloud, as "…$8,979 USDworst crisis replay −$365 USD".

### 4. Result
- "Your situation allows level 5 / Your comfort … points to level 5 / because of:" lists 5 answers, each with a **Change** link (49x20 px). Then "Suggested: level 5, Aggressive growth. It is the lower of the two."
- Answer labels are abstract: "One-year range: **Range for level 5** points to level 5". Tyler picked "$4,390 to $6,339"; he never saw the words "range for level 5".
- The level chooser is in his dollars: "on your $5,000 USD", with level 5 at 2008 replay −$2,641 USD. The caption promises "share in stocks, a bad year and the 2008 replay", but at 375 px the stocks % and bad-year cells are `display:none`. Only the 2008 replay shows.
- The "above your self-check" sheet cannot be reached for this persona: suggested level = 5 = max. Not exercised.
- Tapped **Use level 5**. The card collapsed to "Self-check · suggested 5 · chosen 5 | Review 11 answers | Change level | Start over". The mix card appeared.

### 5. First mix
- "The mix at level 5 with 4 funds · Aggressive growth": VOO 46.5% $2,325 (3 units), VXUS 45.9% $2,296 (26 units), VNQ 3.9% $193 (2), VWO 3.7% $186 (3). Cash left $247. There is a one-fund comparison (AOA), 7 crisis replays in dollars (2008 −$2,641 / −53%, with "VOO, VXUS: estimated before the fund existed"), a paths chart with monthly 300 (middle $63,506), and Copy summary / Copy for AI / Show me how.
- Where the viewport landed: after the self-check collapsed, the card spanned the whole viewport from 654 px above it. Visible were "Compare with a one-fund version" and the AOA table, while the headline range, bad year and funds table were above the fold. `scrollIntoView({block:'nearest'})` (app.js:288) does nothing when the element already spans the viewport. I verified this by calling it by hand: y stayed at −654.
- Tyler: "cool, but where's my QQQ?"

### 6. "where did qqq schd bito go? i want those"
- PAGE STATE still had `picks_not_held: []`, so the page didn't re-read tickers from this message. As the guide I called `propose_change({add:['QQQ','SCHD','BITO']})`. The preview card shows Now/After numbers (bad year $4,011 → $4,010, fees $2 → $3) and a weights table: VOO 47.1, VXUS 32.5, VNQ 6.6, VWO 4.5, **QQQ 0.0 → 9.3%**. SCHD and BITO **do not appear at all**. They were added, and the optimizer gave them 0, but the card says nothing. The guide had to explain it.
- Apply: the proposal buttons went to "Applied" / disabled. The mix card updated in place (one card). Now "SCHD is not held in this mix. Hold at least [2]% Apply" and the same line for BITO. The reason ("at this level the optimizer gave it no weight") appears only under "Checks and notes", about 2,000 px further down the same card.
- QQQ row: "9.3% · $466 USD · **0 units**". One QQQ unit costs more than $466, so Tyler's own pick can't actually be bought, and cash left rose to $848 (17% of $5,000). The row doesn't say this. The only hint is the generic footnote "Units … rounded down".
- The updated mix card sits about 4,700 px above the Apply button. Near the thumb, the only sign of the change is the tray bar ($4,011 → $4,010, fees $2 → $3).

### 7. "Hold at least 5%" BITO
- The input is 40x26 px (min 2, max 10), and the Apply next to it is 57x44. I set 5 and tapped Apply.
- Result: BITO 5.0% (23 units), but **everything else moved and nothing said so**: QQQ 9.3% → 4.5% ($225, still 0 units), VWO 4.5 → 12.1%, VNQ 6.6 → 9.4%, VXUS 32.5 → 28.9%, VOO 47.1 → 40.1% (2 units, but "$2,003"). Cash left $848 → **$1,025** (20%). Bad year $4,010 → **$4,256**, and the range got narrower.
- **The 2008 and 2011 crisis replays disappeared.** The crisis list now starts at 2014-16. The one-fund comparison lost its "2008 financial crisis" row. "In plain words" now leads with "Replaying the 2022 inflation and rate shock, this mix would have fallen about 24% (about $1,200 USD)" instead of the 2008 figure (−53%, −$2,641). There is no note anywhere (`has2008: false`, `has2011: false`). So adding 5% bitcoin futures made the mix *look* half as risky in the crisis replays. Root cause: `stressTest` skips a scenario outright when any fund has no series and no peer median (robokit.js:386, `continue`). Crypto has no peer for 2008 or 2011. This is the same class of bug as round 1 (then SCHD/short history; now BITO).
- The level chooser still shows level 5 at 2008 replay −$2,641, so two screens disagree.

### 8. Tray sheet
- Open: tap the bar. Focus moves to × (`aria-label="Close"`), the body behind is hidden, and the sheet spans y 146–812.
- Close with **Escape**: works, focus returns to the toggle, scroll position is kept (1212 → 1212). Close with **×**: works the same way.
- × is 33x34 px at top-right (y 159). It and the sheet's own header bar are the only close targets, both at the hardest one-handed reach. Tapping the 86 px strip above the sheet does nothing (checked: the sheet stays open), and there is no swipe-down (no touch handlers in app.js).
- **The tray is wider than the phone.** Its grid column is 448.7 px inside a 375 px sheet (`scrollWidth 481`, `overflow-x:auto`). In the open sheet the level-5 segment starts at x = 362 and is 87 px wide, so Tyler's own level is cut off at the right edge. In the collapsed bar the text runs to x = 428 and the chevron sits at x = 438 to 454, off-screen, so the bar reads "…Fees a y" with no open affordance. Likely cause: `.tray-two` (Amount/Monthly) resolves to 220.3 + 8 + 220.3 = 448.7 px, exactly the tray column. The labels keep `min-width:auto` around inputs with intrinsic width.

### 9. Other checks
- "Change level" reopened the same card in place. "Use level 5" again **kept** his picks: satellites [QQQ, SCHD, BITO] and minimum {BITO: 0.05} before and after.
- "Copy as a list": the clipboard was denied in this harness. After about 1.5 s a fallback card "Could not copy. Select the text instead." was appended at the bottom of the thread. The fallback works, but for that second and a half the button showed nothing.
- Bottom chrome: dock 120 px (the empty textarea keeps an inline `height:60px` because the placeholder wraps to 2 lines) + tray bar 64 px + header 60 px = 244 of 812 px. That leaves 568 px for reading, up from about 440 in round 1. With `block:'nearest'` and no `scroll-margin`, a newly pushed card aligns its bottom to 812. For the proposal card I verified that **Apply ends up at y = 747, under the tray bar**. Its top, when aligned, goes to y = 0, under the sticky header: the self-check progress/Back line sat at y = −1 behind the header, and a hand call put the card top at 0.
- Copy: "VOO is 40% of the money but 40% of the risk: the fund that swings most drives most of the ups and downs". The "but" makes no sense when the two numbers are equal.
- Class labels are inconsistent: core funds get slot names ("US stocks"), picks get raw classes ("Equity", "Crypto").
- The sr-only announcer was stale: "Self-check: about 2 minutes · 9 of 9". It never announced the mix or the Apply.

---

## Silent changes (e)
- E1: tickers in the first message were dropped with no word, and the market was not inferred.
- E2: the proposal card hid 2 of the 3 picks (0 weight) without a row or a note.
- E3: "Hold at least 5%" BITO re-optimised every weight, raised cash left from $848 to $1,025, and moved the bad year from $4,010 to $4,256, with no before/after.
- E4: in the same step, the 2008 and 2011 replays vanished from the crisis list, the one-fund table and the plain-words headline, with no note.

## Fixed since round 1 (verified)
- A viewport meta exists and the page lays out at 375.
- The 18+ gate plus 15 separate question cards are now one live card: setup + 9 questions, with the withdrawal-length question skipped for wealth. No answered-card pile-up and no duplicate Q6 or profile cards.
- "5k + 300/mo" prefilled Amount 5000 and Monthly 300. The monthly add is used (paths chart middle $63,506).
- The result names the answers that set the level, each with a Change link. PAGE STATE carries `binding_answers`, so the guide can name them.
- The level chooser uses his $5,000 (round 1 had a hard-coded $10,000).
- SCHD no longer vanishes after Apply: it shows as not held with a "Hold at least" control, and there is a reason under Checks and notes.
- The proposal card shows weights Now → After and disables its buttons after Apply.
- One mix card, updated in place. No stale second report.
- "1 year" (not "1 years") and "$41 USD on $5,000 USD" (round 1 had no $).
- The header is sticky. The dock has an opaque background. Chips hide after landing. Reading area went from about 440 to about 568 px.
- Save/resume exists (the Resume card on landing).
- The tray has a × with an aria-label, Escape closes it, focus returns and scroll is kept.
- Picks and minimums survive re-choosing the level.
