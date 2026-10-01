"""Check what gets published as the Robo-Kit web page, and print the publish settings.

The page is a claude.ai Artifact made from the files listed in web/publish.json. This script checks that list against
the code (every module, worker and data file the page loads is listed, and nothing else), checks the sizes against
the Artifact limits, and summarises the data files, which are single-line JSON too large to read by eye. It uses the
standard library only, so it runs on a fresh clone.

    python scripts/check_publish.py          # report, then the publish settings; exit code 1 on a problem
    python scripts/check_publish.py --json   # the publish settings only (for the Artifact tool)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
MB = 1_000_000
FILE_LIMIT, TOTAL_LIMIT, COUNT_LIMIT = 16 * MB, 64 * MB, 255  # the Artifact tool's limits per file, per publish

# how the page reaches its other files: static and dynamic imports, the worker, and data fetched by a literal path
LOADS = [
    re.compile(r"""\bfrom\s*['"]\./([^'"]+)['"]"""),
    re.compile(r"""\bimport\s*['"]\./([^'"]+)['"]"""),
    re.compile(r"""\bimport\(\s*['"]\./([^'"]+)['"]\s*\)"""),
    re.compile(r"""\bnew Worker\(\s*['"](?:\./)?([^'"]+)['"]"""),
    re.compile(r"""\bfetch\(\s*['"](?:\./)?([^'":]+)['"]"""),
    re.compile(r"""<script[^>]*\ssrc=['"](?:\./)?([^'":]+)['"]"""),
]
MARKUP = re.compile(r"<[a-zA-Z/!?]|javascript:", re.I)  # a tag starts right after "<"; "bonds < cash" is text
HIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]")  # control and text-direction characters


def suspicious(text):
    """A data value that is not plain text: markup, a script link, or a hidden control or text-direction character."""
    return bool(MARKUP.search(text) or HIDDEN.search(text))


def manifest():
    return json.loads((WEB / "publish.json").read_text(encoding="utf-8"))


def loaded_files(page):
    """Every file the page loads, followed from the page through each script it imports."""
    seen, todo = set(), [page]
    while todo:
        name = todo.pop()
        path = WEB / name
        if name in seen or not path.exists():
            seen.add(name)
            continue
        seen.add(name)
        if path.suffix in (".html", ".js", ".mjs"):
            text = path.read_text(encoding="utf-8")
            for rx in LOADS:
                for m in rx.finditer(text):
                    todo.append(str((Path(name).parent / m.group(1)).as_posix()).removeprefix("./"))
    seen.discard(page)
    return seen


def used_capabilities():
    names = set()
    for path in WEB.glob("*.js"):
        names |= set(re.findall(r"""claude\.use\(\s*['"]([a-z]+)['"]""", path.read_text(encoding="utf-8")))
    return names


def problems(m=None):
    """What is wrong with the publish list, as plain sentences; empty when it is right."""
    m = m or manifest()
    out, files = [], list(m["files"])
    if not (WEB / m["page"]).exists():
        out.append(f"the page web/{m['page']} is missing")
    for f in files:
        if not (WEB / f).is_file():
            out.append(f"web/{f} is listed but missing")
        if re.match(r"(?:.*/)?(?:test_|dev_|mock)", f):
            out.append(f"web/{f} is a test or dev file and must not be published")
    if len(set(files)) != len(files):
        out.append("a file is listed twice")
    data = {p.relative_to(WEB).as_posix() for p in (WEB / "data").glob("*.json")}  # fetched as data/<market>.json
    needed = loaded_files(m["page"]) | data
    for f in sorted(needed - set(files)):
        out.append(f"the page loads web/{f}, which is not listed")
    for f in sorted(set(files) - needed):
        out.append(f"web/{f} is listed, but the page never loads it")
    sizes = {f: (WEB / f).stat().st_size for f in [m["page"], *files] if (WEB / f).is_file()}
    out += [f"web/{f} is {s / MB:.1f} MB, over the 16 MB limit" for f, s in sizes.items() if s > FILE_LIMIT]
    if sum(sizes.values()) > TOTAL_LIMIT:
        out.append(f"the files total {sum(sizes.values()) / MB:.1f} MB, over the 64 MB limit")
    if len(files) > COUNT_LIMIT:
        out.append(f"{len(files)} files, over the limit of {COUNT_LIMIT}")
    declared, used = set(m["capabilities"]), used_capabilities()
    if declared != used:
        out.append(f"capabilities declared {sorted(declared)} but the code uses {sorted(used)}")
    for f in files:
        if f.endswith(".json") and (WEB / f).is_file():
            n = sum(1 for s in strings(json.loads((WEB / f).read_text(encoding="utf-8"))) if suspicious(s))
            if n:
                out.append(f"web/{f} has {n} text values with markup, script or hidden characters")
    return out


def strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from strings(x)


def summary(name, j):
    """One paragraph a person (or Claude) can check a data file against."""
    texts = list(strings(j))
    marked = sum(1 for s in texts if suspicious(s))
    lines = [
        f"web/{name}: JSON object with keys {', '.join(j)}; {len(texts):,} text values, "
        + (
            f"{marked} of them with markup, script or hidden characters."
            if marked
            else "all scanned: no markup, script or hidden characters."
        )
    ]
    if "meta" in j:
        meta = j["meta"]
        lines.append(
            f"  snapshot {meta.get('data_snapshot')}, prices through {meta.get('prices_through')}, engine {meta.get('engine_version')}"
        )
        lines.append(f"  sources: {'; '.join(f'{k}: {v}' for k, v in meta.get('sources', {}).items())}")
        lines.append(f"  licensing: {meta.get('licensing')}")
    if "universe" in j:
        u = j["universe"]
        names = [r[u["columns"].index("name")] for r in u["rows"][:3]]
        lines.append(
            f"  market {j.get('market')}: {len(u['rows']):,} funds x {len(u['columns'])} columns ({', '.join(u['columns'][:8])}, ...)"
        )
        lines.append(f"  first funds: {'; '.join(names)}")
    if "returns" in j:
        r = j["returns"]
        lines.append(f"  monthly returns for {len(r['series']):,} funds, {r['months'][0]} to {r['months'][-1]}")
    if "sleeves" in j:
        lines.append(f"  asset classes: {', '.join(s['label'] for s in j['sleeves'])}")
    return "\n".join(lines)


def settings(m=None):
    """The Artifact tool's publish settings for a new copy (paths relative to the repository root)."""
    m = m or manifest()
    return {
        "file_path": f"web/{m['page']}",
        "files": {f: f"web/{f}" for f in m["files"]},
        "capabilities": m["capabilities"],
        "title": m["title"],
        "icon": m["icon"],
        "description": m["description"],
    }


def main(argv):
    m = manifest()
    if "--json" in argv:
        print(json.dumps(settings(m), indent=2))
        return 0 if not problems(m) else 1
    found = problems(m)
    print("Robo-Kit web page: what gets published\n")
    for f in [m["page"], *m["files"]]:
        p = WEB / f
        if p.is_file():
            kind = "data, summarised below" if f.endswith(".json") else f"{p.read_text(encoding='utf-8').count(chr(10)) + 1:,} lines"
            print(f"  web/{f:<16} {p.stat().st_size:>10,} bytes  ({kind})")
    print()
    for f in m["files"]:
        if f.endswith(".json") and (WEB / f).is_file():
            print(summary(f, json.loads((WEB / f).read_text(encoding="utf-8"))), "\n")
    if found:
        print("PROBLEMS (fix these before publishing):")
        print("\n".join(f"  - {p}" for p in found))
        return 1
    print("Checks passed: every file the page loads is listed, nothing else is, sizes are within the Artifact limits,")
    print("and the declared capabilities match the code.\n")
    print("Publish settings for the Artifact tool:")
    print(json.dumps(settings(m), indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
