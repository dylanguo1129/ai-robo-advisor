/* Deterministic readers for what a person types: amounts, monthly flows, and the facts in a first message.
 * No AI and no guessing: when a message is ambiguous, the field is left empty for the person to fill.
 * Kept free of the DOM so web/test_parse.mjs can run it under Node. */

const MULT = { k: 1e3, thousand: 1e3, grand: 1e3, m: 1e6, mm: 1e6, mil: 1e6, million: 1e6 };

/** "50000", "50,000", "$50k", "1.5m", "1.5 million", "50k CAD" -> number; anything else -> null. Never negative. */
export function parseAmount(s) {
  if (s == null) return null;
  const t = String(s).trim().toLowerCase().replace(/[,\s$]/g, '').replace(/(cad|usd|dollars?|bucks)$/g, '');
  const m = t.match(/^(\d+(?:\.\d+)?)(k|thousand|grand|mm|mil|million|m)?$/);
  if (!m) return null;
  const v = Math.round(Number(m[1]) * (MULT[m[2]] || 1));
  return Number.isFinite(v) && v <= 1e11 ? v : null;  // a pasted run of digits is not an amount
}

// "need $2,000 a month" in retirement is money taken out; "need to save 500 a month" is not
const OUT_WORDS = /take[ -]?out|taking out|withdraw(?:al|ing)?|draw(?:ing)?(?:[ -]?down)?|spend(?:ing)?|\bneed(?:s|ed)?\b(?!\s+to\s+(?:save|invest|add|put|contribut|set))|liv(?:e|ing) on/i;

/** A monthly flow: "500", "+500", "500/month", "$500 a month", "-1500", "−1,500", "take out 1500".
 *  Returns a signed number (negative = taking out), 0 for an empty field, or null when it cannot be read. */
export function parseMonthly(s) {
  const raw = String(s ?? '').trim();
  if (!raw) return 0;
  const neg = /^[-−–]/.test(raw) || OUT_WORDS.test(raw);
  const t = raw.replace(/^[-−–+]\s*/, '')
    .replace(new RegExp(OUT_WORDS.source, 'gi'), '')
    .replace(/add(?:ing)?|put(?:ting)? in|contribut(?:e|ing)|save/gi, '')
    .replace(/\/\s*mo(?:nth)?\.?|\ba month\b|per month|monthly|each month|every month/gi, '')
    .trim();
  const v = parseAmount(t);
  return v == null ? null : (neg ? -v : v);
}

/** A question rather than a statement: used to decide whether a message may start the guided build. */
export function isQuestion(t) {
  const s = String(t || '').trim();
  return /[?]/.test(s) || /^(how|what|whats|why|which|who|when|where|is|are|am|can|could|should|would|does|do|did|will|compare|explain|tell me)\b/i.test(s);
}

/** Asking for the guided build in so many words. */
export const BUILD_RX = /\b(?:build|make|create|start|set up|design)\b[^.?!]{0,40}\b(?:portfolio|mix|allocation)\b|\bportfolio for\b/i;

const TOK = /([-−])?\s?([$])?\s?(\d[\d,]*(?:\.\d+)?)(?:\s?(k|thousand|grand|million|mil|mm|m)(?![a-z]))?(?:\s?(cad|usd|dollars?|bucks))?/gi;
const MONTH_AFTER = /^\s*(?:\/\s*mo(?:nth)?\b|a month|per month|monthly|each month|every month)/i;
const MONTH_BEFORE = /(?:monthly|each month|every month|a month|per month)\s*(?:add(?:ing)?|put(?:ting)? in|take out|withdraw(?:ing)?|draw(?:ing)?)?\s*[$]?\s*$/i;
const YEAR_AFTER = /^\s*(?:a year|per year|\/\s*y(?:ea)?r\b|annually|yearly)/i;
const SALARY_BEFORE = /(?:earn(?:s|ing)?|make|makes|making|salary(?: of)?|paid|income(?: of| is)?|wage)\s*(?:is|of|about|around|roughly)?\s*[$]?\s*$/i;
const HAVE_BEFORE = /(?:have|has|had|saved|savings(?: of)?|invest(?:ing)?|put(?:ting)? in|put|deposit(?:ing)?|got|inherit(?:ed)?|lump sum(?: of)?|start(?:ing)? with|with)\s*(?:about|around|roughly|like|of)?\s*[$]?\s*$/i;

