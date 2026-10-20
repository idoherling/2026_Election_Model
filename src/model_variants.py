"""Model variants for the site's "Choose a model" explorer.

The OFFICIAL forecast is the published one and the site headline. The other
variants are graded alternatives: candidates that narrowly failed the
pre-registered shipping rule (s.46 / s.53 / s.55), a layer switched off, the
simple benchmark pipeline, and placeholders for work in progress. The
explorer shows what each one predicts for 2026 (src/build_variants.py runs
it through the production chain) and how each one scored on the backtest.

A variant is
  id            url-safe key (?model=<id> on the site)
  name / desc   EN and HE; desc is one paragraph of HTML whose claims cite the
                evidence registry (<a class="cite" data-s="ID">, ids from
                data/forecast_sources.json) and the decision log
                (decision-log.html#sNN)
  kind          "bayes": the production chain (bayes_model.project on the
                production posterior -> registration mixture -> official
                central count -> formation) with `flags` applied;
                "simple": the weighted-average benchmark (polling_average +
                simulate), then the same central count and formation
  flags         {module: {ATTRIBUTE: value}}, module attributes of
                bayes_model / government_formation (or simulate,
                registration_scenarios) overridden for the run by
                variant_flags(), which restores them afterwards. A callable
                is called at build time and may return None (= unavailable)
  sections      the dossier sections that grade or define it
  backtest      the graded scores at the eve, D-7 and D-21; see BASIS. A
                horizon or metric with no number on that basis is None, never
                a number from another harness
  status        "official" | "advanced" (the leading alternative) | "previous" (the official model as published
                before its last graded change) | "failed" (graded under the rule,
                did not pass) | "layer" (a shipped layer switched off)
                | "benchmark" | "candidate" (not graded on BASIS yet)

A variant whose flag is not in the code yet is skipped. available() checks with hasattr that every flag is a real module
attribute (stacked reads its weights from bayes_model.ERROR_STACK_WEIGHTS),
so a variant appears on the site by itself once the flag lands, and is
skipped until then.

Adding a variant: append a Variant to VARIANTS (flags as module attributes
that already exist in the code, the dossier section, the EN/HE texts with
their citations, and the backtest rows from the graded run on BASIS), then
run `python src/build_variants.py` (or the pipeline) and rebuild the site.
"""
from __future__ import annotations

import contextlib
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# The one scoring basis every backtest number below is on: the official row
# and each variant's row come from the same harness, the same caches, the
# same list mask and the same seeds.
BASIS = {
    "id": "loo50_3seed",
    "technical": ("leave-one-cycle-out harness on the s.50 leave-one-out pollster-scorecard caches "
                  "(CLR latent, ballot-fidelity windows), the shipped list mask (*_fixed), eight "
                  "cycles 2009-2022; eve, D-7 and D-21 each pooled over harness seed offsets "
                  "0/100/200 (s.55 protocol)"),
    "metrics": ["median_mae", "mean_mae", "coverage", "brier", "interval"],
    "horizons": ["eve", "D-7", "D-21"],
}


def _row(median_mae, mean_mae, coverage, brier, interval) -> dict:
    return {"median_mae": median_mae, "mean_mae": mean_mae, "coverage": coverage,
            "brier": brier, "interval": interval}


def _dl(n: int, he: bool = False, first: bool = True) -> str:
    """A decision-log link in the site's house style."""
    if he:
        lab = f"יומן ההחלטות, ‎§{n}" if first else f"‎§{n}"
    else:
        lab = f"decision log §{n}" if first else f"§{n}"
    return f'<a href="decision-log.html#s{n}" rel="noopener">{lab}</a>'


def _n(x: str) -> str:
    """A number inside Hebrew text, isolated left-to-right."""
    return f'<span class="ltr">{x}</span>'


BASIS["en"] = ("the eight elections of 2009–2022, each forecast again from the polls published "
               "before it, with every parameter estimated on the other seven elections and the "
               "pollster weights graded without it (" + _dl(50) + "), at the eve, a week out and "
               "three weeks out, each the mean of three random seeds (" + _dl(55, first=False)
               + "); every row on the same harness, past polls and lists as the official row")
BASIS["he"] = ("שמונה מערכות הבחירות של 2009–2022, שכל אחת מהן נחזתה מחדש מהסקרים שפורסמו לפניה, "
               "כשכל פרמטר נאמד על שבע המערכות האחרות ומשקלי הסוקרים דורגו בלעדיה ("
               + _dl(50, True) + "), בערב הבחירות, שבוע לפני ושלושה שבועות לפני, כל אחד ממוצע "
               "של שלושה זרעים אקראיים (" + _dl(55, True, False) + "); כל שורה על אותו מערך "
               "בדיקה, אותם סקרי עבר ואותן רשימות כמו השורה הרשמית")


