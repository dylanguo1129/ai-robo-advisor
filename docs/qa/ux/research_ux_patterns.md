STATUS: COMPLETE

# Onboarding, risk profiling and chat-with-forms UX: evidence notes

Researched 28 Sep 2026 for Robo-Kit. Every product/regulator claim below has a URL and a verbatim quote (under 25 words; sources not in English are summarised in English) that I checked against the page text (fetched with WebFetch or curl, then searched for the exact wording). Anything I could not check is marked UNSOURCED or left out.

Gaps and blocked sources:
- ciro.ca and osc.ca returned HTTP 403. I used the same CSA texts from mirrors instead: the BCSC PDF of Companion Policy 31-103, the ASC PDF of the CFR FAQ, and the Saskatchewan FCAA PDF of CSA Staff Notice 31-342.
- WebFetch got 403 from Wealthsimple and Morningstar, but curl with a browser user agent worked.
- Schwab returned an authorization error.
- The Material Design 3 page is a single-page app and returned no text.
- Reddit blocked automated access, so there is no Reddit or app-store review evidence here.
- The ACM page for Kim et al. 2019 returned 403, so I read the abstract through the Semantic Scholar API.
- I found no official Ant Fortune help-centre page. The Alipay evidence comes from news reports (21st Century Business Herald and International Finance News via STCN).
- The Vanguard Digital Advisor FAQ page did not say whether you can go above the recommended mix, so I left it out.
- Nothing here is legal advice. The regulatory points explain design choices only, and the course instructor or counsel should confirm them.

---

## 0. What Robo-Kit does today (from the code, for context)

- `web/robokit.js:693`: `can_choose` is levels 1..capacity. When capacity is 4, level 5 is never offered. Capacity 4 comes from a time-horizon score of 10 to 12 (`robokit.js:662`) or from one-step deductions (`:664-666`). This is the level-cap bug found in testing: after a level-4 result, level 5 is not offered.
- `web/app.js:518` (`setLevel`) clamps any request to `max(can_choose)`. The tray level buttons (`app.js:763`) and the ladder rows (`app.js:541`) are disabled or ignored. The person cannot even preview level 5.
- `web/robokit.js:672`: tolerance is the floor of the mean of C1 to C4. It drops one step if the answers spread by 3 or more, and a flag card is raised (`:673-676`). FINRA calls averaging contradictory answers a poor practice (see §2.2). Robo-Kit partly offsets this by flagging the conflict.
- `web/app.js:471` and `:491`: "Back" and "Change answer" re-ask by appending a new question card at the bottom. The old answered card stays in the transcript. Gate, flag and profile cards are appended in between. This is a likely cause of the cluttered transcript.

---

## 1. Risk-profiling products

### 1.1 Wealthsimple managed portfolios (Canada, robo-adviser)
URLs:
- https://help.wealthsimple.com/hc/en-ca/articles/26129491261211-Understanding-the-managed-portfolio-risk-assessment (updated 28 Sep 2026)
- https://help.wealthsimple.com/hc/en-ca/articles/360058461233-Update-your-portfolio-risk-level-or-switch-portfolios (updated 15 Sep 2026)

- Four risk dimensions: "We consider four risk dimensions in your assessment". They are Portfolio risk, Risk required, Risk capacity and Risk tolerance.
- Tolerance is measured with one item: "a slider-style question with four positions: Very low risk, Low risk, Moderate risk, and High risk."
- Four suitability checks (emergency fund, high debt, limited cushion, source of funds): "These checks can lower the maximum risk level available to you". Also: "they act as a ceiling, not a penalty."
- Borrowed money: "If the money you're investing is borrowed rather than saved, we apply a lower risk ceiling".
- An explanation block: "Your financial situation sets the ceiling". The page has a section titled "Why you were recommended this portfolio".
- Ceiling rule: "Your recommendation is a ceiling, not a floor".
- Short re-profiling: "Answer a short three-question reassessment to get an updated risk level recommendation for your current account."
- Going to 100% equities: "To move your account into 100% equities, you'll need to connect with one of our Portfolio Managers".
- Levels shown to clients are 2, 5, 8 and 10 of 10 (Conservative, Balanced, Growth, Aggressive).
- Takeaway: Robo-Kit's gates G2/G3 and its "lower of" rule are close to Wealthsimple's. But Wealthsimple is a discretionary manager with a human escalation path. Robo-Kit has no path at all: no PM, no override.

