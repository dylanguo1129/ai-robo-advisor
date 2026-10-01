# p5_retiree, round 2: Linda, 63, Halifax

Status: COMPLETE. I ran the whole flow in my own browser tab (tab-15) at http://localhost:8765/mock.html. The tester played the Claude stand-in and followed the page's RULES. Evidence comes from DOM reads, `window.__mock` payloads and a few screenshots. The screenshot tool often timed out while the pane was hidden, so most layout evidence comes from `getBoundingClientRect` and `scrollWidth`.

Persona: Linda retires in 2 years. She has 300,000 CAD and a pension. She is very loss-averse, needs income and uses A+. She types her withdrawal with a minus sign and wants to know how long the money lasts. She asks about the war in the news, and she wants crisis replays in dollars.

---

## Measurements

| Metric | Value | How it was measured |
|---|---|---|
| (a) Blocks in `#thread` before the first chat message | 0 (it was 1 on load: the "Resume where you left off?" card, which I cleared with Start over) | `#thread > *` count |
| (a) Blocks after finishing the self-check | 6: 4 chat turns, the 1-line self-check summary and 1 mix card | same |
| (b) Taps from landing to the first full mix | 18 in total. That includes Start over (forced by shared storage), A+, a click into the composer to type one answer, and the 18+ checkbox. The essential path is about 15 taps. | counted by hand |
| (c) Seconds from landing to the first full mix | 219 s. This includes 2 chat round-trips played by the stand-in, which added about 60-90 s of tester overhead. | `Date.now()` at landing (after the 2.5 s load) and at the "Use level 1" tap |
| (d) Duplicated live cards | None. There was always exactly 1 `.card-check` and 1 `.card-mix`. The guide called `propose_change` twice with the same arguments and two preview cards appeared; the older one was disabled and labelled "Replaced by a newer preview". | DOM counts |
| (e) Silent changes | 3 (listed below) | |

## Walkthrough

1. **Landing**
   - The Resume card appeared. Another tester's state had overwritten the origin's storage: "Level 2 · $300,000 CAD · 10 answers". I tapped Start over, which left 0 blocks.
   - A+ set `--text-scale: 1.15` with CSS `zoom` and `aria-pressed=true`. The button label stays "A+", and there is only one step.
2. **First message**
   - I typed: "I'm 63 and retire in 2 years. I have 300,000 saved plus a small pension. I need income and I really hate losing money. I plan to take out -1500 a month. How long would my money last?"
   - The setup card opened below the chat and was prefilled: "From your message: Retirement · $300,000 CAD · **+$1,500 CAD/mo**". The field "Monthly addition (CAD, optional)" held `1500`, and PAGE STATE said `"monthly":1500`.
   - **The minus sign was lost, so her withdrawal became a contribution.** Cause: `monthlyRx` in app.js line 51 has no sign and no "take out/withdraw" verbs, and line 575 always prints `+`. The guide (the stand-in) had to point this out.
   - I typed -1500 into the field and tapped Continue, and `st.monthly` became -1500. The setup field's label never says that a minus sign means a withdrawal. The mix card's field does say so: "Monthly add (minus to withdraw)".
3. **Questions**
   - "Emergency savings": Yes. "High-interest debt": No. "Start taking money out": "In 2 to 4 years". The boundary is now clean ("In less than 2 years" / "In 2 to 4 years"), and the round-1 G1 lock-out did not happen.
   - For "How long will you keep taking money out", I typed "For the rest of my life, hopefully 25 years or so." The reply was inserted above the open card. `answer_self_check(B2,'10plus')` added a dashed pre-select and the line "From what you wrote, this looks like 'More than 10 years'. Tap it to confirm." I tapped it.
   - "Share of savings": More than 75%. "Income": Mostly steady; there is still no option for pension or guaranteed income.
   - The one-year range was in her dollars; she chose the narrowest. For "$300,000 to $240,000" she chose "Sell some".
   - The ten-year question showed dollars plus the worst crisis replay; she chose the first option. For "Worries" she chose "Losing money".
   - **The one-year and ten-year options ignore her -$1,500/mo.** app.js lines 628-629 build them from `ladderRows()` × amount. She sees "$374,468 to $452,466 after ten years" at level 1. With $18,000 a year coming out, the mix card later shows a 10-year middle outcome of about $201k.
   - On screen the text runs together: "$452,466 CAD**worst** crisis replay −$10,740 CAD". The `<small>` is inline, and index.html has no rule for it.
4. **Result**
   - The result read: "Your situation allows level 2 / Your comfort ... points to level 1 / because of: One-year range: Range for level 1 points to level 1 [Change] / Ten-year outcomes: Ten-year outcomes for level 1 points to level 1 [Change] / Losing vs missing out: Losing money points to level 1 [Change] / Suggested: level 1."
   - The level chooser was in her dollars:
     - L1: 17% stocks, bad year $296,100, 2008 −$10,740
     - L3: $273,780 / −$54,660
     - L5: $253,590 / −$115,320
   - The header says "10 questions", but the review link says "Review 12 answers".
   - The chooser shows nothing about how long the money lasts.
