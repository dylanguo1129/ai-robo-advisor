"""A terminal chat with the Robo-Kit guide on your own Anthropic API key.

    set ANTHROPIC_API_KEY=...            (Windows)   export ANTHROPIC_API_KEY=... (macOS/Linux)
    python -m robokit chat --tier default      # quick | default | complex
    python -m robokit chat --model claude-opus-5-5

The model follows AGENT.md, calls Robo-Kit's tools for every number, and each
reply is checked by ``robokit.validate``: a reply with a number or ticker that
no tool produced is sent back once for a rewrite, and anything still
unsupported is flagged on screen. The key is read from the environment and
never written anywhere.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable

from . import tools
from .config import ROOT
from .validate import REWRITE_INSTRUCTION, check_reply

API_URL = "https://api.anthropic.com/v1/messages"
TIERS = {"quick": "claude-haiku-4-5", "default": "claude-sonnet-5-5", "complex": "claude-opus-5-5"}
AGENT_MD = (ROOT / "AGENT.md").read_text(encoding="utf-8")


def tool_specs() -> list[dict]:
    """Tool schemas for the Messages API, taken from the MCP server so both stay identical."""
    from .mcp_server import mcp

    listed = asyncio.run(mcp.list_tools())
    return [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema} for t in listed]


def http_transport(api_key: str) -> Callable[[dict], dict]:
    import requests

    def send(payload: dict) -> dict:
        r = requests.post(
            API_URL,
            json=payload,
            timeout=300,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        )
        if r.status_code != 200:
            raise RuntimeError(f"Anthropic API error {r.status_code}: {r.text[:300]}")
        return r.json()

    return send


class Agent:
    def __init__(self, model: str, transport: Callable[[dict], dict], max_tokens: int = 2048, max_rounds: int = 8):
        self.model = model
        self.send = transport
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds
        self.messages: list[dict] = []
        self.tool_log: list = []  # every tool result this session, for the provenance check
        self.specs = tool_specs()
        from .engine import _load

        U, _, _, _ = _load()
        self.universe = set(U.yahoo) | set(U.symbol)

    def _round_trip(self) -> str:
        for _ in range(self.max_rounds):
            resp = self.send(
                {"model": self.model, "max_tokens": self.max_tokens, "system": AGENT_MD, "tools": self.specs, "messages": self.messages}
            )
            content = resp.get("content", [])
            self.messages.append({"role": "assistant", "content": content})
            if resp.get("stop_reason") != "tool_use":
                return "".join(b.get("text", "") for b in content if b.get("type") == "text")
            results = []
            for b in content:
                if b.get("type") == "tool_use":
                    out = tools.call(b["name"], b.get("input") or {})
                    self.tool_log.append(out)
                    results.append({"type": "tool_result", "tool_use_id": b["id"], "content": json.dumps(out, ensure_ascii=False)[:60000]})
            self.messages.append({"role": "user", "content": results})
        return "(stopped: too many tool rounds)"

    def ask(self, text: str) -> dict:
        self.messages.append({"role": "user", "content": text})
        start = len(self.tool_log)  # evidence is this turn's tool results only: an earlier level's numbers are stale
        reply = self._round_trip()
        check = check_reply(reply, self.tool_log[start:], self.universe)
        retried = False
        if not check["ok"]:
            retried = True
            items = ", ".join(check["unsupported_numbers"] + check["unknown_tickers"])
            self.messages.append({"role": "user", "content": REWRITE_INSTRUCTION.format(items=items)})
            reply = self._round_trip()
            check = check_reply(reply, self.tool_log[start:], self.universe)
        return {"reply": reply, "check": check, "retried": retried}


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="robokit chat", description="Chat with the Robo-Kit guide on your own API key")
    ap.add_argument("--tier", choices=sorted(TIERS), default="default")
    ap.add_argument("--model", default=None, help="any Claude model id; overrides --tier")
    a = ap.parse_args(argv)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_API_KEY in your environment first (your own key; Robo-Kit never stores it).")
    model = a.model or TIERS[a.tier]
    agent = Agent(model, http_transport(key))
    print(f"Robo-Kit guide on {model}. Type 'quit' to leave.\n")
    first = agent.ask("Hello")
    print(first["reply"], "\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit"):
            break
        out = agent.ask(text)
        print("\n" + out["reply"])
        if not out["check"]["ok"]:
            print(f"\n[check] not from a tool, treat with care: {out['check']['unsupported_numbers'] + out['check']['unknown_tickers']}")
        print()
