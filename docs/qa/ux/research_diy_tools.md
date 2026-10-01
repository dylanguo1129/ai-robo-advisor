STATUS: COMPLETE

# DIY portfolio analytics and builders: market notes for Robo-Kit

Researched 28 Sep 2026 with WebSearch + WebFetch. Every product claim has a URL and a short quote. Quotes were pulled through a fetch tool that summarises pages, so treat them as near-verbatim and re-check before citing in a deliverable. When a site blocked the fetch, the note says so and the claim is marked as coming from a search-result snippet (SNIPPET) or left out.

Sites that blocked direct fetch (HTTP 403/402/429): portfolioslab.com (all pages), morningstar.com help centre, etf.com, pwlcapital.com, benderbenderbortolotti.com, help.wealthsimple.com, bogleheads.org, early-retirement.org, findmymoat.com (rate-limited).

---

## 1. Portfolio Visualizer (portfoliovisualizer.com)

- Tool breadth: backtesting, Monte Carlo, efficient frontier, optimisation, Black-Litterman, factor regression, tactical models, fund screener, correlations.
  - https://www.portfoliovisualizer.com/ : "Model the probability of different investment outcomes and better understand the impact of risk."
  - same page: "Tactical allocation models based on moving averages, momentum, market valuation, volatility targeting."
