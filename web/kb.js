/* The words the guided page uses besides the engine's own (questions, options, glossary and disclosures come from
 * data/core.json, written by robokit/profile.py and robokit/glossary.py). Everything here is fixed text the team can
 * review: why each question is asked, a longer "learn more", short acknowledgements, answers to common questions, and a
 * few extra terms. No numbers live here except illustrations marked as such; the page fills real figures from the engine.
 * Plain ES module, no DOM, so web/test_converse.mjs can check it under Node. Canadian English. */

// The conversation script's opening line and its advice-boundary redirect, word for word where the script fixes them.
export const OPENING = "Hi, I'm Penguru. I'll ask a few questions about your goals to suggest a mix of ETFs for your portfolio. I'll explain the reasoning behind each choice in plain language as we go, and you can ask questions whenever you like. Let's start:";
export const ADVICE_REDIRECT = "I can't tell you whether to buy at any specific time, as I am not a licensed advisor. What I can do is provide information about the ETFs and show how each one fits the portfolio we have built together.";
export const PAST_PERFORMANCE = 'Past performance is not reflective of future performance.';
// E4: questions outside investing get the tool's scope; comparisons with other products get the ETF-only rule.
export const SCOPE = 'That is outside what Penguru covers: it helps you learn about investing with Canadian-listed ETFs and build a practice mix. Ask me about ETFs, investing words, or any question on this page.';
export const ETF_ONLY = (other) => `Penguru only covers ETFs at this time, so it does not compare them with ${other}. I can explain what ${other} ${/s$/.test(other) ? 'are' : 'is'}, or anything about the ETFs here.`;
export const OWN_DECISION = 'I understand that Penguru is an educational tool, not a registered advisor, and that any investment decision I make is my own.';
export const SUPPORT = {
  money: 'That sounds stressful. Before investing, it can help to talk it through with someone independent: the Financial Consumer Agency of Canada (canada.ca/en/financial-consumer-agency.html) and non-profit credit counselling (creditcounsellingcanada.ca) are free places to start.',
  crisis: 'I am sorry you are going through this. If you are thinking about harming yourself, please call or text 988 (Canada and US) to reach someone now. The investing questions can wait.',
};

// Explanation depth, from the calibration question (the script's step 00). It never changes the risk disclosure.
export const DEPTH = { novice: 'novice', some: 'some', expert: 'expert' };
export const CALIBRATION = {
  id: 'EXP', text: 'Before we start: how much do you already know about ETFs? This only changes how much I explain, never the math.',
  options: [
    { value: 'novice', text: 'New to this: explain as we go', ex: 'Step by step: each question and each new word explained.' },
    { value: 'some', text: 'I know the basics', ex: 'Short explanations, with more whenever you ask.' },
    { value: 'expert', text: 'I know this well: skip the basics', ex: 'Brief questions, more numbers, and shortcuts for tickers and filters.' },
  ],
  skip: 'Skip: just start',
};
// F1: how the depth is acknowledged (it is never named as a label for the person)
export const DEPTH_ACK = {
  set: {
    novice: "We'll go step by step. I'll explain each question and define new words the first time they come up, and you can ask anything at any point.",
    some: 'I\'ll explain a little as we go. Tap "Why we ask" or "Learn more" on any question for detail, or ask in your own words.',
    expert: 'I\'ll keep the questions short, show the rule behind each one, and put more numbers on your results. You can type several answers at once (for example "20+ years, $50k, no debt, salaried"), name tickers, or add filters at any time. Say "explain more" whenever you want more detail.',
  },
  change: {
    novice: "Sure. From here I'll explain each step in plain words and define new terms as they come up.",
    some: 'Sure. Shorter explanations from here; tap "Learn more" for detail.',
    expert: 'Sure. Shorter questions from here, and more numbers on the results.',
  },
  same: { novice: "Understood; I'll keep explaining as we go.", some: "Understood; I'll keep explaining a little as we go.", expert: "Understood; I'll keep skipping the basics." },
  skipped: 'No problem. I\'ll adjust as we go; say "explain more" or "keep it brief" at any time.',
};
export const DEPTH_ROW = { label: 'Explanations', novice: 'Step by step', some: 'Short, more on request', expert: 'Brief, with more numbers' };
export const DOCK = {
  placeholder: { novice: 'Type an answer, or ask what anything means', some: 'Type an answer or ask a question', expert: 'Type answers, tickers or filters (e.g. 25 years, $50k, high, XEQT)' },
  note: 'Tap an answer or type it in your own words. You can ask a question at any point.',
};

// Why each step is asked: one or two plain sentences, shown under the question for beginners and on "Why we ask".
export const WHY = {
  EXP: 'This only sets how much I explain along the way. It never changes the suggestion or the math.',
  A1: 'Your goal shapes the examples I use. It does not change the math by itself.',
  B1: 'Time is the biggest factor in how many ups and downs your money can absorb: money needed soon has less time to recover from a drop.',
  B2: 'Taking money out a bit at a time leaves the rest invested for longer, so it can carry a little more risk than money you need all at once.',
  BASICS: 'These are the "basics before investing" checks. Without an emergency fund, or with expensive debt, a market drop could force you to sell at a bad time, so Penguru keeps the suggestion on the careful side until they are in place.',
  MONEY: 'Every number from here on is shown in your own dollars. A monthly amount is used only in the projections; it does not change the suggestion.',
  B5: 'A steady income means you are less likely to need this money in a bad year, so your situation can absorb a bit more risk.',
  C0: 'How you see yourself is a good start. Next I will check it against how you might react to a real drop, because the two often differ.',
  C2: 'People often feel braver about risk than they act in a real downturn. Your likely reaction tells me more than a label.',
  C1: 'Each card is a different mix, shown in your dollars after one year. Wider ranges come with bigger ups and downs. Pick the range you could live with.',
  B4: 'If this money is most of what you have, a loss would hurt more, so the suggestion is a little more careful.',
  C3: 'The same idea over ten years. In these simulations riskier mixes end higher on average, but not every time, and the spread between a poor and a good outcome is wider.',
  C4: 'This tells me which mistake you would regret more: losing money, or missing out on growth.',
  PREFS: 'Optional. Your preferences narrow which ETFs go on your shortlist. They do not change your risk level.',
  TICKER: 'Optional. If you already have a fund in mind, I will add it to your shortlist and tell you how it fits.',
};

// "Learn more" for each step: a little longer, with the idea behind it. Shown on request (or by default for beginners).
export const LEARN = {
  EXP: 'There are no wrong answers. "New to this" means I explain each question and define each new word the first time it comes up. "I know this well" means shorter questions, the scoring rule behind each one, and more numbers on your results. Everyone gets the same questions and the same math. You can also skip this: I adjust as we go, and you can say "explain more" or "keep it brief" at any time.',
  A1: 'Goals usually differ in two ways: when you will need the money, and whether you will take it out all at once or bit by bit. The next question asks when; how it comes out follows from your goal (all at once for a home, bit by bit for retirement or tuition), and you can change that. If you are just learning, that is a great reason to be here: we will build a practice mix you can explore, and nothing here buys anything.',
  B1: 'Think of the year you expect to start using this money, not the year you stop. For retirement savings that is roughly the year you retire. If you are not sure, a rough guess is fine; you can change it later.',
  B2: '"All at once" fits a home down payment or a big purchase. "Over several years" fits retirement income or tuition paid term by term. If you have no plan yet, "Not sure yet" is a fine answer.',
  BASICS: 'An emergency fund is money you can reach quickly, usually 3 to 6 months of regular expenses, kept somewhere safe like a savings account. High-interest debt means balances like credit cards that charge around 20% a year: paying those off is a guaranteed "return" that investing rarely beats.',
  MONEY: 'Use any amount: this is a model, and nothing is invested. If you plan to add money regularly, the monthly amount shows how that could build up over time.',
  B5: 'Steady income, like a salary or a pension, means a bad year in the markets is less likely to force you to sell. Freelance, commission or seasonal work counts as "varies a lot."',
  C0: 'Low means you would rather keep things steady even if growth is slow. Medium means some ups and downs are fine. High means you can live with big swings for more growth.',
  C2: 'In 2008 many stock markets fell by about half over many months and took years to recover; in early 2020 they fell about a third in a few weeks and recovered within months. People who sold near the bottom locked in the loss. There is no right answer here; an honest one helps most. ' + 'Past performance is not reflective of future performance.',
  C1: 'Read each card as "a bad-ish year" on the left and "a good year" on the right; in 8 of 10 simulated years the result lands between them. The grey tick is what you put in. The cards further right have higher upsides but also lower lows. Note the differences across the low and high points: that gap is the risk you take on.',
  B4: 'Add up your savings and investments (bank accounts, TFSA, RRSP and so on) and compare them with the amount you are investing here. If you are not sure, you can skip this question.',
  C3: 'Each card shows where 8 of 10 simulated ten-year outcomes land for that mix. In these simulations riskier mixes end higher on average, but not every time, and the range between a poor and a good outcome is much wider. Pick the range you would be comfortable ending up anywhere inside.',
  C4: 'Some people are bothered most by seeing a loss; others by watching a rally pass them by. Both are normal.',
  PREFS: 'If you care about a theme (such as technology or dividends), I look for a low-cost, eligible ETF for it and add it to your shortlist as your own pick, up to the limit your level allows. If you want to avoid something, I leave that fund out. Lowest-cost swaps each default fund for the cheapest fund of the same kind. Hedging removes most of the effect of the US dollar on your US stocks.',
  TICKER: 'Type a ticker such as VFV or XEQT. Penguru only adds funds that pass its screen (enough history, enough assets, no leverage), and tells you why when one does not.',
  RECON: 'Your self-rating and your answer about a sharp drop pointed different ways. That is common: people often feel braver, or more nervous, than they act. Pick the one that feels closer to how you would really behave; Penguru uses it and sets the other aside. You can change either answer later.',
  FT: 'Three optional questions (how much of your savings this is, the ten-year range you would accept, and which mistake you would regret more) refine the suggestion. Skipping them is fine: the suggestion then comes from the answers you have already given.',
  ADJUST: 'When you raise one fund, the others shrink in proportion so the total stays 100%; no fund except the cash fund can go above 50%. Penguru then measures the mix you set: "behaves like level N" compares its ups and downs with the five levels. It does not re-optimize your weights, and the result is not calculated for you from your answers.',
};

