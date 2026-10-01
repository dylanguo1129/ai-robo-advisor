# p2_level_cap - Jordan, 29, Vancouver (round 2, v2.1)

Status: COMPLETE
Persona: 20+ year horizon (retirement), partial emergency fund, uneven income, this money is 50-75% of savings. Wants level 5.
Page: http://localhost:8765/mock.html, own tab, desktop width (plus one 375 px phone pass at the end).
Method note: the Browser pane was hidden for most of the run, so coordinate clicks failed ("page is not compositing frames"). Taps were delivered as DOM `element.click()` on the real buttons, typing as `#q` value + `#composer` submit. Screenshots worked only for the phone pass at the end.

## Metrics (from the DOM)

| Metric | Value |
|---|---|
| Blocks in #thread on load | 1 (a "Resume where you left off?" card from another tester: "Level 2 · $300,000 CAD") -> tapped Start over -> 0 |
| Blocks before first chat message | 0 |
| Blocks at the self-check result screen | 4 (user msg, AI reply, my typed "60%" msg, the one self-check card) |
| Blocks after choosing a level (card collapsed + mix) | 5 (… summary card, mix card) |
| Taps landing -> first full mix (my real path) | 20 (incl. Start over, one wasted Continue without the 18+ box, a typed answer, three level-5 attempts, Keep level 4) |
| Taps landing -> first full mix (shortest path) | 14 (send message, 18+, Continue, 10 answers, Use level N); 15 if a resume card appears |
| Seconds landing -> first full mix | 206.8 s (performance.timeOrigin to mix render). Inflated by agent round-trips (about 5-10 s per step); the human equivalent is roughly 60-90 s |
| Duplicated live cards | None. Always 1 `.card-check`, 1 `.card-mix`. start_self_check called while open returned `{"shown":"setup"}` and added nothing |
| Live buttons on superseded cards | None (the chat preview card is `is-done`, all buttons disabled) |

## Transcript

1. Landing: resume card from someone else's session -> Start over. The thread is empty; the tray shows "Reference mix, level 3 · not checked against your answers".
2. First message: "Hi! I'm 29, in Vancouver. I want to invest $40k CAD for the long haul (retirement, 20+ years), adding $500 a month. I want the most aggressive setting, level 5."
   - The page opened the self-check setup immediately, prefilled: "From your message: Canada · Retirement · $40,000 CAD · +$500 CAD/mo". Canada and Retirement were pressed, the amount was 40000 and monthly was 500. 18+ was not ticked (correct).
   - As the stand-in guide I called start_self_check again (no duplicate card), then replied with the AI disclosure and "suggestion, not a ceiling". The validator accepted it.
3. Tapped Continue without ticking 18+: a warning appeared, but it repeats the muted note under it word for word ("The guided build is for adults. Anyone can use search…"). It never says "tick I am 18 or older".
4. Ticked 18+ -> Continue -> 10 questions. Retirement goal, so the withdrawal-length question was included (10 of 10).
   - Q1 emergency: Partly. Q2 debt: No. Q3 start: 20 years or more. Q4 how long: More than 10 years.
   - Q5 share of savings: I typed "it's about 60% of everything I have saved" in chat. No AI turn happened. The card showed "From what you wrote, this looks like "50% to 75%". Tap it to confirm." with a dashed pre-select. I tapped it.
   - Q6 income: It varies a lot. Q7 one-year range: widest ($36,244 to $48,708). Q8 sharp fall: Buy more. Q9 ten-year: widest (worst crisis replay −$15,376). Q10: Missing out on gains.
