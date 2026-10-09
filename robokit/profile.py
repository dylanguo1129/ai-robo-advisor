"""Risk self-check: fixed questions -> capacity and tolerance -> a suggested level (1-5).

Design (docs/research/ux-conversation.md section 6, methods-signals.md 1.2-1.6):

* Capacity (ability to take risk) and tolerance (willingness) are scored on
  separate blocks, and the suggested level is the LOWER of the two. This is
  what Joint CSA/CIRO Staff Notice 31-368 (Dec 2025) asks for, and what
  Wealthfront, Vanguard and Schwab do in their own ways.
* Gates come first: money needed within two years all at once ends the
  investing flow; no emergency savings or a lot of high-interest debt caps
  what is built at level 2.
* Tolerance items show outcomes in the user's own dollars (scenario cards),
  never self-ratings or percentages. The dollar ranges come from the engine.
* Inconsistent answers lower tolerance by one step and raise a flag that the
  chat must ask about (Wealthfront: less consistent, less risk-tolerant).
* Knowledge and preferences are never scored for risk. Knowledge only sets
  how much is explained and gates viewing leveraged funds in learn mode.
* The result is a suggestion, not a ceiling. The user chooses the level
  (Path A in docs/research/regulation.md). A level above capacity is chosen
  only after the page shows its bad year and crisis replays in the person's
  own dollars, and the choice is recorded (docs/RESEARCH_LOG.md section 7).
* Capacity cushions (most of savings, uneven income, partial emergency fund)
  combine to at most two steps down, one when the horizon is long.

Everything here is deterministic. The item text is fixed and identical in the
button UI, the chat and the MCP server; a language model may explain a
question but may not reword it or score it.

Levels: 1 Conservative, 2 Cautious, 3 Balanced, 4 Growth, 5 Aggressive growth.
The brief's low / mid / high risk appetite are levels 2 / 3 / 4. The engine
works on a 1-10 scale (level x 2): level L takes on about L x 20% of the
stock market's ups and downs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

LEVELS = {
    1: "Conservative",
    2: "Cautious",
    3: "Balanced",
    4: "Growth",
    5: "Aggressive growth",
}
# the brief's three settings. 'low' / 'mid' / 'high' name risk appetite; the *_aversion names say the same thing in the
# brief's own terms (high risk aversion = low appetite = level 2), so a caller never has to guess which way they run
PRESETS = {"low": 2, "mid": 3, "high": 4, "high_aversion": 2, "mid_aversion": 3, "low_aversion": 4}

# ------------------------------------------------------------------ item bank
# kind: gate | capacity | tolerance | knowledge | preference | amount. Points
# are proposals from docs/research/ux-conversation.md 6.2, to be pilot-tested.
ITEMS = [
    {
        "id": "A0",
        "block": "A",
        "kind": "preference",
        "text": "Which market do you want to build from?",
        "options": [
            {"value": "CA", "text": "Canada: ETFs bought in Canadian dollars (TSX, Cboe Canada)"},
            {"value": "US", "text": "US: ETFs listed in the United States (bought in US dollars)"},
            {"value": "unsure", "text": "Not sure: explain the difference"},
        ],
    },
    {
        "id": "A1",
        "block": "A",
        "kind": "preference",
        "text": "What is this money for?",
        "options": [
            {"value": "retirement", "text": "Retirement"},
            {"value": "home", "text": "A home"},
            {"value": "education", "text": "Education"},
            {"value": "wealth", "text": "Building wealth, no fixed date"},
            {"value": "income", "text": "Income I can spend now"},
            {"value": "learning", "text": "I'm just learning"},
        ],
    },
    {
        "id": "A2",
        "block": "A",
        "kind": "gate",
        "text": "Do you have savings set aside for emergencies, separate from this money? Enough to cover 3 to 6 months of your regular expenses.",
        "options": [{"value": "yes", "text": "Yes"}, {"value": "partly", "text": "Partly"}, {"value": "no", "text": "No"}],
    },
    {
        "id": "A3",
        "block": "A",
        "kind": "gate",
        "text": "Do you carry high-interest debt, like a credit-card balance you don't pay off each month?",
        "options": [{"value": "no", "text": "No"}, {"value": "little", "text": "Yes, a little"}, {"value": "lot", "text": "Yes, a lot"}],
    },
    {
        "id": "B1",
        "block": "B",
        "kind": "capacity",
        "text": "When do you expect to start taking money out?",
        "options": [
            {"value": "lt2", "text": "In less than 2 years", "pts": 0},
            {"value": "2to4", "text": "In 2 to 4 years", "pts": 2},
            {"value": "5to9", "text": "In 5 to 9 years", "pts": 5},
            {"value": "10to19", "text": "In 10 to 19 years", "pts": 8},
            {"value": "20plus", "text": "20 years or more", "pts": 10},
        ],
    },
    {
        "id": "B2",
        "block": "B",
        "kind": "capacity",
        "text": "Once you start, how long will you keep taking money out?",
        "options": [
            {"value": "once", "text": "All at once", "pts": 0},
            {"value": "2to5", "text": "Over 2 to 5 years", "pts": 1},
            {"value": "6to10", "text": "Over 6 to 10 years", "pts": 3},
            {"value": "10plus", "text": "More than 10 years", "pts": 5},
            {"value": "unsure", "text": "Not sure yet", "pts": 3},
        ],
        "skip_if": {"A1": ["wealth"]},
    },
    {"id": "B3", "block": "B", "kind": "amount", "text": "About how much will you invest to start?", "options": []},
    {
        "id": "B4",
        "block": "B",
        "kind": "capacity",
        "text": "Roughly what share of all your savings and investments is this?",
        "options": [
            {"value": "lt10", "text": "Less than 10%", "pts": 4},
            {"value": "10to25", "text": "10% to 25%", "pts": 3},
            {"value": "25to50", "text": "25% to 50%", "pts": 2},
            {"value": "50to75", "text": "50% to 75%", "pts": 1},
            {"value": "gt75", "text": "More than 75%", "pts": 0},
        ],
    },
    {
        "id": "B5",
        "block": "B",
        "kind": "capacity",
        "text": "How steady is your income?",
        "options": [
            {"value": "very", "text": "Very steady", "pts": 3},
            {"value": "mostly", "text": "Mostly steady", "pts": 2},
            {"value": "varies", "text": "It varies a lot", "pts": 1},
            {"value": "pension", "text": "Retired, with a pension or other guaranteed income", "pts": 2},
            {"value": "none", "text": "No regular income right now", "pts": 0},
        ],
    },
    {
        "id": "C1",
        "block": "C",
        "kind": "tolerance",
        "scenario": "one_year",
        "text": "Over one year, which range of results would you be most comfortable with?",
        "options": [{"value": str(k), "level": k, "text": f"Range for level {k}"} for k in range(1, 6)],
    },
    {
        "id": "C2",
        "block": "C",
        "kind": "tolerance",
        "scenario": "drop",
        "text": "Imagine the market falls sharply and in three months your {amount} is worth {after}. What would you most likely do?",
        "options": [
            {"value": "sell_all", "text": "Sell everything", "level": 1},
            {"value": "sell_some", "text": "Sell some", "level": 2},
            {"value": "wait", "text": "Wait it out", "level": 4},
            {"value": "buy", "text": "Buy more", "level": 5},
            {"value": "dont_know", "text": "I honestly don't know", "level": 2},
        ],
    },
    {
        "id": "C3",
        "block": "C",
        "kind": "tolerance",
        "scenario": "ten_year",
        "text": "Over ten years, which would you rather have?",
        "options": [{"value": str(k), "level": k, "text": f"Ten-year outcomes for level {k}"} for k in range(1, 6)],
    },
    {
        "id": "C4",
        "block": "C",
        "kind": "tolerance",
        "text": "When you invest, which worries you more?",
        "options": [
            {"value": "losing", "text": "Losing money", "level": 1},
            {"value": "both", "text": "Both equally", "level": 3},
            {"value": "missing", "text": "Missing out on gains", "level": 5},
        ],
    },
    {
        "id": "D1",
        "block": "D",
        "kind": "knowledge",
        "optional": True,
        "text": "When interest rates go up, what usually happens to the price of existing bonds?",
        "options": [
            {"value": "up", "text": "Goes up"},
            {"value": "down", "text": "Goes down", "correct": True},
            {"value": "same", "text": "Stays the same"},
            {"value": "unsure", "text": "Not sure"},
        ],
    },
    {
        "id": "D2",
        "block": "D",
        "kind": "knowledge",
        "optional": True,
        "text": "A fund that promises 2x the daily move of an index is held for a whole year. Will it return exactly 2x the index's yearly return?",
        "options": [
            {"value": "yes", "text": "Yes"},
            {"value": "no", "text": "No, it can be quite different", "correct": True},
            {"value": "unsure", "text": "Not sure"},
        ],
    },
]
ITEM = {i["id"]: i for i in ITEMS}


def _answer_text(value) -> str:
    """An answer as the browser reads it (String(v)): JSON cannot tell 4 from 4.0, so a whole float is '4'."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _opt(item_id: str, value):
    item = ITEM[item_id]
    for o in item["options"]:
        if o["value"] == _answer_text(value):
            return o
    raise ValueError(f"{item_id}: unknown answer {value!r}; options: {[o['value'] for o in item['options']]}")


