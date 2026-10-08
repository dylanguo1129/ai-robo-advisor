"""One random generator for both engines.

``Mulberry32`` is a bit-exact port of ``mulberry32`` in web/engine.js, and ``stationary_rows`` reproduces
``stationaryBootstrapRows``: the same seed gives the same bootstrap histories in Python and in the browser, so
resampled weights and projected ranges agree to rounding instead of to Monte Carlo noise.

``stationary_rows_many`` draws many independent paths at once (one generator per path, each advanced in exactly
the order the scalar version would use), which keeps the projections fast without changing a single draw.
"""

from __future__ import annotations

import numpy as np

M32 = 0xFFFFFFFF
INC = 0x6D2B79F5


class Mulberry32:
    """Callable returning floats in [0, 1); the stream is identical to web/engine.js mulberry32(seed)."""

    __slots__ = ("a",)

    def __init__(self, seed: int):
        self.a = int(seed) & M32

    def __call__(self) -> float:
        self.a = (self.a + INC) & M32
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & M32
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & M32)) & M32)) & M32
        return ((t ^ (t >> 14)) & M32) / 4294967296.0


def stationary_rows(rng: Mulberry32, t: int, n: int, block: float = 6.0) -> np.ndarray:
    """Row indices of one stationary-bootstrap draw (Politis and Romano 1994): blocks with a uniform start and a
    geometric length of mean ``block``, wrapping around the end. Same rule and draw order as web/engine.js."""
    p = 1.0 / block
    rows = np.empty(n, dtype=np.int64)
    i = 0
    while i < n:
        start = int(rng() * t)
        length = 1
        while rng() > p:
            length += 1
        k = 0
        while k < length and i < n:
            rows[i] = (start + k) % t
            k += 1
            i += 1
    return rows


def _step(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Advance many mulberry32 states by one draw (uint32 arithmetic wraps exactly like JavaScript's)."""
    a = a + np.uint32(INC)
    t = (a ^ (a >> np.uint32(15))) * (a | np.uint32(1))
    t = t ^ (t + (t ^ (t >> np.uint32(7))) * (t | np.uint32(61)))
    return a, (t ^ (t >> np.uint32(14))).astype(np.float64) / 4294967296.0


def stationary_rows_many(seeds: np.ndarray, t: int, n: int, block: float = 6.0) -> np.ndarray:
    """``stationary_rows`` for many paths at once: row ``k`` equals ``stationary_rows(Mulberry32(seeds[k]), t, n, block)``."""
    with np.errstate(over="ignore"):
        state = np.asarray(seeds, dtype=np.int64).astype(np.uint32) & np.uint32(M32)
        m = len(state)
        p = 1.0 / block
        rows = np.empty((m, n), dtype=np.int64)
        start = np.zeros(m, dtype=np.int64)
        left = np.zeros(m, dtype=np.int64)  # months left in each path's current block
        pos = np.zeros(m, dtype=np.int64)  # position inside the block
        for i in range(n):
            need = left == 0
            if need.any():
                idx = np.nonzero(need)[0]
                s_ = state[idx]
                s_, u = _step(s_)
                start[idx] = (u * t).astype(np.int64)
                length = np.ones(len(idx), dtype=np.int64)
                drawing = np.ones(len(idx), dtype=bool)
                while drawing.any():
                    d = np.nonzero(drawing)[0]
                    sd, u = _step(s_[d])
                    s_[d] = sd
                    more = u > p
                    length[d[more]] += 1
                    drawing[d[~more]] = False
                state[idx] = s_
                left[idx] = length
                pos[idx] = 0
            rows[:, i] = (start + pos) % t
            pos += 1
            left -= 1
    return rows