/** Facts in a first message, read deterministically (never tolerance answers).
 *  { market?, goal?, amount?, monthly? (signed), amountChoices? (when several amounts fit and none is marked) } */
export function parseOpener(text) {
  const src = String(text || '').replace(/\b(?:https?:\/\/|www\.)\S+/gi, ' '), out = {};  // numbers inside a pasted link are not amounts
  const t = src.replace(/\b(?:401|403|457)\s?\(?[kb]\)?/gi, (m) => ' '.repeat(m.length));  // account names, not amounts
  const low = t.toLowerCase();
  const ca = /canad|\bcad\b|\btsx\b|\btfsa\b|\brrsp\b|\bfhsa\b|toronto|vancouver|montreal|calgary|ottawa/i.test(t);
  const us = /\bU\.?S\.?A?\b/.test(src) || /\busa\b|\bu\.s\.|\b(?:the|in) us\b|(?<!\b(?:tell|show|help|give|let|for|to|with|of|from|ask|about|send|join)\s)\bus (?:[a-z&-]+ )?(?:stocks?|etfs?|funds?|markets?|dollars?|equit(?:y|ies)|bonds?|dividends?|listed|citizen|resident)\b|united states|america|\busd\b|\b401\s?\(?k\)?|\bira\b|\broth\b|\bhsa\b/i.test(src);
  if (ca !== us) out.market = ca ? 'CA' : 'US';
  const goals = [['retirement', /retire/], ['home', /house|home|down ?payment|condo/], ['education', /educat|school|tuition|college|\bresp\b/], ['income', /\bincome\b(?! of)|dividend/], ['learning', /just learning|\blearn/], ['wealth', /wealth|grow|long[- ]term/]];
  for (const [g, rx] of goals) if (rx.test(low)) { out.goal = g; break; }
  if (/\b(?:i'?m|i am|we'?re|we are|already)\s+retired\b|\bin retirement\b|taking (?:money |it )?out (?:now|already)/i.test(src)) out.retiredNow = true;
  const toks = [];
  for (const m of t.matchAll(TOK)) {
    const [raw, minus, dollar, num, mult, cur] = m;
    const v = parseAmount(num + (mult || ''));
    if (v == null || v < 100) continue;
    const lead = raw.length - raw.trimStart().length;
    const before = t.slice(Math.max(0, m.index + lead - 28), m.index + lead), after = t.slice(m.index + raw.length, m.index + raw.length + 16);
    const monthly = MONTH_AFTER.test(after) || MONTH_BEFORE.test(before);
    const yearLike = !dollar && !mult && !cur && !/[,.]/.test(num) && v >= 1900 && v <= 2100;
    if (yearLike && !monthly && !HAVE_BEFORE.test(before) && !OUT_WORDS.test(before.slice(-14))) continue;  // "retire in 2045"
    toks.push({ v, monthly, money: !!(dollar || mult || cur) || v >= 1000,
      salary: !monthly && (YEAR_AFTER.test(after) || SALARY_BEFORE.test(before)),
      out: !!minus || OUT_WORDS.test(before.slice(-14)), have: HAVE_BEFORE.test(before) });
  }
  const mo = toks.find(k => k.monthly);
  if (mo) out.monthly = mo.out ? -mo.v : mo.v;
  const cands = toks.filter(k => !k.monthly && !k.salary && k.money);
  const pick = cands.find(k => k.have) || (cands.length === 1 ? cands[0] : null);
  if (pick) out.amount = pick.v;
  else if (cands.length > 1) out.amountChoices = [...new Set(cands.map(k => k.v))];
  return out;
}

