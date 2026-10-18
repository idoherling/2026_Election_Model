"""Publish checks on the built site (output/site/index.html).

The checks the publish checkpoint ran by hand, plus the owner's content
rules, as functions that pipeline.py and the test suite both call:

  1. js         the page script parses (node --check);
  2. chapters   the English chapters and the Hebrew chapter table (HE_CH)
                have the same count;
  3. citations  every inline citation id (data-s="...") resolves to an id
                or alias in data/forecast_sources.json;
  4. hebrew     Hebrew seat counts say מנדטים, never מושבים;
  5. others     the pollsters' "Others" label never appears (the site says
                "small parties"); verbatim titles and URLs of cited works
                in the embedded registry are exempt;
  6. registry   every finding behind a cited source carries a verified or
                corrected verdict in the research desks
                (data/processed/forecast_research/verify_*.json), and every
                cited decision-log entry (DL-n) names a section that exists
                in docs/priors_dossier.md.

    python src/site_checks.py            # prints each check, exit 1 on failure
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "output" / "site" / "index.html"
SOURCES = ROOT / "data" / "forecast_sources.json"
RESEARCH = ROOT / "data" / "processed" / "forecast_research"
DOSSIER = ROOT / "docs" / "priors_dossier.md"
OK_VERDICTS = {"verified", "corrected"}
# node: $NODE, then PATH, then the install the publish checkpoint used
NODE_CANDIDATES = ("/Users/idoherling/.local/node/bin/node",)
# placeholders in the template's own comments, not citations
PLACEHOLDER_IDS = {"ID", "ID1", "ID2", "<id>"}


def find_node() -> str | None:
    env = os.environ.get("NODE")
    if env and Path(env).exists():
        return env
    on_path = shutil.which("node")
    if on_path:
        return on_path
    return next((p for p in NODE_CANDIDATES if Path(p).exists()), None)


def load_page(path: Path = PAGE) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_sources(path: Path = SOURCES) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def page_script(html: str) -> str:
    """The page's own script: the last bare <script> block (the JSON-LD
    block carries a type attribute and is not matched)."""
    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    if not scripts:
        raise ValueError("no <script> block in the page")
    return scripts[-1]


def check_js(html: str, node: str | None = None) -> list[str]:
    node = node or find_node()
    if node is None:
        return ["node not found (set NODE=/path/to/node): the script parse check cannot run"]
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "page.js"
        js.write_text(page_script(html), encoding="utf-8")
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    return [] if r.returncode == 0 else ["JS parse error: " + r.stderr.strip()[:800]]


def chapter_counts(html: str) -> tuple[int, int]:
    """(English chapters, Hebrew chapter-table entries)."""
    en = len(re.findall(r'<div class="chapter"', html))
    i = html.index("const HE_CH = [")
    j = html.index("function trStatic", i)
    he = len(re.findall(r'\{t:"', html[i:j]))
    return en, he


def check_chapters(html: str) -> list[str]:
    en, he = chapter_counts(html)
    if en == 0:
        return ["no chapters found in the page"]
    return [] if en == he else [f"chapter count mismatch: EN {en} vs HE {he}"]


def cited_ids(html: str) -> set[str]:
    """Static citation ids in data-s attributes (template-literal ids built
    at run time, "${...}", are not citations of the registry), including
    those inside the embedded JSON payload, where the quotes are escaped
    (data-s=\\"ID\\": the model explorer's variant descriptions)."""
    out: set[str] = set()
    for attr in re.findall(r'data-s=\\?"([^"\\]+)\\?"', html):
        for x in attr.split(","):
            x = x.strip()
            if x and "${" not in x and x not in PLACEHOLDER_IDS:
                out.add(x)
    return out


def source_index(sources: list) -> dict:
    """id and every alias -> registry entry."""
    idx = {}
    for s in sources:
        idx[s["id"]] = s
        for a in s.get("aliases", []):
            idx[a] = s
    return idx


def check_citations(html: str, sources: list) -> list[str]:
    idx = source_index(sources)
    missing = sorted(c for c in cited_ids(html) if c not in idx)
    return [f"unresolved citation ids: {missing[:30]}"] if missing else []


def check_hebrew_seats(html: str) -> list[str]:
    """Owner ruling (2 Sept): Hebrew seats are מנדטים, never מושבים (every
    inflected form contains the string)."""
    hits = [m.start() for m in re.finditer("מושבים", html)]
    if not hits:
        return []
    ctx = html[max(hits[0] - 60, 0):hits[0] + 60].replace("\n", " ")
    return [f"'מושבים' appears {len(hits)} time(s), first near: ...{ctx}..."]


_CITED_TEXT = re.compile(r'"(?:citation|url)":"(?:[^"\\]|\\.)*"')
# the redesign's inline citation index: "ID":["short","citation","url"]
_CITE_INDEX = re.compile(r'"(?:[A-Z]{2,4}-F\d+|DL-\d+)":\[(?:"(?:[^"\\]|\\.)*",?)*\]')


def check_others(html: str) -> list[str]:
    """Owner ruling (2 Sept): the site says "small parties", never the
    pollsters' "Others" column. The embedded registry's citation and url
    strings are exempt: they reproduce third-party titles verbatim (Silver
    2016, "...More Bullish Than Others On Trump")."""
    text = _CITE_INDEX.sub('""', _CITED_TEXT.sub('""', html))
    hits = [m.start() for m in re.finditer(r"\bOthers\b", text)]
    if not hits:
        return []
    ctx = text[max(hits[0] - 60, 0):hits[0] + 60].replace("\n", " ")
    return [f"'Others' appears {len(hits)} time(s), first near: ...{ctx}..."]


def desk_verdicts(res_dir: Path = RESEARCH) -> dict:
    """finding id -> verdict status, over every verify_<desk>.json."""
    out = {}
    for vp in sorted(Path(res_dir).glob("verify_*.json")):
        for v in json.loads(vp.read_text(encoding="utf-8")).get("verdicts", []):
            out[v["id"]] = v.get("status")
    return out


def own_measurements(res_dir: Path = RESEARCH) -> dict:
    fp = Path(res_dir) / "own_measurements.json"
    if not fp.exists():
        return {}
    return {m["id"]: m for m in json.loads(fp.read_text(encoding="utf-8"))}


def dossier_sections(path: Path = DOSSIER) -> set[int]:
    if not Path(path).exists():
        return set()
    return {int(n) for n in re.findall(r"^## (\d+)\.", Path(path).read_text(encoding="utf-8"), flags=re.M)}


def check_registry(html: str, sources: list, res_dir: Path = RESEARCH,
                   dossier: Path = DOSSIER) -> list[str]:
    """Every cited source's findings are verified or corrected; every cited
    decision-log entry points at a dossier section that exists."""
    idx = source_index(sources)
    verdicts = desk_verdicts(res_dir)
    own = own_measurements(res_dir)
    sections = dossier_sections(dossier)
    problems = []
    for cid in sorted(cited_ids(html)):
        e = idx.get(cid)
        if e is None:
            continue   # reported by check_citations
        for f in e.get("findings", []):
            if f in own:
                m = re.search(r"#s(\d+)$", own[f].get("url", ""))
                if not m or int(m.group(1)) not in sections:
                    problems.append(f"{cid}: decision-log entry {f} points at no dossier section")
                continue
            st = verdicts.get(f)
            if st not in OK_VERDICTS:
                problems.append(f"{cid}: finding {f} has verdict {st!r}")
    return problems


def run_all(page: Path = PAGE, sources_path: Path = SOURCES, res_dir: Path = RESEARCH,
            dossier: Path = DOSSIER, node: str | None = None) -> dict:
    """check name -> list of problems (empty = pass)."""
    html = load_page(page)
    sources = load_sources(sources_path)
    return {
        "js": check_js(html, node),
        "chapters": check_chapters(html),
        "citations": check_citations(html, sources),
        "hebrew": check_hebrew_seats(html),
        "others": check_others(html),
        "registry": check_registry(html, sources, res_dir, dossier),
    }


def summary(results: dict, page: Path = PAGE, sources_path: Path = SOURCES) -> str:
    html = load_page(page)
    en, he = chapter_counts(html)
    return (f"{en} chapters EN = HE {he}; {len(cited_ids(html))} distinct citation ids; "
            f"{len(load_sources(sources_path))} sources")


def main() -> int:
    results = run_all()
    bad = 0
    for name, problems in results.items():
        if problems:
            bad += 1
            for p in problems:
                print(f"FAIL {name}: {p}")
        else:
            print(f"ok   {name}")
    if bad:
        print(f"{bad} check(s) failed")
        return 1
    print("checks OK: " + summary(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
