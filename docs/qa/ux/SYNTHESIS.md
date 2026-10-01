STATUS: COMPLETE

# Robo-Kit: product synthesis and backlog (28 Sep 2026)

Inputs:
- 5 research lanes: Canadian robos, US robos, DIY tools, AI investing, and UX and regulation. Files are `research_*.md` in this folder.
- 7 persona walkthroughs on the real page:
  - p1 Mei: first-time investor
  - p2 Jordan: wants level 5
  - p3 Priya: DIY pro
  - p4 Tyler: US, on a phone
  - p5 Linda: retiree
  - p6 Daniel: CFA skeptic
  - p7 Sam: keyboard user, low vision
- A read-only check of `web/app.js`, `web/robokit.js`, `web/assistant.js`, `web/validate.js`, `web/data/core.json`, `docs/PRODUCT_SPEC.md` and `docs/research/regulation.md`.

Nothing in the product was edited. None of this is legal advice. The project's own plan already calls for a written legal opinion before any public launch (regulation.md section 7, Path A item 8).

---

## 1. One-paragraph verdict

Robo-Kit already beats every product we looked at on four things:
- It explains risk in the person's own dollars.
- It shows fees in dollars.
- It uses the whole market as its fund shelf.
- It has a validator-checked AI guide. No major robo-advisor has a grounded chat (US lane, AI lane).

It loses at three moments:
- **The moment a person wants more risk.** Levels above capacity are greyed out, clamped silently, and explained only in a tooltip.
- **The first two minutes.** The age gate plus 15 question cards pile up in the chat thread: 40 to 56 blocks and 13,300 to 28,569 px by the end, measured by p2, p4, p5 and p6.
- **The last mile.** There is no dollar amount per fund, nothing is saved, and some inputs are changed silently.

The plan below fixes the two problems found in testing, both as P0, by removing steps and clutter rather than adding features. It then closes the last-mile gaps that make people fall back to Wealthsimple, Passiv or a single XEQT.

---

## 2. The two problems found in testing: root cause (confirmed in code and by 7 of 7 personas)

### 2.1 A level-4 self-check hides level 5

| Where | What it does |
| --- | --- |
| `web/robokit.js:693` | `can_choose = 1..capacity`. When capacity is the lower score (the binding one), the suggestion is also the ceiling. |
| `web/app.js:505` | Profile-card level buttons above capacity are `disabled`, with the reason only in `title` (a hover tooltip, invisible on touch and to keyboard users, per p4 and p7). |
| `web/app.js:518` `setLevel` | Silently clamps any higher level down to `max(can_choose)`. Tapping 5 gave 2 (p2). |
| `web/app.js:541` | Ladder rows above the cap look enabled, but clicking one does nothing (`return`). |
| `web/app.js:763` | Tray buttons above the cap are disabled. The tray is not re-rendered when the profile changes (p2, p6). |
| `web/app.js:396` | `propose_change` clamps, then draws a "Proposed change" card whose before and after are the same (4 → 4) with a live Apply button. The cap note goes only to the model. |

Scoring makes the capacity cap bind far too often:
- B2 (how long withdrawals last) carries up to 5 of the 15 horizon points. A young saver cannot answer it, and it pushed Tyler (p4) to level 3.
- Three one-step deductions stack (share of savings, uneven income, partial emergency fund). Jordan (p2) went from horizon 15/15 to suggested level 2.
- The cap is easy to game. Changing one answer unlocked level 5 in one tap (p1, p2, p4), and a reload removes the cap entirely (p3).

It protects no one and frustrates honest users.

### 2.2 Onboarding and the chat thread are cluttered

- `push()` (`app.js:261`) only ever appends.
- Answered question cards stay at full height with every option still showing.
- "Change answer" (`app.js:471`) appends a new copy of the question at the bottom and leaves the old one highlighted.
- Every profile confirm appends a ladder and a shelf (`app.js:512-513`). Every "Open the full mix" appends another report.
- Old profile cards keep a live "Use this level" button. Tapping one silently reset Linda's applied level (p5) and Mei's (p1).
- Tool cards render below the AI reply, while the rules make the guide say "the card above" (p1, p4, p6, p7).
- Chips post fake user bubbles, and empty search results post a "0 funds match" card (p3, p6).
- The chat ignores what the person already said (market, goal, $50,000, "$300 a month") and asks again (p1, p4, p5).

Every competitor runs this as a form flow, and none puts the questionnaire into a transcript (US lane). GOV.UK's rules apply directly: ask each thing once, show a check-answers page, and change answers in place (UX lane 3.2).

---

## 3. Risk-level policy (replaces "levels above capacity are disabled")

**Principle.** Robo-Kit *suggests*, and the person *chooses*. The suggestion stays the lower of capacity and tolerance, exactly as today. Choosing above it is allowed with friction that is proportionate and visible, and the choice is recorded. Only the three readiness gates stay hard.

