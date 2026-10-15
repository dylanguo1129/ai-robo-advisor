/* The words the guided page uses besides the engine's own (questions, options, glossary and disclosures come from
 * data/core.json, written by robokit/profile.py and robokit/glossary.py). Everything here is fixed text the team can
 * review: why each question is asked, a longer "learn more", short acknowledgements, answers to common questions, and a
 * few extra terms. No numbers live here except illustrations marked as such; the page fills real figures from the engine.
 * Plain ES module, no DOM, so web/test_converse.mjs can check it under Node. Canadian English. */

// The conversation script's opening line and its advice-boundary redirect, word for word where the script fixes them.
export const OPENING = "Hi, I'm Robo-Kit. I'll ask a few questions about your goals to suggest a mix of ETFs for your portfolio. I'll explain the reasoning behind each choice in plain language as we go, and you can ask questions whenever you like. Let's start:";
export const ADVICE_REDIRECT = "I can't tell you whether to buy at any specific time, as I am not a licensed advisor. What I can do is provide information about the ETFs and show how each one fits the portfolio we have built together.";
export const PAST_PERFORMANCE = 'Past performance is not reflective of future performance.';
export const OWN_DECISION = 'I understand that Robo-Kit is an educational tool, not a registered advisor, and that any investment decision I make is my own.';
export const SUPPORT = {
  money: 'That sounds stressful. Before investing, it can help to talk it through with someone independent: the Financial Consumer Agency of Canada (canada.ca/en/financial-consumer-agency.html) and non-profit credit counselling (creditcounsellingcanada.ca) are free places to start.',
  crisis: 'I am sorry you are going through this. If you are thinking about harming yourself, please call or text 988 (Canada and US) to reach someone now. The investing questions can wait.',
};

// Explanation depth, from the calibration question (the script's step 00). It never changes the risk disclosure.
export const DEPTH = { novice: 'novice', some: 'some', expert: 'expert' };
export const CALIBRATION = {
  id: 'EXP', text: 'How much do you already know about ETFs?',
  options: [
    { value: 'novice', text: 'Nothing yet: explain as we go' },
    { value: 'some', text: 'Some basics' },
    { value: 'expert', text: 'I know this well: keep it brief' },
  ],
};

// Why each step is asked: one or two plain sentences, shown under the question for beginners and on "Why we ask".
export const WHY = {
  EXP: 'This only sets how much I explain along the way. It never changes your risk level or the math.',
  A1: 'Your goal shapes the examples I use. It does not change the math by itself.',
  B1: 'Time is the biggest factor in how many ups and downs your money can absorb: money needed soon has less time to recover from a drop.',
  B2: 'Taking money out a bit at a time leaves the rest invested for longer, so it can carry a little more risk than money you need all at once.',
  BASICS: 'These are the "basics before investing" checks. Without an emergency fund, or with expensive debt, a market drop could force you to sell at a bad time, so Robo-Kit keeps the suggested level at 2 or below until they are in place.',
  MONEY: 'Every number from here on is shown in your own dollars. A monthly amount is used only in the projections; it does not change your risk level.',
  B5: 'A steady income means you are less likely to need this money in a bad year, so your situation can absorb a bit more risk.',
  C0: 'How you see yourself is a good start. Next I will check it against how you might react to a real drop, because the two often differ.',
  C2: 'People often feel braver about risk than they act in a real downturn. Your likely reaction tells me more than a label.',
  C1: 'Each card is a different mix, shown in your dollars after one year. Wider ranges come with bigger ups and downs. Pick the range you could live with.',
  B4: 'If this money is most of what you have, a loss would hurt more, so the suggestion is a little more careful.',
  C3: 'The same idea over ten years. In these simulations riskier mixes end higher on average, but not every time, and the spread between a poor and a good outcome is wider.',
  C4: 'This tells me which mistake you would regret more: losing money, or missing out on growth.',
  PREFS: 'Optional. Your preferences narrow which ETFs go on your shortlist. They do not change your risk level.',
  TICKER: 'Optional. If you already have a fund in mind, I will add it to your shortlist and tell you how it fits.',
  SHORTLIST: 'These are the funds the optimizer will weigh. Removing one leaves it out; adding one includes it as your own pick.',
};

