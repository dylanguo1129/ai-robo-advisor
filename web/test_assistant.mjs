// Cases for web/assistant.js (the chat layer), with a scripted stand-in for Claude. Run: node web/test_assistant.mjs
import { Assistant } from './assistant.js';

let bad = 0;
const eq = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) bad++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}: ${JSON.stringify(got)}${ok ? '' : ` (want ${JSON.stringify(want)})`}`);
};

// A stand-in page: each tool records the card it would add to the thread.
const FEES = { QQQ: 0.0018, 'XAW.TO': 0.0022 };
const shown = [];
let mixCalls = 0;
const app = {
  st: { market: 'US', level: 3, levelChosen: false, amount: 10000, monthly: 0, years: 10, goal: null, result: null, check: { open: false }, profile: null },
  core: { meta: { prices_through: '2026-08-31' } },
  levelName: () => 'Balanced', isAbove: () => false, consented: () => false, openQuestion: () => null, profileSummary: () => null,
  trayTickers: () => [], notHeld: () => [], universeSet: () => new Set(['QQQ', 'XAW.TO']), stateNumbers: () => [],
  toolProfile(i) { const t = i.ticker.toUpperCase(); shown.push(`fund:${t}`); return { found: true, ticker: t, mer: FEES[t] }; },
  toolCompare(i) { shown.push(`compare:${i.tickers.join(',')}`); return { funds: i.tickers.map(t => ({ ticker: t, mer: FEES[t.toUpperCase()] })) }; },
  async toolCurrentMix() { mixCalls++; return { level: 3 }; },
};

// Claude, scripted: each pass makes its tool calls (in order, or together when grouped) and then replies.
const scripted = (passes) => {
  let n = 0;
  return async (input, opts) => {
    const pass = passes[n++];
    for (const step of pass.calls) {
      const group = Array.isArray(step[0]) ? step : [step];
      await Promise.all(group.map(([name, args]) => opts.tools.find(t => t.name === name).execute(args)));
    }
    return { text: pass.text, modelTierApplied: 'default' };
  };
};
const guide = (passes) => { const a = new Assistant(app); a.available = true; a.toolsOk = true; a.sample = scripted(passes); return a; };

// The rewrite pass repeats the first pass's calls: each fund card is shown once.
let a = guide([
  { calls: [['etf_profile', { ticker: 'QQQ' }], ['etf_profile', { ticker: 'XAW.TO' }]], text: 'QQQ charges 0.99% a year.' },
  { calls: [['etf_profile', { ticker: 'QQQ' }], ['etf_profile', { ticker: 'XAW.TO' }], ['etf_profile', { ticker: 'qqq' }]], text: 'QQQ charges 0.18% a year and XAW.TO charges 0.22%.' },
]);
let res = await a.ask('Tell me about QQQ and XAW');
eq('rewrite happened', res.retried, true);
eq('rewritten reply passes the check', res.check.ok, true);
eq('one card per fund across the rewrite', shown, ['fund:QQQ', 'fund:XAW.TO']);

// The same comparison asked twice in one turn (in another order, or at the same moment) is one card.
shown.length = 0;
a = guide([{ calls: [[['compare_etfs', { tickers: ['QQQ', 'XAW.TO'] }], ['compare_etfs', { tickers: ['QQQ', 'XAW.TO'] }]], ['compare_etfs', { tickers: ['XAW.TO', 'QQQ'] }]], text: 'QQQ charges 0.18% and XAW.TO 0.22%.' }]);
res = await a.ask('Compare QQQ and XAW');
eq('one comparison card per turn', shown, ['compare:QQQ,XAW.TO']);
eq('repeated call still returns the data', a.log.length, 3);

// A new turn is a new message in the thread: its cards are shown again.
shown.length = 0;
a = guide([
  { calls: [['etf_profile', { ticker: 'QQQ' }]], text: 'QQQ charges 0.18% a year.' },
  { calls: [['etf_profile', { ticker: 'QQQ' }]], text: 'QQQ charges 0.18% a year.' },
]);
await a.ask('What is QQQ?');
await a.ask('And QQQ again?');
eq('cards repeat across turns', shown, ['fund:QQQ', 'fund:QQQ']);

// Tools without a card still run every time (the rules ask for current_mix again before citing the mix).
mixCalls = 0;
a = guide([{ calls: [['current_mix', {}], ['current_mix', {}]], text: 'Here is the mix.' }]);
await a.ask('What is in my mix?');
eq('current_mix runs on every call', mixCalls, 2);

if (bad) { console.log(`\n${bad} failed`); process.exit(1); }
console.log('\nall assistant cases passed');