### 1.2 Betterment (US robo)
URL: https://www.betterment.com/resources/recommended-allocation-methodology
- The recommendation is built on capacity, then the client chooses: "Clients have the option to agree with this recommendation or to deviate from it."
- There is a live slider with outcome ranges: "until they find the allocation that has the expected range of growth outcomes they are willing to experience for that goal"
- Named bands relative to the advice: "Very Aggressive: This risk setting is associated with an allocation that is more than 7 percentage points above our recommended allocation to stocks."
- Warning copy when going above the advice: "exposes you to higher potential losses in the short-term".
- Warning copy when going below: "you may sacrifice potential returns in order to limit your possibility of experiencing losses."

### 1.3 Vanguard investor questionnaire (educational, self-directed)
URL: https://institutional.vanguard.com/content/dam/inst/iig-transformation/offers/vrpa/pdf/participant-education-resources/investor-questionnaire.pdf
- "A suggested investment mix is just an example of a mix that someone with your risk tolerance and investment time horizon may consider."
- "you may decide to use a more conservative or a more aggressive asset mix."
- "So it’s smart to change your mix gradually."
- This is the closest analogue to Robo-Kit Path A: an impersonal educational tool that suggests a mix and still lets the person go either way.

### 1.4 Morningstar Risk Profiler, powered by FinaMetrica
URLs:
- Methodology PDF, dated May 30 2026: https://developer.morningstar.com/content/hidden-from-navigation/MorningstarRiskProfilerMethodology_v4.pdf
- https://www.morningstar.com/financial-advisors/should-your-clients-risk-profile-align-with-their-risk-tolerance
- https://riskprofiling.com/Support
- https://help.adviserlogic.com/en/articles/10584886-morningstar-risk-profiling-powered-by-finametrica

- There is a psychometric test plus a rules matrix that firms can tune: "Firms can customize the rules to align with their policies or professional judgment."
- Comfort is a band, not a single cap: "Risk tolerance is not just an upper limit on a negative."
- "For an individual with a suitability score of 80, the Risk Comfort Range is between 82% to 100% growth assets". The chart shades from comfort through "Marginal Comfort" to "Discomfort".
- A start-slow option for high tolerance with no experience: "It may be worth considering and discussing with the client a start-slow approach"
- Conservative default: "Our approach with the PJM is to err on the side of the conservative."
- Mismatches must be confirmed, not silently blocked: "it’s prudent to confirm any discrepancies between risk tolerance and risk profile selection with clients." Also: "advisors must ensure that clients are doing so knowingly, alternatives have been considered"
- Length: "The FinaMetrica Risk Tolerance Toolkit™ takes 10 to 15 minutes to complete." There is a 25-question and a 10-question version. The AdviserLogic page says the client RTQ "consists of 10 questions".

### 1.5 Oxford Risk, Investor Compass (UK, behavioural)
URLs:
- https://www.oxfordrisk.com/solutions/investor-compass-risk-suitability
- https://www.oxfordrisk.com/blog-posts/from-attitude-to-aptitude-why-risk-tolerance-alone-cant-determine-suitable-risk
- https://help-centre.oxfordrisk.com/en/support/composure

