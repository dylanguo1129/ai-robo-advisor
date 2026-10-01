# p4_us_mobile: Tyler, 23, Austin, on a phone

Status: COMPLETE. The walkthrough ran in a real browser tab at http://localhost:8765/mock.html, emulated as a 375x812 phone with an Android user agent. I played Tyler in the UI and, separately, the Robo-Kit guide through `window.__mock`, following the RULES exactly.

Environment caveats:
- The page has no `<meta name="viewport">`. On first load in phone emulation it laid out at 980 px wide, scaled to 0.38 (`innerWidth 981`, `visualViewport.scale 0.3827`). To test the real phone layout I added a viewport meta at runtime; no file was edited. See finding F1.
- After a few minutes the background tab stopped painting, so screenshots came back blank and CSS transitions froze. From then on I read the page through the DOM (innerText, getBoundingClientRect) and finished animations with `document.getAnimations().forEach(a => a.finish())`. None of the findings depends on this.
- localStorage is shared per origin with the other testers' tabs. After my reload the page came up in CA because someone else had set `robokit2.market="CA"`. I did not toggle anything back, so I would not change their sessions.

---

## Step by step

### 0. Landing (phone width)
- I saw the header "Robo-Kit | Canada | US | (sparkle icon)", then "What would you like to build?" and one input with a send button. The placeholder is cut off: "Ask about ETFs, type a ticker, or say" (the rest, "build a portfolio", is clipped). Next came five chips on three rows and the AI disclosure. At the bottom sits a peek bar: "Level 3 · Volatility 6.4% · Fees a year $12".
- The default market is Canada, and I'm in Texas. I tapped **US**. The pill moved and the peek bar changed to "Level 3 · Volatility 8.3% · Fees a year $4". That's $4 on what amount? The Amount field is empty. (The model gets "amount 10000".)
- The Assistant button has no accessible name on mobile (read_page: `button [ref_4]` with no label), and neither does the tray toggle.
- Tyler: "OK, clean. Where do I just type my stuff?"

### 1. Chat: "qqq schd bito, max risk. 5k + 300/mo"
- I typed into the composer and pressed Enter. "Thinking" appeared, and the composer stayed pinned above three rows of chips.
- As the guide, I called `compare_etfs(['QQQ','SCHD','BITO'])` and `start_self_check`, then replied with the disclosure, the fees and worst drops, a note that BITO is crypto and not a core holding, and "Max risk means level 5; the level comes from a short self-check". The validator passed it.
- What Tyler saw, in order: my reply, "Every number checked against Robo-Kit's tools. Balanced model.", the "Side by side" table, then "Are you 18 or older?".
  - My reply said "The card above" because the card showed above while Claude was thinking. After the reply landed, the card sat **below** the text.
  - The table has a "History 329 / 178 / 58" row with no unit. "fee" is lowercase and "Yield 38.2%" for BITO has no context. For a 23-year-old, a 38% yield reads as a reason to buy.
  - "Balanced model" is the model-tier name, and "Balanced" is also the name of risk level 3. Tyler: "wait, I said max risk, why does it say Balanced?"
- The markdown line "The card above puts your three funds side by side" got rendered as a bullet together with the list under it.

### 2. Self-check (18+ gate plus 15 questions)
- 18+: tapped Yes.
- Q1 "Which market do you want to build from?" I had already picked US in the header and typed US tickers, and it still asks. Tapped US.
- Q2 goal: "Building wealth, no fixed date". Q3 emergency fund: Yes. Q4 debt: No. Q5 "When do you expect to start taking money out?": "In 10 to 19 years".
- Q6 "Once you start, how long will you keep taking money out?": "Over 2 to 5 years". Tyler: "no idea, I'm 23, pick something." There is no "not sure" option.
- Q7 "About how much will you invest to start?" is pre-filled with **10000**, though I typed "5k" in chat a minute earlier. I changed it to 5000 and pressed Enter, which did nothing. I had to tap Continue.
- No question asks about the monthly contribution. The "300/mo" I typed is used nowhere.
- Q8 share of savings: 25% to 50%. Q9 income: Mostly steady.
- Q10 one-year range cards are scaled to my $5,000 ("$4,518 to $6,155", the widest). This is good. Q11 "$5,000 is worth $4,000": Buy more. Q12 ten-year ranges: the widest "$5,798 to $14,963". Q13: Missing out on gains. Q14 bonds and rates: Not sure. Q15 2x leveraged fund: "No, it can be quite different".
- Each answered card stays full size, with every option still listed (disabled) and only the chosen one marked. The market card is 327 px tall on its own. On an 812 px phone with a 244 px sticky dock plus a 64 px tray peek, only about 440 px of reading area is left, so the next question often starts half hidden behind the composer.
- "Change answer" is a 20 px tall text link, under the 44 px thumb target.

