"""Targeting layer, part 6: live model numbers for the site's prose.

The Victory Guide's text quotes many model numbers (forecast probabilities,
lever effects, exchange rates, budgets, segment and locality values). The
forecast is refitted almost daily, so the text carries tokens instead of
literal numbers and the builder fills them from the current pipeline outputs:

    {{key}}                     default format
    {{key|op|op|...}}           ops applied left to right, then formatted

Keys (all probabilities in PERCENT, lever and exchange-rate effects in
percentage POINTS, seats in seats, votes in votes):
    fc.asof                     forecast date (polls to)
    fc.<list>.<col>             official_forecast.csv: seats, lo, hi, pass (0-1), largest (0-1)
    bloc.<k>                    mixture_blocs.csv: nb61, ch61, chraam61, neither (%), nb_mean, nb_p05, nb_p95
    gov.<outcome>               government outcomes (%): netanyahu_right, netanyahu_unaligned, netanyahu_defector,
                                change_alone, change_amcha, change_haredi, centre_minority, unity, repeat,
                                change_raam; plus gov.change_led and gov.netanyahu_led (sums)
    pm.<name>                   PM probabilities (%)
    atlas.<obj>                 atlas baseline: govt, deny, nb61, ch61, chraam61 (%), seats
    lev.<scenario>.<obj>        levers.json effect (points; seats for .seats), .votes
    mv.<list>.<obj>             exchange rate per 10,000 votes (points; seats for .seats), .share (%), .pass (0-1)
    netvote.<obj>               effect of 1,000 net votes (points; seats for .seats)
    netvote.votes_per_seat      net votes per expected change-bloc seat
    bud.<obj>.<150k|400k>.<0|30>.<k>   realistic plan: ve, lo, hi (net votes), pp, pp_lo, pp_hi
                                (points; seats for change_seats), druze (net votes if Druze towns cleared),
                                locs, door, sup, pers, resc (contacts)
    sat.<obj>.<k>               saturation totals (net votes, contacts) over all localities (k),
                                k_noarab (no Arab localities), k_core (also no access-excluded/Druze held out)
    tier.<obj>.<slug>           tier counts (localities)
    seg.<segment>.<col>         any column of segments.csv
    loc.<CBS code>.<col>        any column of localities.csv
    polls.res.<n|above|below|latest>  published polls since 15 Sep listing the Reservists, and how many
                                show them at 4+ seats (from polls.csv, always current)
    kal.<k>                     station counts: stations, arab_led, positive_<obj>, positive_core_<obj>
    cond.<list>.<k>             from the 8,000 draws: pass (%), nb61_pass, nb61_fail (%), chseats_pass,
                                chseats_fail, n_pass, n_fail
    waste.<k>                   wasted vote below the threshold (% of valid vote): mean, p10, p90, nb,
                                change, arab, unaligned, other
    pairs.<k>                   effect of the two change-bloc surplus pairs: nb61 (points), seats
    x.<file>.<k>                page-specific derived values: src/targeting_facts_extra/<file>.py defines
                                facts(ctx, get) -> {k: number or string}; ctx is the Ctx below (data frames,
                                planner, draws), get(key) returns any non-extra fact. Strings (e.g. a list of
                                towns built from the data, "Netanya, Eilat and Holon") render as they are.

List short names: Likud Yashar Together Shas Democrats JL YB UTJ Raam Otzma RZP Amcha Reservists BW
Noam HarediPublic IsraelFirst.

Ops: date ("12 October"), dateshort ("12 Oct"), words / Words (0-12 as "four" / "Four"), abs, neg, x100, d100, d1000, sig1, sig2, sig3, round0, round-1, round-2, round-3 (round to
10^-n... i.e. round-3 = nearest thousand), nolead (".80" for 0.80), and a final format "f:<spec>"
(Python format spec, e.g. f:.1f, f:+.2f, f:,.0f). Without f:, integers print with thousands
separators and other numbers with up to two decimals, trailing zeros dropped.

CLI (run from src/):
    python targeting_facts.py [--root DIR] dump              write facts.json (static facts)
    python targeting_facts.py [--root DIR] get KEY [KEY ...]
    python targeting_facts.py [--root DIR] find TEXT         keys whose value prints as TEXT
    python targeting_facts.py [--root DIR] render FILE       render a content file to stdout
    python targeting_facts.py [--root DIR] validate TOKENISED ORIGINAL
                                                             render and diff string by string
    python targeting_facts.py [--root DIR] watch WATCHFILE   evaluate value-dependent wording conditions
    python targeting_facts.py compare OLDROOT OUTDIR         render all pages under an earlier state and the
                                                             live one: failures, false watches, changed text
--root points at an archived targeting directory (its forecast/ subfolder holds the forecast CSVs).
"""

