STATUS: COMPLETE

# US robo-advisors and portfolio builders: onboarding, risk override, goals, tax, reports

Researched 28 Sep 2026 for Robo-Kit (UX lane). Scope: Betterment, Wealthfront, Vanguard Digital Advisor, Schwab Intelligent Portfolios, Fidelity Go, SoFi Automated Investing, M1 (Pies), Ellevest, Acorns. Plus one regulator source (FINRA 2016 digital advice report) because it speaks directly to the "level 5 disabled" problem.

## How to read this file

- Every product claim has a URL and a short verbatim quote (under 25 words). Claims I could not load a page for are marked **UNSOURCED** or **UNVERIFIED (search snippet only)**.
- Quotes from HTML pages were pulled through a fetch tool that summarises pages. Wording should be exact, but spot-check anything you plan to cite in the course report. Quotes from the two PDFs (FINRA report, Vanguard advice brochure) were pulled straight out of the PDF text with pypdf, so those are exact.
- **Blocked or failed sources:** schwab.com (every page returned an "unable to authorize your request" error page), support.wealthfront.com (HTTP 403), sofi.com/invest/automated (HTTP 403), bogleheads.org (HTTP 402), reddit.com (the search tool refuses the domain). Schwab and SoFi facts therefore come from third-party reviewers.
- **Conflicts found and resolved:**
  - Betterment "On Track": a search snippet said 60%, but the live legal page says average market performance, which is 50%. I used the live page.
  - Acorns prices: NerdWallet (Oct 2025) says $3/$6/$12 and CNBC (Sep 2026) says $4/$5/$12. The official pricing page says $4/$8/$12, and I used that.
  - SoFi fee: NerdWallet (Oct 2025) says 0.25%, but CNBC (Sep 2026) says "zero management fees". **Unresolved** because the official page is blocked.
  - A search summary claimed "Wealthfront 3.0 … July 29, 2026" as an AI launch. The article is actually from 31 Mar 2016, so it is **discarded**.
  - Wealthfront gives two different counts for its risk scale: the whitepaper says 20 allocations (0.5 steps) and a blog says "100 different buckets". Both are recorded below.

---

## 1. Betterment

**Onboarding**
- Sign-up is a goal-setting exercise that asks for age and income. Source: https://www.nerdwallet.com/investing/reviews/betterment (review Oct 2025). Quote: "goal-setting exercise, asking for your age and current annual income"
- There are six goal types (Major Purchase, Education, Retirement, Retirement Income, General Investing, Emergency Fund). This comes from the fetch summary of https://www.betterment.com/resources/recommended-allocation-methodology and I have no verbatim quote for it.

**Risk / allocation override (the key pattern)**
- The whole 0–100% range is available. Source: https://www.betterment.com/investments. Quote: "101 possible stock-to-bond allocations"
- A slider lets you move around while watching the range of outcomes. Source: https://www.betterment.com/resources/asset-allocation-methodology. Quote: "toggle between different investment allocations … until they find the allocation that has the expected range of growth outcomes they are willing to experience"
- The chosen mix is labelled *relative to the recommendation*. Source: https://www.betterment.com/resources/recommended-allocation-methodology.
  - Quote: "This risk setting is associated with an allocation that is within 3 percentage points of our recommended allocation to stocks." (Moderate)
  - Quote: "…more than 7 percentage points above our recommended allocation to stocks." (Very Aggressive; Aggressive is 4–7 points above)
- Warnings are asymmetric: going too conservative gets "You may need to save more in order to reach your goals." Going too aggressive gets "exposes you to higher potential losses in the short-term" (same URL).
- Deviating from the recommendation turns off auto-adjust. Source: https://www.betterment.com/legal/auto-adjust-disclosure. Quote: "If the client selects an allocation other than Betterment's recommended allocation, the auto-adjust feature is disabled."

**Goal planning / probability**
- Source for all four quotes: https://www.betterment.com/legal/goal-projection
  - Quote: "The goal is 'On Track' when the total projected portfolio value exceeds the goal target assuming average market performance."
  - The forecaster shows a median line plus a band. Quote: "The lighter, shaded region indicates the range within which there is 80% likelihood of obtaining the projected portfolio value"
  - Quote: "The recommended monthly contributions estimate is based on a 50% likelihood of the portfolio value reaching the goal target"
  - Disclaimer quote: "An indication of 'On Track' is not a guarantee of achieving a goal in the future"