### 3. Result: "Here is what I heard"
- "Your situation allows Level 3 · Your comfort with ups and downs Level 5 · Suggested level 3 · Balanced"
- "Your time horizon scores 9 of 15, which allows up to level 3."
- Level buttons 4 "Growth" and 5 "Aggressive growth" are disabled. The only explanation is a `title` tooltip, "Above what your situation supports", which never shows on a touchscreen. I tapped 5 and nothing happened, with no message.
- Tyler: "I'm 23, emergency fund, no debt, 10+ years, would buy the dip, and you give me Balanced, 53% stocks? Robinhood lets me buy QQQ in 10 seconds. Betterment would put me at 90% stocks." At this point he would close the tab.

### 4. Chat pushback: "why cant i pick 5?? i said max risk. im 23"
- The model received this page state: "chosen level 3 ... self-check done, suggested level 3, capacity 3, tolerance 5". The answers themselves and the "9 of 15" explanation are **not** in the page state or in any tool (`current_mix` has no profile fields). So the guide cannot say which answer set the cap, although the RULES ask it to "name the input that set the result, show how to change that input".
- As the guide, I explained situation versus comfort, said the lower one wins, and pointed him to "Change answer". It was honest but vague.

### 5. The tray
- I tapped the peek bar and the sheet opened. The tray level buttons 4 and 5 were **enabled**, even though the profile card had them disabled: the tray was not re-rendered when the profile finished.
- I tapped 5. The level stayed 3 without any message (`setLevel` silently clamps it, app.js:518). Only after that tap did the tray gray out 4 and 5. The tray title also changed from "Reference funds" to "Your choices, level 3" although I hadn't chosen anything.

### 6. Gaming the survey
- To find Q6 I scrolled back about 5,000 px, then tapped "Change answer" and picked "More than 10 years".
- A new Q6 card was appended at the very bottom, so the page now holds two Q6 cards. A second "Here is what I heard" card appeared: "Your time horizon scores 13 of 15, which allows up to level 5 ... level 5, Aggressive growth".
- One answer to a question a 23-year-old can't meaningfully answer moved the cap from 3 to 5.
- The first profile card, "Suggested level 3 · Balanced" with 4 and 5 grayed out, **stays live** higher up the page, and its "Use this level" button still works.
- Tyler: "lol, so I just had to lie on one question."

### 7. Level 5, ladder, shelf
- Level 5 was preselected, and I tapped "Use this level".
- The ladder card reads "Hypothetical ranges on **$10,000**", while the tray and survey use $5,000 (the $10,000 is hard-coded at app.js:29 and :537). For example, Level 5 shows "Bad year $8,600" on the ladder and "$4,299" in the tray.
- The "Fill each asset class" card is **1,715 px tall** on the phone. It lists 10 sleeves with 4 to 6 alternatives each, including US bonds, short-term Treasuries, TIPS, international bonds, gold and cash, and the level-5 mix holds 0% of all of these.
- One fund name is garbled: "State Street SPDR Bloomberg 1a??10 Year TIPS ETF" (the same mojibake is in data/us.json).
- "Add your own fund": I typed QQQ and pressed Enter, and it was added. Focus drops to the body after each add, so I had to tap the field again for SCHD, then BITO. No warning about BITO at the add step.

### 8. "Build the mix": first real portfolio
- The card rendered in about 0.3 s: "The mix at level 5 with 6 funds · Aggressive growth": VOO 47.1%, VXUS 30.0%, VNQ 7.5%, QQQ 6.3%, VWO 6.1%, BITO 3.1%.
- **SCHD is gone.** There is no note, and `notes: []`. Root cause: the small-weight drop note only fires when 0 < weight < 2% (robokit.js:500). SCHD came out at exactly 0, so it vanished without a word.
- **The 2008 and 2011 crisis replays disappeared.** The reference mix showed seven, including "2008 financial crisis -28%" at level 3. The level-5 mix with my funds shows only five (2014-16, 2018, 2020, 2022, 2025), and its headline sentence is "Replaying the 2022 inflation and rate shock, this mix would have fallen about 23%". So a 96%-equity mix *looks* only a little worse than the level-3 mix. The estimation window became 2013-07 to 2026-08 (158 months) after I added funds, and nothing on screen says so.
- Other things on this card:
  - "Range of yearly returns by how long you hold: 1 years ..." (should be "1 year").
  - Checks: "would cost about 74 on 5,000" (no $ sign).
  - "BITO is a crypto fund ... capped at a small weight." This is good.
