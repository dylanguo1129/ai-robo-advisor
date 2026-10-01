/* Number and ticker provenance check for the assistant's replies (port of robokit/validate.py).
 * A number in a reply is accepted only when it is a rounding of a number in the tool results
 * (as written, as a percentage, or in thousands/millions); small counts (0-12) and years pass.
 * Tickers must be in the fund list or in the tool results.
 * Boundaries are spelled out as ASCII classes so the rule reads the same as the Python version
 * (where \w would also match non-ASCII letters and skip a number written right against one). */
const NUM = /(?<![A-Za-z0-9_.])[-−+]?(\$)?\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s?(%|k|K|M|B|bn)?(?![A-Za-z0-9_])/g;
const TICKER = /(?<![A-Za-z0-9])([A-Z]{2,5}(?:[.-][A-Z])?(?:\.(?:TO|NE))?)(?![A-Za-z0-9])/g;
// Capitalised words that are not tickers: account types, agencies, indexes, units and plain English.
const COMMON = new Set([
  'ETF', 'ETFS', 'ETN', 'ETNS', 'MER', 'AUM', 'NAV', 'USD', 'CAD', 'FX', 'US', 'USA', 'UK', 'EU', 'TSX', 'NYSE', 'AI', 'LLM',
  'TFSA', 'RRSP', 'RRIF', 'FHSA', 'RESP', 'LIRA', 'RDSP', 'CPP', 'QPP', 'OAS', 'GIS', 'CRA', 'IRA', 'ROTH', 'HSA', 'IRS',
  'FDIC', 'CDIC', 'HISA', 'GIC', 'APR', 'APY', 'YTD', 'CPI', 'PCE', 'GDP', 'PMI', 'EPS', 'VIX', 'REIT', 'REITS', 'TIPS',
  'OK', 'FAQ', 'DIY', 'CEO', 'CFO', 'IPO', 'ID', 'EN', 'PDF', 'API', 'MCP', 'BL', 'HRP', 'CAPM', 'CMA', 'KYC', 'ESG',
  'CSA', 'CIRO', 'OSC', 'AMF', 'SEC', 'FINRA', 'FCAC', 'OBSI', 'NFCC', 'FP', 'IFP', 'EPU', 'GPR', 'GDELT', 'FRED', 'BOC',
  'FOMC', 'FED', 'ECB', 'BOJ', 'IMF', 'OECD', 'OPEC', 'NATO', 'WTO', 'CUSMA', 'USMCA', 'NAFTA', 'EV', 'CDR',
  'BMO', 'RBC', 'TD', 'CIBC', 'EAFE', 'MSCI', 'FTSE', 'SP', 'S&P', 'NOTE', 'YES', 'NO', 'AND', 'OR', 'THE', 'NOT', 'IT',
  'AM', 'PM', 'I', 'A',
]);
// Words a person may type in capitals that are not tickers, for the page's no-AI router
// (several are also real fund symbols: THE, WAR, CASH, SAFE, BOND).
export const COMMON_WORDS = new Set([...COMMON, 'WAR', 'CASH', 'SAFE', 'BOND', 'BONDS', 'GOLD', 'RISK', 'FUND', 'FUNDS', 'BEST', 'HIGH', 'LOW',
  'HYSA', 'WHAT', 'WHY', 'HOW', 'WHO', 'WHEN', 'SELL', 'BUY', 'HOLD', 'NOW', 'NEW', 'TAX', 'RATE', 'RATES', 'NEWS', 'HELP', 'SHOW', 'ME', 'MY', 'IS', 'IN',
  'ON', 'TO', 'OF', 'FOR', 'ALL', 'ANY', 'CAN', 'DO', 'IF', 'BUT', 'SO', 'VS', 'PLS', 'THANKS', 'HI', 'HEY', 'BIG', 'TOP', 'GOOD', 'BAD']);
// Numbers the rules tell the guide to give that no tool returns: the crisis line (call or text 988).
const HELP_NUMBERS = [988];

function parse(m) {
  let v = parseFloat(m[2].replace(/,/g, '') + (m[3] ? '.' + m[3] : ''));
  if (!Number.isFinite(v)) return null;
  const u = m[4];
  if (u === 'k' || u === 'K') v *= 1e3; else if (u === 'M') v *= 1e6; else if (u === 'B' || u === 'bn') v *= 1e9;
  return v;
}