- "Between two and ten minutes to complete"
- Tolerance alone is often wrong: "if you only rely on Risk Tolerance, you’ll recommend an inappropriate portfolio 60% of the time."
- Knowledge is a temporary brake: "Knowledge & Experience – a more objective gauge of how familiar the investor is with investing, which can constrain risk temporarily."
- Composure is measured separately from tolerance: "Lower Composure investors are likely to be more reluctant to invest, and are more at risk of buying high and selling low."
- High capacity can raise the level above tolerance: "it could be suitable to increase their Suitable Risk Level relative to their Risk Tolerance". This is the opposite of a strict "lower of" rule.

### 1.6 Nitrogen (formerly Riskalyze)
URL: https://nitrogenwealth.com/risk-tolerance-questionnaire/
- "Our Risk Assessment is built to quantify a client’s risk tolerance in less than 5 minutes."
- "Using real dollar amounts, each question builds off the last to make a truly interactive experience."
- "Nitrogen generates their Risk Number® on a scale of 1-99"

### 1.7 Pocket Risk
URL: https://pocketrisk.com/methodology/
- "The Pocket Risk questionnaire has 15 questions in 4 sections."
- Goals, tolerance, capacity and biases: "Each of these elements is scored separately."
- It explains "why we give 7 options for many of the questions" (to spread responses out).

### 1.8 Futu (HK broker plus robo-adviser)
URLs: https://www.futuhk.com/hans/support/topic2_1648 and https://www.futuhk.com/hans/support/topic2_28
- Five types, from low to high: conservative, steady, balanced, growth and aggressive.
- The score combines ability and willingness: it is set by the scores of the investment-ability and investment-willingness questions together.
- The robo questionnaire is nested under the account ceiling: the robo-advice risk level is at or below the investor's risk-tolerance assessment level.
- Stale-result pitfall: the robo-advice questionnaire result is not updated automatically.

### 1.9 Tiger Brokers
URL: https://www.itiger.com/hk/en/help/detail/54674404
- "customers can only buy products whose risk rating is equal to or lower than their own risk tolerance rating."

### 1.10 Alipay / Ant Fortune (from news reports; no official page found)
URLs:
- 21st Century Business Herald, 29 Sep 2020: https://m.21jingji.com/article/20200929/herald/0964e716ce59b74c697c94f38fe118da_zaker.html
- International Finance News via STCN, 21 Jun 2024: https://stcn.com/article/detail/1237949.html
- Tiantian Fund (East Money), 24 Sep 2026: https://fund.eastmoney.com/a/202609243882833635.html

- Dissuasion at scale: Alipay was still turning away 340,000 clients whose risk level did not match, and had earlier turned away 4 million purchases that did not match the buyer's risk tolerance.
- Bank apps show three documents in a row when a buyer goes above their level: a purchase notice for medium-to-high-risk products, a risk-mismatch warning letter and an investor confirmation.
- Gaming risk: the reporter re-rated themselves and the product unlocked: after changing their own assessment to A5 (aggressive) and confirming they acted voluntarily and understood the risk, the product could be bought again.
- Friction is by design: buyers face lengthy risk warnings, pop-up confirmations or even a block on the trade.
- New 2026 rules, as reported: the Asset Management Association of China (AMAC) published detailed investor-suitability rules for public securities investment funds on 11 June 2026. Product risk levels are to use quantitative inputs such as maximum drawdown and volatility.

---

## 2. Regulators and professional guidance

### 2.1 Canada: CSA and CIRO
**Companion Policy 31-103** (BCSC PDF, Dec 31 2021): https://www.bcsc.bc.ca/-/media/PWS/New-Resources/Securities-Law/Instruments-and-Policies/Policy-3/31103-CP-December-31-2021.pdf
- "should reflect the lower of (a) the client’s willingness to accept risk and (b) the client’s ability to endure potential financial loss"
- "The questions at the source of this conflict should be revisited with the client."
- "alternatives should be clearly explained such as saving more, spending less or retiring later."
- "A client’s risk profile should not be manipulated to justify recommending higher-risk products"
- "Registrants should always make further inquiries if the information provided by a client appears to be inconsistent". The example given is limited knowledge combined with high risk.
- §8.25 exemption for "advising generally" covers advice that "does not claim to be tailored to the needs and circumstances of any recipient". This matters for Path A. A hard cap computed from personal answers makes the page look more tailored, not less. This is an inference, not a regulator statement.

