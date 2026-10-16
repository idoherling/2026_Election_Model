"""Build the forecast's evidence registry from the verified research desks.

Inputs  data/processed/forecast_research/<desk>.json         (findings)
        data/processed/forecast_research/verify_<desk>.json  (verdicts)
        data/processed/forecast_research/own_measurements.json (optional:
            the model's own documented measurements, cited as decision-log
            sections)
Outputs data/forecast_sources.json   one entry per distinct source, with the
                                     findings it backs and its check status
        data/forecast_findings.json  finding id -> claim, numbers, source id

Only findings whose verdict is "verified" or "corrected" enter the registry
(a corrected finding carries the corrected numbers and URL). Rejected or
unverifiable findings are listed in the build report and never cited.
Same standard as the field atlas (data/processed/targeting/research).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "data" / "processed" / "forecast_research"

DESKS = {  # file stem -> registry group
    "aggregation": "Poll aggregation and house effects",
    "poll_error": "How large poll errors are",
    "electoral_system": "Israel's electoral system",
    "strategic_voting": "Strategic voting and thresholds",
    "sector_turnout": "Sectors and turnout",
    "coalition_formation": "Coalition formation",
    "campaign_dynamics": "Campaign dynamics and late movement",
    "forecast_evaluation": "Forecast evaluation and computation",
}
OK = {"verified", "corrected"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _key(src: dict) -> str:
    """Dedupe key: DOI if present, else normalised title."""
    u = (src.get("doi_or_url") or "").lower()
    m = re.search(r"10\.\d{4,9}/\S+", u)
    if m:
        return "doi:" + m.group(0).rstrip(".")
    return "t:" + _norm(src.get("title", ""))[:80]


def _authors(authors: str) -> list[str]:
    """Split an author string written as 'A; B; C', 'A, B and C', 'Smith, J.,
    Doe, K.' or 'Smith J & Doe K' into names."""
    a = (authors or "").strip()
    if not a:
        return []
    if ";" in a:
        parts = a.split(";")
    else:
        a = re.sub(r",?\s+(and|&)\s+", ";", a)
        # 'Smith, J., Doe, K.' -> keep 'Surname, Initials' pairs together
        if re.search(r",\s*[A-Z]\.", a):
            parts = re.split(r"(?<=\.),\s*(?=[A-Z][a-z])|;", a)
        else:
            parts = re.split(r",|;", a)
    return [p.strip() for p in parts if p.strip()]


def _surname(name: str) -> str:
    name = name.strip().rstrip(".")
    if "," in name:                      # 'Jackman, S.'
        return name.split(",")[0].strip()
    toks = [t for t in name.split() if not re.fullmatch(r"[A-Z]\.?(-[A-Z]\.?)?", t)]
    if not toks:
        return name
    # institutional authors keep their full (short) name
    if len(name) > 30 or any(w in name for w in ("Committee", "Institute", "Bureau", "Center", "Centre",
                                                   "Association", "Knesset", "Commission", "Ministry")):
        return name if len(name) <= 40 else name[:40]
    return toks[-1]


INSTITUTION_LABELS = [  # (substring in the author field, short label)
    ("own measurement", "Own measurement"), ("Election Model", "Own measurement"),
    ("desk computation", "Own measurement"), ("Central Elections Committee", "CEC"),
    ("Central Electio", "CEC"), ("Knesset", "Knesset"), ("Israel Democracy Institute", "IDI"),
    ("Israel National Election Studies", "INES"), ("Wikipedia", "Wikipedia"),
    ("Jewish Telegraphic Agency", "JTA"), ("Jewish People Policy", "JPPI"),
    ("ParlGov", "ParlGov"), ("Kalshi", "Kalshi & Polymarket"), ("Times of Israel", "Times of Israel"),
]


def _short(src: dict) -> str:
    raw = src.get("authors") or ""
    yr = src.get("year") or "n.d."
    lead = raw.split("(")[0].strip()
    personal = bool(re.match(r"^[A-ZÀ-Ž][a-zà-ž]+ [A-ZÀ-Ž][a-zà-ž]+$", lead)) and "Wikipedia" not in lead
    for key, label in INSTITUTION_LABELS:
        k = key.lower()
        if k in lead.lower() or (k in raw.lower() and not personal):
            return f"{label} {yr}"
    raw = re.sub(r"\s*\([^)]*\)", "", raw)       # drop parenthetical notes
    names = _authors(raw)
    yr = src.get("year") or "n.d."
    if not names:
        return f"{(src.get('venue') or src.get('title') or 'Anon')[:30]} {yr}"
    first = _surname(names[0])
    if len(names) == 1:
        return f"{first} {yr}"
    if len(names) == 2:
        return f"{first} & {_surname(names[1])} {yr}"
    return f"{first} et al. {yr}"


