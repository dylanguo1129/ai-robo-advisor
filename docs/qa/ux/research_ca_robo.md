STATUS: COMPLETE

# Canadian robo-advisors and one-ticket ETFs: onboarding, risk levels, overrides, fees, accounts

Research date: 28 Sep 2026. Method: official pages and help centres fetched directly (curl with a browser user agent, because WebFetch got HTTP 403 on help.wealthsimple.com and questrade.com), plus reviewers (Million Dollar Journey, Savvy New Canadians, Ratehub, GrowSimple) and the regulator notice CSA 31-342. All quotes below are verbatim from the page at the URL and under 25 words. Cursor and agy were not used in this lane; it was assigned WebSearch/WebFetch directly.

Gaps (being upfront about them):
- BMO SmartFolio official pages (bmo.com) timed out twice, both through WebFetch and curl. BMO facts below come from a Million Dollar Journey review I verified verbatim, plus Ratehub's fee table.
- Reddit blocked the fetch (HTTP 403). No Reddit threads or app-store reviews were read, so there are no end-user complaints here.
- "TD Automated Investing" is a TD Bank **U.S.** product (Cherry Hill, N.J.). The Canadian URL returns 404. I found no Canadian TD robo-advisor.
- National Bank: NBDB's InvestCube is **closed to new accounts**. I found no active NBDB/NBI robo-advisor.
- For the one-ticket ETFs, I checked only XEQT, VEQT and ZGRO against official documents. Fees for VGRO, VBAL, XGRO and XBAL are UNSOURCED here.
- Search-engine summaries got three things wrong or out of date, so every number below comes from a page I fetched myself:
  - They said InvestCube has no extra cost. The official page shows a 0.30%–0.50% rebalancing fee and says new accounts are closed.
  - They presented TD Automated Investing as if it were available in Canada.
  - Reviewers list Wealthsimple SRI and Halal portfolios, but Wealthsimple's help centre now names only Classic, Summit and Income.

---

## 1. Wealthsimple Managed Investing (Classic / Summit / Income)

**Onboarding / questionnaire**
- The suitability assessment covers four areas: goal, timeline, risk tolerance and household financials. Source: https://help.wealthsimple.com/hc/en-ca/articles/35584545350555-Open-a-Classic-portfolio. Quote: "you'll complete a suitability assessment that checks your goal, timeline, risk tolerance, and household financials."
- Risk tolerance is **one** slider question with four positions. Source: https://help.wealthsimple.com/hc/en-ca/articles/26129491261211-Understanding-the-managed-portfolio-risk-assessment. Quote: "a slider-style question with four positions: Very low risk, Low risk, Moderate risk, and High risk."
- Each slider position has a plain-language description (same URL). Quote: "Each position comes with a plain-language description so you can choose the one that best reflects how you'd respond to a loss."
- The household financials asked for are income, savings, assets, debts and source of funds (same URL). Quote: "Household financials include your income, current savings, the value of your assets, your debts, and your source of funds."
- The model has four risk dimensions (same URL). Quote: "We consider four risk dimensions in your assessment: Portfolio risk Risk required Risk capacity Risk tolerance".
- Four suitability checks act as a ceiling (same URL). Quote: "These checks can lower the maximum risk level available to you — they act as a ceiling, not a penalty."
- The four checks are: emergency fund, high debt, limited cushion (income, net worth or age), and source of funds (borrowed money lowers the ceiling). Same URL. Quote: "If the money you're investing is borrowed rather than saved, we apply a lower risk ceiling".
- Changing risk later takes a 3-question reassessment. Source: https://help.wealthsimple.com/hc/en-ca/articles/360058461233-Update-your-portfolio-risk-level-or-switch-portfolios. Quote: "Answer a short three-question reassessment to get an updated risk level recommendation for your current account."
- The assessment is repeated yearly. Source: 26129491261211 article. Quote: "We review your managed portfolio's risk assessment yearly to make sure you're on track to achieving your goals."
- Reviewer claim, not confirmed by Wealthsimple: 8–10 questions. Source: https://www.growsimple.ca/wealthsimple-robo-advisor-review-2026-is-it-worth-the-fee/. Quote: "Answer 8–10 questions about your timeline, financial goals, income, risk tolerance, and how you'd react to market downturns".