- When a goal is off track, Betterment gives three levers. Source: https://www.betterment.com/help/off-track-goal. Quote: "increasing the amount of future monthly contributions, increasing the term to make it longer, or increasing the current balance"

**Tax**
- Tax Impact Preview appears before an allocation change or withdrawal. Source: https://www.betterment.com/help/how-tax-impact-preview-works.
  - Quote: "shows the estimated gains and losses the sale is expected to realize, as well as an estimate of the taxes that may result"
  - Quote: "The estimated tax is an upper bound, meaning it assumes the highest applicable tax rates of combined federal, state, and medicare surtax."
- Asset location. Source: https://www.betterment.com/resources/tax-tools. Quote: "sorting of asset types based on tax treatments, rather than divvying them up equally across accounts, is known as asset location"
- Tax-loss harvesting is only worth it for some investors (same URL). Quote: "The strategy doesn't make sense for everyone"

**Pricing**
- Source: https://www.betterment.com/pricing. Quotes: "$0 - $24K balance: $5 Monthly" and "0.25% Annually". Premium is "0.65% annual management fee".

**Weaknesses (reviewer)**
- Source: https://www.nerdwallet.com/investing/reviews/betterment. Quote: "No direct indexing". Also quote: "Poor customer service response and technical issues with the app".

**App store**
- 4.8/5, about 65K ratings. Source: https://apps.apple.com/us/app/betterment-invest-save-money/id393156562. The reviews praise ease and automation. Quote: "I chose Betterment because of its ease of use, it's automated guidance, and it's low fees."

---

## 2. Wealthfront

**Risk questionnaire**
- Scale. Source: https://www.wealthfront.com/blog/ask-wealthfront-risk-score-explainer/. Quote: "helps assign you a risk score from 0.5 (least risky) to 10 (highest risk)."
- There are 10 questions: 4 objective and 6 subjective. Source: https://www.wealthfront.com/blog/what-is-risk-tolerance/.
  - Quote: "We ask four questions – age and income questions — to estimate whether you are likely to have enough money saved at retirement"
  - Quote: "six questions, which focus on your willingness to take on risk"
- Contradictory answers are detected (same URL). Quote: "if you tell us you make angel investments but would sell your stocks after a big drop – that's a clue"
- Scoring. Source: https://research.wealthfront.com/whitepapers/investment-methodology/.
  - Quote: "Our overall Risk Score combines subjective and objective risk tolerance, with a heavier weighting to whichever component is more risk averse."
  - Quote: "The less consistent the answers, the exponentially less risk-tolerant you are likely to be."
  - Quote: "Each Risk Score corresponds to one of the twenty asset allocations"
  - The blog says instead: "puts clients into one of 100 different buckets" (inconsistent with the whitepaper).

**Risk override**
- Changes are allowed but discouraged. Source: research.wealthfront.com whitepaper (above). Quote: "We inform our customers about the impacts of changing their Risk Score frequently, and that it might not be appropriate for their ultimate goals."
- Changing risk after a market move is called out as market timing. Source: blog explainer (above). Quote: "Changing your score for this reason is market timing, and it is unlikely to work."
- **UNVERIFIED (search snippet only; support.wealthfront.com returned 403):**
  - The risk score is changed with "+"/"-" buttons.
  - Saving requires dragging a slider to "Acknowledge and update".
  - There is a "Switch to recommended risk" option.
- App store complaint about where risk can be changed. Source: https://apps.apple.com/us/app/wealthfront-save-and-invest/id816020992 (4.8/5, 17K ratings; review date unknown). Quote: "The app does not give users the ability to change their risk tolerance score. Users must log on to Wealthfront's actual website"

**Customization**
- Source: https://www.wealthfront.com/investing. Quote: "you can change allocation weights and even add, remove and swap ETFs of your choosing."
- Source: https://www.wealthfront.com/pricing. Quote: "Adjust your allocations and edit your portfolio with hundreds of funds to choose from."

