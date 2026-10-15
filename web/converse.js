/* The guided page's conversation logic, without the DOM: what a typed message means (an answer, a question, a
 * request for advice, a change to an earlier answer, a ticker), the answers the page can give without AI, and the
 * short texts tied to a mix (one line per fund, the closing recap). Checked under Node by web/test_converse.mjs.
 * Nothing here computes a number: figures come from robokit.js results passed in. */
import { parseAmount, parseMonthly, parseOpener, matchTerm } from './parse.js';
import { COMMON_WORDS } from './validate.js';
import * as KB from './kb.js';

export const norm = (t) => String(t ?? '').toLowerCase().replace(/[’‘`]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim();
const has = (re, t) => re.test(norm(t));

// ------------------------------------------------------------------ what kind of message this is
/** A request for personal advice or a prediction: always answered with the same redirect (the script's one fixed rule). */
const ADVICE = [
  /\bshould i (?:\w+ ){0,2}(?:buy|sell|invest|put|get|pick|choose|go with|hold|move|switch|use)\b/, /\bwhat (?:should|do|would|could|can|must) i (?:\w+ ){0,2}(?:do|buy|invest|pick|choose|get|put|hold|sell)\b/,
  /\btell me what i (?:should|ought to|need to) (?:\w+ ){0,2}(?:do|buy|invest|pick|choose)\b/, /\bwhat(?:'s|s| is) (?:the )?(?:right|smart|best) (?:thing|move|choice)\b/,
  /\bwhat do you think i should\b/, /\b(?:right|best|good|suitable|appropriate|ok|okay) for me\b/, /\bis (?:this|it|that|my|the) (?:a )?good (?:portfolio|mix|idea|investment|choice|plan|level|fund|etf)\b/,
  /\bis [a-z.]{2,8} better than [a-z.]{2,8}\b/, /\bwhich (?:one )?is better\b/,
  /\b(?:do|would) you think i should\b/, /\bcan you (?:advise|suggest|recommend)\b/, /\badvi[cs]e me\b/, /\bgive me (?:some )?(?:advice|a recommendation)\b/,
  /\bis it (?:smart|wise|a good idea|worth it) to (?:buy|sell|invest|put)\b/, /\bworth (?:buying|investing in|it)\b/, /\bwould you (?:invest|buy|put)\b/,
  /\b(?:a good|the right|the) time to (?:buy|sell|invest)\b/, /\bshould i wait (?:for|until)\b/, /\bgo for it\b/, /\byour advice\b/, /\bwhat do you suggest\b/, /\bwhat would you suggest\b/,
  /\b(?:tell|show) me what to (?:buy|invest|do|pick)\b/, /\bjust tell me\b/, /\bwhat (?:etf|fund|stock)s? should i\b/,
  /\bwhich (?:etf|fund|one|stock|option|level)s? (?:is|are|should|would|do you) (?:the )?(?:best|better|i|recommend)/, /\bwhat(?:'s| is| are) the best (?:etf|fund|stock|investment|level|mix|option)s?\b/,
  /\bis (?:it|this|now|today) (?:a )?(?:good|bad|right|smart) (?:time|idea|moment)\b/, /\bwill (?:the )?(?:market|stocks?|prices?|it|they|this|gold|bonds?) (?:go|crash|rise|fall|drop|recover|keep)\b/,
  /\bwhat will (?:the )?(?:market|stocks?|it)\b/, /\b(?:do|would|can) you recommend\b/, /\byour recommendation\b/, /\bwhat do you recommend\b/,
  /\bis [a-z.]{2,8} a good (?:buy|investment|etf|fund|choice)\b/, /\bwhere should i (?:invest|put)\b/, /\bshould i be (?:buying|selling|investing)\b/,
  /\bwhen should i (?:buy|sell|invest)\b/, /\bwhat would you (?:do|buy|pick|choose)\b/,
];
export const isAdvice = (t) => ADVICE.some((re) => re.test(norm(t)));
export const isCrisis = (t) => has(/\b(?:kill myself|suicid\w*|end my life|self[- ]harm|hurt myself|want to die)\b/, t);
export const isMoneyStress = (t) => has(/\b(?:lost my job|laid off|can'?t pay|cannot pay|unpaid bills|eviction|bankrupt\w*|collections? agenc\w*|gambling|in debt up to|drowning in debt)\b/, t);
export const isDontKnow = (t) => has(/^(?:i )?(?:don'?t|do not|dunno|honestly don'?t) know\b|^not sure\b|^no idea\b|^idk\b|^unsure\b|^no clue\b|^(?:i'?m|i am) not sure\b/, t);
export const isSkip = (t) => has(/^(?:skip|pass|next|no thanks|nothing|none|no preference|no preferences|not now|later)\b/, t);
export const isContinue = (t) => has(/^(?:continue|keep going|go on|back(?: to (?:it|building|the (?:questions|portfolio|mix)))?|let'?s (?:continue|go|keep going|build)|ok(?:ay)?,? (?:continue|let'?s go)|carry on|resume|build (?:it|my portfolio|the portfolio))\b/, t);
export const wantsLearnMore = (t) => has(/\blearn more\b|\bexplain\b|\bi don'?t (?:understand|get it)\b|\bwhat do you mean\b|\bwhat does (?:this|that|it) mean\b|\bconfus\w*\b|\bhelp me understand\b|\bmore (?:info|information|detail)\b|^help\b|^\?+$/, t);
export const asksWhy = (t) => has(/\bwhy (?:do|did) you (?:ask|need)\b|\bwhy (?:this|that) question\b|\bwhy does (?:this|that|it) matter\b|\bwhy does time matter\b|\bwhy does income matter\b/, t);
/** A question rather than an answer: a question mark, a question word first, or an ask to explain. */
export function isQuestionText(t) {
  const s = norm(t);
  return /\?\s*$/.test(s) || /^(?:how|what|what's|whats|why|which|who|when|where|is|are|am|can|could|should|would|does|do|did|will|explain|tell me|define|meaning of)\b/.test(s) || wantsLearnMore(s);
}

// ------------------------------------------------------------------ answers typed in words
const n1 = (s) => { const m = String(s).match(/(\d+(?:\.\d+)?)/); return m ? Number(m[1]) : null; };
const WORDNUM = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, fifteen: 15, twenty: 20, thirty: 30, forty: 40, a: 1, an: 1, couple: 2, few: 3 };
const numIn = (s) => { const d = n1(s); if (d != null) return d; const m = norm(s).match(/\b(one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|a couple|a few|an?)\b(?= (?:of )?(?:years?|yrs?|months?|decades?))/); return m ? WORDNUM[m[1].replace(/^a /, '')] : null; };

/** The calibration answer (step 00). */
export function parseDepth(t) {
  const s = norm(t);
  if (/\b(?:know (?:this|it|etfs?|them) (?:well|very well)|experienced|expert|advanced|a lot|years of|regularly|professional|keep it brief|pro)\b/.test(s)) return 'expert';
  if (/\b(?:nothing|new|beginner|never|first time|no experience|no idea|not much|very little|don'?t know (?:much|anything)|know nothing|explain as we go|newbie|novice)\b/.test(s)) return 'novice';
  if (/\b(?:some|basics?|a bit|a little|a few|intermediate|okay|decent|somewhat|bought (?:a few|some))\b/.test(s)) return 'some';
  return null;
}
/** A goal (A1) named in words. */
export function parseGoal(t) {
  const s = norm(t);
  if (/\bretir\w*|\bpension\b/.test(s)) return 'retirement';
  if (/\b(?:house|home|condo|down ?payment|mortgage|apartment|property|car|wedding|major purchase|big purchase)\b/.test(s)) return 'home';
  if (/\b(?:school|tuition|education|universit\w*|college|resp|kids?'? (?:school|education))\b/.test(s)) return 'education';
  if (/\b(?:income|dividends?|spend (?:it|now)|live (?:off|on)|cash ?flow)\b/.test(s)) return 'income';
  if (/\b(?:learn\w*|practi[cs]e|curious|just looking|explor\w*|understand investing)\b/.test(s)) return 'learning';
  if (/\b(?:wealth|grow\w*|long[- ]term|future|general|save more|build (?:up )?(?:savings|money))\b/.test(s)) return 'wealth';
  return null;
}
/** When withdrawals start (B1), from words or numbers. {value, sure}: sure=false when the words were vague. */
export function parseHorizon(t, { year = new Date().getFullYear() } = {}) {
  const s = norm(t);
  const bucket = (y) => (y < 2 ? 'lt2' : y < 5 ? '2to4' : y < 10 ? '5to9' : y < 20 ? '10to19' : '20plus');
  const age = s.match(/\b(?:i'?m|i am|age(?:d)?|at) (\d{2})\b(?! years? (?:from|until|till))/), retireAt = s.match(/\bretir\w* (?:at|by|around) (\d{2})\b/);
  if (age && retireAt && Number(retireAt[1]) > Number(age[1])) return { value: bucket(Number(retireAt[1]) - Number(age[1])), sure: true };
  const yr = s.match(/\b(?:in|by|around|until) (20[2-9]\d)\b/); if (yr) return { value: bucket(Number(yr[1]) - year), sure: true };
  const months = s.match(/(\d+(?:\.\d+)?|a few|a couple of|six|three)\s*months?\b/);
  if (months) return { value: 'lt2', sure: true };
  const m = s.match(/(?:(within|under|less than|fewer than|before|up to|in|over|more than|after|at least)\s+)?(?:the next\s+)?(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|a couple of|a few)(?:\s*(?:-|to|or)\s*(\d+))?\s*(?:\+\s*)?(years?|yrs?|decades?)\b/);
  if (m) {
    let y = Number(m[2]) || WORDNUM[m[2].replace(/^a (?:couple of|few)$/, (x) => (x.includes('couple') ? 'couple' : 'few'))] || 0;
    if (m[3]) y = (y + Number(m[3])) / 2;
    if (/decade/.test(m[4])) y *= 10;
    if (/within|under|less than|fewer than|before|up to/.test(m[1] || '')) y -= 0.5;
    if (/more than|after|at least|over/.test(m[1] || '') && !m[3]) y += 0.5;
    return { value: bucket(y), sure: true };
  }
  if (/\b(?:next year|this year|right away|asap|immediately|very soon|soon)\b/.test(s)) return { value: 'lt2', sure: true };
  if (/\b(?:a long time|decades|forever|never|no rush|when i'?m old)\b/.test(s)) return { value: '20plus', sure: false };
  if (/\bshort[- ]term\b/.test(s)) return { value: '2to4', sure: false };
  if (/\b(?:medium|mid)[- ]term\b/.test(s)) return { value: '5to9', sure: false };
  if (/\blong[- ]term\b/.test(s)) return { value: '10to19', sure: false };
  return null;
}
/** How withdrawals are taken (B2). */
export function parseWithdrawal(t) {
  const s = norm(t);
  if (/\ball at once|lump|one go|in one shot|single withdrawal|once\b/.test(s)) return 'once';
  if (/\bnot sure|don'?t know|no plan|unsure\b/.test(s)) return 'unsure';
  if (/\b(?:rest of my life|decades|long time|for ever|forever|indefinitely)\b/.test(s)) return '10plus';
  const y = numIn(s);
  if (y != null && /year|yr/.test(s)) return y <= 1 ? 'once' : y <= 5 ? '2to5' : y <= 10 ? '6to10' : '10plus';
  if (/\b(?:a few|couple of|several) years\b/.test(s)) return '2to5';
  return null;
}
export function parseEmergency(t) {
  const s = norm(t);
  if (/\b(?:partly|partial|some|a bit|kind of|sort of|working on it|half|not enough|a little)\b/.test(s)) return 'partly';
  if (/^(?:no|nope|nah|not yet|none|i don'?t|don'?t)\b|\bno (?:savings|emergency)\b/.test(s)) return 'no';
  if (/^(?:yes|yeah|yep|yup|i do|i have|sure|definitely|of course|absolutely)\b|\b\d+ months\b/.test(s)) return 'yes';
  return null;
}
export function parseDebt(t) {
  const s = norm(t);
  if (/^(?:no|nope|nah|none|i don'?t|zero)\b|\bno debt\b|\bpaid (?:it )?off\b|\bdebt[- ]free\b/.test(s)) return 'no';
  if (/\b(?:a lot|lots|loads|huge|big|a ton|significant|maxed)\b/.test(s)) return 'lot';
  if (/\b(?:a little|a bit|small|some|minor|a few hundred)\b/.test(s)) return 'little';
  return null;  // a bare "yes" leaves which one open: the page asks
}
export function parseIncome(t) {
  const s = norm(t);
  if (/\bretired\b|\bpension\b|\bretirement income\b/.test(s) && !/\bretir(?:e|ing) (?:in|at|by)\b/.test(s)) return 'pension';  // saving for retirement is a goal, not a pension
  if (/\b(?:no (?:regular )?income|unemployed|student|not working|between jobs|no job|out of work)\b/.test(s)) return 'none';
  if (/\b(?:varies|varied|irregular|freelanc\w*|self[- ]employed|commission|gig|seasonal|contract\w*|part[- ]time|uneven|unpredictable|up and down)\b/.test(s)) return 'varies';
  if (/\bmostly\b|\bfairly\b|\busually\b/.test(s)) return 'mostly';
  if (/\b(?:very steady|steady|stable|salary|salaried|full[- ]time|permanent|fixed|guaranteed|government job)\b/.test(s)) return 'very';
  return null;
}
export function parseComfort(t) {
  const s = norm(t);
  if (/\b(?:low|conservative|safe|careful|cautious|not much|little|steady|nervous|scared|risk[- ]averse)\b/.test(s)) return 'low';
  if (/\b(?:high|aggressive|a lot|lots|very comfortable|big swings|risk[- ]taker|bold)\b/.test(s)) return 'high';
  if (/\b(?:medium|moderate|middle|balanced|some|average|in between|okay|fine)\b/.test(s)) return 'medium';
  return null;
}
export function parseDrop(t) {
  const s = norm(t);
  if (/\b(?:don'?t know|not sure|no idea|unsure)\b/.test(s)) return 'dont_know';
  if (/\bbuy (?:more|the dip|in)\b|\badd more\b|\binvest more\b/.test(s)) return 'buy';
  if (/\bsell (?:some|part|a bit|half|a little)\b|\btake some (?:out|off)\b/.test(s)) return 'sell_some';
  if (/\bsell (?:all|everything|it all)?\b|\bget out\b|\bcash out\b|\bpanic\b|\bpull (?:it|everything|out)\b/.test(s)) return 'sell_all';
  if (/\b(?:hold|wait|nothing|stay|keep|ride it out|stay the course|leave it|do nothing)\b/.test(s)) return 'wait';
  return null;
}
export function parseShare(t) {
  const s = norm(t);
  if (/\b(?:not sure|don'?t know|no idea)\b/.test(s)) return null;
  const p = s.match(/(\d+(?:\.\d+)?)\s*(?:%|percent)/);
  if (p) { const v = Number(p[1]); return v < 10 ? 'lt10' : v < 25 ? '10to25' : v < 50 ? '25to50' : v <= 75 ? '50to75' : 'gt75'; }
  if (/\b(?:all|everything|almost all|nearly all)\b/.test(s)) return 'gt75';
  if (/\b(?:most|majority|more than half)\b/.test(s)) return '50to75';
  if (/\b(?:half)\b/.test(s)) return '25to50';
  if (/\b(?:quarter)\b/.test(s)) return '10to25';
  if (/\b(?:small|tiny|little|bit)\b/.test(s)) return 'lt10';
  return null;
}
export function parseWorry(t) {
  const s = norm(t);
  if (/\bboth\b|\bequally\b/.test(s)) return 'both';
  if (/\bmiss\w*|\bfomo\b|\bgains?\b/.test(s)) return 'missing';
  if (/\blos\w*\b|\bloss\b/.test(s)) return 'losing';
  return null;
}
const ORDINAL = { first: 1, second: 2, third: 3, fourth: 4, fifth: 5, last: 5, middle: 3 };
export function parseCard(t) {
  const s = norm(t);
  const m = s.match(/^(?:card |option |#|no\.? ?)?([1-5])(?:st|nd|rd|th)?\b/); if (m) return m[1];
  const o = s.match(/\b(first|second|third|fourth|fifth|last|middle)\b/); return o ? String(ORDINAL[o[1]]) : null;
}

/** An option chosen by number ("2"), by its exact text, or by a unique part of its text. */
export function matchOption(options, text) {
  const s = norm(text).replace(/[.!]+$/, '');
  const n = s.match(/^(?:option |#|no\.? ?)?(\d)$/); if (n) return options[Number(n[1]) - 1]?.value ?? null;
  const exact = options.find((o) => norm(o.text) === s || norm(o.value) === s); if (exact) return exact.value;
  if (s.length < 3) return null;
  const hits = options.filter((o) => norm(o.text).includes(s) || s.includes(norm(o.text)));
  return hits.length === 1 ? hits[0].value : null;
}

/** What a typed message answers for one step. Returns an engine value (or {B3, MONTHLY} for the money step), or null. */
export function parseStep(id, text, options = [], ctx = {}) {
  const viaOption = () => (options.length ? matchOption(options, text) : null);
  switch (id) {
    case 'EXP': return viaOption() ?? parseDepth(text);
    case 'A1': return viaOption() ?? parseGoal(text);
    case 'B1': { const o = viaOption(); if (o) return o; const h = parseHorizon(text, ctx); return h && h.sure ? h.value : null; }
    case 'B2': return viaOption() ?? parseWithdrawal(text);
    case 'A2': return viaOption() ?? parseEmergency(text);
    case 'A3': return viaOption() ?? parseDebt(text);
    case 'B5': return viaOption() ?? parseIncome(text);
    case 'C0': return viaOption() ?? parseComfort(text);
    case 'C2': return viaOption() ?? parseDrop(text);
    case 'B4': return viaOption() ?? parseShare(text);
    case 'C4': return viaOption() ?? parseWorry(text);
    case 'C1': case 'C3': return parseCard(text);
    case 'MONEY': {
      text = String(text).replace(/(\d),(?=\d{3}\b)/g, '$1');  // "15,000" is one amount, not 15 and 000
      const monthlyWords = /(?:a|per|each|every)\s*month|monthly|\/\s*mo/i.test(text);
      const out = {};
      const parts = String(text).split(/\band\b|,|;|\bplus\b/i);
      for (const part of parts) {
        if (/(?:a|per|each|every)\s*month|monthly|\/\s*mo/i.test(part)) { const v = parseMonthly(part); if (v != null && v >= 0) out.MONTHLY = v; }
        else { const v = parseAmount(part.replace(/^[^\d$]*(?=[\d$])/, '').replace(/\s*(?:to start|to invest|now|today|upfront|up front)\s*$/i, '')); if (v != null && v > 0) out.B3 = v; }
      }
      if (!('B3' in out) && !('MONTHLY' in out) && !monthlyWords) { const v = parseAmount(text); if (v != null && v > 0) out.B3 = v; }
      if (!Object.keys(out).length) { const o = parseOpener(text); if (o.amount > 0) out.B3 = o.amount; if (o.monthly > 0) out.MONTHLY = o.monthly; }
      return Object.keys(out).length ? out : null;
    }
    default: return viaOption();
  }
}

/** Several facts in one message ("25 years, $50k, high risk"), for people who prefer to type. Only clear facts. */
export function extractFacts(text, ctx = {}) {
  const out = {};
  const s = norm(text);
  const goal = parseGoal(s); if (goal) out.A1 = goal;
  const h = parseHorizon(s, ctx); if (h) out.B1 = h;  // {value, sure}
  const o = parseOpener(text);  // amounts inside a sentence ("I have $50k for retirement")
  if (o.amount > 0) out.B3 = o.amount;
  if (o.monthly > 0) out.MONTHLY = o.monthly;
  const clauses = s.split(/[,;.]|\band\b|\bbut\b|\bplus\b/);
  const riskC = clauses.find((c) => /\brisk\b|\bcomfort/.test(c));
  if (riskC) { const c = parseComfort(riskC.replace(/\b(?:risk|comfort\w*)\b/g, '')); if (c) out.C0 = c; }
  const incC = clauses.find((c) => /\bincome\b|\bjob\b|\bsalary\b|\bsalaried\b|\bfreelanc|\bretired\b|\bpension\b|\bretirement income\b|\bwork\b/.test(c));
  if (incC) { const i = parseIncome(incC); if (i) out.B5 = i; }
  if (/\b(?:new to|beginner|first time|never invested|experienced|know (?:this|etfs) well)\b/.test(s)) { const d = parseDepth(s); if (d) out.EXP = d; }
  return out;
}

// ------------------------------------------------------------------ commands: change an earlier answer, add or remove a fund
const LEVEL_WORDS = { conservative: 1, cautious: 2, balanced: 3, moderate: 3, growth: 4, aggressive: 5 };
/** "actually, change my risk to high", "make it level 4", "change the amount to $20k", "I meant 10 years". */
export function parseCommand(text, ctx = {}) {
  const s = norm(text);
  if (/^(?:start over|restart|reset|begin again)\b/.test(s)) return { type: 'restart' };
  const changeish = /\b(?:change|switch|set|make|update|actually|instead|i meant|correct|use|try)\b/.test(s);
  const lvl = s.match(/\blevel (\d)\b/) || (changeish && s.match(/\b(conservative|cautious|balanced|moderate|growth|aggressive)\b/));
  if (lvl && changeish) { const v = Number(lvl[1]) || LEVEL_WORDS[lvl[1]]; if (v >= 1 && v <= 5) return { type: 'level', level: v }; }
  if (changeish && /\brisk\b/.test(s)) { const c = parseComfort(s.replace(/\brisk\b/g, '')); if (c) return { type: 'change', id: 'C0', value: c }; }
  if (changeish && /\b(?:amount|invest(?:ing)?|start(?:ing)? with|have)\b/.test(s)) { const v = parseStep('MONEY', text); if (v?.B3 != null || v?.MONTHLY != null) return { type: 'change', id: 'MONEY', value: v }; }
  if (changeish && /\bmonth/.test(s)) { const v = parseMonthly(s.replace(/^.*?(?=[-\d$])/, '')); if (v != null && v >= 0) return { type: 'change', id: 'MONEY', value: { MONTHLY: v } }; }
  if (changeish && /\byears?\b|\bhorizon\b|\bretire/.test(s)) { const h = parseHorizon(s, ctx); if (h?.sure) return { type: 'change', id: 'B1', value: h.value }; }
  if (changeish && /\bgoal\b/.test(s)) { const g = parseGoal(s.replace(/\bgoal\b/, '')); if (g) return { type: 'change', id: 'A1', value: g }; }
  // an explicit verb reads words in any case; "I want ..." only takes tickers written in capitals ("I want a house" is not a fund)
  const add = s.match(/^(?:please )?(?:add|include|put in)\s+(.+)$/), rem = s.match(/^(?:please )?(?:remove|drop|exclude|take out|delete|leave out)\s+(.+)$/);
  if (add || rem) {
    const tickers = findTickers((add || rem)[1], ctx.symbols, { loose: true, allowCommon: true });
    if (tickers.length) return { type: add ? 'add' : 'remove', tickers };
  }
  const want = String(text).match(/^\s*(?:i want|i'?d like|i like)\s+(.+)$/i);
  if (want) { const tickers = findTickers(want[1], ctx.symbols); if (tickers.length) return { type: 'add', tickers }; }
  return null;
}

/** Tickers named in a message. symbols: Map of upper-case symbol -> yahoo ticker. loose: words in any case count. */
const NOT_TICKERS = new Set([...COMMON_WORDS, 'ETF', 'ETFS', 'MER', 'TFSA', 'RRSP', 'RESP', 'FHSA', 'CAD', 'USD', 'US', 'USA', 'AI', 'OK', 'TSX', 'NYSE', 'IPO', 'REIT', 'REITS', 'ESG', 'GDP', 'CPI', 'VIX', 'FAQ', 'HI', 'NO', 'YES', 'I', 'IM', 'ID', 'IT', 'IS', 'ME', 'MY', 'SO', 'DO', 'OR', 'AND', 'THE', 'ALL', 'ANY', 'CAN', 'ONE', 'TWO', 'NEW', 'BUY', 'NOW', 'HOW', 'WHY', 'WHO', 'LOW', 'HIGH', 'RISK', 'BOND', 'GOLD', 'CASH', 'MORE', 'LESS', 'SAFE', 'BEST',
  'MIX', 'LIFE', 'RATE', 'TECH', 'BANK', 'LONG', 'TERM', 'EASY', 'GOOD', 'HOME', 'FUND', 'PLAN', 'SAVE', 'GROW', 'CORE', 'PLUS', 'EACH', 'NEXT', 'YEAR', 'HELP', 'WORK', 'REAL', 'DATA', 'BIG', 'OLD', 'TEN', 'FIVE', 'MUCH', 'SOME', 'WHAT', 'WHEN', 'TELL', 'ABOUT', 'YOUR', 'MINE', 'OUR', 'THIS', 'THAT', 'THEM', 'WITH', 'FROM', 'INTO', 'OVER', 'RICH', 'RICHER', 'WAY', 'GO', 'UP', 'DOWN', 'ON', 'OFF', 'IN', 'OUT', 'BY', 'AT', 'AS', 'IF', 'BE', 'WE', 'HE', 'SHE', 'HER', 'HIS', 'AM', 'AN', 'TO', 'OF']);
export function findTickers(text, symbols, { loose = false, allowCommon = false } = {}) {
  if (!symbols) return [];
  const out = [];
  for (const m of String(text).matchAll(/(?<![\w.$-])([A-Za-z]{2,5}(?:[.-][A-Za-z]{1,2})?)(?![\w-])/g)) {
    const raw = m[1], up = raw.toUpperCase(), base = up.replace(/\.(TO|NE|V|CN)$/, '');
    if (NOT_TICKERS.has(base) && !(allowCommon && symbols.has(base)) && !(raw === up && symbols.has(base) && !COMMON_WORDS.has(base))) continue;
    if (!loose && raw !== up) continue;  // in running text only capitals count ("vfv" only after "add")
    if (raw !== up && /\b(?:my|this|the|our|your|a|an)\s+$/i.test(String(text).slice(0, m.index))) continue;  // "my mix", "the fund"
    const y = symbols.get(up) || symbols.get(base);
    if (y && !out.includes(y)) out.push(y);
  }
  return out;
}

// ------------------------------------------------------------------ answers without AI
const pct = (x, nd = 2) => (x == null || !Number.isFinite(x) ? null : `${(Math.round(x * 100 * 10 ** nd) / 10 ** nd).toFixed(nd)}%`);
const money = (v) => `$${Math.round(v).toLocaleString('en-CA')}`;
const sizeTxt = (aum) => (aum == null ? null : aum >= 1e9 ? `$${(aum / 1e9).toFixed(1)} billion` : `$${Math.round(aum / 1e6).toLocaleString('en-CA')} million`);
const KIND = { Equity: 'stock', 'Fixed income': 'bond', Cash: 'cash', 'Real estate': 'real estate', Commodity: 'commodity', 'Multi-asset': 'multi-asset', Alternative: 'alternative' };

/** What a fund is, and the answer to one question about it, from its facts (and the issuer holdings for default funds). */
export function fundAnswer(f, text = '', { holds = null, plain = null } = {}) {
  if (!f) return null;
  const s = norm(text), sym = f.symbol || f.yahoo, kind = KIND[f.asset_class] || (f.asset_class || '').toLowerCase();
  const holdLine = holds ? `${sym} holds ${holds.holds}.` : plain ? `${sym}: ${plain}` : `${sym} is a ${kind} ETF${f.region ? ` focused on ${f.region === 'Global' ? 'markets around the world' : f.region}` : ''}${f.theme ? ` (${f.theme.toLowerCase()})` : ''}.`;
  const top = holds?.top?.length ? `Its largest holdings (as of ${holds.as_of}, from the issuer): ${holds.top.slice(0, 3).map(([n, w]) => `${n} ${w.toFixed(2)}%`).join(', ')}.` : '';
  if (/\b(?:hold|holds|holding|own|owns|inside|in it|made of|consist|example|stocks? in|companies|what'?s in|contain)\b/.test(s)) {
    if (holds) {
      const notStocks = f.asset_class !== 'Equity' && f.asset_class !== 'Real estate' && /\bstocks?\b|\bcompan/.test(s);
      return `${notStocks ? `${sym} holds no stocks: ` : ''}${holdLine} ${top}`.replace(/\s+/g, ' ').trim();
    }
    return `${holdLine} I don't have its holdings list here; the issuer (${f.issuer || 'the fund company'}) publishes it in the fund's ETF Facts and on its website.`;
  }
  if (/\b(?:fee|fees|mer|cost|expensive|cheap|charge)\b/.test(s)) return f.mer != null ? `${sym}'s yearly fee (MER) is ${pct(f.mer)}: about ${money(f.mer * 10000)} a year on ${money(10000)}.` : `I don't have ${sym}'s fee; it is in the fund's ETF Facts.`;
  if (/\b(?:return|returns|perform\w*|did|made|gain|grew|growth)\b/.test(s)) {
    const r = [f.ret_1y != null && `${pct(f.ret_1y, 1)} over the last year`, f.ret_3y != null && `${pct(f.ret_3y, 1)} a year over 3 years`, f.ret_5y != null && `${pct(f.ret_5y, 1)} a year over 5 years`].filter(Boolean);
    return r.length ? `${sym} returned ${r.join(', ')}, with distributions reinvested. ${KB.PAST_PERFORMANCE}` : `I don't have ${sym}'s past returns.`;
  }
  if (/\b(?:risk|risky|safe|volatil\w*|swing|drop|fall|lose|crash)\b/.test(s)) {
    const r = [f.vol_3y != null && `its value swung about ${pct(f.vol_3y, 1)} a year over the last 3 years`, f.max_drawdown != null && `its worst fall from a peak was ${pct(f.max_drawdown, 0)}`].filter(Boolean);
    return r.length ? `${sym}: ${r.join(', and ')}. ${KB.PAST_PERFORMANCE}` : `I don't have risk figures for ${sym}.`;
  }
  if (/\b(?:big|size|aum|assets|large|small|popular)\b/.test(s)) return f.aum != null ? `${sym} holds about ${sizeTxt(f.aum)} in total (AUM).` : `I don't have ${sym}'s size.`;
  if (/\b(?:currency|hedg\w*|dollar|cad|usd)\b/.test(s)) return `${sym} trades in ${f.currency === 'USD' ? 'US' : 'Canadian'} dollars${f.hedged ? ' and hedges its currency back to Canadian dollars' : ''}.`;
  if (/\b(?:who|issuer|company|manage\w*|run)\b/.test(s)) return `${sym} is run by ${f.issuer || 'its issuer'}.`;
  if (/\b(?:old|new|age|since|history|start\w*)\b/.test(s)) return f.first_month ? `${sym}'s price history here starts in ${f.first_month.slice(0, 7)}.` : `I don't have ${sym}'s start date.`;
  const facts = [f.mer != null && `fee ${pct(f.mer)} a year`, f.aum != null && `about ${sizeTxt(f.aum)} in assets`, f.issuer && `from ${f.issuer}`].filter(Boolean);
  return `${sym} (${f.name}). ${holdLine} ${top} ${facts.length ? `Key facts: ${facts.join(', ')}.` : ''}`.replace(/\s+/g, ' ').trim();
}