**Risk display and override**
- Four named levels, each also shown on a 10-point scale: Conservative 2/10, Balanced 5/10, Growth 8/10, Aggressive 10/10. Source: https://help.wealthsimple.com/hc/en-ca/articles/360058004294-Advice-on-risk-profiles. Quote: "Wealthsimple's managed portfolios use four risk profiles. Each profile corresponds to a different mix of stocks, bonds, and gold".
- **Clients cannot pick a riskier level than recommended.** Source: 360058461233 article. Quote: "Your recommendation is a ceiling, not a floor — you can always choose something more conservative".
- Same article. Quote: "Moving to a higher risk level depends on your suitability assessment".
- Source: 26129491261211 article. Quote: "Moving to a higher level is capped by what your financial situation supports."
- The app shows the highest level still allowed (same URL). Quote: "the app will show you the highest level that's appropriate given your circumstances."
- Wealthsimple explains why a person got their recommendation, in order: goal and timeline set the base, tolerance shapes it, the checks set the ceiling, then the portfolio type is matched (same URL). Quote: "Your financial situation sets the ceiling — if any of the four suitability checks apply".
- The recommendation is presented as the highest suitable level, not the only option (same URL). Quote: "The recommendation is the highest level we consider suitable".
- 100% equities goes through a human. This is a search-snippet claim only: I did not load that exact sentence, so it is UNSOURCED.

**Portfolio display**
- Projections are shown as a cone chart. Source: https://help.wealthsimple.com/hc/en-ca/articles/18970042588443-Understand-risk-and-how-Wealthsimple-assesses-it. Quote: "You can see this range represented in the app as a cone chart".
- Each portfolio holds 8–10 ETFs, one per asset class, and holdings vary by account and tax status. Source: https://help.wealthsimple.com/hc/en-ca/articles/360056590494-Wealthsimple-s-portfolio-asset-classes-and-securities. Quote: "your individual holdings may vary based on your account type, time horizon, or tax status."
- Each asset class has a list of alternative ETFs (for example XIC, VCN, ZCN and XIU for Canadian equities). Same URL.
- A tax banner appears when switching in a non-registered account. Source: 360058461233 article. Quote: "If your account is non-registered, you'll see a tax banner before confirming."

