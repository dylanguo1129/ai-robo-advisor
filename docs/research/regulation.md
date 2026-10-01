STATUS: COMPLETE

# What it legally takes to ship Robo-Kit in Canada and the US

Lane: regulation. Researched 2026-09-28. Not legal advice: this is a map of what regulators have written, so the team knows which questions to put to a securities lawyer in each country. Every quote below was copied from the page named next to it; 62 of them were machine-checked as exact substrings of the downloaded source text (see "Method" at the end). Where a page could not be opened, the report says so.

Extends `docs/METHOD.md` section 7, open item 3 ("Suitability ... the report should say the prototype is educational, not advice"), which is the only place the existing docs touch regulation.

---

## 1. In one minute (plain language)

1. **The legal line is "personal or not personal", not "AI or not AI".** Both countries regulate *advice tailored to a person*. General education, and tools that let people explore on their own, are treated much more lightly. Using AI does not change the rules in either direction.
2. **Robo-Kit today sits close to the line.** Asking someone about their risk and then showing them specific ETF weights "for them" looks like tailored advice. Canada's dealer regulator said in March 2026 that even a registered broker may not put named ETFs into a model portfolio for DIY clients, and that a disclaimer does not fix it.
3. **A disclaimer is not a shield.** Regulators look at what the product does, not what the footer says.
4. **What can ship now:** a free, impersonal learning simulator. It shows asset-class mixes by risk level, lets the user pick their own ETFs with neutral filters, shows the maths, labels every backtest as hypothetical, and has a chat that explains but never tells a person what to buy.
5. **What needs a licence (or a licensed partner):** telling a specific person "this is your portfolio", linking to their accounts, rebalancing their money, or charging for any of it.
6. **Building on Claude adds its own rule.** Anthropic's Usage Policy lists investment advice as a high-risk use. It requires a qualified human to review advice before it reaches consumers, and an AI disclosure at the start of every session.

---

## 2. The core question: is Robo-Kit "advising"?

### 2.1 Canada

