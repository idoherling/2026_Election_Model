"""Targeting layer: build the Victory Guide and check it before publishing.

    cd src && ../.venv/bin/python targeting_check.py            # assemble content, build, audit
    cd src && ../.venv/bin/python targeting_check.py --no-build # audit the last build only

Fails (exit 1) when a model-number token cannot be filled, a cited id does not resolve in Sources,
a cited finding is rejected, the built page still holds a token, or an Arab locality carries a
targeting value in the published CSVs. Prints warnings for value-dependent wording whose watch
condition is false, house-style slips and banned terms.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
R = ROOT / "data" / "processed" / "targeting" / "research"
OUT = ROOT / "output" / "targeting"
DESKS = ["gotv", "persuasion", "israeli-behaviour", "israeli-turnout", "israel-geography", "context-2026",
         "coordination", "messaging", "media", "coalition", "turnout_scale", "operations", "context-final",
         "finaldays"]
PAGES = ["segments", "playbook", "strategy", "messaging", "coalition", "victory"]


def main() -> int:
    errors, warnings = [], []
    if "--no-build" not in sys.argv:
        p = subprocess.run([sys.executable, "build_targeting_site.py", "--assemble-content"], cwd=SRC,
                           capture_output=True, text=True)
        print(p.stdout[-3000:])
        if p.returncode:
            print(p.stderr[-3000:])
            errors.append("build failed")
            return report(errors, warnings)
        warnings += [ln for ln in p.stdout.splitlines() if ln.startswith("WARNING")]
    C = json.loads((ROOT / "site" / "targeting_content.json").read_text())
    print("content files:", C.get("files"), "forecast:", C.get("facts_asof"))

    # verdicts of every research finding
    V = {}
    for d in DESKS:
        f = R / f"verify_{d}.json"
        if f.exists():
            for x in json.loads(f.read_text()).get("verdicts", []):
                V[x["id"]] = x.get("status")
    ids = {}
    for s in C["sources"]:
        for k in [s.get("id")] + list(s.get("aliases") or []):
            if k:
                if k in ids:
                    errors.append(f"duplicate source id {k}")
                ids[k] = s
    cited = {}

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "cites" and isinstance(v, list):
                    for i in v:
                        cited.setdefault(i, []).append(path)
                else:
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for j, v in enumerate(o):
                walk(v, f"{path}[{j}]")
    for k in PAGES:
        walk(C[k], k)
    text = json.dumps({k: C[k] for k in PAGES}, ensure_ascii=False)
    for m in re.finditer(r"\(((?:D\d+|P)-F\d+)\)", text):     # inline "(D8-F14)" mentions
        cited.setdefault(m.group(1), []).append("inline")
    for i, where in sorted(cited.items()):
        if i not in ids:
            errors.append(f"cite {i} does not resolve in Sources ({where[:2]})")
        if V.get(i) == "rejected":
            errors.append(f"cite {i} is a rejected finding ({where[:2]})")
        elif V.get(i) == "unverifiable":
            warnings.append(f"cite {i} is unverifiable: the text must say so ({where[:2]})")
    print(f"{len(cited)} cited ids, {len(ids)} source ids/aliases")

    # leftovers and banned terms
    full = json.dumps(C, ensure_ascii=False)
    if "{{" in full or "[[MISSING" in full:
        errors.append("an unrendered token is left in site/targeting_content.json")
    page = (OUT / "index.html").read_text() if (OUT / "index.html").exists() else ""
    if "{{" in page.replace("{{-", ""):
        warnings.append("'{{' appears in index.html (check it is code, not a token)")
    for name, pat in {"opposition stronghold": r"opposition stronghold", "em dash": "—",
                      "covert/quiet": r"\b(covert|low-visibility)\b", "suppress": r"\bsuppress(ion)?\b",
                      "ballot letters בד": "בד"}.items():
        n = len(re.findall(pat, text, flags=re.I))
        if n:
            warnings.append(f"{name}: {n} occurrence(s) in page content")
    for stale in [r"13 Oct(ober)? forecast", r"\bthis week\b", r"\b14 days\b", r"two weeks out", r"bw_withdraws"]:
        n = len(re.findall(stale, text, flags=re.I))
        if n:
            warnings.append(f"time/stale phrase /{stale}/: {n}")

    # no Arab town-level targeting values in the published CSVs
    if (OUT / "localities.csv").exists():
        loc = pd.read_csv(OUT / "localities.csv", low_memory=False)
        arab = loc["segment"].astype(str).str.startswith("arab")
        vcols = [c for c in loc.columns if "__" in c and not c.endswith("__tier")]
        leak = loc.loc[arab, vcols].notna().any(axis=1).sum() if vcols else 0
        if leak:
            errors.append(f"{leak} Arab localities carry targeting values in localities.csv")
    return report(errors, warnings)


def report(errors, warnings) -> int:
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("CHECK", "FAILED" if errors else "PASSED", f"({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