@dataclass
class ProfileResult:
    status: str  # "complete" | "incomplete" | "not_ready"
    suggested_level: int | None
    label: str | None
    capacity: int | None
    tolerance: int | None
    binding: str | None
    gates: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    knowledge: dict = field(default_factory=dict)
    can_choose: list = field(default_factory=list)
    explanation: dict = field(default_factory=dict)
    gate_cap: int = 5  # the highest level Robo-Kit builds (2 while G2/G3 hold, 1 under G1)
    within_check: list = field(default_factory=list)  # levels at or below capacity: no extra step to choose
    binding_answers: list = field(default_factory=list)  # the answers that set the suggestion
    capacity_answers: list = field(default_factory=list)  # the answers that set capacity (the step above it needs a look first)

    def to_dict(self) -> dict:
        return asdict(self)


def _item_answer(item_id: str, value) -> dict:
    """Question and chosen answer, for naming the answer that set a limit."""
    it = ITEM[item_id]
    o = _opt(item_id, value)
    return {"id": item_id, "question_en": it["text"], "answer_en": o["text"]}


def score(answers: dict) -> ProfileResult:
    """Score the self-check. ``answers`` maps item id -> option value (amount B3 is a number)."""
    a = {k: v for k, v in (answers or {}).items() if v is not None and v != ""}
    for k, v in a.items():  # reject answers that are not one of the fixed options
        if k in ITEM and ITEM[k]["options"]:
            _opt(k, v)
    gates, flags, why_en = [], [], []

    # B2 is not asked when there is no withdrawal date (building wealth): it scores the middle option
    b2_asked = "B2" in a and a.get("A1") != "wealth"  # no withdrawal date: an old B2 answer no longer counts
    b2 = a.get("B2") if b2_asked else ("unsure" if a.get("A1") == "wealth" else None)

    # ---- gates: whether to invest at all (G1) or how far to go before basics are in place (G2, G3)
    horizon = a.get("B1")
    g1 = horizon == "lt2" and b2 == "once"
    if g1:
        gates.append(
            {
                "id": "G1",
                "en": "You need all of this money within two years. Money like that usually sits in cash-like savings, so Robo-Kit will not build a stock mix for it.",
            }
        )
    gate_cap = 5
    if a.get("A2") == "no":
        gate_cap = 2
        gates.append(
            {
                "id": "G2",
                "en": "First things first: an emergency fund of 3 to 6 months of expenses usually comes before investing. Until then, Robo-Kit builds at most level 2.",
            }
        )
    if a.get("A3") == "lot":
        gate_cap = 2
        gates.append(
            {
                "id": "G3",
                "en": "Paying off high-interest debt is often a better 'return' than investing. Until then, Robo-Kit builds at most level 2.",
            }
        )
    if g1:
        gate_cap = 1

    # ---- capacity (1-5): horizon, then at most one or two steps down for the cushions
    missing = [i for i in ("B1", "B2", "B4", "B5", "C1", "C2", "C3", "C4") if i not in a and not (i == "B2" and b2 is not None)]
    capacity, cap_items = None, []
    if "B1" in a and b2 is not None:
        H = _opt("B1", a["B1"])["pts"] + _opt("B2", b2)["pts"]
        base = 1 if H <= 2 else 2 if H <= 5 else 3 if H <= 9 else 4 if H <= 12 else 5
        b1o, b2o = _opt("B1", a["B1"]), _opt("B2", b2)
        how_en = b2o["text"].lower() if b2_asked else "not asked (no fixed date)"
        why_en.append(f"Time horizon (start taking money out: {b1o['text'].lower()}; for how long: {how_en}) allows up to level {base}.")
        cap_items.append({**_item_answer("B1", a["B1"]), "effect_en": f"allows up to level {base}"})
        if b2_asked:
            cap_items.append({**_item_answer("B2", b2), "effect_en": f"allows up to level {base}"})
        cushions = []
        if "B4" in a and _opt("B4", a["B4"])["pts"] <= 1:
            cushions.append(("B4", "this money is most of your savings"))
        if "B5" in a and _opt("B5", a["B5"])["pts"] <= 1:
            cushions.append(("B5", "your income is uneven"))
        if a.get("A2") == "partly":
            cushions.append(("A2", "your emergency savings are partial"))
        steps = min(len(cushions), 1 if H >= 13 else 2)
        if steps:
            n_en = "one step" if steps == 1 else "two steps"
            names = [c[1] for c in cushions]
            listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
            both = len(cushions) > 1
            why_en.append(f"Because {listed}: {'together, ' if both else ''}{n_en} lower.")
            for cid, _ in cushions:
                cap_items.append(
                    {
                        **_item_answer(cid, a[cid]),
                        "lowers": True,
                        "effect_en": f"together with the others, {n_en} lower" if both else f"{n_en} lower",
                    }
                )
        capacity = max(1, base - steps)
        if horizon == "lt2" and not g1:
            why_en.append("Keeping the next 1 to 2 years of withdrawals in cash-like savings is a common approach.")

    # ---- tolerance (1-5)
    tol_levels = {i: int(_opt(i, a[i])["level"]) for i in ("C1", "C2", "C3", "C4") if i in a}
    tolerance = None
    if tol_levels:
        vals = list(tol_levels.values())
        tolerance = max(1, int(sum(vals) / len(vals)))  # mean, rounded down
        if len(vals) >= 3 and max(vals) - min(vals) >= 3:
            tolerance = max(1, tolerance - 1)
            flags.append(
                {
                    "id": "F_inconsistent",
                    "en": "Two of your answers point different ways: one says you are fine with big swings, another that you would pull back after a drop. Which is closer to you?",
                    "items": [k for k, v in tol_levels.items() if v in (max(vals), min(vals))],
                }
            )
        if a.get("C2") == "sell_all" and tol_levels.get("C1", 0) >= 5:
            flags.append(
                {
                    "id": "F_drop_vs_range",
                    "en": "You chose the widest one-year range but would sell everything after a sharp fall. Selling at the bottom locks in the loss; which answer fits you better?",
                    "items": ["C1", "C2"],
                }
            )
        why_en.append(f"Your answers about ups and downs point to level {tolerance}.")
    tol_items = []
    if tol_levels:
        low = min(tol_levels.values())
        tol_items = [{**_item_answer(k, a[k]), "effect_en": f"points to level {v}"} for k, v in tol_levels.items() if v == low]

    # ---- knowledge (never scored for risk)
    know = {i: bool(_opt(i, a[i]).get("correct", False)) for i in ("D1", "D2") if i in a}
    if know and not any(know.values()) and (tolerance or 0) >= 4:
        flags.append(
            {
                "id": "F_knowledge",
                "en": "You are comfortable with a lot of risk, and the two quiz questions were new to you. Want a quick explanation of bond prices and leveraged funds before choosing?",
                "items": ["D1", "D2"],
            }
        )
    if (tolerance or 0) >= 4 and any(g["id"] in ("G2", "G3") for g in gates):
        flags.append(
            {
                "id": "F_gate_vs_tolerance",
                "en": "You are comfortable with risk, but your savings cushion or debt limits how much risk your situation can take right now.",
                "items": ["A2", "A3"],
            }
        )
    gate_items = [
        {**_item_answer(g, a[g]), "effect_en": "keeps the build at level 2 or below"}
        for g, v in (("A2", "no"), ("A3", "lot"))
        if a.get(g) == v
    ]

    expl = {"en": why_en}
    choose = list(range(1, gate_cap + 1))
    if g1:
        return ProfileResult(
            "not_ready",
            1,
            LEVELS[1],
            capacity,
            tolerance,
            "time horizon",
            gates,
            flags,
            missing,
            know,
            [1],
            expl,
            gate_cap=1,
            within_check=[1],
            binding_answers=[_item_answer("B1", a["B1"]), _item_answer("B2", b2)],
            capacity_answers=cap_items,
        )
    if capacity is None or tolerance is None:
        lvl = min(capacity or tolerance, gate_cap) if (capacity or tolerance) else None
        return ProfileResult(
            "incomplete",
            lvl,
            LEVELS[lvl] if lvl else None,
            capacity,
            tolerance,
            None,
            gates,
            flags,
            missing,
            know,
            choose,
            expl,
            gate_cap=gate_cap,
            within_check=list(range(1, min(capacity or 5, gate_cap) + 1)),
            binding_answers=gate_items,
            capacity_answers=cap_items,
        )
    level = min(capacity, tolerance, gate_cap)
    if gate_cap < min(capacity, tolerance):
        binding, bind_items = "gate", gate_items
        why_en.append(f"Your savings cushion or debt answer keeps the build at level {gate_cap} for now.")
    else:
        binding = "capacity" if capacity < tolerance else ("tolerance" if tolerance < capacity else "both")
        bind_items = cap_items if binding == "capacity" else tol_items if binding == "tolerance" else cap_items + tol_items
    if capacity == tolerance and binding != "gate":
        why_en.append(f"Suggested: level {level}, {LEVELS[level]}. Both point there.")
    else:
        why_en.append(f"Suggested: the lower of the two, level {level}, {LEVELS[level]}.")
    # The suggestion is not a ceiling (Path A: the person chooses). Levels above capacity need an
    # explicit look at their bad year in the page; only the gates cap what is built.
    return ProfileResult(
        "complete",
        level,
        LEVELS[level],
        capacity,
        tolerance,
        binding,
        gates,
        flags,
        missing,
        know,
        choose,
        expl,
        gate_cap=gate_cap,
        within_check=list(range(1, min(capacity, gate_cap) + 1)),
        binding_answers=bind_items,
        capacity_answers=cap_items,
    )


def engine_level(level_1_to_5: float) -> float:
    """Map the 1-5 profile level to the engine's 1-10 risk scale."""
    return float(level_1_to_5) * 2.0


def risk_share(level: float) -> float:
    """Engine risk level 1..10 -> share of the stock market's volatility: level / 10."""
    level = min(max(float(level), 1.0), 10.0)
    return level / 10.0


def cash_cap(level: float) -> float:
    """Most of the portfolio that may sit in cash at an engine level (1..10).

    Only the most conservative levels (money needed soon) may be mostly cash;
    above that, short-term bonds lower risk while earning more over time."""
    return 1.0 if level <= 2 else (0.30 if level <= 4 else 0.15)


def satellite_cap(level: float) -> float:
    """How much of the portfolio may sit in the user's own non-core picks, by engine level."""
    return 0.10 if level <= 4 else (0.20 if level <= 6 else 0.30)


LEVEL_NAMES = {k: LEVELS[max(1, min(5, round(k / 2)))] for k in range(1, 11)}