| Test | What the regulator says | Source |
|---|---|---|
| Who must register as an advisor | Two advisor categories: "(a) portfolio manager; (b) restricted portfolio manager." | NI 31-103 s.7.2(1), OSC unofficial consolidation (2023-09-13) |
| The "business trigger" | Compensation need not be received: "It does not matter if the individual or firm actually receives compensation or in what form." The other factors are acting like a registrant, intermediating trades, repetition/regularity, and soliciting. | Companion Policy 31-103CP s.1.3, OSC consolidation (2022-01-05) |
| Exemption for non-tailored advice | Registration is not required "if the advice the person or company provides does not purport to be tailored to the needs of the person or company receiving the advice" | NI 31-103 s.8.25(2) |
| What "not tailored" looks like | It is general discussion of merits and risks, delivered through newsletters, websites and similar channels, that "does not claim to be tailored to the needs and circumstances of any recipient" | 31-103CP s.8.25 |
| Conflict disclosure under the exemption | If the exempt advisor (or its insiders) has a financial interest in a security it recommends, it must disclose that interest at the same time as the advice | NI 31-103 s.8.25(3) |
| Ontario is different | "This section does not apply in Ontario. Note: In Ontario, measures similar to those in section 8.25 are in section 34 of the Securities Act (Ontario)." | NI 31-103 s.8.25(5). **Securities Act (Ontario) s.34 itself: not opened** (ontario.ca and Qweri render by script). A lawyer must confirm the Ontario wording. |
| Where regulators drew the line for DIY tools (2026) | "OEO Dealers cannot avoid the revised recommendation prohibition by simply stating that a sample portfolio is not tailored to a specific client." and "OEO Dealers can make available sample portfolios that set out asset allocations and can also provide filtering tools relating to those allocations" | CIRO Bulletin 26-0059, 12 Mar 2026, "New guidance on order execution only account services and activities" ("The updated OEO Guidance is effective immediately.") |
| The same line, as a dealer-side reading | "It also clarifies that OEO dealers are prohibited from naming individual exchange traded funds (ETFs) or stocks in any of their sample portfolios." | TD Securities, 10 Apr 2026 (secondary source; CIRO's primary text is above) |
| AI changes nothing about the test | "Securities laws are generally technology-neutral and apply regardless of the technology being used to carry out a given activity." | CSA Staff Notice and Consultation 11-348 (5 Dec 2024) |
| The OSC's own reading on AI advice | "In Canada, regulations forbid firms from using AI to provide advice or recommendations without human oversight; this use case was observed in the other jurisdictions." | OSC, *Artificial Intelligence and Retail Investing: Use Cases and Experimental Research* (2024), footnote 1 |

**Reading for Robo-Kit (a lawyer must confirm):** CIRO's OEO guidance binds only CIRO dealer members, so it does not bind an unregistered educational tool. It is still the clearest recent statement of where Canadian regulators see the line. An asset-class mix by risk level, plus neutral filters that the user drives, is on the "education" side. A named-ETF portfolio for a profiled user is on the "recommendation" side. Robo-Kit's current flow (risk level, then ETF weights) is on the wrong side of that line unless it is redesigned (section 7).

### 2.2 United States

| Test | What the law / SEC says | Source |
|---|---|---|
| Definition | An investment advisor "means any person who, for compensation, engages in the business of advising others, either directly or through publications or writings, as to the value of securities or as to the advisability of investing in, purchasing, or selling securities" | Advisors Act s.202(a)(11), 15 U.S.C. 80b-2 (LII) |
| "Compensation" is broad | "Generally, the receipt of any economic benefit, whether in the form of an advisory fee, some other fee relating to the total services rendered, a commission, or some combination, satisfies this element." | SEC staff outline *Regulation of Investment Advisers by the U.S. SEC* (March 2013), summarising Release IA-1092 |
| Publisher's exclusion (Lowe v. SEC, 1985) | The newsletters were excluded because "they do not offer individualized advice attuned to any specific portfolio or to any client's particular needs". Congress "did not seek to regulate the press through the licensing of nonpersonalized publishing activities." | *Lowe v. SEC*, 472 U.S. 181 (LII) |
| Filters are not personalisation | Seeking Alpha's alert and filter features "merely allow the subscriber to filter generally available content that would be visible to any subscriber who looks for it or signs up for the same alerts." (S.D.N.Y., Aug 2024) | Greenberg Traurig alert (secondary; court opinion not opened) |
| Auto-trading breaks the exclusion | Weiss Research (2006): a newsletter whose "auto-trading" signals went to a broker-dealer, "which automatically traded subscriber/customer securities consistent with signals", was treated as a personalised advisor | SEC staff outline (March 2013), fn. 27 |
| What makes online advice "digital advice" | The 2024 rule defines digital investment advisory service as "investment advice to clients that is generated by the operational interactive website's software-based models, algorithms, or applications based on personal information each client supplies through the operational interactive website" | SEC Final Rule IA-6578 (Mar 2024) |

**Reading for Robo-Kit (a lawyer must confirm):** a tool that takes a user's personal financial information and returns a portfolio is what the SEC calls digital investment advice. The publisher's exclusion protects impersonal content that everyone can see. Being free weakens the "compensation" element, but only while there is no economic benefit of any kind (no ads, affiliate fees, issuer payments, paid tier or data sales). State advisor definitions were not researched (gap).

---

## 3. Canada in detail

### 3.1 Online advice by registered portfolio managers (CSA Staff Notice 31-342, 24 Sep 2015)

- "There is no “online advice” exemption from the normal conditions of registration for a PM."
- Approved online advisors are *hybrid*: an advising representative (AR) remains responsible for suitability. The portfolios are "relatively simple products, including unleveraged exchange traded funds (ETFs)".
- "A KYC questionnaire used with an online platform cannot be just a “tick the box” exercise."
- A well-designed online questionnaire must: use behavioural questions for risk tolerance; block progress until all questions are answered; "test for inconsistencies in the answers (for example, answers that indicate both low risk tolerance and a maximum growth objective), and will not let the client or prospective client complete the questionnaire until the conflict is resolved"; flag conflicts for an AR call; offer investor education; and remind the user that an AR is available. It should also prompt an update at least once a year.
- If a firm will not have an AR contact every client, CSA staff "may recommend that terms and conditions be imposed limiting it to using the relatively simple investment products described in this Notice".

Implication: this is the ready-made specification for Robo-Kit's questionnaire if it ever runs as, or for, a registered firm (see R4 in section 8).

### 3.2 Client Focused Reforms: KYC, KYP, suitability

Per Staff Notice 31-368, the reforms' "enhancements to KYC, KYP and suitability determination requirements came into force on December 31, 2021."

- **KYC facts a registrant must collect** (NI 31-103 s.13.2(2)(c)): personal circumstances, financial circumstances, investment needs and objectives, investment knowledge, risk profile and investment time horizon.
- **Risk profile = the lower of tolerance and capacity.** "The risk profile for a client should reflect the lower of (a) the client’s willingness to accept risk and (b) the client’s ability to endure potential financial loss." (31-103CP s.13.2) The same passage asks firms to identify "clients that are more suited to placing their money in cash deposits or guaranteed products because they are unwilling or unable to accept the risk of loss of capital".
- **Newest guidance (Joint CSA/CIRO Staff Notice 31-368, 10 Dec 2025):** questionnaires should ask separate questions for tolerance and for capacity, and firms should "avoid, for example, scenarios where a client with a low risk capacity and high risk tolerance is determined to have a high risk profile". The review also found firms that did not document client confirmation of their risk profile.
- **KYP (s.13.2.1):** before making a security available, a firm must assess "the securities’ structure, features, risks, initial and ongoing costs and the impact of those costs", approve it, and monitor it for significant changes.
- **Suitability (s.13.3(1)):** factors include concentration and liquidity, "(iv) the potential and actual impact of costs on the client’s return on investment; (v) a reasonable range of alternative actions available to the registrant through the registered firm", and the action must put the client's interest first.
- **Records:** "A registered firm must keep a record that it is required to keep under securities legislation (a) for 7 years from the date the record is created" (s.11.6).

### 3.3 NI 81-102 as it touches ETFs (OSC consolidation to 2024-08-31)

- **Who the sales-communication rules bind:** "sales communication" means a communication relating to, and by, a fund or asset allocation service, "its promoter, manager, portfolio adviser, principal distributor, a participating dealer or a person or company providing services to any of them". An independent, unpaid tool is probably outside this definition. Taking money from an ETF issuer could bring Robo-Kit inside it (lawyer to confirm).
- **Comparison discipline worth copying anyway:** a performance comparison with a benchmark must, among other things, include the facts that would materially change its conclusions, and "(b) it presents data for each subject of the comparison for the same period or periods" (s.15.3(1)). A fund's own performance data needs at least 12 consecutive months of history (s.15.6(1)(a)).
- **Official risk rating (Appendix F, as amended 2016, effective 2017):** every Canadian mutual fund, ETFs included, rates itself from the standard deviation of its last 10 years of monthly returns (n = 120). Funds younger than 10 years fill the gap with a reference index. The bands are "0 to less than 6 Low 6 to less than 11 Low to medium 11 to less than 16 Medium 16 to less than 20 Medium to High 20 or greater High". The fund discloses the rating in its ETF Facts (s.15.1.1). The formula image did not extract, so the annualisation factor must be read from the PDF before this is coded.
- Implication: Robo-Kit should *display the issuer's official rating from ETF Facts* and, separately, its own computed rating using the same bands, labelled as "computed by Robo-Kit". It should never replace one with the other.

### 3.4 Hypothetical and back-tested performance (CSA Staff Notice 31-325, 5 Jul 2011)

- Hypothetical data covers back-tested and model data, and "also includes statistics such as standard deviation and Sharpe ratios".
- Concerns the CSA names include hindsight and possible manipulation, splicing with real results, weak methodology disclosure, and that "PMs do not always deduct trading and other costs from the performance data".
- Expected practice for portfolio managers includes "restricting the presentation to investors known to have sophisticated investment knowledge (i.e. not widely disseminating the presentation on a website or in an advertisement)", labelling data "hypothetical" clearly and prominently, never linking it with actual returns, and disclosing methodology, assumptions, risks and limitations.
- **This conflicts with Robo-Kit's plan to publish backtests on a public web page.** The notice binds registered portfolio managers, not an educational site, but it shows how Canadian regulators view public backtests. The mitigation is to present backtests as simulations the user runs on their own inputs (the US "interactive analysis tool" pattern in 4.4), never as Robo-Kit's "track record". If Robo-Kit later operates through a registered PM, public backtests may have to come off the marketing pages. A lawyer must confirm.

### 3.5 AI-specific guidance (CSA Staff Notice and Consultation 11-348, 5 Dec 2024)

- Decision support is acceptable if the registrant "does not automatically act on it but rather, treats that information as no more than an input for their own decision-making". But "using an AI system directly in suitability determinations and trading decisions will be problematic unless a high degree of explainability is assured."
- Client chatbots: "Registrants using AI systems in this way should take steps to ensure that the AI systems will support the delivery of accurate information to clients."
- Outsourcing: "registrants cannot outsource registerable activity (e.g., trade suitability determinations for clients)." So a registered partner cannot simply hand suitability to Robo-Kit's engine.
- Monitoring should cover "model drift and hallucinations". Explainability is needed so firms can meet record-keeping duties.
- AI washing: "To avoid AI washing, vague and unsubstantiated statements that incorporate jargon in order to attract investors should not be made."
- **Anything newer:** one search found no final CSA AI instrument or response to the 11-348 comments (comments closed 31 Mar 2025). INSUFFICIENT EVIDENCE either way. The search was not exhaustive; recheck before launch.
- **Evidence on user behaviour (OSC 2024 experiment):** "we did not observe any material difference in adherence between our human and AI conditions". People follow AI suggestions about as closely as a human advisor's, which raises the stakes of a wrong AI suggestion.

---

## 4. United States in detail

### 4.1 Registration route if Robo-Kit gives personalised advice

- **SEC or state.** Subject to exemptions, "only advisers that advise a registered investment company or have assets under management above $100 million are allowed to register with the Commission"; smaller advisors register with the states. The national de minimis standard bars a state from requiring registration where the advisor has no place of business there and "has had fewer than six clients who are residents of that State during the preceding 12-month period". (SEC Final Rule IA-6578, background)
- **Internet adviser exemption (amended March 2024, compliance date 31 Mar 2025).** This is the route a small robo uses to register with the SEC instead of 50 states: "the amendments will require an internet investment adviser to provide investment advice to all of its clients exclusively through an “operational” interactive website at all times during which it relies on the Internet Adviser Exemption." The 2024 amendments also removed the old carve-out that allowed fewer than 15 non-internet clients. The release notes that advisors now reach clients through "chatbots, and other similar digital platforms", so a chat interface is compatible with the route.

### 4.2 SEC robo-advisor guidance (IM Guidance Update 2017-02, Feb 2017)

- "Robo-advisers, like all registered investment advisers, are subject to the substantive and fiduciary obligations of the Advisers Act."
- **Disclosures the SEC staff expects** include: the degree of human involvement; how the algorithm works; "A description of the assumptions and limitations of the algorithm used to manage client accounts (e.g., if the algorithm is based on modern portfolio theory, a description of the assumptions behind and the limitations of that theory)"; algorithm-specific risks; when the firm might override the algorithm; third-party involvement in the algorithm and the resulting conflicts; that questionnaire answers may be the sole basis of the advice; and how and when to update information.
- **Presentation:** key disclosures before sign-up, emphasised with pop-ups, tooltips and FAQs, and adapted for mobile.
- **Questionnaire:** questions clear enough, with tooltips; inconsistent answers flagged to the client or for review. Where a client picks a portfolio other than the one suggested, give "commentary as to why it believes particular portfolios may be more appropriate".
- **Compliance program topics:** "The development, testing, and backtesting of the algorithmic code" and monitoring after release; disclosure of code changes that materially affect portfolios; oversight of third parties that build or own the algorithm; cybersecurity; and marketing through social media, paid bloggers and refer-a-friend schemes.

### 4.3 Marketing Rule and hypothetical performance (17 CFR 275.206(4)-1; SEC staff FAQ "Updated Jan. 15, 2026")

- Hypothetical performance includes model-portfolio results and "Performance that is backtested by the application of a strategy to data from prior time periods when the strategy was not actually used during those time periods", plus targeted or projected returns.
- An advisor may show it only with policies making it relevant to the audience's financial situation, disclosure of criteria and assumptions, and "sufficient information to enable the intended audience to understand the risks and limitations of using such hypothetical performance in making investment decisions".
- General ban: an advertisement may not "Include or exclude performance results, or present performance time periods, in a manner that is not fair and balanced".
- **Carve-out that fits Robo-Kit's design:** an *interactive analysis tool* that users run themselves to produce simulations is not "hypothetical performance" if the advisor (1) describes criteria, methodology, limitations and key assumptions; (2) "Explains that the results may vary with each use and over time"; (3) describes the universe, how the tool selects investments and any favouritism, and "states that other investments not considered may have characteristics similar or superior to those being analyzed"; and (4) "Discloses that the tool generates outcomes that are hypothetical in nature".
- These are the four disclosures Robo-Kit should build into every backtest and optimizer screen, whatever its registration status.

### 4.4 FINRA (relevant only if a broker-dealer partner distributes Robo-Kit)

Confidence is medium for this subsection. finra.org blocked direct download, so these quotes come from a fetch tool's extraction and were not machine-checked.
- Regulatory Notice 24-09 (27 Jun 2024): FINRA rules are "technologically neutral". "The content standards of Rule 2210 (Communications with the Public) apply whether member firms' communications are generated by a human or technology tool". Named risks include "accuracy, privacy, bias".
- Rule 2210(d)(1)(F): communications "may not predict or project performance". The exceptions include investment analysis tools that meet Rule 2214.
- Rule 2214 requires a prominent legend: "The projections or other information generated by [tool name] regarding the likelihood of various investment outcomes are hypothetical in nature, do not reflect actual investment results and are not guarantees of future results."
- Rule 2111.03: asset allocation models are educational, not recommendations, if based on generally accepted theory with full disclosure of assumptions, "as long as they do not include (standing alone or in combination with other communications) a recommendation of a particular security or securities". This is the US mirror of CIRO's 2026 line.
- FINRA 2026 Annual Regulatory Oversight Report (Dec 2025) adds a section on AI agents. **Not opened** (403); known only from law-firm summaries. Low confidence.

### 4.5 Status of rules and enforcement around AI

- **Predictive data analytics rule: withdrawn.** The SEC withdrew the 2023 proposal (with 13 others): "The Commission does not intend to issue final rules with respect to these proposals." ("Dated: June 12, 2025.") There is no AI-specific advisor rule. Existing fiduciary, antifraud and marketing rules apply.
- **AI washing is enforced.** In March 2024 the SEC settled with Delphia and Global Predictions: "Investment advisers should not mislead the public by saying they are using an AI model when they are not." Global Predictions "falsely claimed to be the “first regulated AI financial advisor”" and also "included an impermissible liability hedge clause in its advisory contract".
- **FY2026 exam priorities (SEC Division of Examinations):** for automated tools, examiners check whether "(3) algorithms lead to advice or recommendations consistent with investors’ investment profiles or stated strategies". They also "will review for accuracy registrant representations regarding their AI capabilities or AI".

---

## 5. The platform rule: Anthropic Usage Policy (anthropic.com/legal/aup, opened 2026-09-28)

This matters because the Robo-Kit chat runs on Claude, including on the viewer's own Claude plan.
- High-risk use cases include "Finance: Use cases related to financial decisions, including investment advice, loan approvals, and determining financial eligibility or creditworthiness".
- For these, when Claude is used to give advice or recommendations to consumers, "a qualified professional in that field must review the content or decision prior to dissemination or finalization". Also, "you must disclose to them that you are using AI to help produce your advice, decisions, or recommendations. This disclosure must be provided at a minimum at the beginning of each session."
- All consumer-facing chatbots, high-risk or not, "must disclose to users that they are interacting with AI rather than a human. This disclosure must be provided at a minimum at the beginning of each chat session."
- Products serving minors carry extra guidelines. MCP servers listed in Anthropic's Connector Directory must follow its Directory Policy.

**Reading:** an education-only chat still needs the start-of-session AI disclosure. A chat that gives personalised investment advice needs a qualified human reviewer before output reaches the user. That is incompatible with a fully automated, unregistered "AI robo-advisor", and it matches the Canadian hybrid model in 3.1. Whether the policy binds Robo-Kit as page author when the viewer pays for the tokens is not settled by the text. Comply anyway.

---

## 6. What "educational tool" framing does and does not protect

**It helps when the substance is impersonal:**
- Canada s.8.25 and 31-103CP: general discussion that "does not claim to be tailored to the needs and circumstances of any recipient".
- US *Lowe*: impersonal, bona fide, regularly available content is outside the Advisors Act. *Seeking Alpha* (2024): user-driven filters over generally available content stay impersonal.
- Asset-class-only models: CIRO OEO guidance (2026) and FINRA Rule 2111.03.
- Registrants' interactive tools: the Marketing Rule carve-out when the four disclosures are given (4.3).

**It does not help when:**
- The output is in substance tailored. CIRO: a firm cannot avoid the rule "by simply stating that a sample portfolio is not tailored to a specific client."
- The product acts like a registrant: collects KYC-style data, says "your portfolio", solicits, or earns any economic benefit (31-103CP business trigger; IA-1092 compensation).
- It trades or links to execution (Weiss Research).
- Statements are misleading, including overstated AI claims (CSA 11-348; SEC 2024-36). Antifraud and misrepresentation rules apply to everyone, registered or not.
- It tries to waive liability. The SEC cited an "impermissible liability hedge clause" (applies to registered advisors; for an unregistered tool, the enforceability of limitation-of-liability terms is a question for counsel).

**Disclaimer language in the market (for tone, not as a safe harbour).** Portfolio Visualizer (opened 2026-09-28) says "All outputs (including backtests and performance results) are hypothetical and not indicative of future outcomes." and "The Platform is not a broker-dealer, investment adviser, or financial institution and is not registered with any regulator." It also discloses that it may receive referral or advertising compensation. Robo-Kit's current footer (`web/index.html`) says "Educational prototype ... Not investment advice" and warns that realised risk hit three times the target in a crash year. Keep that honesty and add the items in R2.

---

## 7. Launch-path recommendation

### Path A: ship now as an impersonal, free learning simulator ("Robo-Kit Lab")

Conditions, all of them needed together:
1. **No economic benefit of any kind.** No fees, ads, affiliate or referral links, issuer sponsorship, or sale of data. (IA-1092 "any economic benefit"; 31-103CP business trigger; NI 81-102 "person ... providing services".) A grant or course credit is probably fine, but a lawyer should confirm.
2. **No account linking, order routing, custody or real-money rebalancing** (Weiss Research; the CSA 31-342 model assumes a registered firm does these).
3. **Default output at asset-class level.** For example, "a Medium-risk illustration is about X% equity / Y% bonds / Z% cash", shown for every risk level side by side, the way CIRO allows sample portfolios.
4. **The user fills asset classes with ETFs themselves**, using neutral, user-controlled filters (cost, exposure, size, liquidity) over the *whole* universe of the chosen market (CAD or US), sorted by a user-chosen key and never by "best for you". The optimizer then weights *the user's own shortlist*, and the result is labelled "what the model does with the inputs you chose".
5. **Risk level is chosen by the user.** An optional self-check quiz teaches tolerance versus capacity and the lower-of rule, but it is not stored and does not auto-assign a portfolio. It shows what each level has meant in past drawdowns.
6. **The chat explains and routes; it never recommends.** Every number comes from a deterministic page function. The chat discloses that it is AI at the start of each session (Anthropic AUP). It declines "what should I buy/sell" and points to a registered advisor instead.
7. **All the disclosures in R2 and the backtest rules in R3.**
8. **A written legal opinion before public launch**, covering Canada (s.8.25; Ontario Securities Act s.34; Quebec, AMF and French-language requirements) and the US (federal definition, publisher's exclusion, state advisor definitions).

### Path B: the full personal robo-advisor (registered)

Telling a specific person which ETFs to hold, charging for it, or managing their money needs one of:
- **Canada:** register as a portfolio manager or restricted portfolio manager under NI 31-103, following the CSA 31-342 hybrid model (an AR reviews KYC and suitability; CSA reviews the questionnaire, investor profiles and model portfolios before launch; accounts sit at a CIRO dealer). Or **license Robo-Kit as a tool to an existing registered online advisor**, who keeps KYC and suitability (11-348: suitability "cannot" be outsourced). An **OEO-dealer partnership** is possible only in the asset-class-sample-portfolio form (no named ETFs).
- **US:** register as an SEC RIA under the internet adviser exemption (all advice through the operational interactive website), or with the states. That brings Form ADV, a compliance program (Rule 206(4)-7) and the Marketing Rule. Or **license the engine to an RIA or broker-dealer**, in which case FINRA 2210/2214/2111 apply to the partner's use.
- **Either country:** Anthropic's human-in-the-loop requirement means a qualified professional reviews personalised output. The Canadian hybrid model already provides this.

The engine, disclosures and records built for Path A are reusable in Path B. Build them to the Path B standard now.

---

## 8. Product requirements this implies

Each requirement names its source so it can be checked. (P0 = needed for Path A; P1 = needed before Path B.)

**R1 Output design (P0)**
- R1.1 The default view shows asset-class mixes for all risk levels. Named-ETF weights appear only for a shortlist the user built. (CIRO OEO 2026; FINRA 2111.03)
- R1.2 No copy that says "recommended for you", "your portfolio", "you should", "best ETF", or ranks ETFs by fit to the person. (CIRO; 31-103CP s.8.25)
- R1.3 Filters are user-controlled, use objective criteria, draw on the full universe, and do not favour any issuer. The screen explains how results were produced. (CIRO OEO; Marketing Rule (e)(8)(ii)(A)(3))
- R1.4 No links to or embedding of order entry, and no auto-rebalancing of real accounts. (Weiss)

**R2 Disclosures (P0), shown in context and not only on a disclaimers page**
- R2.1 At the start of each chat session: "You are chatting with an AI (Claude). It explains how the tool works; it does not give personal investment advice." (Anthropic AUP)
- R2.2 Persistent, short: not registered as an advisor or dealer in Canada or the US; educational; you make your own decisions. Wording to be approved by counsel.
- R2.3 Methodology card: criteria, the equilibrium and Black-Litterman method, key assumptions (normal-ish returns, history-based covariance), limitations (MPT assumptions, the 2016-2026 sample, currency), in plain language. (IM 2017-02; Marketing Rule tool condition 1)
- R2.4 State that "the results may vary with each use and over time". (Marketing Rule tool condition 2; FINRA 2214)
- R2.5 The universe used, how ETFs enter it, any exclusions, and "other investments not considered may have characteristics similar or superior to those being analyzed". (Marketing Rule tool condition 3)
- R2.6 Proposed legend, adapted from the FINRA 2214 wording: "The results are hypothetical in nature, do not reflect actual investment results and are not guarantees of future results." (Marketing Rule tool condition 4; FINRA 2214)
- R2.7 Conflicts: state that the team holds no financial interest in any ETF shown and receives no payment from issuers. If that ever changes, disclose it at the point of display. (NI 31-103 s.8.25(3))
- R2.8 Data provenance: source and as-of date for every figure. Signals (news, sentiment, geopolitics) are labelled "scenario input", never "forecast".
- R2.9 Real-time placement: disclosures sit next to the number they qualify (tooltips and pop-ups). CIRO accepted comments that one-time or buried "general disclaimers" disclosure is "not necessarily effective". (IM 2017-02; CIRO 26-0059)

**R3 How to show backtests and expected figures (P0)**
- R3.1 Label every chart and table "Hypothetical backtest", clearly and prominently. (31-325; Marketing Rule)
- R3.2 Show results net of estimated trading costs and fund fees, and state the cost assumptions. (31-325 "do not always deduct trading and other costs")
- R3.3 Use the full available period by default, with fixed sub-periods (for example 2020 and 2022) always visible. The user cannot cherry-pick the start date without the full-period figure staying on screen. (Marketing Rule (a)(6))
- R3.4 Comparisons use the same periods for every subject, and the benchmark existed during the period. (NI 81-102 s.15.3(1))
- R3.5 Never splice backtests with any real track record. Show how many configurations were tried. (31-325; METHOD.md robustness grid)
- R3.6 Expected return and volatility are shown as model assumptions with ranges (the existing 5-95% bands), not as projections. There is no "you will earn X%". (FINRA 2210(d)(1)(F); Marketing Rule "Targeted or projected performance returns" count as hypothetical performance)
- R3.7 Show the official ETF Facts risk rating and the Robo-Kit computed rating (NI 81-102 Appendix F bands), each labelled.

**R4 Risk questionnaire (P0 as an unstored self-check; P1 as KYC)**
- R4.1 Separate question blocks for risk tolerance (behavioural) and risk capacity (horizon, liquidity needs, income stability, share of total wealth). (31-342; 31-368)
- R4.2 The overall level is the lower of the two, and the screen explains why. (31-103CP s.13.2; 31-368)
- R4.3 An inconsistency check blocks completion until resolved (for example, low tolerance with a maximum-growth goal). (31-342; IM 2017-02)
- R4.4 A cash or GIC outcome is allowed: "you may be better suited to cash or guaranteed products". (31-103CP)
- R4.5 Plain-language explanation for every question, with an education link. (31-342; 31-103CP "KYC questions ... should be in plain language")
- R4.6 P1 only: collect all six s.13.2(2)(c) facts, record client confirmation of the profile, prompt an update at least annually, and route flagged cases to a human AR. (NI 31-103; 31-342; 31-368)
- R4.7 Age gate (18+) before any personalised flow. (Anthropic AUP, products serving minors)

**R5 Deterministic suitability-style checks (P0 as warnings; P1 as gates)**
- R5.1 Concentration: largest single-ETF weight, and overlap between ETFs.
- R5.2 Liquidity: average daily value traded and spread, with a warning below a threshold.
- R5.3 Cost: weighted MER and estimated trading cost, and the impact on 10- and 25-year outcomes. (s.13.3(1)(a)(iv))
- R5.4 Product complexity flags for leveraged, inverse, alternative-mutual-fund and single-stock ETFs. In Path A, exclude them from default filters. (31-342 "unleveraged exchange traded funds (ETFs)")
- R5.5 A mismatch warning when the user's shortlist puts the portfolio's volatility above the chosen risk level, with commentary. (IM 2017-02 pop-ups)
- R5.6 Show "a reasonable range of alternatives": the same risk level filled with lowest-cost broad-market funds as a reference. (s.13.3(1)(a)(v))

**R6 Know-your-product data (P0)**
- R6.1 For every ETF: structure, features, risks, MER and ongoing costs, from the prospectus or ETF Facts, with as-of date. (s.13.2.1)
- R6.2 A monitoring job flags significant changes (mandate, fee, merger, termination, leverage) and marks affected results stale. (s.13.2.1(1)(c))
- R6.3 Written, versioned universe-inclusion criteria. (CIRO OEO filtering safeguards)

**R7 AI chat guardrails (P0)**
- R7.1 The system prompt forbids personalised buy, sell or hold instructions, price or return predictions, and claims of AI superiority. It must never describe Robo-Kit as a "regulated" or "AI financial advisor". (SEC 2024-36; CSA 11-348 AI washing)
- R7.2 Numbers come only from tool calls, and the chat cites the tool output and data date. An automated test fails any response containing a number not present in a tool result. (CSA 11-348 "hallucinations"; accuracy of chatbot information)
- R7.3 Escalation script: when a user asks for personal advice, reveals vulnerability or distress, is a minor, or gives inconsistent information, the chat explains the limits and points to a registered advisor, with a link to CSA/NRD registration search in Canada or the SEC/FINRA advisor search in the US.
- R7.4 Model tier choice (the viewer's own plan) does not change guardrails or tools. Log which model answered.

**R8 Records and reproducibility (P0 lightweight; P1 at regulatory standard)**
- R8.1 Every result is reproducible from engine version, data snapshot hash, parameters and disclosure version shown. Store these per result, with no personal data in Path A.
- R8.2 P1: KYC, suitability rationale, client confirmations and communications kept 7 years. (NI 31-103 s.11.6; 31-103CP "document the basis upon which they make a suitability determination")
- R8.3 A code-change log. Changes that materially move weights are announced on the page. (IM 2017-02)

**R9 Model governance (P0)**
- R9.1 Pre-release tests: the existing Python-JS test vectors, plus backtest regression, before any engine change ships. (IM 2017-02 "development, testing, and backtesting of the algorithmic code")
- R9.2 Third-party oversight file: data vendors, Anthropic and the hosting platform, with what each does and the failure mode. (IM 2017-02; CSA 11-348 "full supply chain")
- R9.3 An explainability panel for each weight: the prior, the views, and the constraint that bound it. (CSA 11-348 explainability)

**R10 Monetisation and partnership gate (P0 policy)**
- R10.1 Any revenue or benefit (subscription, ads, affiliate, issuer sponsorship, data licensing, lead generation) requires legal sign-off before launch. It can switch on the compensation or business trigger and NI 81-102's sales-communication scope.

---

## 9. Where a lawyer must confirm (explicit list)

1. Whether Path A, as specified in section 7, "purports to be tailored" under NI 31-103 s.8.25, and the equivalent under Securities Act (Ontario) s.34 (text not opened) and in Quebec.
2. Whether a user-selected risk level combined with optimised weights on a user-built ETF shortlist is "personalised advice" under the Advisors Act and state definitions, or falls within *Lowe* and *Seeking Alpha*.
3. Whether a university grant, competition prize or course context counts as compensation or business purpose.
4. Enforceability of the terms of use and limitation of liability for an unregistered tool, in both countries.
5. Whether the Anthropic Usage Policy high-risk requirements bind Robo-Kit when chat tokens are billed to the viewer's own Claude plan.
6. Privacy law for any stored questionnaire or chat data (PIPEDA, Quebec Law 25, US state laws). Not researched in this lane.
7. Quebec French-language requirements for a public product. Not researched in this lane.
8. For Path B: category (PM or restricted PM), terms and conditions, and the CSA pre-registration review package; SEC versus state registration and the internet adviser exemption fit.

---

## 10. Sources (all opened on 2026-09-28 unless marked)

| # | Source | URL | Opened |
|---|---|---|---|
| 1 | CSA Staff Notice 31-342 (2015) | https://www.bcsc.bc.ca/-/media/PWS/Resources/Securities_Law/Policies/Policy3/31342-CSA-Staff-Notice-September-24-2015.pdf | yes |
| 2 | NI 31-103 consolidation (2023-09-13) | https://www.osc.ca/sites/default/files/2023-12/ni_20230913_31-103_unofficial-consolidation.pdf | yes |
| 3 | 31-103CP consolidation (2022-01-05) | https://www.osc.ca/sites/default/files/2022-04/cp_20220105_31-103CP_unofficial-consolidation.pdf | yes |
| 4 | Joint CSA/CIRO Staff Notice 31-368 (10 Dec 2025) | https://www.osc.ca/en/securities-law/instruments-rules-policies/3/31-368/joint-csaciro-staff-notice-31-368-client-focused-reforms-review-registrants-know-your-client-know | yes |
| 5 | CIRO Bulletin 26-0059, OEO guidance (12 Mar 2026) | https://www.ciro.ca/newsroom/publications/new-guidance-order-execution-only-account-services-and-activities | yes (curl) |
| 6 | TD Securities on CIRO OEO guidance (10 Apr 2026) | https://www.tdsecurities.com/ca/en/ciro-guidance-for-oeo-sample-portfolios | yes |
| 7 | BLG on CIRO OEO guidance (17 Apr 2026) | https://www.blg.com/en/insights/2026/04/diy-with-oeo-but-first-read-the-updated-ciro-guidance | yes |
| 8 | NI 81-102 consolidation (to 2024-08-31) | https://www.osc.ca/sites/default/files/2024-10/ni_20240831_81-102_unofficial-consolidation-v2.pdf | yes |
| 9 | NI 81-102 Appendix F amendments (2016) | https://www.asc.ca/-/media/ASC-Documents-part-1/Regulatory-Instruments/2018/10/5318291-Annex-B-Amendments-to-NI-81-102.ashx | yes |
| 10 | CSA Staff Notice 31-325 (2011) | https://www.osc.ca/sites/default/files/pdfs/irps/csa_20110705_31-325_marketing-practices.pdf | yes |
| 11 | CSA Staff Notice and Consultation 11-348 (Dec 2024) | https://www.osc.ca/sites/default/files/2024-12/csa_20241205_11-348_artificial-intelligence-systems-capital-markets.pdf | yes |
| 12 | OSC, AI and Retail Investing (2024) | https://www.osc.ca/en/investors/investor-research-and-reports/artificial-intelligence-and-retail-investing | yes |
| 13 | Securities Act (Ontario) s.34 | https://www.ontario.ca/laws/statute/90s05 | **not opened** (script-rendered) |
| 14 | Advisors Act s.202(a)(11) | https://www.law.cornell.edu/uscode/text/15/80b-2 | yes |
| 15 | Lowe v. SEC, 472 U.S. 181 | https://www.law.cornell.edu/supremecourt/text/472/181 | yes |
| 16 | SEC staff outline, Regulation of Investment Advisers (Mar 2013) | https://www.sec.gov/about/offices/oia/oia_investman/rplaze-042012.pdf | yes |
| 17 | GT alert on Seeking Alpha decision (Aug 2024) | https://www.gtlaw.com/en/insights/2024/8/no-need-for-seeking-alpha-to-seek-registration | yes (court opinion not opened) |
| 18 | SEC IM Guidance Update 2017-02 | https://www.sec.gov/investment/im-guidance-2017-02.pdf | yes |
| 19 | SEC Final Rule IA-6578, internet adviser exemption (2024) | https://www.sec.gov/files/rules/final/2024/ia-6578.pdf | yes |
| 20 | Marketing Rule 17 CFR 275.206(4)-1 | https://www.law.cornell.edu/cfr/text/17/275.206(4)-1 | yes |
| 21 | SEC Marketing Compliance FAQ (updated 15 Jan 2026) | https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/marketing-compliance-frequently-asked-questions | yes |
| 22 | FINRA Regulatory Notice 24-09 | https://www.finra.org/rules-guidance/notices/24-09 | via fetch tool only (direct download 403) |
| 23 | FINRA Rules 2210, 2214, 2111 | https://www.finra.org/rules-guidance/rulebooks/finra-rules/2210 (and /2214, /2111) | via fetch tool only |
| 24 | SEC withdrawal of 14 proposals (12 Jun 2025) | https://www.sec.gov/files/rules/final/2025/33-11377.pdf | yes |
| 25 | SEC press release 2024-36 (AI washing) | https://www.sec.gov/newsroom/press-releases/2024-36 | yes |
| 26 | SEC FY2026 examination priorities | https://www.sec.gov/files/2026-exam-priorities.pdf | yes |
| 27 | Anthropic Usage Policy | https://www.anthropic.com/legal/aup | yes |
| 28 | Portfolio Visualizer home and terms | https://www.portfoliovisualizer.com/ ; https://www.portfoliovisualizer.com/terms-of-service | yes |
| 29 | FINRA 2026 Annual Regulatory Oversight Report | https://www.finra.org/sites/default/files/2025-12/2026-annual-regulatory-oversight-report.pdf | **not opened** (403) |

## Method

Pages were downloaded with Python requests or curl and converted to text (PyMuPDF for PDFs, BeautifulSoup for HTML). Quotes were then checked as exact substrings after whitespace and curly-quote normalisation: 62 of 62 passed. A second pass pulled every quoted span out of this report and matched it against the downloaded texts. The only spans that did not match are the FINRA quotes in 4.4, wording proposed for Robo-Kit's own UI, and Robo-Kit's own footer. The FINRA quotes came from a summarising fetch tool and are **not** machine-verified. No external model CLIs were used.