- Pricing (https://www.portfoliovisualizer.com/pricing):
  - Free: "supports portfolios with up to 15 assets with limited history"
  - Basic: "$30 / month" (billed annually), "allows 50 portfolio models to be saved"
  - Pro: "$55 / month" (billed annually), "enables 150 portfolio models"
  - All tiers: Excel/CSV/PDF export, custom reports, tax-assumption settings (summary of pricing page).
- Backtest inputs (https://www.portfoliovisualizer.com/backtest-portfolio):
  - Rebalancing: "No rebalancing, Rebalance annually, semi-annually, quarterly, monthly, or rebalance bands"
  - Cashflows: "Contribute fixed amount, Withdraw fixed amount, Withdraw fixed percentage"
  - Compare: "up to three different portfolios" against a benchmark
  - Outputs: max drawdown with recovery time, worst-10 drawdowns, rolling 1/3/5/7/10-year returns, Sharpe/Sortino/Calmar, risk attribution.
  - Taxes: page disclaimer says results do not reflect "actual taxes due on investment returns."
- Reviews:
  - https://riskparitychronicles.substack.com/p/three-portfolio-backtesters-every : "For newcomers, PV can feel cluttered and overwhelming"
  - Bogleheads thread on the 2023 redesign and 10-year free limit (https://www.bogleheads.org/forum/viewtopic.php?t=432090): fetch blocked (402). SNIPPET only: users complained the free tier was "limited to 10Y data unless paying".
- No holdings look-through (regions/sectors/currency) found on the pages read.

## 2. testfol.io (testfolio)

- Backtester guide (https://testfol.io/guides/portfolio-backtester/):
  - "rebalance frequency, optional rebalance offset, annual drag, dividend setting, and optional rebalance bands"
  - "The tool supports recurring cashflow legs and one-time cashflows."
  - Simulated long-history tickers: "Extended-history simulated tickers such as SPYSIM, QQQSIM, TLTSIM, GLDSIM"
  - Leverage: "create custom leveraged ETF-style series like SPYSIM?L=3"
- Help / methodology (https://testfol.io/help/):
  - Sharing: "Share links and saved optimizations store the full setup so you can revisit or share"
  - Local saving: "Saved portfolios are stored in your browser's localStorage. No saved data ever reaches our servers."
  - AI export: "Use Export for AI in Results to preview, copy, or download completed inputs and results as Markdown or JSON."
  - Limits: "There is a limit of 5 portfolios per backtest, and a limit of 10 tickers per portfolio."
  - Tax drag: "The Turnover & Taxes tab estimates one-way turnover, trading-cost drag, realized capital-gains taxes."
  - Honest limits: "This tax model is an estimate only...Wash sales, state/local taxes, foreign withholding...are not modeled."
  - Tool list includes Monte Carlo, Life Cycle Monte Carlo, Lump Sum vs DCA, Safe Withdrawal Rate, Sequence of Returns Risk, Rebalancing Sensitivity, Factor Regression, PCA.
- Pricing (https://testfol.io/pricing):
  - Free "$0", "Best for getting started"
  - Pro "$12.5 /month, billed annually", "Best for most serious investors"
  - Pro+ "$25 /month, billed annually"
  - Max "$80 /month, billed annually", "Best for AI-assisted research"; includes "Use the Testfolio plugin in ChatGPT" and "Connect with Codex and Claude Code"
- Review (riskparitychronicles substack, older): praised the "simulated funds" and individual tickers; cons that tutorials are "pitched a little high" for beginners. Its claim that testfolio is "Currently free" is out of date; the pricing page now shows paid tiers.

## 3. PortfoliosLab (portfolioslab.com)

- All portfolioslab.com pages returned 403 (subscription page, portfolio-analysis tool page, AI docs page).
- https://sourceforge.net/software/product/PortfoliosLab/ (third-party listing):
  - "allowing users to backtest portfolio returns, drawdowns, and various risk characteristics"
  - "asset correlations, portfolio optimization, risk parity optimization, and Hierarchical Risk Parity (HRP) optimization"
  - Pricing listed as starting at "$7.99 per month" (third-party, not checked on the vendor page)
- SNIPPET only (findmymoat, rate-limited): free tier capped at "15 holdings per portfolio, 10 calculations per month, and 5 years of history"; paid tiers add imports, exports and MCP access. The vendor docs page "Analyze Any Stock or Portfolio with ChatGPT and Claude" exists (https://portfolioslab.com/docs/getting-started/analyze-with-ai) but was blocked (403).

## 4. Morningstar Portfolio X-Ray / Morningstar Investor

- morningstar.com help-centre pages returned 403.
- Sample report (https://im.morningstar.com/im/IMCLP_PortfolioXRay_sample.html): sections are asset allocation, style box, regions, sectors, fees and stock intersection.
- Review (https://www.wallstreetsurvivor.com/is-morningstar-worth-it/):
  - "'Looks through' your mutual funds and ETFs to expose the underlying holdings across your entire investment portfolio"
  - Price: "$249/year for the standard annual plan", "a first-year discount around $199", "a 7-day free trial"
  - UI: "Dated interface that feels clunky compared to modern fintech apps"
  - Tracking: "Performance tracking from linked brokerage accounts isn't always fully automated."
  - "In-page advertising appears even for paying subscribers."
- SNIPPET (morningstar help, blocked): Stock Intersection shows "a table of the top 50 stocks" concentrated in the portfolio; World Regions maps each holding to its region; "Stock sector reveals how you're concentrated across 12 sectors."
- Third-party claim (a developer's blog, https://dev.to/tianninglab/morningstar-killed-free-portfolio-x-ray-i-rebuilt-it-using-gleif-esma-firds-and-15-other-free-5hma): says the free X-Ray was the "only tool that worked with ISINs and showed multi-fund look-through". The blog puts its removal in April 2025. Only this blog supports that date.

## 5. justETF (strategy builder, portfolio, rebalancing, order list)

- Strategy builder (https://www.justetf.com/en/etf-strategy-builder.html): 7 steps (amount, risk profile, risk share, commodity mix, bond share, ETF selection, order list).
  - "Adjust the risk portion of your portfolio to your personal risk capacity and your investment horizon."
  - Risk is picked on a free slider: "0% 100% 50% Risk share". No questionnaire and no lock.
  - "The analysis shows you the historic range of drawdowns and returns of a diversified portfolio with an equivalent risk rate."
- Free vs Premium:
  - https://www.justetf.com/en/free.html : "1 portfolio and 1 watchlist included" plus strategy builder, screener, portfolio analysis and order list.
  - https://www.justetf.com/en/premium.html : "5 portfolios and unlimited watchlists included"; "Portfolio rebalancing with just a click"; EUR 9.90/month on the yearly plan (EUR 118.80/yr), EUR 14.90/month billed quarterly.
- Order list (https://www.justetf.com/en/tutorial/orderlist/how-does-the-order-list-work.html):
  - "For a one-time investment, this number must be an integer. Fractional shares are only available for savings plans."
  - Broker fee models (flat, percent, min/max); cash can't go negative; each line shows ISIN, shares, price, amount and fee.
- Rebalancing (https://www.justetf.com/en/tutorial/rebalancing/how-does-portfolio-rebalancing-work.html):
  - "The justETF System automatically calculates an order list with all necessary buy and sell transactions for the portfolio rebalancing."
  - "You have the option to rebalance only through buying via a deposit in the portfolio. The advantage is that no taxable capital gains will apply"
- Planning mode (https://www.justetf.com/en/tutorial/structuring/professional-portfolio-planning-mode.html): shows live "fees per year", "return in per cent", "volatility" as weights change; a "Pen" button swaps an ETF for similar ones.
- Model-portfolio tutorial page said "No tutorial available" (https://www.justetf.com/en/tutorial/model-portfolios/).

## 6. Curvo (backtest tool + investing app, EU)

- Backtest article (https://curvo.eu/article/understand-your-portfolio-of-etfs-with-backtest):
  - "You can include the impact of brokerage costs in the simulation."
  - "It is possible to simulate and compare different rebalancing strategies."
  - "All data is in euro and one can only analyse funds that are available in Europe."
  - "The tool is available to everyone free of charge."
  - "Backtest uses the data of the underlying index, also taking into account the costs of the fund."
- App profiles (https://curvo.eu/help/en/article/what-investor-profiles-do-the-portfolios-offer-mpsxbe/): "Growth (100% equities), Energetic (70% equities, 30% bonds), Smooth (50% equities, 50% bonds), Calm (30% equities, 70% bonds), Protective (15% equities, 85% bonds)"
- Portfolios page (https://curvo.eu/portfolios): "When you sign up, we ask you a series of questions to get to know you and learn what type of investor you are."; platform fee "0.6% and 1%"; forward returns from a CAPM model plus Monte Carlo scenarios.
- Changing risk (https://curvo.eu/help/en/article/how-can-i-change-my-portfolio-1j4icpb/):
  - "You'll then complete the questionnaire again."
  - "Based on your updated answers, we'll match you with the portfolio that fits you best."
  - "There's no cost to switch, and you're never locked in."

## 7. Passiv (Canada; rebalancing and trade lists)

- Home (https://passiv.com/): "Rebalance in one click"; "One-click trades make rebalancing across multiple accounts easy."
- Pricing (https://passiv.com/pricing/): Community (free) and Elite ($99/year). The page lists the same features for both, including "One-click trades", "Multi-account portfolios", "Advanced currency handling", "Keep stock picks separate".
  - CONFLICT: https://milliondollarjourney.com/passiv-review.htm says "the ability to make one-click trades – is exclusive to Elite users". The review may be older than the pricing page.
- Rebalancing help (https://passiv.com/help/tutorials/how-to-rebalance-your-portfolio/):
  - "By default, Passiv is set to only allocate new cash to your underweight targets, not sell overweight assets."
  - "Check the Allow selling to rebalance box. Now, Passiv's calculations will factor in selling as an option."
- Onboarding (https://landing.passiv.com/blog/getting-started-passiv/): 4 steps (sign up, link broker, set target, multi-account). Targets can be set "by importing your current Questrade holdings as a target, or by building a portfolio from scratch."
- Limits (milliondollarjourney):
  - "If you hold individual bonds, options, or GICs in your portfolio, you won't be able to include them in your model allocation"
  - "you'll still need to do some upfront homework" (Passiv is not a robo-adviser)

## 8. Canadian Couch Potato model portfolios

- https://www.canadiancouchpotato.com/model-portfolios/ : five mixes (100/0, 80/20, 60/40, 40/60, 20/80) using Vanguard, iShares or BMO asset-allocation ETFs.
  - "With this one-fund solution, you'll never need to rebalance your portfolio."
  - "Finding the appropriate combination of stocks and bonds is the most important decision you'll need to make."
  - "You can combine an all-equity ETF with a bond ETF. In this case, you will occasionally need to rebalance your portfolio."
  - Fees shown as annual MER of about 0.17% to 0.20%. The page shows no historical returns.

## 9. PWL Capital / Canadian Portfolio Manager (Justin Bender) model portfolios

- pwlcapital.com and benderbenderbortolotti.com returned 403.
- https://www.canadianportfoliomanagerblog.com/model-etf-portfolios/ :
  - One-ticket ETFs where "ETF providers will even take care of the rebalancing for you"
  - Range "very conservative (80% bonds, 20% stocks) to very aggressive (100% stocks)"
  - Each model comes with "20 years of back-tested returns"; the page adds "Past returns don't predict future outcomes"
- SNIPPET only: Bender rebalancing spreadsheets, and US-listed ETFs in RRSPs to cut foreign withholding tax (search results, pages blocked). The Passmore/Felix factor-tilt model portfolios are described only by third parties (optimizedportfolio.com, portfolioeinstein.com). Not verified.

## 10. ETF Database (etfdb.com) and ETF.com screeners

- https://etfdb.com/screener/ : filters for asset class, market cap, style, region, duration ("All-Term, Intermediate-Term, Long-Term..."), leverage, tax form, ESG and dividend frequency. Some filters show "Sign Up for Free to Unlock". CSV export needs "ETF Database Pro".
- ETF.com screener: blocked (403). No claims.
- Related: ETF Research Center overlap (https://www.etfrc.com/funds/overlap.php): "See which holdings any two equity ETFs have in common, along with top differences in exposure." and "For overlap across multiple ETFs use Portfolio Builder."

## 11. Portfolio Charts (portfoliocharts.com)

- https://portfoliocharts.com/ :
  - "With 56 years of market data spanning 71 unique assets, the charts are also fully customizable"
  - "12 home countries in local currency & inflation"
  - "The Heat Map chart displays compound annual growth rates not over a single timeframe, but over all timeframes."
  - "No paywalls, no ads, no strings attached."
- Portfolio Matrix (https://portfoliocharts.com/charts/portfolio-matrix/): "ranks every recommended asset allocation across a variety of valuable metrics and allows you to sort the list by any data point"
- Works with asset classes, not tickers (substack review: "PC focuses on asset classes, not tickers").

## 12. Stock Rover

- Plans (https://www.stockrover.com/plans/): Premium $29/mo, Premium Plus $49/mo, Ultimate $79/mo, Ultimate Pro $149/mo (annual billing); monthly billing is higher (Premium $34/mo).
- Portfolio features (https://www.stockrover.com/portfolio-management/):
  - Rebalancing: "comparing your target versus actual allocations, calculating the exact trades needed to restore your balance"
  - Import: "Import a file from your brokerage, or create a CSV file with three columns: Symbol, Buy Price and Quantity."
  - "Use Monte Carlo simulations to stress-test your portfolio against thousands of market scenarios."
  - Emailed reports "daily, weekly, or monthly"
- Future Simulations (https://www.stockrover.com/help/future-simulations/future-simulations-overview/): users "define how bullish or bearish the market is likely to be and plug those probabilities directly into the model"; models "the statistical odds of maintaining your lifestyle in retirement".
- Review (https://www.stockbrokers.com/review/tools/stockrover): "The platform has a learning curve due to all the information, research, and tools"; research and screening "focused on U.S. and Canadian securities".

## Reference (outside scope, but relevant to the level-lock issue): Wealthsimple managed

- help.wealthsimple.com returned 403. SNIPPET: "To move your account into 100% equities, you'll need to connect with one of our Portfolio Managers so that we can make sure this investment is suitable for you." The reassessment is described as three questions (goal, timeline, comfort with risk).
- Wealthsimple is a registered portfolio manager with a suitability duty. Robo-Kit's Path A is an impersonal simulator with no such duty.

---

## Robo-Kit code check (read-only)

- web/app.js:505 renders the five level buttons after the self-check with `disabled` on every level not in `profile.can_choose`. web/app.js:763 does the same in the tray.
- web/app.js:396 and web/app.js:518 clamp any requested level down to max(can_choose). One comment reads "never above the self-check's capacity cap".
- So when capacity is 4, level 5 can't be reached from the ladder card, the tray, or (by clamping) the chat. It is a design choice, not a crash. But it is stricter than every DIY tool reviewed. Only a registered manager with a suitability duty (Wealthsimple) blocks higher risk, and even then through a human review, not a dead button.

---

## Cross-cutting patterns

1. DIY tools do not lock risk. justETF uses a free 0-100% slider. PV, testfolio and Portfolio Charts let you type any mix. CCP and CPM list all five mixes side by side. Curvo re-matches you through its questionnaire. Only Wealthsimple (a regulated manager) adds a gate, and that gate is a human review, not a greyed-out button.
2. Wizards beat chat for setup. justETF's 7-step builder and Passiv's 4-step onboarding each show one decision at a time, with progress, and end in a concrete order list.
3. Order lists with whole shares are standard. justETF forces integer shares for lump sums and includes broker fees and cash. Passiv defaults to buy-only. Stock Rover and justETF both compute "exact trades".
4. Look-through is scarce and paywalled. Morningstar X-Ray ($249/yr) is the reference. ETFRC does pairwise overlap. The free options are gone or partial. Nothing seen gives CAD-market look-through for regions, sectors and currencies across a mix of Canadian wrapper ETFs.
5. Sharing, export and AI hand-off are the new front. testfolio has share links, localStorage saves and "Export for AI" (Markdown/JSON), and puts MCP, ChatGPT plugin and Claude Code in its $80/mo Max tier. PortfoliosLab has an AI docs page and MCP in paid tiers.
6. Fees and taxes in dollars are uncommon. Curvo models broker costs. testfolio estimates turnover and capital-gains tax, and says clearly what it does not model. justETF shows fees per year. Hardly any tool models Canadian foreign withholding tax or account type (TFSA/RRSP/taxable), even though CPM discusses it.
7. The one-ticket benchmark is how Canadian DIY investors think (CCP, CPM). Any custom mix gets judged against VEQT/XEQT/VGRO. Few tools do that comparison automatically.
8. Paywalls and free-tier limits drive churn. PV's limited free history, PortfoliosLab's 15 holdings and 10 calcs/month, and testfolio's 5 portfolios x 10 tickers are the main complaints.
9. Complexity is the most common weakness in reviews: PV "cluttered and overwhelming", Stock Rover "learning curve", Morningstar "dated" and "clunky".
