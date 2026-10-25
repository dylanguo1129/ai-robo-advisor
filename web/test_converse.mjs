// Checks for the guided page's conversation logic (web/converse.js) and fixed words (web/kb.js), under Node.
// Run: node web/test_converse.mjs
import { readFileSync } from 'node:fs';
import * as C from './converse.js';
import * as KB from './kb.js';
import { Market, scoreProfile, lockedCategoryProblem } from './robokit.js';

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
ok('weather gets the scope (E4)', C.localAnswer('what is the weather like', ctx)?.kind === 'scope');

// every suggested question has an answer without AI (the review found ten that did not)
for (const [step, qs] of Object.entries(KB.SUGGEST)) for (const q of qs) ok(`suggested question answered: ${step} ${q}`, C.localAnswer(q, { ...ctx, step }) !== null);
for (const t of ['What do you think I should do?', 'Is level 4 right for me?', 'Is this a good portfolio?', 'Is VFV better than XIC?']) ok(`advice: ${t}`, C.isAdvice(t));
for (const t of ['Do you think I should invest?', 'Can you advise me?', 'Is it smart to buy VFV?', 'is it worth buying XEQT', 'should I wait for a crash']) ok(`advice: ${t}`, C.isAdvice(t));
eq('region focus', C.parsePrefs('I would like more emerging markets')?.regions, ['em']);
ok('defines active and factor funds', /judgement/.test(C.localAnswer('what is an active fund?', { glossary: core.glossary })?.text || '') && /rule/.test(C.localAnswer('what is a factor fund?', { glossary: core.glossary })?.text || ''));
ok('context learn-more is neutral', !/followed by higher|returns/i.test(KB.CONTEXT_LEARN));

// fixed words: every step has a reason and a learn-more, every default fund has sourced holdings
for (const id of ['EXP', 'A1', 'B1', 'B2', 'BASICS', 'MONEY', 'B5', 'C0', 'C2', 'C1', 'B4', 'C3', 'C4', 'PREFS', 'TICKER']) ok(`WHY and LEARN for ${id}`, KB.WHY[id] && KB.LEARN[id]);
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
eq('self-rating levels: low and medium are the brief settings, high reaches the top (3.3.1)', core.questions.find((q) => q.id === 'C0').options.map((o) => o.level), [2, 3, 5]);

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

// v3.2, the team's PRD v3: scope and the ETF-only rule (E4)
for (const t of ['what is the weather tomorrow?', 'write me a poem', 'who won the hockey game last night?']) eq(`scope: ${t}`, C.localAnswer(t, ctx)?.text, KB.SCOPE);
for (const t of ['Can you sum up my situation so far?', 'how do I start?', 'what do you mean by steady?']) ok(`not out of scope: ${t}`, C.localAnswer(t, { ...ctx, step: 'B5' })?.kind !== 'scope');
for (const [t, other] of [['is an ETF better than buying Apple stock?', 'individual stocks'], ['ETFs or bonds?', 'buying bonds directly'], ["what's the difference between an ETF and a mutual fund?", 'mutual funds'], ['ETFs vs GICs', 'GICs']])
  ok(`ETF only: ${t}`, C.localAnswer(t, ctx)?.kind === 'etf_only' && C.localAnswer(t, ctx).text.startsWith(KB.ETF_ONLY(other)));
