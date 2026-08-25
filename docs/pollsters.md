# The Israeli Polling Industry, 2026 Cycle

Reference dossier on every firm in the poll database: principals, clients,
methodology, lineage, and — critically for modeling — which house effects are
correlated rather than independent. Compiled August 2026 from Hebrew and
English sources; claims tagged [verified] / [inference] / [unresolved] where
it matters. Companion machine-readable table: `data/pollster_meta.csv`.

## The headline for modeling

**The 2026 field is two blocs, not fourteen independent draws.**

- The two coalition-friendly outliers — **Direct Polls** (i24NEWS, house
  effect +8.0) and **Filber/Next Data** (Channel 14, +11.5) — are the two
  halves of one former firm. Direct Polls was founded in 2019 by **Shlomo
  Filber** (the former Likud campaigns chief, Netanyahu-appointed
  Communications Ministry DG, and Case 4000 state's witness — the same
  person) together with **Zuriel Sharon**, who ran Likud's SMS operation in
  2015. In April 2025 Filber sold his stake to Sharon; Direct Polls signed
  exclusively with i24NEWS, while Filber went on to advise **Next Data** — a
  polling company registered October 2025 and, per a May 2026 Haaretz exposé,
  owned by Channel 14's owners' representative (Netanel Siman-Tov, via Ofrim
  Media). The channel published its own polls without disclosing it owns the
  pollster; the Press Council flagged it, and in August 2026 Haaretz reported
  Channel 14 failed to file poll data with the Central Elections Committee.
  Shared personnel, shared undisclosed SMS methodology, shared political
  provenance: **model these two as one strongly correlated pair.**
- The mainstream firms share infrastructure too: three opt-in internet panels
  carry most of the industry (see table below), so "mainstream consensus" is
  partly a shared-mode artifact — the same under-coverage of offline haredim
  and Arab society pushes them all the same way. An August 2026 Haaretz
  investigation into poll-rigging bots infiltrating these panels adds a
  shared vulnerability.
- **Arab-sector assumptions flow through one node**: StatNet (Yousef
  Makladeh, Haifa) supplies the Arab-sector sample to Channel 13/HaMadad,
  Maagar Mochot, and its own Dayan Center polls. An error there propagates
  across nominally independent houses.
- **Accuracy and lean are separate axes.** Direct Polls was among the most
  accurate nationally in 2021–2022 (the only house calling the 2022
  Netanyahu-bloc majority), then failed 14 of 40 cities in the Feb 2024
  municipal exit polls for Channel 14 and redefined error margins to claim
  "90.5% accuracy". Maagar Mochot is mainstream-bloc in 2026 but ranks last
  on accuracy. Smith is the consistent accuracy leader (best in Knesset
  22, 23, 24, and 2022 per the Paamon ratings) with a ~zero house effect in
  all nine cycles of our own backtest. Estimate accuracy weights and
  house-effect priors separately.

## Active firms

| Firm | Principal | Outlet(s) | Fieldwork | Notes |
|---|---|---|---|---|
| Midgam | Mano Geva (founded 1988) | Channel 12 / N12 (TV flagship since 1999-era Ch1) | iPanel + phone | Geva co-founded iPanel — pollster part-owns its panel. Mina Tzemach (ex-Dahaf) partner since 2013. NOT related to "Midgam Project". |
| Lazar / Panels Politics | Dr. Menachem Lazar | Maariv, 103FM, Knesset Channel | Panel4All | Lazar co-founded the Panels institute (2006) that owns Panel4All; "Lazar Research" and "Panels Politics" are the same operation under two bylines. |
| Kantar | Dudi Hasid | Kan 11; Israel Hayom (2026) | Kantar infra | Corporate heir of Teleseker (→ TNS Teleseker → Kantar). Closest exit poll of Sep 2019. |
| Maagar Mochot | Prof. Yitzhak Katz | 103FM, Israel Hayom era, Arutz Sheva, Ch16 | mixed; StatNet for Arab sector | Bottom of the Paamon accuracy rankings across recent cycles. |
| Direct Polls | Zuriel Sharon (sole owner since Apr 2025; co-founded with Shlomo Filber 2019) | i24NEWS (since Jun 2025); before: Channel 14, Kan, Likud | SMS/cellular, method undisclosed | See headline section. Also serviced Likud as a client while polling publicly. |
| Filber / Next Data | Shlomo Filber (adviser); owned via Channel 14's owners' rep | Channel 14 | SMS-style, undisclosed | Registered Oct 2025 after Direct Polls left Ch14. The cycle's extreme outlier (coalition 62–66). |
| Tatika | Yossi Tatika (founded Mar 2025) | Zman Yisrael | Adgenda panel (Roei Shindler) | New firm, no election track record. |
| HaMadad consortium | Shmuel Rosner & Noah Slepkov | Channel 13 | Midgam Project + Askaria (haredi) + StatNet (Arab) | Continuation of the late Camil Fuchs's Ch13 stack. Rosner also runs the poll-of-polls that grades everyone. |
| Midgam Project | Dr. Ariel Ayalon (est. ~2007-09) | fieldwork house | own ~40K panel | Panel vendor, not Geva's Midgam — the name collision is a known trap. |
| Smith Consulting | Rafi Smith (family institute since 1972, Hanoch Smith lineage) | Globes, JPost, Galey Israel | phone/mixed | Accuracy leader; ~zero measured lean in all nine cycles. |
| StatNet | Yousef Makladeh | Dayan Center; subcontractor to many | Arab-society specialist | The industry's centralized Arab-sector node. |
| TrendZone | [unresolved] — "research arm of Provo" | Israel Hayom | unclear | Some polls far to the coalition-friendly side. |
| Timor Group | Adi Timor (with Riki Herzberg) | i24NEWS | [unresolved] | Campaign-strategist background; thin public record. |
| Camil Fuchs | Prof. Camil Fuchs (1945–2024) | Haaretz (Dialog era), then Ch10/13 | Midgam Project + StatNet | Died April 2024; his 2026-cycle polls are early-cycle legacy rows. Only pollster to nail April 2019. |