def _citation(src: dict) -> str:
    parts = [src.get("authors") or "", f"({src.get('year') or 'n.d.'}).",
             (src.get("title") or "").rstrip(".") + ".", (src.get("venue") or "")]
    return " ".join(p for p in parts if p).strip()


def main() -> None:
    entries: dict[str, dict] = {}
    findings: dict[str, dict] = {}
    report = {"used": 0, "dropped": []}
    for stem, group in DESKS.items():
        fp, vp = RES / f"{stem}.json", RES / f"verify_{stem}.json"
        if not fp.exists():
            print(f"missing desk {stem}", file=sys.stderr)
            continue
        desk = json.loads(fp.read_text(encoding="utf-8"))
        verd = {}
        if vp.exists():
            verd = {v["id"]: v for v in json.loads(vp.read_text(encoding="utf-8")).get("verdicts", [])}
        for f in desk.get("findings", []):
            v = verd.get(f["id"], {"status": "unverified"})
            if v.get("status") not in OK:
                report["dropped"].append((f["id"], v.get("status"), (v.get("note") or "")[:160]))
                continue
            src = dict(f.get("source") or {})
            if v.get("corrected_url"):
                src["doi_or_url"] = v["corrected_url"]
            k = _key(src)
            e = entries.get(k)
            if e is None:
                e = entries[k] = {
                    "id": "", "short": _short(src), "citation": _citation(src),
                    "url": src.get("doi_or_url") or "", "group": group,
                    "status": src.get("type") or "", "findings": [], "backs": [],
                    "checked": [],
                }
            e["findings"].append(f["id"])
            e["backs"].append(f.get("claim", ""))
            e["checked"].append(v.get("status"))
            findings[f["id"]] = {
                "claim": f.get("claim", ""),
                "quant": v.get("corrected_quant") or f.get("quant", ""),
                "source": k, "status": v.get("status"), "model_link": f.get("model_link", ""),
            }
            report["used"] += 1
    own = RES / "own_measurements.json"
    if own.exists():
        for m in json.loads(own.read_text(encoding="utf-8")):
            k = "own:" + m["id"]
            entries[k] = {"id": m["id"], "short": m["short"], "citation": m["citation"],
                          "url": m.get("url", ""), "group": "This model's own measurements",
                          "status": "own measurement", "findings": [m["id"]],
                          "backs": [m.get("backs", "")], "checked": ["documented"]}
    # stable ids: first finding id of each source
    out = []
    for k, e in entries.items():
        if not e["id"]:
            e["id"] = e["findings"][0]
        e["aliases"] = [f for f in e["findings"] if f != e["id"]]
        st = "corrected" if "corrected" in e["checked"] else e["checked"][0]
        e["checked"] = {"verified": "verified against the source",
                        "corrected": "verified; the figures were corrected against the source",
                        "documented": "documented in the decision log"}.get(st, st)
        e["note"] = "Backs: " + " | ".join(sorted(set(b for b in e["backs"] if b)))[:600]
        for f in e["findings"]:
            if f in findings:
                findings[f]["source"] = e["id"]
        del e["backs"]
        out.append(e)
    out.sort(key=lambda e: (list(DESKS.values()).index(e["group"]) if e["group"] in DESKS.values() else 99,
                            e["short"]))
    # disambiguate identical author-year labels (APA style: 2020a, 2020b)
    from collections import defaultdict
    by_short = defaultdict(list)
    for e in out:
        by_short[e["short"]].append(e)
    for short, es in by_short.items():
        if len(es) > 1:
            for k, e in enumerate(sorted(es, key=lambda e: e["citation"])):
                e["short"] = short + "abcdefghij"[k]
    (ROOT / "data" / "forecast_sources.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "data" / "forecast_findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} sources, {report['used']} findings used, {len(report['dropped'])} dropped")
    for d in report["dropped"]:
        print("  dropped", *d)


if __name__ == "__main__":
    main()