from __future__ import annotations

import importlib
import json
import math
import pickle
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parent
PROCESSED = SRC.parent / "data" / "processed"
TARGET = PROCESSED / "targeting"
EXTRA_DIR = SRC / "targeting_facts_extra"

SHORT = {
    "Likud": "Likud", "Yashar": "Yashar", "Bennett 2026 + Yesh Atid": "Together", "Shas": "Shas",
    "The Democrats": "Democrats", "Balad + Hadash-Ta'al": "JL", "Yisrael Beytenu": "YB",
    "United Torah Judaism": "UTJ", "Ra'am": "Raam", "Otzma Yehudit": "Otzma",
    "Religious Zionist Party": "RZP", "Amcha Yisrael": "Amcha", "Reservists – Economic Party": "Reservists",
    "Blue and White": "BW", "Noam": "Noam", "The Haredi Public": "HarediPublic", "Israel First": "IsraelFirst",
    "Code Black – Shield of the Torah World": "CodeBlack", "Tzomet Beit Yisrael": "Tzomet",
    "Ahi – Back to the Roots": "Ahi", "Unity": "Unity", "Balad (alone)": "BaladAlone",
}
LONG = {v: k for k, v in SHORT.items()}
GOV_SLUG = {
    "Netanyahu rightist coalition": "netanyahu_right",
    "Netanyahu + unaligned / defector coalition": "netanyahu_unaligned",   # name until 19 Oct
    "Netanyahu + unaligned / Amcha": "netanyahu_unaligned",
    "Netanyahu + a change-bloc defector": "netanyahu_defector",
    "Change coalition (without Ra'am)": "change_alone",
    "Change coalition with unaligned / Amcha": "change_amcha",
    "Change coalition with a haredi party": "change_haredi",
    "Centre minority backed by the Joint List": "centre_minority",
    "Unity government (Likud without Netanyahu)": "unity",
    "Repeat election": "repeat",
    "Change coalition with Ra'am": "change_raam",
}
CHANGE_LED = ["change_alone", "change_amcha", "change_haredi", "centre_minority", "change_raam"]
PM_SLUG = {"none (repeat election)": "repeat", "Eisenkot": "eisenkot", "Netanyahu": "netanyahu",
           "rotation / Likud successor": "rotation", "Likud successor (unity)": "rotation",
           "Bennett": "bennett", "Liberman": "liberman", "another leader": "other"}
OBJ_KEY = {"change_govt": "govt", "block_nb": "deny", "change_seats": "seats",
           "change61": "ch61", "change_raam61": "chraam61"}
PLAN_OBJ = ["change_govt", "block_nb", "change_seats"]
TIER_SLUG = lambda t: re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")
COND_LISTS = ["Raam", "Reservists", "Amcha", "RZP", "Otzma", "Democrats", "YB", "Together", "BW", "JL"]
# lever / exchange-rate scale: probabilities in points, seats in seats
SCALE = {"govt": 100, "deny": 100, "ch61": 100, "chraam61": 100, "seats": 1}