5. Result: "Your situation allows level 4 / Your comfort with ups and downs points to level 5 / because of: …" with 5 rows and Change links, then "Suggested: level 4, Growth. It is the lower of the two." A chooser lists 1-5 in my dollars; level 5 is tagged "Above your self-check".
6. Route 1, chooser: tapped row 5 -> the primary button changed to "Use level 5" -> tapped it -> an in-page dialog opened: "Level 5 is above what your answers suggest". It shows the bad year, 2008, 2020 and 2022 in dollars for level 5 against level 4, with Keep level 4 / Change that answer / Explore level 5 anyway. Escape closed it with nothing changed.
7. Route 2, tray: tapped "5 ↑" in the tray -> the same dialog. Tapped Keep level 4 -> the check collapsed to "Self-check · suggested 4 · chosen 4" and the full mix card appeared (first full mix).
8. Route 3, chat: "just give me 5". As the guide I called propose_change({level:5}). It returned a read-only preview with "Explore level 5" / "Not now". My reply (vol 8.6%->10.5%, bad year $34,672->$33,828, fees $50->$46, the three binding answers) passed the validator.
9. Route 4, chat: "why can't I pick 5? I'm 29, I won't touch this for 30 years." I answered that 5 is allowed, the horizon was not the limit and three cushions were, then listed the two ways forward. It passed the validator.
10. Tapped "Explore level 5" on the chat preview -> the same dialog opened, and the preview card went `is-done` with both buttons disabled at the same moment. I pressed Escape: the level stayed at 4 and the preview card stayed dead with no status line.
11. Tray 5 -> dialog -> "Explore level 5 anyway". The mix card updated in place to "Level 5 · above your self-check (suggested 4)". The tray and the summary ("suggested 4 · exploring 5") were labelled too. The mix card was 3,234 px above the viewport when this happened.
12. Review 12 answers -> the result screen reopened in place (same card), with level 4 pre-selected and a primary button "Use level 4", even though I was on level 5.
13. Changed Emergency savings Partly->Yes: the page went straight back to the result screen, still suggesting 4. There was no note; the Emergency row just disappeared from "because of".
14. Changed Share of savings 50-75%->25-50%: still 4, no note. The only row left reads "Income: It varies a lot, together with the other cushions, one step lower", but no other cushions remain.
15. Changed Income -> Mostly steady: capacity 5, "Suggested: level 5 … It is the lower of the two." While the result was open, the tray and mix still said "Level 5 · above your self-check (suggested 4)" (stale). Tapped Use level 5: explore cleared and a note "You changed "Income"; the suggestion went from 4 to 5." appeared. The mix card moved to the bottom of the thread.
16. Phone pass (375x812, reload, Start over): the tray is wider than the screen (section G).

## Top-to-bottom read of the final thread

0 user (first msg) / 1 AI disclosure / 2 user "it's about 60%…" (no reply, and the card note that answered it is gone) / 3 NOTE "You changed Income; suggestion 4->5" / 4 summary "suggested 5 · chosen 5" / 5 user "just give me 5" / 6 AI "suggested level 4 because three answers…" / 7 dead preview card / 8 user "why can't I pick 5?" / 9 AI "…took it one step lower, to level 4" / 10 mix card (level 5).

It is not clean. The income-change note (3) and the "suggested 5" summary (4) sit above messages 5-9, although they happened after them. Read top to bottom, the thread says "suggested 5", then the guide twice says "suggested 4". My exploration of level 5 (step 11) left no trace in the thread. The two answer changes that did not move the level left no trace either.

## Section G - phone (375 px)
- `#tray` is a one-column grid whose track sizes to content: 456 px wide in a 375 px viewport (scrollWidth 488). The Risk level row shows 1-4. **Level 5 sits at x 384-472, off screen.** The Monthly add field and the allocation bar are cut off, and the tray toggle summary ("Level 3 · Bad year … · Fees a…") is clipped under the close "×". This happens at text size 1.0 and gets worse at A+ 1.15 (the toggle's right edge moves from 472 to 543).
- The close button exists, and Escape sets aria-expanded=false.
- The A+ button always reads "A+" and has no pressed state, so you cannot tell whether it is on (text size 1.15 came in from shared storage).

## Numbers that disagree for the same level and amount ($40,000)
- Level 5, 2008: −$15,376 (Q9, chooser, dialog) vs −$15,433 (built mix, one-fund table).
- Level 5 bad year: $33,812 (chooser, dialog) vs $33,828 (preview, mix, tray).
- Level 5 one-year range: $36,244-$48,708 (Q7) vs $36,304-$48,700 (mix).
- Level 4: bad year $34,676 vs $34,672, 2008 −$10,616 vs −$10,618, COVID −$5,676 vs −$5,674.
- Level 4 fees: "$50 CAD (0.13%)" and "Fund fees average 0.13%" vs "fund fees of 0.12% a year would cost about $839" in Checks.