| Case | What the page does |
| --- | --- |
| Level at or below the suggestion | Free, no friction. |
| Above tolerance but within capacity | Free (this is already allowed today). Label: "Above your comfort answers". |
| **Above capacity, no gate fired** | The level is tappable everywhere (profile ladder, tray, ladder, chat proposal). A tap opens the **"Explore above your self-check" sheet**, described below. One explicit tap on "Explore level 5 anyway" sets it. After that a persistent label, "Level 5 · above your self-check (suggested 4)", shows in the tray, the mix card, the export and PAGE STATE. |
| **Gate G2/G3 fired** (no emergency fund, or a lot of high-interest debt) | The *build* stays capped at level 2, as today. Higher levels remain **viewable** in the ladder and in read-only "what level N would do" comparisons. The reason is shown as visible text, never only as a tooltip, together with the one answer that would clear it. |
| **Gate G1** (needs the money within 2 years, **all at once**) | No stock mix is built, as today. It is narrowed so that a phased drawdown (a retiree drawing income for years) no longer fires it (fix RK-05). |
| Before any self-check | All five levels are open. The tray reads "Reference mix · not checked against your answers". The self-check is optional in Path A (regulation.md section 7, item 5). |

**The sheet.** It renders in the page, not in chat, and the AI cannot tap it on anyone's behalf.

> **Level 5 is above what your answers suggest**
> Your self-check suggested level 4. Your comfort answers point to 5, but this answer set the limit: "This money is 50% to 75% of your savings." [Change that answer]
> What level 5 has meant on your $25,000
> - A bad year (about 1 in 20): about $X
> - Replaying the 2008 financial crisis: about −$Y at the worst point
> Buttons: **Keep level 4** (primary) · Change that answer · Explore level 5 anyway
> Small print: "Exploring is a simulation. Robo-Kit does not decide what is suitable for you. You can switch back any time."

- **Escalation.** For two steps or more above capacity, the sheet also shows the three worst crisis replays in dollars, side by side for the suggested level and the chosen one (Vanguard allows up to two steps before asking for a retake).
- **Frequent changes.** If an answer change raises the suggestion, the page adds one line: "You changed 'Emergency savings'; the suggestion went from 3 to 4." This follows FINRA's advice to watch frequent profile changes. It is a note, not a block.

**Why this is right for Path A (sources):**
- **Suggestion = lower of the two** stays. That is CP 31-103 s.13.2, "should reflect the lower of (a) … willingness … and (b) … ability" (BCSC PDF), and Joint CSA/CIRO Staff Notice 31-368 (Dec 2025), which says to avoid a high profile when capacity is low. FINRA calls averaging "a poor practice".
- **Choosing above it with a warning and a record is what even registered firms may do.**
  - CFR FAQ (ASC PDF): after explaining and offering an alternative, the firm "can proceed with the original unsolicited client order", and must "receive recorded confirmation".
  - China CSRC suitability measures Art. 19: after a special written risk warning, if the investor still insists on buying, the firm may sell the product. AMAC guideline Art. 16 requires a record.
  - Betterment offers 101 allocations, labelled relative to the recommendation. Vanguard allows up to two steps. Fidelity Go and Acorns let you pick any strategy.
- **A hard wall is where a discretionary manager has a duty**, such as Wealthsimple, whose recommendation is "a ceiling, not a floor". It also has a human escalation path ("connect with one of our Portfolio Managers"). Robo-Kit is neither.
- **The project's own regulatory plan says so.**
  - Path A: "Risk level is chosen by the user. An optional self-check quiz … does not auto-assign a portfolio." (regulation.md section 7, item 5)
  - R5 suitability checks: "P0 as warnings; P1 as gates".
  - Our inference, not a regulator statement: a hard cap computed from personal answers makes the page look *more* tailored under NI 31-103 s.8.25, not less. Daniel (p6) said the same thing as a professional.
- **Friction is required, not optional.** The FCA criticised services where clients "could disregard advice … without any safeguards or risk warnings".
- **Copy.** ESMA says firms should avoid "giving the impression, that it is the client who decides on the suitability". So the copy says "you chose to explore level 5", never "suitable".
- **The measure is fragile.** Tolerance comes from four items (C1 to C4). Grable (CFA Institute Research Foundation, 2017) warns that very short scales are unreliable. That argues for soft bands over a wall.
- **Why the gates stay hard.** They answer *whether to invest at all* rather than *how much risk*. FINRA's practice is to "make clients aware when investing may not be appropriate". CP 31-103 names a cash or guaranteed-product outcome. Vanguard does not let its loss-aversion result be overridden. CSRC Art. 22(5) keeps a hard line for the lowest category.

What changes in the docs:
- `AGENT.md` rule 5
- `web/assistant.js` RULES rule 5
- `docs/PRODUCT_SPEC.md:178` and §14 R4, which should say "higher levels: explore with a recorded acknowledgement; gates G1-G3 stay hard"

Open decision for the owner: whether G2/G3 should also become "explore with acknowledgement". Our recommendation is no.

---

## 4. Onboarding redesign (P0): one live stepper, one summary, one live mix

**Rule:** the thread is the conversation; state lives in single live cards that update in place.

1. **Landing.**
   - One input and four chips (Build a mix · What is an ETF? · Compare two ETFs · Markets today).
   - "Sources and method" moves to the header so it stays reachable (p7).
   - Chips put text in the composer or open a card. They never post a fake user bubble (p3).