**Fees** (source: https://www.wealthsimple.com/en-ca/pricing)
- Core. Quote: "0.5% management fees on managed investing accounts".
- Premium ($100,000+). Quote: "0.4% management fees on managed investing accounts".
- Generation ($500,000+). Quote: "0.2%*–0.4% management fees on managed investing accounts".
- Summit eligibility. Source: 26129491261211 article. Quote: "Summit requires at least $30,000 in liquid assets and $30,000 in net worth."

**Accounts**
- Classic can be opened in TFSA, FHSA, RESP (individual and joint), RRSP (including spousal), non-registered (individual and joint), RRIF, LIRA and LIF. Source: 35584545350555 article.

**Portfolio types**
- The help centre names Classic, Summit and Income (26129491261211 article). Quote: "Your portfolio type — Classic, Summit, or Income — is then matched to that risk level".
- Savvy New Canadians (https://www.savvynewcanadians.com/wealthsimple-invest-review/) still lists SRI and Halal, and 3 levels. Quote: "Choose your portfolio type such as Classic, SRI, or Halal, and your risk level (Conservative, Balanced, or Growth)."
- This conflicts with the official 4-level, Classic/Summit/Income set. Treat the reviewer version as out of date.

---

## 2. Questwealth Portfolios (Questrade)

**Onboarding**
- Questrade says a match takes 15 minutes. Source: https://www.questrade.com/questwealth-portfolios/etf-portfolios. Quote: "Get matched with an ETF portfolio in just 15 minutes".
- Same URL. Quote: "Answer a few simple questions to evaluate your financial situation, goals and feelings towards risk."
- Reviewer count of ten questions. Source: https://www.savvynewcanadians.com/questwealth-portfolios-review/. Quote: "answer ten questions so the system can determine your risk tolerance and investment objectives and recommend a portfolio".
- The questionnaire can be retaken at any time. Source: https://www.questrade.com/learning/questrade-basics/explore-questmobile/questwealth-portfolios. Quote: "You can retake the risk tolerance questionnaire anytime, whether it's for an annual review or a change in your investment goals."

**Risk display and override**
- The results screen shows, in order: Recommended portfolio, Risk level, Asset allocations (with a chart or list toggle), then Management fee, Historical performance and Disclosure. Same learning URL.
- **To get a different portfolio, the client has to redo the questionnaire. I found no direct picker.** Quote: "If you'd like to change the information you provided, please select Redo your questionnaire".
- A human reviews changes. Quote: "Please allow 1-2 business days for us to review the changes."
- There are five portfolios, from Conservative to Aggressive Growth (100% equity). Source: etf-portfolios URL. Quote: "the Aggressive Growth portfolio can be right. This portfolio invests in 100% equity."
- Model portfolio performance is published publicly (etf-portfolios URL). Quote: "Since inception in Nov 2014, this portfolio has returned".
- The published returns are shown before fees (same URL). Quote: "management fees, optional charges or income taxes payable by Questwealth clients that would have reduced returns are not taken into account."
- SRI portfolios exist. Same URL, heading "Socially Responsible Investment (SRI) Portfolios".

**Fees** (source: https://www.questrade.com/questwealth-portfolios)
- "0.25% with a balance of $250-$99,999"
- "0.20% with a balance of $100,000+"
- Minimum per Million Dollar Journey (https://milliondollarjourney.com/questwealth-portfolios-review.htm). Quote: "Minimum investment required of $1,000".
- Tax-loss harvesting is offered (same review). Quote: "services such as automatic rebalancing and tax-loss harvesting".
- Rebalancing (main page). Quote: "Real-time rebalancing".

**Accounts**
- RRSP, TFSA, FHSA, RESP and "Cash" (non-registered). Source: main page.
- The FHSA description (same page). Quote: "A tax-free account that you can use to save up to $40,000 towards your first home".

---

## 3. Justwealth

**Onboarding**
- The first step is an investment questionnaire, with a recommendation per account. Source: https://www.justwealth.com/faqs/. Quote: "you will immediately receive a recommended portfolio based on your answers for each account you plan to open."

**Portfolios**
- More than 80 portfolios. Source: FAQs. Quote: "We currently offer over 80 different portfolios".
- Target-date RESP portfolios (FAQs). Quote: "Target date portfolios are ideal investment solutions when there is a well-defined time horizon such as a pending retirement or education enrollment date."
- Reviewer claim that this is unique. Source: https://milliondollarjourney.com/justwealth-review.htm. Quote: "The only Canadian robo advisor to offer target-date RESP accounts."

**Override**
- Clients cannot pick their own ETFs. Source: FAQs. Quote: "Am I able to pick my own Exchange Traded Fund(s)? No."
- Same page. Quote: "the portfolios are managed by Justwealth on a fully discretionary basis."

**Plan features**
- A personalised Investment Policy Statement for every account. Source: FAQs. Quote: "All clients will receive a personalized Investment Policy Statement for each account that is opened with Justwealth."
- Benefits listed on https://www.justwealth.com/pricing/: "Dedicated Personal Portfolio Advisor", "Personalized financial planning" and "Tax loss harvesting".

**Fees**
- Base rate. Source: https://www.justwealth.com/. Quote: "A Justwealth client would pay a low, annual management fee of 0.50%".
- Tiers per Ratehub (https://www.ratehub.ca/investing/robo-advisors): "0.5% on first $500K" and "0.4% on $500K+".
- Minimum fee. Source: pricing page. Quote: "The minimum Justwealth management fee is $4.99/month for all account types (excluding RESPs/FHSAs/RDSPs)."
- Minimum account size (pricing page). Quote: "Minimum account size is $5,000 for all non-RESP/FHSA/RDSP accounts."

**Accounts**
- The pricing page names RESP, FHSA and RDSP. RRSP, TFSA, non-registered and RRIF also appear in the FAQs, for example: "RESP, RRIF, TFSA, FHSA and non-registered accounts: No fee."

---

## 4. CI Direct Investing (formerly WealthBar; site now at cifinancial.com/ci-di)

**Fees** (source: https://www.cifinancial.com/ci-di/ca/en/invest/pricing.html)
- "First $150,000 0.60% annually"
- "Next $350,000 0.40% annually"
- "Above $500,000 0.35% annually"
- Minimum. Quote: "This could be as low as $100."
- No switching fees. Source: https://help.cidirectinvesting.com/en_US/fees-and-minimums/types-of-fees. Quote: "We do not charge additional fees for transactions, such as withdrawals or portfolio switching."

**How the recommendation is built**
- The recommendation depends on the amount invested. Source: https://help.cidirectinvesting.com/rds-changes. Quote: "If you're investing less than $50,000 ... we'll recommend a portfolio typically consisting of a single diversified investment fund".
- Leverage (same page). Quote: "we do not adjust our recommendation based on your use of borrowed funds for the purpose of investing". This is the opposite of Wealthsimple's source-of-funds ceiling.
- Onboarding time per reviewer (https://milliondollarjourney.com/ci-direct-investing-review-2020-formerly-wealthbar-the-robo-advisor-for-canadian-expats.htm). Quote: "you can get started in as little as ten minutes".
- Account types in that review include RESP, RRSP, TFSA, FHSA, RRIF, LIRA, LIF and Individual Pension Plans. I could not load the official account list; the site is JavaScript-rendered.
- Planning is described as a feature on the official page (https://www.cidirectinvesting.com/en/home.html). Quote: "our financial planners can work with you to build a financial plan so you can meet your goals."

---

## 5. RBC InvestEase

**Onboarding**
- Four to five minutes. Source: https://www.rbcinvestease.com/topics-trends/how-to-get-investment-portfolio.html. Quote: "Our questionnaire is done entirely online and usually takes about four or five minutes to fill out."
- Capacity questions (same URL). Quote: "Questions that ask how much you plan to invest, when you'll need the funds and the value of your net liquid assets are designed to assess your risk capacity."
- Tolerance framing (same URL). Quote: "does the idea of losing 5% of your investments make your palms sweat".
- A human reviews each recommendation (same URL). Quote: "Our accredited Portfolio Advisors will personally review your portfolio recommendation to make sure it's appropriate for you."

**Risk display**
- The article says five profiles (same URL). Quote: "recommend one of five portfolios for you: Very Conservative, Conservative, Balanced, Growth and Aggressive Growth."
- Allocations on that page: 20/80, 35/65, 55/45, 70/30 and 100% equity.
- RBC's homepage (https://www.rbcinvestease.com/) says six. Quote: "We offer six types of ETF portfolios, ranging from Short-Term Bond to Aggressive Growth." The official site contradicts itself.

**Override**
- The only choice offered is the ESG version, not the risk level. Source: homepage. Quote: "You can choose either the Core or Responsible Investing version of the portfolio we recommend for you".

**Small accounts**
- Starter portfolio (homepage). Quote: "For balances of $100 to $1,499, we will invest your money in a Starter Portfolio".

**Goal feature**
- NOMI Insights (homepage). Quote: "NOMI Insights for RBC InvestEase helps you make progress towards your financial goals by letting you know when you may have spare cash available to invest."

**Fees**
- Source: https://www.rbcinvestease.com/how-it-works.html. Quote: "RBC InvestEase charges an annual management fee of 0.50% + applicable sales tax".
- MERs are 0.11%–0.13% for standard and 0.18%–0.23% for RI. Source: https://www.rbcinvestease.com/accounts-investments.html.

**Accounts**
- Source: how-it-works. Quote: "the investment portfolio you hold in your TFSA, RRSP, FHSA or non-registered account(s)". RESP is not listed.

---

## 6. BMO SmartFolio (official bmo.com timed out; reviewer source verified verbatim)

**Onboarding**
- Source: https://milliondollarjourney.com/online-portfolio-manager-review-bmo-smartfolio.htm. Quote: "answering a series of personal and investment questions (10 multiple choice questions) and then you will be presented with a recommended model ETF portfolio".
- Same review. Quote: "The survey took under 10 minutes and didn't require me to sign up or pay for anything."
- The questions start with income, investment knowledge and timeline, and finish with volatility tolerance (same review).

**Fees**
- From the same review: "First $100,000: 0.70%", "Next $150,000: 0.60%", "Next $250,000: 0.50%", "$500,000 and greater: $0.40%". Ratehub gives the same tiers.

**Minimum**
- Quote: "Minimum account size: $1,000".

**Accounts**
- Quote: "You can open registered accounts (TFSA, RRSP, RESP, RRIF), non-registered accounts, and joint investment accounts." FHSA is not mentioned.
- The review also lists "No socially responsible investing (SRI) options".

---

## 7. TD Automated Investing: not a Canadian product

- Source: https://www.prnewswire.com/news-releases/td-bank-strengthens-investment-advice-offerings-with-launch-of-robo-advisor-301401130.html. Datelined CHERRY HILL, N.J. Quote: "aligns the client's risk profiles with one of U.S. Wealth's professionally managed portfolios".
- https://www.td.com/ca/en/investing/direct-investing/td-automated-investing returns 404 ("Sorry, we couldn't find what you're looking for.").
- I found no Canadian TD robo-advisor. Anything about a Canadian TD robo is UNSOURCED.

## 8. National Bank (NBDB InvestCube): closed to new clients

- Source: https://nbdb.ca/accounts/investcube.html. Quote: "It is no longer possible to apply for a new InvestCube account. Only existing accounts will remain active."
- The design is worth noting because it is the closest Canadian match to Robo-Kit's shelf. Quote: "Build your ETF portfolio by choosing from 5 asset classes".
- There are five mixes: Conservative, Moderate, Balanced, Growth and Equity (Equity = 15% fixed income / 80% equity, with 5% cash mandatory).
- Fee. Quote: "Rebalancing fee of 0.30% to 0.50%".
- Rebalancing rule. Quote: "The portfolio is rebalanced when an asset class deviates by 20% or more from its target weight."
- Minimum: $10,000.
- A human step before activation. Quote: "Our dedicated team will contact you by telephone to confirm your selection".

---

## 9. DIY benchmark: one-ticket asset-allocation ETFs

**XEQT** (source: https://www.blackrock.com/ca/investors/en/literature/fact-sheet/xeqt-ishares-core-equity-etf-portfolio-fund-fact-sheet-en-ca.pdf, August 2026)
- "Management Fee : 0.17%"
- "Management Expense Ratio (MER) : 0.19%"
- "targets a strategic asset allocation of 100% equity."
- "Continuously monitored and automatically rebalanced, as needed".
- The same factsheet's bullet still says "Management fee of 0.18%". The document contradicts itself.

**VEQT** (source: https://fund-docs.vanguard.com/VEQT_All_Equity_ETF_Portfolio_9692_FS_EN_CA.pdf, Aug 31 2026)
- "Effective November 18, 2025, Vanguard reduced the management fee for this ETF from 0.22% to 0.17%."
- MER is 0.22% as of March 31, 2026.
- Eligible accounts: "RRSP, RRIF, RESP, TFSA, DPSP, RDSP, Non-Reg, FHSA".

**ZGRO** (source: https://fundfacts.bmo.com/EtfEnglish/BMO_Growth_ETF-EN-CAD_Units.pdf)
- "Management expense ratio (MER)*: 0.20%"
- "The adjusted MER is 0.17%"
- Risk rating: "rated the volatility of this ETF as low to medium."
- This is the CSA standard fund risk scale, which is different from the robo-advisors' own 1–10 or named scales.

**VGRO, VBAL, XGRO, XBAL**: fees UNSOURCED (not checked against official documents in this lane).

---

## 10. Regulator reference: CSA Staff Notice 31-342 (online advisers)

Source: https://www.osc.ca/en/securities-law/instruments-rules-policies/3/31-342/csa-staff-notice-31-342-guidance-portfolio-managers-regarding-online-advice

What regulators expect from an online adviser's KYC questionnaire:
- Detect conflicting answers. Quote: "test for inconsistencies in the answers (for example, answers that indicate both low risk tolerance and a maximum growth objective)".
- Teach as you ask. Quote: "offer investor education about the terms and concepts involved".
- Use behavioural questions. Quote: "use a series of behavioural questions to establish risk tolerance and elicit other KYC information".

This notice applies to registered portfolio managers (discretionary). Robo-Kit's Path A (an impersonal learning simulator) is not a registered portfolio manager, so the "ceiling" these firms apply is a legal duty for them, not a UX law for Robo-Kit. That is my interpretation, not legal advice.

---

## 11. Implications for the two problems found in testing

**(1) A level-4 self-check hides level 5.**
- This copies the Wealthsimple rule exactly ("a ceiling, not a floor"). Wealthsimple does it because, as a discretionary portfolio manager, it is legally responsible for suitability.
- The rest of the market does the same: Questwealth makes you redo the questionnaire, RBC only offers the Core vs RI version, and Justwealth and CI are discretionary.
- Robo-Kit is a simulator. Hiding level 5 stops the person learning exactly what they came to learn.
- A better approach:
  - Keep "suggested" as the default.
  - Show levels above capacity as unlockable, not disabled: "Above what your answers support — see why".
  - Name the answer that set the cap (for example, "your 1-year range answer" or "G2: no emergency fund").
  - Offer (a) "change that answer" (one tap, no restart) or (b) "explore level 5 anyway", which shows the level 4 vs 5 crisis replays in dollars and requires one acknowledgement.
  - Keep a "simulated at a level above your self-check" label on every exploratory result.
- This beats Wealthsimple (which only shows the highest level allowed) and Questwealth (which forces a redo).

**(2) Onboarding and the chat thread are cluttered.**
- Competitors are short and linear:
  - RBC takes 4–5 minutes.
  - BMO: 10 multiple-choice questions, under 10 minutes, no sign-up.
  - Questwealth: 10 questions, "15 minutes".
  - Wealthsimple: one tolerance slider plus household financials, and a 3-question reassessment.
- They present one result screen in a fixed order: recommended portfolio → risk level → allocation chart/list → fee → history → next.
- Robo-Kit's 18+ gate plus 15 question cards, each posted into the chat, makes a long transcript.
- Suggestion: one stepper card that updates in place, with a progress bar and back/edit, then collapses into a single "Here is what I heard" summary. Keep the chat for questions only.
