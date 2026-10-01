# Design

Visual system for the Robo-Kit web surfaces. Direction: the category standard, played straight. Wealthsimple-style minimal, information-complete. Craft bar: Wealthsimple managed-investing screens, Betterment portfolio pages. Mode: Operate.

## Principles

1. The tool disappears into the task: familiar controls, nothing invented for flavour.
2. One visible layer for the client, one registered layer for the mechanism ("Show the mechanism" switch). Both layers share the same grid so every number maps to its cause.
3. Numbers are the loudest thing on the page; chrome is quiet.
4. Uncertainty is shown, never hidden: bands on weights, "target" wording on volatility.

## Color

Strategy: Restrained. Neutrals plus one accent.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--ground` | `#FCFCFC` | `#141414` | page |
| `--surface` | `#FFFFFF` | `#1C1C1C` | panels, inputs |
| `--surface-2` | `#F4F4F2` | `#242423` | control tracks, hover wash, table stripe |
| `--ink` | `#111111` | `#F2F2F0` | primary text |
| `--ink-2` | `#5C5C58` | `#B9B9B3` | secondary text |
| `--ink-3` | `#6B6B66` | `#8A8A85` | muted labels, axis (4.9:1 on white, 5.0:1 on the dark ground) |
| `--rule` | `#E6E6E2` | `#2E2E2C` | hairlines |
| `--accent` | `#1F6B4F` | `#5DBE93` | primary action, selection, focus ring, Robo-Kit series |
| `--accent-soft` | `#E4F1EA` | `#173327` | selected wash |
| `--textbook` | `#8A8A85` | `#8A8A85` | the comparison series (neutral by design: it is the foil) |
| `--warn` | `#B54708` | `#F0A35B` | notes that need attention (with icon + label) |

Asset-class categorical palette (validated with the dataviz validator, adjacent pairlist, both modes): Equity `#2a78d6` / `#3987e5`, Real estate `#eb6834` / `#d95926`, Fixed income `#1baf7a` / `#199e70`, Cash `#eda100` / `#c98500`, Commodity `#e87ba4` / `#d55181`. Light-mode aqua/yellow/magenta sit under 3:1 on the surface, so every mark carries a visible text label (ticker + value) and a class legend; identity is never colour alone.

## Type

One family: Manrope (Google Fonts), fallback `system-ui, -apple-system, "Segoe UI", sans-serif`. Fixed rem scale, ratio ~1.2: 12 / 13 / 14 (body) / 16 / 20 / 24 / 32 (hero figure 40). Weights 400 / 500 / 600 / 700 only. `tabular-nums` in tables and bar labels; proportional figures on the hero numbers. Sentence case everywhere; no tracked uppercase eyebrows except the single section kicker style used for panel titles (13px, 600, `--ink-2`).

## Shape and space

Radius: 10px on controls and inputs, 14px on panels, 999px on the segmented risk control and chips. One scale, documented here; nothing else.
Spacing: 4-point scale (4 / 8 / 12 / 16 / 24 / 32 / 48). More space above a heading than below. Gutter 20px at phone width, 32px from 900px.
Layout: two columns from 960px (inputs 380px, results fluid), single column below; inputs collapse into a sticky summary bar with an "Edit inputs" toggle on phones.
Depth: no shadows on panels; a 1px `--rule` hairline. The only shadow is the tooltip: `0 8px 24px rgba(0,0,0,.12)`.

## Components and states

Segmented control (risk attitude), checkbox rows (shortlist, grouped by asset class with per-group select all), range sliders with numeric readout (cap per fund, cash cap, draws), switches (resample, mechanism, textbook comparison). Every control: default, hover (surface-2 wash), focus-visible (2px accent ring, 2px offset), active (scale .98), disabled (40% opacity, no pointer). Results: skeleton bars while recomputing (150 ms delay before showing the skeleton so fast solves never flash); empty state when the shortlist is empty; error state when caps cannot reach 100% (inline, names the fix).

## Charts

Bars ≤ 20px thick, 4px rounded data-end, square baseline; 2px surface gap between stacked segments; hairline gridlines only where a scale is read. Value at the bar tip in `--ink-2`. Legend for ≥ 2 series (asset classes; Robo-Kit vs textbook). Hover tooltip per bar (name, class, weight, band, risk share). A table view of every chart exists in the mechanism layer.

## Motion

150–200 ms, `cubic-bezier(.2,.8,.2,1)`, transform/opacity/width only. Bars re-tween to new lengths; the mechanism layer reveals with a 200 ms opacity/translate; no page-load choreography. All disabled under `prefers-reduced-motion`.

## Copy

Plain, second person, English, from one string table (`web/strings.js`). Controls name the action. Volatility is always "expected" or "target", never "risk-free" or "guaranteed". Disclaimer in the footer: educational prototype, not advice.

## v2 surface: the chat-first lab (28 Sep 2026)

Same world, new structure (`web/index.html`). Everything above still applies; these are the durable additions.

- **Layout.** Top bar (brand, market switch Canada CAD / US USD, Assistant menu) over a two-column grid from 1100px: the thread column (max 760px) and a 380px tray. Below 1100px the tray becomes a bottom sheet with a 64px summary bar (class bar, level, volatility, fees).
- **Landing.** Left-aligned 32px question headline, one 16px input in a 14px-radius field with a round accent send button, five chips (the first, "Build a portfolio", filled in the accent), the AI disclosure and the data date. No hero art: the tray showing a working mix is the proof.
- **Thread.** User turns are right-aligned `surface-2` bubbles; assistant turns are unboxed text with a small accent "Robo-Kit guide" label and a verification footer (check icon when every number matched a tool; warn colour and highlighted `mark` for anything that did not). Everything else is a card (surface, 1px rule, 14px radius, 20px padding): questions, profile, ladder, shelf, mix report, fund, comparison, context, definition, proposal.
- **Question cards.** Counter ("Question 4 of 15"), 17px question, full-width option rows (10px radius); scenario options pair a dollar range with a small range bar and a zero tick. Answered cards keep the chosen option in the accent wash and dim the rest, with "Change answer".
- **Tray.** Level segments 1-5 (numbers only; the name is in the sub-line and tooltip), a 16px class bar, class list, a 2x2 grid of dollar figures, amount input, fund list, and two actions. When a fund is added, the class bar pulses once (the one authored motion, 350ms, disabled under reduced motion).
- **Data colour.** Asset-class hues as before, plus Multi-asset `#6b7fd6` / `#7d8fe6` and Alternative / crypto `#8f857b` / `#a59a8f`; stress losses in `--warn`, gains in the accent; the projection fan in two accent tints with an accent median line and end dot.
- **Icons.** Phosphor regular (MIT), inlined in `web/icons.js`; 14-18px, `currentColor`.
