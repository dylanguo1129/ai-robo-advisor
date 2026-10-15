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
  /\brecommend\b/, /\b(?:top|your|best) picks?\b/, /\bpick (?:one |a fund |an etf )?for me\b/, /\b(?:choose|decide) for me\b/, /\bhelp me (?:decide|choose|pick)\b/,
  /\bwhich (?:fund|etf|one) would you\b/, /\bgood (?:etf|fund)s? to buy\b/, /\bwhere (?:do|should) i put\b/, /\bwhich (?:fund|etf|one) (?:to|do i|should i) buy\b/,
  /\bis [a-z.]{2,8} a buy\b/, /\bwill [a-z.]{2,8} go (?:up|down)\b/, /\bshould i start with\b/, /\bwhat (?:etf|fund)s? should\b/,
  /\bbest (?:etf|fund|one|option|mix|portfolio)s? for me\b/, /\bwill (?:this|it|they|my (?:mix|portfolio)) (?:make|earn|lose) (?:me )?money\b/, /\bhow much will i (?:make|earn|have)\b/,
  // levels and weights asked about as a personal decision ("should I go to level 5?", "is level 5 too risky for me?")
  /\bshould i (?:go|stay|stick|move|switch|jump|bump|drop) (?:up |down |back )?(?:to|at|with|on) (?:a |the )?(?:level|risk level|lvl|[1-5]\b)/,
  /\bshould i (?:cut|raise|lower|increase|reduce|trim|boost|bump|drop|sell off|add to|top up|change) (?:\w+ ){0,3}(?:to|by) (?:\$?\d|level|zero|nothing)/,
  /\b(?:too (?:risky|safe|aggressive|conservative|much|little|high|low)|a lot|enough|right|risky|safe) for (?:me|someone like me|my situation)\b/,
];
export const isAdvice = (t) => ADVICE.some((re) => re.test(norm(t)));
export const isCrisis = (t) => has(/\b(?:kill myself|suicid\w*|end my life|self[- ]harm|hurt myself|want to die)\b/, t);
export const isMoneyStress = (t) => has(/\b(?:lost my job|laid off|can'?t pay|cannot pay|unpaid bills|eviction|bankrupt\w*|collections? agenc\w*|gambling|in debt up to|drowning in debt)\b/, t);
export const isDontKnow = (t) => has(/^(?:i )?(?:don'?t|do not|dunno|honestly don'?t) know\b|^not sure\b|^no idea\b|^idk\b|^unsure\b|^no clue\b|^(?:i'?m|i am) not sure\b/, t);
export const isSkip = (t) => has(/^(?:skip|pass|next|no thanks|nothing|none|no preference|no preferences|not now|later)\b|\bcan (?:i|we) skip\b|\bskip (?:this|it|that|the (?:boring )?questions?)\b|\brather not (?:say|answer)\b|\bprefer not to (?:say|answer)\b/, t);
/** "ok, let's keep going", "thanks, back to it": a wish to go on, in a short message. */
export const isContinue = (t) => { const s = norm(t).replace(/[.!]+$/, ''); return s.split(' ').length <= 8 && (/^(?:(?:ok(?:ay)?|thanks|thank you|sure|great|cool|got it|alright|right)[,!.]?\s+)*(?:continue|keep going|go on|back(?: to (?:it|building|the (?:questions|portfolio|mix)))?|let'?s (?:continue|go|keep going|build|move on)|carry on|resume|move on|next question|build (?:it|my portfolio|the portfolio))\b/.test(s) || /\b(?:keep going|carry on|back to (?:it|building|the questions)|let'?s (?:continue|keep going|move on))\b/.test(s)); };
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

/** A stated investing background ("I've been investing for 10 years", "I manage my own portfolio"): a sign of experience,
 * never a time horizon. */
const BACKGROUND = /\b(?:(?:been )?(?:investing|invested|trading|traded|managing|managed|running) (?:my own (?:money|portfolio|investments)|for (?:\d+|a few|several|many|over \d+|about \d+) (?:years?|decades?))|i (?:manage|run) my own (?:portfolio|investments|money)|work in (?:finance|asset management|wealth management)|(?:cfa|portfolio manager|financial analyst))\b/;
/** Experience signals in what someone types, for the internal depth (never shown as a label): jargon an expert uses
 * unprompted, several tickers, or a stated background. Returns 'expert', 'novice' or null. */
export function inferDepth(text, { tickers = 0 } = {}) {
  const s = norm(text);
  if (BACKGROUND.test(s)) return 'expert';
  const jargon = (s.match(/\b(?:sharpe|sortino|tracking error|correlation|covariance|rebalanc\w*|drawdown|beta|factor (?:tilt|exposure)|duration|expense ratio|mer|asset allocation|efficient frontier|risk parity|hedged|unhedged|smart beta|market cap(?:italization)?[- ]weighted)\b/g) || []).length;
  if (jargon >= 2 || tickers >= 2 || (jargon >= 1 && tickers >= 1)) return 'expert';
  if (/\b(?:(?:just|still) learning|new to (?:this|investing|etfs?)|never invested|first time investing|beginner|no idea how|don'?t know (?:much|anything) about)\b/.test(s)) return 'novice';
  return null;
}
/** The calibration answer (step 00). */
export function parseDepth(t) {
  const s = norm(t);
  if (/\b(?:know (?:this|it|etfs?|them) (?:well|very well)|experienced|expert|advanced|a lot|years of|regularly|professional|keep it brief|pro)\b/.test(s) || BACKGROUND.test(s)) return 'expert';
  if (/\b(?:nothing|new|beginner|never|first time|no experience|no idea|not much|very little|don'?t know (?:much|anything)|know nothing|explain as we go|newbie|novice|(?:just|still) learning|learning the basics|explain (?:it )?(?:more )?simply|simpler)\b/.test(s)) return 'novice';
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
  const s = norm(t).replace(new RegExp(BACKGROUND.source, 'g'), ' ').replace(PAST_DURATION, ' ');  // "investing for 10 years" is experience, not when the money is needed
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
  if (/\b(?:sell nothing|not sell|wouldn'?t sell|won'?t sell|never sell|don'?t sell|no selling|not selling)\b/.test(s)) return 'wait';  // a "no" before "sell" is holding on
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

/** An option chosen by number ("2"), by its exact text, or by a whole-word part of its text. Several texts may name the
 * same value (each depth's button words): a match counts when it points to one value. */
export function matchOption(options, text) {
  const s = norm(text).replace(/[.!]+$/, '');
  const uniq = [...new Map(options.map((o) => [o.value, o])).values()];
  const n = s.match(/^(?:option |#|no\.? ?)?(\d)$/); if (n) return uniq[Number(n[1]) - 1]?.value ?? null;
  const exact = options.find((o) => norm(o.text) === s || norm(o.value) === s); if (exact) return exact.value;
  if (s.length < 3) return null;
  const re = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const hits = options.filter((o) => { const t = norm(o.text); return t.length >= 4 && (new RegExp(`\\b${re(t)}\\b`).test(s) || (s.length >= 4 && !/\d/.test(s) && new RegExp(`\\b${re(s)}\\b`).test(t))); });
  const vals = [...new Set(hits.map((o) => o.value))];
  return vals.length === 1 ? vals[0] : null;
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
  if (/\b(?:new to|beginner|first time|never invested|experienced|know (?:this|etfs) well|(?:just|still) learning)\b/.test(s) || BACKGROUND.test(s)) { const d = parseDepth(s); if (d) out.EXP = d; }
  // softer signs, shown as a highlighted option to confirm rather than recorded: feelings about risk, and experience
  // read from jargon or tickers (F1: inferred internally, never shown as a label)
  const hints = {};
  const feelC = clauses.find((c) => /\b(?:nervous|scared|worried|anxious|afraid|terrified|hate (?:losing|losses))\b/.test(c));
  if (!out.C0 && feelC) hints.C0 = 'low';
  else if (!out.C0 && clauses.some((c) => /\b(?:don'?t mind|fine with|ok with|okay with|comfortable with) (?:some |big |a lot of )?(?:swings|ups and downs|risk|volatility)\b/.test(c))) hints.C0 = /\bbig|a lot\b/.test(s) ? 'high' : 'medium';
  if (!out.EXP) { const d = inferDepth(text, { tickers: ctx.symbols ? findTickers(text, ctx.symbols).length : 0 }); if (d) hints.EXP = d; }
  if (Object.keys(hints).length) out.hints = hints;
  return out;
}

// ------------------------------------------------------------------ commands: change an earlier answer, add or remove a fund
const LEVEL_WORDS = { conservative: 1, cautious: 2, balanced: 3, moderate: 3, growth: 4, aggressive: 5 };
/** "actually, change my risk to high", "make it level 4", "change the amount to $20k", "I meant 10 years". */
export function parseCommand(text, ctx = {}) {
  const s = norm(text);
  if (/^(?:start over|restart|reset|begin again)\b/.test(s)) return { type: 'restart' };
  const changeish = /\b(?:change|switch|set|make|update|actually|instead|i meant|correct|use|try)\b/.test(s);
  const strong = /\b(?:change|switch|update|actually|instead|i meant|correct(?:ion)?|wait)\b/.test(s);  // "I make 80k a year" is not a change
  const lvl = s.match(/\blevel (\d)\b/) || (changeish && s.match(/\b(conservative|cautious|balanced|moderate|growth|aggressive)\b/));
  if (lvl && changeish) { const v = Number(lvl[1]) || LEVEL_WORDS[lvl[1]]; if (v >= 1 && v <= 5) return { type: 'level', level: v }; }
  // saying how much explanation you want, at any point (F1: self-identification sets the depth for the rest of the session)
  if (/^(?:(?:actually|honestly|well|ok(?:ay)?)[, ]+)?(?:i'?m|i am) (?:a |an |still a |a complete |a total )?(?:beginner|newbie|novice|new to (?:this|investing|etfs?)|just learning|still learning)\b|\bexplain (?:it |things |this )?(?:more )?simply\b|\bsimpler please\b|\bin plain (?:english|words)\b/.test(s)) return { type: 'change', id: 'EXP', value: 'novice' };
  if (/^(?:(?:actually|honestly|well|ok(?:ay)?)[, ]+)?(?:i'?m|i am) (?:an? )?(?:experienced|expert|advanced|seasoned)(?: investor)?\b|\bkeep it (?:brief|short)\b|\bless (?:detail|explanation)\b|\bskip the explanations?\b/.test(s) || (changeish && BACKGROUND.test(s))) return { type: 'change', id: 'EXP', value: 'expert' };
  if (changeish && /\brisk\b/.test(s)) { const c = parseComfort(s.replace(/\brisk\b/g, '')); if (c) return { type: 'change', id: 'C0', value: c }; }
  if (changeish && /\byears?\b|\bhorizon\b|\bretire/.test(s)) { const h = parseHorizon(s, ctx); if (h?.sure) return { type: 'change', id: 'B1', value: h.value }; }
  if (changeish && /\bmonth/.test(s)) { const v = parseMonthly(s.replace(/^.*?(?=[-\d$])/, '')); if (v != null && v >= 0) return { type: 'change', id: 'MONEY', value: { MONTHLY: v } }; }
  if ((changeish && /\b(?:amount|invest(?:ing)?|start(?:ing)? with|have)\b/.test(s)) || (strong && /\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*k\b|\b\d{1,3}(?:,\d{3})+\b|\b\d{3,}\b/.test(s) && !/\byears?\b/.test(s))) { const v = parseStep('MONEY', text); if (v?.B3 != null || v?.MONTHLY != null) return { type: 'change', id: 'MONEY', value: v }; }
  if (changeish && /\bgoal\b|\bsaving for\b/.test(s)) { const g = parseGoal(s.replace(/\bgoal\b/, '')); if (g) return { type: 'change', id: 'A1', value: g }; }
  if (strong && /\b(?:income|job|salary|work|paycheque|paycheck|pension)\b/.test(s)) { const v = parseIncome(s); if (v) return { type: 'change', id: 'B5', value: v }; }
  if (strong && /\bemergenc\w*/.test(s)) { const v = parseEmergency(s.replace(/^.*?emergenc\w*(?: fund| savings)?\W*/, '')) ?? parseEmergency(s.replace(/^.*?\b(?:actually|i meant|change\w*)\b\W*/, '')); if (v) return { type: 'change', id: 'A2', value: v }; }
  if (strong && /\b(?:debt|credit cards?|loans?)\b/.test(s)) { const v = parseDebt(s.replace(/^.*?\b(?:actually|i meant|change\w*|update)\b\W*/, '')) ?? parseDebt(s.replace(/^.*?\b(?:debt|credit cards?|loans?)\b\W*/, '')); if (v) return { type: 'change', id: 'A3', value: v }; }
  if (strong && /\b(?:drop\w*|crash\w*|fall\w*|fell|downturn|dip\w*)\b/.test(s)) { const v = parseDrop(s.replace(/^.*?\b(?:drop\w*|crash\w*|fall\w*|fell|downturn|dip\w*)\b/, '')) ?? parseDrop(s); if (v && v !== 'dont_know') return { type: 'change', id: 'C2', value: v }; }
  // an explicit verb reads words in any case; "I want ..." only takes tickers written in capitals ("I want a house" is not a fund)
  const add = s.match(/^(?:please )?(?:add|include|put in)\s+(.+)$/), rem = s.match(/^(?:please )?(?:remove|drop|exclude|take out|delete|leave out)\s+(.+)$/);
  if (add || rem) {
    const tickers = findTickers((add || rem)[1], ctx.symbols, { loose: true, allowCommon: true });
    const unknown = tickerLike(String(text).replace(/^\s*(?:please\s+)?\S+(?:\s+(?:in|out))?\s+/i, ''), ctx.symbols);
    if (tickers.length || unknown.length) return { type: add ? 'add' : 'remove', tickers, ...(unknown.length ? { unknown } : {}) };
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

/** Words that look like tickers but are not in the data: capitals ("XEQ", "SPY"), or a lone word after "add". */
export function tickerLike(text, symbols) {
  const words = String(text).trim().split(/[\s,;&+]+|\band\b/i).filter(Boolean);
  const out = [];
  for (const w0 of words) {
    const w = w0.replace(/[!?.]+$/, '');
    if (!/^[A-Za-z]{2,6}(?:[.-][A-Za-z]{1,2})?$/.test(w)) continue;
    const up = w.toUpperCase(), base = up.replace(/\.(TO|NE|V|CN)$/, '');
    if (symbols?.has(up) || symbols?.has(base)) continue;
    if (NOT_TICKERS.has(base) || (w !== up && words.length > 1)) continue;
    if (!out.includes(base)) out.push(base);
  }
  return out;
}
function editDistance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
/** The closest tickers in the data to one that is not there (F3): eligible funds first, at most three. rows: the
 * Market's rows ({symbol, yahoo, eligible}). */
export function closestTickers(word, rows = []) {
  const w = String(word).toUpperCase().replace(/\.(TO|NE|V|CN)$/, '').replace(/[^A-Z]/g, '');
  if (w.length < 2) return [];
  const scored = [];
  for (const r of rows) {
    const sy = String(r.symbol || '').toUpperCase(); if (!sy || /-/.test(r.yahoo || '')) continue;
    const dist = editDistance(w, sy), prefix = sy.startsWith(w) || w.startsWith(sy);
    if (dist <= (w.length <= 3 ? 1 : 2) || (prefix && Math.abs(sy.length - w.length) <= 2)) scored.push({ r, score: dist - (prefix ? 0.5 : 0) - (r.eligible ? 0.25 : 0) });
  }
  return scored.sort((a, b) => a.score - b.score || String(a.r.symbol).localeCompare(String(b.r.symbol))).slice(0, 3).map((x) => x.r.yahoo);
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
  if (/\b(?:old|new|age|since|history|start\w*)\b/.test(s)) return /^\d{4}-/.test(f.first_month || '') ? `${sym}'s price history here starts in ${f.first_month.slice(0, 7)}.` : `I don't have ${sym}'s start date.`;  // D3: "NaT" or blank is missing
  const facts = [f.mer != null && `fee ${pct(f.mer)} a year`, f.aum != null && `about ${sizeTxt(f.aum)} in assets`, f.issuer && `from ${f.issuer}`].filter(Boolean);
  return `${sym}${f.name ? ` (${f.name})` : ''}. ${holdLine} ${top} ${facts.length ? `Key facts: ${facts.join(', ')}.` : ''}`.replace(/\s+/g, ' ').trim();
}

/** How a fund uses leverage or derivatives, from its data and, where the data leave it blank, from what its name and
 * issuer say (Hamilton's "Enhanced" funds borrow about 25% more; Harvest's "Leaders Income" funds sell covered calls).
 * One of 'leverage', 'borrowing', 'options', 'futures', 'swaps', 'alternative', or null. */
export function derivativeKind(f) {
  if (!f) return null;
  const d = String(f.derivatives || '').toLowerCase(), name = `${f.name || ''}`, text = `${f.strategy || ''} ${f.theme || ''} ${name}`;
  if ((f.leverage != null && Number(f.leverage) !== 1) || /leverage/.test(d)) return 'leverage';
  if (/\benhanced\b/i.test(name) && !/\b(?:bond|government|duration|fixed income|money market|treasury)\b/i.test(name) && /hamilton|mulvihill|brompton/i.test(`${f.issuer || ''} ${name}`)) return 'borrowing';
  if (/option/.test(d) || /options-based|covered call|option income|premium yield|put[- ]?write|buy-?write/i.test(text) || (/harvest/i.test(`${f.issuer || ''} ${name}`) && /\bincome\b/i.test(name))) return 'options';
  if (/futures/.test(d)) return 'futures';
  if (/swap/.test(d)) return 'swaps';
  if (/\balternative\b|\blong[- ]short\b/i.test(name)) return 'alternative';
  return null;
}
const KIND_NOTE = {
  leverage: 'uses leverage, which can amplify both gains and losses. It is built for short-term tactical use, not typically for long-term holding',
  borrowing: 'is an "Enhanced" fund: funds like this usually borrow to invest more than they hold (often about 25% more), which makes both gains and losses larger',
  options: 'sells options (such as covered calls) on some of what it holds: that adds income but gives up part of the gains when markets rise',
  futures: 'uses futures contracts instead of holding the assets directly, so its returns can differ from the assets it tracks',
  swaps: 'gets its returns through a swap agreement with a bank instead of holding the investments directly, which adds the risk that the bank does not pay',
  alternative: 'is an alternative fund: it may use leverage, short selling or derivatives, so it can behave quite differently from a regular index fund',
};
/** The leverage/derivatives heads-up the script shows for every user, every time (C3). */
export function leverageNote(f) {
  const k = derivativeKind(f);
  return k ? `Heads up: ${f.symbol || f.yahoo} ${KIND_NOTE[k]}. Read its ETF Facts before relying on it. This applies regardless of your experience level.` : null;
}


// E4: is a question about investing at all, and is it a comparison with something that is not an ETF?
const INVESTING = /\b(?:steady|stable|guarantee\w*|safe\w*|hold\w*|own\w*|beta|swing\w*|drops?|fall\w*|worth|costs?|cheap|expensive|sectors?|themes?|compan(?:y|ies)|banks?|tech\w*|energy|utilit\w*|kids?|house|home|tuition|school|job|work\w*|pay\w*|bills?|why|ask\w*|mean\w*|learn\w*|explain\w*|invest\w*|etfs?|funds?|stocks?|shares?|equit\w*|bonds?|portfolio|mix|risk\w*|returns?|fees?|mers?|markets?|money|sav\w*|retir\w*|tfsa|rrsp|fhsa|resp|gics?|dividends?|interest|inflation|index\w*|levels?|tickers?|brokers?|brokerage|accounts?|tax\w*|crypto\w*|bitcoin|gold|cash|real estate|reits?|hedg\w*|volatil\w*|diversif\w*|rebalanc\w*|robo-?kit|page|tool|questions?|answers?|options?|cards?|ranges?|crash\w*|recession|economy|rates?|prices?|dollars?|loans?|debt|mortgage|income|salary|pension|goals?|horizon|years?|months?|emergency|optimi[sz]\w*|shortlist|allocation|assets?|capital|growth|loss\w*|lose|losing|gain\w*|profit\w*|yield\w*|distribution\w*|currency|exchange|tsx|s&p|nasdaq|dow|inflation|economy|financ\w*|wealth|spend\w*|budget\w*|afford\w*)\b/;
const OFF_TOPIC = /\b(?:weather|forecast|poems?|jokes?|recipes?|cook\w*|pasta|dinner|hockey|soccer|football|basketball|baseball|nhl|nba|nfl|game score|who won|movies?|films?|songs?|lyrics|homework|essays?|write (?:me )?(?:a |some )?(?:code|program|story|letter)|travel|vacation|holiday plans|dating|girlfriend|boyfriend|celebrit\w*|horoscope|translate|name for my (?:dog|cat|pet|baby)|capital of|president|election|video games?)\b/;
const OTHER_PRODUCTS = [
  [/\b(?:individual |single |buying )?(?:stocks?|shares)\b(?! (?:etf|fund|market))|\bapple\b|\btesla\b|\bnvidia\b|\bshopify\b|\bamazon\b/, 'individual stocks', 'stock'],
  [/\bgics?\b|\bguaranteed investment/, 'GICs', 'gic'], [/\bmutual funds?\b/, 'mutual funds', 'mutual_fund'],
  [/\bcrypto\w*|\bbitcoin\b|\bethereum\b/, 'crypto', 'crypto'], [/\breal estate\b|\b(?:a |buying a )?(?:house|condo|rental property)\b/, 'real estate', 'real_estate'],
  [/\bsavings accounts?\b|\bhisa\b|\bhigh[- ]interest savings\b/, 'savings accounts', null], [/\bgold (?:bars?|coins?)\b/, 'gold bars or coins', null],
  [/\b(?:buying |individual |government )?bonds?\b(?! (?:etf|fund))/, 'buying bonds directly', 'bond'],
];
const COMPARE = /\b(?:vs\.?|versus|or|better than|worse than|instead of|compared? (?:to|with)|rather than|difference between|differ from|safer than|riskier than)\b/;
/** A comparison of ETFs with another product: { other, key } or null. */
export function etfComparison(text) {
  const s = norm(text);
  if (!/\betfs?\b|\bindex funds?\b|\bthis (?:mix|portfolio)\b|\brobo-?kit\b/.test(s) || !COMPARE.test(s)) return null;
  for (const [re, other, key] of OTHER_PRODUCTS) if (re.test(s.replace(/\betfs?\b/g, ''))) return { other, key };
  return null;
}
/** "What does this question mean?", "what do you mean by steady?": a question about the question on screen. */
const ABOUT_STEP = /\b(?:this|that|the) (?:question|one|option|answer|card|choice)s?\b|\bwhat do you mean\b|\bmean by\b|\bwhich (?:one|option|card) (?:is|fits|means|should)\b|\bwhat (?:does|do) (?:this|that|these|those|it) mean\b|\bi don'?t (?:get|understand)\b|\bconfus\w*|\bhow do i (?:answer|choose|pick)\b|\bwhat should i (?:say|answer|pick here)\b/;
/** E4: clearly outside investing (a fixed list of topics, so a question about the person's own situation is never
 * mistaken for one); anything else unmatched goes to Claude when connected, or the general help without it. */
export const isOffTopic = (t) => { const s = norm(t); return OFF_TOPIC.test(s) && !INVESTING_STRICT.test(s); };
const INVESTING_STRICT = /\b(?:invest\w*|etfs?|funds?|stocks?|bonds?|portfolio|tfsa|rrsp|dividends?|returns?)\b/;

/** The answer the page can give without AI, or null. ctx: { step, glossary, fund, holds, plain, symbols, M }.
 * Fixed wording first (advice redirect, scope, the ETF-only rule, the FAQ), then a definition, then fund facts. */
export function localAnswer(text, ctx = {}) {
  const s = norm(text);
  if (isAdvice(s)) return { kind: 'advice', text: KB.ADVICE_REDIRECT };
  const cmp = etfComparison(s);
  if (cmp) { const t = cmp.key && (ctx.glossary?.[cmp.key]?.en || KB.TERMS[cmp.key]); return { kind: 'etf_only', text: `${KB.ETF_ONLY(cmp.other)}${t ? ` ${t.term}: ${t.definition}` : ''}` }; }
  const named0 = findTickers(text, ctx.symbols, { loose: /\b(?:what is|what's|whats|tell me about|about|explain|is)\b/.test(s) });
  // a lower-case word that is both a ticker and a term ("what is beta?") is the term
  const defQ = /^(?:what(?:'s| is| are)\b|what does .+ mean\b|define\b|meaning of\b|explain\b)/.test(s) && !/\b(?:it|its|this (?:fund|etf|one))\b/.test(s);
  const termKey = matchTerm(s, { loose: true }), termG = termKey && ctx.glossary?.[termKey]?.en;
  const extra = Object.entries(KB.TERMS).find(([, t]) => t.match.test(s) && /\bwhat|\bmean|\bdefine|\bexplain|\?/.test(s));
  const named = named0.filter((y) => !(defQ && (termG || extra) && !new RegExp(`\\b${String(y).replace(/\.(TO|NE)$/, '')}\\b`).test(String(text))));
  const fundT = named[0] || ctx.fund;
  const aboutFund = named.length || /\b(?:it|its|this (?:fund|etf|one))\b|\b(?:hold|holds|holding|own|fee|fees|mer|cost|return|returns|perform\w*|risky|volatil\w*|size|big|aum|currency|hedg\w*|issuer|who|old|new|history|example)\b/.test(s);
  const general = !named.length && (!ctx.fund || defQ || !aboutFund || /\bguarantee\w*|\bcan i lose\b|\blose (?:all|everything|my money)\b/.test(s));  // the honest-uncertainty answer wins, even about one fund
  if (general) {
    for (const q of KB.FAQ) {
      if (!q.re.test(s)) continue;
      if (q.a === '__WHY__') { if (ctx.step && KB.WHY[ctx.step]) return { kind: 'why', text: KB.WHY[ctx.step] }; continue; }
      if (q.a === '__CARDS__') return { kind: 'learn', text: KB.LEARN[ctx.step === 'C3' ? 'C3' : 'C1'] };
      if (q.a === '__UNSURE__') { if (ctx.step && KB.LEARN[ctx.step]) return { kind: 'learn', text: `A rough guess is fine, and you can change it later. ${KB.LEARN[ctx.step]}` }; continue; }
      return { kind: 'faq', text: q.a };
    }
    if (termG) return { kind: 'term', key: termKey, text: termAnswer(termKey, ctx.depth, ctx.glossary, ctx.figs) || `${termG.term}: ${termG.definition}` };  // E1: at the person's depth
    if (extra) return { kind: 'term', key: extra[0], text: `${extra[1].term}: ${extra[1].definition}` };
  }
  if (fundT && ctx.M) { const f = ctx.M.fund(fundT); if (f) return { kind: 'fund', ticker: fundT, text: fundAnswer(f, s, { holds: KB.HOLDINGS[fundT] || null, plain: ctx.plainFor?.(fundT) }) }; }
  if (asksWhy(s) && ctx.step && KB.WHY[ctx.step]) return { kind: 'why', text: KB.WHY[ctx.step] };
  if (ctx.step && KB.LEARN[ctx.step] && (wantsLearnMore(s) || isDontKnow(s) || ABOUT_STEP.test(s))) return { kind: 'learn', text: KB.LEARN[ctx.step] };
  if (!named0.length && isOffTopic(s)) return { kind: 'scope', text: KB.SCOPE };  // last: only when nothing about investing matched
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

/** Preferences typed in words ("low fees, avoid emerging markets, I like tech", "no active funds", "fees under 0.2%",
 * "Canada only"): the keys the page's chips use, or null. Each clause is read on its own, so a "no" or "avoid" applies
 * to its own clause only ("no active funds" turns active funds off; it never turns them on). */
export function parsePrefs(text) {
  const out = { focus: [], avoid: [] };
  const US = /\bu\.s\.?(?=\W|$)|\bamerican\b|\bunited states\b|\bus (?:stocks?|market|equit\w*|companies|funds?|etfs?|exposure|dollars?|only)\b/;
  const REGION = { canada: /\bcanad\w*/, us: US, intl: /\binternational\b|\beurope\w*|\bjapan\w*|\bdeveloped markets?\b/, em: /\bemerging\b|\bchina\b|\bindia\b/ };
  const FOCUS = { tech: /\btech\w*|\bai\b|\bsoftware\b|\bsemiconductors?\b/, esg: /\besg\b|\bclean\b|\bgreen\b|\bsustain\w*|\bclimate\b|\bethical\b|\bresponsible\b/, dividend: /\bdividends?\b|\bincome (?:funds?|etfs?|investing|stream)\b|\bmonthly income\b|\byield\b/, infra: /\binfrastructure\b|\butilit\w*/, banks: /\bbanks?\b|\bfinancials?\b/, energy: /\benergy\b|\boil\b/, small: /\bsmall(?:er)?(?:[- ]cap)?\b|\bmid[- ]cap\b/ };
  const AVOID = { us: US, em: /\bemerging\b|\bchina\b/, reit: /\breal estate\b|\breits?\b|\bproperty\b/, gold: /\bgold\b/ };
  const NEG = /\b(?:avoid|no|not|without|exclude|skip|don'?t want|don'?t like|leave out|except|stay away from|nothing in)\b/;
  for (const raw of String(text).split(/[,;.]|\bbut\b|\band\b/i)) {
    const part = norm(raw), upperUS = /\bUS\b/.test(raw);
    if (!part) continue;
    const neg = NEG.test(part), only = !neg && /\bonly\b|\bjust\b/.test(part);
    if (/\bactive\b/.test(part)) out.open = !neg;
    if (/\bfactor\b|\bsmart beta\b/.test(part)) { if (neg) out.noFactor = true; else out.open = true; }
    if (/\b(?:index|passive)\b/.test(part) && (only || /\b(?:prefer|want|like|stick to)\b/.test(part))) out.open = false;
    if (/\bunhedged\b/.test(part) || (neg && /\bhedg/.test(part))) out.hedge = false;
    else if (/\bhedg\w*/.test(part)) out.hedge = true;
    if ((/\b(?:cad|canadian dollars?)\b/.test(part) && only) || /\b(?:no|avoid|without) (?:usd|us dollars?|currency risk)\b/.test(part)) out.currency = 'CAD';
    const regionHit = (k, re) => re.test(part) || (k === 'us' && upperUS);
    if (only && !/\bhedg|dollars?\b|\bcad\b|\busd\b/.test(part)) for (const [k, re] of Object.entries(REGION)) if (regionHit(k, re)) out.only = k;
    for (const [k, re] of Object.entries(neg ? AVOID : FOCUS)) if (regionHit(k, re) && !(k === 'us' && /\bhedg|dollars?\b/.test(part))) (neg ? out.avoid : out.focus).push(k);
    if (!neg && !only && /\b(?:more|focus|like|prefer|want|overweight|heavier|bigger|add)\b/.test(part)) for (const [k, re] of Object.entries(REGION)) if (regionHit(k, re) && !(k === 'us' && /\bhedg/.test(part))) (out.regions ||= []).push(k);
  }
  const s = norm(text);
  const fee = s.match(/\b(?:fees?|mers?|costs?|expense ratios?)\b[^;,]*?\b(?:under|below|less than|at most|max(?:imum)?(?: of)?|no more than|up to)\s*(\d+(?:\.\d+)?)\s*%/) || s.match(/\b(?:under|below|less than|at most|max(?:imum)?(?: of)?|no more than|up to)\s*(\d+(?:\.\d+)?)\s*%\s*(?:in |a year in |yearly )?(?:fees?|mers?|costs?|expense ratios?)\b/) || s.match(/\b(?:max(?:imum)?|cap)\s+(?:fee|mer)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%/);
  if (fee) { const v = Number(fee[1]); if (v > 0 && v <= 3) out.maxFee = v / 100; }
  if (/\blow(?:est)?[- ](?:fee|cost)s?\b|\bcheap\w*\b|\bfees? matter\b|\bminimi[sz]e fees\b/.test(s)) out.lowCost = true;
  if (/\blarge(?:r)?\b|\bestablished\b|\bbig(?:ger)? funds?\b|\bliquid\w*/.test(s)) out.large = true;
  out.focus = [...new Set(out.focus)]; out.avoid = [...new Set(out.avoid)];
  return out.focus.length || out.avoid.length || out.regions?.length || out.only || out.lowCost || out.maxFee != null || out.hedge != null || out.currency || out.open != null || out.noFactor || out.large ? out : null;
}


// ================================================================== v3.2: open conversation and explanation depth
// The team's PRD v3 (F1, E1) and the reviewer's two points. Pure functions; the fixed words are in kb.js.

// ------------------------------------------------------------------ F1: what the person says about themselves wins
const SELF = {
  novice: /\b(?:i'?m|i am) (?:new|a beginner|a newbie|just (?:starting|learning|getting started))\b|\bnew to (?:this|investing|etfs?|the (?:stock )?market|all (?:of )?this)\b|\bnever (?:invested|bought (?:a|an|any) (?:etf|stock|fund)s?)\b|\bfirst time (?:investing|investor)\b|\bbeginner\b|\bnovice\b|\bjust learning\b|\b(?:don'?t|do not) (?:really )?know (?:much|anything)\b|\bknow (?:nothing|very little)\b|\bexplain (?:everything|as we go|(?:things |it )?(?:more )?simply|in plain)\b|\b(?:plain|simple) (?:english|words|language)\b|\bless jargon\b|\btoo (?:technical|complicated)\b|\blike i'?m (?:five|5|new)\b|\bbrand new\b|\bjust starting\b/,
  some: /\b(?:know|understand) (?:the |some )?basics\b|\bsome (?:experience|knowledge)\b|\ba (?:bit|little) of (?:experience|knowledge)\b|\bbought (?:a few|some) (?:etfs?|funds|stocks)\b|\bintermediate\b|\bsomewhat familiar\b|\bknow what an etf is\b|\bnot an expert\b/,
  expert: /\bknow (?:this|it|etfs?|them|investing) (?:well|very well|inside out)\b|\bexperienced\b|\bexpert\b|\badvanced\b|\bkeep it (?:brief|short)\b|\bskip the basics\b|\bless (?:detail|explanation|text)\b|\b(?:more|go) (?:technical|deeper) from now on\b|\bshow me the (?:numbers|math|maths)\b|\bi (?:work|worked) in (?:finance|investments?|wealth management|asset management|capital markets)\b|\b(?:cfa|cfp|cim|pfp|portfolio manager)\b|\bdiy (?:investor|portfolio)\b|\bmanage my own (?:portfolio|investments|money)\b|\bself[- ]directed\b|\b(?:traded|invested in|been trading) (?:\w+ ){0,2}for (?:years|decades|a long time)\b/,
};
export const EXPERIENCE_YEARS = /\b(?:(?:i'?ve|i have) )?(?:been )?(?:invest(?:ing|ed)|held|owned|traded|trading)\b[^.,;]{0,40}?\bfor (\d+|a few|a couple of|several|many) (?:years?|decades?)\b|\b(\d+|several|many) years? (?:of )?(?:investing|experience)\b/;
const PAST_DURATION = /\b(?:i'?ve|i have|been|held|owned|had|invested|traded|used)\b[^.,;]{0,40}?\bfor (?:the (?:last|past) )?(?:\d+|a few|a couple of|several|many) (?:years?|decades?)\b|\bnever (?:invested|bought|traded)(?: before)?\b/g;
/** A self-identification ("I'm new to this", "keep it brief", "invested for 10 years"): 'novice', 'some', 'expert' or null.
 * Mixed signals ("new to ETFs but I've traded stocks for years") give 'some'. */
export function selfDepth(text) {
  const s = norm(text);
  const hit = Object.keys(SELF).filter((k) => SELF[k].test(s));
  const yrs = s.match(EXPERIENCE_YEARS);
  if (yrs) { const n = Number(yrs[1] ?? yrs[2]); hit.push(Number.isFinite(n) ? (n >= 3 ? 'expert' : 'some') : /several|many/.test(yrs[0]) ? 'expert' : 'some'); }
  const u = [...new Set(hit)];
  if (!u.length) return null;
  if (u.includes('novice') && u.includes('expert')) return 'some';
  return u.includes('novice') ? 'novice' : u.includes('expert') ? 'expert' : 'some';
}
// soft cues, collected only while the depth is not said: jargon, finance numbers, tickers (up); basic questions and
// "I don't understand" outside the risk questions (down). Tickers or account names alone never reach the expert depth.
const BASIC_JARGON = /\b(?:mer|expense ratio|rebalanc\w*|asset allocation|index (?:funds?|etfs?)|all[- ]in[- ]one|volatility|dividend yield|my (?:tfsa|rrsp|fhsa|resp|brokerage|portfolio|holdings)|wealthsimple|questrade|qtrade|interactive brokers|direct investing|investorline)\b/g;
const ADV_JARGON = /\b(?:tracking error|sharpe|sortino|standard deviation|std ?dev|drawdowns?|duration|convexity|beta|alpha|correlation|efficient frontier|mean[- ]variance|black[- ]litterman|risk parity|factor (?:tilts?|investing|etfs?|funds?)|smart beta|covered calls?|swap[- ]based|adjusted cost base|tax[- ]loss harvest\w*|withholding tax|asset location|home bias|glide ?path|\d{2}\/\d{2}(?: portfolio| split| mix)?|currency[- ]hedg\w*|unhedged|bid[- ]ask|over-?weight\w*|under-?weight\w*|tilt\w*)\b/g;
const FIN_NUMBER = /\b\d+(?:\.\d+)?\s?%\s?(?:mer|fee|expense|allocation|equit\w*|stocks?|bonds?)\b|\b(?:mer|fees?) (?:of |under |below |above |at |<\s?|>\s?)?\d/;
const BASIC_Q = /^(?:what(?:'s| is| are| does)|define|meaning of|explain)\b.*\b(?:etfs?|stocks?|bonds?|funds?|index|fees?|mer|risk|portfolio|tickers?|invest\w*|market|dividends?|interest|savings|tfsa|rrsp|shares?)\b/;
const TOLERANCE_STEPS = new Set(['C0', 'C1', 'C2', 'C3', 'C4', 'RECON']);  // "I don't know" there is about risk, not knowledge
const CUE_CAP = { basic: 2, adv: 4, ticker: 2, num: 1, basicQ: -2, dontKnow: -2 };
export function depthCues(text, { step = null, symbols = null } = {}) {
  const s = norm(text), out = [];
  if (step && TOLERANCE_STEPS.has(step)) return out;
  const question = isQuestionText(text) && !/^(?:i |i'm |my )/.test(s);
  if (question) {
    if ((BASIC_Q.test(s) && !(s.match(ADV_JARGON) || []).length) || /^what does .+ mean\b|^what do you mean\b/.test(s)) out.push({ kind: 'basicQ', key: s.slice(0, 40), w: -1 });
  } else {
    for (const m of new Set(s.match(BASIC_JARGON) || [])) out.push({ kind: 'basic', key: m, w: 1 });
    for (const m of new Set(s.match(ADV_JARGON) || [])) out.push({ kind: 'adv', key: m, w: 2 });
    if (FIN_NUMBER.test(s)) out.push({ kind: 'num', key: 'num', w: 1 });
    for (const t of findTickers(text, symbols)) out.push({ kind: 'ticker', key: t, w: 1 });
  }
  if (step && (isDontKnow(s) || /\bwhat does (?:that|this|it) mean\b|\bi don'?t understand\b/.test(s))) out.push({ kind: 'dontKnow', key: `${step}:${s.slice(0, 20)}`, w: -1 });
  return out;
}
/** The depth the soft cues point to, settled once the first questions are answered (F1). */
export function classifyDepth(cues = []) {
  const seen = new Set(), uniq = cues.filter((c) => !seen.has(`${c.kind}:${c.key}`) && seen.add(`${c.kind}:${c.key}`));
  let sum = 0;
  for (const k of Object.keys(CUE_CAP)) { const v = uniq.filter((c) => c.kind === k).reduce((a, c) => a + c.w, 0); sum += CUE_CAP[k] > 0 ? Math.min(v, CUE_CAP[k]) : Math.max(v, CUE_CAP[k]); }
  const strong = uniq.some((c) => ['adv', 'num', 'basic'].includes(c.kind) && !/^my |wealthsimple|questrade|qtrade|interactive|direct|investorline/.test(c.key));
  return sum >= 3 && strong ? 'expert' : sum <= -2 ? 'novice' : 'some';
}

// ------------------------------------------------------------------ reading a whole message, clause by clause
export const TOPIC = {
  EXP: /\b(?:invest(?:ed|ing)? (?:for|since)|been investing|years? of (?:investing|experience)|new to (?:this|investing|etfs?)|first time|beginner|newbie|never invested|just starting|just learning|(?:know|familiar with) (?:etfs?|investing|this|it)\b|(?:don'?t|do not) (?:\w+ ){0,2}know (?:much|anything)|know (?:a bit|the basics|some basics)|keep it (?:brief|short)|skip the basics)/,
  A1: /\b(?:retir\w*|house|home|condo|down ?payment|mortgage|apartment|property|cottage|car|wedding|school|tuition|education|universit\w*|college|resp|income (?:i can spend|now|to live on)|for income|live (?:off|on)|cash ?flow|dividends?|learn\w*|practi[cs]e|wealth|grow (?:my|our|the) money|for the future|save more)\b/,
  B1: /\b(?:years?|yrs?|decades?|months?|20[2-9]\d|next year|this year|right away|asap|soon|long[- ]term|short[- ]term|medium[- ]term|mid[- ]term)\b|\bretir\w* (?:at|by|in|around)\b/,
  B2: /\b(?:all at once|lump|in one go|one shot|bit by bit|a bit at a time|withdraw\w*|draw (?:on|down))\b|\bover\b.*\b(?:years?|decades?)\b/,
  B4: /\b(?:share of|percent of (?:my|all)|% of (?:my|all)|most of (?:my|our) (?:savings|money)|all (?:of )?(?:my|our) savings|everything i have)\b/,
  A2: /\b(?:emergenc\w*|rainy[- ]day|cushion|safety net|savings?|set aside|months? of expenses)\b/,
  A3: /\b(?:debts?|credit[- ]?cards?|loans?|owe|line of credit|payday)\b/,
  MONEY: /\$\s?\d|\b\d[\d,.]*\s?(?:k|grand|thousand|dollars|bucks)\b|\b(?!(?:19|20)\d\d\b)\d{3,}\b|\b(?:a|per|each|every) month\b|\bmonthly\b/,
  B5: /\b(?:income|salary|salaried|paycheque|paycheck|job|work(?:ing)?|freelanc\w*|self[- ]employed|contract\w*|commission|pension|retired|unemployed|student|full[- ]time|part[- ]time|employ\w*)\b/,
  C0: /\b(?:risk|comfort\w*|cautious|conservative|aggressive|swings|volatil\w*)\b/,
  C2: /\b(?:drops?|dropped|dip|crash\w*|falls?|fell|plunge\w*|downturn)\b|\b(?:sell everything|sell some|hold on|ride it out|buy (?:more|the dip)|panic\w*)\b/,
  C4: /\b(?:worr\w*|regret\w*|missing out|miss out|fomo|afraid of losing|bother\w*)\b/,
};
const START_CUE = /\b(?:in|by|within|until|retir\w*|start\w*|need|from now|away|when|next|this|soon|right away)\b|\b20[2-9]\d\b/;
export const CORRECTION = /\b(?:actually|i meant|sorry|correction|change (?:that|it)|make (?:that|it)|instead|scratch that)\b|^no,/;
const VAGUE_B1 = [[/\blong[- ]term\b|\ba long time\b|\bdecades\b|\bwhen i'?m old\b/, 'long term', ['10to19', '20plus']], [/\bshort[- ]term\b/, 'short term', ['lt2', '2to4']], [/\b(?:medium|mid)[- ]term\b/, 'medium term', ['5to9', '10to19']]];
/** One step's answer from a clause: {value} | {candidates, word} | null. Option values only. */
export function readAnswer(id, text, options = [], ctx = {}) {
  const s = norm(text);
  if (id === 'FT') return /^(?:yes|yeah|sure|ok(?:ay)?|fine[- ]tune|let'?s do it|refine)\b/.test(s) ? { value: 'yes' } : /^(?:no|nope|nah|skip|show|straight|not now)\b/.test(s) ? { value: 'no' } : null;
  if (id === 'RECON') return /\b(?:self|rating|rated|first)\b/.test(s) ? { value: 'C0' } : /\b(?:drop|reaction|react|second|what i'?d do)\b/.test(s) ? { value: 'C2' } : null;
  if (id === 'B1') {
    const bare = s.match(/^(?:about |around |maybe |roughly )?(\d{1,2})\s*\+?$/);
    if (bare) {
      const nn = Number(bare[1]), yrs = nn < 2 ? 'lt2' : nn < 5 ? '2to4' : nn < 10 ? '5to9' : nn < 20 ? '10to19' : '20plus';
      const vals = [...new Set(options.map((o) => o.value))], opt = nn >= 1 && nn <= vals.length ? vals[nn - 1] : null;
      if (!opt || opt === yrs) return { value: yrs };
      return { candidates: [opt, yrs], word: bare[1], num: nn };  // "3": option 3, or 3 years from now
    }
    const h = parseHorizon(text, ctx);
    if (h?.sure && /\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|a few|a couple)\b/.test(s)) return { value: h.value };
    const o = options.length ? matchOption(options, text) : null; if (o) return { value: o };
    if (h?.sure) return { value: h.value };
    for (const [re, word, cands] of VAGUE_B1) if (re.test(s)) return { candidates: cands, word };
    return null;
  }
  if (id === 'A3' && /^(?:yes|yeah|yep|i do|some)\b\W*$/.test(s)) return { candidates: ['little', 'lot'] };
  if (id === 'B2') { const mt = s.match(/\b(?:more than|at least|over) (\d+) (?:years?|yrs?)\b/); if (mt) { const y = Number(mt[1]); return { value: y >= 10 ? '10plus' : y >= 5 ? '6to10' : '2to5' }; } }
  if (id === 'C2' && /^(?:i'?d |i would |probably |maybe )*sell(?: it)?\W*$/.test(s)) return { candidates: ['sell_all', 'sell_some'] };
  if (id === 'C0') { const lo = /\blow\b|\bcautious\b|\bsteady\b/.test(s), mid = /\bmedium\b|\bmoderate\b|\bmiddle\b/.test(s), hi = /\bhigh\b|\baggressive\b/.test(s); if ([lo, mid, hi].filter(Boolean).length === 2) return { candidates: lo && mid ? ['low', 'medium'] : ['medium', 'high'] }; }
  if (id === 'A1') { const hits = ['retirement', 'home', 'education', 'income'].filter((g) => ({ retirement: /\bretir\w*/, home: /\b(?:house|home|condo|down ?payment)\b/, education: /\b(?:school|tuition|education|universit\w*|college|resp)\b/, income: /\bincome (?:i can spend|now)|\blive off\b/ })[g].test(s)); if (hits.length === 2) return { candidates: hits }; }
  if (id === 'B5' && /\b(?:salary|full[- ]time|steady)\b/.test(s) && /\b(?:freelanc\w*|side|commission|gig|contract\w*)\b/.test(s)) return { candidates: ['mostly', 'varies'] };
  if (id === 'EXP') { const v = selfDepth(text) ?? (options.length ? matchOption(options, text) : null) ?? parseDepth(text); return v ? { value: v } : null; }
  if (id === 'MONEY') {
    const r = s.match(/\$?(\d[\d,.]*\s?k?)\s*(?:to|-|or)\s*\$?(\d[\d,.]*\s?k?)\b(?!\s*(?:years?|months?))/);
    if (r && !/\bmonth/.test(s)) { const suf = /k$/.test(r[2]) && !/k$/.test(r[1]) && Number(r[1].replace(/,/g, '')) < 1000 ? 'k' : '', a = parseStep('MONEY', r[1] + suf), b = parseStep('MONEY', r[2]); if (a?.B3 && b?.B3 && a.B3 !== b.B3) return { candidates: [{ B3: a.B3 }, { B3: b.B3 }] }; }
  }
  if (id === 'A2' || id === 'A3') {  // "emergency fund yes", "debt: none": read what follows the topic words too
    const rest = s.replace(id === 'A2' ? /^.*?\b(?:emergency (?:fund|savings)|emergenc\w*|savings?|cushion|safety net)\b\W*/ : /^.*?\b(?:high[- ]interest )?(?:debts?|credit[- ]?cards?|loans?)\b\W*/, '');
    if (rest !== s && rest) { const v = id === 'A2' ? parseEmergency(rest) : parseDebt(rest) ?? (/^(?:none|nothing|zero|no)\b/.test(rest) ? 'no' : null); if (v) return { value: v }; }
  }
  const o = options.length && id !== 'MONEY' ? matchOption(options, text) : null; if (o != null) return { value: o };
  const v = parseStep(id, text, [], ctx);
  return v != null ? { value: v } : null;
}
/** Every answer in one message, by clause. ctx: { pending, options: {id: [{value, text}]}, answers, year, symbols }.
 * Returns { facts, vague, changes, words, question, advice }. A clause with no topic words answers only the open
 * question; a clause about debt never answers the emergency fund; a duration in the past is never a horizon. */
export function readTurn(text, ctx = {}) {
  const raw = String(text), s = norm(raw), pending = ctx.pending, answers = ctx.answers || {};
  const out = { facts: {}, vague: {}, changes: [], words: {}, question: isQuestionText(raw), advice: isAdvice(raw) };
  if (out.advice) return out;
  const cue = CORRECTION.test(s);
  const clauses = raw.replace(/(\d),(?=\d{3}\b)/g, '$1').replace(PAST_DURATION, ' ').split(/[,;!?]|\.(?!\d)|\band\b|\bbut\b|\bplus\b|\balso\b/i).map((c) => c.trim()).filter(Boolean);
  const money = {}, seen = {};
  const put = (id, r) => {
    if (!r) return;
    if (r.candidates) { if (!(id in out.facts)) out.vague[id] = r; return; }
    if (id === 'MONEY') { Object.assign(money, r.value); return; }
    if (id in seen && seen[id] !== r.value) { out.vague[id] = { candidates: [seen[id], r.value] }; delete out.facts[id]; return; }  // "retirement and a house": ask which
    if (out.vague[id] && id in seen) return;
    seen[id] = r.value; out.facts[id] = r.value; delete out.vague[id];
  };
  const anyTopic = (x) => Object.keys(TOPIC).some((k) => TOPIC[k].test(norm(x)));
  const merged = [];
  for (const c of clauses) {  // a short qualifier belongs to the clause before it ("I have some savings, but not much")
    const n = norm(c), prev = merged[merged.length - 1];
    if (prev && !anyTopic(c) && anyTopic(prev) && n.split(' ').length <= 3 && /^(?:not|though|only|just|maybe|probably|kind of|sort of|a bit|a little|mostly|i think|i guess)\b/.test(n)) merged[merged.length - 1] = `${prev} ${c}`;
    else merged.push(c);
  }
  for (const c of merged) {
    const n = norm(c); if (!n) continue;
    const topics = Object.keys(TOPIC).filter((k) => TOPIC[k].test(n));
    const t = new Set(topics);
    if (EXPERIENCE_YEARS.test(n)) t.delete('B1');
    if (t.has('C2')) t.delete('B1');                                           // "in three months" inside the drop story
    if (t.has('B2') && !START_CUE.test(n.replace(/\bover\b.*$/, ''))) t.delete('B1');  // "over 3 years" is how long, not when
    if (t.has('B1') && pending === 'B2' && !/\b(?:in|by|within|until|start\w*|from now|away)\b|\bretir/.test(n)) { t.delete('B1'); t.add('B2'); }
    if (t.has('B4')) t.delete('A2');
    if (t.has('B5') && t.has('A1')) t.delete(pending === 'A1' && !/\b(?:pension|income|salary|job|work)\b/.test(n) ? 'B5' : 'A1');  // "retired with a pension" is income
    if (t.has('A3')) t.delete('A2');                                           // "no debt" never answers the emergency fund
    if ((t.has('A2') || t.has('A3') || t.has('B5')) && !/\b(?:invest\w*|to start|start with|put in|initial|lump sum|this money)\b/.test(n)) t.delete('MONEY');  // "$500 on my credit card" is debt, not the amount
    if (t.has('A2') && /\bsavings?\b/.test(n) && !/\bemergenc|rainy|cushion|safety|set aside|expenses\b/.test(n) && pending !== 'BASICS' && pending !== 'A2') t.delete('A2');
    if (t.has('EXP') && t.size > 1 && !selfDepth(n)) t.delete('EXP');
    if (!t.size && topics.length) continue;  // about something else, just not clearly: never taken as the open question
    if (!t.size && pending) { const id = pending === 'BASICS' ? (answers.A2 == null ? 'A2' : 'A3') : pending; put(id, readAnswer(id, c, ctx.options?.[id] || [], ctx)); continue; }
    for (const id of t) {
      if (id === 'EXP') { const v = selfDepth(n); if (v) put('EXP', { value: v }); continue; }
      const clean = id === 'C0' ? n.replace(/\b(?:risk|comfort\w*)\b/g, '') : n;
      const opts = id === pending || !/^\W*\d\W*$/.test(n) ? ctx.options?.[id] || [] : [];  // a bare number only answers the open question
      put(id, readAnswer(id, clean, opts, ctx));
    }
  }
  if (/\b(?:i'?m|i am|aged?) \d{2}\b/.test(s) && /\bretir\w* (?:at|by|around) \d{2}\b/.test(s)) { const h = parseHorizon(raw, ctx); if (h?.sure) { out.facts.B1 = h.value; delete out.vague.B1; } }
  if (Object.keys(money).length) out.facts.MONEY = money;
  for (const [id, v] of Object.entries(out.facts)) {  // a new value for an answer already given
    const old = id === 'MONEY' ? null : answers[id];
    if (old != null && old !== v) { out.changes.push({ id, from: old, to: v, cue }); delete out.facts[id]; }
  }
  const g = goalWords(raw); if (g) out.words.goal = g;
  const y = yearsSaid(raw); if (y != null && (out.facts.B1 || out.changes.some((x) => x.id === 'B1'))) out.words.years = y;
  return out;
}
/** A value is recorded only if it is one of the engine's options (typed, tapped, or proposed by Claude). */
export function validValue(questions, id, v) {
  if (id === 'EXP') return ['novice', 'some', 'expert'].includes(v);
  if (id === 'FT') return v === 'yes' || v === 'no';
  if (id === 'RECON') return v === 'C0' || v === 'C2';
  if (id === 'MONEY') return !!v && typeof v === 'object' && Object.keys(v).length > 0 && Object.entries(v).every(([k, x]) => ['B3', 'MONTHLY'].includes(k) && Number.isFinite(x) && x >= 0 && x < 1e9) && (v.B3 == null || v.B3 > 0);
  const q = questions.find((x) => x.id === id);
  return !!q && q.options.some((o) => o.value === String(v));
}
/** The risk-check answers count only from their own card: read elsewhere, they are highlighted for a tap. */
export const OPEN_ONLY = new Set(['C1', 'C2', 'C3', 'C4', 'B4', 'RECON', 'FT']);
export function admit(id, value, { open = null, source = 'typed', questions = [] } = {}) {
  if (!validValue(questions, id, value)) return 'reject';
  if (OPEN_ONLY.has(id)) return id === open ? 'record' : id === 'FT' ? 'reject' : 'preselect';
  if (source === 'claude' && ['C0'].includes(id)) return 'preselect';
  return 'record';
}

// ------------------------------------------------------------------ composing a turn from the fixed words
const capFirst = (t) => t.charAt(0).toUpperCase() + t.slice(1);
/** Fill {slots}; {Slot} capitalizes. Returns null when a slot has no value, so a half-filled sentence never shows. */
export function fill(tpl, slots = {}) {
  if (tpl == null) return null;
  let missing = false;
  const out = String(tpl).replace(/\{(\w+)\}/g, (_, k) => { const lower = k.charAt(0).toLowerCase() + k.slice(1), v = slots[k] ?? slots[lower]; if (v == null) { missing = true; return ''; } if (v === '') return ''; return k === lower ? String(v) : capFirst(String(v)); });
  return missing ? null : out.replace(/\s+/g, ' ').trim();
}
export function goalWords(text) { const s = norm(text); for (const [re, np, goal] of KB.GOAL_WORDS) if (re.test(s)) return { np, goal }; return null; }
export function yearsSaid(text) { const s = norm(text); if (EXPERIENCE_YEARS.test(s)) return null; const m = s.match(/\b(?:in|about|around|roughly|maybe|another)\s+(?:about\s+)?(\d{1,2})\s*(?:years?|yrs?)\b/); return m ? Number(m[1]) : null; }
/** Slots for the fixed sentences, from the state the page keeps (st: answers, amount, monthly, words, amountSet). */
export function slotsFrom(st) {
  const a = st.answers || {}, own = a.A1 != null && st.words?.goal?.goal === a.A1 ? st.words.goal.np : null;  // their own words, only for the goal they belong to
  const m = (v) => `$${Math.round(v).toLocaleString('en-CA')}`;
  return {
    goal: own && a.A1 !== 'retirement' ? `saving for ${own}` : KB.PHRASE.A1[a.A1], goal_np: own || KB.GOAL_NP[a.A1] || 'this money',
    when: st.words?.years != null && a.B1 ? `in about ${st.words.years} years` : KB.PHRASE.B1[a.B1],
    how: a.B2 && a.A1 !== 'wealth' && a.A1 !== 'learning' ? `, ${KB.PHRASE.B2[a.B2]}` : '',
    ef: KB.PHRASE.A2[a.A2], debt: KB.PHRASE.A3[a.A3], income: KB.PHRASE.B5[a.B5],
    amount: st.amountSet ? m(st.amount) : null, after: st.amountSet ? m(st.amount * 0.8) : null,
    monthly: st.monthly ? ` plus ${m(st.monthly)} a month` : '',
    c0: KB.PHRASE.C0[a.C0], c2: KB.PHRASE.C2[a.C2], c0w: a.C0, years: st.words?.years,
  };
}
/** The words for one step at one depth: {q, options: [{value, text, ex}], why, whyDeep}. Values and order are the
 * engine's; 'some' keeps the approved text (base) except B1 for a learning goal. */
export function stepWording(id, depth, { base = '', options = [], slots = {}, goal = null, why = null, core = null } = {}) {
  const w = KB.WORDING[id] || {}, d = (depth === 'novice' || depth === 'expert') ? w[depth] || {} : {};
  let q = base;
  if (depth === 'novice' && d.qBy) q = fill(d.qBy[goal] || d.qBy._, slots) || base;
  else if (d.q) q = fill(d.q, slots) || base;
  else if (depth !== 'novice' && depth !== 'expert' && id === 'B1' && goal === 'learning') q = KB.WORDING.B1.someLearning;
  const opts = options.map((o) => ({ value: o.value, text: d.opts?.[o.value] || o.text, ex: depth === 'novice' ? w.ex?.[o.value] || null : null }));
  return { q, options: opts, why, whyDeep: depth === 'expert' && core ? KB.whyDeep(id, core) : null };
}
/** The acknowledgement for one recorded answer at a depth, or '' (the tier rule: beginners hear every one; the
 * standard depth the ones that matter; the experienced depth only the gates and learning). */
export function ackText(id, v, st) {
  const depth = st.depth || 'some', sl = slotsFrom(st), a = KB.ACK[id];
  const gate = (id === 'A2' && v === 'no') || (id === 'A3' && v === 'lot') || (id === 'B1' && v === 'lt2') || (id === 'A1' && v === 'learning');
  const someIds = { A1: true, B1: ['lt2'], A2: true, A3: ['lot'], B5: true, C2: ['dont_know'] };
  if (depth === 'expert' && !gate) return '';
  if (depth === 'some' && !gate && !(someIds[id] === true || someIds[id]?.includes(v))) return '';
  if (id === 'MONEY') return depth === 'novice' ? fill(KB.ACK.MONEY.novice, sl) || '' : '';
  if (id === 'B1' && v !== 'lt2' && sl.years != null && depth === 'novice') return fill(KB.ACK.B1.years, sl) || '';
  return a?.[v] ? fill(a[v], sl) || a[v] : '';
}
/** "Here's what I have so far": each fact as a clause about the person, in reading order. */
export function readbackText(facts, st) {
  const sl = slotsFrom(st), parts = [];
  for (const id of ['A1', 'B1', 'B2', 'MONEY', 'A2', 'A3', 'B5', 'C0', 'C2']) {
    if (!(id in facts)) continue;
    const v = facts[id];
    parts.push(fill(KB.REFLECT[id], { ...sl, c2: KB.PHRASE.C2[v], c0: KB.PHRASE.C0[v], how: KB.PHRASE.B2[v], ef: KB.PHRASE.A2[v], debt: KB.PHRASE.A3[v], income: KB.PHRASE.B5[v], when: id === 'B1' ? (sl.years != null ? `in about ${sl.years} years` : KB.PHRASE.B1[v]) : sl.when }));
  }
  const list = parts.filter(Boolean);
  return list.length > 1 ? `${list.slice(0, -1).join(', ')} and ${list.at(-1)}` : list[0] || '';
}
/** The checkpoint after the situation questions: what was understood and what it means, in words (no level number). */
export function checkpointText(st, profile) {
  const depth = st.depth || 'some', sl = slotsFrom(st), a = st.answers || {};
  let effect = '';
  const gates = (profile?.gates || []).map((g) => g.id);
  if (gates.includes('G1')) effect = KB.EFFECT.G1;
  else if (gates.length) effect = fill(KB.EFFECT.gate, { gate: gates.includes('G2') && gates.includes('G3') ? 'the emergency fund and the high-interest debt' : gates.includes('G2') ? 'the emergency fund' : 'the high-interest debt' });
  else {
    const parts = [KB.EFFECT.time[a.B1]];
    const low = (a.B2 === 'once' && !['10to19', '20plus'].includes(a.B1) ? [KB.EFFECT.names.B2once] : []).concat((profile?.capacity_answers || []).filter((x) => x.lowers).map((x) => KB.EFFECT.names[`${x.id}${a[x.id]}`]).filter(Boolean));
    if (low.length) { const list = low.length > 1 ? `${low.slice(0, -1).join(', ')} and ${low.at(-1)}` : low[0]; parts.push(fill(KB.EFFECT.lowers, { list: capFirst(list), verb: low.length > 1 ? 'make' : 'makes' })); }
    effect = parts.filter(Boolean).join(' ');
  }
  return fill(KB.CHECKPOINT[depth], { ...sl, effect: effect || ' ' });
}
export function clarifyText(id, r) {
  const ph = (v) => (id === 'MONEY' ? `$${Math.round(v.B3).toLocaleString('en-CA')}` : (KB.BARE[id] || KB.PHRASE[id])?.[v] ?? v);
  const [a, b] = r.candidates.map(ph);
  if (id === 'B1' && r.num != null) return fill(KB.CLARIFY.B1num, { n: r.num, a, b });
  return fill(KB.CLARIFY[id] || KB.CLARIFY._, { a, b, word: r.word || '' }) || fill(KB.CLARIFY._, { a, b });
}
/** The repair ladder: the first miss puts the question another way; the second adds the explanation. */
export function repairText(id, { misses = 1, required = true, depth = 'some', learn = '' } = {}) {
  const alt = KB.REPAIR[id] || '';
  if (misses <= 1) return `${KB.REPAIR.lead} ${alt}`.trim();
  return [KB.REPAIR.lead, alt, depth !== 'expert' ? learn : '', required ? KB.REPAIR.second.required : KB.REPAIR.second.optional].filter(Boolean).join(' ');
}

// ------------------------------------------------------------------ E1: more depth for experienced viewers, plain words for beginners
const pcf = (x, nd = 1) => (x == null || !Number.isFinite(x) ? null : `${(Math.round(x * 100 * 10 ** nd + 1e-9) / 10 ** nd).toFixed(nd)}%`);
const dol = (v) => (v == null || !Number.isFinite(v) ? null : `$${Math.round(v).toLocaleString('en-CA')}`);
/** Figures for the experienced views, formatted from robokit.js results only. */
export function figures(p, profile = null) {
  if (!p) return {};
  const st = p.stats, r = p.risk, top = p.holdings.reduce((a, b) => ((b.risk_share ?? 0) > (a.risk_share ?? 0) ? b : a));
  const shown = (p.stress || []).filter((x) => x.portfolio_return != null), worst = shown.length ? shown.reduce((a, b) => (b.portfolio_return < a.portfolio_return ? b : a)) : null;
  const big = p.holdings[0];
  return {
    vol: pcf(st.volatility), target: pcf(r.target_vol), mkt: pcf(r.stock_market_vol), sd10: pcf(st.ni81_102?.std_10y), rating: st.ni81_102?.rating?.toLowerCase(),
    wmer: pcf(st.weighted_mer, 2), fee: dol(st.fee_per_year), drag25: (p.checks || []).find((c) => c.id === 'fee_drag_25')?.en || '',
    worst: worst?.scenario, worstRet: worst ? pcf(worst.portfolio_return, 0) : null,
    topSym: top.symbol, topW: pcf(top.weight, 0), topRs: pcf(top.risk_share, 0), eff: st.effective_holdings?.toFixed(1),
    sharpe: st.sharpe_model?.toFixed(2), model: pcf(st.model_return), rf: pcf(st.risk_free), plan: pcf(st.planning_return),
    nboot: p.method?.n_boot || null, band: big?.band ? `${big.symbol} ${pcf(big.band[0])} to ${pcf(big.band[1])}` : null,
    tol: profile?.tolerance ?? null, cap: profile?.capacity ?? null,
  };
}
/** A term at a depth: the glossary sentence for everyone; an everyday example for beginners; the rule and this
 * person's figure for experienced viewers (left out when a figure is missing). */
export function termAnswer(key, depth, glossary, figs = {}) {
  const g = glossary?.[key]?.en || KB.TERMS[key]; if (!g) return null;
  const base = `${g.term}: ${g.definition}`, deep = KB.TERM_DEEP[key];
  if (depth === 'novice' || depth == null) return [base, KB.TERM_PLAIN[key]].filter(Boolean).join(' ');
  if (depth !== 'expert') return base;
  return [base, deep?.text, deep?.fig ? fill(deep.fig, figs) : null].filter(Boolean).join(' ');
}
/** The experienced "Under the hood" panel, as rows of text; every number is a formatting of a number in p. */
export function hoodRows(p) {
  const st = p.stats, r = p.risk, m = p.method || {};
  const risk = p.holdings.map((h) => `${h.symbol}: weight ${pcf(h.weight)}${h.band ? ` (band ${pcf(h.band[0])} to ${pcf(h.band[1])})` : ''}, ${pcf(h.risk_share)} of the risk, volatility ${pcf(h.volatility)}, planning return ${pcf(h.planning_return_net)} a year after its ${h.mer != null ? `${pcf(h.mer, 2)} fee` : 'fee (not in the data)'}`);
  const assumptions = [st.planning_source ? `Projections: ${st.planning_source}; the mix's planning return is ${pcf(st.planning_return)} a year.` : null, m.expected_returns_for_weights ? `Weights: ${m.expected_returns_for_weights} returns${m.delta != null ? ` (risk aversion ${m.delta})` : ''}; the mix's equilibrium return is ${pcf(st.model_return)} a year against cash at ${pcf(st.risk_free)}${st.risk_free_source ? ` (${st.risk_free_source})` : ''}.` : null].filter(Boolean);
  const caps = Object.entries(m.sleeve_caps || {}).map(([t, v]) => `${t.replace(/\.(TO|NE)$/, '')} ${pcf(v, 0)}`).join(', ');
  const constraints = ['Weights add up to 100%, long only, nothing borrowed; no fund above 50% except the cash fund.', caps ? `Sleeve caps: ${caps}.` : null, r.cash_cap != null ? `Cash at most ${pcf(r.cash_cap, 0)} at this level; your own picks together at most ${pcf(r.satellite_cap, 0)}.` : null].filter(Boolean);
  const method = [
    m.weights && r.target_vol != null ? `${capFirst(m.weights)}, risk aversion calibrated so volatility reaches ${pcf(r.target_vol)} (${pcf(r.risk_share, 0)} of the stock market's ${pcf(r.stock_market_vol)}); reached ${pcf(r.achieved_vol)}.` : null,
    m.covariance ? `Covariance: ${m.covariance === 'lw_cc' ? 'Ledoit-Wolf shrinkage to constant correlation' : m.covariance}${m.shrinkage != null ? ` (intensity ${m.shrinkage.toFixed(2)})` : ''}${p.window ? `, ${p.window.months} months from ${p.window.start} to ${p.window.end}` : ''}.` : null,
    m.resampled ? `Resampled over ${m.n_boot} bootstrap draws; bands are the 5th to 95th percentile of each weight.` : null,
    p.projection?.method ? `Ranges: ${p.projection.method}; ${Number(p.projection.n_paths).toLocaleString('en-CA')} paths.` : null,
    st.ni81_102 ? `Risk-rating scale (NI 81-102): 10-year standard deviation ${pcf(st.ni81_102.std_10y)}, ${String(st.ni81_102.rating).toLowerCase()}.` : null,
    p.projection?.one_year?.prob_loss != null ? `Chance of a loss over the first year: ${pcf(p.projection.one_year.prob_loss, 0)}.${st.effective_holdings != null ? ` Effective number of holdings: ${st.effective_holdings.toFixed(1)}.` : ''}` : null,
  ].filter(Boolean);
  const stress = (p.stress || []).filter((x) => x.portfolio_return != null).map((x) => `${x.scenario} (${x.from.slice(0, 7)} to ${x.to.slice(0, 7)}): ${pcf(x.portfolio_return)}`);
  const checks = (p.checks || []).map((c) => c.en);
  return { risk, assumptions, constraints, method, stress, checks };
}
const CLASS_PLAIN = { Equity: 'stocks', 'Fixed income': 'bonds', Cash: 'cash', 'Real estate': 'real estate', Commodity: 'gold' };
/** "Why this mix" for beginners: the engine's facts in plain words (no equity, fixed income or volatility). */
export function whyPlain(p, { amount, monthly = 0 } = {}) {
  const st = p.stats, pr = p.projection, one = pr.one_year, val = pr.one_year_value, amt = amount ?? pr.amount;
  const parts = Object.entries(p.mix.asset_class).filter(([, v]) => v >= 0.005).map(([k, v]) => `${pcf(v, 0)} ${CLASS_PLAIN[k] || k.toLowerCase()}`);
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : parts[0];
  const lo = monthly && val ? val.p10 : amt * (1 + one.p10), hi = monthly && val ? val.p90 : amt * (1 + one.p90), bad = monthly && val ? val.p5 : amt * (1 + one.p5);
  const top = p.holdings.reduce((a, b) => ((b.risk_share ?? 0) > (a.risk_share ?? 0) ? b : a));
  const shown = (p.stress || []).filter((x) => x.portfolio_return != null), worst = shown.length ? shown.reduce((a, b) => (b.portfolio_return < a.portfolio_return ? b : a)) : null;
  return [
    `Your mix: ${list}, spread over ${p.holdings.length} funds.`,
    p.risk.risk_share != null ? `Level ${p.risk.level} of 5 aims for about ${pcf(p.risk.risk_share, 0)} of the stock market's ups and downs.` : `These are weights you set yourself; they behave like level ${Math.round(p.risk.level * 10) / 10} of 5.`,
    `In 8 years out of 10, your ${dol(amt)}${monthly > 0 ? ` plus ${dol(monthly)} a month` : ''} might end the first year between ${dol(lo)} and ${dol(hi)}. In a bad year (about 1 in 20) it could be about ${dol(bad)}. These are ranges, not promises.`,
    st.fee_per_year != null ? `Fund fees come to about ${dol(st.fee_per_year)} a year in total.` : null,
    `${top.symbol} causes the most ups and downs in the mix, so it matters most in a bad year.`,
    worst ? `If the ${worst.scenario} happened again, this mix would have fallen about ${pcf(-worst.portfolio_return, 0)} before recovering.` : null,
  ].filter(Boolean);
}
/** One line per fund for experienced viewers. */
export const rationaleDeep = (h) => `${h.sleeve_label || 'Your pick'}. ${pcf(h.weight)} of the mix${h.band ? ` (band ${pcf(h.band[0])} to ${pcf(h.band[1])})` : ''}, ${pcf(h.risk_share)} of the risk; volatility ${pcf(h.volatility)}; planning return ${pcf(h.planning_return_net)} a year after its ${h.mer != null ? `${pcf(h.mer, 2)} fee` : 'fee (not in the data)'}.`;

// ------------------------------------------------------------------ Claude's replies: the same rules as the fixed words (RAI)
const DIRECTIVE = [
  /\byou should (?:\w+ )?(?:buy|sell|invest|hold|put|choose|pick|go with|get|move|switch)\b/i, /\bI(?: would|'d)? (?:recommend|advise)\b/i, /\bmy (?:recommendation|advice) (?:is|would be)\b/i,
  /\b(?:best|right|ideal|perfect|smartest) (?:etf|fund|choice|option|level|mix|move) for you\b/i, /\b(?:is|are|would be) (?:the )?(?:best|right|ideal|a good fit|suitable) for you\b/i,
  /\b[Gg]o with (?:[Ll]evel \d|[A-Z]{2,5}\b)/, /\bnow is (?:a )?(?:good|great|bad) time\b/i, /\b(?:buy|sell) (?:now|today|before)\b/i,
];
const LABEL = [/\byou(?:'re| are)(?: (?:clearly|definitely|more of))?(?: an?)? (?:novice|beginner|expert|experienced|sophisticated|seasoned|conservative|aggressive|cautious|risk[- ]averse|risk[- ]taking)(?: investor| type)?\b/i, /\bas an? (?:novice|beginner|expert|experienced investor|conservative investor|aggressive investor)\b/i, /\b(?:novice|beginner|expert)[- ]level\b/i, /\bfor (?:a |an )?(?:beginner|novice|newbie|experienced investor)s?\b/i];
const GUARANTEE = [/\bwill (?:definitely |certainly |surely )?(?:grow|rise|go up|make you|earn|double|recover)\b/i, /\b(?:can'?t|cannot|won'?t) lose\b/i, /\brisk[- ]free\b/i];
const NEGATED = /\b(?:no|not|nothing|never|isn'?t|aren'?t|cannot|can'?t|without|doesn'?t|don'?t|won'?t)\b/i;
const FIXED_SAFE = /\bguaranteed income\b|\bpay(?:ing)?(?: \w+)? (?:off|down)\b[^.]{0,60}\bguaranteed\b/gi;
const promisesGuarantee = (t) => { t = t.replace(FIXED_SAFE, ''); return [...t.matchAll(/\bguarantee[sd]?\b/gi)].some((m) => !NEGATED.test(t.slice(Math.max(0, m.index - 40), m.index).split(/[.;:!?,]|\bbut\b|\band\b/).pop())); };
const LEVEL_TALK = [
  /\byour answers? (?:so far )?(?:points?|suggests?|means?|shows?|puts?)\b/i,
  /\byou(?:'ll| will| would|'d)? (?:probably |likely )?(?:be|get|land|end up|fall)(?: at| in| on| with)? (?:a )?(?:risk )?level\b/i,
  /\b(?:your|you'?re|you are) (?:suggested |likely |probable )?(?:at )?(?:a )?(?:risk )?level (?:is |of |would be )?[1-5]\b/i,
  /\b(?:sounds|looks|seems) like (?:a |an )?(?:level [1-5]|conservative|cautious|balanced|growth|aggressive|careful|bold)\b/i,
  /\b(?:conservative|cautious|balanced|growth|aggressive|careful|bold) (?:mix|portfolio|profile|level) (?:for you|suits you|fits you|is right)\b/i,
  /\b(?:that|this|it|everything) (?:so far )?(?:points?|leans?|suggests?) (?:to|toward|towards) (?:a |an )?(?:level|conservative|cautious|balanced|growth|aggressive|careful|bold)\b/i,
];
/** Problems in a Claude reply: a directive, a label for the person, a guarantee, or a preview of their level before
 * the assessment. The page shows its own answer instead when one is found. */
export function outputIssues(text, { assessed = false } = {}) {
  const t = String(text || ''), issues = [];
  if (DIRECTIVE.some((re) => re.test(t))) issues.push('directive');
  if (LABEL.some((re) => re.test(t))) issues.push('label');
  if (promisesGuarantee(t) || GUARANTEE.some((re) => re.test(t))) issues.push('guarantee');
  if (!assessed && LEVEL_TALK.some((re) => re.test(t))) issues.push('level_before_assessment');
  return issues;
}
/** Numbers the person typed (amounts, ages, spans), which a reply may repeat although the page did not compute them. */
export function personNumbers(texts) {
  const out = [];
  for (const raw of texts) {
    const t = String(raw), o = parseOpener(t);
    if (o.amount > 0) out.push(o.amount); if (o.monthly > 0) out.push(o.monthly);
    for (const m of norm(t).matchAll(/\b(?:i'?m|i am|aged?|age is|retire(?:ment)? at|at age) (\d{1,2})\b|\b(\d{1,2})(?=\s*(?:-\s*)?(?:years?|yrs?|year[- ]old|months?)\b)/g)) out.push(Number(m[1] ?? m[2]));
  }
  return [...new Set(out)];
}