**Planning / projections**
- Path shows trade-offs. Source: https://www.wealthfront.com/planning. Quote: "One decision will impact another – buying a house may impact your plans to retire early."
- Disclaimer (same URL). Quote: "All information provided by Wealthfront's financial planning tool is for illustrative purposes only"
- Source: https://www.wealthfront.com/blog/understanding-path-retirement/. Quote: "Performance projections are hypothetical and not an indicator of any investor's actual current or future experience"

**Tax**
- Source: https://www.wealthfront.com/pricing. Quote: "We find opportunities to turn market dips into tax savings, to help boost your after-tax returns."
- Direct indexing threshold. Source: https://www.nerdwallet.com/investing/reviews/wealthfront. Quote: "stock-level tax-loss harvesting…at a $100,000 minimum"

**Pricing and minimum**
- Source: https://www.wealthfront.com/pricing. Quote: "just 0.25% annually."
- Minimum. Source: NerdWallet (above). Quote: "you'll need to deposit at least the $500 account minimum"

**Weakness (reviewer)**
- Source: NerdWallet (above). Quote: "No human financial advisors are available, not even for an extra fee"

---

## 3. Vanguard Digital Advisor

**Onboarding**
- Source for all three quotes: https://investor.vanguard.com/advice/robo-advisor
  - Quote: "The initial process can take up to 30 minutes to ensure we can deliver the best results for you."
  - Quote: "Portions of enrollment screens are overlaid on video showing a range of 10,000 scenarios that predict a client's possible account balances at retirement."
  - Quote: "$100 in assets is required to enroll in Vanguard Digital Advisor."

**Risk survey**
- Three scenario questions. Source: https://ownyourfuture.vanguard.com/content/en/learn/financial-planning/how-risk-shapes-your-investment-mix.html. Quote: "The risk survey poses 3 financial scenarios. One scenario focuses on the long term, and 2 focus on the short term."
- The survey shows pairs of best and worse outcomes (same URL). Quote: "pairs of best and worse outcomes for your money"

**Risk override (the closest precedent for the Robo-Kit level-5 problem)**
- Source: ownyourfuture (above). Quote: "If it doesn't feel true to you, you can bump it up or down 1 or 2 levels. Or you can retake the survey entirely."
- Exact PDF text. Source: https://personal1.vanguard.com/pdf/vanguard-digital-advice-brochure.pdf, p.28.
  - Quote: "selecting a different risk attitude up to two steps away to make your selected risk more conservative or aggressive"
  - More than two steps means retaking the assessment. Quote: "If you wish to deviate more than two steps … you will have an option to retake the assessment."
  - Quote: "You may not choose to deviate the assessed loss aversion." The attitude can be overridden but the loss-aversion measure cannot.
  - Quote: "If the assessment results are inconsistent, then you will not be attributed with a low or high loss aversion."
- Glide paths. Source: same brochure. Quote: "map a client to the optimal asset allocation from over 1,000 possible glide path options"

**Goal probability / projections (brochure, exact PDF text)**
- Quote: "the Services' forecasts will generate 10,000 scenarios to measure your likelihood of success of reaching your goals"
- Quote: "A projected funding status (well-funded, moderately-funded, and under-funded) will be estimated on the Site."
- Fees are built into the projections. Quote: "For Digital Advisor, asset class returns for fixed income and equity allocations are reduced by 0.30% annually"
- Disclaimer quote: "They aren't a guarantee of future results or a guarantee of the success rate of the simulated outcomes."
- Asset location is also used in the projections. Quote: "For clients with taxable accounts, we apply asset location logic when modeling returns."

**Tax**
- Source: investor.vanguard.com robo page. Quote: "including tax-loss harvesting, which can help offset taxes paid on capital gains."

**Fees in dollars (framing Robo-Kit already uses)**
- Source: same page. Quote: "$15 - $16 is approximately what you pay per year for every $10K in an all-index portfolio."

---

## 4. Schwab Intelligent Portfolios

schwab.com blocked every fetch, so all facts here come from third parties.

- Minimum and cash allocation. Source: https://www.nerdwallet.com/investing/reviews/schwab-intelligent-portfolios (Oct 2025).
  - Quote: "Account minimum: $5,000."
  - Quote: "a minimum of 6% all the way up to nearly 22.5% of total portfolio holdings"