class Ctx:
    """Lazy access to every pipeline output under one root (an archive or the live directory)."""

    def __init__(self, root: Path | None = None):
        self.T = Path(root) if root else TARGET
        fdir = self.T / "forecast"
        self.P = fdir if fdir.exists() else PROCESSED

    def csv(self, name, where="T"):
        return pd.read_csv((self.T if where == "T" else self.P) / name, low_memory=False)

    @cached_property
    def fc(self): return self.csv("official_forecast.csv", "P")
    @cached_property
    def gov(self): return self.csv("government_formation.csv", "P")
    @cached_property
    def pm(self): return self.csv("pm_probabilities.csv", "P")
    @cached_property
    def blocs(self): return self.csv("mixture_blocs.csv", "P").iloc[0]
    @cached_property
    def lev(self): return json.loads((self.T / "levers.json").read_text())
    @cached_property
    def mv(self): return self.csv("marginal_values.csv")
    @cached_property
    def mmeta(self): return json.loads((self.T / "marginal_meta.json").read_text())
    @cached_property
    def val(self): return json.loads((self.T / "validation.json").read_text())
    @cached_property
    def sens(self): return json.loads((self.T / "sensitivity_summary.json").read_text())
    @cached_property
    def loc(self): return self.csv("localities.csv")
    @cached_property
    def seg(self): return self.csv("segments.csv")
    @cached_property
    def kal(self): return pd.read_parquet(self.T / "kalpi_all.parquet")
    @cached_property
    def units(self):
        with open(self.T / "planner_units.pkl", "rb") as fh:
            return pickle.load(fh)

    @cached_property
    def loc_sorted(self):
        """Localities in the order the planner indexes them (sorted by CBS code)."""
        return self.loc.sort_values("locality").reset_index(drop=True)

    @cached_property
    def tranches(self):
        import targeting_planner as tp
        return tp.tranches(self.units, self.loc_sorted["locality"])

    @cached_property
    def exclusions(self):
        """Planner exclusions as in the summary budgets: core = Arab localities, access-excluded
        and low-confidence (Druze/Circassian) towns; arab_only = without the Druze hold-out."""
        L = self.loc_sorted
        arab = L.segment.str.startswith("arab")
        core = set(L.index[arab | L.field_excluded.notna() | L.low_confidence.notna()])
        arab_only = set(L.index[arab | L.field_excluded.notna()])
        return core, arab_only

    def plan(self, obj, budget, ident, exclude=None):
        import targeting_planner as tp
        core, _ = self.exclusions
        return tp.allocate(self.tranches[obj], budget, ident, exclude=core if exclude is None else exclude)

    @cached_property
    def draws(self):
        meta = json.loads((self.T / "share_draws_meta.json").read_text())
        return pd.read_parquet(self.T / "share_draws.parquet").values, list(meta["labels"])

    @cached_property
    def seats(self):
        import targeting_marginal as tmg
        S, labels = self.draws
        return tmg.allocate(S, tmg.label_pairs(labels))


