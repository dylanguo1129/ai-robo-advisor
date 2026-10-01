// Runs the heavy engine calls (resampled portfolios, the five-level ladder) off the main thread.
// app.js falls back to the same functions on the main thread if this worker cannot load.
import { Market, buildPortfolio, ladderRow, oneFund } from './robokit.js';

let core = null;
const markets = {};

async function market(code) {
  if (!core) core = await (await fetch('data/core.json')).json();
  if (!markets[code]) markets[code] = new Market(core, await (await fetch(`data/${code.toLowerCase()}.json`)).json());
  return markets[code];
}

self.onmessage = async (ev) => {
  const { id, type, market: code, req } = ev.data;
  try {
    const M = await market(code);
    if (type === 'build') {
      self.postMessage({ id, ok: true, result: buildPortfolio(M, req) });
    } else if (type === 'onefund') {
      self.postMessage({ id, ok: true, result: oneFund(M, req.share, req) });
    } else if (type === 'ladder') {
      const rows = [];
      for (const lvl of [1, 2, 3, 4, 5]) {
        rows.push(ladderRow(M, req, lvl));
        self.postMessage({ id, ok: true, partial: true, rows: rows.slice() });
      }
      self.postMessage({ id, ok: true, rows });
    }
  } catch (e) {
    self.postMessage({ id, ok: false, error: String(e && e.message || e) });
  }
};