// ------------------------------------------------------------------ the no-AI router: what a typed message asks for
// Without the assistant the page answers a message with a fund card (tickers, found by the page), the guided build, a
// glossary card, the market context card or a fund search. The rules, in order:
//   1. a fund request ("gold etfs", "corporate bond etf", "tell me about dividend etfs") is a search, unless it only asks
//      what a term means ("what is a covered call etf?");
//   2. a glossary term counts when the message asks what it is ("what is a REIT", "how do bonds work") or is only the
//      term ("reits", "emerging markets"); terms that never name a fund (fees, TFSA, rebalancing...) count anywhere;
//   3. news and market words ("how are markets?", "tariffs") open the market context card;
//   4. otherwise a search on the words that carry meaning; greetings and filler search nothing.

const FUND_RX = /\b(?:etfs?|funds?)\b/;
const DEFINE_RX = /^(?:what(?:'s|s)?\b|whats\b|define\b|explain\b|meaning\b|how (?:do|does|is|are)\b|why\b|tell me (?:about|what)\b)|\bmeans?\b/;
const CONTEXT_RX = new RegExp([
  /\b(?:news|headlines?|wars?|crash\w*|tariffs?|geopolit\w*|recessions?|economy|economic)\b/.source,
  /\b(?:interest rates?|rate (?:cuts?|hikes?)|bank of canada|boc|federal reserve|the fed|cpi|yield curve|credit spreads?|canadian dollar|loonie|exchange rates?|usd ?\/? ?cad|cad ?\/? ?usd)\b/.source,
  /(?<!\b(?:money|total|broad|emerging|frontier|developed|capital|debt|private|bond|whole)\s)\bmarkets?\b(?!\s(?:caps?|index\w*|weight\w*|neutral|value|portfolio))/.source,
].join('|'));
/** Asking how to change the fund list ("switch market", "which market am I in"), not about market news. */
const SWITCH_RX = /\b(?:switch|change|toggle|select|pick|choose|which|other)\b(?:\s+\w+){0,2}\s+markets?\b|\bmarkets? (?:toggle|switch|setting)\b/;
/** A message asked as a question (a question mark, a question word, or "is it", "should I"...), not a statement that
 *  happens to start with "would" or "will" ("would wait it out" is an answer). */
const QUESTION_START = /^(?:what|whats|what's|why|how|which|explain|define|tell me)\b|^(?:is|are|am|can|could|should|would|will|do|does|did)\s+(?:i|it|you|we|they|that|this|there|he|she|an?|the|etfs?|my|our)\b/;
export function asksQuestion(text) { const raw = String(text || '').trim(); return /\?\s*$/.test(raw) || QUESTION_START.test(raw.toLowerCase()); }
/** Words that keep a question about ETFs general ("are etfs safe?", "the difference between an etf and a mutual fund"). */
const GENERIC = new Set(('safe safer safest risky risk risks difference differences different differ between mutual investment investments investing ' +
  'taxed tax taxes taxable work works working zero worth start starting beginner beginners vs versus compared comparison better worse idea ' +
  'smart way ways go goes going own owning hold holding stock stocks bad pros cons advantages disadvantages trade traded traders cost costs').split(' '));

/** Glossary key, words, and mode: 'any' (the word never names a fund) or 'ask' (a question about it, or the term alone). */
export const TERMS = [
  ['bond_prices_rates', /\bbonds?\b.*\b(?:rates?|interest)\b|\b(?:rates?|interest)\b.*\bbonds?\b/, 'any'],
  ['covered_call', /covered[- ]?calls?/, 'ask'], ['tbill_hisa', /\bt-?bills?\b|\bhisa\b|\bhysa\b|high[- ](?:interest|yield) savings|cash etfs?|savings etfs?/, 'ask'],
  ['emerging_markets', /emerging(?: markets?)?/, 'ask'], ['equilibrium_return', /equilibrium/, 'any'], ['black_litterman', /black[- ]?litterman/, 'any'],
  ['tracking_error', /tracking error/, 'any'], ['spread', /bid[- ]?ask(?: spreads?)?|(?<!credit )\bspreads?\b/, 'ask'], ['risk_tolerance', /risk tolerance/, 'any'],
  ['risk_capacity', /risk capacity/, 'any'], ['asset_class', /asset class(?:es)?/, 'ask'], ['index_fund', /index funds?/, 'ask'],
  ['mer', /\bmer\b|expense ratio|management (?:expense|fee)|\bfees?\b/, 'any'], ['aum', /\baum\b|assets under management/, 'ask'],
  ['volatility', /volatil\w*/, 'ask'], ['leverage', /leverag\w*|\binverse\b|\b[23]x\b/, 'ask'], ['hedged', /(?:currency[- ])?hedg\w*/, 'ask'],
  ['duration', /\bduration\b/, 'ask'], ['yield', /\byields?\b(?! curve)/, 'ask'], ['bond', /\bbonds?\b/, 'ask'], ['tfsa_rrsp', /\btfsa\b|\brrsp\b/, 'any'],
  ['diversification', /diversif\w*/, 'any'], ['rebalancing', /rebalanc\w*/, 'any'], ['drawdown', /drawdowns?/, 'any'], ['reit', /\breits?\b/, 'ask'],
  ['resampling', /resampl\w*/, 'any'], ['sharpe', /sharpe/, 'any'], ['correlation', /correlat\w*/, 'any'], ['inflation', /inflation/, 'ask'],
  ['hypothetical', /hypothetical/, 'any'],
  // the general question about ETFs, asked as such ("what are etfs", "how do etfs work"), never a request for some ETFs
  ['etf', /^(?:what(?:'s|s)?|whats)\s+(?:is|are)?\s*(?:an?\s+)?etfs?\b|^how (?:do|does) (?:an? )?etfs? work|^(?:explain|define) (?:an? )?etfs?$|^etfs?$/, 'any'],
];
/** Glossary terms that are also fund themes: their card offers the funds, and "covered call etf" goes straight to them. */
export const THEMES = { covered_call: ['covered', 'call'], emerging_markets: ['emerging', 'markets'], reit: ['reit'], bond: ['bond'], yield: ['yield'],
  hedged: ['hedged'], inflation: ['inflation'], tbill_hisa: ['bill'], index_fund: ['index'], leverage: ['leveraged'], volatility: ['volatility'] };
/** Words that carry no search meaning ("hi", "thanks", "tell me about", "the cheapest"). */
export const FILLER = new Set(('a an the and or but if of to in on at by for with about from into onto over under as is are was were be been am do does did ' +
  'doing done have has had i me my mine we us our ours you your yours he she him her his it its they them their theirs this that these those there here ' +
  'what whats which who whom whose why how when where can could should would will shall may might must not no yes yeah yep nope nah sure ok okay ' +
  'hi hello hey hiya yo thanks thank thx ty please pls cool great nice lol hmm hmmm wow morning afternoon evening night some any all more most less much many very really just also too ' +
  'like want need know tell show give find get let make help pick choose buy invest put recommend suggest looking look good best better top cheap ' +
  'cheapest cheaper lowest options option ideas idea something anything kind kinds type types sort list go between than pay pays paying etf etfs fund funds index indexes trust portfolio shares series units class').split(' '));

/** A message lower-cased, without trailing punctuation. */
const clean = (t) => String(t || '').toLowerCase().replace(/[’`]/g, "'").replace(/[?!.\s]+$/, '').trim();
/** The words of a message that can find a fund (no filler, no "etf"/"fund"). */
export function searchWords(text) {
  const raw = String(text || '').replace(/\b(?:https?:\/\/|www\.)\S+/gi, ' ');  // a pasted link is not search words
  const us = US_WORD.test(raw) || /\bu\.s\.|\bamerican\b/i.test(raw)
    || /(?<!\b(?:tell|show|help|give|let|for|to|with|of|from|ask|about|send|join|email|call|contact|both|all|each|many|some|most)\s)\bus\s+(?!(?:know|out|up|in|on|at|a|an|the|with|to|about|and|or)\b)[a-z]/i.test(raw);
  const t = clean(raw).replace(/'s\b/g, '').replace(/\bu\.s\.a?\b|\bamerican\b/g, ' ').replace(/\bglobal x\b/g, 'globalx').replace(/\breal estate\b/g, 'reit')
    .replace(/\b(s&p|sp|nasdaq|tsx|russell|dow)\s?(\d{2,4})\b/g, (m, a, n) => `${a === 'sp' ? 's&p' : a} ${n}`);
  const words = t.replace(/[^\p{L}\p{N}\s&]/gu, ' ').split(/\s+/).filter(w => w.length > 1 && !FILLER.has(w));
  return us ? ['usregion', ...words.filter(w => w !== 'usregion')] : words;
}
/** "US", "U.S.", "USA" or "American" in a message (the country, written as such). */
const US_WORD = /\bU\.?S\.?A?\b|\bAmerican\b/;
/** Search words with a meaning wider than their letters: the region, equity funds for "stocks", a fund family. */
export const ALIASES = { usregion: /\bU\.?S\.?\b|\bUS\b|\bAmeric|(?:^|\| )US(?: |$)/, stock: /(?:^|\| )Equity\b|\bstocks?\b|\bequit(?:y|ies)\b/i, globalx: /\bGlobal X\b/i, inflation: /inflation|real return|\bTIPS\b/i, money: /money market|(?:^|\| )Cash\b/i, reit: /\bREITs?\b|real estate/i };
/** A word reduced so it matches its plural and singular forms as a prefix ("bonds" -> "bond", "equities" -> "equity"). */
export function stem(w) { return w.length > 3 ? w.replace(/ies$/, 'y').replace(/(?<=[^s])(?:es|s)$/, '') : w; }
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** A pattern for a search word as a whole word, singular or plural ("reit" finds "REITs", "equity" finds "Equities",
 *  "gold" does not find "Goldman"). */
export function wordPattern(w) {
  const s = reEsc(stem(w)), alt = /y$/.test(s) ? `${s}|${s.slice(0, -1)}ies` : `${s}(?:s|es)?`;
  return new RegExp(`(?<![\\p{L}\\p{N}])(?:${alt})(?![\\p{L}\\p{N}])`, 'iu');
}
/** A pattern for a search word as the start of a word ("tech" finds "Technology"). */
export function prefixPattern(w) { return new RegExp(`(?<![\\p{L}\\p{N}])${reEsc(stem(w))}`, 'iu'); }

/** The glossary key a message asks about, or null. loose: any mention counts (for the assistant's explain_term). */
export function matchTerm(text, { loose = false } = {}) {
  const raw = String(text || ''), t = clean(raw);
  for (const [k, re, mode] of TERMS) {
    if (!re.test(t)) continue;
    if (loose || mode === 'any') return k;
    const rest = searchWords(raw.replace(new RegExp(re.source, 'gi'), ' '));  // the original text, so "U.S." still counts
    if (!rest.length) return k;  // only the term: "reits", "covered call etf", "emerging markets"
    if (DEFINE_RX.test(t) && !FUND_RX.test(t)) return k;  // "what is a REIT", "how do bonds work" (not "what are some bond etfs")
  }
  return null;
}

/** What a message asks for without the assistant: {kind: 'term', key, theme} | {kind: 'context'} | {kind: 'search', words}. */
export function routeText(text) {
  const raw = String(text || ''), t = clean(raw), fund = FUND_RX.test(t), key = matchTerm(raw);
  if (key) {
    const mode = TERMS.find(x => x[0] === key)[2];
    if (fund && mode === 'ask' && !DEFINE_RX.test(t)) return { kind: 'search', words: searchWords(raw), fund };  // "bond etfs"
    return { kind: 'term', key, theme: THEMES[key] || null };
  }
  const words = searchWords(raw);
  // "are etfs safe?", "the difference between an etf and a mutual fund": a question about ETFs themselves
  if (/\betfs?\b/.test(t) && (asksQuestion(raw) || /\b(?:vs\.?|versus|compared?)\b/.test(t)) && words.every(w => GENERIC.has(w))) return { kind: 'term', key: 'etf', theme: null };  // also "etf vs mutual fund\"
  if (SWITCH_RX.test(t)) return { kind: 'switch' };  // "which market", "change the market to US": the toggle at the top
  if (!fund && CONTEXT_RX.test(t)) return { kind: 'context' };
  return { kind: 'search', words, fund };
}
