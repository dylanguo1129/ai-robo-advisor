// Checks for the guided page's conversation logic (web/converse.js) and fixed words (web/kb.js), under Node.
// Run: node web/test_converse.mjs
import { readFileSync } from 'node:fs';
import * as C from './converse.js';
import * as KB from './kb.js';
import { Market, scoreProfile } from './robokit.js';

const here = new URL('.', import.meta.url);
const core = JSON.parse(readFileSync(new URL('data/core.json', here)));
const M = new Market(core, JSON.parse(readFileSync(new URL('data/ca.json', here))));
const symbols = new Map(); for (const r of M.rows) { symbols.set(r.symbol.toUpperCase(), r.yahoo); symbols.set(r.yahoo.toUpperCase(), r.yahoo); }
let fails = 0, n = 0;
const eq = (name, got, want) => { n++; const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) { fails++; console.log('FAIL', name, '\n   got ', JSON.stringify(got), '\n   want', JSON.stringify(want)); } };
const ok = (name, cond) => { n++; if (!cond) { fails++; console.log('FAIL', name); } };

// advice requests: always the same redirect (the conversation script's one fixed rule)
for (const t of ['Should I buy VFV?', 'what should I do with my money', 'just tell me what to buy', 'Which ETF is the best?', 'is now a good time to invest?', 'will the market crash next year', 'do you recommend XIC', 'what would you buy', 'Is XEQT a good investment?', 'when should I sell', 'What should I actually do?', 'Should I really buy XIC?', 'tell me what I should do', 'whats the smart move here'])
  ok(`advice: ${t}`, C.isAdvice(t));
for (const t of ['what is an ETF?', 'why do you ask', 'how do I buy an ETF', 'what does volatility mean', 'can I lose money?', 'What is XIC?'])
  ok(`not advice: ${t}`, !C.isAdvice(t));
eq('local answer to advice is the redirect', C.localAnswer('should I buy VFV?', { glossary: core.glossary })?.text, KB.ADVICE_REDIRECT);

// horizon in words (the review: "Within 2 years" was not understood)
const H = (t) => C.parseHorizon(t, { year: 2026 });
eq('within 2 years', H('Within 2 years'), { value: 'lt2', sure: true });
eq('in 2 years', H('in 2 years'), { value: '2to4', sure: true });
eq('6 months', H('in 6 months'), { value: 'lt2', sure: true });
eq('retire at 65 aged 35', H("I'm 35 and want to retire at 65"), { value: '20plus', sure: true });
eq('by 2031', H('by 2031'), { value: '5to9', sure: true });
eq('10-15 years', H('10-15 years'), { value: '10to19', sure: true });
eq('a couple of years', H('a couple of years'), { value: '2to4', sure: true });
eq('short term is vague', H("I'm a short term investor"), { value: '2to4', sure: false });
eq('long term is vague', H('long term'), { value: '10to19', sure: false });
eq('no horizon', H('hello'), null);

// other answers typed in words
eq('depth new', C.parseDepth("I'm new to investing"), 'novice');
eq('depth some', C.parseDepth('I know some basics'), 'some');
eq('depth expert', C.parseDepth('I know this well'), 'expert');
eq('goal learning', C.parseGoal('I am just learning'), 'learning');
eq('goal home', C.parseGoal('saving for a down payment'), 'home');
eq('goal retirement', C.parseGoal('for when I retire'), 'retirement');
eq('withdrawal once', C.parseWithdrawal('all at once'), 'once');
eq('withdrawal 3 years', C.parseWithdrawal('over 3 years'), '2to5');
eq('emergency partly', C.parseEmergency('I have some savings'), 'partly');
eq('emergency no', C.parseEmergency('not yet'), 'no');
eq('debt none', C.parseDebt('no debt'), 'no');
eq('debt a lot', C.parseDebt('a lot of credit card debt'), 'lot');
eq('debt bare yes asks', C.parseDebt('yes'), null);
eq('income freelance', C.parseIncome('I freelance so it varies'), 'varies');
eq('income student', C.parseIncome("I'm a student"), 'none');
eq('comfort low', C.parseComfort('low, I am cautious'), 'low');
eq('drop hold', C.parseDrop('I would hold and wait'), 'wait');
eq('drop buy', C.parseDrop('buy the dip'), 'buy');
eq('drop sell some', C.parseDrop('sell some of it'), 'sell_some');
eq('drop unsure', C.parseDrop("I don't know"), 'dont_know');
eq('card third', C.parseCard('the third one'), '3');
eq('card number', C.parseCard('2'), '2');
eq('money both', C.parseStep('MONEY', '$20k and 300 a month'), { B3: 20000, MONTHLY: 300 });
eq('money sentence', C.parseStep('MONEY', 'I can put in 15k'), { B3: 15000 });
eq('money monthly only', C.parseStep('MONEY', '500 a month'), { MONTHLY: 500 });
eq('option by number', C.matchOption(core.questions.find((q) => q.id === 'B5').options, '3'), 'varies');
eq('facts in one go', C.extractFacts('I have $50k for retirement in 25 years, high risk, I am a beginner', { year: 2026 }), { A1: 'retirement', B1: { value: '20plus', sure: true }, B3: 50000, C0: 'high', EXP: 'novice' });