- The card is **2,827 px tall**. "Monthly add" sits about 1,580 px into it. I typed 300, and the chart updated only after the field lost focus (on change, not on input). The middle outcome went to $60,019. The card doesn't say that I'd have put in $41,000 of my own money.

### 9. "where did schd go? and why is qqq only 6%"
- As the guide, `current_mix` gives no reason for SCHD, so I answered "I don't have that data" (rule 8).
- I called `propose_change({swap:{us_equity:'QQQ'}})`. The card shows before and after volatility (13.7% to 15.4%), bad year ($4,269 to $4,138), fees ($4 to $8), and funds "QQQ, VXUS, BITO, VWO" **without weights**, so Tyler can't see QQQ would be 50%. My reply gave the 50% from the tool result.
- Self-critique as the guide: I also wrote "VOO already covers most of the same US companies", which no tool returned. The validator doesn't catch unsupported claims that contain no numbers.
- I tapped **Apply** and the tray updated (QQQ 50%, VXUS 42%, BITO 5%, VWO 3%; bad year **$4,140**, versus $4,138 promised on the card, which is resampling noise). The big mix card in the transcript **still shows the old VOO 47% mix**. It went stale without any marker.
- "Open the full mix" appends a *second* full report at the bottom. The 2008 replay is still missing.

### 10. Chip: "Markets today"
- This one works without the AI. It showed ten flags for a **US** user, five of them Canadian (Canada policy uncertainty 576.843, Bank of Canada rate, Canada CPI, Canada curve, USD in CAD).
- Values are raw with no units ("117.919", "219.209", "1.181").
- "US dollar in Canadian dollars, 12-month change: 1.4164" is an exchange-rate level labeled as a change.
- Headlines include "Thieves Stole Nvidia Trailers. They Got 20 Tons of Sand".

### 11. Size of the transcript
- After the first report the page was 14,947 px, and it reached 20,380 px (about 25 phone screens) after re-opening the mix.
- It held 25 cards: 17 answered question cards (15 questions, the age gate, and the re-asked Q6), 2 profile cards, 1 ladder, 1 shelf, 2 mix reports, 1 proposal, 1 compare and 1 context card.
- The header isn't sticky, so the market and assistant controls are far off-screen.
- The dock (composer plus three chip rows) is sticky, but its background is transparent (`rgba(0,0,0,0)`), so cards scroll visibly *behind* the chips.

### 12. Reload
- I reloaded the page. Answers, level, funds and monthly add were all gone (`answers: {}`, level 3). Only the market persists in localStorage. On a phone, where the browser often evicts background tabs, one switch to Robinhood to check a price loses the whole session.

### 13. Skip path
- On the fresh load I opened the tray, tapped **5**, then "Open the full mix". That gave a full level-5 report in **3 taps**, with no 18+ gate and no self-check (`profile: null`, `adult: false`). The capacity cap only binds people who take the self-check honestly.

---

## Time to first portfolio
- Guided path, as Tyler did it: 1 market tap, 1 chat message, 1 age tap, 15 answers plus typing the amount and tapping Continue, 2 taps to fix Q6, 1 "Use this level", 3 fund adds (tap, type, Enter each), 1 "Build the mix". That's about 26 interactions and about 18 phone screens of scrolling before the first report of *his* mix. Realistically 4 to 6 minutes.
- Skip path: 3 taps, under 10 seconds, but nothing tells you it exists or that it bypasses the check.
- For comparison: Robinhood takes 3 taps to a QQQ order screen. M1 builds a pie from typed tickers in about a minute. Betterment asks about 6 questions (age, income, goal) and shows a 90/10 portfolio.

## What delighted Tyler
- The one-year and ten-year range cards are in *my* dollars ($5,000). That's much better than "rate your risk tolerance 1 to 10".
- Fees in dollars ("$4 a year", "$74 over 10 years") are clearer than Robinhood or M1.
- The proposal card shows before and after for bad year and fees, and changes nothing until Apply.
- The BITO crypto check is honest. The guide doesn't cheerlead.
- The first report renders in about 0.3 s. The compare table appeared instantly.
- Crisis replays: "the 2020 crash would have been -21%" lands better than a volatility number.