**CFR FAQ** (ASC PDF, updated Dec 6 2023): https://www.asc.ca/-/media/ASC-Documents-part-2/Market-Reg/2023/CFR-FAQ.ashx
- "A registrant has no obligation to accept a client order or instruction that, in the registrant’s view, is not suitable"
- "If the client does not choose to follow the registrant’s recommended alternative action, then the registrant can proceed with the original unsolicited client order"
- "The registrant must also receive recorded confirmation of the client’s instructions to proceed"
- "In our view, marking the order as unsolicited is not sufficient."
- Put together, the Canadian pattern for "above my profile" is: explain why, offer a suitable alternative, get a recorded confirmation, then allow.

**CSA Staff Notice 31-342, online advice** (FCAA SK PDF, Sep 24 2015): https://fcaa.gov.sk.ca/public/plugins/pdfs/2493/31_342_csa_staff_notice_september_24_2015.pdf
- "test for inconsistencies in the answers (for example, answers that indicate both low risk tolerance and a maximum growth objective)"
- "A KYC questionnaire used with an online platform cannot be just a “tick the box” exercise."
- "offer investor education about the terms and concepts involved"

### 2.2 US: FINRA, Report on Digital Investment Advice (Mar 2016)
URL: https://www.finra.org/sites/default/files/digital-investment-advice-report.pdf
- "The tools FINRA reviewed seek answers to between four and twelve questions"
- "Averaging is a poor practice, as it can result in a customer being placed in a portfolio that exceeds his or her risk tolerance."
- Resolve contradictions "by making a customer aware of contradictory responses and asking additional questions to resolve the inconsistency".
- "Problems can arise when risk willingness exceeds risk capacity."
- On re-profiling: "If investors frequently change their profile, an effective practice is for broker-dealers to contact the investor to understand why"

### 2.3 UK: FCA, Automated investment services (first published 21 May 2018, updated 7 May 2024)
URL: https://www.fca.org.uk/publications/multi-firm-reviews/automated-investment-services-our-expectations
- "We saw examples where clients could disregard advice given by the automated offering without any safeguards or risk warnings to prevent or challenge this."
- "some services failed to request or gather adequate information about customers’ debt and other outgoings"

### 2.4 EU: ESMA MiFID II suitability guidelines (23 Sep 2022, ESMA35-43-3172)
URL: https://www.esma.europa.eu/sites/default/files/library/esma35-43-3172_final_report_on_mifid_ii_guidelines_on_suitability.pdf
- In-flow inconsistency alerts: "incorporating in the questionnaire design features to alert clients when their responses appear internally inconsistent and suggest them to reconsider such responses"
- Help text in place: "through the use of design features, such as tool-tips or pop-up boxes"
- Ask about losses, not feelings: "instead of asking whether a client feels comfortable with taking risk, the firm should ask what level of loss over a given time period"
- Neutral layout: "The layout should be carefully elaborated and should avoid orienting investors’ choices (font, line spacing…)"
- Pre-filled answers must be reviewable: "the client is given the opportunity to review and, if necessary, correct and/or complete each of the pre-filled answers"
- "Firms should avoid stating, or giving the impression, that it is the client who decides on the suitability of the investment". For Robo-Kit, the override copy should say "you chose to explore level 5, which is outside your range", not "you chose level 5 as suitable".