// "Learn more" for each step: a little longer, with the idea behind it. Shown on request (or by default for beginners).
export const LEARN = {
  EXP: 'There are no wrong answers. If you pick "Nothing yet," I define each new word the first time it comes up and add short notes as we go. If you pick "I know this well," I keep things brief and show more controls up front. Everyone gets the same questions and the same math.',
  A1: 'Goals usually differ in two ways: when you will need the money, and whether you will take it out all at once or bit by bit. The next questions ask exactly that. If you are just learning, that is a great reason to be here: we will build a practice mix you can explore, and nothing here buys anything.',
  B1: 'Think of the year you expect to start using this money, not the year you stop. For retirement savings that is roughly the year you retire. If you are not sure, a rough guess is fine; you can change it later.',
  B2: '"All at once" fits a home down payment or a big purchase. "Over several years" fits retirement income or tuition paid term by term. If you have no plan yet, "Not sure yet" is a fine answer.',
  BASICS: 'An emergency fund is money you can reach quickly, usually 3 to 6 months of regular expenses, kept somewhere safe like a savings account. High-interest debt means balances like credit cards that charge around 20% a year: paying those off is a guaranteed "return" that investing rarely beats.',
  MONEY: 'Use any amount: this is a model, and nothing is invested. If you plan to add money regularly, the monthly amount shows how that could build up over time.',
  B5: 'Steady income, like a salary or a pension, means a bad year in the markets is less likely to force you to sell. Freelance, commission or seasonal work counts as "varies a lot."',
  C0: 'Low means you would rather keep things steady even if growth is slow. Medium means some ups and downs are fine. High means you can live with big swings for more growth. Robo-Kit treats these as levels 2, 3 and 4.',
  C2: 'In 2008 many stock markets fell by about half over many months and took years to recover; in early 2020 they fell about a third in a few weeks and recovered within months. People who sold near the bottom locked in the loss. There is no right answer here; an honest one helps most. ' + 'Past performance is not reflective of future performance.',
  C1: 'Read each card as "a bad-ish year" on the left and "a good year" on the right; in 8 of 10 simulated years the result lands between them. The grey tick is what you put in. The cards further right have higher upsides but also lower lows. Note the differences across the low and high points: that gap is the risk you take on.',
  B4: 'Add up your savings and investments (bank accounts, TFSA, RRSP and so on) and compare them with the amount you are investing here. If you are not sure, you can skip this question.',
  C3: 'Each card shows where 8 of 10 simulated ten-year outcomes land for that mix. In these simulations riskier mixes end higher on average, but not every time, and the range between a poor and a good outcome is much wider. Pick the range you would be comfortable ending up anywhere inside.',
  C4: 'Some people are bothered most by seeing a loss; others by watching a rally pass them by. Both are normal.',
  PREFS: 'If you care about a theme (such as technology or dividends), I look for a low-cost, eligible ETF for it and add it to your shortlist as your own pick, up to the limit your level allows. If you want to avoid something, I leave that fund out. Lowest-cost swaps each default fund for the cheapest fund of the same kind. Hedging removes most of the effect of the US dollar on your US stocks.',
  TICKER: 'Type a ticker such as VFV or XEQT. Robo-Kit only adds funds that pass its screen (enough history, enough assets, no leverage), and tells you why when one does not.',
  SHORTLIST: 'The optimizer weighs the shortlist so the mix matches your risk level. A fund can end up at zero if it does not help at that level. Your own picks are limited to 10% of the mix at levels 1 and 2, 20% at level 3 and 30% at levels 4 and 5.',
};

// Short acknowledgements after notable answers. {depth} decides whether they show: 'all' for every depth.
export const ACK = {
  A1: {
    learning: 'Great place to start. We will build a practice mix you can explore and change; nothing here buys anything.',
    retirement: 'Retirement it is. The next questions are about when you would start using the money.',
    home: 'Saving for a home. Timing matters a lot here, so the next question is about when you need it.',
    education: 'Education savings. Tuition is usually paid over a few years, which matters for the next questions.',
    income: 'Income you can spend now. That usually means taking money out regularly, which I will ask about next.',
    wealth: 'Building wealth with no fixed date. That usually means a long horizon.',
  },
  B1: { lt2: 'Money needed within two years has little time to recover from a drop, so the suggestion will be careful.' },
  A2: { no: 'Thanks for being straightforward. An emergency fund usually comes first, so Robo-Kit keeps the level at 2 or below for now.', partly: 'A partial emergency fund is a good start; the suggestion will be a step more careful until it is complete.' },
  A3: { lot: 'Paying down high-interest debt often beats investing, so Robo-Kit keeps the level at 2 or below for now.' },
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
  C0: ['What is risk?', 'What do the levels mean?'],
  C2: ['Has the market really dropped like that?', 'What would most people do?'],
  C1: ['What do these numbers mean?', 'Why are some ranges wider?'],
  B4: ["What if I don't know?", 'Why does this matter?'],
  C3: ['What do these numbers mean?', 'What is a 2008-style crisis?'],
  C4: ['Why do you ask this?'],
  PREFS: ['What is a theme?', 'What does hedged mean?'],
  TICKER: ['What is a ticker?', 'Can I add any ETF?'],
  SHORTLIST: ['Why these funds?', 'Can a fund end up at zero?'],
  MIX: ['What does volatility mean?', 'Why is there so much in bonds?', 'How do I buy an ETF?'],
};