- Tax-loss harvesting (same URL). Quote: "Tax-loss harvesting is available at a $50,000 minimum balance."
- Customization is narrow (same URL). Quote: "Investors can tweak the allocation in Schwab's recommended model by picking as many as three ETFs to remove"
- Fees. Source: https://www.unbiased.com/discover/investing/schwab-intelligent-portfolio-review (Aug 14 2026).
  - Quote: "Advisory fee: $0. Schwab does not charge a management or advisory fee"
  - Quote: "Portfolios may hold 6%–30% in cash"
  - Premium quotes: "One-time planning fee: $300" and "Ongoing advisory fee: $30/month"
- Questionnaire length. Source: https://smartasset.com/financial-advisor/schwab-intelligent-portfolios-review (dated Feb 2021, may be stale). Quote: "12-question survey about your goals, timeline and risk tolerance"
- **UNSOURCED (schwab.com blocked):**
  - Separate Risk Capacity and Risk Willingness scores.
  - Clients can move up or down one portfolio after the recommendation.
  - Goal Tracker thresholds (above 50% on target, 25–50% at risk, below 25% off target).

---

## 5. Fidelity Go

**Onboarding**
- Source: https://www.fidelity.com/managed-accounts/fidelity-go/overview. Quote: "your personalized investment strategy in just a few minutes."
- Source: https://www.fidelity.com/managed-accounts/fidelity-go/investment-account-faqs. Quote: "how comfortable you are with risk on a scale of 1 to 10"
- The questionnaire works before sign-up. Source: https://www.nerdwallet.com/investing/reviews/fidelity-go (Dec 17 2025). Quote: "without signing up or sharing any personal information, users can take that questionnaire and view a portfolio recommendation"

**Risk override**
- Source: FAQ (above). Quote: "If you'd rather choose a strategy other than the one we suggested, you can explore our other options and select the one you prefer."
- The recommendation is shown as a chart first (same URL). Quote: "we'll show you a chart that breaks down the mix of stocks, bonds, and short-term investments"
- Range of strategies (same URL). Quote: "Our most conservative investment strategy targets 20% stocks and 80% bonds and short-term investments"
- Annual check-in (same URL). Quote: "Each year, we'll check in with you to ask if anything major in your life has changed"

**Tax**
- Source: FAQ (above). Quote: "Once your balance reaches $25,000 in a Fidelity Go® taxable account, tax-loss harvesting is automatically included."

**Pricing**
- Source: overview (above). Quotes: "$0 advisory fees under $25,000" and "0.35% for accounts $25,000 and above"

**Weakness (reviewer)**
- Source: NerdWallet (above). Quote: "lacks exposure to international bonds and non-market-correlated assets such as real estate investment trusts and commodities"

---

## 6. SoFi Automated Investing

The official page returned 403, so these facts come from reviewers.

