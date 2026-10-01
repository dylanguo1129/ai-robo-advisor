"""Claude Code Stop hook: check the guide's last reply against this turn's Robo-Kit tool results.

Runs when Claude finishes a reply. If Robo-Kit tools were used in the turn
and the reply contains a number or ticker that none of them produced, the
hook blocks the stop with a correction request, so Claude rewrites the reply
using tool numbers only. It never blocks twice in a row (stop_hook_active)
and stays silent in turns that did not use Robo-Kit, so it does not get in
the way of other work.

The flawed reply has already been shown when this runs (Claude Code shows the
reply, then the hook fires); the correction follows it. That limit is
documented in docs/research/gap-artifact-runtime-and-distribution.md (f2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text", "") if isinstance(c, dict) else c) for c in content)
    return ""


def turn_evidence(transcript: Path) -> tuple[list, str]:
    """Tool results from Robo-Kit tools since the last human message, and the last assistant text."""
    entries = []
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    start = 0
    for i, e in enumerate(entries):  # last genuine user prompt (not a tool result)
        msg = e.get("message") or {}
        if e.get("type") == "user" and msg.get("role") == "user":
            c = msg.get("content")
            if isinstance(c, str) or (isinstance(c, list) and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)):
                start = i
    ids, results, last_text = set(), [], ""
    for e in entries[start:]:
        msg = e.get("message") or {}
        c = msg.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and "robokit" in str(b.get("name", "")):
                ids.add(b.get("id"))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in ids:
                raw = _text(b.get("content"))
                try:
                    results.append(json.loads(raw))
                except ValueError:
                    results.append(raw)
            elif b.get("type") == "text" and msg.get("role") == "assistant":
                last_text = b.get("text", "")
    return results, last_text


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("stop_hook_active"):
        return 0
    path = data.get("transcript_path")
    if not path or not Path(path).exists():
        return 0
    results, last_text = turn_evidence(Path(path))
    if not results:
        return 0  # not a Robo-Kit turn
    reply = data.get("last_assistant_message") or last_text
    from robokit.validate import REWRITE_INSTRUCTION, check_reply

    try:
        from robokit.engine import _load

        U = _load()[0]
        universe = set(U.yahoo) | set(U.symbol)
    except Exception:
        universe = None
    check = check_reply(reply, results, universe)
    if check["ok"]:
        return 0
    items = ", ".join(check["unsupported_numbers"] + check["unknown_tickers"])
    print(json.dumps({"decision": "block", "reason": "Robo-Kit check: " + REWRITE_INSTRUCTION.format(items=items)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