### 2.5 China: CSRC suitability measures and AMAC fund guideline
**Suitability measures for securities and futures investors** (CSRC): https://www.csrc.gov.cn/csrc/c106256/c1653849/content.shtml
- Art. 19: a product or service riskier than the investor can bear calls for a special written risk warning. If the investor still insists on buying, the firm may sell the product or provide the service.
- Art. 22(5) forbids selling to investors in the lowest risk-tolerance category any product or service whose risk level is above their risk tolerance.

**Investor suitability guideline for fund sellers (trial)** (AMAC 2017; read from a fund-company mirror because the amac.org.cn link returned 404): https://www.susingfund.com/contents/2024/1/20-caf37c3598334536b477e90854c9b1d4.html
- Art. 48: the buyer confirms they fully understand that the fund product or service is riskier than they can bear.
- Art. 16 requires an online record of the confirmation: when the process runs online or otherwise remotely, the fund seller and partner platforms must keep a traceable record of the investor's confirmation.
- Art. 29 defines the lowest category, for example investors with no risk tolerance or unwilling to bear any investment loss.
- Users in China already expect this sequence: C1–C5 labels, then a risk-mismatch notice, then a special warning, then a confirmation, then allowed. A hard wall is less familiar to them, except for the lowest category.

### 2.6 CFA Institute Research Foundation: Grable, "Financial Risk Tolerance: A Psychometric Review" (2017)
URL: https://rpc.cfainstitute.org/research/foundation/2017/financial-risk-tolerance
- "financial advisers should be skeptical of claims that one, two, or three questions can be used to adequately measure a person’s risk tolerance"
- "financial advisers should use risk-tolerance questionnaires with a reported reliability estimate of at least 0.70"
- "Validity in this context means that the items reflect actual risk tolerance, not concepts related to time horizon, spending plans, or risk capacity."
- Implication: Robo-Kit's tolerance comes from four items (C1–C4). A hard wall built on that little data is fragile, which supports soft bands.

---

## 3. Conversation design for guided flows in chat

### 3.1 Nielsen Norman Group
URLs:
- https://www.nngroup.com/articles/genui-buttons-and-checkboxes/ (6 Mar 2026)
- https://www.nngroup.com/articles/chatbots/ (2018)
- https://www.nngroup.com/articles/site-ai-chatbot/ (20 Mar 2026)
- https://www.nngroup.com/articles/wizards/ (2017)
- https://www.nngroup.com/articles/chat-ux/ (2019)

- AI chat is starting to include form elements: "Simple interactive elements — buttons, form fields, checkboxes — are starting to appear contextually within conversations"
- Claude's AskUserQuestion keeps a tight limit: "the AskUserQuestion model seems to currently limit its use to four questions max."
- Tap or type: "for more complex questions, the user should be able to type their answer in an open-text field immediately below the question."
- Why it matters: "In AI chat, they prevent the back and forth that makes chat feel slow or tiring."
- Linear bots break when people go off-script: "they have a hard time whenever users deviate from such flows". NN/g's recommendation: "infer context and allow people to jump forward and backward in the linear flow."
- Buttons for common inputs: "Predetermined links and buttons saved users from typing."
- Don't forget what the person said: "The bot asked for her address a second time, having apparently forgotten altogether that she had already entered her address."
- Transcripts get long: chat will "force users to hold more information in working memory or scroll back to find earlier results."
- Wizards: "Communicate a clear mental model of the process by displaying a list or a diagram of the steps involved and highlighting the current step." Also: "Wizards are not gracefully interruptible."
- Chat UX: "It’s very annoying when the chat agent asks again for the same information". One guideline is titled "Allow Users to Save a Transcript of the Session".

### 3.2 GOV.UK Design System
URLs:
- https://design-system.service.gov.uk/patterns/question-pages/
- https://design-system.service.gov.uk/patterns/check-answers/
- https://designnotes.blog.gov.uk/2015/07/03/one-thing-per-page/

