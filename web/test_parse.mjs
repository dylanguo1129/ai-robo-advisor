// Cases for web/parse.js (the reader for amounts, monthly flows and first messages). Run: node web/test_parse.mjs
import { parseAmount, parseMonthly, parseOpener, isQuestion, BUILD_RX, routeText, matchTerm, stem, wordPattern, prefixPattern, asksQuestion } from './parse.js';

let bad = 0;
const eq = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}: ${JSON.stringify(got)}${ok ? '' : ` (want ${JSON.stringify(want)})`}`);
};

eq('amount 50k', parseAmount('50k'), 50000);
eq('amount $1,500', parseAmount('$1,500'), 1500);
eq('amount 1.5 million', parseAmount('1.5 million'), 1500000);
eq('amount negative is not an amount', parseAmount('-500'), null);
eq('amount a pasted run of digits is not an amount', parseAmount('9'.repeat(400)), null);
eq('amount 50 billion is still an amount', parseAmount('50000000000'), 50000000000);

eq('monthly empty', parseMonthly(''), 0);
eq('monthly 500/month', parseMonthly('500/month'), 500);
eq('monthly $500 a month', parseMonthly('$500 a month'), 500);
eq('monthly -1500', parseMonthly('-1500'), -1500);
eq('monthly unicode minus', parseMonthly('−1,500'), -1500);
eq('monthly take out', parseMonthly('take out 1500'), -1500);
eq('monthly nonsense', parseMonthly('lots'), null);

eq('opener 401k', parseOpener('I have 25k in my 401k'), { market: 'US', amount: 25000 });
eq('opener salary', parseOpener('I earn 90k a year and have 15k saved'), { amount: 15000 });
eq('opener take out', parseOpener('Retired in Ottawa with $300,000, I want to take out -1500 a month'), { market: 'CA', goal: 'retirement', monthly: -1500, amount: 300000 });
eq('opener 401k is not retired', parseOpener('I have 25k in my 401k').retiredNow, undefined);
eq('opener withdraw verb', parseOpener('I have 400k and need to withdraw 2000 a month'), { monthly: -2000, amount: 400000 });
eq('opener need a month is taking out', parseOpener('I am retired with 400k and need $2,000 a month').monthly, -2000);
eq('opener need to save is adding', parseOpener('I have 20k and need to save 500 a month').monthly, 500);
eq('monthly need 1500', parseMonthly('need 1500'), -1500);
eq('opener "us" is a pronoun', parseOpener('tell us about XEQT').market, undefined);
eq('opener help us pick', parseOpener('help us pick a dividend etf with 20k').market, undefined);
eq('opener the US', parseOpener('I live in the US and have 50k').market, 'US');
eq('opener U.S.', parseOpener('U.S. stocks with 20k').market, 'US');
eq('question whats', isQuestion('whats an etf'), true);
eq('opener number in a link is not an amount', parseOpener('https://www.example.com/etf/product/309480 is this fund ok?').amount, undefined);
eq('opener tickers and flows', parseOpener('qqq schd bito, max risk. 5k + 300/mo'), { monthly: 300, amount: 5000 });
eq('opener retired now', parseOpener("I'm retired and have $300,000 in my RRIF. I need to take out $1,500 a month.").retiredNow, true);
eq('opener year is not money', parseOpener('I want to retire in 2045 with a house'), { goal: 'retirement' });
eq('opener two amounts, none marked', parseOpener('Between 20000 and 30000 CAD'), { market: 'CA', amountChoices: [20000, 30000] });
eq('opener fee question', parseOpener('Is a fee of 0.2% on 1,500 a year a lot?'), {});

eq('question how', isQuestion('How does my mix compare with XEQT, which I hold'), true);
eq('statement', isQuestion('I have 50k CAD for retirement'), false);
eq('build en', BUILD_RX.test('can you build me a portfolio'), true);
eq('compare mix is not build', BUILD_RX.test('compare my mix with XEQT'), false);

// the no-AI router
const route = (t) => { const r = routeText(t); return r.kind === 'term' ? `term:${r.key}` : r.kind === 'context' || r.kind === 'switch' ? r.kind : `search:${r.words.join(' ')}`; };
const ROUTES = [
  ['What is an ETF?', 'term:etf'], ['what are etfs', 'term:etf'], ['whats an etf', 'term:etf'], ['how do etfs work', 'term:etf'], ['etfs', 'term:etf'],
  ['tell me about dividend etfs', 'search:dividend'], ['what are some dividend etfs', 'search:dividend'], ['explain low fee etfs', 'term:mer'],
  ["what's the cheapest S&P 500 ETF", 'search:s&p 500'], ['tell me about gold etfs', 'search:gold'], ['tech etf', 'search:tech'],
  ['corporate bond etf', 'search:corporate bond'], ['canadian bonds etf', 'search:canadian bonds'], ['reits in canada', 'search:reits canada'],
  ['low volatility etf', 'search:low volatility'], ['hedged s&p 500 etf', 'search:hedged s&p 500'], ['total stock market etf', 'search:total stock market'],
  ['money market fund', 'search:money market'], ['emerging markets etf', 'search:emerging markets'], ['covered call etf', 'search:covered call'],
  ['what is a covered call etf?', 'term:covered_call'], ['emerging markets', 'term:emerging_markets'], ['reits', 'term:reit'], ['what is a REIT?', 'term:reit'],
  ['how do bonds work', 'term:bond'], ['what is a bond etf?', 'term:bond'], ['what is volatility', 'term:volatility'], ['is a 1% fee on $100,000 a lot?', 'term:mer'],
  ['should I use my TFSA', 'term:tfsa_rrsp'], ['how do bond prices react to interest rates', 'term:bond_prices_rates'], ['inflation', 'term:inflation'],
  ['how are markets?', 'context'], ["what's going on in the markets", 'context'], ['market news', 'context'], ['tariffs', 'context'], ['inflation news', 'context'],
  ['is the stock market crashing?', 'context'], ['hi', 'search:'], ['thanks!', 'search:'], ['sure', 'search:'], ['ty', 'search:'], ['hello there my friend', 'search:friend'],
  ['can I lose money?', 'search:lose money'], ['money market', 'search:money market'], ['bond market', 'search:bond market'], ['how are the markets', 'context'], ['vanguard', 'search:vanguard'], ['software etf', 'search:software'],
];
for (const [t, want] of ROUTES) eq(`route ${t}`, route(t), want);
eq('term loose: currency hedged ETF', matchTerm('currency hedged ETF', { loose: true }), 'hedged');
eq('term loose: leveraged and inverse ETFs', matchTerm('leveraged and inverse ETFs', { loose: true }), 'leverage');
eq('term loose: volatility of a portfolio', matchTerm('volatility of a portfolio', { loose: true }), 'volatility');
eq('whole words', [['gold', 'Goldman Sachs ETF'], ['gold', 'SPDR Gold Shares'], ['reit', 'Canadian REITs'], ['equity', 'US Equities'], ['morning', 'Morningstar Growth']].map(([w, t]) => wordPattern(w).test(t)), [false, true, true, true, false]);
eq('word starts', [['tech', 'Technology'], ['canad', 'Canada'], ['gold', 'Goldman']].map(([w, t]) => prefixPattern(w).test(t)), [true, true, true]);
eq('route good morning', route('Good morning!'), 'search:');
eq('route a pasted link', route('https://www.example.com/products/etf/239447/very-long-path'), 'search:');
eq('stem plural', ['bonds', 'reits', 'equities', 'indexes', 'gas', 'class'].map(stem), ['bond', 'reit', 'equity', 'index', 'gas', 'class']);
eq('opener lower-case "the us" is the country', parseOpener('i live in the us and have 50k').market, 'US');
eq('opener "us stocks"', parseOpener('us stocks with 20k').market, 'US');
eq('opener "us dividend etfs"', parseOpener('us dividend etfs').market, 'US');
eq('opener "tell us about dividend etfs"', parseOpener('tell us about dividend etfs').market, undefined);

// round 4: questions about ETFs, markets, themes, regions and joined index names
const R4 = [
  ['are etfs safe?', 'term:etf'], ['etf vs mutual fund', 'term:etf'], ['whats the difference between an etf and a mutual fund', 'term:etf'], ['is an etf a good investment', 'term:etf'],
  ['how are etfs taxed', 'term:etf'], ['can etfs go to zero?', 'term:etf'], ['what are some dividend etfs', 'search:dividend'],
  ['total market index', 'search:total market'], ['broad market index', 'search:broad market'], ['what is market cap weighting', 'search:market cap weighting'],
  ['how are the markets doing', 'context'], ['what is the yield curve?', 'context'], ['what is a credit spread?', 'context'], ['interest rates', 'context'],
  ['bank of canada', 'context'], ['the canadian dollar', 'context'], ['bond etfs', 'search:bond'], ['show me bond etfs', 'search:bond'], ['inflation etf', 'search:inflation'],
  ['hedged etfs', 'search:hedged'], ['what is a bond?', 'term:bond'], ['US equity etf', 'search:usregion equity'], ['us dividend etf', 'search:usregion dividend'],
  ['U.S. bonds', 'search:usregion bonds'], ['tell us about bonds', 'term:bond'], ['canadian stocks', 'search:canadian stocks'], ['global x etfs', 'search:globalx'],
  ['S&P500', 'search:s&p 500'], ['sp500 etf', 'search:s&p 500'], ['nasdaq100', 'search:nasdaq 100'], ['what is a HYSA?', 'term:tbill_hisa'],
];
for (const [t, want] of R4) eq(`route ${t}`, route(t), want);
const Q = [['would wait it out', false], ['will need it in 3 years', false], ['should be about 20 years', false], ["can't touch it for 10 years", false],
  ['what does sell some mean?', true], ['should I sell?', true], ['is it safe', true], ['explain this', true], ['when I retire in 25 years', false]];
eq('asks a question', Q.map(([t]) => asksQuestion(t)), Q.map(([, v]) => v));

// round 5: market news statements, the US pronoun, closest matches stay narrow
const R5 = [
  ['markets are down, should i sell?', 'context'], ['markets dropped today', 'context'], ['will the market recover', 'context'], ['bear market', 'context'],
  ['money market', 'search:money market'], ['total market index', 'search:total market'], ['market cap', 'search:market cap'],
  ['show us dividend etfs', 'search:dividend'], ['american stocks', 'search:usregion stocks'], ['u.s. stocks', 'search:usregion stocks'],
  ['us real estate etf', 'search:usregion reit'], ['are etfs good for us', 'term:etf'], ['which market', 'switch'], ['switch market', 'switch'],
  ['change the market to US', 'switch'], ['how are the markets doing', 'context'],
];
for (const [t, want] of R5) eq(`route ${t}`, route(t), want);

console.log(bad ? `${bad} FAILED` : 'all parse cases pass');
process.exit(bad ? 1 : 0);
