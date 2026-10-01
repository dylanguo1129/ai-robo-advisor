"""Command line: python -m robokit <command>.

refresh        download listings, prices, macro, geopolitics and news; rebuild the universe (15-30 min)
build          print a portfolio as JSON, e.g.  python -m robokit build --market CA --level 3 --amount 25000
chat           chat with the Robo-Kit guide on your own ANTHROPIC_API_KEY
mcp            run the MCP server (stdio; --http PORT for streamable HTTP)
bundle         export the web data bundle (web/data/)
status         data dates and sources
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "chat":
        from .agent import main as chat

        chat(rest)
    elif cmd == "mcp":
        sys.argv = [sys.argv[0]] + rest
        from .mcp_server import main as serve

        serve()
    elif cmd == "build":
        import argparse

        from .tools import build_portfolio_tool

        ap = argparse.ArgumentParser(prog="robokit build")
        ap.add_argument("--market", default="CA", choices=["CA", "US"])
        ap.add_argument("--level", type=float, default=3)
        ap.add_argument("--amount", type=float, default=10000)
        ap.add_argument("--satellites", nargs="*", default=[])
        a = ap.parse_args(rest)
        print(json.dumps(build_portfolio_tool(a.market, a.level, satellites=a.satellites, amount=a.amount), indent=1, ensure_ascii=False))
    elif cmd == "refresh":
        from .refresh import refresh

        refresh()
    elif cmd == "bundle":
        from .bundle import export_bundle
        from .engine import data_source

        if data_source() != "local":
            sys.exit(
                "bundle needs the local data cache in data/v2/ (run `python -m robokit refresh` first). "
                "Without it, it would rebuild web/data/ from the committed snapshot itself and drop the newest month of rates."
            )
        print(json.dumps(export_bundle(), indent=1))
    elif cmd == "status":
        from .tools import data_status

        print(json.dumps(data_status(), indent=1))
    else:
        print(f"unknown command {cmd!r}\n{__doc__}")
        sys.exit(2)


if __name__ == "__main__":
    main()