- "Make sure to only ask for a piece of information once within a single journey."
- "Start by testing your form without a progress indicator to see if it’s simple enough that users do not need one." If one is needed, the simple form is "Question 3 of 9".
- "Always include a Back link component at the top of question pages"
- "Avoid using range slider questions"
- Check answers: "If a user decides to go back to a previous answer, make sure information they’ve already entered is pre-populated." After a change: "They should not need to go through the rest of the transaction again."
- One question per page: "they’re better at handling things like errors, branches, loops and saving progress"

### 3.3 Google conversation design
URL: https://developers.google.com/assistant/conversation-design/learn-about-conversation
- "Because users are cooperative, they often offer more information than is literally required of them."
- "Cooperative users will be frustrated by having to repeat the shoe size again."
- "In conversation, saying too much is as uncooperative as saying too little."

### 3.4 Research: chatbot surveys vs web forms
- Kim, Lee, Gweon, CHI 2019. Abstract via Semantic Scholar: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3290605.3300316?fields=title,abstract,year. Chatbot respondents "were more likely to produce differentiated responses and were less likely to satisfice".
- Xiao et al., TOCHI 2020, https://arxiv.org/abs/1905.10700: "the chatbot drove a significantly higher level of participant engagement and elicited significantly better quality responses"

---

## 4. Mobile patterns

- NN/g bottom sheets (2023), https://www.nngroup.com/articles/bottom-sheet/:
  - Close button (wording is verbatim, including the typo): "include a visible a Close (or X) button on the screen"
  - Back support: "You can prevent this issue by supporting the use of Back for dismissing the bottom sheet"
  - Reach myth: "the middle of the screen represents the most easily tappable area"
- Apple HIG Sheets, https://developer.apple.com/design/human-interface-guidelines/sheets:
  - "Use a sheet only as a temporary interruption to the current workflow, and only to facilitate an important task."
  - "detents specify particular heights at which a sheet naturally rests"
- Baymard, https://baymard.com/blog/button-design: "Always Provide Sticky “Apply” Buttons in the Mobile Filtering Interface"

---

## 5. Cross-cutting patterns

1. **Two axes, one ceiling (for managed or advised products).** Capacity and tolerance are measured separately, and the lower one wins (CSA CP 31-103, Wealthsimple, Futu). Profilers aimed at advisers (Morningstar, Oxford Risk) allow judgment, with bands and adjustments.
2. **Going above the level means friction, not a wall.** The sequence in Canada (CFR FAQ) and China (CSRC Art. 19, AMAC Art. 48) is: explain, offer an alternative, get explicit confirmation, record it. Betterment and Vanguard's educational tool allow it with warning copy. The FCA criticised overrides that came with no warning at all. Hard walls show up where there is a human escalation path (Wealthsimple, CMB bank) or for the lowest risk category.
3. **Hard caps invite gaming.** Self-rated tests can be retaken to unlock products (STCN 2024). FINRA suggests watching for frequent profile changes.
4. **Resolve contradictions; don't average them.** FINRA, ESMA and CSA 31-342 all call for in-flow alerts and a chance to reconsider.
5. **Length.** FINRA saw 4 to 12 questions. Wealthsimple reassesses with 3. Pocket Risk has 15. FinaMetrica has 10 or 25 and takes 10 to 15 minutes. Oxford Risk takes 2 to 10 minutes and Nitrogen under 5. Grable warns that 1 to 3 tolerance items are unreliable.
6. **Chat plus form hybrid.** Show one question at a time with tap options and a free-text field. Don't re-ask what the person already said; pre-fill and let them confirm. Use a check-answers summary with Change links. Allow resuming.
7. **Show dollars and scenarios instead of self-rating.** ESMA asks for a "level of loss over a given time period". Nitrogen uses real dollar amounts, and Betterment's slider shows outcome ranges live.
8. **Product risk labels are becoming quantitative in China** (2026 AMAC rules, as reported): drawdown and volatility drive R-levels.
9. **Mobile.** Use sheets for short tasks, with a visible close button and Back support, and a sticky apply button.