@dataclass(frozen=True)
class Variant:
    id: str
    name_en: str
    name_he: str
    desc_en: str
    desc_he: str
    flags: Any = field(default_factory=dict)   # {module: {ATTR: value}} or a callable
    kind: str = "bayes"
    sections: tuple = ()
    status: str = "failed"
    verdict_en: str = ""
    verdict_he: str = ""
    backtest: dict | None = None
    backtest_src: str = ""

    def resolved_flags(self) -> dict | None:
        """The flags dict, or None when a callable says the variant is not
        available yet."""
        f = self.flags() if callable(self.flags) else self.flags
        return None if f is None else dict(f)


# --- flag handling ----------------------------------------------------------

def _module(name: str):
    return importlib.import_module(name)


def missing_flags(flags: dict) -> list[str]:
    """'module.ATTR' for every flag that is not an attribute in the code."""
    out = []
    for mod, attrs in flags.items():
        m = _module(mod)
        out += [f"{mod}.{a}" for a in attrs if not hasattr(m, a)]
    return out


@contextlib.contextmanager
def variant_flags(flags: dict):
    """Apply {module: {ATTR: value}} for the duration of the block and put
    every attribute back afterwards, also when the block raises. An
    attribute that does not exist raises AttributeError before anything is
    changed (a typo must not create a new, silently unused attribute)."""
    missing = missing_flags(flags or {})
    if missing:
        raise AttributeError(f"not module attributes: {missing}")
    saved = []
    try:
        for mod, attrs in (flags or {}).items():
            m = _module(mod)
            for a, v in attrs.items():
                saved.append((m, a, getattr(m, a)))
                setattr(m, a, v)
        yield
    finally:
        for m, a, v in reversed(saved):
            setattr(m, a, v)


def available(v: Variant) -> tuple[bool, str]:
    """(available, reason). A placeholder whose flag or input does not exist
    yet is skipped, not an error."""
    try:
        flags = v.resolved_flags()
    except Exception as e:   # a malformed weights file and the like
        return False, f"flags not resolvable: {e}"
    if flags is None:
        return False, "input not present"
    miss = missing_flags(flags)
    if miss:
        return False, "flag not in the code: " + ", ".join(miss)
    return True, ""


def _stack_flags() -> dict | None:
    """The s.62 stack at its fitted production weights
    (bayes_model.ERROR_STACK_WEIGHTS). While ERROR_STACK is set the stack owns
    the residual line and the t scaling, so RESID_SPACE "seat" and
    T_UNIT_VAR False, the configuration s.62 graded. None until the stacking
    code exists."""
    import bayes_model as bm
    if not hasattr(bm, "ERROR_STACK_WEIGHTS"):
        return None
    return {"bayes_model": {"ERROR_STACK": dict(bm.ERROR_STACK_WEIGHTS),
                            "RESID_SPACE": "seat", "T_UNIT_VAR": False}}


# --- the registry -----------------------------------------------------------

# The official row is the shipped configuration since 18 Oct (RESID_SPACE
# "seat_fix", s.62.5): s.62.2's Bfix row, three seeds. The pre-fix shipped row
# (RESID_SPACE "seat") is the old_residual variant's, and the reproduction
# gate of s.57.3, s.60.2 and s.62.2.
_OFFICIAL_ROWS = {
    "eve": _row(1.4858, 1.6253, 0.9717, 0.0447, 9.0108),
    "D-7": _row(1.4860, 1.6424, 0.9604, 0.0465, 9.3891),
    "D-21": _row(1.6249, 1.7795, 0.9683, 0.0519, 9.5994),
}
_SEAT_ROWS = {
    "eve": _row(1.4927, 1.6291, 0.9807, 0.0475, 9.2173),
    "D-7": _row(1.4866, 1.6478, 0.9896, 0.0490, 9.3600),
    "D-21": _row(1.6211, 1.7943, 0.9896, 0.0541, 9.6900),
}