class Facts:
    def __init__(self, root: Path | None = None):
        self.ctx = Ctx(root)
        self._static: dict | None = None

    # ------------------------------------------------------------ static facts
    INPUTS = ["levers.json", "marginal_values.csv", "marginal_meta.json", "validation.json",
              "sensitivity_summary.json", "localities.csv", "segments.csv", "kalpi_all.parquet",
              "planner_units.pkl", "share_draws.parquet"]
    FORECAST_INPUTS = ["official_forecast.csv", "government_formation.csv", "pm_probabilities.csv",
                       "mixture_blocs.csv"]

    def _inputs_mtime(self) -> float:
        c = self.ctx
        paths = [c.T / n for n in self.INPUTS] + [c.P / n for n in self.FORECAST_INPUTS] + [Path(__file__)]
        return max(p.stat().st_mtime for p in paths if p.exists())

    @property
    def static(self) -> dict:
        """Static facts, cached in <root>/facts_static.json until any input changes."""
        if self._static is None:
            cache = self.ctx.T / "facts_static.json"
            stamp = self._inputs_mtime()
            if cache.exists():
                d = json.loads(cache.read_text())
                if d.get("_stamp") == stamp:
                    self._static = d["facts"]
            if self._static is None:
                self._static = self._build_static()
                cache.write_text(json.dumps({"_stamp": stamp, "facts": self._static}, ensure_ascii=False,
                                            default=float))
        return self._static

    def _build_static(self) -> dict:
        c, f = self.ctx, {}
        fc = c.fc
        f["fc.asof"] = str(fc["asof"].iloc[0])
        for r in fc.itertuples():
            s = SHORT.get(r.list, r.list)
            lo, hi = (int(x) for x in str(r.interval_90).split("-"))
            f.update({f"fc.{s}.seats": int(r.central_seats), f"fc.{s}.lo": lo, f"fc.{s}.hi": hi,
                      f"fc.{s}.pass": float(r.p_pass), f"fc.{s}.largest": float(r.p_largest)})
        b = c.blocs
        for k, col in [("nb61", "p_nb_61"), ("ch61", "p_anti_61"), ("chraam61", "p_anti_raam_61"), ("neither", "p_neither")]:
            f[f"bloc.{k}"] = 100 * float(b[col])
        for k in ("nb_mean", "nb_p05", "nb_p95"):
            f[f"bloc.{k}"] = float(b[k])
        g = c.gov.set_index("outcome")["probability"]
        for name, slug in GOV_SLUG.items():
            if name in g.index or f"gov.{slug}" not in f:
                f[f"gov.{slug}"] = 100 * float(g.get(name, 0.0))
        f["gov.change_led"] = sum(f[f"gov.{s}"] for s in CHANGE_LED)
        f.setdefault("gov.netanyahu_defector", 0.0)
        f["gov.netanyahu_led"] = f["gov.netanyahu_right"] + f["gov.netanyahu_unaligned"] + f["gov.netanyahu_defector"]
        for r in c.pm.itertuples():
            f[f"pm.{PM_SLUG.get(r.pm, r.pm)}"] = 100 * float(r.probability)
        base = c.mmeta["baseline"]
        f.update({"atlas.govt": 100 * base["change_govt"], "atlas.deny": 100 * base["block_nb"],
                  "atlas.nb61": 100 * (1 - base["block_nb"]), "atlas.ch61": 100 * base["change61"],
                  "atlas.chraam61": 100 * base["change_raam61"], "atlas.seats": base["change_seats"]})
        f["atlas.valid_votes"] = int(c.mmeta["valid_votes_2026"])
        for sc in c.lev["scenarios"]:
            f[f"lev.{sc['key']}.votes"] = int(sc["votes"])
            for obj, k in OBJ_KEY.items():
                f[f"lev.{sc['key']}.{k}"] = SCALE[k] * sc["delta"][obj]
        for r in c.mv.itertuples():
            s = SHORT.get(r.list, r.list)
            f[f"mv.{s}.share"] = 100 * r.share_mean
            f[f"mv.{s}.pass"] = float(r.p_pass)
            for obj, k in OBJ_KEY.items():
                f[f"mv.{s}.{k}"] = SCALE[k] * getattr(r, obj)
        ref = c.val["mv_ref_per_vote"]
        for obj, k in OBJ_KEY.items():
            f[f"netvote.{k}"] = SCALE[k] * ref[obj] * 1000
        f["netvote.votes_per_seat"] = 1 / ref["change_seats"]
        # realistic plans
        core, arab_only = c.exclusions
        sb = c.sens.get("budgets", {})
        for obj in PLAN_OBJ:
            k = OBJ_KEY[obj]
            for b in (150_000, 400_000):
                for ident in (0.0, 0.3):
                    r = c.plan(obj, b, ident)
                    key = f"bud.{k}.{b // 1000}k.{int(round(ident * 100))}"
                    sk = f"{b}_{ident if ident else '0.0'}"
                    rng = [d[obj][sk] for n, d in sb.items()
                           if n not in ("base", "lists_off", "druze_minus20", "persuasion_no_side") and obj in d]
                    to_pp = SCALE[k] * ref[obj]
                    f[f"{key}.ve"] = r["ve"]
                    f[f"{key}.pp"] = r["ve"] * to_pp
                    if rng:
                        f[f"{key}.lo"], f[f"{key}.hi"] = min(rng), max(rng)
                        f[f"{key}.pp_lo"], f[f"{key}.pp_hi"] = min(rng) * to_pp, max(rng) * to_pp
                    f[f"{key}.druze"] = c.plan(obj, b, ident, exclude=arab_only)["ve"] - r["ve"]
                    f[f"{key}.locs"] = int(r["localities"])
                    for p, n in r["contacts"].items():
                        f[f"{key}.{'door' if p == 'area' else p}"] = n
        # saturation
        L = c.loc_sorted
        arab = L.segment.str.startswith("arab")
        masks = {"": np.ones(len(L), bool), "_noarab": ~arab.values,
                 "_core": ~(arab | L.field_excluded.notna() | L.low_confidence.notna()).values}
        for obj in PLAN_OBJ:
            k = OBJ_KEY[obj]
            for part in ("potential", "area_pot", "list_pot", "gotv_pot", "pers_pot", "resc_pot",
                         "area_contacts", "list_contacts"):
                for suf, m in masks.items():
                    f[f"sat.{k}.{part}{suf}"] = float(L.loc[m, f"{obj}__{part}"].sum())
        # tiers
        for obj in PLAN_OBJ:
            for t, n in c.loc[f"{obj}__tier"].value_counts().items():
                f[f"tier.{OBJ_KEY[obj]}.{TIER_SLUG(t)}"] = int(n)
        # stations
        K = c.kal
        f["kal.stations"] = int(len(K))
        f["kal.arab_led"] = int(K["arab_led"].sum())
        locmeta = c.loc.set_index("locality")
        core_loc = set(locmeta.index[~(locmeta.segment.str.startswith("arab") | locmeta.field_excluded.notna()
                                       | locmeta.low_confidence.notna())])
        for obj in PLAN_OBJ:
            pos = K[f"{obj}__area_ve1k"] > 0
            f[f"kal.positive_{OBJ_KEY[obj]}"] = int(pos.sum())
            f[f"kal.positive_core_{OBJ_KEY[obj]}"] = int((pos & K.locality.isin(core_loc) & ~K.arab_led).sum())
        f.update(self._draw_facts())
        return f

    def _draw_facts(self) -> dict:
        import targeting_marginal as tmg
        c, f = self.ctx, {}
        S, labels = c.draws
        seats = c.seats
        d = pd.DataFrame(seats, columns=labels)
        ch = d[[x for x in tmg.CHANGE if x in d]].sum(1).values
        nb = d[[x for x in tmg.NB if x in d]].sum(1).values
        nb61 = nb >= 61
        f["draws.n"] = int(len(S))
        f["draws.nb61"] = 100 * nb61.mean()
        f["draws.ch61"] = 100 * (ch >= 61).mean()
        f["draws.chraam61"] = 100 * ((ch + d["Ra'am"].values) >= 61).mean()
        f["draws.ch_seats"] = float(ch.mean())
        for s in COND_LISTS:
            lab = LONG[s]
            if lab not in labels:
                continue
            p = S[:, labels.index(lab)] >= tmg.THRESHOLD
            f.update({f"cond.{s}.pass": 100 * p.mean(), f"cond.{s}.n_pass": int(p.sum()),
                      f"cond.{s}.n_fail": int((~p).sum()),
                      f"cond.{s}.nb61_pass": 100 * nb61[p].mean() if p.any() else float("nan"),
                      f"cond.{s}.nb61_fail": 100 * nb61[~p].mean() if (~p).any() else float("nan"),
                      f"cond.{s}.chseats_pass": float(ch[p].mean()) if p.any() else float("nan"),
                      f"cond.{s}.chseats_fail": float(ch[~p].mean()) if (~p).any() else float("nan")})
        fail = S < tmg.THRESHOLD
        waste = (S * fail).sum(1)
        f["waste.mean"] = 100 * waste.mean()
        f["waste.p10"], f["waste.p90"] = (100 * np.percentile(waste, [10, 90])).tolist()
        camps = {"nb": tmg.NB, "change": tmg.CHANGE, "arab": ["Ra'am", "Balad + Hadash-Ta'al", "Balad (alone)"],
                 "unaligned": ["Blue and White", "Reservists – Economic Party"]}
        used = set()
        for k, v in camps.items():
            cols = [labels.index(x) for x in v if x in labels]
            used.update(cols)
            f[f"waste.{k}"] = 100 * (S[:, cols] * fail[:, cols]).sum(1).mean()
        other = [i for i in range(len(labels)) if i not in used]
        f["waste.other"] = 100 * (S[:, other] * fail[:, other]).sum(1).mean()
        pairs = tmg.label_pairs(labels)
        cp = [p for p in pairs if labels[p[0]] in tmg.CHANGE]
        s1 = tmg.allocate(S, [p for p in pairs if p not in cp])
        d1 = pd.DataFrame(s1, columns=labels)
        nb1 = d1[[x for x in tmg.NB if x in d1]].sum(1).values >= 61
        f["pairs.nb61"] = 100 * (nb1.mean() - nb61.mean())
        f["pairs.seats"] = float(ch.mean() - d1[tmg.CHANGE].sum(1).values.mean())
        return f

    # ------------------------------------------------------------ lookup
    @cached_property
    def extras(self) -> dict:
        """Page extras. A module that fails is recorded in extra_errors, so only its own
        tokens fail to render (with the module's error), not every page's."""
        out, self.extra_errors = {}, {}
        if EXTRA_DIR.exists():
            sys.path.insert(0, str(SRC))
            for p in sorted(EXTRA_DIR.glob("*.py")):
                if p.stem.startswith("_"):
                    continue
                try:
                    mod = importlib.import_module(f"targeting_facts_extra.{p.stem}")
                    for k, v in mod.facts(self.ctx, self._get_core).items():
                        out[f"x.{p.stem}.{k}"] = v
                except Exception as e:  # noqa: BLE001
                    self.extra_errors[p.stem] = f"{type(e).__name__}: {e}"
        return out

    def _get_core(self, key: str):
        """Any fact except the page-specific extras (what extras may build on)."""
        if key.startswith("x."):
            raise KeyError(f"extras may not depend on other extras: {key}")
        return self.get(key)

    def get(self, key: str):
        if key in self.static:
            return self.static[key]
        if key.startswith("x."):
            if key in self.extras:
                return self.extras[key]
            page = key.split(".")[1]
            if page in getattr(self, "extra_errors", {}):
                raise KeyError(f"{key} (extras module {page!r} failed: {self.extra_errors[page]})")
            raise KeyError(key)
        if key.startswith("polls."):
            return self._polls(key)
        head, _, rest = key.partition(".")
        if head in ("seg", "loc", "fc", "mv"):
            ident, _, col = rest.rpartition(".")
            if head == "seg":
                row = self.ctx.seg.set_index("segment").loc[ident]
            elif head == "loc":
                row = self.ctx.loc.set_index("locality").loc[int(ident)]
            elif head == "fc":
                row = self.ctx.fc.set_index("list").loc[LONG.get(ident, ident)]
            else:
                row = self.ctx.mv.set_index("list").loc[LONG.get(ident, ident)]
            v = row[col]
            return v.item() if hasattr(v, "item") else v
        raise KeyError(key)

    @cached_property
    def _poll_counts(self) -> dict:
        """Published 2026 polls since 15 Sep that list the Reservists (zionist_home), and how many
        show them at 4+ seats (the summary's rescue card uses the same count)."""
        p = pd.read_csv(PROCESSED / "polls.csv", low_memory=False)
        p = p[(p["cycle"].astype(str) == "2026") & (p["party_id"] == "zionist_home")].copy()
        p["fe"] = pd.to_datetime(p["fieldwork_end"], errors="coerce")
        p = p[p["fe"] >= "2026-09-15"]
        g = p.groupby("poll_id").agg(seats=("seats", "max"), fe=("fe", "max"))
        return {"polls.res.n": int(len(g)), "polls.res.above": int((g["seats"] >= 4).sum()),
                "polls.res.below": int((g["seats"] < 4).sum()),
                "polls.res.latest": g["fe"].max().date().isoformat() if len(g) else ""}

    def _polls(self, key: str):
        return self._poll_counts[key]

    def all_numeric(self) -> dict:
        d = {k: v for k, v in {**self.static, **self.extras}.items() if isinstance(v, (int, float))}
        return d