// Words to define the first time they come up (beyond the engine's glossary in core.json).
export const TERMS = {
  stock: { term: 'Stock (equity)', definition: 'A small share of ownership in a company. Stocks can grow the most over time and also fall the most.', match: /\bstocks?\b|\bequit(?:y|ies)\b/i },
  portfolio: { term: 'Portfolio', definition: 'All your investments taken together, here the mix of ETFs.', match: /\bportfolios?\b/i },
  emergency_fund: { term: 'Emergency fund', definition: 'Money set aside for surprises, usually 3 to 6 months of expenses, kept somewhere safe and easy to reach.', match: /\bemergency (?:fund|savings)\b/i },
  horizon: { term: 'Time horizon', definition: 'How long until you need the money. Longer horizons can ride out more ups and downs.', match: /\b(?:time )?horizon\b/i },
  risk_level: { term: 'Risk level', definition: "Robo-Kit's scale from 1 (Conservative) to 5 (Aggressive growth). Each level aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80% and level 5 about all of it.", match: /\brisk level\b/i },
  ticker: { term: 'Ticker', definition: 'The short code a fund trades under, such as VFV or XIC.', match: /\btickers?\b/i },
  shortlist: { term: 'Shortlist', definition: 'The funds the optimizer may use for your mix.', match: /\bshortlist\b/i },
  optimizer: { term: 'Optimizer', definition: "The calculation that sets each fund's weight so the mix matches your risk level.", match: /\boptimi[sz]er\b/i },
  active: { term: 'Active fund', definition: 'A fund whose managers choose the investments by judgement, instead of copying an index. Fees are usually higher.', match: /\bactive (?:funds?|etfs?|management|strategy)\b|\bactive or factor\b/i },
  factor: { term: 'Factor (smart-beta) fund', definition: 'An index fund that follows a rule, such as cheaper companies (value) or recent winners (momentum), instead of company size alone.', match: /\bfactor(?: funds?| etfs?)?\b|\bsmart[- ]beta\b/i },
  range: { term: 'Range (8 in 10)', definition: 'The span where 8 of 10 simulated outcomes land: the low end is a bad-ish result, the high end a good one.', match: /\b8 (?:years )?(?:out )?(?:of|in) 10\b/i },
};
// Engine glossary keys worth linking in text, with the words that name them.
export const GLOSSARY_MATCH = {
  etf: /\bETFs?\b/, mer: /\bMERs?\b|\bfees?\b/i, volatility: /\bvolatility\b/i, bond: /\bbonds?\b/i, diversification: /\bdiversif\w*/i,
  hedged: /\bhedg\w*/i, reit: /\bREITs?\b/i, emerging_markets: /\bemerging[- ]markets?\b/i, drawdown: /\bdrawdowns?\b/i,
  index_fund: /\bindex funds?\b/i, asset_class: /\basset class(?:es)?\b/i, rebalancing: /\brebalanc\w*/i, leverage: /\bleverag\w*/i,
  inflation: /\binflation\b/i, tfsa_rrsp: /\bTFSA\b|\bRRSP\b/, hypothetical: /\bhypothetical\b/i, risk_tolerance: /\brisk tolerance\b/i,
  risk_capacity: /\brisk capacity\b|\bcapacity\b/i, tbill_hisa: /\bhigh[- ]interest savings\b|\bcash ETF\b/i, yield: /\byields?\b/i,
};