- Onboarding. Source: https://www.nerdwallet.com/investing/reviews/sofi-automated-investing (Oct 2025). Quote: "asks how long you plan to invest, what you're investing for, and how comfortable you are with risk"
- No tax-loss harvesting (same URL). Quote: "SoFi doesn't offer tax-loss harvesting"
- Fee (same URL). Quote: "0.25% management fee". This conflicts with CNBC (https://www.cnbc.com/select/best-robo-advisors/, Sep 2026), which says "zero management fees". **Unresolved.**
- Advisor access (same URL). Quote: "Everyone can access one meeting with an advisor; SoFi Plus members can meet with an advisor as needed."
- Hands-on test. Source: https://www.bestroboadvisors.org/sofi-automated-investing-review/ (third party, lower credibility).
  - Onboarding took "about four minutes – age, income, time horizon, risk tolerance, what the money is for."
  - The reviewer lists five risk tiers from Conservative to Aggressive.

---

## 7. M1 (Pies): the DIY builder, closest to Robo-Kit's shelf

- There is no questionnaire and no personal risk recommendation.
  - The create flow is "Select 'Choose securities' to view all supported stocks, ETFs, and Model Portfolios". Source: https://help.m1.com/en/articles/9332044-how-to-create-your-m1-portfolio
  - Same URL. Quote: "All Slices within a Pie must total 100%"
- Target weights. Source: https://m1.com/invest/. Quote: "Set target allocations for each Slice—the percentage of your portfolio you want each holding to comprise."
- Deposits rebalance the portfolio. Source: https://help.m1.com/en/articles/9331915-what-is-a-pie. Quote: "M1 calls this funding methodology Dynamic Rebalancing."
- Size limit (same URL). Quote: "Portfolios can have a total of 100 Slices."
- Model Portfolios are framed as not advice, with hypothetical back-tests. Source: https://help.m1.com/en/articles/9332050-what-are-m1-model-portfolios.
  - Quote: "should not be construed as financial, investment, legal, or tax advice."
  - Quote: "M1 shows hypothetical, back-tested performance"
  - The back-test "does not reflect taxes or all possible fees."
- Fee. Source: m1.com/invest. Quote: "A $3 monthly platform fee will apply to clients with less than $10,000 in M1 assets"
- Weakness. According to https://www.optimizedportfolio.com/m1-finance-review/ (May 2025) there is no automatic tax-loss harvesting. This is a paraphrase with no verbatim quote.

---

## 8. Ellevest: automated investing no longer exists

- Source: https://www.prnewswire.com/news-releases/betterment-acquires-ellevests-automated-investing-business-302386022.html
  - Quote: "Ellevest will transfer their automated investing accounts to Betterment on or about April 17, 2025."
  - Ellevest now serves clients "looking to invest $500,000 or more".
- Its historical gender-aware projections (salary curves, career breaks) are **UNSOURCED**; I found them only in a search summary.

---

## 9. Acorns

- Recommendation. Source: https://www.nerdwallet.com/investing/reviews/acorns (Oct 2025).
  - Quote: "considers your data — including age, goals, income and time horizon — and then recommends one of five portfolios that range from conservative to aggressive."
  - Override quote: "You can accept the recommendation or choose a different portfolio that takes more or less risk."
  - Quote: "Acorns does not offer any form of tax strategy."
- Pricing (official, current). Source: https://www.acorns.com/pricing/.
  - Bronze "$4/mo.", Silver "$8/mo.", Gold "$12/mo."
  - Gold adds: "Customize your portfolio with the ability to add individual stocks and ETFs"
  - Round-Ups quote: "Save and invest spare change everyday with Round-Ups®"
- Portfolio definitions. Source: https://www.acorns.com/learn/investing/conservative-vs-aggressive-investing-and-portfolios/. Quote: "40% large company stocks, 20% small company stocks, 10% emerging market stocks, 10% real estate stocks, 20% international large company stocks" (Aggressive)

---

## 10. Regulator reference: FINRA Report on Digital Investment Advice (Mar 2016)

Source: https://www.finra.org/sites/default/files/digital-investment-advice-report.pdf. All quotes are exact PDF text.

- Quote: "Problems can arise when risk willingness exceeds risk capacity."
- Contradictory answers, quote: "in a purely digital environment, by making a customer aware of contradictory responses and asking additional questions to resolve the inconsistency"
- Quote: "Averaging is a poor practice, as it can result in a customer being placed in a portfolio that exceeds his or her risk tolerance."
- The cost of taking the more conservative answer, quote: "However, even with this approach, the customer could end up with a portfolio that does not reflect their desired risk."
- Invest vs save vs pay off debt, quote: "make clients aware when investing may not be appropriate for them"
- Frequent profile changes, quote: "If investors frequently change their profile, an effective practice is for broker-dealers to contact the investor to understand why"
- Slider-based risk willingness, quote: "Investors can use a slider bar to adjust the potential loss and gain to the level they are comfortable with."
- Rebalancing, quote: "apprising the customer of the potential cost and tax implications of the rebalancing"

---

## 11. Cross-cutting patterns

1. **No verified competitor hard-blocks a riskier choice with a disabled button.**
   - Betterment offers any of 101 mixes, labelled relative to the recommendation.
   - Vanguard allows ±2 steps, or a retake for bigger moves.
   - Fidelity Go and Acorns let you pick any strategy.
   - Wealthfront allows changes with discouragement (the acknowledgement slider is unverified).
   - Schwab's ±1 portfolio is unsourced.
   - What competitors restrict is *side effects* (Betterment turns off auto-adjust) or *which inputs* can be overridden (Vanguard's loss aversion), not the choice itself.
2. **The lower-of-two scoring is standard, and so is its known flaw.** Wealthfront weights the more risk-averse component more heavily, and FINRA endorses taking the conservative answer over averaging. FINRA also says this can leave people in a portfolio that "does not reflect their desired risk". The industry answer is to reconcile: show the conflict and ask more questions or allow a bounded override.
3. **Question counts are short.** Vanguard's risk survey has 3 scenarios, Wealthfront has 10 questions, Schwab about 12 (2021 source), and SoFi takes about 4 minutes (third party). Fidelity uses one 1–10 self-rating. Robo-Kit has an 18+ gate plus 15.
4. **Onboarding is a form flow, not a chat transcript.** Every product runs a linear questionnaire and then a recommendation screen. None verified puts the questionnaire into a conversational log.
5. **Recommendations are shown as a picture before commitment.** Fidelity shows a chart before you choose. Betterment's slider shows outcome ranges as you drag. Vanguard overlays 10,000 scenarios during enrollment.
6. **Probability of success is framed as a status plus levers.**
   - Betterment is On/Off Track at the median, with an 80% band and three levers.
   - Vanguard shows the share of 10,000 scenarios plus well/moderately/under-funded, with fees subtracted from returns.
   - Schwab's thresholds are unsourced.
7. **Disclaimers are explicit and repeated:** hypothetical, not a guarantee, and fees and taxes not reflected (M1).
8. **Tax is a key paid feature.**
   - Tax-loss harvesting minimums: Wealthfront has none, Fidelity $25K, Schwab $50K, SoFi and Acorns have no TLH.
   - Asset location: Betterment Tax Coordination; Vanguard also uses it in its projections.
   - Betterment's Tax Impact Preview shows an upper-bound tax before an allocation change.
9. **Customization runs from narrow to total.** Schwab lets you remove 3 ETFs, Betterment offers 101 stock/bond mixes plus custom portfolios, Wealthfront lets you add, remove or swap from "hundreds", and M1 allows 100 slices. Robo-Kit's roughly 8,000-ETF shelf is broader than all of them.
10. **Fees in dollars are rare.** Vanguard uses "$15-$16 per $10K"; most others quote percentages.
11. **I found no verified consumer AI chat assistant at the big US robos.** Search results about 2026 AI launches were advisor-side (Advisor360, Altruist Hazel), and one Wealthfront "AI" claim turned out to be a 2016 article. A grounded AI guide is a differentiator for Robo-Kit if the structured flow stays primary.

---

## 12. What this means for the two problems found in testing

These are observations from reading the code, not from a browser test.

**Problem 1: level 4 suggested, level 5 unavailable**
- `web/robokit.js:693` sets `can_choose` to levels 1..capacity. When capacity is 4, level 5 is excluded.
- `web/app.js:505` renders level 5 disabled on the profile card.
- `web/app.js:541` makes a click on a blocked ladder row return silently, with no message.
- `web/app.js:518` (`setLevel`) silently clamps any higher level to the maximum allowed.
- `web/app.js:763` disables level 5 in the tray.
- `web/app.js:396`: only the AI `propose_change` path returns a "capped" note.
- So a person who meant 5 sees a dead button and, in the ladder, no explanation.
- Competitor precedent (Vanguard ±2 steps, Betterment labels relative to the recommendation plus a warning, FINRA's reconcile-rather-than-average advice) suggests replacing the hard cap with a bounded, explained override. A hard stop would stay only where a gate (G1–G3) fires, matching FINRA's "invest vs save/pay debt" practice.

**Problem 2: cluttered onboarding transcript**
- `web/app.js:437` pushes each question into the chat stream as a card.
- Answered cards stay (`is-done`).
- "Back" (`app.js:471`) appends a *new* copy of the question at the bottom while the old answered card remains.
- Gate cards (`app.js:476`) and flag cards (`app.js:484`) interleave mid-flow.
- Profile, ladder and shelf cards follow (`app.js:485, 512-513`), plus any AI messages.
- Competitors keep the questionnaire out of any log. Suggested fix: a single focused stepper surface with edits in place, then one summary card posted to the chat.