5. **Use level 1**
   - The card collapsed to "Self-check · suggested 1 · chosen 1 / Review 12 answers / Change level / Start over", and one mix card appeared below it.
   - Mix at level 1:
     - 70.2% CASH, 7 funds, with dollars and units per fund. "Left over in cash: $201 CAD".
     - A one-fund comparison with XINC (fees $323 vs $570; 2008 −$10,734 vs −$11,058).
     - 7 crisis replays in dollars.
   - Withdrawal line: "Taking out $1,500 CAD a month: the money lasted all 10 years in 100% of simulated paths." The default horizon is 10 years, even though she answered "More than 10 years".
6. **Years changed to 25**
   - The line changed to "the money lasted all 25 years in **29%** of simulated paths. In the worst 10%, it ran out after about 21 years." The middle outcome at year 25 is $0 CAD.
   - The same edit also changed the headline numbers with no note: "8 years in 10" went from $300,990–$317,880 to $301,680–$318,030, "Bad year" went from $296,100 to $296,880, and "Chance of a losing year" went from 1 in 12 to 1 in 13.
7. **Chat: the war**
   - I asked: "I keep seeing the war on the news. Should I wait until things calm down before I put my money in?"
   - The stand-in called `market_context` and `current_mix`, then answered under rule 6: context only, the GPR index is above its usual range, the research finding, bad year $296,880, and the 2008 and 2022 replays. The validator accepted the reply the first time.
   - The Market context card had problems:
     - The headlines are all "technology" (Nvidia, TSMC, "Thieves Stole Nvidia Trailers"), with nothing about the war.
     - "US dollar in Canadian dollars, 12-month change: 1.4164" is a rate, not a change.
     - Several flags are dated 2026-09-30, one day after today.
     - The footer is raw: "Kept from the fetch of 2026-09-28T18:16:01Z: the refresh ... was rate-limited".
8. **Level 3 above the self-check**
   - Tapping level 3 in the tray opened the sheet: "Level 3 is above what your answers suggest".
     - It named the capacity answers, each with a Change link.
     - Level 3 on $300,000: bad year $273,780, 2008 −$54,660, COVID −$30,300, 2022 −$32,160. Level 1 for comparison: $296,100 / −$10,740 / −$8,940 / −$7,110.
     - Buttons: Keep / Change that answer / Explore anyway.
   - Explore anyway updated the mix card in place: "Level 3 · above your self-check (suggested 1)". The summary now reads "exploring 3".
   - **Withdrawal line at level 3: 81% of paths last 25 years, compared with 29% at level 1.** The sheet does not show this; it shows only the downside.
   - Some numbers disagree with each other:
     - Level 3's bad year is $273,780 on the sheet but $277,860 on the mix card.
     - The 2008 replay at level 1 is −$10,740 on the sheet but −$10,734 on the mix card; COVID is −$8,940 vs −$8,959.
9. **Chat: "Why does the safe level 1 run out sooner than level 3?"**
   - The stand-in explained the trade-off using tool numbers: planning return 3.2% vs 5.1%, 29% vs 81% of paths lasting 25 years, and 2008 −$10,734 vs −$54,636.
   - Its `propose_change(level 1)` preview shows volatility, bad year and fees, but **not the withdrawal line**.
   - Tapping "Not now" greyed out the buttons with no status text.
10. **Phone (375×812)**
    - The tray is wider than the screen: `#tray` scrollWidth is 488 against a clientWidth of 375 at normal size, and 488 vs 326 at A+.
    - The peek button's no-wrap text ("Level 3 · Bad year (1 in 20) $9,126 CAD · Fees a year $12 CAD") is 456 px wide.
    - Opening the tray focuses × and scrolls the content 87 px sideways. "The mix" heading and level 1 are cut off on the left, level 5 on the right, and × sits on top of the peek text.
    - The close button works, and Escape closes the tray and returns focus to the toggle.
    - At A+ the header wraps: "Robo-/Kit".

## What now works (compared with round 1)

- Amount and goal from the first message prefill setup. Round 1 showed 10,000.
- There is no G1 lock-out at "2 years": the boundary is clean and the withdrawal-length question is asked.
- One live self-check card. Chat replies go above it, typed answers pre-select, and old cards are disabled.
- The result names the answers in plain words with Change links. Round 1 showed "C3"-style IDs.
- The level chooser and the above-self-check sheet use her dollars, and she can explore higher levels. Round 1 disabled them and used a hard-coded $10,000.
- Crisis replays are in dollars, both on the mix card and in `current_mix.stress_tests[].dollars`. Round 1 showed percentages only.
- Monthly accepts a minus sign, and the mix card shows a withdrawal line with years. Round 1 reset -1500 to 0 without a message.
- The mix card updates in place. Superseded previews are disabled and labelled, so the round-1 stale "Use this level" reset is gone.
- Dollars and whole units per fund, "Copy as a list", "Copy summary" and "Copy for AI" exist. Round 1 had no order list.
- Fixed label bugs: "1 year" (was "1 years"), and fee checks now show "$4,319 CAD" (previously the $ sign was missing).
- The A+ control exists.
- Save/resume exists.
- The tray has a close button and responds to Escape.
- The validator accepted every reply the first time; round 1 had a false rejection.

## How Linda felt

She was relieved to see her $300,000 and dollar crash replays everywhere. She was confused that her "-1500" became "+$1,500". She was alarmed that the "safe" choice runs out in 71% of 25-year paths. She found that out only because the chat and the level-3 exploration revealed it; the self-check steered her to level 1 without showing that trade-off. She would print this for her adviser. She also wants the numbers after inflation.