// Short acknowledgements after notable answers. {depth} decides whether they show: 'all' for every depth.
export const ACK = {
  A1: {
    learning: 'Great place to start. We will build a practice mix you can explore and change; nothing here buys anything.',
    retirement: 'Retirement it is. The next questions are about when you would start using the money.',
    home: 'Saving for a home. Timing matters a lot here, so the next question is about when you need it.',
    education: 'Education savings. Tuition is usually paid over a few years, so I will plan on that; you can change it.',
    income: 'Income you can spend now. That usually means taking money out regularly over time.',
    wealth: 'Building wealth with no fixed date. That usually means a long horizon.',
  },
  B1: { lt2: 'Money needed within two years has little time to recover from a drop, so the suggestion will be careful.', years: 'So about {years} years from now.' },
  B5: { varies: 'Uneven income means a little more care, since you might need this money in a lean year.', none: 'Without a regular income for now, the suggestion leans a little more careful.' },
  C2: { dont_know: "That's an honest answer; it's hard to know until it happens." },
  MONEY: { novice: '{amount} to start{monthly}. Every number from here on is in those dollars.' },
  A2: { no: 'Thanks for being straightforward. An emergency fund usually comes first, so Penguru keeps the suggestion on the careful side for now. Your result will show exactly what that means.', partly: 'A partial emergency fund is a good start; the suggestion will be a step more careful until it is complete.' },
  A3: { lot: 'Paying down high-interest debt often beats investing, so Penguru keeps the suggestion on the careful side for now. Your result will show exactly what that means.' },
};

// Suggested questions for beginners under each step (the guided path rather than a blank box).
export const SUGGEST = {
  EXP: ['What is an ETF?', 'Is this real investing?'],
  A1: ["What if I don't have a goal yet?", 'What is an ETF?'],
  B1: ["What if I'm not sure?", 'Why does time matter?'],
  B2: ['What does "all at once" mean?', "What if I'm not sure?"],
  BASICS: ['What is an emergency fund?', 'What counts as high-interest debt?'],
  MONEY: ['How much should I start with?', 'Is any of this invested?'],
  B5: ['What counts as steady income?', 'Why does income matter?'],
  C0: ['What is risk?', 'Why do you ask this?'],
  C2: ['Has the market really dropped like that?', 'What would most people do?'],
  C1: ['What do these numbers mean?', 'Why are some ranges wider?'],
  B4: ["What if I don't know?", 'Why does this matter?'],
  C3: ['What do these numbers mean?', 'What is a 2008-style crisis?'],
  C4: ['Why do you ask this?'],
  PREFS: ['What is a theme?', 'What does hedged mean?'],
  TICKER: ['What is a ticker?', 'Can I add any ETF?'],
  MIX: ['What does volatility mean?', 'Why is there so much in bonds?', 'How do I buy an ETF?'],
};

// Words to define the first time they come up (beyond the engine's glossary in core.json).
export const TERMS = {
  stock: { term: 'Stock (equity)', definition: 'A small share of ownership in a company. Stocks can grow the most over time and also fall the most.', match: /\bstocks?\b|\bequit(?:y|ies)\b/i },
  portfolio: { term: 'Portfolio', definition: 'All your investments taken together, here the mix of ETFs.', match: /\bportfolios?\b/i },
  emergency_fund: { term: 'Emergency fund', definition: 'Money set aside for surprises, usually 3 to 6 months of expenses, kept somewhere safe and easy to reach.', match: /\bemergency (?:fund|savings)\b/i },
  horizon: { term: 'Time horizon', definition: 'How long until you need the money. Longer horizons can ride out more ups and downs.', match: /\b(?:time )?horizon\b/i },
  risk_level: { term: 'Risk level', definition: "Penguru's scale from 1 (Conservative) to 5 (Aggressive growth). Each level aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80% and level 5 about all of it.", match: /\brisk level\b/i },
  ticker: { term: 'Ticker', definition: 'The short code a fund trades under, such as VFV or XIC.', match: /\btickers?\b/i },
  shortlist: { term: 'Shortlist', definition: 'The funds the optimizer may use for your mix.', match: /\bshortlist\b/i },
  optimizer: { term: 'Optimizer', definition: "The calculation that sets each fund's weight so the mix matches your risk level.", match: /\boptimi[sz]er\b/i },
  active: { term: 'Active fund', definition: 'A fund whose managers choose the investments by judgement, instead of copying an index. Fees are usually higher.', match: /\bactive (?:funds?|etfs?|management|strategy)\b|\bactive or factor\b/i },
  factor: { term: 'Factor (smart-beta) fund', definition: 'An index fund that follows a rule, such as cheaper companies (value) or recent winners (momentum), instead of company size alone.', match: /\bfactor (?:funds?|etfs?|investing)\b|\bfactor \(smart[- ]beta\)|\bsmart[- ]beta\b/i },
  range: { term: 'Range (8 in 10)', definition: 'The span where 8 of 10 simulated outcomes land: the low end is a bad-ish result, the high end a good one.', match: /\b8 (?:years )?(?:out )?(?:of|in) 10\b/i },
  gic: { term: 'GIC (guaranteed investment certificate)', definition: 'A deposit at a Canadian bank or credit union that pays a set interest rate for a set term; the amount you put in is guaranteed if you hold it to the end.', match: /\bGICs?\b|\bguaranteed investment certificates?\b/i },
  mutual_fund: { term: 'Mutual fund', definition: 'A pooled fund bought and sold through the fund company once a day at its end-of-day price, rather than traded on an exchange like an ETF.', match: /\bmutual funds?\b/i },
  index: { term: 'Index', definition: 'A list of investments that stands for a market, such as the S&P/TSX Composite for Canadian stocks. An index fund holds what the index holds.', match: /(?<!(?:risk|price|uncertainty|volatility|policy) )\b(?:market )?index(?:es)?\b(?! funds?)/i },
  distribution: { term: 'Distribution', definition: 'Money an ETF pays out from the dividends or interest it receives, usually monthly or quarterly. You can take it as cash or reinvest it.', match: /(?<!(?:normal|joint|probability|return|bell) )\bdistributions?\b(?! of\b)/i },
  dca: { term: 'Dollar-cost averaging', definition: 'Investing a fixed amount at regular times, such as every month, so you buy more units when prices are low and fewer when they are high.', match: /\bdollar[- ]cost averag\w*|\bDCA\b/i },
  crypto: { term: 'Cryptocurrency', definition: 'Digital tokens such as bitcoin whose prices can swing very widely. Penguru leaves crypto funds out of its shortlists.', match: /\bcrypto\w*|\bbitcoin\b/i },
  real_estate: { term: 'Real estate', definition: 'Property such as buildings and land. In a mix it usually appears as REITs, companies that own and rent out property.', match: /\breal estate\b/i },
};
// Engine glossary keys worth linking in text, with the words that name them.
export const GLOSSARY_MATCH = {
  etf: /\bETFs?\b/, mer: /\bMERs?\b|\bfees?\b/i, volatility: /\bvolatility\b/i, bond: /\bbonds?\b/i, diversification: /\bdiversif\w*/i,
  hedged: /\bhedg\w*/i, reit: /\bREITs?\b/i, emerging_markets: /\bemerging[- ]markets?\b/i, drawdown: /\bdrawdowns?\b/i,
  index_fund: /\bindex funds?\b/i, asset_class: /\basset class(?:es)?\b/i, rebalancing: /\brebalanc\w*/i, leverage: /\bleverag\w*/i,
  inflation: /\binflation\b/i, tfsa_rrsp: /\bTFSA\b|\bRRSP\b/, hypothetical: /\bhypothetical\b/i, risk_tolerance: /\brisk tolerance\b/i,
  risk_capacity: /\brisk capacity\b|\bcapacity for risk\b/i, tbill_hisa: /\bhigh[- ]interest savings\b|\bcash ETF\b/i, yield: /\b(?:bond|dividend|distribution|current|annual|average) yields?\b|\byields? (?:of|on) (?:about )?\d/i,
};