// commands
eq('change risk', C.parseCommand('actually change my risk to high'), { type: 'change', id: 'C0', value: 'high' });
eq('level', C.parseCommand('make it level 4'), { type: 'level', level: 4 });
eq('horizon change', C.parseCommand('I meant 10 years', { year: 2026 }), { type: 'change', id: 'B1', value: '10to19' });
eq('add ticker', C.parseCommand('add xeqt', { symbols }), { type: 'add', tickers: ['XEQT.TO'] });
eq('remove ticker', C.parseCommand('remove VEE', { symbols }), { type: 'remove', tickers: ['VEE.TO'] });
eq('restart', C.parseCommand('start over'), { type: 'restart' });
eq('no command', C.parseCommand('what is a bond?'), null);

// tickers: capitals in running text, words only after "add"; common words are not funds
eq('ticker in text', C.findTickers('I like VFV and XIC', symbols), ['VFV.TO', 'XIC.TO']);
eq('lower case needs loose', C.findTickers('i like vfv', symbols), []);
eq('bond is a word', C.findTickers('what is a bond', symbols, { loose: true }), []);
eq('cash only when asked', C.findTickers('add CASH', symbols, { loose: true, allowCommon: true }), ['CASH.TO']);

// answers without AI
const ctx = { glossary: core.glossary, M, symbols };
ok('term answer', C.localAnswer('what is volatility?', ctx)?.text.startsWith('Volatility:'));
ok('bond is a term, not a fund', C.localAnswer('what is a bond?', ctx)?.kind === 'term');
ok('fund answer', /XIC/.test(C.localAnswer('What is XIC?', ctx)?.text || ''));
const zag = C.localAnswer('Whats an example of a stock in this ETF?', { ...ctx, fund: 'ZAG.TO' });
ok('a bond fund holds no stocks (review item)', /holds no stocks/.test(zag?.text || '') && /Government/.test(zag.text));
ok('faq: is this real', C.localAnswer('is any of this invested?', ctx)?.kind === 'faq');
ok('why we ask', C.localAnswer('why do you ask?', { ...ctx, step: 'B5' })?.text === KB.WHY.B5);
ok('learn more on the open step', C.localAnswer('I want to learn more', { ...ctx, step: 'C1' })?.text === KB.LEARN.C1);
ok('nothing to say about weather', C.localAnswer('what is the weather like', ctx) === null);

// every suggested question has an answer without AI (the review found ten that did not)
for (const [step, qs] of Object.entries(KB.SUGGEST)) for (const q of qs) ok(`suggested question answered: ${step} ${q}`, C.localAnswer(q, { ...ctx, step }) !== null);
for (const t of ['What do you think I should do?', 'Is level 4 right for me?', 'Is this a good portfolio?', 'Is VFV better than XIC?']) ok(`advice: ${t}`, C.isAdvice(t));
for (const t of ['Do you think I should invest?', 'Can you advise me?', 'Is it smart to buy VFV?', 'is it worth buying XEQT', 'should I wait for a crash']) ok(`advice: ${t}`, C.isAdvice(t));
eq('region focus', C.parsePrefs('I would like more emerging markets')?.regions, ['em']);
ok('defines active and factor funds', /judgement/.test(C.localAnswer('what is an active fund?', { glossary: core.glossary })?.text || '') && /rule/.test(C.localAnswer('what is a factor fund?', { glossary: core.glossary })?.text || ''));
ok('context learn-more is neutral', !/followed by higher|returns/i.test(KB.CONTEXT_LEARN));

