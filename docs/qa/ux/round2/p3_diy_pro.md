# p3_diy_pro (round 2, v2.1): Priya, 41, Calgary, experienced DIY

Status: COMPLETE. Real page at http://localhost:8765/mock.html in my own tab (tab-14), 1440x900. I played the guide via window.__mock following the RULES; the validator accepted the reply on the first try.

Test-harness notes (not product bugs):
- Other testers share this origin's localStorage. My saved state was overwritten about 9 s after it was written, and the market key changed under me. To test resume, I put back the exact state blob the page had written (captured from storage at 04:25:36) and reloaded at once. That stands in for Priya's own browser, where nobody else writes.
- `requestAnimationFrame` never fires in this background tab (measured: "raf timeout" while visibilityState=visible). So the page's auto-scroll (`push()` → rAF → scrollIntoView) cannot be judged here. I do not report any "did not scroll" as a bug. Screenshots were blank or offset whenever the document was scrolled (same as round 1), so I read most of the page from the DOM.

---

## 1. Landing
A shared "Resume where you left off? Level 2 · $300,000 CAD · 10 answers" card from another tester was showing. I tapped **Start over**. The thread had 0 blocks. The tray showed "Reference mix, level 3 · not checked against your answers" with 9 funds, **Edit funds** and **Reset to reference**.

## 2. Tray → Edit funds (skipping the survey)
One tap put the full mix card in the thread: dollars and whole units per fund, "Left over in cash: $193 CAD", Edit funds / Set my own weights / Copy as a list, a one-fund comparison (ZBAL), crisis replays in dollars, "Where the money is" and Show me how. **First full mix: tap 2 (1 without the shared resume card), t = 26.3 s after navigation start.** That includes about 6 s of page load in this harness and several seconds of tool latency per action. For a human this is about 5 s.
The funds editor opens *below* the 9-row holdings table. In the first screenshot after the tap, the table filled the viewport and no editor was visible. Inside the editor slot there is a one-line gate: "The guided build is for adults... [I am 18 or older]". That is one extra tap, which is reasonable.

## 3. Swapping each class
The shelf has 10 classes, each a 6-option dropdown with fee and a Remove button, plus "Add your own fund".
- US stocks VFV → **XUU**. The card updated in place: still 1 card and 1 block. XUU shows "fee n/a". XUU's fee is still missing from the data, same as round 1.
- International FLUR → **XEF**, EM VEE → **XEC**. Fees went from $12 to $14 (0.14%).
- VALT was dropped below 2%, and the note now reads "VALT", not "VALT.TO" (fixed).

## 4. Adding XAW and XEF
- Typed XAW + Enter. The card showed "XAW is not held in this mix. Hold at least [2]% [Apply]", and the shelf row read "XAW ... · Added · not held". This is honest. Round 1's "In the mix" card that lied is fixed.
- Typed XEF + Enter while XEF was already held. **Nothing happened.** There was no message, and "XEF" stayed in the field (app.js:1007 returns true silently).

## 5. Own weights (XUU 40, XEF 20, XIC 20, ZAG 20)
Tapped **Set my own weights**. The grid appeared just below the fold (top at 917 px in a 900 px viewport), so the tap looked like it did nothing until I scrolled. The grid was prefilled with the model weights, which total **99%**, and read "Total 99%. It must add up to 100%." I typed 8 fields. At 100% the line still reads "Total 100%. It must add up to 100%."
The grid lists only the 9 held funds. **XAW, which I had just added, cannot be given a weight.**
Tapped **Use these weights**. The result was excellent: "Your own weights, 4 funds · they behave like level 4.2" with exact 40/20/20/20 weights, $4,000/$2,000... units, "XUU is 40% of the money but 50% of the risk", 2008 replay −29%, "Where the money is: 40% US, 40% Canada, 20% International developed", "About 60% is exposed to foreign currencies (not hedged)". The one-fund comparison switched automatically to **ZGRO (80% stocks)**: fees $13 vs $18, volatility 9.0% vs 8.8%, 2008 −$2,908 vs −$2,960 on $10k. Still 1 card and 1 block.
Taps to her own mix: about 23 (Start over, Edit funds, 18+, 3 dropdowns x2, XAW add x2, XEF add x2, Set my own weights, 8 fields, Use). t = 178.8 s in the harness, about 90 s for a human.

## 6. Amount 120,000 and copy the list
Tray Amount = 120000 (later "120k" parsed fine). The card updated in place: XUU $48,000 / 615 units, XIC $24,000 / 415, XEF $24,000 / 458, ZAG $24,000 / 1,773, "Left over in cash: $139 CAD", fees $152 CAD (0.13%).
Copy as a list: the clipboard was denied in this pane, so the fallback card "Could not copy. Select the text instead." appeared with a pre-selected textarea (good fallback). The copied text was:
"The mix at level 4.2 with the funds you chose, applied to $120,000 CAD. Hypothetical; not an order. / XUU 40.0% $48,000 CAD 615 units / ... / Left over in cash: $139 CAD / Data to 2026-08-31".
The header says "level 4.2" and "the funds you chose", but these are her own weights. There is no unit price per line, although current_mix has price 77.9319 for XUU.