# ------------------------------------------------------------ formatting
TOKEN = re.compile(r"\{\{([^{}|]+?)((?:\|[^{}|]+)*)\}\}")


def _round_half_up(x: float, nd: int) -> float:
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def _sig(x: float, n: int) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    nd = n - 1 - int(math.floor(math.log10(abs(x))))
    return _round_half_up(x, nd)


def fmt_value(v, ops: list[str]) -> str:
    spec = None
    for op in ops:
        op = op.strip()
        if op.startswith("f:"):
            spec = op[2:]
        elif op == "abs":
            v = abs(v)
        elif op == "neg":
            v = -v
        elif op == "x100":
            v = v * 100
        elif op == "d100":
            v = v / 100
        elif op == "d1000":
            v = v / 1000
        elif op in ("sig1", "sig2", "sig3"):
            v = _sig(float(v), int(op[3]))
        elif op.startswith("round"):
            nd = int(op[5:] or 0)
            v = _round_half_up(float(v), nd)
            if nd <= 0:
                v = int(v)
        elif op in ("date", "dateshort"):
            from datetime import date as _d
            d = _d.fromisoformat(str(v))
            v = f"{d.day} {d:%B}" if op == "date" else f"{d.day} {d:%b}"
        elif op in ("words", "Words"):
            n = int(round(float(v)))
            w = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                 "eleven", "twelve"][n] if 0 <= n <= 12 else f"{n:,}"
            v = w.capitalize() if op == "Words" else w
        elif op == "nolead":
            spec = (spec or ".2f") + "|nolead"
        else:
            raise ValueError(f"unknown op {op!r}")
    if isinstance(v, str):
        return v
    nolead = False
    if spec and spec.endswith("|nolead"):
        spec, nolead = spec[:-7], True
    if spec:
        m = re.fullmatch(r"([+ -]?)(,?)\.(\d+)f", spec)
        if m:   # half-up rounding for fixed-point specs (Python's format rounds half-even on binary)
            sign, comma, nd = m.group(1), m.group(2), int(m.group(3))
            r = _round_half_up(float(v), nd)
            s = format(r, f"{sign}{comma}.{nd}f")
        else:
            s = format(v, spec)
    elif isinstance(v, (int, np.integer)) or (isinstance(v, float) and float(v).is_integer() and abs(v) >= 100):
        s = f"{int(v):,}"
    else:
        s = f"{_round_half_up(float(v), 2):,.2f}".rstrip("0").rstrip(".")
    if nolead:
        s = s.replace("0.", ".", 1) if s.startswith(("0.", "-0.")) else s
    return s.replace("-", "−") if s.startswith("-") and False else s