// Answers to common questions, matched by pattern (first match wins). {level} etc. are filled by the page.
export const FAQ = [
  { re: /\bhow long (?:does|will) (?:this|it) take\b|\bhow many (?:more )?questions\b/i, a: 'About five minutes for the main questions; the three optional ones add about a minute. You can ask questions along the way.' },
  { re: /\bdon'?t have a goal\b|\bno goal\b|\bnot sure (?:what|about) (?:my|the) goal/i, a: 'That is fine. Pick "Building wealth, no fixed date" or "I\'m just learning" and we will build a practice mix you can explore. You can change the goal at any time.' },
  { re: /\bwhat does "?all at once"? mean\b/i, a: '"All at once" means you plan to take the whole amount out in one go, for example a home down payment. "Over several years" means you would take it out bit by bit, like retirement income or tuition paid each term.' },
  { re: /\bwhat counts as (?:high[- ]interest|expensive) debt\b/i, a: 'Usually balances that charge around 10% a year or more and that you carry from month to month: credit cards, store cards, payday loans. A mortgage or a low-rate student loan does not usually count.' },
  { re: /\bwhat counts as (?:a )?steady income\b/i, a: 'A salary, a pension or other regular payments you can count on. Freelance, commission, seasonal or gig work counts as "varies a lot," and having no regular income right now is its own answer.' },
  { re: /^what is risk\b|\bwhat does risk mean\b/i, a: 'Here, risk means how much the value of your money can swing up and down, and how far it could fall before it recovers. More risk usually comes with more growth over long periods, but also bigger drops along the way.' },
  { re: /\bwhat do these numbers mean\b|\bhow do i read (?:these|the) cards\b/i, a: '__CARDS__' },
  { re: /\bwhy are some ranges wider\b|\bwhy (?:is|are) (?:the )?ranges? (?:wider|different)\b/i, a: 'Mixes with more stocks swing more, so their good outcomes are better and their bad ones worse: the range is wider. Mixes with more bonds and cash move less, so their range is narrower.' },
  { re: /\bwhat is a 2008[- ]style crisis\b|\bwhat happened in 2008\b/i, a: 'In 2008 banks failed, credit froze and stock markets fell by about half from peak to bottom over many months; it took years to recover. Penguru replays that period on a mix to show how much it could have fallen. ' + 'Past performance is not reflective of future performance.' },
  { re: /\bcan i add any etf\b|\bcan i (?:add|pick|choose) (?:my own|any) (?:etf|fund)/i, a: 'Most Canadian-listed ETFs, yes. Penguru only adds funds that pass its screen: enough price history (3 years), enough assets ($20 million), regular trading, and no leverage. If a fund does not pass, it says why.' },
  { re: /\b(is|are) (this|these|it|any of (?:this|it))\b.*\b(real|invested|actual)\b|\breal (?:money|investing)\b|\bany of (?:this|it) invested\b/i, a: 'No. Penguru is a model: nothing is bought, sold or stored, and no account is opened. It shows what a mix could look like and why.' },
  { re: /\bhow (?:do|can|would) i (?:actually )?(?:buy|purchase|get|invest in)\b|\bwhere (?:do|can) i buy\b/i, a: 'ETFs are bought like shares, through a brokerage account at a bank or an online broker, often inside a TFSA or RRSP. Penguru does not recommend a broker or place trades. Before buying any ETF, read its ETF Facts document on the issuer\'s website.' },
  { re: /\bcan i lose\b|\blose (?:all|everything|my money)\b|\bis (?:it|this) (?:safe|risky)\b|\bguarantee/i, a: 'Yes, investments can lose value, and nothing here is guaranteed. That is why Penguru shows a bad year (about 1 in 20) and a 2008 replay in your own dollars next to every mix, so you can judge whether you could live with it.' },
  { re: /\bhow much should i (?:invest|start|put)\b|\bhow much (?:money )?(?:do i need|to start)\b/i, a: 'There is no set amount; many brokers let you start small. A common order of steps is: an emergency fund first, then paying off high-interest debt, then investing money you will not need soon. Penguru works with any amount you type.' },
  { re: /\b(?:what|how) (?:do|does|did) (?:the )?(?:risk )?levels?\b|\bwhat (?:is|does) (?:a |my )?(?:risk )?level\b|\blevel \d means?\b/i, a: "Penguru's levels run from 1 (Conservative) to 5 (Aggressive growth). Each aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80%, level 5 about all of it. Higher levels usually hold more stocks, so they can grow more but also fall more." },
  { re: /\bhow (?:was|is|did) (?:this|my|the) (?:mix|portfolio|level)\b.*\b(?:chosen|calculated|picked|made|work)|\bhow does (?:this|it|robo-kit|penguru) work\b|\bwhy (?:this|these) (?:mix|funds?)\b/i, a: 'Your answers give two scores: how much risk your situation can absorb (time, savings, income) and how much you are comfortable with. The suggestion is the lower of the two. The optimizer then weighs one low-cost index fund per kind of investment so the mix matches that suggestion, a risk level from 1 (steadiest) to 5 (most growth). Every step is shown, and you can change any answer.' },
  { re: /\bwhat (?:if|happens if) (?:the )?market(?:s)? (?:crash|drop|fall)|\bcrash\b|\brecession\b/i, a: 'Markets do fall, sometimes sharply. Penguru replays past crises (2008, 2020, 2022 and others) on today\'s mix so you can see the size of a drop in your dollars. After past crises diversified mixes recovered, over months in 2020 and years in 2008. ' + 'Past performance is not reflective of future performance.' },
  { re: /\bwhy (?:do|did) you (?:ask|need)\b|\bwhy (?:this|that) question\b|\bwhat(?:'s| is) the point\b/i, a: '__WHY__' },
  { re: /\bwhat (?:if|happens if) i(?:'m| am)? (?:not sure|don't know|do not know)\b|\bi(?:'m| am) not sure\b|\bno idea\b/i, a: '__UNSURE__' },
  { re: /\b(?:do|does) (?:you|robo-kit|penguru|this) (?:store|save|keep|collect)\b|\bprivacy\b|\bmy data\b/i, a: 'Nothing you type is stored or sent anywhere by Penguru, and it never asks for your name, accounts or contact details. Closing the page clears your answers.' },
  { re: /\btax(?:es)?\b|\bTFSA\b|\bRRSP\b|\bFHSA\b|\bRESP\b/i, a: 'TFSAs, RRSPs, FHSAs and RESPs are Canadian accounts with tax benefits; ETFs can be held inside them. Which account fits you depends on your income and plans, which a tax professional can advise on. Penguru does not give tax advice.' },
  { re: /\brebalanc|\bhow often\b.*\b(?:check|change|adjust)/i, a: 'Markets move a mix away from its targets over time. Rebalancing means trading back to the targets, for example once or twice a year or when a fund drifts more than a few points. Penguru shows the targets; when and whether to rebalance is your decision.' },
  { re: /\bwhat(?:'s| is) a ticker\b/i, a: 'A ticker is the short code a fund trades under, like VFV or XIC. You can type one at any time to add that fund to your shortlist.' },
  { re: /\bwhat(?:'s| is) a theme\b/i, a: 'A theme is a focus beyond the broad market, such as technology, dividends, clean energy or banks. Theme funds hold fewer companies, so they can swing more than a broad index fund.' },
  { re: /\bcan a fund end up at zero\b|\bwhy (?:is|did) .* (?:0|zero)%/i, a: 'Yes. The optimizer only gives a fund weight if it helps the mix reach your risk level efficiently; at some levels a fund adds nothing that the others do not already cover.' },
  { re: /\bwhy (?:is there )?so much (?:in )?bonds?\b|\bwhy bonds\b|\bwhy do bonds matter\b|\bwhat are bonds for\b|\bwhy (?:hold|own|have) bonds\b/i, a: 'Bonds usually move less than stocks and often hold up when stocks fall, so they steady a mix. The lower the risk level, the more of the mix sits in bonds and cash.' },
  { re: /\bhow (?:is|was) my (?:risk )?level (?:worked out|set|decided|calculated|chosen)\b|\bhow (?:do|did) you (?:get|pick|choose|work out) (?:my|the) level\b/i, a: 'Your answers give two scores: how much risk your situation can absorb (time until you need the money, your savings and income) and how much you said you are comfortable with (your self-rating, your reaction to a drop and the range you picked). The suggested level is the lower of the two, and it is held at 2 or below until an emergency fund and paying off expensive debt are in place.' },
  { re: /\b(?:can|could) an etf (?:go to zero|lose everything)\b|\betf (?:go|goes|going) (?:to )?zero\b/i, a: 'A broad index ETF holds hundreds or thousands of companies or bonds, so it would only go to zero if all of them failed at once. It can still fall a lot: broad stock funds lost about half in 2008. Narrow, leveraged or single-theme funds can fall much further. Past performance is not reflective of future performance.' },
  { re: /\bwhat (?:are|is) (?:a )?distributions?\b|\bdo etfs pay\b|\bdividends? from (?:an )?etfs?\b/i, a: 'Many ETFs pass on the dividends or interest they receive as distributions, usually monthly or quarterly. Penguru\'s figures assume they are reinvested. You can take them as cash or reinvest them; how they are taxed depends on the account they are in.' },
  { re: /\bcontract(?:or|ing)\b|\bfreelanc\w*\b|\bself[- ]employed\b|\bcounts? as steady\b/i, a: 'Freelance, contract, commission or seasonal work counts as "varies a lot" unless you have a steady contract you can count on for years. A salary or a pension counts as steady.' },
  { re: /\bline of credit\b|\bstudent loans?\b|\bcar loan\b|\bmortgage\b.*\bdebt\b/i, a: 'Usually not high-interest debt: a mortgage, a student loan or a line of credit at a low rate does not count. High-interest debt is mainly credit cards and similar balances that charge around 10% a year or more.' },
  { re: /\bgrey tick\b|\btwo numbers\b|\bwhat do the cards (?:mean|show)\b|\bhow do (?:the )?cards work\b/i, a: '__CARDS__' },
  { re: /\bwhat (?:would|do) most people (?:do|choose|pick)\b/i, a: 'There is no "normal" answer, and Penguru does not compare you with anyone. What matters is how you would actually feel and act; an honest guess is the best answer.' },
  { re: /\bhas the market (?:really|ever) dropped\b|\bhas (?:that|this) (?:really )?happened\b/i, a: 'Yes. In 2008 broad stock markets fell about half from peak to bottom, and in early 2020 they fell about a third in a few weeks. Both later recovered, over years in 2008\'s case. ' + 'Past performance is not reflective of future performance.' },
];

// What the market-context readings are, for "What do these mean?": what each measures, never what it implies.
export const CONTEXT_KEYS = ['ca_policy', 'ca_cpi', 'usdcad', 'vix'];  // the Canadian readings first (the requirements limit context to Canada)
// Approved sources for market and industry trends (E3, X5): the page links out to them; it does not copy their news.
export const TREND_LINKS = [
  { name: 'BNN Bloomberg: markets', url: 'https://www.bnnbloomberg.ca/markets/' },
  { name: 'CNN Business: markets', url: 'https://www.cnn.com/markets' },
  { name: 'Nasdaq: ETF news', url: 'https://www.nasdaq.com/news-and-insights/topic/markets/etfs' },
];
export const CONTEXT_LEARN_CA = 'The Bank of Canada policy rate is the rate the Bank targets; it sets what cash and short-term savings pay. Inflation is how fast prices are rising; the Bank aims for 2%. The US dollar in Canadian dollars matters for US funds that are not hedged. The VIX measures how big the swings in US stocks are expected to be over the next month. All of these describe the moment. None of them is a timing signal, and Penguru never changes a mix because of them.';
export const CONTEXT_LEARN = 'The VIX measures how big the swings in US stocks are expected to be over the next month; the geopolitical risk index counts newspaper coverage of wars, threats and terrorism. Both describe the mood today. Neither is a timing signal, and Penguru never changes a mix because of them.';

// Where the market-context readings come from (the data scripts in robokit/data/context.py).
export const CONTEXT_SOURCES = {
  vix: { name: 'Cboe (VIX), via Yahoo Finance', url: 'https://www.cboe.com/tradable_products/vix/' },
  ca_policy: { name: 'Bank of Canada', url: 'https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/' },
  ca_cpi: { name: 'Bank of Canada (CPI)', url: 'https://www.bankofcanada.ca/rates/price-indexes/cpi/' },
  ca_curve: { name: 'Bank of Canada (bond yields)', url: 'https://www.bankofcanada.ca/rates/interest-rates/canadian-bonds/' },
  usdcad: { name: 'Yahoo Finance (CAD=X)', url: 'https://finance.yahoo.com/quote/CAD%3DX/' },
  gpr: { name: 'Caldara and Iacoviello', url: 'https://www.matteoiacoviello.com/gpr.htm' },
  epu_us: { name: 'Economic Policy Uncertainty', url: 'https://www.policyuncertainty.com/' },
  epu_ca: { name: 'Economic Policy Uncertainty', url: 'https://www.policyuncertainty.com/' },
};
export const LEVELS_LEARN = "Each level aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80%, level 5 about all of it. Higher levels usually hold more stocks, so they can grow more but also fall more. The suggestion is the lower of what your situation can absorb and what you said you are comfortable with.";

// F3: tickers listed in the US are outside the data. For well-known ones, the Canadian-listed funds in the data that
// follow the same or a similar index (information, not a recommendation; the page checks each is in the data).
export const US_LISTED = {
  SPY: { index: 'the S&P 500', ca: ['VFV', 'ZSP', 'XUS'] }, VOO: { index: 'the S&P 500', ca: ['VFV', 'ZSP', 'XUS'] }, IVV: { index: 'the S&P 500', ca: ['VFV', 'ZSP', 'XUS'] },
  QQQ: { index: 'the Nasdaq-100', ca: ['QQC', 'ZQQ', 'XQQ'] }, QQQM: { index: 'the Nasdaq-100', ca: ['QQC', 'ZQQ', 'XQQ'] },
  VTI: { index: 'the whole US stock market', ca: ['VUN', 'XUU'] }, ITOT: { index: 'the whole US stock market', ca: ['VUN', 'XUU'] },
  VT: { index: 'stocks around the world', ca: ['XAW', 'VXC'] }, ACWI: { index: 'stocks around the world', ca: ['XAW', 'VXC'] },
  VEA: { index: 'developed markets outside North America', ca: ['XEF', 'VIU'] }, IEFA: { index: 'developed markets outside North America', ca: ['XEF', 'VIU'] }, EFA: { index: 'developed markets outside North America', ca: ['XEF', 'VIU'] },
  VWO: { index: 'emerging markets', ca: ['VEE', 'XEC', 'ZEM'] }, EEM: { index: 'emerging markets', ca: ['VEE', 'XEC', 'ZEM'] }, IEMG: { index: 'emerging markets', ca: ['VEE', 'XEC', 'ZEM'] },
  BND: { index: 'US investment-grade bonds', ca: ['VBU', 'XAGG'] }, AGG: { index: 'US investment-grade bonds', ca: ['VBU', 'XAGG'] },
  GLD: { index: 'gold bullion', ca: ['VALT', 'KILO', 'CGL'] }, IAU: { index: 'gold bullion', ca: ['VALT', 'KILO', 'CGL'] },
  TLT: { index: 'long-term US Treasury bonds', ca: ['ZTL'] }, IWM: { index: 'US small companies (the Russell 2000)', ca: ['XSU'] }, DIA: { index: 'the Dow Jones Industrial Average', ca: ['ZDJ'] },
  ARKK: { index: null, ca: [] }, SCHD: { index: null, ca: [] }, JEPI: { index: null, ca: [] }, VUG: { index: null, ca: [] }, VIG: { index: null, ca: [] }, XLK: { index: null, ca: [] }, SOXX: { index: null, ca: [] }, SMH: { index: null, ca: [] }, VNQ: { index: null, ca: [] }, BITO: { index: null, ca: [] },
};
export const NOT_CANADIAN = (t) => `${t} is listed in the US. Penguru only has prices, fees and risk data for Canadian-listed ETFs, so it cannot add ${t} to your shortlist or optimize it.`;

// Generic help when nothing matches and Claude is not connected.
export const FALLBACK = {
  chat: "I don't have a written answer for that here. I can explain any investing word (try \"What is a bond?\"), say why a question is asked, or describe any ETF by its ticker (try \"What is XIC?\").",
  claude: 'Connect Claude above and you can ask anything in your own words; Claude reasons with the numbers on this page.',
};

// Top holdings of the ten default funds, from the issuers' own pages (data/fund_holdings.json has each source row
// quoted). Two independent lookups on 2026-10-14 agreed. Holdings change; the as-of date is shown with them.
export const HOLDINGS = {
 "XIC.TO": {
  "as_of": "Oct 13, 2026",
  "url": "https://www.blackrock.com/ca/investors/en/products/239837/ishares-sptsx-capped-composite-index-etf/1464253357814.ajax?fileType=csv&fileName=XIC_holdings&dataType=fund",
  "top": [
   [
    "Royal Bank of Canada (RY)",
    7.49
   ],
   [
    "Shopify (SHOP)",
    5.91
   ],
   [
    "Toronto-Dominion Bank (TD)",
    5.38
   ],
   [
    "Bank of Montreal (BMO)",
    3.21
   ],
   [
    "Bank of Nova Scotia (BNS)",
    3.05
   ]
  ],
  "holds": "about 217 Canadian company stocks listed on the TSX, so it follows the Canadian stock market"
 },
 "VFV.TO": {
  "as_of": "Aug 31 2026",
  "url": "https://www.vanguard.ca/en/product/etf/equity/9563/vanguard-sp-500-index-etf",
  "top": [
   [
    "NVIDIA Corp",
    8.07
   ],
   [
    "Apple Inc",
    7.03
   ],
   [
    "Microsoft Corp",
    5.69
   ],
   [
    "Amazon.com Inc",
    3.84
   ],
   [
    "Alphabet Inc (one share class)",
    3.0
   ]
  ],
  "holds": "about 500 large US companies (the S&P 500), held through Vanguard's US-listed S&P 500 ETF"
 },
 "FLUR.NE": {
  "as_of": "September 30, 2026",
  "url": "https://www.franklintempleton.ca/download/en-ca/factsheet/7efeb244-bbce-4d09-a26b-c5e8eacb2b7f/Factsheet-FranklinInternationalEquityIndexETF-27748-FF-CA-en-CA.PDF",
  "top": [
   [
    "ASML Holding NV",
    3.07
   ],
   [
    "HSBC Holdings PLC",
    1.52
   ],
   [
    "Roche Holding AG",
    1.36
   ],
   [
    "Mitsubishi UFJ Financial Group Inc",
    1.19
   ],
   [
    "Shell PLC",
    1.17
   ]
  ],
  "holds": "about 850 large and mid-size companies in developed markets outside North America, such as Europe and Japan"
 },
 "VEE.TO": {
  "as_of": "Aug 31 2026",
  "url": "https://www.vanguard.ca/en/product/etf/equity/9556/vanguard-ftse-emerging-markets-all-cap-index-etf",
  "top": [
   [
    "Taiwan Semiconductor Manufacturing Co Ltd",
    14.67
   ],
   [
    "Tencent Holdings Ltd",
    2.89
   ],
   [
    "Alibaba Group Holding Ltd",
    2.18
   ],
   [
    "MediaTek Inc",
    1.46
   ],
   [
    "Delta Electronics Inc",
    0.9
   ]
  ],
  "holds": "thousands of company stocks in emerging markets such as Taiwan, China and India, held mainly through Vanguard's US-listed emerging-markets ETF"
 },
 "ZAG.TO": {
  "as_of": "Sep 30, 2026",
  "url": "https://df.bmogam.com/assets/static/etf-profiles-pdfs/BMO%20Aggregate%20Bond%20Index%20ETF_Factsheet_EN_ZAG.pdf",
  "top": [
   [
    "Canadian Government Bond 2.75% 03/01/2031",
    1.52
   ],
   [
    "Canadian Government Bond 2.75% 09/01/2030",
    1.52
   ],
   [
    "Canadian Government Bond 3.25% 12/01/2035",
    1.49
   ],
   [
    "Canadian Government Bond 3.25% 06/01/2036",
    1.45
   ],
   [
    "Gov. of Canada 3.00% 09/01/2031",
    1.41
   ]
  ],
  "holds": "about 1,900 Canadian investment-grade bonds: federal, provincial, corporate and municipal. It holds bonds, not stocks"
 },
 "XSB.TO": {
  "as_of": "Oct 13, 2026",
  "url": "https://www.blackrock.com/ca/investors/en/products/239491/ishares-canadian-short-term-bond-index-etf/1464253357814.ajax?fileType=csv&fileName=XSB_holdings&dataType=fund",
  "top": [
   [
    "Canada (Government of) 2.75% due Sep 1, 2030",
    3.38
   ],
   [
    "Canada (Government of) 2.75% due Mar 1, 2031",
    3.38
   ],
   [
    "Canada (Government of) 3.00% due Sep 1, 2031",
    3.05
   ],
   [
    "Canada (Government of) 2.75% due Mar 1, 2030",
    2.71
   ],
   [
    "Canada (Government of) 3.50% due Sep 1, 2029",
    2.54
   ]
  ],
  "holds": "several hundred Canadian investment-grade bonds that mature within about five years. It holds bonds, not stocks"
 },
 "VBU.NE": {
  "as_of": "Aug 31 2026",
  "url": "https://www.vanguard.ca/en/product/etf/fixed-income/9567/vanguard-us-aggregate-bond-index-etf-cad-hedged",
  "top": [
   [
    "United States Treasury Note/Bond 3.50% Jan 31 2028",
    0.47
   ],
   [
    "United States Treasury Note/Bond 4.25% Nov 15 2034",
    0.41
   ],
   [
    "United States Treasury Note/Bond 4.38% May 15 2034",
    0.41
   ],
   [
    "United States Treasury Note/Bond 3.38% Nov 30 2027",
    0.4
   ],
   [
    "United States Treasury Note/Bond 4.63% Feb 15 2035",
    0.4
   ]
  ],
  "holds": "thousands of US investment-grade bonds, mostly US Treasuries, held through Vanguard's US-listed Total Bond Market ETF, with the currency hedged to CAD. It holds bonds, not stocks"
 },
 "XRE.TO": {
  "as_of": "Oct 13, 2026",
  "url": "https://www.blackrock.com/ca/investors/en/products/239843/ishares-sptsx-capped-reit-index-etf/1464253357814.ajax?fileType=csv&fileName=XRE_holdings&dataType=fund",
  "top": [
   [
    "RioCan Real Estate Investment Trust (REI.UN)",
    13.12
   ],
   [
    "Granite Real Estate Investment Trust stapled units (GRT.UN)",
    11.4
   ],
   [
    "First Capital Real Estate Investment Trust (FCR.UN)",
    10.76
   ],
   [
    "Canadian Apartment Properties REIT (CAR.UN)",
    10.41
   ],
   [
    "Choice Properties Real Estate Investment Trust (CHP.UN)",
    8.83
   ]
  ],
  "holds": "about 14 Canadian real estate investment trusts (REITs), companies that own and rent out property"
 },
 "VALT.TO": {
  "as_of": "September 30, 2026",
  "url": "https://funds.cifinancial.com/en/documents/static/Fund_Profiles/Monthly_Profile/52496/Monthly_Profile.pdf",
  "top": [
   [
    "Gold Bullion",
    99.99
   ]
  ],
  "holds": "physical gold bullion, no stocks or bonds"
 },
 "CASH.TO": {
  "as_of": "September 30, 2026",
  "url": "https://www.globalx.ca/product/cash",
  "top": [
   [
    "National Bank cash account",
    49.53
   ],
   [
    "Scotiabank cash account",
    28.07
   ],
   [
    "CIBC cash account",
    14.79
   ],
   [
    "Scotiabank cash account 2",
    4.48
   ],
   [
    "CIBC Mellon cash account",
    3.14
   ]
  ],
  "holds": "cash deposits at Canadian banks, no stocks or bonds"
 }
};

// ================================================================== v3.2: the words for open conversation and depth
// Depth changes the words and what is open first, never an option value, a step or a number. The standard depth keeps
// the approved script text; these are the beginner ("novice") and experienced ("expert") columns, plus the turn texts.

// WORDING[id] = { novice: {q, qBy?, opts?, monthly?}, expert: {q, opts?, monthly?, card?}, ex: {value: example line for beginners} }
export const WORDING = {
  A1: {
    novice: { q: 'What is this money for? Pick the closest one; you can change it later.' },
    expert: { q: 'Goal for this money?', opts: { wealth: 'Wealth building, no fixed date', income: 'Income now (drawing it down)' } },
    ex: { retirement: 'Money to live on after you stop working.', home: 'Saving for a down payment on a home.', education: 'Paying for school, for you or your children.', wealth: 'Growing your savings with no set deadline.', income: 'Taking money out regularly, starting soon.', learning: 'Practising with a model portfolio; nothing is bought.' },
  },
  B1: {
    novice: { qBy: {
      retirement: 'Roughly when do you expect to retire and start using this money? A guess like "in about 25 years" is fine.',
      home: 'When do you think you\'ll need the money for {goal_np}? A rough guess like "in about 4 years" is fine.',
      education: 'When will the first school costs come up, roughly? "In 10 years" or "by 2034" both work.',
      income: 'When would you like to start taking income from it? "Right away" is a fine answer.',
      wealth: 'Even without a set date, when might you start using some of it? "Not for 20 years" is a fine answer.',
      learning: 'If this were real money, when might you start using it? A rough guess is fine; you can change it later.',
      _: "When do you think you'll start using this money? A rough guess is fine.",
    } },
    someLearning: 'If this were real money, when would you expect to start taking it out?',
    expert: { q: 'Horizon: when do withdrawals start?', opts: { lt2: 'Under 2 years', '2to4': '2 to 4 years', '5to9': '5 to 9 years', '10to19': '10 to 19 years', '20plus': '20+ years' } },
    ex: { lt2: 'Within the next year or two, like a planned purchase.', '2to4': 'In a few years, like a down payment.', '5to9': "Later this decade, like a child's tuition.", '10to19': 'Ten or more years away, like retirement still some way off.', '20plus': 'Twenty or more years away, like retirement far in the future.' },
  },
  B2: {
    novice: { qBy: {
      home: 'And when the time comes, would you take it out all at once, like a down payment, or bit by bit over a few years?',
      retirement: 'Once you retire, would you draw on it bit by bit over many years, or take it out in one go?',
      education: 'Would you take it out all at once, or bit by bit, like tuition paid each term?',
      _: 'Once you start using it, will you take it out all at once or a bit at a time?',
    } },
    expert: { q: 'Withdrawal period once they start?', opts: { once: 'Lump sum', '2to5': '2 to 5 years', '6to10': '6 to 10 years', '10plus': '10+ years', unsure: 'Not sure yet' } },
    ex: { once: 'Like a home down payment.', '2to5': 'Like tuition paid each term.', '6to10': 'Like topping up your income for several years.', '10plus': 'Like living on it through retirement.', unsure: "That's fine; I'll use a middle setting." },
  },
  BASICS: { novice: { q: "Two quick checks before investing. Both situations are common, and there's no wrong answer." }, expert: { q: 'Prerequisites.' } },
  A2: {
    novice: { q: 'Do you have money set aside for emergencies, separate from this money? Enough for 3 to 6 months of bills.' },
    expert: { q: 'Emergency fund (3 to 6 months of expenses), separate from this money?' },
    ex: { yes: 'For example, in a savings account you can reach quickly.', partly: 'Some, but less than 3 months.', no: 'Not yet. Many people start here.' },
  },
  A3: {
    novice: { q: "Do you owe money on a credit card or loan with high interest that you don't pay off each month?" },
    expert: { q: 'High-interest debt carried month to month?', opts: { no: 'None', little: 'A little', lot: 'A lot' } },
    ex: { no: 'Or only a mortgage or a low-rate loan.', little: 'A balance you expect to clear soon.', lot: 'A balance that is hard to pay down.' },
  },
  MONEY: {
    novice: { q: 'About how much would you put in to start? Any amount works: this is a model, and nothing is invested.', monthly: 'Could you add some each month?' },
    expert: { q: 'Initial amount and monthly contribution? You can type both, like "$50k + $500 a month".', monthly: 'Monthly contribution' },
  },
  B5: {
    novice: { q: 'How steady is your income?' },
    expert: { q: 'Income stability?', opts: { very: 'Steady', mostly: 'Mostly steady', varies: 'Variable', pension: 'Pension or guaranteed income', none: 'None right now' } },
    ex: { very: 'A regular salary or paycheque.', mostly: 'Mostly regular, with some ups and downs.', varies: 'Freelance, commission or seasonal work.', pension: 'Retired, with a pension or other income you can count on.', none: 'Student, between jobs or not working right now.' },
  },
  C0: {
    novice: { q: 'How do you feel about your money going up and down in value?' },
    expert: { q: 'Self-rated risk tolerance?', opts: { low: 'Low', medium: 'Medium', high: 'High' } },
    ex: { low: 'Seeing a loss would worry me a lot.', medium: 'Some dips are fine if things recover.', high: 'Big drops are OK if growth is higher over time.' },
  },
  C2: {
    novice: { q: "Imagine the market falls sharply: in three months your {amount} is worth {after}. What would you most likely do? There's no right answer; an honest guess helps most." },
    expert: { q: '{amount} falls to {after} over three months. Most likely response?', opts: { sell_all: 'Sell all', sell_some: 'Sell some', wait: 'Hold', buy: 'Buy more', dont_know: "Don't know" } },
    ex: { sell_all: 'Move everything to cash to stop the loss.', sell_some: 'Take some out to feel safer.', wait: 'Leave it and wait for a recovery.', buy: 'Add more while prices are lower.', dont_know: "Hard to say. That's an honest answer." },
  },
  RECON: {
    novice: { q: "Those two answers point different ways: you said {c0}, but after a sharp drop you'd {c2}. That gap is very common. Which feels more accurate: how you rated yourself, or what you'd do in the drop? I'll use that one and set the other aside.", opts: { C0: 'How I rated myself', C2: "What I'd do in a drop" } },
    expert: { q: 'Your self-rating ({c0w}) and your drop response ("{c2}") point different ways. Which should count? The other is set aside.', opts: { C0: 'Self-rating', C2: 'Drop response' } },
  },
  C1: {
    novice: { q: 'Here are five possible mixes. Each card shows where your {amount} might be after one year. Which range could you live with?' },
    expert: { q: 'One-year outcomes by mix, 10th to 90th percentile. Which range would you accept?' },
  },
  FT: {
    novice: { q: 'Want to answer three more questions so the suggestion fits you better? About a minute; you can skip.', opts: { yes: 'Yes, three more', no: 'Skip, show my result' } },
    expert: { q: 'Optional refinement: share of savings, a ten-year range, and losses vs. missed gains (three items).', opts: { yes: 'Refine', no: 'Skip' } },
  },
  B4: {
    novice: { q: 'Roughly how much of all your savings and investments is this money? A guess is fine, or skip.' },
    expert: { q: 'Share of total investable assets?' },
    ex: { lt10: 'A small part of what you have.', '10to25': 'Up to about a quarter.', '25to50': 'Up to about half.', '50to75': 'More than half.', gt75: 'Almost everything you have.' },
  },
  C3: {
    novice: { q: 'Same idea over ten years. Which range would you be comfortable ending up anywhere inside?' },
    expert: { q: 'Ten-year outcomes by mix, 10th to 90th percentile. Which would you accept?' },
  },
  C4: {
    novice: { q: 'Which would bother you more?' },
    expert: { q: 'Which weighs more: losses or missed gains?', opts: { losing: 'Losses', both: 'Equally', missing: 'Missed gains' } },
    ex: { losing: 'Seeing your balance go down.', both: 'Both, about the same.', missing: 'Watching prices rise without you.' },
  },
  PREFS: {
    novice: { q: "Anything you'd like your mix to focus on or avoid? This is optional; many people skip it." },
    expert: { q: 'Screens and tilts (optional). Tap, or type filters such as "MER under 0.20%, hedged US, no emerging markets, tech".' },
  },
  TICKER: {
    novice: { q: "Do you already have a specific fund in mind? Most people skip this. If you do, type its ticker: the short code it trades under, like XIC. Then I'll build your mix." },
    expert: { q: 'Tickers to add as your own picks? Comma-separated. They join the shortlist without re-running the screens; the mix is built next.' },
  },
};

// "How this is scored" for experienced viewers: the rule itself. CAPACITY_BREAKS is not in core.json, so a Node test
// checks it against scoreProfile for all 25 horizon pairs; the points and levels come from core.json.
export const CAPACITY_BREAKS = [[2, 1], [5, 2], [9, 3], [12, 4]];  // horizon points <= p -> level; above 12 -> level 5
const LEVEL_IS = 'Risk level runs from 1 (steadiest) to 5 (most growth); your result shows what yours means. ';
export function whyDeep(id, core) {
  const q = (k) => core.questions.find((x) => x.id === k);
  const pts = (k) => q(k).options.map((o) => `${o.text.toLowerCase()} ${o.pts}`).join(', ');
  const lvls = (k) => q(k).options.map((o) => `${o.text.split(':')[0].replace(/^./, (c) => c.toLowerCase())} ${o.level}`).join(', ');
  switch (id) {
    case 'EXP': return 'Depth changes only the wording and what is shown first. Scoring and the optimizer are identical for everyone.';
    case 'A1': return 'The goal sets how the money comes out, as an assumption you can change: a home all at once, education over 2 to 5 years, retirement over more than 10 years, anything else "Not sure yet" (the middle setting). "Building wealth" has no withdrawal date, so it is not used.';
    case 'B1': case 'B2': return `${LEVEL_IS}Risk capacity starts from horizon points. Start (${pts('B1')}) plus period (${pts('B2')}). A total of 2 or less allows level 1; 5 or less, level 2; 9 or less, level 3; 12 or less, level 4; more, level 5. Under 2 years and all at once: no stock mix.`;
    case 'BASICS': case 'A2': case 'A3': return LEVEL_IS + 'Gate: no emergency fund, or a lot of high-interest debt, caps the build at level 2. A partial emergency fund counts as a cushion (one step lower).';
    case 'B5': case 'B4': return `${LEVEL_IS}Cushions: uneven or no income (${pts('B5')}) and this money being 50% or more of your savings (${pts('B4')}) each lower capacity one step; at most two steps, or one when horizon points are 13 or more.`;
    case 'MONEY': return 'The amount scales the dollar figures and projections only. It does not change the suggestion or the weights; a monthly amount enters the simulated paths only.';
    case 'C0': case 'C2': case 'C1': case 'C3': case 'C4': case 'RECON': return `${LEVEL_IS}Tolerance is the average of the levels your answers map to, rounded down, and one lower when three or more answers spread by 3 or more levels. Self-rating: ${lvls('C0')}. Drop response: ${lvls('C2')}. Suggested level = the lowest of capacity, tolerance and any gate.`;
    case 'FT': return 'The three optional answers join the tolerance average (B4 joins capacity as a cushion).';
    case 'PREFS': return 'Screens change the shortlist, never the level. A theme adds your own pick (the cheapest eligible plain fund; index funds only unless you allow active funds); an exclusion drops that slot; a fee cap swaps a slot to an eligible fund under it; hedging switches US stocks to a CAD-hedged fund.';
    case 'TICKER': return 'The optimizer then runs constrained mean-variance on the shortlist with equilibrium returns: weights add up to 100%, no fund above 50% (the cash fund excepted), slot caps on emerging markets, real estate and gold, long only, no leverage. Your picks join without re-screening and each keeps a small minimum weight. Together they are capped at 10% of the mix at levels 1 and 2, 20% at level 3 and 30% at levels 4 and 5.';
    default: return null;
  }
}

// How each answer reads inside a sentence (read-backs, checkpoints, follow-ups).
export const PHRASE = {
  A1: { retirement: 'saving for retirement', home: 'saving for a home', education: 'saving for education', wealth: 'growing your money with no fixed date', income: 'looking for income you can spend now', learning: 'here to learn how this works' },
  B1: { lt2: 'within two years', '2to4': 'in 2 to 4 years', '5to9': 'in 5 to 9 years', '10to19': 'in 10 to 19 years', '20plus': 'in 20 years or more' },
  B2: { once: 'all at once', '2to5': 'over 2 to 5 years', '6to10': 'over 6 to 10 years', '10plus': 'over more than 10 years', unsure: 'with no set plan for taking it out yet' },
  A2: { yes: 'an emergency fund in place', partly: 'part of an emergency fund', no: 'no emergency fund yet' },
  A3: { no: 'no high-interest debt', little: 'a little high-interest debt', lot: 'a fair amount of high-interest debt' },
  B5: { very: 'very steady', mostly: 'mostly steady', varies: 'uneven', pension: 'from a pension or other guaranteed income', none: 'not coming in regularly right now' },
  C0: { low: "you'd rather keep things steady", medium: 'some ups and downs are fine', high: 'you can live with big swings' },
  C2: { sell_all: 'sell everything', sell_some: 'sell some', wait: 'wait it out', buy: 'buy more', dont_know: "aren't sure what you'd do" },
  B4: { lt10: 'less than 10%', '10to25': '10% to 25%', '25to50': '25% to 50%', '50to75': '50% to 75%', gt75: 'more than 75%' },
  C4: { losing: 'losing money', both: 'losing money and missing gains equally', missing: 'missing out on gains' },
};
export const BARE = { B1: { lt2: 'under 2 years', '2to4': '2 to 4 years', '5to9': '5 to 9 years', '10to19': '10 to 19 years', '20plus': '20 years or more' }, A1: { retirement: 'retirement', home: 'a home', education: 'education', income: 'income now', wealth: 'growth with no fixed date', learning: 'learning' }, C0: { low: 'keeping things steady', medium: 'some ups and downs', high: 'big swings for more growth' } };
// A story told up front reads back as clauses about the person.
export const REFLECT = {
  A1: "you're {goal}", B1: "you'd start using it {when}", B2: "you'd take it out {how}", MONEY: "you're starting with {amount}{monthly}",
  A2: 'you have {ef}', A3: 'you have {debt}', B5: 'your income is {income}', C0: '{c0}', C2: "you'd {c2} in a drop (I'll check that with your numbers when we get there)",
};
export const READBACK = { full: "Here's what I have so far: {list}. I'll only ask about what's missing, and you can change anything.", short: "Noted. I'll only ask about what's missing." };
// The person's own goal words that may be echoed back (a whitelist: free text is never echoed).
export const GOAL_NP = { retirement: 'retirement', home: 'the home', education: 'school costs', wealth: 'this money', income: 'this income', learning: 'this practice money' };
export const GOAL_WORDS = [
  [/\bdown ?payment\b/, 'the down payment', 'home'], [/\bcondo\b/, 'the condo', 'home'], [/\bcottage\b/, 'the cottage', 'home'], [/\b(?:first )?house\b/, 'the house', 'home'],
  [/\bapartment\b/, 'the apartment', 'home'], [/\bwedding\b/, 'the wedding', 'home'], [/\bcar\b/, 'the car', 'home'],
  [/\b(?:kids?'?|children'?s?) (?:school|education|university|college)\b|\bresp\b/, "your kids' education", 'education'], [/\btuition\b/, 'tuition', 'education'], [/\buniversit\w*\b/, 'university', 'education'], [/\bcollege\b/, 'college', 'education'],
  [/\bretir\w* early\b|\bearly retirement\b/, 'retiring early', 'retirement'],
];
// One-line versions of each question, for coming back after a side question.
export const SHORT_ASK = {
  EXP: 'How much do you already know about ETFs?', A1: "What's this money for?", B1: 'When would you start using the money?', B2: 'All at once, or bit by bit?', BASICS: 'The two quick checks: emergency savings and high-interest debt.',
  A2: 'Do you have an emergency fund?', A3: 'Any high-interest debt?', MONEY: 'How much would you start with?', B5: 'How steady is your income?',
  C0: 'How comfortable are you with ups and downs?', C2: 'What would you most likely do in that drop?', RECON: 'Which one should I go with?',
  C1: 'Which range could you live with?', FT: 'Fine-tune, or go to your result?', B4: 'What share of your savings is this?', C3: 'Which ten-year range would you rather have?', C4: 'Which would bother you more?',
  PREFS: 'Any preferences, or skip?', TICKER: 'Any fund to add, or skip?',
};
// Feelings and life events mentioned in passing: acknowledged once each, before anything else.
export const CUES = {
  nervous: [/\b(?:nervous|worried|scared|anxious|afraid)\b|\bhate (?:losing|losses)\b/, 'Feeling nervous about losing money is common. Before anything is suggested, you will see what ups and downs could look like in your own dollars.'],
  firstJob: [/\b(?:first|new) (?:real |full[- ]time )?job\b|\bjust (?:got|started) (?:a |my )?(?:new )?job\b/, 'Congratulations on the new job.'],
  graduated: [/\bjust (?:graduated|finished school)\b/, 'Congratulations on finishing school.'],
};
// A typed answer that could mean two options: ask about just those two.
export const CLARIFY = {
  B1: 'When you say "{word}", is that closer to {a} or {b}?', B1num: 'Do you mean option {n} ({a}), or about {n} years from now ({b})?', A3: 'A little, or a lot?', C2: 'Would you sell everything, or just some?',
  C0: 'Which is closer: {a}, or {b}?', A1: 'Which is this money mainly for: {a} or {b}? You can run Penguru again for the other.',
  MONEY: 'Which should I use: {a} or {b}?', B5: 'Is that mostly steady, or does it vary a lot?', _: 'Just to check: did you mean {a} or {b}?',
};
// A reply that is not understood: said plainly once, then the question another way with the choices inline.
export const REPAIR = {
  lead: "Sorry, I didn't quite follow that.",
  EXP: 'Would you say you\'re new to investing, know the basics, or know it well? Or tap "Skip: just start".',
  A1: 'Is it for retirement, a home, education, income now, growing your money with no set date, or just learning?',
  B1: 'Roughly how many years until you\'d start using it? A number like "8" works.', B2: 'All at once, or spread over a few years?',
  BASICS: 'Do you have emergency savings (yes, partly or no), and any high-interest debt (none, a little or a lot)?',
  A2: 'Do you have emergency savings: yes, partly, or no?', A3: 'Any high-interest debt: none, a little, or a lot?',
  MONEY: 'What amount should I use? A number like 10000 or $10k works.', B5: 'Is your income steady, mostly steady, uneven, a pension, or none right now?',
  C0: 'Low, medium or high comfort with ups and downs?', C2: 'Would you sell everything, sell some, wait it out, buy more, or honestly not know?',
  C1: 'Pick the card whose range you could live with, or say "the second one".', C3: 'Pick the card whose range you would rather have, or say "the second one".',
  B4: 'Less than 10%, 10 to 25%, 25 to 50%, 50 to 75%, or more than 75%? Or skip it.', C4: 'Losing money, missing out on gains, or both equally?',
  FT: 'Fine-tune with three more questions, or go straight to your result?', RECON: "Should I go with your self-rating or with what you'd do in a drop?",
  PREFS: 'Tap the preferences you want and then "Apply preferences", type them (like "low fees, no emerging markets"), or skip.', TICKER: 'Type a ticker like XEQT, or skip.',
  second: { required: 'Even a rough guess is fine, and you can change it later.', optional: 'Or skip this one.' },
};
export const CONFIRM = {
  change: 'Earlier I noted "{old}". Change it to "{new}"?',
  C2: "Earlier you said you'd {c2} in a drop. Just to check with your numbers: if your {amount} fell to {after} over three months, would you still {c2}? Tap it to confirm, or pick another.",
};
export const REQUIRED_SKIP = 'I do need this one to make a suggestion; a rough answer is fine, and you can change it later. Only the experience question and the optional ones can be skipped.';
export const HIGHLIGHT = 'From what you said, this looks closest. Tap it to confirm, or pick another.';
export const SAVED_PREFS = "Saved for your shortlist: {prefs}. I'll apply it when we get to preferences.";
// The checkpoint after the situation questions (beginner UX: consistent checkpoints). No level number: a number here
// would anchor the questions about feelings that come next.
export const CHECKPOINT = {
  novice: 'Let me check I have this right. You\'re {goal}, and you\'d start using the money {when}{how}. You have {ef} and {debt}, you\'re starting with {amount}{monthly}, and your income is {income}. {effect} If anything is off, tap "Change something" or just tell me, like "actually it\'s 15 years". Next, a few questions about how you feel about ups and downs.',
  some: "Here's what I have: {goal}; starting to use it {when}{how}; {ef}; {debt}; {amount}{monthly}; income {income}. {effect} Tell me if anything is off. Next: how you feel about ups and downs.",
  expert: 'So far: {goal}; withdrawals start {when}{how}; {ef}; {debt}; {amount}{monthly}; income {income}.',
};
export const EFFECT = {
  time: { lt2: 'Money needed within two years has little time to recover from a drop.', '2to4': 'Two to four years gives the money only a little time to recover from a drop.', '5to9': 'Five to nine years gives the money some time to recover from a drop.', '10to19': 'Ten years or more gives the money plenty of time to recover from drops.', '20plus': 'Twenty years or more gives the money plenty of time to recover from drops.' },
  lowers: '{list} {verb} the suggestion a little more careful.',
  names: { B2once: 'taking it out all at once', A2partly: 'a partial emergency fund', B5varies: 'uneven income', B5none: 'having no regular income right now', B450to75: 'this being most of your savings', B4gt75: 'this being most of your savings' },
  G1: "Since you need all of it within two years, Penguru won't build a stock mix for this money.",
  gate: 'Until {gate} is sorted out, Penguru keeps the suggestion on the careful side.',
};
// Experienced viewers: a one-time card of shortcuts that fill the box (they never send by themselves).
export const SHORTCUTS = { text: 'Shortcuts: tap one to put it in the box, then edit and send.', chips: ['25 years, $50k + $500 a month, high risk, salaried', 'add XEQT', 'hedged US, no emerging markets, low fees', 'actually, my horizon is 10 years'] };
// Soft progress for beginners instead of "Step 3 of 9".
export const PROGRESS = { many: 'A few more questions', two: 'Two more questions', one: 'Last question before your result', optional: 'Optional' };

// Term answers at three depths (E1). Beginners: the glossary sentence plus an everyday example. Experienced: the rule and
// how Penguru uses it, plus this person's figure when the page has one ({...} slots; a line with a missing slot is left out).
export const TERM_PLAIN = {
  etf: 'Think of it as a basket: one purchase gets you a small piece of many companies or bonds.',
  index_fund: 'It follows a list of companies, like the biggest ones on the Toronto Stock Exchange, instead of someone picking them.',
  mer: 'You never pay it as a bill: it comes out of the fund a little at a time.',
  volatility: 'Think of it as how bumpy the ride is: cash barely moves, while a stock fund has bigger ups and downs.',
  drawdown: 'For example, if $10,000 grows to $12,000 and then falls to $9,000, the drawdown is the 25% fall from $12,000 (an illustration).',
  diversification: 'Like not putting all your eggs in one basket: if one company has a bad year, the others soften the blow.',
  bond: 'You lend money, get paid interest along the way, and get your money back at the end, as long as the borrower can pay.',
  bond_prices_rates: 'Think of a seesaw: when interest rates go up, the price of bonds you already own goes down.',
  duration: 'A bond fund with a longer duration moves more when interest rates change.',
  hedged: 'A change in the US dollar mostly will not affect what you earn from US investments.',
  rebalancing: 'For example, if stocks grow to more of your mix than planned, you sell a little of them and buy bonds to get back to the plan.',
  risk_tolerance: 'It is about how you feel when your balance drops.',
  risk_capacity: 'It is about how much a drop would actually affect your life, whatever you feel about it.',
  correlation: 'If two funds usually rise and fall together, holding both spreads your risk less.',
  sharpe: 'In plain terms: how much extra return you get for each bit of bumpiness.',
  equilibrium_return: 'Penguru starts from what the whole market seems to expect, rather than from whatever did well lately.',
  resampling: 'Like asking the same question many times with slightly different data and averaging the answers.',
  aum: 'A bigger fund is usually cheaper to trade and less likely to close.',
  spread: 'It is a small hidden cost each time you buy or sell; for large, popular ETFs it is usually tiny.',
  reit: 'A REIT fund lets you own a slice of many buildings without buying property.',
  emerging_markets: 'These markets can grow faster, and they usually swing more.',
  inflation: 'If prices rise 3% this year, $100 buys about what $97 bought last year (an illustration).',
  leverage: 'They are built for short-term trading, and Penguru never adds them to a mix.',
  covered_call: 'You get more income now, but if the market jumps, you keep less of the rise.',
  asset_class: 'Stocks, bonds and cash are the main ones, and each behaves differently.',
  tbill_hisa: 'It is the steadiest part of a mix, a bit like a savings account.',
  hypothetical: 'It shows what the rules would have done, not what anyone actually earned.',
};
export const TERM_DEEP = {
  etf: { text: "Penguru's universe is Canadian-listed ETFs in Canadian dollars. To be added, a fund needs 3 years of price history, $20 million in assets, regular trading and no leverage." },
  mer: { text: "The MER covers the management fee, operating costs and sales taxes; trading costs and the bid-ask spread are extra. Penguru subtracts each fund's MER from its planning return.", fig: 'Your mix: {wmer} a year on average, about {fee} a year.' },
  volatility: { text: "The annualized standard deviation of monthly returns. Each risk level (1 to 5) targets a share of the stock market's volatility: level 1 about 20%, up to about all of it at level 5.", fig: 'Your mix: {vol} a year (target {target}; stock-market reference {mkt}).' },
  drawdown: { text: 'The fall from a peak to the following low.', fig: "Today's mix in the {worst}: {worstRet}." },
  diversification: { text: 'Risk contribution shows where the ups and downs really come from, which can differ from where the money sits.', fig: 'Your mix: {topSym} is {topW} of the money and {topRs} of the risk.' },
  bond_prices_rates: { text: 'Roughly, price change = minus duration times the change in yield: a 1-point rise in rates costs a duration-7 fund about 7% (an illustration).' },
  duration: { text: 'Price sensitivity to yields: price change is roughly minus duration times the change in yield. Short-term bond funds have low duration; aggregate funds more.' },
  hedged: { text: 'Hedging uses currency forwards to remove most of the Canadian-US dollar effect, at a small cost. It changes the return series, so volatility and risk shares change too.' },
  rebalancing: { text: 'Markets move a mix away from its targets; calendar or threshold rebalancing trades back. The weights shown are targets, not trades.' },
  risk_tolerance: { text: "Penguru's tolerance is the average of the levels your risk answers map to, rounded down, and one lower when three or more answers spread by 3 or more levels.", fig: 'Yours: level {tol}.' },
  risk_capacity: { text: "Penguru's capacity comes from horizon points, minus one step per cushion (uneven income, most of your savings, a partial emergency fund), at most two.", fig: 'Yours: level {cap}.' },
  correlation: { text: 'The correlation of monthly returns. Penguru flags pairs above 0.97 as near-duplicates that add little diversification.' },
  sharpe: { text: '(Expected return minus the cash rate) divided by volatility. Penguru does not maximize it; it targets a volatility per level.', fig: 'On equilibrium returns your mix is about {sharpe}: ({model} minus {rf}) divided by {vol}.' },
  equilibrium_return: { text: 'The weights use returns implied by a reference mix instead of past returns; projections use published planning assumptions after fees.', fig: 'Your mix: equilibrium return {model} a year; planning return {plan} a year.' },
  resampling: { text: 'The weights are averaged over bootstrap re-estimates of the inputs; each weight band is the 5th to 95th percentile across the draws.', fig: "Your mix: {nboot} draws; the largest fund's band is {band}." },
  tracking_error: { text: 'The annualized standard deviation of the return gap against a reference portfolio.' },
  aum: { text: 'Screen: at least $20 million; "Larger, established funds only" raises it to $250 million.' },
  spread: { text: 'Penguru warns when a fund trades less than about $100,000 a day in Canada; use limit orders there.' },
  leverage: { text: "Daily-reset 2x or -1x funds compound daily returns, so over a year they can differ a lot from 2x the index. Penguru's screen excludes them and always shows a risk note when a fund uses leverage or derivatives." },
  covered_call: { text: 'Selling call options adds option premium as income and caps part of the upside; Penguru flags these funds with the derivatives note.' },
};