## 7. Reload → resume
The resume card said "Resume where you left off? **Level 3** · $120,000 CAD". It does not mention own weights or 4 funds, and she never chose level 3. Tapped Resume: the page was on US from shared storage and **switched back to CA itself**. Own weights, the XUU/XEF/XEC swaps, XAW pick and $120,000 all came back, in 1 card. **Fixed since round 1.**

## 8. Market US and back
- US: the CAD mix was stashed in mixByMarket, and the US reference mix showed "$120,000 USD". **The amount was relabelled CAD → USD without conversion or any note.** The tray and card say "Your choices, level 3" / "What the model does with the funds you chose", but she made no US choices.
- Back to CA: her own-weights mix returned intact. **Fixed since round 1** (round 1 wiped everything).

## 9. Edge cases a DIY user hits next
- **Tray level 4 while on own weights:** the highlight moved from 3 to 4, st.level became 4, and the mix did not change. There was no message; only a check line deep in the card lost "That is not level 3". Before the tap, the selector showed 3 pressed next to a header saying "behave like level 4.2".
- **XAW "Hold at least 5%" → Apply while on own weights:** minimums became {XAW.TO: 0.05}. The mix and card did not change and no message appeared. The card still says "XAW is not held: at this level the optimizer gave it no weight. You can set a minimum to hold it anyway." That is false twice: no optimizer ran, and the minimum she just set does nothing.
- **Let the model decide:** this discarded her 40/20/20/20 with no confirmation or undo. The mix became level 4, 8 funds, with XAW at 5.0% labelled "Equity" rather than a class name. Reopening Set my own weights prefilled the model weights, so she had to retype all 8 fields.
- **Shelf swap XIC → VCN while on own weights:** swaps.ca_equity=VCN.TO and the dropdown shows VCN. **The mix still holds XIC 20%**, now labelled "Equity" instead of "Canadian stocks". The Canadian-stocks row jumped into the collapsed "Other asset classes (no weight at this level)" section. The shelf shows one fund and the mix holds another. This is the round-1 bug class, now in own-weights mode. Swapping back to XIC restored it.

## 10. Chat
Blocks before my first chat message: **1** (the live mix card).
I asked: "How does my mix (XUU 40, XEF 20, XIC 20, ZAG 20) compare with XEQT, which I hold in my TFSA? Also the page says XUU fee n/a, I think it is 0.07%."
- **The self-check card opened uninvited.** The word "mix" matched app.js:328 on the first message, and "Canada" was parsed from TFSA. The setup showed "Add XUU, XEF, XIC, ZAG, XEQT as your own picks" **pre-toggled ON**. With one Continue, she would add her comparison fund XEQT to her mix.
- The AI reply went in above the open check card (as designed). As the guide I used current_mix (it now exposes slot_key, units and price; fixed), compare_one_fund (ZGRO only, with no ticker parameter), and etf_profile for XEQT and XUU. There is **no tool that runs the same report for XEQT**, so the honest answer was "not comparable side by side". XEQT's card shows worst drop −17.6% over 84 months, while the mix shows a 2008 replay −29%. XUU fee: "I don't have that data."
- "Continue later" collapsed the check into "Self-check paused · 0 of 10 answered · Continue". Blocks after that: **6** (mix, user, AI, 2 fund cards, paused line). There were no duplicate cards.
- The fund card reads "fee | fee n/a" (the label is repeated in the value).

## 11. Fee figure accuracy
The checks say "Fee not in the data for XUU; the fee figures cover the other funds only." But $152 = 0.127% x $120,000: the other funds' *average* fee applied to the whole amount, including XUU's $48,000. "Other funds only" would be about $91. If XUU is 0.07%, the true figure is about $125, so the page overstates it by about $27 and describes the method wrongly.

## Metrics
- (a) Blocks before the first chat message: 1. After the self-check: n/a, since Priya skipped it. The uninvited check opened on chat; after "Continue later" there were 6 blocks.
- (b) Taps to the first full mix: 2 (Start over on the shared resume card + tray Edit funds). Taps to her own-weights mix: about 23.
- (c) Seconds to the first full mix: 26.3 (harness, includes about 6 s load plus tool latency). To the own-weights mix: 178.8.
- (d) Duplicates: none. There was one mix card through about 20 updates, a market round trip, resume and chat, and one self-check card. There were no live buttons on superseded mix cards.
- (e) Silent changes: the 7 listed in sections 4, 8 and 9 above (XEF re-add, CAD→USD relabel, level tap on own weights, minimum on own weights, Let-the-model-decide wipe, VCN swap on own weights) and the uninvited self-check with pre-toggled picks.

## Verdict as Priya
This is now a tool I would actually use. I could skip the survey, swap every sleeve, type my exact weights, see my dollars and units for $120k, compare with an 80% one-ticket fund, and come back tomorrow to the same thing. Three things would still make me distrust it:
- Own-weights mode ignores two controls without saying so (the minimum and the shelf swap).
- The fee total quietly guesses XUU's fee.
- I cannot compare against XEQT, the fund I actually own.