// A small count ("3 funds") passes without a source, unless it counts future events ("2 cuts next year").
const EVENT_AFTER = /^\s*(?:more\s+)?(?:times|cuts?|hikes?|rate\s+cuts?|basis\s+points|bps)/i;

/** Numbers as [value, isPercent]: a figure written with % in a string is a percent; a raw number is not,
 * though a fraction (|x| <= 1.5) may be quoted as a percent (0.064 -> 6.4%). Same rule as robokit/validate.py. */
export function collectNumbers(obj, out = []) {
  if (obj == null || typeof obj === 'boolean') return out;
  if (typeof obj === 'number') { if (Number.isFinite(obj)) out.push([obj, false]); return out; }
  if (typeof obj === 'string') { for (const m of obj.matchAll(NUM)) { const v = parse(m); if (v != null) out.push([v, m[4] === '%']); } return out; }
  if (Array.isArray(obj)) { for (const v of obj) collectNumbers(v, out); return out; }
  if (typeof obj === 'object') { for (const v of Object.values(obj)) collectNumbers(v, out); }
  return out;
}

function supported(v, dec, isPct, unit, pool) {
  const tol = 0.5 * 10 ** -dec + 1e-9;
  for (const [a, aPct] of pool) {
    const frac = !aPct && Math.abs(a) <= 1.5;
    let cands = isPct ? (aPct ? [a, Math.abs(a)] : frac ? [a * 100, Math.abs(a) * 100] : []) : [a, Math.abs(a), ...(frac ? [a * 100, Math.abs(a) * 100] : [])];
    if (aPct && !isPct) cands = [];
    if (unit === 'k' || unit === 'K') { const t = 0.5 * 10 ** -dec * 1e3 + 1e-9; if (Math.abs(v - a) <= t || Math.abs(v - Math.abs(a)) <= t) return true; }
    if (unit === 'M' || unit === 'B' || unit === 'bn') { const mult = unit === 'M' ? 1e6 : 1e9; const t = 0.5 * 10 ** -dec * mult + 1e-9; if (Math.abs(v - a) <= t || Math.abs(v - Math.abs(a)) <= t) return true; }
    if (cands.some(c => Math.abs(v - c) <= tol)) return true;
    if (!isPct && !aPct && v >= 1000 && dec === 0 && Math.abs(v - Math.abs(a)) <= Math.max(0.005 * Math.abs(a), 50)) return true;
  }
  return false;
}

const ACCOUNT_NAMES = /\b(?:401|403|457)\s?\(?[kb]\)?/gi;  // US retirement accounts: names, not figures

export function checkReply(text, toolResults, universe = null, extra = []) {
  text = (text || '').replace(ACCOUNT_NAMES, (s) => ' '.repeat(s.length));
  const pool = collectNumbers(toolResults, [...extra, ...HELP_NUMBERS].map(x => [x, false]));
  const bad = [];
  for (const m of (text || '').matchAll(NUM)) {
    const v = parse(m); if (v == null) continue;
    const unit = m[4], dec = (m[3] || '').length;
    const plain = unit == null && dec === 0 && !m[1] && !m[2].includes(',');
    const countsEvents = EVENT_AFTER.test((text || '').slice(m.index + m[0].length));
    if (plain && ((v <= 12 && !countsEvents) || (v >= 1900 && v <= 2100))) continue;  // counts and years ("$" or a comma means money)
    if (!supported(v, dec, unit === '%', unit, pool)) bad.push(m[0].trim());
  }
  const unknown = [];
  if (universe) {
    const toolText = JSON.stringify(toolResults);
    for (const m of (text || '').matchAll(TICKER)) {
      const t = m[1];
      if (COMMON.has(t)) continue;
      if (universe.has(t) || universe.has(t + '.TO') || toolText.includes(t)) continue;
      unknown.push(t);
    }
  }
  return { ok: !bad.length && !unknown.length, unsupported_numbers: [...new Set(bad)], unknown_tickers: [...new Set(unknown)] };
}

export const REWRITE = (items) => `Your reply contained numbers or tickers that are not in this turn's tool results or the page state: ${items}. Rewrite the reply using only numbers and tickers that appear in the tool results, or call a tool to get them. If the data is not available, say so plainly.`;