## Panel infrastructure

| Panel | Owner | Used by |
|---|---|---|
| iPanel (~100K, est. 2006) | co-founded by Mano Geva (Midgam) + Israel Olenik | Midgam/Ch12; sold widely |
| Panel4All (est. 2006) | Panels Ltd (Lazar's parent institute) | Lazar/Panels Politics; sold widely |
| Midgam Project panel (~40K) | Dr. Ariel Ayalon | Fuchs/Ch13 stack, HaMadad, academia |
| Adgenda | Roei Shindler | Tatika |
| none (SMS outreach) | — | Direct Polls, Next Data (method undisclosed) |

## Historical lineage (backtest-era firms)

- **Dahaf** — Mina Tzemach's institute (Yedioth Ahronoth, dominant TV exit
  polls); closed 2013, Tzemach moved to Midgam. The Dahaf→Midgam succession.
- **Dialog** — Haaretz's phone-era house polls under Camil Fuchs's academic
  supervision; faded after Fuchs moved to Ch13. No Lazar connection found —
  Fuchs's fieldwork partners were Dialog, then Midgam Project + StatNet.
- **Teleseker** → TNS Teleseker → **Kantar Israel**.
- **New Wave Research** — Reuven Harari; Israel Hayom's pollster 2013–2015.
- **Geocartography** — Prof. Avi Degani; historically Army Radio's pollster.
- **Shvakim Panorama** — Yossi Vedana; long-time Israel Radio pollster.

## Correlation groups for the simulation layer

`data/pollster_meta.csv` assigns each 2026-cycle pollster a
`correlation_group`; the simulation layer should draw house-effect and mode
errors with within-group correlation rather than treating firms as
independent:

- `sms_likud`: Direct Polls, Filber — one origin, one methodology, one
  political ecosystem.
- `ipanel`: Midgam.
- `panel4all`: Lazar, Panels Politics.
- `midgam_project`: Midgam Project, Midgam Project & StatNet (+ HaMadad
  consortium polls, however credited).
- `adgenda`: Tatika.
- `phone_mixed`: Smith Consulting, Maagar Mochot, Kantar, Camil Fuchs
  (legacy), Timor Group, TrendZone — residual group; refine as facts emerge.

All opt-in-panel groups additionally share mode risk (offline haredi/Arab
under-coverage; panel-infiltration exposure) that the correlated-error model
should encode as a common factor across `ipanel`, `panel4all`,
`midgam_project`, and `adgenda`.

## Key sources

Paamon pollster ratings (Knesset 22–24, 25) · The Seventh Eye on Direct
Polls' Kan hiring, the 2024 municipal exit polls, and the 142% broadcast ·
TheMarker on the Filber–Sharon split and i24 move · Haaretz exposés on Next
Data's ownership (May 2026), CEC filing failures (Aug 2026), and panel
infiltration (Aug 2026) · Hebrew Wikipedia entries for Mano Geva, Shlomo
Filber, Mina Tzemach, Camil Fuchs, Hanoch Smith · Israel Policy Forum
pollster guide (Aug 2026) · The Media Line on the polling system · firm
sites: panelspolitics.co.il, panelsltd.com, midgam.com, maagar-mochot.co.il,
geokg.com, s-panorama.com, ilpoll.com.
