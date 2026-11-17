"""Derived numbers for the coalition page (data/processed/targeting/research/content_tok_coalition.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.

Central-seat arithmetic (the forecast's central seats, official_forecast.csv):
    ch_central            the four change lists (targeting_marginal.CHANGE)
    nb_central            the Netanyahu bloc (targeting_marginal.NB), i.e. Netanyahu's recommendations
                          if every NB list backs him
    nb_central_no_haredi  the Netanyahu bloc without Shas and UTJ (they recommend no one)
    chraam_central        change lists + Ra'am
    ch_plus_arab          change lists + Ra'am + the Joint List (recommendations incl. both Arab lists)
    ch_plus_shas          change lists + Shas
    ch_plus_utj           change lists + UTJ
    ch_noyb_plus_haredi   change lists without Yisrael Beytenu + Shas + UTJ
    ch_plus_likud         change lists + Likud (a unity government after Netanyahu)
Formation model:
    repeat_p05, repeat_p95  5th/95th percentile of the repeat-election share across the formation
                            model's behaviour vectors (government_formation.csv), in percent
    arab_routes           points of change-led government that depend on an Arab party
                          (with Ra'am inside + centre minority backed by the Joint List)
    pledge_left           points of change-led government left if the bloc pledged against Arab
                          parties, haredi parties and Likud (change alone + with unaligned/Amcha)
Forecast pass rates:
    min_change_pass       lowest threshold pass rate among the four change lists (percent)
Levers (atlas scenario engine; base = atlas baseline):
    pers1_ch61_after      P(change lists alone >= 61) after 1 point moves from Likud (percent)
    pers1_chraam61_after  P(change lists + Ra'am >= 61) after 1 point moves from Likud (percent)
Value-dependent wording (strings built from the numbers, so the prose stays true after a refit):
    ch_short              seats the four change lists are short of 61 on central seats (use |words)
    chraam_short          seats the four change lists + Ra'am are short of 61 on central seats (|words)
    chraam_vs_ch_times    "more than three times" etc.: P(change + Ra'am >= 61) / P(change alone >= 61)
    repeat_vs_changeled_times  the same phrase for the repeat-election share / change-led share
    noyb_haredi_phrase    "61, the barest majority" / "60, still short of 61" / "63, a majority":
                          central seats of the three change lists other than Yisrael Beytenu + Shas + UTJ
    atlas_base_phrase     "also about 24%" when the atlas base (atlas.govt) rounds to the forecast's
                          change-led share, else "about 23%, close to the 24% here"
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import targeting_marginal as tmg

SHAS, UTJ, RAAM, JL, YB, LIKUD = ("Shas", "United Torah Judaism", "Ra'am", "Balad + Hadash-Ta'al",
                                  "Yisrael Beytenu", "Likud")
REPEAT = "Repeat election"
CHANGE_SHORT = ["Yashar", "Together", "Democrats", "YB"]
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve"]


def _half_up(x: float, nd: int = 0) -> float:
    """Round half up, as the renderer's f: formats do."""
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def _times(k: int) -> str:
    if k == 2:
        return "twice"
    return f"{WORDS[k] if 0 <= k <= 12 else f'{k:,}'} times"


def times_phrase(num: float, den: float) -> str:
    """'about twice', 'more than three times', 'nearly four times', 'about 1.5 times', ...
    for the ratio num/den, so a sentence like '..., X the change lists' chance alone' stays true."""
    if den <= 0:
        return "far more than" if num > 0 else "the same as"
    r = num / den
    if r < 0.95:
        return "less than"
    if r < 1.1:
        return "about the same as"
    n = int(r)
    frac = r - n
    if frac >= 0.8:
        return f"nearly {_times(n + 1)}"
    if n == 1:
        return f"about {_half_up(r, 1):.1f} times"
    if frac < 0.1:
        return f"about {_times(n)}"
    return f"more than {_times(n)}"


def facts(ctx, get):
    out = {}
    seats = ctx.fc.set_index("list")["central_seats"]
    s = lambda labels: int(sum(int(seats.get(x, 0)) for x in labels))

    ch = s(tmg.CHANGE)
    nb = s(tmg.NB)
    out["ch_central"] = ch
    out["nb_central"] = nb
    out["nb_central_no_haredi"] = s([x for x in tmg.NB if x not in (SHAS, UTJ)])
    out["chraam_central"] = ch + s([RAAM])
    out["ch_plus_arab"] = ch + s([RAAM, JL])
    out["ch_plus_shas"] = ch + s([SHAS])
    out["ch_plus_utj"] = ch + s([UTJ])
    out["ch_noyb_plus_haredi"] = s([x for x in tmg.CHANGE if x != YB]) + s([SHAS, UTJ])
    out["ch_plus_likud"] = ch + s([LIKUD])

    g = ctx.gov.set_index("outcome")
    out["repeat_p05"] = 100 * float(g.loc[REPEAT, "p05"])
    out["repeat_p95"] = 100 * float(g.loc[REPEAT, "p95"])
    out["arab_routes"] = get("gov.change_raam") + get("gov.centre_minority")
    out["pledge_left"] = get("gov.change_alone") + get("gov.change_amcha")

    out["min_change_pass"] = 100 * min(float(get(f"fc.{x}.pass")) for x in CHANGE_SHORT)

    out["pers1_ch61_after"] = get("atlas.ch61") + get("lev.pers_likud_1.0.ch61")
    out["pers1_chraam61_after"] = get("atlas.chraam61") + get("lev.pers_likud_1.0.chraam61")

    # Value-dependent wording, generated so it stays true after a refit.
    out["ch_short"] = 61 - ch
    out["chraam_short"] = 61 - out["chraam_central"]
    out["chraam_vs_ch_times"] = times_phrase(get("bloc.chraam61"), get("bloc.ch61"))
    out["repeat_vs_changeled_times"] = times_phrase(get("gov.repeat"), get("gov.change_led"))
    v = out["ch_noyb_plus_haredi"]
    out["noyb_haredi_phrase"] = (f"{v}, still short of 61" if v < 61 else
                                 "61, the barest majority" if v == 61 else f"{v}, a majority")
    a, g = _half_up(get("atlas.govt")), _half_up(get("gov.change_led"))
    out["atlas_base_phrase"] = (f"also about {a:.0f}%" if a == g else
                                f"about {a:.0f}%, close to the {g:.0f}% here")
    return out