// fixed words: every step has a reason and a learn-more, every default fund has sourced holdings
for (const id of ['EXP', 'A1', 'B1', 'B2', 'BASICS', 'MONEY', 'B5', 'C0', 'C2', 'C1', 'B4', 'C3', 'C4', 'PREFS', 'TICKER', 'SHORTLIST']) ok(`WHY and LEARN for ${id}`, KB.WHY[id] && KB.LEARN[id]);
for (const [t, h] of Object.entries(KB.HOLDINGS)) ok(`holdings ${t}`, M.fund(t)?.eligible && h.top.length >= 1 && /^https:\/\//.test(h.url) && h.as_of);
eq('ten default funds have holdings', Object.keys(KB.HOLDINGS).length, 10);
const words = JSON.stringify(KB);
ok('Canadian spelling: no "per cent"', !/per cent/i.test(words));
ok('no "best" advice wording', !/\byou should (?:buy|invest)\b/i.test(words));

// the second chance: self-rating against the drop (engine flag)
const P = (a) => scoreProfile(core.questions, { A1: 'wealth', A2: 'yes', A3: 'no', B1: '20plus', ...a });
ok('low vs buy disagree', P({ C0: 'low', C2: 'buy' }).flags.some((f) => f.id === 'F_self_vs_drop'));
ok('medium vs wait agree', !P({ C0: 'medium', C2: 'wait' }).flags.some((f) => f.id === 'F_self_vs_drop'));
ok("don't know never flags", !P({ C0: 'high', C2: 'dont_know' }).flags.some((f) => f.id === 'F_self_vs_drop'));
eq('self-rating levels are the brief three', core.questions.find((q) => q.id === 'C0').options.map((o) => o.level), [2, 3, 4]);

// leverage heads-up and rationale
ok('leverage note', /leverage/.test(C.leverageNote(M.fund('AAPU.TO')) || ''));
ok('no note for an index fund', C.leverageNote(M.fund('XIC.TO')) === null);
ok('rationale for a pick', /You added this yourself/.test(C.rationale({ ticker: 'XEQT.TO' }, { level: 3, picks: ['XEQT.TO'], satCap: 0.2 })));
const rc = C.recap({ lowerOf: true, capacity: 5, tolerance: 3, terms: ['volatility', 'ETF'], badYear: '$9,000' });
ok('recap has covered items and a next step', rc.covered.length >= 2 && /ETF Facts/.test(rc.next));

// from driving the page: amounts with commas, facts read clause by clause, everyday words that are also tickers
eq('money with commas', C.parseStep('MONEY', '$15,000 to start and $500 a month'), { B3: 15000, MONTHLY: 500 });
eq('money in the millions', C.parseStep('MONEY', '1,250,000'), { B3: 1250000 });
eq('change amount with commas', C.parseCommand('change the amount to 15,000')?.value, { B3: 15000 });
eq('comfort and income from their own clauses', C.extractFacts('I want low risk but I have a steady job', { year: 2026 }), { C0: 'low', B5: 'very' });
ok('saving for retirement is not a pension', C.extractFacts('saving for retirement, my income is steady', { year: 2026 }).B5 === 'very');
eq('retired is a pension', C.parseIncome("I'm retired"), 'pension');
ok('retiring in 10 years is not a pension', C.parseIncome('retiring in 10 years') !== 'pension');
for (const t of ['show me my mix', 'is this a good long term plan', 'what does the rate mean', 'I work in tech'])
  eq(`no ticker in: ${t}`, C.findTickers(t, symbols), []);
eq('capitals still count', C.findTickers('What about XEQT and VFV?', symbols), ['XEQT.TO', 'VFV.TO']);
for (const t of ['What is your advice?', 'what do you suggest', 'what would you suggest I buy', 'is it the time to buy?'])
  ok(`advice: ${t}`, C.isAdvice(t));
const inZag = { ...ctx, fund: 'ZAG.TO' };
ok('a term inside a fund answers the term', C.localAnswer('what is volatility?', inZag)?.kind === 'term');
ok('a fund question inside a fund stays on the fund', C.localAnswer('what does it hold?', inZag)?.kind !== 'term');

console.log(fails ? `${fails} of ${n} checks FAILED` : `all ${n} conversation checks pass`);
if (fails) process.exit(1);