VARIANTS: list[Variant] = [
    Variant(
        id="official",
        name_en="Official", name_he="המודל הרשמי",
        status="official", sections=(46, 50, 55, 62),
        desc_en=("The published forecast: every headline number on this page comes from it. A Bayesian "
                 "state-space model of every 2026 poll and CEC filing is projected to election day "
                 "through the election-day shocks measured on eight past elections, mixed over the "
                 "open registration events, and passed through the 3.25% threshold and Bader–Ofer. "
                 "Each graded layer in it passed the pre-registered shipping rule on the "
                 "leave-one-cycle-out backtest <a class=\"cite\" data-s=\"DL-28,DL-46\"></a>; the "
                 "judgment layers the backtest cannot see (the certainty layer, event risk, the "
                 "capacity bounds) are stated as such (" + _dl(55) + "). Since 18 October its "
                 "per-list residual is the corrected line (" + _dl(62, first=False) + "). Its scores "
                 "are the row every alternative is graded against <a class=\"cite\" "
                 "data-s=\"EVAL-F17\"></a>."),
        desc_he=("התחזית שמתפרסמת: כל מספר בכותרות העמוד מגיע ממנה. מודל מרחב־מצבים בייסיאני של כל סקרי "
                 "2026 וכל הדוחות לוועדת הבחירות מוקרן ליום הבחירות דרך זעזועי יום הבחירות שנמדדו "
                 "בשמונה מערכות בחירות קודמות, מעורבב על פני אירועי ההרשמה הפתוחים, ומועבר דרך אחוז "
                 "החסימה (" + _n("3.25%") + ") ושיטת באדר־עופר. כל שכבה שנבחנה בו עברה את כלל "
                 "ההכנסה שנרשם מראש במבחן־העבר בהשמטת־מחזור <a class=\"cite\" "
                 "data-s=\"DL-28,DL-46\"></a>; השכבות השיפוטיות שמבחן־העבר אינו רואה (שכבת הוודאות, "
                 "סיכון האירועים, גבולות הקיבולת) מוצהרות ככאלה (" + _dl(55, True) + "). מאז "
                 "18 באוקטובר הזעזוע השיורי לכל רשימה בו הוא הקו המתוקן (" + _dl(62, True, False)
                 + "). הציונים שלו הם השורה שכל חלופה נמדדת מולה <a class=\"cite\" "
                 "data-s=\"EVAL-F17\"></a>."),
        verdict_en="Passed the pre-registered rule; published.",
        verdict_he="עבר את הכלל שנרשם מראש; מתפרסם.",
        backtest=_OFFICIAL_ROWS,
        backtest_src=("dossier s.62.2 (arm Bfix = RESID_SPACE seat_fix, shipped in s.62.5; three "
                      "seeds); scratch s62/grade.txt arm 'Bfix' and w57/diag arm 'cal_Bfix' "
                      "(identical)"),
    ),
    # the leading alternative (s.61): shown once bayes_model.ERROR_MODEL exists
    Variant(
        id="hierarchical",
        name_en="Advanced hierarchical model", name_he="המודל ההיררכי המתקדם",
        flags={"bayes_model": {"ERROR_MODEL": "hierarchical"}},
        sections=(61,), status="advanced",
        desc_en=("The advanced model. Instead of measuring each election-day error separately and "
                 "stacking the pieces, it fits the whole error record of the eight past elections at "
                 "once as a hierarchical Bayesian model: a bloc error, a haredi family error and a "
                 "Student-t residual whose width grows with the list's size, each estimated with "
                 "its own uncertainty, and it draws 2026's errors from that model's predictive for a "
                 "new election <a class=\"cite\" data-s=\"AGG-F08\"></a>. On the backtest it "
                 "beats the official model on every proper score at every horizon: a lower mean "
                 "error, threshold Brier score and interval score, and a 24–29% better Brier score "
                 "for a Netanyahu-bloc majority <a class=\"cite\" data-s=\"EVAL-F01,EVAL-F02\"></a>. "
                 "It is not the official forecast because it fails two of the pre-registered tests: "
                 "in 2015 it misses a large list's median by one more seat a week and three weeks "
                 "out, and three weeks out its 90% intervals cover 97.5% of results against the "
                 "official 96.8%, further from 90% (" + _dl(61) + "). It puts the correlated bloc "
                 "error at about half the official swing, so it gives either side a majority less "
                 "often."),
        desc_he=("המודל המתקדם. במקום למדוד כל שגיאה של יום הבחירות בנפרד ולחבר את החלקים זה על גבי זה, הוא "
                 "מתאים בבת אחת את כל רקורד השגיאות של שמונה מערכות הבחירות הקודמות כמודל בייסיאני "
                 "היררכי: שגיאה גושית, שגיאה של המשפחה החרדית ושיורי מהתפלגות t שרוחבו גדל עם גודל "
                 "הרשימה, כל אחד נאמד עם אי־הוודאות שלו, ואת השגיאות של 2026 הוא מגריל מהתחזית של "
                 "המודל הזה למערכת בחירות חדשה <a class=\"cite\" data-s=\"AGG-F08\"></a>. "
                 "במבחן־העבר הוא עדיף על המודל הרשמי בכל ציון תקין ובכל אופק: שגיאה ממוצעת, ציון "
                 "ברייר של אחוז החסימה וציון רווח נמוכים יותר, וציון ברייר טוב ב־" + _n("24–29%")
                 + " לרוב של גוש נתניהו <a class=\"cite\" data-s=\"EVAL-F01,EVAL-F02\"></a>. "
                 "הוא אינו התחזית הרשמית משום שהוא נכשל בשניים מהמבחנים שנרשמו מראש: ב־2015 הוא "
                 "מחטיא את החציון של רשימה גדולה במנדט נוסף שבוע ושלושה שבועות לפני, ושלושה "
                 "שבועות לפני רווחי ה־90% שלו מכסים " + _n("97.5%") + " מהתוצאות מול " + _n("96.8%")
                 + " במודל הרשמי, רחוק יותר מ־90% (" + _dl(61, True) + "). הוא מעריך את השגיאה "
                 "הגושית המתואמת בכמחצית מהתנודה של המודל הרשמי, ולכן הוא נותן רוב לאחד הצדדים "
                 "לעתים רחוקות יותר."),
        verdict_en=("Wins every proper score at every horizon; fails the 2015 median fold a week out "
                    "(+0.121) and three weeks out (+0.182), and the three-week coverage test (97.5% "
                    "against 96.8%)."),
        verdict_he=("מנצח בכל ציון תקין בכל אופק; נכשל בקפל החציון של 2015 שבוע לפני ("
                    + _n("+0.121") + ") ושלושה שבועות לפני (" + _n("+0.182") + "), ובמבחן הכיסוי "
                    "שלושה שבועות לפני (" + _n("97.5%") + " מול " + _n("96.8%") + ")."),
        backtest={
            "eve": _row(1.5393, 1.6105, 0.9717, 0.0405, 8.6723),
            "D-7": _row(1.4827, 1.6382, 0.9582, 0.0437, 9.0865),
            "D-21": _row(1.6753, 1.7695, 0.9747, 0.0498, 9.2435),
        },
        backtest_src=("dossier s.61.2 (arm H1 against the seat_fix shipped stack, three seeds; its "
                      "shipped rows = the official rows); scratch hier/grade/registered_rows.csv"),
    ),
    Variant(
        id="bw_2022",
        name_en="Blue and White voters: 2022 pattern", name_he="מצביעי כחול לבן: דפוס 2022",
        flags=lambda: {"registration_scenarios": {"FOLD_TRANSFER": dict(
            __import__("registration_scenarios").FOLD_TRANSFER,
            blue_white=list(__import__("registration_scenarios").BW_TRANSFER_2022))}},
        sections=(64,), status="previous",
        desc_en=("The official model with Blue and White's withdrawn vote routed by the list's measured "
                 "2022 pattern, when its absorbed voters went to National Unity (70%) and Yesh Atid (30%): "
                 "60% to Yashar and 25% to Together, the rest staying home. It was the official assumption "
                 "until 20 October, when it was replaced by an editorial judgment that Gantz's last voters "
                 "lean towards a unity government (" + _dl(64) + "). No poll has yet measured where they go."),
        desc_he=("המודל הרשמי כשקולות כחול לבן שפרשה מנותבים לפי הדפוס שנמדד אצל הרשימה ב־2022, כשבוחריה "
                 "שנבלעו עברו למחנה הממלכתי (" + _n("70%") + ") וליש עתיד (" + _n("30%") + "): " + _n("60%")
                 + " לישר ו־" + _n("25%") + " לביחד, והשאר נשארים בבית. זו הייתה ההנחה הרשמית עד 20 באוקטובר, "
                 "אז הוחלפה בשיפוט מערכתי שלפיו בוחריו האחרונים של גנץ נוטים לממשלת אחדות (" + _dl(64, True)
                 + "). אף סקר עוד לא מדד לאן הם הולכים."),
        verdict_en="Official until 20 October; replaced by an editorial judgment, not by a graded test.",
        verdict_he="רשמי עד 20 באוקטובר; הוחלף בשיפוט מערכתי, לא במבחן מדורג.",
        backtest=_OFFICIAL_ROWS,
        backtest_src=("a 2026 registration judgment the backtest cannot see: its rows are the official "
                      "rows"),
    ),
    Variant(
        id="old_residual",
        name_en="Old residual line", name_he="קו השיורי הישן",
        flags={"bayes_model": {"RESID_SPACE": "seat"}},
        sections=(48, 62), status="previous",
        desc_en=("The official model with the per-list residual line it used until 18 October. "
                 "That line was fitted on the seat errors of eight past elections pooled with a "
                 "colliding index, so the seat leader's anchor was subtracted from every row that "
                 "shared its label; the fitted sd was 1.83 + 0.044 × seats instead of 1.48 + "
                 "0.041 × seats <a class=\"cite\" data-s=\"ERR-F24\"></a>. The corrected line "
                 "passed the rule at every horizon on three seeds and replaced it (" + _dl(48) + ", "
                 + _dl(62, first=False) + "). It is shown so the effect of the fix can be read off."),
        desc_he=("המודל הרשמי עם קו הזעזוע השיורי לכל רשימה שבו השתמש עד 18 באוקטובר. הקו הזה "
                 "הותאם על שגיאות במנדטים משמונה מערכות בחירות שאוחדו עם אינדקס מתנגש, כך שעוגן "
                 "הרשימה המובילה הופחת מכל שורה שנשאה את אותה תווית; סטיית התקן שהותאמה הייתה "
                 + _n("1.83") + " ועוד " + _n("0.044") + " לכל מנדט של הרשימה, במקום " + _n("1.48")
                 + " ועוד " + _n("0.041") + " <a class=\"cite\" data-s=\"ERR-F24\"></a>. הקו המתוקן עבר את הכלל בכל אופק "
                 "על שלושה זרעים והחליף אותו (" + _dl(48, True) + ", " + _dl(62, True, False)
                 + "). הוא מוצג כדי שאפשר יהיה לראות את השפעת התיקון."),
        verdict_en="Published until 18 October; the corrected line passed the rule and replaced it.",
        verdict_he="פורסם עד 18 באוקטובר; הקו המתוקן עבר את הכלל והחליף אותו.",
        backtest=_SEAT_ROWS,
        backtest_src=("dossier s.57.3 / s.60.2 / s.62.2 (the then-shipped row, the reproduction "
                      "gate of all three; three seeds); scratch s62/grade.txt arm 'shipped', "
                      "w57/diag arm 'shipped'"),
    ),
    Variant(
        id="vote_residual",
        name_en="Vote-share residual", name_he="שיורי לפי נתחי קולות",
        flags={"bayes_model": {"RESID_SPACE": "vote"}},
        sections=(48, 57),
        desc_en=("The per-list election-day residual re-estimated on the vote-share errors of the "
                 "lists that ran, instead of their seat errors. In the seat record a list that died "
                 "at the threshold counts as a miss of its whole polled seat count, and the "
                 "projection then applies the threshold again, so each death is counted twice "
                 "<a class=\"cite\" data-s=\"ERR-F22,ERR-F24\"></a>. Graded twice (" + _dl(48)
                 + ", arm B; " + _dl(57, first=False) + ", cal_B): it improves the mean error, the "
                 "threshold Brier score and the interval score at every horizon and moves coverage "
                 "toward 90%, but fails the fold test at the eve, where one-seat median flips on "
                 "large lists (September 2019 on the boundary, 2022 +0.13) count against it."),
        desc_he=("הזעזוע השיורי של יום הבחירות לכל רשימה נאמד מחדש על שגיאות בנתחי הקולות של "
                 "הרשימות שהתמודדו, במקום על שגיאות במנדטים. ברקורד המנדטים, רשימה שנפלה מתחת "
                 "לאחוז החסימה נספרת כהחטאה של כל המנדטים שנסקרו לה, וההקרנה מפעילה את אחוז החסימה "
                 "פעם נוספת, כך שכל נפילה נספרת פעמיים <a class=\"cite\" "
                 "data-s=\"ERR-F22,ERR-F24\"></a>. החלופה נבחנה פעמיים (" + _dl(48, True)
                 + ", זרוע B; " + _dl(57, True, False) + ", cal_B): היא משפרת את השגיאה הממוצעת, את "
                 "ציון ברייר של אחוז החסימה ואת ציון הרווח בכל אופק ומקרבת את הכיסוי ל־90%, אבל "
                 "נכשלת במבחן הקפלים בערב הבחירות, שבו היפוכים של מנדט אחד בחציון של רשימות "
                 "גדולות (ספטמבר 2019 על הגבול, 2022 " + _n("+0.13") + ") נזקפים לחובתה."),
        verdict_en=("Failed the eve fold test: September 2019 (+0.100, on the boundary) and 2022 "
                    "(+0.128)."),
        verdict_he=("נכשל במבחן הקפלים בערב הבחירות: ספטמבר 2019 (" + _n("+0.100") + ", על הגבול) ו־2022 ("
                    + _n("+0.128") + ")."),
        backtest={
            "eve": _row(1.5196, 1.6013, 0.9717, 0.0409, 8.6709),
            "D-7": _row(1.4591, 1.6273, 0.9514, 0.0439, 9.0077),
            "D-21": _row(1.6196, 1.7550, 0.9524, 0.0502, 9.5263),
        },
        backtest_src="dossier s.57.3 (cal_B, three seeds); scratch w57/diag arm 'cal_B'",
    ),
    Variant(
        id="resid_hybrid",
        name_en="Hybrid residual", name_he="שיורי היברידי",
        flags={"bayes_model": {"RESID_SPACE": "hybrid"}},
        sections=(60,),
        desc_en=("The vote-share residual for lists of up to 8 seats only, the residual's own "
                 "small-list group, and the shipped seat-error line for every larger list, so the "
                 "large lists keep their graded width <a class=\"cite\" data-s=\"ERR-F24\"></a>. "
                 "Near the threshold it behaves like the vote-share residual and it wins every "
                 "pooled score a week and three weeks out, but it loses two folds, 2022 at the eve "
                 "(+0.13) and 2021 a week out (+0.12): the seats freed when small lists die land in "
                 "the large lists' medians (" + _dl(60) + ")."),
        desc_he=("הזעזוע השיורי לפי נתחי קולות רק לרשימות של עד 8 מנדטים, קבוצת הרשימות הקטנות "
                 "של השיורי עצמו, וקו השגיאות במנדטים של המודל הרשמי לכל רשימה גדולה יותר, כך "
                 "שהרשימות הגדולות שומרות על הרוחב שנבחן <a class=\"cite\" data-s=\"ERR-F24\"></a>. "
                 "ליד אחוז החסימה הוא מתנהג כמו השיורי לפי נתחי קולות, והוא מנצח בכל ציון מאוחד "
                 "שבוע ושלושה שבועות לפני, אבל מפסיד בשני קפלים, 2022 בערב הבחירות ("
                 + _n("+0.13") + ") ו־2021 שבוע לפני (" + _n("+0.12") + "): המנדטים שמשתחררים "
                 "כשרשימות קטנות נופלות עוברים לחציון של הרשימות הגדולות (" + _dl(60, True) + ")."),
        verdict_en=("Failed two folds: 2022 at the eve (+0.128) and 2021 a week out (+0.119); every "
                    "pooled score passed."),
        verdict_he=("נכשל בשני קפלים: 2022 בערב הבחירות (" + _n("+0.128") + ") ו־2021 שבוע לפני ("
                    + _n("+0.119") + "); כל ציון מאוחד עבר."),
        backtest={
            "eve": _row(1.5111, 1.6000, 0.9717, 0.0410, 8.8149),
            "D-7": _row(1.4607, 1.6250, 0.9769, 0.0439, 8.9701),
            "D-21": _row(1.6181, 1.7535, 0.9678, 0.0503, 9.4421),
        },
        backtest_src="dossier s.60.2 (three seeds); scratch w57/diag60 arm 'resid_hybrid'",
    ),
    Variant(
        id="stacked",
        name_en="Stacked error models", name_he="שילוב מודלי שגיאה",
        flags=_stack_flags,
        sections=(62,), status="failed",
        desc_en=("Each simulated election draws its error stack from one of three graded "
                 "alternatives, weighted by Bayesian stacking on the backtest's leave-one-out log "
                 "score: the t-scale fix .302, the vote-share residual .448 and the hybrid "
                 "residual .250 <a class=\"cite\" data-s=\"EVAL-F12\"></a>. The mixture's "
                 "median sits between its components', so the one-seat median flips that failed "
                 "the residual alternatives become ties in every past election. Graded by nested "
                 "leave-one-out <a class=\"cite\" data-s=\"EVAL-F15\"></a>, it loses the "
                 "interval score a week and three weeks out, almost all of it on 2021, and its "
                 "out-of-sample log score is below every component's: eight elections cannot pin "
                 "down the weights (" + _dl(62) + ")."),
        desc_he=("כל בחירות מדומות מגרילות את שכבת השגיאה שלהן מאחת משלוש חלופות שנבחנו, "
                 "במשקלים שנקבעו בשיטת stacking בייסיאנית לפי ציון הלוג בהשמטת־מחזור של "
                 "מבחן־העבר: תיקון סקאלת t " + _n(".302") + ", השיורי לפי נתחי קולות "
                 + _n(".448") + " והשיורי ההיברידי " + _n(".250") + " <a class=\"cite\" "
                 "data-s=\"EVAL-F12\"></a>. החציון של התערובת נמצא בין החציונים של רכיביה, "
                 "ולכן היפוכי המנדט האחד בחציון, שהכשילו את חלופות השיורי, הופכים לתיקו בכל "
                 "מערכת עבר. בבחינה בהשמטת־מחזור מקוננת <a class=\"cite\" "
                 "data-s=\"EVAL-F15\"></a> היא מפסידה בציון הרווח שבוע ושלושה שבועות לפני, "
                 "כמעט כולו ב־2021, וציון הלוג שלה מחוץ למדגם נמוך מזה של כל אחד מרכיביה: שמונה "
                 "מערכות בחירות אינן מספיקות כדי לקבוע את המשקלים (" + _dl(62, True) + ")."),
        verdict_en=("Failed: the interval score a week out (+0.064) and three weeks out (+0.114); "
                    "every median fold tied."),
        verdict_he=("נכשל: ציון הרווח שבוע לפני (" + _n("+0.064") + ") ושלושה שבועות לפני ("
                    + _n("+0.114") + "); כל קפלי החציון בתיקו."),
        backtest={
            "eve": _row(1.4855, 1.6130, 0.9717, 0.0423, 9.0273),
            "D-7": _row(1.4748, 1.6363, 0.9552, 0.0450, 9.4238),
            "D-21": _row(1.6169, 1.7698, 0.9524, 0.0510, 9.8036),
        },
        backtest_src=("dossier s.62.2 (the graded nested-LOO stacked forecast, row 'stack', three "
                      "seeds; production weights = bayes_model.ERROR_STACK_WEIGHTS); scratch "
                      "s62/grade.txt"),
    ),
    Variant(
        id="t_unit_narrow",
        name_en="Narrower shocks", name_he="זעזועים צרים יותר",
        # graded (s.48.6) on the residual line before the 18 Oct fix: run on that line
        flags={"bayes_model": {"T_UNIT_VAR": True, "RESID_SCALE": 0.6, "RESID_SPACE": "seat"}},
        sections=(48,),
        desc_en=("Two changes to the width of the election-day shocks. Each Student-t shock is "
                 "scaled to unit variance, so the bloc swing and the sector shocks have the spread "
                 "they were measured at instead of 1.29 times it <a class=\"cite\" "
                 "data-s=\"ERR-F13\"></a>, and the per-list residual is cut to 0.6 of the shipped "
                 "line, the width chosen by nested leave-one-cycle-out <a class=\"cite\" "
                 "data-s=\"EVAL-F15\"></a>. It passed on the first harness, whose pollster weights "
                 "had seen each graded election's final polls; on the leak-free harness its chosen "
                 "width moved from 0.4 to 0.6 and it loses the interval score a week and three "
                 "weeks out beyond the tolerance (" + _dl(48) + "). It was graded on the residual "
                 "line as fitted before the 18 October fix and runs on that line here; the two "
                 "horizons were graded on one seed only, so the scorecard leaves them blank."),
        desc_he=("שני שינויים ברוחב זעזועי יום הבחירות. כל זעזוע מהתפלגות t מנורמל לשונות אחת, כך "
                 "שלתנודת הגוש ולזעזועי המגזרים יש הפיזור שבו נמדדו ולא פי " + _n("1.29")
                 + " ממנו <a class=\"cite\" data-s=\"ERR-F13\"></a>, והזעזוע השיורי לכל רשימה מצטמצם "
                 "ל־" + _n("0.6") + " מהקו של המודל הרשמי, הרוחב שנבחר בהשמטת־מחזור מקוננת "
                 "<a class=\"cite\" data-s=\"EVAL-F15\"></a>. החלופה עברה במבחן־העבר הראשון, שבו "
                 "משקלי הסוקרים כבר הכירו את הסקרים הסופיים של כל מערכת שנבחנה; במבחן־העבר הנקי "
                 "מהדליפה הרוחב שנבחר זז מ־" + _n("0.4") + " ל־" + _n("0.6") + " והיא מפסידה בציון "
                 "הרווח שבוע ושלושה שבועות לפני מעבר לסף הסובלנות (" + _dl(48, True) + "). היא "
                 "נבחנה על קו השיורי כפי שהותאם לפני התיקון של 18 באוקטובר ומורצת כאן על אותו קו; "
                 "שני האופקים האלה נבחנו על זרע אחד בלבד, ולכן כרטיס הציונים משאיר אותם ריקים."),
        verdict_en=("Failed on the leak-free harness: the interval score a week out (+0.174) and "
                    "three weeks out (+0.236), beyond the 0.05 tolerance (one seed)."),
        verdict_he=("נכשל במבחן־העבר הנקי: ציון הרווח שבוע לפני (" + _n("+0.174") + ") ושלושה "
                    "שבועות לפני (" + _n("+0.236") + "), מעבר לסף של " + _n("0.05") + " (זרע אחד)."),
        backtest={
            "eve": _row(1.5184, 1.6170, 0.9514, 0.0421, 8.8585),
            "D-7": None,    # offset 0 only (s.48.6): not the three-seed basis
            "D-21": None,
        },
        backtest_src=("dossier s.48.6 (arm CA = T_UNIT_VAR + nested width, on the pre-fix seat "
                      "line; eve offsets 0/100/200 on the s.50 caches, its base row = the pre-fix "
                      "shipped eve row); scratch w48loo/summary.csv. D-7 and D-21 exist on offset "
                      "0 only and are left empty"),
    ),
    Variant(
        id="no_trail",
        name_en="No late Likud surge", name_he="בלי זינוק מאוחר לליכוד",
        flags={"bayes_model": {"TRAIL_ON": False}},
        sections=(36, 46, 57), status="layer",
        desc_en=("The polls and every other layer as published, without the trailing-Likud layer: "
                 "no late Likud surge when Likud trails or ties the largest list outside its bloc. "
                 "The layer rests on the three cycles in which Likud trailed in the final week "
                 "(2015, April and September 2019), when it beat its final polls by +8.8, +6.8 "
                 "and −0.5 seats, paid mostly by its own bloc's smaller lists <a class=\"cite\" "
                 "data-s=\"DL-36,DYN-F09,ERR-F19\"></a>. It is a layer check, not a candidate: "
                 "switched off, the backtest's median and mean seat errors are worse at every "
                 "horizon, so the layer stays (" + _dl(46) + ", " + _dl(57, first=False) + ")."),
        desc_he=("הסקרים וכל שאר השכבות כפי שפורסמו, בלי שכבת הליכוד המפגר: אין זינוק מאוחר "
                 "לליכוד כשהוא מפגר אחרי הרשימה הגדולה ביותר מחוץ לגוש שלו או שווה לה. השכבה נשענת "
                 "על שלוש המערכות שבהן הליכוד פיגר בשבוע האחרון (2015, אפריל וספטמבר 2019), "
                 "ובהן הוא עקף את הסקרים הסופיים שלו ב־" + _n("+8.8") + ", " + _n("+6.8") + " ו־"
                 + _n("−0.5") + " מנדטים, בעיקר על חשבון הרשימות הקטנות של הגוש שלו עצמו "
                 "<a class=\"cite\" data-s=\"DL-36,DYN-F09,ERR-F19\"></a>. זו בדיקת שכבה ולא מועמד: "
                 "כשהיא כבויה, השגיאה החציונית והשגיאה הממוצעת במנדטים גרועות יותר בכל אופק, ולכן "
                 "השכבה נשארת (" + _dl(46, True) + ", " + _dl(57, True, False) + ")."),
        verdict_en="A shipped layer switched off; worse median and mean error at every horizon.",
        verdict_he="שכבה שמתפרסמת, כבויה; שגיאה חציונית וממוצעת גרועות יותר בכל אופק.",
        backtest={
            "eve": _row(1.5657, 1.6688, 0.9604, 0.0505, 9.4144),
            "D-7": _row(1.6205, 1.7240, 0.9490, 0.0509, 9.5894),
            "D-21": _row(1.7345, 1.8456, 0.9683, 0.0514, 9.5424),
        },
        backtest_src=("layer check on the current shipped configuration (RESID_SPACE seat_fix) "
                      "with the s.57.1 runner (every layer as in validate_bayes / validate_horizon, "
                      "s.50 caches, offsets 0/100/200, shipped list mask), gevalt_cond off; its "
                      "shipped rows reproduce the s.62.2 Bfix rows exactly. scratch "
                      "explorer/notrail. The same check on the pre-fix line is s.57.1's "
                      "(w57/diag no_trail); s.46's is on the pre-s.50 harness"),
    ),
    Variant(
        id="simple_average",
        name_en="Simple poll average", name_he="ממוצע סקרים פשוט",
        kind="simple", sections=(23,), status="benchmark",
        desc_en=("The benchmark: each firm's latest poll averaged with weights for recency, sample "
                 "size, the firm's graded accuracy and a discount for related firms "
                 "<a class=\"cite\" data-s=\"DL-23,AGG-F11\"></a>, corrected for house effects and "
                 "trend, then a correlated-error simulation through the same seat law. It reads the "
                 "published seat tables only, not the CEC filings, and has no registration "
                 "mixture, certainty layer or late-surge layers. It is run here on the polls "
                 "fielded since filing day (9 September), when the ballot was fixed; the file it "
                 "last wrote predates the ballot. Its own backtest is a different harness, so the "
                 "scorecard leaves it blank (" + _dl(28) + ")."),
        desc_he=("נקודת הייחוס: הסקר האחרון של כל מכון, בממוצע משוקלל לפי עדכניות, גודל מדגם, "
                 "הדיוק המדורג של המכון והנחה למכונים קשורים <a class=\"cite\" "
                 "data-s=\"DL-23,AGG-F11\"></a>, מתוקן לאפקטי בית ולמגמה, ואחר כך סימולציה של "
                 "שגיאות מתואמות דרך אותו חוק חלוקת מנדטים. הוא קורא רק את טבלאות המנדטים "
                 "שפורסמו, לא את הדוחות לוועדת הבחירות, ואין בו תערובת הרשמה, שכבת ודאות או "
                 "שכבות של זינוק מאוחר. כאן הוא מורץ על הסקרים שנערכו מאז יום הגשת הרשימות "
                 "(9 בספטמבר), כשפתק ההצבעה כבר נקבע; הקובץ שכתב לאחרונה קודם לפתק. מבחן־העבר שלו "
                 "הוא מערך בדיקה אחר, ולכן כרטיס הציונים משאיר אותו ריק (" + _dl(28, True) + ")."),
        verdict_en="Benchmark; graded on its own harness (validate_model.py), not on this basis.",
        verdict_he="נקודת ייחוס; נבחן במערך בדיקה משלו (validate_model.py), לא על הבסיס הזה.",
        backtest={"eve": None, "D-7": None, "D-21": None},
        backtest_src=("none on the official basis: the simple pipeline's retro-validation "
                      "(validate_model.py, model_validation.csv) is a different harness"),
    ),
]

BY_ID = {v.id: v for v in VARIANTS}


def get(vid: str) -> Variant:
    return BY_ID[vid]


def cited_ids(v: Variant) -> set[str]:
    """Every registry id the variant's texts cite."""
    import re
    out = set()
    for txt in (v.desc_en, v.desc_he):
        for attr in re.findall(r'data-s="([^"]+)"', txt):
            out |= {x.strip() for x in attr.split(",") if x.strip()}
    return out


def dl_sections(v: Variant) -> set[int]:
    import re
    return {int(n) for txt in (v.desc_en, v.desc_he)
            for n in re.findall(r'decision-log\.html#s(\d+)', txt)}