def render(text: str, facts: Facts, where: str = "") -> str:
    def sub(m):
        key = m.group(1).strip()
        ops = [o for o in m.group(2).split("|") if o]
        try:
            v = facts.get(key)
        except KeyError:
            raise KeyError(f"unknown fact {key!r} at {where}") from None
        return fmt_value(v, ops)
    return TOKEN.sub(sub, text)


def render_tree(obj, facts: Facts, where: str = ""):
    if isinstance(obj, str):
        return render(obj, facts, where) if "{{" in obj else obj
    if isinstance(obj, list):
        return [render_tree(v, facts, f"{where}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, dict):
        return {k: render_tree(v, facts, f"{where}.{k}") for k, v in obj.items()}
    return obj


def tokens_in(obj) -> list[str]:
    out = []
    if isinstance(obj, str):
        out += [m.group(1).strip() for m in TOKEN.finditer(obj)]
    elif isinstance(obj, list):
        for v in obj:
            out += tokens_in(v)
    elif isinstance(obj, dict):
        for v in obj.values():
            out += tokens_in(v)
    return out


def _walk_pairs(a, b, where=""):
    if isinstance(a, str) or isinstance(b, str):
        yield where, a, b
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield where, f"<list of {len(a)}>", f"<list of {len(b)}>"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from _walk_pairs(x, y, f"{where}[{i}]")
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                yield f"{where}.{k}", a.get(k, "<missing>"), b.get(k, "<missing>")
            else:
                yield from _walk_pairs(a[k], b[k], f"{where}.{k}")
    elif a != b:
        yield where, a, b


def _diff(a: str, b: str) -> list[str]:
    """Show only the differing stretches of two long strings, with context."""
    import difflib
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        out.append(f"...{a[max(0, i1 - 40):i1]}[RENDERED: {a[i1:i2]!r} | ORIGINAL: {b[j1:j2]!r}]{a[i2:i2 + 30]}...")
    return out


CANDIDATE_OPS = [[], ["f:.0f"], ["f:.1f"], ["f:.2f"], ["f:+.1f"], ["f:+.2f"], ["f:,.0f"], ["sig2"], ["sig2", "f:,.0f"],
                 ["abs", "f:.1f"], ["abs", "f:.2f"], ["abs", "f:,.0f"], ["abs", "sig2"], ["x100", "f:.0f"],
                 ["x100", "f:.1f"], ["nolead"], ["round-3", "f:,.0f"], ["round-2", "f:,.0f"], ["sig1"], ["sig3"],
                 ["round-1", "f:,.0f"], ["sig2", "f:.0f"]]


def find(facts: Facts, text: str, limit: int = 60) -> list[str]:
    text = text.strip().lstrip("+").replace("−", "-")
    out = []
    for k, v in facts.all_numeric().items():
        if isinstance(v, float) and not math.isfinite(v):
            continue
        for ops in CANDIDATE_OPS:
            try:
                s = fmt_value(v, ops).lstrip("+")
            except Exception:
                continue
            if s == text or s.lstrip("-") == text:
                out.append(f"{{{{{k}{''.join('|' + o for o in ops)}}}}}   (= {v!r})")
                break
        if len(out) >= limit:
            break
    return out


def check_watch(watch: list, facts: Facts) -> list[dict]:
    """Evaluate value-dependent wording. Each entry: {"where", "phrase", "condition"}, where the
    condition is a Python expression over F('<fact key>'), e.g. "40 <= F('gov.repeat') < 50".
    Returns the entries whose condition is false or cannot be evaluated."""
    bad = []
    for w in watch:
        try:
            ok = bool(eval(w["condition"], {"__builtins__": {}, "abs": abs, "min": min, "max": max,
                                            "round": round}, {"F": facts.get}))
        except Exception as e:  # noqa: BLE001
            ok, w = False, {**w, "error": repr(e)}
        if not ok:
            bad.append(w)
    return bad


PAGES = ["strategy", "messaging", "coalition", "victory", "playbook", "segments", "sources"]
RESEARCH = TARGET / "research"


def render_tolerant(obj, facts: Facts, where: str = "", missing: list | None = None):
    """Like render_tree, but a token that cannot be filled becomes [[MISSING key]] and is logged."""
    missing = [] if missing is None else missing

    def one(text, w):
        def sub(m):
            key, ops = m.group(1).strip(), [o for o in m.group(2).split("|") if o]
            try:
                return fmt_value(facts.get(key), ops)
            except Exception as e:  # noqa: BLE001
                missing.append((w, key, repr(e)[:200]))
                return f"[[MISSING {key}]]"
        return TOKEN.sub(sub, text)

    def walk(o, w):
        if isinstance(o, str):
            return one(o, w) if "{{" in o else o
        if isinstance(o, list):
            return [walk(v, f"{w}[{i}]") for i, v in enumerate(o)]
        if isinstance(o, dict):
            return {k: walk(v, f"{w}.{k}") for k, v in o.items()}
        return o
    return walk(obj, where), missing


def compare(old_root: Path, out_dir: Path) -> str:
    """Render every content page under an earlier state and the live state: token failures, false
    watch conditions under the live state, and every string whose rendered text changed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    Fo, Fn = Facts(old_root), Facts()
    rep = [f"extras errors: old {Fo.extras and Fo.extra_errors} live {Fn.extras and Fn.extra_errors}"]
    for page in PAGES:
        src = json.loads((RESEARCH / f"content_final_{page}.json").read_text())
        ro, mo = render_tolerant(src, Fo, page)
        rn, mn = render_tolerant(src, Fn, page)
        (out_dir / f"{page}.old.json").write_text(json.dumps(ro, ensure_ascii=False, indent=1))
        (out_dir / f"{page}.new.json").write_text(json.dumps(rn, ensure_ascii=False, indent=1))
        wp = RESEARCH / f"content_watch_{page}.json"
        watch = json.loads(wp.read_text()) if wp.exists() else []
        bad = check_watch(watch, Fn)
        ch = [(w, a, b) for w, a, b in _walk_pairs(ro, rn) if a != b]
        rep.append(f"== {page}: {len(tokens_in(src))} tokens; {len(mn)} fail under the live state; "
                   f"{len(bad)} of {len(watch)} watch conditions false; {len(ch)} strings change")
        rep += [f"  MISSING (live): {w} | {k} | {e}" for w, k, e in mn]
        rep += ["  FALSE: " + json.dumps(b, ensure_ascii=False) for b in bad]
        for w, a, b in ch:
            rep.append(f"  CHANGED {w}")
            rep += ["     " + ln.replace("RENDERED", "NEW").replace("ORIGINAL", "OLD") for ln in _diff(str(b), str(a))]
    txt = "\n".join(rep)
    (out_dir / "report.txt").write_text(txt)
    return txt


def main(argv: list[str]) -> None:
    root = None
    if argv[:1] == ["--root"]:
        root, argv = Path(argv[1]), argv[2:]
        if not root.is_absolute():
            root = TARGET / root
    F = Facts(root)
    cmd, args = (argv[0], argv[1:]) if argv else ("dump", [])
    if cmd == "dump":
        out = (F.ctx.T / "facts.json")
        out.write_text(json.dumps({**F.static, **F.extras}, indent=1, ensure_ascii=False, default=float))
        print("wrote", out, len(F.static), "static +", len(F.extras), "extra facts")
    elif cmd == "get":
        for k in args:
            print(k, "=", repr(F.get(k)))
    elif cmd == "find":
        for line in find(F, " ".join(args)):
            print(line)
    elif cmd == "render":
        print(json.dumps(render_tree(json.loads(Path(args[0]).read_text()), F), ensure_ascii=False, indent=1))
    elif cmd == "validate":
        tok = json.loads(Path(args[0]).read_text())
        orig = json.loads(Path(args[1]).read_text())
        rend = render_tree(tok, F)
        n_tok = len(tokens_in(tok))
        bad = [(w, a, b) for w, a, b in _walk_pairs(rend, orig) if a != b]
        print(f"{n_tok} tokens; {len(bad)} strings differ from the original")
        for w, a, b in bad:
            print(f"--- {w}")
            for line in _diff(str(a), str(b)):
                print("   ", line)
    elif cmd == "compare":
        old = Path(args[0]) if Path(args[0]).is_absolute() else TARGET / args[0]
        txt = compare(old, Path(args[1]))
        print("\n".join(l for l in txt.splitlines() if not l.startswith(("  CHANGED", "     "))))
    elif cmd == "watch":
        for path in args:
            w = json.loads(Path(path).read_text())
            bad = check_watch(w, F)
            print(f"{path}: {len(w)} conditions, {len(bad)} false")
            for b in bad:
                print("  FALSE:", json.dumps(b, ensure_ascii=False))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
