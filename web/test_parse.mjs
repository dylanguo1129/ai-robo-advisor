// Cases for web/parse.js (the reader for amounts, monthly flows and first messages). Run: node web/test_parse.mjs
import { parseAmount, parseMonthly, parseOpener, isQuestion, BUILD_RX } from './parse.js';

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
eq('opener tickers and flows', parseOpener('qqq schd bito, max risk. 5k + 300/mo'), { monthly: 300, amount: 5000 });
eq('opener retired now', parseOpener("I'm retired and have $300,000 in my RRIF. I need to take out $1,500 a month.").retiredNow, true);
eq('opener year is not money', parseOpener('I want to retire in 2045 with a house'), { goal: 'retirement' });
eq('opener two amounts, none marked', parseOpener('Between 20000 and 30000 CAD'), { market: 'CA', amountChoices: [20000, 30000] });
eq('opener fee question', parseOpener('Is a fee of 0.2% on 1,500 a year a lot?'), {});

eq('question how', isQuestion('How does my mix compare with XEQT, which I hold'), true);
eq('statement', isQuestion('I have 50k CAD for retirement'), false);
eq('build en', BUILD_RX.test('can you build me a portfolio'), true);
eq('compare mix is not build', BUILD_RX.test('compare my mix with XEQT'), false);

console.log(bad ? `${bad} FAILED` : 'all parse cases pass');
process.exit(bad ? 1 : 0);