// Answers to common questions, matched by pattern (first match wins). {level} etc. are filled by the page.
export const FAQ = [
  { re: /\bdon'?t have a goal\b|\bno goal\b|\bnot sure (?:what|about) (?:my|the) goal/i, a: 'That is fine. Pick "Building wealth, no fixed date" or "I\'m just learning" and we will build a practice mix you can explore. You can change the goal at any time.' },
  { re: /\bwhat does "?all at once"? mean\b/i, a: '"All at once" means you plan to take the whole amount out in one go, for example a home down payment. "Over several years" means you would take it out bit by bit, like retirement income or tuition paid each term.' },
  { re: /\bwhat counts as (?:high[- ]interest|expensive) debt\b/i, a: 'Usually balances that charge around 10% a year or more and that you carry from month to month: credit cards, store cards, payday loans. A mortgage or a low-rate student loan does not usually count.' },
  { re: /\bwhat counts as (?:a )?steady income\b/i, a: 'A salary, a pension or other regular payments you can count on. Freelance, commission, seasonal or gig work counts as "varies a lot," and having no regular income right now is its own answer.' },
  { re: /^what is risk\b|\bwhat does risk mean\b/i, a: 'Here, risk means how much the value of your money can swing up and down, and how far it could fall before it recovers. More risk usually comes with more growth over long periods, but also bigger drops along the way.' },
  { re: /\bwhat do these numbers mean\b|\bhow do i read (?:these|the) cards\b/i, a: '__CARDS__' },
  { re: /\bwhy are some ranges wider\b|\bwhy (?:is|are) (?:the )?ranges? (?:wider|different)\b/i, a: 'Mixes with more stocks swing more, so their good outcomes are better and their bad ones worse: the range is wider. Mixes with more bonds and cash move less, so their range is narrower.' },
  { re: /\bwhat is a 2008[- ]style crisis\b|\bwhat happened in 2008\b/i, a: 'In 2008 banks failed, credit froze and stock markets fell by about half from peak to bottom over many months; it took years to recover. Robo-Kit replays that period on a mix to show how much it could have fallen. ' + 'Past performance is not reflective of future performance.' },
  { re: /\bcan i add any etf\b|\bcan i (?:add|pick|choose) (?:my own|any) (?:etf|fund)/i, a: 'Most Canadian-listed ETFs, yes. Robo-Kit only adds funds that pass its screen: enough price history (3 years), enough assets ($20 million), regular trading, and no leverage. If a fund does not pass, it says why.' },
  { re: /\b(is|are) (this|these|it|any of (?:this|it))\b.*\b(real|invested|actual)\b|\breal (?:money|investing)\b|\bany of (?:this|it) invested\b/i, a: 'No. Robo-Kit is a model: nothing is bought, sold or stored, and no account is opened. It shows what a mix could look like and why.' },
  { re: /\bhow (?:do|can|would) i (?:actually )?(?:buy|purchase|get|invest in)\b|\bwhere (?:do|can) i buy\b/i, a: 'ETFs are bought like shares, through a brokerage account at a bank or an online broker, often inside a TFSA or RRSP. Robo-Kit does not recommend a broker or place trades. Before buying any ETF, read its ETF Facts document on the issuer\'s website.' },
  { re: /\bcan i lose\b|\blose (?:all|everything|my money)\b|\bis (?:it|this) (?:safe|risky)\b|\bguarantee/i, a: 'Yes, investments can lose value, and nothing here is guaranteed. That is why Robo-Kit shows a bad year (about 1 in 20) and a 2008 replay in your own dollars next to every mix, so you can judge whether you could live with it.' },
  { re: /\bhow much should i (?:invest|start|put)\b|\bhow much (?:money )?(?:do i need|to start)\b/i, a: 'There is no set amount; many brokers let you start small. A common order of steps is: an emergency fund first, then paying off high-interest debt, then investing money you will not need soon. Robo-Kit works with any amount you type.' },
  { re: /\b(?:what|how) (?:do|does|did) (?:the )?(?:risk )?levels?\b|\bwhat (?:is|does) (?:a |my )?(?:risk )?level\b|\blevel \d means?\b/i, a: "Robo-Kit's levels run from 1 (Conservative) to 5 (Aggressive growth). Each aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80%, level 5 about all of it. Higher levels usually hold more stocks, so they can grow more but also fall more." },
  { re: /\bhow (?:was|is|did) (?:this|my|the) (?:mix|portfolio|level)\b.*\b(?:chosen|calculated|picked|made|work)|\bhow does (?:this|it|robo-kit) work\b|\bwhy (?:this|these) (?:mix|funds?)\b/i, a: 'Your answers give two scores: how much risk your situation can absorb (time, savings, income) and how much you are comfortable with. The suggestion is the lower of the two. The optimizer then weighs one low-cost index fund per kind of investment so the mix matches that level. Every step is shown, and you can change any answer.' },
  { re: /\bwhat (?:if|happens if) (?:the )?market(?:s)? (?:crash|drop|fall)|\bcrash\b|\brecession\b/i, a: 'Markets do fall, sometimes sharply. Robo-Kit replays past crises (2008, 2020, 2022 and others) on today\'s mix so you can see the size of a drop in your dollars. After past crises diversified mixes recovered, over months in 2020 and years in 2008. ' + 'Past performance is not reflective of future performance.' },
  { re: /\bwhy (?:do|did) you (?:ask|need)\b|\bwhy (?:this|that) question\b|\bwhat(?:'s| is) the point\b/i, a: '__WHY__' },
  { re: /\bwhat (?:if|happens if) i(?:'m| am)? (?:not sure|don't know|do not know)\b|\bi(?:'m| am) not sure\b|\bno idea\b/i, a: '__UNSURE__' },
  { re: /\b(?:do|does) (?:you|robo-kit|this) (?:store|save|keep|collect)\b|\bprivacy\b|\bmy data\b/i, a: 'Nothing you type is stored or sent anywhere by Robo-Kit, and it never asks for your name, accounts or contact details. Closing the page clears your answers.' },
  { re: /\btax(?:es)?\b|\bTFSA\b|\bRRSP\b|\bFHSA\b|\bRESP\b/i, a: 'TFSAs, RRSPs, FHSAs and RESPs are Canadian accounts with tax benefits; ETFs can be held inside them. Which account fits you depends on your income and plans, which a tax professional can advise on. Robo-Kit does not give tax advice.' },
  { re: /\brebalanc|\bhow often\b.*\b(?:check|change|adjust)/i, a: 'Markets move a mix away from its targets over time. Rebalancing means trading back to the targets, for example once or twice a year or when a fund drifts more than a few points. Robo-Kit shows the targets; when and whether to rebalance is your decision.' },
  { re: /\bwhat(?:'s| is) a ticker\b/i, a: 'A ticker is the short code a fund trades under, like VFV or XIC. You can type one at any time to add that fund to your shortlist.' },
  { re: /\bwhat(?:'s| is) a theme\b/i, a: 'A theme is a focus beyond the broad market, such as technology, dividends, clean energy or banks. Theme funds hold fewer companies, so they can swing more than a broad index fund.' },
  { re: /\bcan a fund end up at zero\b|\bwhy (?:is|did) .* (?:0|zero)%/i, a: 'Yes. The optimizer only gives a fund weight if it helps the mix reach your risk level efficiently; at some levels a fund adds nothing that the others do not already cover.' },
  { re: /\bwhy (?:is there )?so much (?:in )?bonds?\b|\bwhy bonds\b/i, a: 'Bonds usually move less than stocks and often hold up when stocks fall, so they steady a mix. The lower the risk level, the more of the mix sits in bonds and cash.' },
  { re: /\bwhat (?:would|do) most people (?:do|choose|pick)\b/i, a: 'There is no "normal" answer, and Robo-Kit does not compare you with anyone. What matters is how you would actually feel and act; an honest guess is the best answer.' },
  { re: /\bhas the market (?:really|ever) dropped\b|\bhas (?:that|this) (?:really )?happened\b/i, a: 'Yes. In 2008 broad stock markets fell about half from peak to bottom, and in early 2020 they fell about a third in a few weeks. Both later recovered, over years in 2008\'s case. ' + 'Past performance is not reflective of future performance.' },
];

// What the market-context readings are, for "What do these mean?": what each measures, never what it implies.
export const CONTEXT_LEARN = 'The VIX measures how big the swings in US stocks are expected to be over the next month; the geopolitical risk index counts newspaper coverage of wars, threats and terrorism. Both describe the mood today. Neither is a timing signal, and Robo-Kit never changes a mix because of them.';

// Where the market-context readings come from (the data scripts in robokit/data/context.py).
export const CONTEXT_SOURCES = {
  vix: { name: 'Yahoo Finance (^VIX)', url: 'https://finance.yahoo.com/quote/%5EVIX/' },
  gpr: { name: 'Caldara and Iacoviello', url: 'https://www.matteoiacoviello.com/gpr.htm' },
  epu_us: { name: 'Economic Policy Uncertainty', url: 'https://www.policyuncertainty.com/' },
  epu_ca: { name: 'Economic Policy Uncertainty', url: 'https://www.policyuncertainty.com/' },
};
export const LEVELS_LEARN = "Each level aims for a set share of the stock market's ups and downs: level 1 about 20%, level 2 about 40%, level 3 about 60%, level 4 about 80%, level 5 about all of it. Higher levels usually hold more stocks, so they can grow more but also fall more. The suggestion is the lower of what your situation can absorb and what you said you are comfortable with.";

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