for (const t of ['what is a GIC?', 'what is a mutual fund?', 'what is a stock?', 'what is an index?', 'what are distributions?']) ok(`defined: ${t}`, ['term', 'faq'].includes(C.localAnswer(t, ctx)?.kind));
ok('a question about the question gets its learn more', C.localAnswer('what does this question mean?', { ...ctx, step: 'C2' })?.text === KB.LEARN.C2);
ok('guarantee inside a fund gets the honest answer', /nothing here is guaranteed/.test(C.localAnswer('is it guaranteed?', { ...ctx, fund: 'ZAG.TO' })?.text || ''));
ok('learn more for the second chance, fine-tune and adjust', KB.LEARN.RECON && KB.LEARN.FT && KB.LEARN.ADJUST);
// tickers that are not in the data (F3)
eq('closest to XEQ', C.closestTickers('XEQ', M.rows)[0], 'XEQT.TO');
eq('closest to VFVV', C.closestTickers('VFVV', M.rows)[0], 'VFV.TO');
eq('ticker-like words', C.tickerLike('SPY and QQQ', symbols), ['SPY', 'QQQ']);
eq('everyday words are not tickers', C.tickerLike('more bonds please', symbols), []);
eq('add an unknown ticker', C.parseCommand('add XEQ', { symbols }), { type: 'add', tickers: [], unknown: ['XEQ'] });
for (const [t, list] of Object.entries(KB.US_LISTED)) for (const c of list.ca) ok(`US ${t}: ${c} is an eligible Canadian fund`, M.fund(symbols.get(c))?.eligible);
// preferences read clause by clause (F2): a "no" applies to its own clause
eq('no active funds', C.parsePrefs('no active funds')?.open, false);
eq('active funds are fine', C.parsePrefs('active funds are fine')?.open, true);
eq('no hedging', C.parsePrefs('no hedging please')?.hedge, false);
eq('unhedged', C.parsePrefs('unhedged only')?.hedge, false);
eq('fee cap', C.parsePrefs('fees under 0.15%')?.maxFee, 0.0015);
eq('fee cap other order', C.parsePrefs('max fee 0.2%')?.maxFee, 0.002);
eq('one region', C.parsePrefs('Canada only')?.only, 'canada');
eq('CAD only', C.parsePrefs('CAD only')?.currency, 'CAD');
eq('no factor', C.parsePrefs('no factor funds')?.noFactor, true);
eq('income is not a dividend preference', C.parsePrefs('my income is steady'), null);
eq('"us" the pronoun is not a region', C.parsePrefs('help us decide'), null);
// leverage and derivatives the data leave blank (C3)
const kind = (s) => C.derivativeKind(M.rows.find((r) => r.symbol === s));
eq('Hamilton Enhanced borrows', kind('HCAL'), 'borrowing');
eq('Harvest Leaders Income sells options', kind('HTA'), 'options');
eq('an index fund uses none', kind('XIC'), null);
eq('a bond fund named Enhanced is not leveraged', kind('FGO'), null);
ok('every derivative fund gets a note', M.rows.filter((r) => r.eligible && C.derivativeKind(r)).every((r) => /regardless of your experience level/.test(C.leverageNote(r))));
// experience: self-identified or inferred, never from a background read as a horizon (F1)
eq('investing for 10 years is experience', C.parseDepth("I've been investing for 10 years"), 'expert');
eq('and not a horizon', C.parseHorizon("I've been investing for 10 years"), null);
eq('just learning is a beginner', C.parseDepth("I'm just learning"), 'novice');
eq('jargon suggests experience', C.inferDepth('what is the sharpe ratio and tracking error?'), 'expert');
eq('a hint, not an answer', C.extractFacts('I want XEQT and VFV, low MER', { symbols }).hints?.EXP, 'expert');
eq('nervous suggests low comfort', C.extractFacts("I'm nervous about losing money").hints?.C0, 'low');
// typed changes to any earlier answer (F4)
eq('change income', C.parseCommand('actually my income varies a lot', { symbols })?.id, 'B5');
eq('change debt', C.parseCommand('actually I have no debt', { symbols })?.value, 'no');
eq('change the drop answer', C.parseCommand('actually I would buy more if it dropped', { symbols })?.value, 'buy');
eq('an amount with a change word', C.parseCommand('actually I meant 40,000', { symbols })?.value, { B3: 40000 });
eq('a salary is not an amount change', C.parseCommand('I make 80k a year', { symbols }), null);
eq('self-identify mid-session', C.parseCommand("I'm a beginner", { symbols })?.value, 'novice');
ok('ok, let us keep going', C.isContinue("ok let's keep going") && C.isContinue('thanks, back to it'));
ok('polite skip', C.isSkip('can I skip this one?'));
// the locked category lists (D2)
eq('a category outside the list', lockedCategoryProblem({ asset_class: 'Equities (US)', region: 'US', strategy: 'Active' }), "category not in the locked list: asset_class 'Equities (US)'");
ok('every fund in the data is inside the lists', M.rows.every((r) => !r.flagged));

