# p5_retiree: Linda, 63, Halifax

Status: COMPLETE (the whole flow ran in a real browser tab at http://localhost:8765/mock.html, with the Claude stand-in played by the tester under the page's RULES)

Persona: retires in 2 years, 300,000 CAD, has a pension, very worried about losses, needs income. Reads in English and needs large text. Compares against her bank adviser and RBC InvestEase.

Tester note: the screenshot tool returned blank frames whenever the background tab was scrolled. Layout evidence therefore comes from DOM reads (getBoundingClientRect, elementFromPoint, computed styles), not from pictures. That is a limit of the test harness, not a product bug.

---

## 1. Landing (viewport 1280x800)

Heading "What would you like to build?", one input and five chips, with the tray on the right: level 3, $10,000, "Bad year (1 in 20) $9,434".

- Linda: the page is clean and calm, but the grey text is small. The note "You are chatting with an AI (Claude)..." is 13px, and "Data to 2026-08-31" is 12.5px.
- Measured: `body` is 14px. There are 332 text nodes at 13px, 52 at 11px, and the date chips are 10.8px. All 65 `font-size` rules in index.html use px and none use rem, so Chrome's "Font size: Large" setting changes nothing. There is no text-size control on the page.

## 2. First message

Typed: "Hello. I'm 63 and I retire in 2 years. I have about $300,000 saved and I am very worried about losing it. I will have a pension too. Can you help me?"

The guide (tester playing Claude under the RULES) called `start_self_check`. The reply began with the AI disclosure, and the page showed "Are you 18 or older?".

- Linda: "I just told you I'm 63." Small, but it signals that nothing she typed was heard. The tray still shows $10,000, not the $300,000 she typed.

## 3. Self-check

- Q1 market: Canada. Q2: Retirement. Q3 emergency fund: Yes. Q4 high-interest debt: No.
- Q5 "When do you expect to start taking money out?" The options are "Within 2 years" and "In 2 to 4 years". Linda retires in exactly 2 years, which fits both, so she tapped "Within 2 years".
  - Result: the survey stopped right there with the card "Before investing: You need this money within two years. Most people keep money like that in cash-like savings, so Robo-Kit will not build a stock portfolio for it."
  - The card showed "Your situation allows -", "Your comfort with ups and downs -" and "Suggested level 1 · Conservative", with an enabled "Use this level" button. Levels 2-5 were disabled.
  - `st.profile`: status "not_ready", can_choose [1], 7 answers missing.
  - Linda: "I'm not buying a house. This money has to last me 30 years." She felt shut out and a little scolded.
  - Contradiction: the card says it "will not build a stock portfolio", yet "Use this level" builds a level-1 mix with 17% stocks. I confirmed this later.
  - The very next question, Q6 ("Once you start, how long will you keep taking money out?"), would have told the page what it needed. But the G1 gate fires before Q6 is ever asked.
- Chat: "Wait, I retire in 2 years but I won't spend it all at once... Does this mean I can't invest at all?" The guide explained that the question is read literally and pointed her to "Change answer". PAGE STATE told the model "self-check done, suggested level 1, capacity null, tolerance null". It did not tell the model which answer set off the gate.
- "Change answer" on Q5 did not reopen the card. It added a second "Question 5 of 15" at the bottom of the thread. The old Q5 card (still showing "Within 2 years" as chosen), the gate card and the old level card all stayed above, and that old "Use this level" button stayed enabled.
- New answers:
  - Q5: In 2 to 4 years.
  - Q6: More than 10 years.
  - Q7: 300,000. The field was prefilled with 10000 even though she had typed $300,000 in chat. Typing "300,000" was accepted as 300000.
  - Q8: More than 75%.
  - Q9: Very steady. There is no option for a pension or guaranteed income.
- Q10, the one-year ranges, were shown in her own dollars ("$301,650 to $317,400" ... "$282,300 to $356,910"). This was the best moment of the flow. She picked the narrowest range.
- Q11: "...your $300,000 is worth $240,000. What would you most likely do?" She answered "Sell some".
- Q12: "Over ten years, which would you rather have?" The options were $379,067-446,254, $388,130-525,744, $391,917-606,897, $394,673-699,069 and $395,471-799,195.
  - Linda: "The last one has the best low and the best high. Why would anyone pick the first?" She picked the last.
  - Designer view: the low end of the range rises with risk, so the riskiest option beats the others at both ends. The question does not measure tolerance at all.
- Q13: Losing money. Q14: Goes down. Q15: Not sure.
- Result card:
  - "Two answers point different ways: one says you are fine with big swings, another that you would pull back after a drop. Which is closer to you?"
  - Its buttons: "Keep my answers", "Change an answer C1", "Change an answer C3", "Change an answer C4". These are internal question IDs.
  - Linda: "What is C3?" She had not chosen "big swings"; she had chosen the best worst case.
  - "Keep my answers" gave no visible response.
- Profile: "Your situation allows Level 2 / comfort Level 1 / Suggested 1 · Conservative". The explanation: "time horizon scores 7 of 15, which allows up to level 3. This money is most of your savings, so one step lower...". Levels 3-5 were disabled. The disabled level buttons in the tray explain themselves only through a hover title, "Above what your situation supports".

## 4. Build

"Use this level" produced the ladder card "What each level has meant", with the subtitle "Hypothetical ranges on $10,000". That $10,000 is hard-coded in app.js line 29, even though her amount is 300,000.

The shelf "Fill each asset class" came next: 10 sleeves x 6 funds, which is about 60 fund names.
- Blank fees: "XUU · fee ·", "XSTH · fee ·", "ZMMK · fee · BMO Mutual Funds - BMO Money Market Fund".
- The iShares 0-5 Year TIPS funds (XSTH, XSTP) sit under "Short-term Canadian bonds", with region Canada in the data.

"Build the mix" produced the mix at level 1:
- 70.2% CASH. The "8 years in 10" range is $301,650 to $317,400, and "Bad year (1 in 20)" is $298,560. Fees are $323 (0.11%).
- Plain-words block: "Replaying the 2008 financial crisis, this mix would have fallen about 4%".
- Crisis list:
  - Shown only as percentages: -4% (2008), -1%, "4%" for the oil crash (a gain, but shown without a +), -1%, -3%, -2%, and "-0%" for the 2025 tariff shock.
  - "Range of yearly returns by how long you hold" starts with the label "1 years".
- Checks:
  - "Over 10 years, fund fees of 0.11% a year would cost about 4,307 on 300,000", with no $ sign.
  - "3 fund(s) ... were dropped".
- "Possible paths" has inputs for Amount, Monthly add (min 0) and years. There is no withdrawal input.
- "Show me how" shows "Hypothetical back-test, after costs · Level 2" inside a level-1 mix card. In app.js line 655, `{1: 2, 2: 2, 3: 3, 4: 4, 5: 4}` silently maps level 1 to 2. The panel also shows "rate V80691344", a raw StatCan series ID.

## 5. What could go wrong?

- Chat: "What would have happened to my $300,000 in a crash like 2008, in dollars?"
  - `current_mix` returns stress tests as fractions only (-0.0358). Under the rule "Never compute", the guide could not give dollars and had to say "I don't have a dollar figure for 2008".
  - Linda asked the single most important question for her persona and got a percentage.
- Chat: "I keep seeing news about the war. Should I wait?"
  - The `market_context` card showed:
    - Geopolitical risk index "117.919 above its usual range"
    - US dollar "12-month change" with the value "1.4164" (that is the rate, not a change)
    - Several flags dated "2026-09-30"; today is 2026-09-28
  - Headlines: one topic, "technology": "Nvidia China Chip Sales...", "Thieves Stole Nvidia Trailers . They Got 20 Tons of Sand", "TSMC Accelerates 2nm...". The tool result also held a fool.com stock-pick headline.
  - Nothing about the war she asked about.
  - The guide's answer followed rule 6 well (context only, research finding, bad-year dollars, closest replay). The reply said "the card above", but the page puts the card below the reply.

## 6. Income and withdrawals

- Chat: "When I retire I would like to take out about $1,500 a month... How long would the money last? How much monthly income?"
  - There is no tool for this. `explain_term('withdrawal')` returned found:false, and the known terms include nothing on withdrawal, RRIF or sequence risk.
  - `etf_profile` returned no yield, so the guide said "The fund cards here do not list it". The ZAG fund card rendered right under that sentence shows "Yield 3.5%" (app.js line 690 reads `f.dividend_yield`, which is not in the tool result).
- In "Possible paths" I typed -1500 into Monthly add. It silently went back to 0, with no message.
- Years set to 25 gave a middle line of $659,266. The 10-90 range ($580,426 - $748,789) exists only in the svg aria-label and is not visible. The figures are nominal, with no mention of inflation.

## 7. Comparison with her adviser

- Chat: "Why is 70% in cash? ... What would level 2 look like?"
  - `propose_change` level 2 produced a card: bad year $291,180 vs $298,560, volatility 4.3% vs 2.1%, fees $321.
  - Apply worked, and the tray switched to level 2. The mix report in the thread still read "The mix at level 1 with 7 funds".
- Stale-card test:
  - Scrolling up to the original G1 gate card and tapping its still-enabled "Use this level" silently reset the level from 2 to 1.
  - It also added a second ladder card and a second shelf card to the bottom of the thread.
  - Thread at that point: 42 blocks, 17,058 px tall. It holds 16 fully expanded question cards, 2 profile cards, 2 ladders, 2 shelves and 1 stale mix card.
- Chat: "the level went back to 1 on its own?" The guide has no event log and could only guess that an older button did it.
  - The guide also cannot see the profile explanation lines. It gets only "capacity 2, tolerance 1", so its answer to "why are 3-5 greyed out" has to be generic.
- Chat: "Is CASH insured?" The guide had no data. It gave the facts from the fund card (worst drop 0%, 57 months of history) and sent her to the issuer or her bank.
- Chat: "Would this be cheaper than RBC InvestEase? Who buys the funds and rebalances?"
  - The first reply was rejected by the validator for "$323, 0.11%, 31". Those numbers came from earlier turns' tool results and from the date format that RULES itself asks for ("31 Aug 2026").
  - The guide had to call `current_mix` again. The footer then read "rewritten once to use tool numbers only".
  - The page offers nothing on how to buy, no share counts or order list, no rebalancing plan, and no export or print.

## 8. Return visit

After a reload, answers {}, level 3, amount 10000 and an empty thread: everything is lost. Only market and tier are stored (app.js lines 115, 203, 206, 249).

At 853 px wide (about 150% zoom), the tray becomes a bottom bar ("Level 1 · Volatility 2.1% · Fees a year $323"), there is no horizontal scroll, and the composer stays reachable.

---

## How Linda felt

Relieved at Q10, when the page finally showed her own dollars. She was shut out at Q5 and puzzled at "C3". She was reassured by "2008: about -4%", but wanted that in dollars. She was let down that nothing answers "how long will my money last" or "how much income a month". She was confused when her level changed back by itself. She would print the result for her adviser, but there is no way to do that, and on a return visit she would start over from zero.