2. **Read the opener, locally and deterministically** (no AI needed). Parse:
   - market words (Canada/CAD/TSX, US/USD)
   - goal words (retire, house, …)
   - amount (`50k`, `$50,000`, `1.5m`)
   - monthly amount (`300/mo`)
   - horizon (`20+ years`, `retire in 2 years`)
   - tickers

   These pre-fill A0, A1, B3, the monthly amount and the shelf picks. They are shown once for confirmation:
   > "From your message: Canada · Retirement · $50,000 CAD. [Change]"

   Tolerance answers are never pre-filled (ESMA: pre-filled answers must be reviewable; tolerance must come from the person's own tap).
3. **The stepper** is one DOM node, **always the last element in the thread while it is open**. On phones it docks above the composer with a visible Close and a "Continue later" button.
   - Header: "Self-check · about 2 minutes · 3 of 9", plus Back.
   - The 18+ question is its first screen, not a separate card.
   - **Core set (9):**
     - A2 emergency fund
     - A3 debt
     - B1 horizon, relabelled "In less than 2 years"
     - B2, only when the goal is not "building wealth" and with a new "Not sure yet" option
     - B4 share of savings
     - B5 income
     - C1 one-year dollar ranges
     - C2 "your $50,000 is worth $40,000"
     - C4 losing vs missing out
   - A0, A1 and B3 are confirmed from step 2.
   - D1 and D2 become an optional "Two quick knowledge checks" after the result.
   - C3 comes back only once it shows a real trade-off (RK-05).
   - Each tap renders the next question **inside the same card**. Focus moves to the question heading, and a polite live region announces "Question 4 of 9".
   - Gates show inline as one line ("Levels 3 to 5 stay locked while you have no emergency savings"), and the flow continues.
   - A contradiction shows as **one clarifying step** that quotes both answers, with buttons named after the questions ("Ten-year range: $395,471 to $799,195 · Change"), never "C3".
4. **Chat while the stepper is open.** The composer stays live.
   - Typed text is first matched locally against the open question (option text plus a small synonym list, and the amount parser). A match *pre-selects* the option and says "Tap Continue to use this". Nothing is recorded until the person taps.
   - Otherwise the text goes to the AI. PAGE STATE then carries the open question's id, text and options. The reply is inserted **above** the stepper, so the question never scrolls away.
   - The AI may call `answer_self_check(question_id, value)`, which only pre-selects.
   - While D1 or D2 is open, the AI does not explain the concept being tested.
5. **The result lives inside the stepper**, merging today's profile card and ladder (one card fewer). It shows:
   - A collapsed "Review 9 answers" list with a Change link on each row (GOV.UK check-answers).
   - Two plain lines, each naming the binding answer with a Change link:
     - "Your situation allows level 4 — because this money is 50% to 75% of your savings [Change]"
     - "Your comfort points to level 5"
   - "Suggested: level 4 (the lower of the two)".
   - **The ladder as the chooser**, scaled to the person's amount. Each row shows the stock share, the bad-year dollars and the 2008-replay dollars.
     - Row 4 is tagged "Suggested".
     - Row 5 is tagged "Above your self-check" and opens the sheet.
     - Gate-locked rows are tagged "Locked: emergency fund".
   - One button: **Use level 4**.
6. **After confirming**, the stepper collapses into a one-line summary card (the same node):
   > "Self-check · suggested 4 · chosen 4 · [Review answers] [Change level]"

   The **mix report is then built immediately** with the default funds. It is a singleton card, and "Edit funds" opens the shelf *inside* it. The shelf shows only the sleeves that have weight at this level; the rest fold under "Other asset classes (0% at level 5)". That removes a card and a "Build the mix" tap.
7. **Later changes happen in place.**
   - "Change" on any answer re-opens the same stepper node, moved to the bottom, at that question.
   - Re-scoring updates the summary and the mix in place, and adds at most one note line.
   - Tray levels behave per section 3.
   - Superseded snapshots (proposal cards, and mix snapshots the AI referred to) get a "Replaced · see latest" stamp, and their controls are disabled.
8. **Two doors.** "Skip to funds" (tray and mix "Edit funds") opens the shelf at any level without the survey. If 18+ is not yet confirmed, a one-line check appears the first time.
9. **Return visit.**
   > "Resume where you left off? Level 4 · 7 funds · $50,000 [Resume] [Start over]"

   This is kept in localStorage, wrapped in try/catch.

**Targets** (re-run the 7 persona scripts after the P0 work):

| Measure | Today (from the persona runs) | Target |
| --- | --- | --- |
| Thread blocks before the first chat message | about 20 (estimate: 18+ card, 15 questions, gate/flag, profile, ladder, shelf; p6 measured 12,050 px before typing) | **4 or fewer** (opener, summary, mix, at most one note) |
| Taps to a first mix | about 26 (phone) | **12 or fewer** |
| Time to a first mix | not timed | **2 minutes or less** (RBC takes 4-5 minutes, Vanguard up to 30) |
| Duplicated question cards; live controls on superseded cards | present | **zero** (enforced by a DOM test) |
| Silent clamps or drops | present | **zero** (every change renders a visible reason) |

---

## 5. Feature matrix (Robo-Kit vs best in market)

| Feature | Robo-Kit now | Best in market (source) | Gap | Priority |
| --- | --- | --- | --- | --- |
| Time to first mix | 18+ card plus 15 cards; about 26 interactions on a phone (p4) | RBC InvestEase "about four or five minutes" (rbcinvestease.com/topics-trends/how-to-get-investment-portfolio.html); Nitrogen "less than 5 minutes" | partial | P0 |
| Choosing above the suggestion | Levels above capacity disabled; silent clamp | Betterment, 101 mixes labelled relative to the recommendation with warnings (betterment.com/resources/recommended-allocation-methodology); Vanguard ±2 steps (personal1.vanguard.com/pdf/vanguard-digital-advice-brochure.pdf) | missing | P0 |
| Naming the answer that set the level | Explanation lines, but the lock reason is a tooltip | Wealthsimple "Why you were recommended this portfolio", with checks as a ceiling (help.wealthsimple.com …26129491261211) | partial | P0 |
| Editing answers in place | Appends duplicates; stale cards stay live | GOV.UK check answers (design-system.service.gov.uk/patterns/check-answers/) | missing | P0 |
| Using what the person already said | Re-asks market, goal and amount | Public Agents: follow-up questions, then a reviewable spec (prnewswire …302729050) | missing | P0 |
| Contradiction handling | Flag card with "C1/C3" buttons | Wealthfront inconsistency scoring (research.wealthfront.com/whitepapers/investment-methodology/); FINRA and ESMA in-flow alerts | partial | P1 |
| Risk in the person's own dollars during the check | One-year range cards in own dollars; C3 has a dominant option | Nitrogen, "real dollar amounts" (nitrogenwealth.com/risk-tolerance-questionnaire/) | ahead | P0 (fix C3) |
| Crisis replays | 7 named replays, % only; rows vanish for young funds | No one in dollars; Portfolio Visualizer worst-10 drawdowns (portfoliovisualizer.com/backtest-portfolio) | ahead | P0 |
| Fees in dollars | Fees per year in $ plus 10/25-year drag | Vanguard "$15 - $16 … for every $10K" (investor.vanguard.com/advice/robo-advisor) | ahead | P1 (add comparison rows) |
| One-ticket baseline | A check line only; no button | Canadian Couch Potato five one-fund mixes (canadiancouchpotato.com/model-portfolios/) | partial | P1 |
| Fund choice per asset class | Whole-market shelf, but only after the 15 questions | Wealthfront add/remove/swap (wealthfront.com/investing); M1 100 slices | ahead | P0 (access) |
| Own weights | None | M1 Pies target % (m1.com/invest/); Portfolio Visualizer | missing | P1 |
| Dollars and units per fund / order list | Weights only | justETF integer-share order list (justetf.com/en/tutorial/orderlist/…); Passiv | missing | P1 |
| Save, resume, share | Only market and tier persist | testfol.io share links plus localStorage (testfol.io/help/) | missing | P1 |
| Printable summary / export | None | Justwealth per-account IPS (justwealth.com/faqs/); testfol.io "Export for AI" | missing | P1 |
| Goal probability and levers | Fan chart only | Vanguard 10,000 scenarios plus funding status; Betterment three levers (betterment.com/help/off-track-goal) | partial | P2 |
| Retirement withdrawals and income | Monthly add ≥ 0 only; no yield in tools | Stock Rover retirement odds (stockrover.com/help/future-simulations/…); Vanguard Digital Advisor | missing | P1 |
| Look-through (region, currency, overlap) | Engine computes region (robokit.js:561) but never shows it | Morningstar X-Ray, $249/yr (wallstreetsurvivor.com/is-morningstar-worth-it/); ETFRC overlap | missing | P2 |
| Account type and tax | TFSA/RRSP glossary only | Betterment Tax Impact Preview (betterment.com/help/how-tax-impact-preview-works); Wealthsimple tax banner | partial | P2 |
| Rebalancing guidance | None | Passiv buy-only by default (passiv.com/help/tutorials/how-to-rebalance-your-portfolio/); NBDB 20% drift rule | missing | P2 |
| Grounded AI guide | Claude plus a number and ticker validator plus page tools | Origin, deterministic modules plus 138 checks (useorigin.com/resources/blog/technical-overview) | ahead | P1 (context gaps) |
| Mobile | No viewport meta; dock covers 308 of 812 px | NN/g bottom-sheet guidance (nngroup.com/articles/bottom-sheet/); native robo apps | partial | P1 |
| Accessibility | Focus drops to body; locked levels invisible to keyboard; px fonts | GOV.UK one thing per page (designnotes.blog.gov.uk/2015/07/03/one-thing-per-page/) | partial | P1 |
| Method and back-test honesty | Pre-registered back-test that honestly shows no edge; method card | testfol.io "what is not modelled" (testfol.io/help/) | ahead | P2 (surface the headline) |
| Price and paywall | Free, no account, no quotas | Portfolio Charts "No paywalls" (portfoliocharts.com) | ahead | skip |

---

## 6. Backlog

### P0: the two problems found in testing and anything that silently misleads

**RK-01: Suggested is not a ceiling; explore above it with a recorded acknowledgement** (M)
- Evidence: problem 1 (section 2.1); p1, p2, p3, p4, p6, p7; US lane (Betterment, Vanguard); UX lane (CFR FAQ, CSRC Art. 19, ESMA); regulation.md Path A item 5.
- Spec:
  - `scoreProfile` (`web/robokit.js`) and `robokit/profile.py` keep `suggested_level`, and add:
    - `within_check = 1..capacity`
    - `gate_cap` (2 if G2/G3, 0 if G1, else 5)
    - `binding_answers`: a list of `{id, answer_text_en, effect}`
  - `can_choose` becomes `1..gate_cap`.
  - `setLevel(l)` in `app.js` never clamps:
    - if `l > capacity` and there is no stored ack, it calls `cardExplore(l)` (the sheet in section 3)
    - if `l > gate_cap`, it opens the gate reason sheet
  - Buttons are never `disabled`. Use `aria-disabled` plus a visible tag ("Above your self-check", "Locked: emergency fund").
  - The ack is stored as `st.explore = {level, suggested, capacity, binding, at}` and shown in the tray sub-line, the mix header, PAGE STATE and the export.
  - `toolPropose` returns `needs_acknowledgement:true` and renders a read-only "What level 5 would do" comparison with an "Explore level 5" button that opens the same sheet. It never renders a same-to-same Apply card.
  - Update `AGENT.md` rule 5, RULES rule 5 ("You cannot confirm for the person; name the binding answer from PAGE STATE") and `PRODUCT_SPEC.md:178`.
  - Tests: Python and JS parity for the new fields, plus a DOM test that no `.lvl` or `.seg` is `disabled`.
- Guardrails:
  - The suggestion stays min(capacity, tolerance) (CP 31-103 s.13.2; 31-368).
  - The ack is a tap by the person on a page-rendered sheet, never through chat text.
  - Copy says "explore" and "simulation", never "suitable".
  - Dollar figures come from ladder rows, not from the AI.
  - Gates stay hard for the build.

**RK-02: The self-check becomes one live stepper; the thread gets one summary** (L)
- Evidence: problem 2 (section 2.2); thread of 40-56 blocks and 13,300-28,569 px (p2, p4, p5, p6); duplicated questions (p1, p2, p7); 62 tabs to a re-asked question (p7); US lane ("none puts the questionnaire into a transcript"); GOV.UK and NN/g wizards (UX lane).
- Spec:
  - In `app.js`, replace `cardAge`, `cardQuestion`, `answer`, `cardFlag`, `showProfile` and `cardProfile` with one `Stepper` object that owns one node (`data-live="check"`).
  - The core set of 9 questions, order and copy are as in section 4.
  - "Back" and "Change" re-render in place. On completion the node becomes the summary card.
  - The ladder merges into the result step, scaled to `st.amount`.
  - Flags become one clarifying step whose buttons are named after the questions.
  - D1 and D2 move to an optional post-result chip.
  - Add a time label ("about 2 minutes").
  - CSS goes in `web/index.html`, including the sticky dock position on phones.
- Guardrails:
  - Questions keep fixed wording (R4.5).
  - The 18+ step stays before any build (R4.7).
  - Tolerance and capacity stay in separate blocks (R4.1).
  - The answer is recorded only on the person's tap.

**RK-03: One live copy of each card; superseded cards are frozen; no no-op proposals** (M)
- Evidence: stale "Use this level" silently reset levels (p1, p5, p6); 3 ladders, 3 shelves and 3 mix cards (p6); a stale mix after Apply (p4, p5); same-to-same proposals (p1, p2, p3, p6); resampling noise shown as a change (p6).
- Spec:
  - `push(node, {key})`: if `this.live[key]` exists, re-render it in place (and move it to the end with a subtle highlight if it is off-screen) instead of appending. Keys: `check`, `mix`, `context`.
  - When the level, funds or amount change, the mix singleton re-renders.
  - Proposal cards become "Replaced by a newer preview" (disabled) when a newer one renders.
  - `toolPropose` builds with the same `nBoot:200, seed:0` as the main build, and Apply sets `st.result = after` without a rebuild, so preview equals applied.
  - If `after` equals `before` (same level, same tickers), return the notes to the model and render nothing.
  - Proposal cards show per-fund weights before → after.
  - `renderTray()` is called whenever `st.profile` or `st.level` changes.
- Guardrails:
  - Apply stays a person-only button.
  - A fixed seed must not hide real uncertainty: bands stay visible.

**RK-04: The chat knows the open question and the profile; typed answers and amounts are parsed and confirmed by tap** (M)
- Evidence: typed answers ignored (p1, p2, p4); the AI contaminated D1 (p1); the guide cannot name the binding answer (p2, p4, p5); reply and card order (p1, p4, p6, p7).
- Spec:
  - `assistant.js` `pageState()` adds:
    - `open_question {id, text, options}`
    - `profile {suggested, capacity, tolerance, binding_answers, explanation lines, within_check, gate_cap}`
    - `explore` status
    - the last 5 page events (level changes with their source)
    - amount and monthly
  - New tool `answer_self_check(question_id, value)`, which pre-selects only.
  - RULES: "while D1/D2 is open, do not explain bond prices or leverage"; "cards appear below your reply".
  - New `parseAmount()` in `app.js` for k, m, commas and $. Values below the minimum show "Enter at least $100", never a clamp.
  - Opener parsing as in section 4, step 2.
  - Tool cards render inside the AI turn, after its text.
  - A monthly amount field is added to the tray.
- Guardrails:
  - Deterministic matching only; the LLM never scores answers.
  - Pre-filled facts are shown for confirmation; tolerance is never pre-filled.
  - No personal data in URLs.

**RK-05: Fix the scoring that makes the cap misfire** (M)
- Evidence: Jordan went from 15/15 to level 2 (p2); Tyler reached level 3 through B2 (p4); G1 blocks retirees before B2 is asked (p5); the Q5 boundary overlaps (p5); C3 has a dominant option (p1, p2, p3, p5, p6); "scores 15/15" jargon (p1, p7).
- Spec (all in both `robokit/profile.py` and `web/robokit.js`, plus `web/data/core.json`):
  1. B2 gets a "Not sure yet" option (3 points). B2 is skipped when A1 = `wealth` and scored as 3, with the summary showing "Not asked: no fixed date".
  2. Deductions from B4 (points ≤ 1), B5 (points ≤ 1) and A2 = partly combine to **at most 2 steps, and at most 1 when the horizon score is 13 or more**. The explanation lists the factors and says "together, one step lower".
  3. G1 fires only when B1 = `lt2` **and** B2 = `once`. For a phased drawdown, capacity is scored normally and an educational note is added: "Keeping the next 1 to 2 years of withdrawals in cash-like savings is a common approach." The check moves from `answer('B1')` to after B2.
  4. B1 is relabelled "In less than 2 years".
  5. C3 options show the ten-year range **plus** that level's worst crisis replay in dollars (`ladderRow.worst × amount`), so higher levels show a worse downside. Until that ships, C3 is left out of the tolerance mean.
  6. Horizon wording: "You won't need this money for 20+ years, which allows up to level 5."
- Tests: update `tests/test_v2.py` and `web/test_robokit.mjs` with the seven persona answer sets as fixtures. Expected: Jordan suggested 4 (was 2); Tyler 4 (was 3); Linda no G1.
- Guardrails:
  - The lower-of rule is unchanged.
  - Log the scoring change in `docs/RESEARCH_LOG.md` before running.
  - Do not add questions to the core set.

**RK-06: No silent changes to inputs, funds or level** (M)
- Evidence: level 5 tap became 2 (p2); SCHD vanished (p4); XEF and XAW were dropped while the button said "In the mix" (p3); XEQT dropped (p6, p7); the market toggle wiped work and the shelf showed a stale mix (p3).
- Spec:
  - For each user-added fund (satellite) with weight 0 or dropped below 2%, the mix card and shelf show "SCHD: under 2% in this mix, so it is not held. Hold at least [2]% anyway?". The input is wired to the existing `st.mix.minimums`.
  - The fund card button says "In the mix · 13.6%" only when the weight is above 0, else "Added · not held".
  - `current_mix` returns `dropped:[{ticker, reason}]`, using the engine's reason only.
  - `st.mixByMarket[code]` is saved and restored in `setMarket` (`app.js:250`). Confirm before discarding changes, and call `_redraw` on the shelf and mix after the switch.
  - The tray amount uses `parseAmount`.
- Guardrails:
  - Never invent why the optimizer dropped a fund.
  - Minimums stay within the engine's caps (the satellite cap).

**RK-07: Numbers that tie out** (M)
- Evidence:
  - the ladder uses $10,000 while the person entered another amount (p1, p2, p4, p5, p6, p7)
  - 0.13% vs 0.12% (p1, p2, p6)
  - the 2008 and 2011 replays silently disappear for user funds (p4)
  - crisis replays in % only (p5)
  - the level-5 back-test is labelled level 4 (p5, p6)
  - a correlation of 1.00 shown for 0.996 (p3, p6)
  - `prob_loss` is not shown (p6)
- Spec:
  - The ladder uses `st.amount` (`app.js:537`; `ladderSub` gets `{amount}`).
  - The engine stress output adds `dollars` and `trough_value`. The mix card reads "2008 financial crisis: −$13,500 (−27%)", and `mixSummary` passes both to `current_mix`.
  - Satellites are backfilled on the extended history, as core sleeves are, so all seven replays remain. A row that is impossible shows "Not available: BITO has 58 months of data" instead of vanishing.
  - The Checks fee line uses the header's fee rate and money formatting (`robokit.js:607`).
  - Back-test for levels 1 and 5: "Nearest tested level: 4 (level 5 was not back-tested)".
  - Correlations of 0.995 and above display as "above 0.99".
  - Show "Chance of a losing year: about 1 in 5" from `one_year.prob_loss`.
  - When a band is wider than 30 points, print a whole-number weight and the band ("25%, between 0% and 50% across resampled histories").
- Guardrails:
  - Every displayed number comes from the engine.
  - The validator pool gets the new fields.
  - Python and JS parity.

**RK-08: Edit funds without the survey** (S)
- Evidence: p3 (blocker for DIY users); regulation.md Path A item 5 (the self-check is optional); DIY lane (no DIY tool gates fund choice).
- Spec:
  - An "Edit funds" button in the tray and in the mix card opens the shelf inside the mix singleton at the current level.
  - If 18+ has not been confirmed, show the one-line check "I'm 18 or older" once.
  - The tray label reads "Reference mix · not checked against your answers" until a self-check is done.
- Guardrails: R4.7 age check; the reference label stays visible.

### P1: close the last mile and fix trust leaks

| ID | Title | Effort | Evidence | Spec (where) | Guardrails |
| --- | --- | --- | --- | --- | --- |
| RK-09 | Dollars per fund, then units, plus a copyable list | M | p1 blocker; p3, p4, p5; justETF order list, Passiv | A "$ on $50,000" column in the mix card and tray rows (amount × weight, rounded to $10). `current_mix` adds `fund.dollars`. "Copy as a list", with the label "The mix at level 4 with the funds you chose, applied to $50,000. Hypothetical; not an order." Units: add `last_close` and `last_close_date` to the universe build (robokit universe/snapshot → ca.json/us.json), show "about N units at the 29 Aug close" rounded down, plus leftover cash. | No broker links, order tickets or affiliate links. The AI quotes tool dollars only. |
| RK-10 | Bad-year and ranges include 2000-02 and 2008 | L | p6: the 1-in-20 figure of −10.5% for 95% stocks comes from a 2011-2026 window (MAX_WINDOW=180, robokit.js:14/190/196); p3 | `project()` bootstraps from the full spliced core history. Weight estimation keeps 180 months. "Show me how" and the method card state both windows. Mirror in `robokit/projection.py`; the ladder and range cards update. | Log it before running; the pre-registered back-test is untouched; parity tests. |
| RK-11 | Save, resume, share | M | p3, p4, p5 (reload wipes everything); testfol.io | localStorage (try/catch): answers, profile, explore ack, level, amount, monthly, mixByMarket. Resume prompt in section 4, step 9. A share link hash carries only the market, level, tickers and swaps. | Never put answers or amount in the URL. Storage is a per-viewer convenience. |
| RK-12 | Compare with a one-fund version and with robo fees | M | p3; CA lane (XEQT, VEQT, ZGRO fees; Wealthsimple 0.5%, Questwealth 0.20-0.25%, RBC 0.50% plus tax, BMO 0.70%); DIY lane pattern 7; RBC Starter, CI single fund | A "Compare with a one-fund version" row picks the asset-allocation ETF nearest the level's stock share from a list in `core.json` (CA: XEQT/VEQT/ZEQT, XGRO/VGRO/ZGRO …; US: AOA/AOR/AOM/AOK if in the universe) and shows fee $, volatility, bad year and replays on the same window. A "Managed robo cost on $X" row comes from `core.json.provider_fees` with URL and as_of. Below $5,000, the one-fund row shows first. | Impersonal wording ("a one-fund version at a similar stock share"). Competitor fees only from dated primary sources. No links to sign up. |
| RK-14 | Mobile layout | M | p4, p7 (no viewport meta, index.html; dock covers 308 of 812 px; the tray sheet covers 82% with no Escape) | Add a viewport meta (check whether the artifact frame already sets one). Solid dock background. After the first message the chips collapse to one scrolling row and hide while the keyboard is open. The tray sheet gets a close button, Escape/Back, aria-expanded and inert background. 44 px targets. The shelf folds 0% sleeves. Sticky Continue in the stepper. | none |
| RK-15 | Keyboard, screen reader, text size | M | p7; p5 (13 px body, 11 px axes) | `#thread` becomes role=log. Focus moves to each new question heading. Option groups are radiogroups with arrow keys and aria-checked. Enter submits the amount. The shelf select commits on Enter or blur, not on arrow keys. Font sizes in rem with a 16 px base and an A/A+ toggle. Axes at least 12 px. Skip link. Names for icon buttons. `th scope=row` in compare tables. | none |
| RK-16 | Shelf truth and data quality | M | p1, p3, p6, p7 (the "lowest fee first" claim is false in 7 of 10 classes; blank MERs; XSTH/XSTP under Canadian short bonds; ZMMK is a mutual fund; XAW region Canada; mojibake in us.json; XUU MER null and silently imputed) | Sort candidates by MER within the eligibility rule, or change the copy to the real rule. Hide null-MER funds from the default six ("fee n/a" if shown). Reclassify TIPS. Exclude non-ETFs. Check regions against "ex Canada", "ex US" and "TIPS" in the name (robokit/classify.py). Fill core MERs. Show "fee unknown, estimated as X" when imputed. Re-encode names as UTF-8. | The classification reasons stay attached to each fund (R6). |
| RK-17 | Retirement income view | L | p5 | A monthly withdrawal input in the projection. The engine returns the percentiles of months until depleted and the monthly income. `dividend_yield` goes into `etf_profile` and `current_mix`, with the mix yield in $ labelled "distribution yield, not a return". A pension question (asked only when A1 is retirement or income and B1 is 4 years or less) enters capacity. Glossary: rrif, sequence_risk, withdrawal_rate. | Hypothetical labels. No "safe withdrawal rate" advice. No tax advice. |
| RK-18 | Validator and guide fixes | S | p3 (VTI rejected), p5 (date format), p6/p7 (card order), p3 (empty cards) | `validate.js` allows tickers that appear in the user's own message or in tool arguments, and treats 2026-08-31 and 31 Aug 2026 as the same. No 0-result search card. RULES say "the card below". | New tickers from the model stay banned. |
| RK-19 | "Your own weights" mode | M | p3; M1, Portfolio Visualizer | The mix card toggle "Set my own weights" gives editable % per fund that must sum to 100, and runs the same report on fixed weights (a new `fixed_weights` engine path in JS and Python). Label: "Your weights, not the model's". Add a mismatch warning when the volatility is closer to another level (R5.5). `propose_change` accepts weights. | The same risk report and the same disclosures. |
| RK-20 | One-page summary and export | M | p5 (take to the adviser), p6 (client files), p1; Justwealth IPS; testfol.io Export for AI | "Save summary" opens a print view: answers, suggested vs chosen level with the ack, the mix with dollars, fees, crisis replays in $, windows, disclosures and data date. "Copy for AI" gives Markdown/JSON. | Labelled as an educational simulation. Generated locally only. |
| RK-21 | Copy and label sweep | S | p2, p3, p5, p6, p7 | Fix "1 years", "fund(s)", the .NE/.TO suffixes, the raw series id V80691344, "$" and currency in Checks, "+" on gains and "−0%", "Keep" → "Add back", "History (months)", a yield tooltip, and the docs/RESEARCH_LOG.md path → a method-card anchor. | none |

### P2: the depth that beats the paid tools

| ID | Title | Effort | Evidence | Spec | Guardrails |
| --- | --- | --- | --- | --- | --- |
| RK-22 | Look-through: region, currency, overlap | M | p3, p6; Morningstar X-Ray is paid; DIY lane pattern 4 | Show `mix.region` (robokit.js:561), plus a currency line (CAD vs USD-denominated underlying, hedged flag), plus a warning when wrappers overlap (for example XEQT plus VFV). Holdings-level overlap only once holdings data is licensed. | Data provenance and dates. |
| RK-23 | Account-type education | M | p3, p6; Wealthsimple tax banner; Betterment | Glossary and notes on TFSA/RRSP/FHSA/taxable and US withholding tax on US-listed vs Canadian-listed funds. | Education only, never "put X in your RRSP" (R9). |
| RK-24 | Rebalancing lessons | M | p1; NBDB 20% drift rule; Passiv buy-only; M1 | "Where would your next $500 go?" (buy-only) and a drift-band simulation. | No order routing or reminders that act. |
| RK-25 | Goal view | S | Vanguard; Betterment | "X of 1,000 simulated paths reach $Y" (the engine already returns `chance_need_to_adjust`), with three lever chips (monthly, years, lump sum). | "Not a guarantee"; net of the person's fund fees. |
| RK-26 | Market-context cleanup | S | p4, p5, p6, p7 | Filter flags by market; percentile bars instead of raw values; fix the USD/CAD "12-month change" (it shows a level); no dates after the data date; a source allowlist that drops promotion and off-topic headlines; fix the "91th" ordinals. | Context never changes the mix (rule 6). |
| RK-27 | French | L | p6 (Quebec, Bill 96) | FR UI strings and data fields. | Legal opinion covers Quebec. |
| RK-28 | Borrowed-money check | S | CA lane (Wealthsimple lowers the ceiling for borrowed money) | A third option on A3, "Some of this money is borrowed", which caps the suggestion at 3. | Do not lengthen the core set. |

---

## 7. What makes Robo-Kit better than every portfolio builder (after P0 and P1)

1. **The only one that names the exact answer that set your level and lets you explore above it with the evidence** (Wealthsimple lists its checks; nobody names the binding one; CA lane).
2. **Risk in your own dollars, end to end.** Range cards during the check, bad-year dollars and **seven crisis replays in dollars**. Nobody shows crisis replays in dollars.
3. **An AI guide whose every number is checked against code.** The major robos have no consumer chat (US lane). Magnifi's chat dodges numbers (AI lane). testfol.io charges $80 a month for AI hand-off.
4. **The whole market, free.** 2,187 CAD and 5,770 US listings on a guided shelf. InvestCube is closed. Schwab only lets you remove three ETFs. Portfolio Visualizer, PortfoliosLab and Morningstar charge.
5. **Fees in dollars against a one-fund version and against managed robos**, dated and sourced.
6. **A first mix in about two minutes**, against RBC's 4-5 and Vanguard's up to 30. No sign-up.
7. **Honest method.** A pre-registered back-test that says it found no edge over a static mix, with windows and proxies disclosed.

---

## 8. Do not do

- Do not remove the lower-of suggestion, do not default anyone above it, and do not average capacity and tolerance.
- Do not let the AI confirm an above-self-check level, press Apply, or record an answer. Only the person's tap on a page control does that.
- Do not let the AI compute dollars per fund, units, withdrawals or fee comparisons. Expose them through tools.
- Do not add broker links, order tickets, "Buy on …" buttons, referral or affiliate links, or issuer sponsorship. Path A requires no economic benefit and no order entry.
- Do not write "recommended for you", "your portfolio", "suitable", "approved", or "best fund". Do not title proposal cards "Recommended change".
- Do not add questions to fix edge cases without removing others. Do not replace the dollar-range cards with a 1-10 self-rating.
- Do not make the chat the questionnaire (LLM-scored free text). Typed answers are matched deterministically and confirmed by a tap.
- Do not put self-check answers or the amount in URLs or share links, and do not send them anywhere.
- Do not show competitor fees or ETF facts without a primary source and a date. Do not claim "beats X" with numbers the engine did not produce.
- Do not add market-timing nudges that change the level or mix because of news.
- Do not chase robo features that need custody or registration (automatic rebalancing, tax-loss harvesting, account linking). Those belong to Path B.
- Do not hide uncertainty with a fixed seed. Keep the bands, and round weights when the bands are wide.
- Do not use typed consent phrases ("type I UNDERSTAND"). A clear sheet with dollar figures and one explicit button is more accessible.
- Do not re-run or edit the pre-registered back-test to make it look better.

---

## 9. Sequencing (fits the course dates in PRODUCT_SPEC section 16)

1. **By about 6 Oct:** RK-05 (scoring), RK-01 (explore sheet), RK-03 (singletons and frozen cards), RK-06 (no silent changes). These fix problem 1 and most of the clutter.
2. **By about 13 Oct:** RK-02 (stepper), RK-04 (chat bridge), RK-07, RK-08. Then re-run the 7 persona scripts against the targets in section 4, before gate 2 on 18 Oct.
3. **Before 27 Oct:** RK-09, RK-11, RK-12, RK-16, RK-18, RK-21. Then RK-10, RK-14, RK-15.
4. **After the course:** RK-17, RK-19, RK-20 and the P2 items.

## 10. Evidence gaps to keep in mind

- Reddit and app-store sentiment is missing for most products (blocked).
- Schwab's override and scoring details are UNSOURCED.
- The Wealthsimple "100% equities needs a Portfolio Manager" sentence was quoted by the UX lane but marked UNSOURCED by the CA lane.
- VGRO, VBAL, XGRO and XBAL fees are unverified.
- The SoFi fee conflicts between sources.
- No legal opinion yet on s.8.25, Ontario s.34 or Quebec.
