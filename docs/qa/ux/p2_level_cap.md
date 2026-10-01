# p2_level_cap: Jordan wants level 5 after the self-check says 4 or less

Status: COMPLETE. Real page (http://localhost:8765/mock.html) in my own tab at 1366x850. I played the chat guide faithfully from the RULES in turns[0], using only real tools through window.__mock.call. I changed no project files.

Persona: Jordan, 29, Vancouver. Confident, 20+ year horizon, partial emergency fund, income that varies. Canada market, $25,000.

---

## 1. Landing, typed opener

- **Saw.** "What would you like to build?" with one input and five chips. The tray already shows level 3 (Balanced), and all level buttons 1-5 work before the survey.
- **Typed.** "hey, I'm 29 in Vancouver and want to build a long-term portfolio. I'm pretty aggressive, 20+ years"
- **Guide (me).** Called `start_self_check` and got `{"shown":"age_check"}`. Replied with the required AI disclosure plus one line about the self-check.
- **Card order.** The age card rendered *below* my reply, but I had written "shown as buttons above". The RULES never say where cards appear, so a real model will make this mistake too.
- **Footer.** Under the reply: "Every number checked against Robo-Kit's tools. Balanced model." As Jordan I read "Balanced" as the risk level, since level 3 is also called Balanced. In fact it is the model tier (`app.js:23` tierDefault 'Balanced' vs `robokit.js:18` level 3 'Balanced').
- **Feeling.** Fine so far.

## 2. Mixing tap and type during the survey

- **Tapped** "Yes, 18 or older", then "Canada". Answered cards dim, and the choice stays highlighted (`is-chosen`). Good.
- **Focus lost.** After each tap, focus drops to BODY, so a keyboard user loses their place.
- **Typed answer.** On Q2 ("What is this money for?") I typed the exact option text: "building wealth, no fixed date".
  - It did not answer the card. It went to Claude as a chat message.
  - The PAGE STATE Claude gets says only "self-check not done". Claude does not know a question is open, which question it is, or any earlier answers.
  - As the guide I called `start_self_check`. It moved the open Q2 card below the Thinking bubble. I replied "Robo-Kit records self-check answers only from the buttons... Please tap..."
- **Jordan's reaction.** "I literally typed the button text and it made me tap anyway." One AI round trip was spent for nothing. The thread now has a user bubble and a guide bubble wedged between Q1 and Q2.
- **Already told, asked again.** Q5 asked for the horizon I had already typed in my first message ("20+ years"). Nothing was pre-filled.
- **Amount card (Q7).** Typing 25000 and pressing Enter does nothing. You must click Continue.

My answers:

| Question | Answer |
|---|---|
| Emergency fund | Partly |
| High-interest debt | No |
| Horizon | 20 years or more |
| Draw-down | More than 10 years |
| Amount | $25,000 |
| Share of savings | 50% to 75% |
| Income | It varies a lot |
| One-year range | $23,525 to $29,743 (the widest) |
| 20% drop | Buy more |
| Ten-year range | $32,956 to $66,600 (the widest) |
| Worry | Missing out on gains |
| Knowledge questions | Both correct |

**The ten-year question has a dominated answer.** Options go from "$31,589 to $37,188" up to "$32,956 to $66,600". The level-5 option has the highest low end *and* the highest high end, so there is no trade-off and anyone sensible picks it. That pushes everyone's tolerance up, which makes capacity bind more often.

## 3. The profile card: level 2, not even 4

"Here is what I heard"
- Your situation allows: Level 2
- Your comfort with ups and downs: Level 5
- Suggested level: 2 · Cautious

Reasons shown on the card:
- "Your time horizon scores 15 of 15, which allows up to level 5."
- "This money is most of your savings, so one step lower."
- "Your income is uneven, so one step lower."
- "Your emergency savings are partial, so one step lower."
- "Your answers about ups and downs point to level 5."
- "We use the lower of the two: level 2, Cautious."

Then "Choose the level to use": 1 and 2 are tappable. 3, 4 and 5 are at 40% opacity and disabled. Their only explanation is a `title` tooltip, "Above what your situation supports", which never shows on touch.

Jordan: "I'm 29, no debt, 20+ years, I'd buy the dip, and I'm Cautious? Three separate one-step penalties stacked up to take 3 levels off." The reasons are clear and honest. The outcome feels punitive, and nothing tells me how to get back up.

Code: `robokit.js:664-667` stacks the three -1 steps. `robokit.js:693` sets `can_choose = 1..capacity`. So **whenever capacity is the lower score, the suggested level is also the ceiling**. You can never choose even one level above the suggestion. The "or a higher one up to capacity" in rule 5 only helps when tolerance is the lower score. That is the level-cap bug, exactly.

## 4. Tapping 5 in the tray

- **Before.** The tray still said "Reference funds, level 3 · Balanced", and all five buttons were enabled. The profile card had just said levels 3-5 were not allowed, so the tray was stale.
- **Tapped 5** (real click). The tray changed to **"Your choices, level 2 · Cautious"**, and 3, 4 and 5 became disabled.
- **What happened.** I tapped 5 and got 2, with no message or toast. `setLevel` quietly clamps the level (`app.js:516-519`: "never above the self-check's capacity cap").
- **Jordan.** "Wait, I pressed 5 and it went *down*?" This is the worst moment of the session.

## 5. Asking the chat "why can't I pick 5?"

- **Typed.** "why can't I pick 5? I said I'd buy more if it dropped and I have 20+ years"
- **PAGE STATE.** "self-check done, suggested level 2, capacity 2, tolerance 5". It does **not** include the reasons, the answers, or which answer lowered capacity (`assistant.js:82`).
- **Guide (me).** Explained the two scores and the lower-wins rule. I pointed to the card for which answers lowered capacity and to "Change answer". The validator passed it.
- **Limits.** The honest answer is a bit generic. The guide cannot say *which* answer did it without guessing, and no tool returns the profile or its explanation.

## 6. "just give me 5, 100% stocks"

- **Guide (me).** Following rule 7, I called `propose_change({level:5})`. The result was `level_note: "Level 5 is above what your self-check allows, so this uses level 2."`
- **Useless card.** The page showed a "Proposed change" card with identical Now and After columns: level 2 · Cautious, 4.3%, $24,265, $27. The Apply button still worked. The cap note is in the tool result only and **not on the card**.
- **My reply.** "I hear you, and I can't unlock level 5 from here..." It named the inputs that would change the result. The RULES allow nothing more: no educate-then-acknowledge path, no record that the person asked for more risk, no override.
- **No 100% stocks.** Nothing on the page says so, but level 5 is 95% stocks (the ladder shows "Stocks 95%"). Neither the chat nor the page told Jordan that "100% stocks" isn't a level at all.
- **Card placement again.** The proposal card appears *below* the reply, and I had written "above".

## 7. Confirming, then the ladder

- **Confirmed.** Tapped "Not now", then "Use this level" (2) on the profile card. A ladder card ("What each level has meant") and a shelf card ("Fill each asset class") appeared.
- **Wrong dollar base.** The ladder says "Hypothetical ranges on $10,000", although I had just entered $25,000 and the question cards used $25,000.
- **Ladder rows 3-5 look fully tappable** (opacity 1, pointer cursor, no disabled state).
- **Tapped "5 Aggressive growth" on the ladder.** Nothing happened: no highlight, no message, still level 2 (`app.js:541` returns silently; `app.js:532` never disables the row).
- **Shelf glitches.**
  - Some alternatives show a blank fee: "XUU · fee ·", "XSTH · fee", "ZMMK · fee".
  - A US TIPS fund (XSTH) is offered under "Short-term Canadian bonds".
  - A mutual fund, "BMO Mutual Funds - BMO Money Market Fund", is listed under Cash.

## 8. Changing earlier answers (reproducing "level 4")

- **Change 1.** Jordan decides his workplace RRSP counts. He taps "Change answer" on Q8 and picks 25% to 50%.
  - A *new* "Question 8 of 15" card appears at the bottom of the thread, below the ladder and shelf.
  - The original Q8 card up top still shows "50% to 75%" as chosen.
  - A second profile card follows: "Situation allows Level 3 ... Suggested 3 · Balanced".
- **Change 2.** "Change answer" on Q9 income: Mostly steady.
  - Another "Question 9 of 15" card and a third profile card: **"Situation allows Level 4, comfort Level 5, Suggested 4 · Growth"**, with 5 disabled.
  - **This reproduces the level-cap bug exactly.**
- **Stale tray.** The tray still had 3 and 4 **disabled** even though the profile now allows 4. Clicking tray 4 did nothing. The tray only re-renders on `setLevel`; `showProfile` never calls it (`app.js:481-486`).
- **Stale profile card.** The level-3 profile card is still live with an enabled "Use this level". Two contradictory live cards (3 and 4) sit in the thread.
- **Asked the chat.** "ok now it says 4. why is 5 still greyed out?? my comfort is literally 5". As the guide I called `propose_change({level:4})`, because the tray was still on 2. I read out volatility 4.3% → 8.6%, bad year about 7.9%, fees about $31.
- **Where I cheated.** My reply named "partial emergency savings" as the cause. A real model could not know that: it is not in any tool result or in PAGE STATE. I used tester knowledge. This proves the gap: the guide needs the profile explanation.
- **Applied** the level-4 proposal. The tray changed to level 4, with 5 disabled.
- **Confirmed again.** Tapped "Use this level" on the level-4 profile card. It added a **second ladder and a second shelf**. The first ladder still highlights level 2.
- **Unlocking 5 is one tap.** "Change answer" on Q3 (emergency fund): Yes. Capacity went to 5, and a fourth profile card appeared with "Suggested 5 · Aggressive growth" and 5 enabled.
  - There was no check or friction. The hard lock is beaten by changing one honest answer to a flattering one.
  - The lock pushes people to shade answers instead of protecting them. The tray still showed 5 disabled (stale).

## 9. How the thread reads afterwards

40 items, about 13,300 px tall. From the top:

1. Opener, disclosure, age card, Q1
2. A stray typed answer and the guide's "please tap" reply
3. Q2-Q15, with the *old* answers still highlighted on Q3, Q8 and Q9
4. Profile #1 (Level 2, done)
5. Two chat turns and a no-op "Proposed change" (2 → 2)
6. Ladder #1 (still highlighting 2) and Shelf #1
7. Q8 again, profile #2 (Level 3, **still live**)
8. Q9 again, profile #3 (Level 4)
9. Chat turn and proposal (2 → 4, Applied)
10. Ladder #2 and Shelf #2
11. Mix report (level 4)
12. Q3 again, profile #4 (Level 5, live)

The question counter reads "Question 8 of 15", then "Question 9 of 15", then "Question 3 of 15" near the end, as if the survey restarted. Nothing in the thread says which answers are current. Scrolling up shows contradictory selections and two live "Use this level" buttons that would change the level. It is a mess.

## 10. Mix report (Open the full mix)

- **Rich and good.** Weights with a risk share ("VFV is 32% of the money but 40% of the risk"), dollar ranges, crisis replays ("2008 ... -27%"), and a projection fan.
- **Small inconsistencies.**
  - "Fund fees average 0.13%" but Checks say "fees of 0.12% a year would cost about 529 on 25,000". The rates differ and the check has no $ or CAD.
  - "1 years" in the holding-period table.
- **Missing.** Nothing in the report records the self-check (capacity 4, tolerance 5), that the chosen level is below comfort, or that the person asked for more.

---

## What a good product would do for Jordan (designer view)

1. **Separate "suggested" from "allowed".** Show the suggestion, but let the person choose a higher level after a short, specific acknowledgement. For example: "Level 5 at $25,000: in a bad year, about 1 in 20, about $X; 2008 replay about -Y%. Your emergency fund is partial, so a job gap could force selling at the bottom."
   - Record the choice, the suggestion and the acknowledgement (a "chosen above suggestion" note in the mix report and in the tray).
   - This is how suitability-style tools treat a client who "insists": document it, don't refuse.
   - Keep the hard cap only for the G1-G3 gates (money needed within 2 years, no emergency fund, high-interest debt), which are real affordability stops.
2. **Never silently clamp.** Replace the tap-5-get-2 behaviour with an inline sheet: "Level 5 is above your suggested 4. Here's why: partial emergency fund. [See what 5 means] [Choose 5 anyway] [Change that answer]." Ladder rows above the suggestion must look different and respond the same way.
3. **Show what unlocks the next level.** Say it at the point of the lock: "Build your emergency fund to 3-6 months → level 5 available." The page shows it as a what-if, not just a past-tense reason.
4. **Soften stacked penalties.** Three independent -1 steps turn a 20-year horizon into "Cautious". Consider a cap of -2 in total, or weighting by horizon (a partial emergency fund matters less when the horizon is 20+ years). Also fix the dominated ten-year question: show the bad-decade low end, so there is a real trade-off.
5. **One live survey object, not a scroll of cards.**
   - Collapse answered questions into a single "Your answers" summary card that edits in place.
   - "Change answer" edits that row and re-scores the same profile card, instead of appending new ones.
   - Mark superseded cards "Replaced by your newer answer", or remove them.
   - Only one ladder and one shelf ever; re-render them.
6. **Let typed answers count.** When a question card is open and the typed text matches an option (or clearly implies one, like "20+ years"), answer the card locally with no AI round trip. Pre-fill answers stated in the opener and ask the person to confirm.
7. **Give the guide the facts.** Add the profile explanation, the per-answer drivers, the open question id and the can_choose list to PAGE STATE (or a `self_check_status` tool). Also tell the guide that cards render below its reply.
8. **Rename the model tier.** "Balanced model" should become something like "Standard model", so it never reads as risk level 3.