/** The leverage/derivatives heads-up the script shows for every user, every time. */
export function leverageNote(f) {
  if (!f) return null;
  const lev = f.leverage != null && Number(f.leverage) !== 1, deriv = f.derivatives && String(f.derivatives).trim() && !/^none$/i.test(String(f.derivatives).trim());
  const options = /option|covered/i.test(`${f.strategy || ''} ${f.theme || ''}`);
  if (!lev && !deriv && !options) return null;
  return `Heads up: ${f.symbol || f.yahoo} uses ${lev ? 'leverage' : 'derivatives'}${options && !lev ? ' (options)' : ''}, which ${lev ? 'can amplify both gains and losses. It is built for short-term tactical use, not typically for long-term holding' : 'changes how it behaves: for example, selling options adds income but gives up part of the upside'}. This applies regardless of your experience level.`;
}

/** The answer the page can give without AI, or null. ctx: { step, glossary, fund, holds, plain, symbols, M }. */
export function localAnswer(text, ctx = {}) {
  const s = norm(text);
  if (isAdvice(s)) return { kind: 'advice', text: KB.ADVICE_REDIRECT };
  const named = findTickers(text, ctx.symbols, { loose: /\b(?:what is|what's|whats|tell me about|about|explain|is)\b/.test(s) });
  const fundT = named[0] || ctx.fund;
  const aboutFund = named.length || /\b(?:it|its|this (?:fund|etf|one))\b|\b(?:hold|holds|holding|own|fee|fees|mer|cost|return|returns|perform\w*|risky|safe|volatil\w*|size|big|aum|currency|hedg\w*|issuer|who|old|new|history|example)\b/.test(s);
  const defQ = /^(?:what(?:'s| is| are)\b|what does .+ mean\b|define\b|meaning of\b|explain\b)/.test(s) && !/\b(?:it|its|this (?:fund|etf|one))\b/.test(s);
  if (ctx.fund && !named.length && (defQ || !aboutFund)) {
    const k0 = matchTerm(s, { loose: true }), g0 = k0 && ctx.glossary?.[k0]?.en;
    if (g0) return { kind: 'term', key: k0, text: `${g0.term}: ${g0.definition}` };
  }
  if (fundT && ctx.M) { const f = ctx.M.fund(fundT); if (f) return { kind: 'fund', ticker: fundT, text: fundAnswer(f, s, { holds: KB.HOLDINGS[fundT] || null, plain: ctx.plainFor?.(fundT) }) }; }
  if (asksWhy(s) && ctx.step && KB.WHY[ctx.step]) return { kind: 'why', text: KB.WHY[ctx.step] };
  for (const q of KB.FAQ) {
    if (!q.re.test(s)) continue;
    if (q.a === '__WHY__') { if (ctx.step && KB.WHY[ctx.step]) return { kind: 'why', text: KB.WHY[ctx.step] }; continue; }
    if (q.a === '__CARDS__') return { kind: 'learn', text: KB.LEARN[ctx.step === 'C3' ? 'C3' : 'C1'] };
    if (q.a === '__UNSURE__') { if (ctx.step && KB.LEARN[ctx.step]) return { kind: 'learn', text: `A rough guess is fine, and you can change it later. ${KB.LEARN[ctx.step]}` }; continue; }
    return { kind: 'faq', text: q.a };
  }
  const key = matchTerm(s, { loose: true }), g = key && ctx.glossary?.[key]?.en;
  if (g) return { kind: 'term', key, text: `${g.term}: ${g.definition}` };
  for (const [k, t] of Object.entries(KB.TERMS)) if (t.match.test(s) && /\bwhat|\bmean|\bdefine|\bexplain|\?/.test(s)) return { kind: 'term', key: k, text: `${t.term}: ${t.definition}` };
  if ((wantsLearnMore(s) || isDontKnow(s)) && ctx.step && KB.LEARN[ctx.step]) return { kind: 'learn', text: KB.LEARN[ctx.step] };
  return null;
}

/** Terms in a text that have not been defined yet in this session (at most two), with their definitions. */
export function termsIn(text, glossary, defined = new Set()) {
  const out = [], t = String(text);
  for (const [k, re] of Object.entries(KB.GLOSSARY_MATCH)) {
    if (out.length >= 2) break;
    if (defined.has(k) || !re.test(t)) continue;
    const g = glossary?.[k]?.en; if (g) out.push({ key: k, term: g.term, definition: g.definition });
  }
  for (const [k, v] of Object.entries(KB.TERMS)) {
    if (out.length >= 2) break;
    if (defined.has(k) || !v.match.test(t)) continue;
    out.push({ key: k, term: v.term, definition: v.definition });
  }
  return out;
}

// ------------------------------------------------------------------ texts tied to a mix
const SLEEVE_WHY = {
  ca_equity: 'Canadian companies, for growth.', ca_us_equity: 'The largest US companies, for growth.', ca_intl_equity: 'Companies in Europe, Japan and other developed markets, to spread risk beyond North America.',
  ca_em_equity: 'Companies in emerging markets: more growth potential and bigger swings.', ca_agg_bond: 'Canadian bonds, the steadier part of the mix.', ca_short_bond: 'Short-term bonds, which move less when interest rates change.',
  ca_global_bond: 'US bonds with the currency hedged, to spread the bond part beyond Canada.', ca_reit: 'Property companies, a different source of return.',
  ca_gold: 'Gold, which often holds up when stocks fall.', ca_cash: 'Cash at Canadian banks: almost no ups and downs.',
};
/** One line per fund in the mix, tied to what the person said (the script's "[Ticker] — [weight]%. [rationale]"). */
export function rationale(h, ctx = {}) {
  const lvl = ctx.level, eq = ctx.classShare?.Equity ?? 0, fi = ctx.classShare?.['Fixed income'] ?? 0;
  if (ctx.picks?.includes(h.ticker)) { const why = ctx.pickWhy?.[h.ticker]; return `You added this yourself${why && why !== 'your pick' ? ` for ${why}` : ''}; at level ${lvl} your own picks can be up to ${pct(ctx.satCap, 0)} of the mix, and each gets at least a small share so it stays in.`; }
  const base = SLEEVE_WHY[h.sleeve] || h.plain || '';
  const extra = [];
  if (h.sleeve === 'ca_us_equity' && ctx.hedged) extra.push('You asked to hedge US stocks to Canadian dollars.');
  if (ctx.swapped?.[h.sleeve] === h.ticker) extra.push('The lowest-cost fund of its kind, as you asked.');
  if (ctx.esg && /esg|sustain|responsible/i.test(h.name || '')) extra.push('An ESG version, as you asked.');
  if (h.asset_class === 'Equity' && lvl) extra.push(`At level ${lvl}, stocks are ${pct(eq, 0)} of the mix.`);
  if (h.asset_class === 'Fixed income' && lvl) extra.push(`Your level keeps ${pct(fi, 0)} in bonds${ctx.horizonShort ? ', partly because you need the money fairly soon' : ''}.`);
  return [base, ...extra].join(' ');
}

/** The closing recap: 2-3 teaching moments that actually fired, and one general next step. */
export function recap(ctx = {}) {
  const covered = [];
  if (ctx.lowerOf) covered.push(`how your level was set: the lower of what your situation can absorb (${ctx.capacity}) and what you are comfortable with (${ctx.tolerance})`);
  if (ctx.gates?.length) covered.push('why an emergency fund and paying off expensive debt usually come before investing');
  if (ctx.secondChance) covered.push('the gap between how people rate their comfort with risk and how they react to a real drop');
  if (ctx.terms?.length) { const t = ctx.terms.slice(0, 3); covered.push(`what ${t.length > 1 ? `${t.slice(0, -1).join(', ')} and ${t.at(-1)}` : t[0]} mean${t.length > 1 ? '' : 's'}`); }
  if (ctx.badYear) covered.push(`what a bad year could look like in your dollars (${ctx.badYear})`);
  const next = ctx.leverage ? 'read the ETF Facts document for any fund with leverage or derivatives before buying it.' : "read each fund's ETF Facts document on the issuer's website, and check the fees and what it holds, before you invest.";
  return { covered: covered.slice(0, 3), next };
}

/** Preferences typed in words ("low fees, avoid emerging markets, I like tech"): the keys the page's chips use, or null. */
export function parsePrefs(text) {
  const s = norm(text), out = { focus: [], avoid: [] };
  const REGION = { canada: /\bcanad\w*/, us: /\b(?:us|u\.s\.|american|united states)\b/, intl: /\binternational\b|\beurope\w*|\bjapan\w*/, em: /\bemerging\b|\bchina\b|\bindia\b/ };
  const FOCUS = { tech: /\btech\w*|\bai\b|\bsoftware\b/, esg: /\besg\b|\bclean\b|\bgreen\b|\bsustain\w*|\bclimate\b/, dividend: /\bdividends?\b|\bincome\b/, infra: /\binfrastructure\b|\butilit\w*/, banks: /\bbanks?\b|\bfinancials?\b/, energy: /\benergy\b|\boil\b/, small: /\bsmall(?:er)?(?:[- ]cap)?\b|\bmid[- ]cap\b/ };
  const AVOID = { us: /\b(?:us|u\.s\.|american)\b/, em: /\bemerging\b|\bchina\b/, reit: /\breal estate\b|\breits?\b|\bproperty\b/, gold: /\bgold\b/ };
  for (const part of s.split(/[,;.]|\bbut\b|\band\b/)) {
    const neg = /\b(?:avoid|no|not|without|exclude|skip|don'?t want|leave out|except)\b/.test(part);
    for (const [k, re] of Object.entries(neg ? AVOID : FOCUS)) if (re.test(part)) (neg ? out.avoid : out.focus).push(k);
    if (!neg && /\b(?:more|focus|like|prefer|want|overweight|heavier|bigger)\b/.test(part)) for (const [k, re] of Object.entries(REGION)) if (re.test(part) && !(k === 'us' && /\bhedg/.test(part))) (out.regions ||= []).push(k);
  }
  if (/\blow(?:est)?[- ](?:fee|cost)s?\b|\bcheap\w*\b|\bfees? matter\b|\bminimi[sz]e fees\b/.test(s)) out.lowCost = true;
  if (/\bhedg\w*/.test(s) && !/\bno hedg|\bunhedged\b|\bdon'?t hedge/.test(s)) out.hedge = true;
  if (/\bactive\b|\bfactor\b|\bsmart beta\b/.test(s)) out.open = true;
  if (/\blarge(?:r)?\b|\bestablished\b|\bbig(?:ger)? funds?\b|\bliquid\w*/.test(s)) out.large = true;
  return out.focus.length || out.avoid.length || out.regions?.length || out.lowCost || out.hedge || out.open || out.large ? out : null;
}
