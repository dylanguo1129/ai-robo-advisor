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
  return Math.round(Number(m[1]) * (MULT[m[2]] || 1));
}

const OUT_WORDS = /take[ -]?out|taking out|withdraw(?:al|ing)?|draw(?:ing)?(?:[ -]?down)?|spend(?:ing)?/i;

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
  return /[?]/.test(s) || /^(how|what|why|which|who|when|where|is|are|am|can|could|should|would|does|do|did|will|compare|explain|tell me)\b/i.test(s);
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
  const src = String(text || ''), out = {};
  const t = src.replace(/\b(?:401|403|457)\s?\(?[kb]\)?/gi, (m) => ' '.repeat(m.length));  // account names, not amounts
  const low = t.toLowerCase();
  const ca = /canad|\bcad\b|\btsx\b|\btfsa\b|\brrsp\b|\bfhsa\b|toronto|vancouver|montreal|calgary|ottawa/i.test(t);
  const us = /\bu\.?s\.?a?\b|united states|america|\busd\b|\b401\s?\(?k\)?|\bira\b|\broth\b|\bhsa\b/i.test(src);
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