// ================================================================== v3.2: open conversation and depth (the spec's Node tests)
// advice: levels and weights asked as a personal decision; flow questions are not advice
for (const t of ['should I go to level 5?', 'should I cut XSP to 25%?', 'is level 5 too risky for me?', 'is 52% stocks a lot for me?', 'should I stay at level 3?']) ok(`advice: ${t}`, C.isAdvice(t));
for (const t of ['should I go back?', 'should I change my answer?', 'is 20 years a lot?', 'I want to go to level 4', 'what does too risky mean', 'should I skip this one?']) ok(`not advice: ${t}`, !C.isAdvice(t));
// the reader: every answer in a message, in any order, never into the wrong question
const RT = (t, pending = null, answers = {}) => C.readTurn(t, { pending, answers, symbols, year: 2026 });
eq('no debt at the basics: debt only', RT('no debt', 'BASICS').facts, { A3: 'no' });
ok('"not sure" is never No', RT('not sure', 'BASICS').facts.A2 == null);
ok('some savings is not a depth', RT('I have some savings but not much', 'EXP').facts.EXP == null);
ok('held for 8 years is not a horizon', RT("I've held XEQT and VFV in my TFSA for 8 years").facts.B1 == null);
ok('never invested is not a horizon', RT('never invested before').facts.B1 == null && C.parseHorizon('never invested before') == null);
eq("don't really know anything", C.selfDepth("I don't really know anything about ETFs"), 'novice');
eq('over 25 years while the period is open', RT('over 25 years', 'B2').facts, { B2: '10plus' });
eq('2 years', RT('2 years', 'B1').facts.B1, '2to4');
eq('long term is two candidates', RT('long term', 'B1').vague.B1?.candidates, ['10to19', '20plus']);
eq('two goals is two candidates', RT('retirement and a house', 'A1').vague.A1?.candidates?.length, 2);
eq('one line, four answers', RT('25 years, $50k, high risk, salaried', 'B1').facts, { B1: '20plus', C0: 'high', B5: 'very', MONEY: { B3: 50000 } });
eq('a story told up front', RT("I'm 30, saving for a condo in about 5 years, I have $15k and no debt").facts, { A1: 'home', B1: '5to9', A3: 'no', MONEY: { B3: 15000 } });
eq('their own words, whitelisted', RT('saving for a condo').words.goal, { np: 'the condo', goal: 'home' });
ok('a correction cue is seen', RT('actually 20 years', 'C0', { B1: '5to9' }).changes[0]?.cue === true);
ok('advice records nothing', Object.keys(RT('should I buy VFV with my 20k?').facts).length === 0);
// the gate: risk answers only from their own card; only option values are recorded
const AD = (id, v, open) => C.admit(id, v, { open, questions: core.questions });
eq('C2 read elsewhere is highlighted', AD('C2', 'wait', 'B1'), 'preselect');
eq('C2 on its own card records', AD('C2', 'wait', 'C2'), 'record');
eq('an explicit self-rating records', AD('C0', 'high', 'B1'), 'record');
eq('a value outside the options is rejected', AD('B1', '7years', 'B1'), 'reject');
ok('every answer the reader can produce is an option value', ['25 years, $50k, high risk, salaried', 'retired with a pension', 'I would sell some', 'no debt, some emergency savings', 'all at once in 3 years'].every((t) => Object.entries(RT(t, 'B1').facts).every(([id, v]) => C.validValue(core.questions, id, v))));
// depth: what people say wins; cues settle the rest; tickers alone never make it expert
for (const [t, d] of [["I'm new to this", 'novice'], ['keep it brief', 'expert'], ["I've been investing for 10 years", 'expert'], ['I know the basics', 'some'], ["new to ETFs but I've traded stocks for years", 'some'], ['explain it more simply', 'novice'], ['I work in finance', 'expert']]) eq(`self: ${t}`, C.selfDepth(t), d);
eq('tickers alone stay standard', C.classifyDepth(C.depthCues('XEQT VFV ZAG XIC', { symbols })), 'some');
eq('jargon reaches expert', C.classifyDepth([...C.depthCues('my target is a 60/40 split with low tracking error and a Sharpe above 0.5'), ...C.depthCues('MER under 0.2% only')]), 'expert');
eq('basic questions reach beginner', C.classifyDepth([...C.depthCues('what is an ETF?'), ...C.depthCues('what is a bond?')]), 'novice');
eq('nothing is read from the risk questions', C.depthCues('I have no idea', { step: 'C2' }), []);
// wording at three depths: values and order are the engine's; no unfilled slot; examples for beginners; the rule for experts
const fullSlots = { goal: 'saving for a home', goal_np: 'the home', when: 'in 5 to 9 years', how: ', all at once', ef: 'x', debt: 'y', income: 'z', amount: '$25,000', after: '$20,000', monthly: '', c0: 'some ups and downs are fine', c2: 'sell everything', c0w: 'medium', years: 5 };
for (const id of ['A1', 'B1', 'B2', 'A2', 'A3', 'B5', 'C0', 'C2', 'B4', 'C4']) {
  const opts = core.questions.find((x) => x.id === id).options;
  for (const d of ['novice', 'some', 'expert']) {
    const w = C.stepWording(id, d, { base: 'BASE', options: opts, slots: fullSlots, goal: 'home', core });
    eq(`${id} ${d}: values unchanged`, w.options.map((o) => o.value), opts.map((o) => o.value));
    ok(`${id} ${d}: no unfilled slot`, !/\{\w+\}/.test(w.q));
    if (d === 'some') eq(`${id} some: the approved text`, w.q, 'BASE');
    if (d === 'novice') ok(`${id} novice: an example on every option`, w.options.every((o) => o.ex));
    if (d === 'expert') ok(`${id} expert: the scoring rule`, !!w.whyDeep);
  }
  for (const [v, t] of Object.entries(KB.WORDING[id]?.expert?.opts || {})) eq(`${id}: "${t}" reads back as ${v}`, C.matchOption(opts.concat(Object.entries(KB.WORDING[id].expert.opts).map(([value, text]) => ({ value, text }))), t), v);
}
// the rule text matches the code: horizon points to capacity for all 25 pairs
for (const b1 of core.questions.find((x) => x.id === 'B1').options) for (const b2 of core.questions.find((x) => x.id === 'B2').options) {
  const pts = b1.pts + b2.pts, lvl = (KB.CAPACITY_BREAKS.find(([p]) => pts <= p) || [0, 5])[1];
  const pr = scoreProfile(core.questions, { A1: 'home', A2: 'yes', A3: 'no', B1: b1.value, B2: b2.value, B5: 'very', B4: 'lt10', C0: 'high', C2: 'buy', C1: '5' });
  if (!(b1.value === 'lt2' && b2.value === 'once')) eq(`capacity rule ${b1.value}+${b2.value}`, pr.capacity, lvl);
}
// the house rules for every new fixed text: no exclamation marks, no labels, Canadian spelling, no directives
const shown = (x, key = '') => (typeof x === 'string' ? (key === 'value' ? [] : [x]) : Array.isArray(x) ? x.flatMap((y) => shown(y)) : x && typeof x === 'object' && !(x instanceof RegExp) ? Object.entries(x).flatMap(([k, y]) => shown(y, k)) : []);  // the words people see, not keys or option values
const newText = shown([KB.WORDING, KB.DEPTH_ACK, KB.CALIBRATION, KB.CHECKPOINT, KB.EFFECT, KB.CLARIFY, KB.REPAIR, KB.CONFIRM, KB.CUES.nervous[1], KB.TERM_PLAIN, KB.TERM_DEEP, KB.READBACK, KB.SHORT_ASK, KB.PHRASE, KB.REQUIRED_SKIP, KB.SHORTCUTS]).join(' | ');
ok('no exclamation marks', !/!/.test(newText));
ok('no labels for the person', !/\b(?:novice|beginners?|experts?|experienced investor|intermediate|newbie)\b/i.test(newText));
ok('Canadian spelling', !/\b(?:color|favor|behavior|center|per cent|adviser)\b/i.test(newText));
ok('no directives', !/\byou should (?:buy|sell|invest)\b|\bI recommend\b/i.test(newText));
ok('the approved opening, with the product name', KB.OPENING.startsWith("Hi, I'm Penguru. I'll ask a few questions about your goals"));
// the checkpoint says what the answers mean, never a level number
for (const a of [{ A1: 'home', B1: '2to4', B2: 'once', A2: 'yes', A3: 'no', B5: 'very' }, { A1: 'wealth', B1: '20plus', B2: 'unsure', A2: 'partly', A3: 'no', B5: 'varies' }, { A1: 'home', B1: 'lt2', B2: 'once', A2: 'yes', A3: 'no', B5: 'very' }, { A1: 'retirement', B1: '10to19', B2: '10plus', A2: 'no', A3: 'lot', B5: 'none' }])
  for (const d of ['novice', 'some', 'expert']) { const t = C.checkpointText({ answers: a, amount: 25000, amountSet: true, monthly: 0, depth: d, words: {} }, scoreProfile(core.questions, a)); ok(`checkpoint ${d} ${a.B1}`, t && !/\{/.test(t) && !/level [1-5]/i.test(t.replace(/level at 2 or below/, ''))); }
// term answers at three depths
eq('standard: the glossary sentence', C.termAnswer('volatility', 'some', core.glossary), `${core.glossary.volatility.en.term}: ${core.glossary.volatility.en.definition}`);
ok('beginner: an everyday example', /bumpy/.test(C.termAnswer('volatility', 'novice', core.glossary)));
ok('experienced: the rule', /standard deviation/.test(C.termAnswer('volatility', 'expert', core.glossary)));
// provenance: every number in the experienced views is the engine's (validate.js)
{
  const { buildPortfolio } = await import('./robokit.js'), { checkReply } = await import('./validate.js');
  const p = buildPortfolio(M, { risk_level: 3, amount: 25000, monthly: 0, years: 25, nBoot: 60 });
  const h = C.hoodRows(p), all = [...h.risk, ...h.assumptions, ...h.constraints, ...h.method, ...h.stress, ...C.whyPlain(p, { amount: 25000 }), ...p.holdings.map(C.rationaleDeep)].join(' ');
  const r = checkReply(all, p, null, [1, 0.5, 0.05, 0.95, 25000, 8, 10, 2008]);
  ok(`under the hood: every number comes from the engine (${r.unsupported_numbers?.join(', ') || 'none unsupported'})`, r.ok);
  ok('plain reasons use plain words', !/\b(?:equity|fixed income|commodity|volatility)\b/i.test(C.whyPlain(p, { amount: 25000 }).join(' ')));
  const f = C.figures(p); ok('figures for the expert terms', f.vol && f.target && f.sharpe);
}
// Claude's replies: the same rules as the fixed words
eq('a directive', C.outputIssues('Go with level 3.'), ['directive']);
ok('a guarantee', C.outputIssues('Returns are not high, but growth is guaranteed.').includes('guarantee'));
ok('a level preview before the assessment', C.outputIssues('Your answers so far point to a careful mix').includes('level_before_assessment'));
ok('a label', C.outputIssues('As a beginner, you might like this.').includes('label'));
eq('the same words after the assessment', C.outputIssues('Your answers so far point to a careful mix', { assessed: true }), []);
eq('a fine sentence', C.outputIssues('Your level of comfort is your own call.'), []);
ok('every fixed text passes', [KB.ADVICE_REDIRECT, KB.OPENING, ...Object.values(KB.LEARN), ...Object.values(KB.WHY), ...KB.FAQ.map((x) => x.a)].every((t) => C.outputIssues(t, { assessed: true }).filter((x) => x !== 'level_before_assessment').length === 0));
eq("the person's own numbers", C.personNumbers(["I'm 29 with $300 a month for 20 years"]).sort((a, b) => a - b), [20, 29, 300]);
// found by the cross-family review, each reproduced before the fix
eq('a debt amount is not the amount to invest', RT('I owe $500 on my credit card', 'BASICS', { A2: 'yes' }).facts.MONEY, undefined);
eq('emergency savings are not the amount to invest', RT('I have $5k in emergency savings', 'BASICS').facts, { A2: 'yes' });
eq('an amount to invest next to a debt clause still counts', RT('I want to invest $10k and I have no debt').facts, { A3: 'no', MONEY: { B3: 10000 } });
eq('sell nothing is holding on', C.parseDrop('sell nothing'), 'wait');
eq("I wouldn't sell is holding on", C.parseDrop("I wouldn't sell"), 'wait');
const B1o = { B1: core.questions.find((x) => x.id === 'B1').options };
eq('a bare 3 asks: option 3 or 3 years', C.readTurn('3', { pending: 'B1', options: B1o }).vague.B1?.candidates, ['5to9', '2to4']);
eq('a bare 8 is 8 years', C.readTurn('8', { pending: 'B1', options: B1o }).facts.B1, '5to9');
eq('a bare 1 is the same either way', C.readTurn('1', { pending: 'B1', options: B1o }).facts.B1, 'lt2');
eq('none is an income answer, not a skip', C.readAnswer('B5', 'none', core.questions.find((x) => x.id === 'B5').options), { value: 'none' });

// v3.3: the team's cleaned-up feedback (Penguru review, tab 3)
{ // the product name in every fixed text (the engine's own words are renamed by the page as they come in)
  const fixed = JSON.stringify(Object.fromEntries(Object.entries(KB).filter(([, v]) => typeof v !== 'function'))) + KB.NOT_CANADIAN('SPY') + KB.ETF_ONLY('stocks') + ['EXP', 'A1', 'B1', 'BASICS', 'C0', 'TICKER'].map((id) => KB.whyDeep(id, core)).join(' ');
  ok('the fixed words say Penguru, never Robo-Kit', !fixed.includes('Robo-Kit') && fixed.includes('Penguru'));
}
// item 9: a word is a term button only in its investing sense
ok('"the biggest factor in" is not the factor-fund term', !KB.TERMS.factor.match.test(KB.WHY.B1) && !KB.TERMS.factor.match.test('Time is the biggest factor in how many ups and downs'));
ok('a factor fund is still the term', KB.TERMS.factor.match.test('No factor (smart-beta) funds') && KB.TERMS.factor.match.test('factor ETFs') && KB.TERMS.factor.match.test('smart beta'));
ok('a risk or price index is not a market index', !KB.TERMS.index.match.test('the geopolitical risk index') && !KB.TERMS.index.match.test('the consumer price index') && KB.TERMS.index.match.test('an index such as the S&P 500'));
ok('a distribution of outcomes is not a fund distribution', !KB.TERMS.distribution.match.test('the distribution of outcomes') && KB.TERMS.distribution.match.test('with distributions reinvested'));
ok('"capacity" alone is not risk capacity', !KB.GLOSSARY_MATCH.risk_capacity.test('the capacity of the fund') && KB.GLOSSARY_MATCH.risk_capacity.test('your risk capacity'));
ok('"yields" as a verb is not a yield', !KB.GLOSSARY_MATCH.yield.test('this yields a mix') && KB.GLOSSARY_MATCH.yield.test('bond yields'));
{ // item 10: no risk level in anything said before the assessment introduces it
  const PRE = ['EXP', 'A1', 'B1', 'B2', 'BASICS', 'A2', 'A3', 'MONEY', 'B5', 'C0', 'C2', 'RECON', 'C1', 'FT', 'B4', 'C3', 'C4'];
  const w = (id) => KB.WORDING[id] || {};
  const texts = [KB.OPENING, KB.REQUIRED_SKIP, KB.EFFECT.gate, KB.EFFECT.G1, KB.HIGHLIGHT, KB.CALIBRATION.text, ...KB.CALIBRATION.options.flatMap((o) => [o.text, o.ex]),
    ...PRE.flatMap((id) => [KB.WHY[id], KB.LEARN[id], KB.SHORT_ASK[id], KB.REPAIR[id], ...(KB.SUGGEST[id] || []), w(id).novice?.q, w(id).expert?.q, ...Object.values(w(id).novice?.qBy || {}), ...Object.values(w(id).novice?.opts || {}), ...Object.values(w(id).expert?.opts || {}), ...Object.values(w(id).ex || {})]),
    ...Object.values(KB.ACK).flatMap((x) => Object.values(x)), ...Object.values(KB.CHECKPOINT), ...Object.values(KB.DEPTH_ACK).flatMap((x) => (typeof x === 'string' ? [x] : Object.values(x)))].filter(Boolean);
  const said = texts.filter((t) => /\blevels?\b/i.test(t));
  ok(`no risk level before the assessment (${said.join(' | ') || 'none'})`, !said.length);
  for (const id of PRE) { const t = KB.whyDeep(id, core); ok(`"How this is scored" says what a risk level is before using one: ${id}`, !t || !/\blevels?\b/i.test(t) || t.startsWith('Risk level runs from 1')); }
}
{ // item 3 (Q3 removed): the withdrawal plan assumed from the goal scores the same and says it was assumed
  const a = { A1: 'home', A2: 'yes', A3: 'no', B1: '2to4', B2: 'once', B5: 'very', C0: 'medium', C2: 'wait' };
  const asked = scoreProfile(core.questions, a), assumed = scoreProfile(core.questions, a, { assumed: ['B2'] });
  eq('an assumed withdrawal plan scores the same', [assumed.capacity, assumed.tolerance, assumed.suggested_level], [asked.capacity, asked.tolerance, asked.suggested_level]);
  ok('the explanation says it was assumed', /all at once, assumed from your goal/.test(assumed.explanation.en.join(' ')) && !/assumed/.test(asked.explanation.en.join(' ')));
  ok('the checkpoint says so too', /all at once \(assumed from your goal\)/.test(C.checkpointText({ answers: a, auto: new Set(['B2']), amount: 25000, amountSet: true, monthly: 0, depth: 'novice', words: {} }, assumed)));
  eq('a home needed within two years, all at once, still gets no stock mix', scoreProfile(core.questions, { ...a, B1: 'lt2' }, { assumed: ['B2'] }).status, 'not_ready');
}


// v3.3.1: found by rehearsing the two demo personas
{ // level 5 within reach: every tolerance answer at its top, a long horizon spread over time, no cushions or limits
  const top = { A1: 'retirement', A2: 'yes', A3: 'no', B1: '20plus', B2: '10plus', B5: 'very', B4: 'lt10', C0: 'high', C1: '5', C2: 'buy', C3: '5', C4: 'missing' };
  eq('all-top answers reach level 5', [scoreProfile(core.questions, top).tolerance, scoreProfile(core.questions, top).suggested_level], [5, 5]);
  eq('the shortest path (no fine-tune) reaches 5 too', scoreProfile(core.questions, { A1: 'wealth', A2: 'yes', A3: 'no', B1: '20plus', B5: 'very', C0: 'high', C1: '5', C2: 'buy' }).suggested_level, 5);
  eq('one answer below the top keeps it at 4', scoreProfile(core.questions, { ...top, C3: '4' }).suggested_level, 4);
  eq('a home bought all at once in 20+ years stays at 4 (capacity)', scoreProfile(core.questions, { ...top, A1: 'home', B2: 'once' }, { assumed: ['B2'] }).suggested_level, 4);
  eq('a home bought all at once in 10-19 years stays at 3 (capacity)', scoreProfile(core.questions, { ...top, A1: 'home', B1: '10to19', B2: 'once' }, { assumed: ['B2'] }).suggested_level, 3);
}
ok('"If I add $350 a month, would it be invested in the mix?" is a question', C.isConditionalQuestion('If I add 350 a month, would those added funds get invested in the chosen mix?') && !C.isConditionalQuestion('10 years?') && !C.isConditionalQuestion('if I retire in 20 years'));
ok('and it has a saved answer', /each month's amount is added to the same mix/.test(C.localAnswer('If I add 350 a month, would those added funds get invested in the chosen mix?', { step: 'MONEY', glossary: core.glossary })?.text || ''));
eq('"10-25%" is the 10% to 25% band', C.parseShare('10-25%'), '10to25');
eq('"10 to 25%" too', C.parseShare('10 to 25%'), '10to25');
eq('"25-50%" is the next band', C.parseShare('25-50%'), '25to50');
eq('"about 20%" unchanged', C.parseShare('about 20%'), '10to25');
eq('"Yes, no" on the two checks fills them in order', RT('Yes, No', 'BASICS').facts, { A2: 'yes', A3: 'no' });
eq('"no, a little" too', RT('no, a little', 'BASICS').facts, { A2: 'no', A3: 'little' });
eq('a long-term investor looking to learn more is building wealth', C.parseGoal("I'm a longer term investor looking to learn more"), 'wealth');
eq('just learning is still learning', C.parseGoal("I'm just learning"), 'learning');
{ // the recap names the limit when it holds the level, and says "both" when the two scores agree
  const rc = C.recap({ lowerOf: true, capacity: 3, tolerance: 3, binding: 'gate', gateCap: 2, gates: [{ id: 'G2' }] }).covered.join(' ');
  ok('recap: the limit holds the level', /holds it at 2 for now/.test(rc) && !/\(3\) and .*\(3\)/.test(rc));
  ok('recap: both point to the same level', /both point to 3/.test(C.recap({ lowerOf: true, capacity: 3, tolerance: 3, binding: 'both' }).covered.join(' ')));
}
eq('the one-year card question includes the monthly money', C.stepWording('C1', 'novice', { slots: C.slotsFrom({ answers: {}, amount: 10000, amountSet: true, monthly: 350, words: {} }) }).q, 'Here are five possible mixes. Each card shows where your $10,000 plus $350 a month might be after one year. Which range could you live with?');

eq('"Actually I don\u2019t have an emergency fund" is a no', C.parseEmergency("Actually I don't have an emergency fund"), 'no');
eq('"I do not have emergency savings" is a no, not a yes', C.parseEmergency('I do not have emergency savings'), 'no');
eq('"I haven’t got one" is a no', C.parseEmergency('I haven’t got an emergency fund'), 'no');
eq('"I don’t have much saved" is partly', C.parseEmergency('I don’t have much saved'), 'partly');
eq('"I don’t have much debt" is a little', C.parseDebt('I don’t have much debt'), 'little');
eq('"Actually I don’t have any debt" is none', C.parseDebt('Actually I don’t have any debt'), 'no');
eq('a correction naming both checks changes both', C.readTurn("Actually I don't have an emergency fund and I have a lot of credit card debt", { answers: { A2: 'yes', A3: 'no' } }).changes.map((c) => [c.id, c.to]), [['A2', 'no'], ['A3', 'lot']]);

{ // the share-of-savings question: a bare range or number is a percent (found rehearsing persona 2: "10-25")
  const o = { B4: [{ value: 'lt10', text: 'Less than 10%' }, { value: '10to25', text: '10% to 25%' }, { value: '25to50', text: '25% to 50%' }, { value: '50to75', text: '50% to 75%' }, { value: 'gt75', text: 'More than 75%' }] };
  const at = (t) => C.readTurn(t, { pending: 'B4', options: o, answers: {} }).facts.B4;
  eq('"10-25" on the share question is 10% to 25%', at('10-25'), '10to25');
  eq('"10 to 25" too', at('10 to 25'), '10to25');
  eq('"between 10 and 25" is one range, not two answers', at('between 10 and 25'), '10to25');
  eq('a bare "15" is a percent', at('15'), '10to25');
  eq('a bare "2" is still the second option', at('2'), '10to25');
  eq('"80" is more than 75%', at('80'), 'gt75');
  eq('"120" is not a share', at('120'), undefined);
  eq('"between 5 and 9 years" on the horizon still reads', C.readTurn('between 5 and 9 years', { pending: 'B1', answers: {} }).facts.B1, '5to9');
}

// v3.3.2: found by the whole-repository review (docs/VERIFICATION.md section 8.15)
{
  const OPTS = Object.fromEntries(core.questions.map((q) => [q.id, q.options]));
  const RO = (t, pending, answers = {}) => C.readTurn(t, { pending, answers, options: OPTS, symbols, year: 2026 });
  // S: months are a horizon only when they say when
  eq('"6 months of expenses" on the basics is the emergency fund, not the horizon', (({ facts, changes }) => ({ facts, changes }))(RO('Yes, I have 6 months of expenses', 'BASICS', { B1: '20plus' })), { facts: { A2: 'yes' }, changes: [] });
  eq('"hold for 6 months" answers the drop question', RO('Probably hold for 6 months and see', 'C2', { B1: '20plus' }).facts, { C2: 'wait' });
  eq('"250 monthly for 6 months" is money, not the horizon', RO('10k now, then 250 monthly for 6 months', 'MONEY', { B1: '20plus' }).changes, []);
  eq('"about 6 months" on the horizon question is still less than 2 years', RO('about 6 months', 'B1').facts.B1, 'lt2');
  eq('"I need it in about 18 months" is still less than 2 years', RO('I need it in about 18 months').facts.B1, 'lt2');
  eq('a bare "18 months" after the goal is still the horizon', RO('A car, 18 months', 'A1').facts, { A1: 'home', B1: 'lt2' });
  eq('a bare "6 months" on the basics is the emergency fund', RO('6 months', 'BASICS').facts, { A2: 'yes' });
  eq('"eighteen months" is less than 2 years', H('eighteen months'), { value: 'lt2', sure: true });
  eq('"24 months" is two years', H('24 months'), { value: '2to4', sure: true });
  // T: a student loan is debt, not "no income"
  eq('a student loan says nothing about income', C.parseIncome('I have a student loan'), null);
  eq('"no credit card debt, just student loans" answers only the debt', RT('no credit card debt, just student loans', 'BASICS').facts, { A3: 'no' });
  eq('a student loan on the debt card does not record income', RT('I have a student loan', 'A3').facts.B5, undefined);
  eq('nor does a student credit card', RT('just a student credit card', 'A3').facts.B5, undefined);
  eq('"I am a student" is still no regular income', C.parseIncome('I am a student'), 'none');
  // V: "... for me" said as an answer is an answer; asked, it is advice
  for (const t of ['medium is ok for me', 'I would hold, selling is not right for me', '10k is a lot for me']) ok(`not advice: ${t}`, !C.isAdvice(t));
  for (const t of ['I want to know which level is right for me', 'Is level 4 right for me?', 'is level 5 too risky for me?', 'pick something good for me', 'choose a level that is right for me', 'give me something safe for me', 'I need something good for me', 'set the level that is best for me', 'make it right for me', 'Please tell me the portfolio that is right for me', 'I need to know the mix that is right for me', 'the portfolio that is right for me', 'What is the right mix for me?', 'Tell me the right mix for me', 'Which level is good for my situation?', 'the best level for someone like me']) ok(`advice: ${t}`, C.isAdvice(t));
  for (const t of ['that is too risky for me', 'level 4 feels right for me', 'Medium sounds right for me']) ok(`not advice: ${t}`, !C.isAdvice(t));
  eq('"medium is ok for me" answers the self-rating', RO('medium is ok for me', 'C0').facts, { C0: 'medium' });
  // Z: a month count is compared with the 3-month bar
  for (const t of ['I have 2 months of expenses', 'only 2 months', 'I have a month of expenses', 'a couple of months', 'less than 3 months of expenses', 'under 3 months', 'almost 3 months']) eq(`emergency fund: ${t}`, C.parseEmergency(t), 'partly');
  eq('emergency fund: zero months is none', C.parseEmergency('I have zero months of expenses'), 'no');
  for (const t of ['I have 6 months of expenses', 'I have 3 months', 'twelve months']) eq(`emergency fund: ${t}`, C.parseEmergency(t), 'yes');
  eq('"I have 2 months saved" on the basics is partly', RO('I have 2 months saved', 'BASICS', { B1: '20plus' }).facts, { A2: 'partly' });
  eq('a typed change to 2 months is partly', C.parseCommand('actually my emergency fund is only 2 months', { symbols })?.value, 'partly');
  // U: the person's own number of years only while it names the recorded horizon
  eq('years said for an earlier horizon are not used', C.slotsFrom({ answers: { B1: '5to9' }, words: { years: 25 } }).when, KB.PHRASE.B1['5to9']);
  eq('years said for this horizon are used', C.slotsFrom({ answers: { B1: '20plus' }, words: { years: 25 } }).when, 'in about 25 years');
  ok('the beginner acknowledgement does not repeat outdated years', !/25/.test(C.ackText('B1', '5to9', { depth: 'novice', answers: { B1: '5to9' }, words: { years: 25 } })));
  // Y: the goal feeds the level through the withdrawal pattern, and the "why" says so
  ok('why the goal is asked does not say it leaves the math alone', !/does not change/.test(KB.WHY.A1));
}

console.log(fails ? `${fails} of ${n} checks FAILED` : `all ${n} conversation checks pass`);
if (fails) process.exit(1);
