# MODEL BRIEF for content writers (Change Bloc Victory Guide)

Context: Israel's 26th Knesset election is Tue 27 Oct 2026 (brief generated Fri 23 Oct 2026, D-4). The change bloc: Yashar (Eisenkot), Together (Bennett 2026 + Yesh Atid; ballot letters רק), The Democrats (Golan), Yisrael Beytenu (Liberman). Netanyahu bloc (NB) = Likud, Shas, UTJ, Otzma, RZP-Zehut, Amcha, Noam, Haredi Public. Arab lists = Ra'am, Joint List (Balad + Hadash-Ta'al). Reservists-Economic (Hendel/Zelekha) is a right-of-centre, reservist-branded list near the threshold. Blue and White (Gantz) withdrew on 19 Oct without an endorsement; the forecast routes its vote.
Forecast (polls to 2026-10-21): Likud 25, Yashar 22, Together 13, Shas 9, Joint List 9, Democrats 9, UTJ 8, YB 8, Ra'am 6 (pass 0.84), Otzma 6 (pass 0.82), RZP-Zehut 5 (pass 0.64), Reservists 0 (pass 0.23), Amcha 0 (pass 0.22). P(NB>=61) 8.9%; P(change bloc alone >=61) 5.5%; with Ra'am 26.7%; neither 64.4%.
Government outcomes (formation model): Netanyahu rightist coalition 7.4%; Netanyahu + unaligned / Amcha 0.3%; Change coalition (without Ra'am) 5.5%; Change coalition with unaligned / Amcha 3.0%; Change coalition with a haredi party 6.7%; Centre minority backed by the Joint List 3.8%; Unity government (Likud without Netanyahu) 17.2%; Repeat election 27.6%; Change coalition with Ra'am 8.8%; Netanyahu + a change-bloc defector 19.8%. Change-led government (sum of change outcomes) 27.8%. PM: none (repeat election) 27.6%; Netanyahu 27.4%; Eisenkot 26.5%; Likud successor (unity) 8.6%; Bennett 7.3%; Liberman 1.5%; another leader 1.1%.
Key dates: final published polls Fri 23 Oct (poll-publication ban from the end of Friday: Sat 24 - Tue 27 Oct); election day Tue 27 Oct, polls 07:00-22:00; double-envelope votes counted centrally afterwards.

Every model number in the site's prose is a live token filled from the pipeline (src/targeting_facts.py); check any number with `cd src && ../.venv/bin/python targeting_facts.py get <key>`.

## Exchange rate per 10,000 extra votes (pp of probability; seats for change_seats)

list,share_mean,p_pass,change_govt,block_nb,change_seats
The Democrats,0.07235,0.994,0.72,0.36,0.169
Likud,0.19094,1.0,-0.6,-0.39,-0.11
Otzma Yehudit,0.04934,0.82,-0.8,-0.41,-0.135
Ra'am,0.04584,0.845,-0.23,0.53,-0.156
Religious Zionist Party,0.03866,0.644,-0.98,-0.6,-0.168
Shas,0.06748,0.996,-0.49,-0.38,-0.11
United Torah Judaism,0.06468,0.999,-0.45,-0.38,-0.109
Yashar,0.16608,1.0,0.72,0.36,0.166
Yisrael Beytenu,0.06435,0.984,0.61,0.34,0.175
Reservists – Economic Party,0.01759,0.225,-0.11,0.16,-0.054
Bennett 2026 + Yesh Atid,0.09866,0.999,0.69,0.29,0.163
Balad + Hadash-Ta'al,0.07059,0.995,-0.42,0.33,-0.108
Amcha Yisrael,0.01764,0.22,-0.23,-0.27,-0.052
Israel First,0.00548,0.001,0.03,-0.01,0.005
Noam,0.00654,0.003,0.02,-0.06,0.004
The Haredi Public,0.007,0.003,0.03,-0.03,0.005
Ahi – Back to the Roots,0.00567,0.002,0.03,-0.01,0.005
Code Black – Shield of the Torah World,0.00569,0.002,0.02,0.0,0.004
Tzomet Beit Yisrael,0.00543,0.001,0.02,0.0,0.006

One net vote for an average change list = 1.67e-05 expected change-bloc seats (about 60,000 votes per expected seat).

## Saturation potential (net votes; every positive station area at 35%, plus list programmes at 30% identified)

- change_govt: {'potential': 3393, 'area_pot': 2631, 'list_pot': 762, 'gotv_pot': 2543, 'pers_pot': 576, 'resc_pot': 274, 'area_contacts': 1180214, 'list_contacts': 125355}
- block_nb: {'potential': 10242, 'area_pot': 9709, 'list_pot': 534, 'gotv_pot': 9667, 'pers_pot': 575, 'resc_pot': 0, 'area_contacts': 1352615, 'list_contacts': 132740}
- change_seats: {'potential': 3857, 'area_pot': 3071, 'list_pot': 785, 'gotv_pot': 2814, 'pers_pot': 602, 'resc_pot': 441, 'area_contacts': 1357014, 'list_contacts': 91825}

## Realistic budgets (Arab localities, Arab-led stations, access-excluded and low-confidence Druze towns excluded; ranges = min-max across sensitivity scenarios)

- change_govt, 150,000 contacts, 0% identified: 781 net votes (range 431-1,560; 0.054 pp); Druze towns would add 175; 13 localities; top: Tel Aviv - Yafo 416, Haifa 78, Rishon LeZiyyon 56, Ramat Gan 49, Herzliyya 32, Giv'atayim 31, Jerusalem 29, Bat Yam 27
- change_govt, 150,000 contacts, 30% identified: 1,107 net votes (range 741-2,216; 0.077 pp); Druze towns would add 152; 987 localities; top: Tel Aviv - Yafo 451, Haifa 96, Ramat Gan 58, Herzliyya 40, Netanya 37, Jerusalem 32, Be'er Sheva 26, Giv'atayim 22
- change_govt, 400,000 contacts, 0% identified: 1,403 net votes (range 796-3,292; 0.097 pp); Druze towns would add 212; 48 localities; top: Tel Aviv - Yafo 505, Haifa 123, Ramat Gan 105, Herzliyya 71, Rishon LeZiyyon 56, Jerusalem 44, Giv'atayim 41, Rehovot 39
- change_govt, 400,000 contacts, 30% identified: 1,847 net votes (range 1,167-4,402; 0.128 pp); Druze towns would add 205; 1006 localities; top: Tel Aviv - Yafo 544, Haifa 142, Ramat Gan 92, Herzliyya 78, Jerusalem 76, Rishon LeZiyyon 74, Netanya 62, Bat Yam 45
- block_nb, 150,000 contacts, 0% identified: 855 net votes (range 468-1,619; 0.029 pp); Druze towns would add 278; 12 localities; top: Tel Aviv - Yafo 503, Haifa 157, Ramat Gan 46, Herzliyya 30, Jerusalem 25, Rehovot 22, Giv'atayim 18, Bat Yam 14
- block_nb, 150,000 contacts, 30% identified: 999 net votes (range 578-2,242; 0.034 pp); Druze towns would add 258; 155 localities; top: Tel Aviv - Yafo 461, Haifa 110, Ramat Gan 46, Netanya 42, Herzliyya 31, Bat Yam 28, Be'er Sheva 27, Jerusalem 27
- block_nb, 400,000 contacts, 0% identified: 1,449 net votes (range 825-3,302; 0.049 pp); Druze towns would add 323; 48 localities; top: Tel Aviv - Yafo 551, Haifa 188, Ramat Gan 98, Herzliyya 65, Giv'atayim 48, Rishon LeZiyyon 47, Jerusalem 39, Rehovot 36
- block_nb, 400,000 contacts, 30% identified: 1,739 net votes (range 1,004-4,491; 0.059 pp); Druze towns would add 314; 279 localities; top: Tel Aviv - Yafo 565, Haifa 190, Jerusalem 83, Ramat Gan 77, Netanya 61, Rishon LeZiyyon 55, Herzliyya 52, Bat Yam 47
- change_seats, 150,000 contacts, 0% identified: 832 net votes (range 456-1,560; 0.014 seats); Druze towns would add 162; 14 localities; top: Tel Aviv - Yafo 430, Haifa 91, Rishon LeZiyyon 68, Ramat Gan 53, Bat Yam 48, Herzliyya 34, Rehovot 29, Giv'atayim 18
- change_seats, 150,000 contacts, 30% identified: 1,265 net votes (range 889-2,252; 0.021 seats); Druze towns would add 155; 983 localities; top: Tel Aviv - Yafo 479, Haifa 112, Ramat Gan 68, Bat Yam 58, Herzliyya 45, Netanya 28, Jerusalem 26, Giv'atayim 25
- change_seats, 400,000 contacts, 0% identified: 1,546 net votes (range 868-3,437; 0.026 seats); Druze towns would add 209; 41 localities; top: Tel Aviv - Yafo 516, Haifa 145, Ramat Gan 113, Herzliyya 75, Bat Yam 71, Rishon LeZiyyon 68, Giv'atayim 42, Jerusalem 40
- change_seats, 400,000 contacts, 30% identified: 2,052 net votes (range 1,340-4,394; 0.034 seats); Druze towns would add 209; 999 localities; top: Tel Aviv - Yafo 567, Haifa 166, Ramat Gan 103, Rishon LeZiyyon 92, Jerusalem 83, Bat Yam 82, Netanya 70, Herzliyya 69

## Tiers (change_govt)

{'Low yield': 746, 'Netanyahu-bloc stronghold': 262, 'Arab-list turf (partner-led)': 127, 'Secondary target': 46, 'Turnout engine': 25, 'Not targeted (access)': 5, 'Supporter-list ground': 3, 'Persuasion battleground': 1}
- Turnout engine: Tel Aviv - Yafo (587), Haifa (181), Rishon LeZiyyon (133), Ramat Gan (129), Jerusalem (108), Herzliyya (86), Holon (68), Bat Yam (65), Rehovot (63), Kefar Sava (58), Giv'atayim (52), Daliyat Al-Karmel (51), Ra'annana (49), Ashdod (48), Beit Jann (44), Modi'in-Makkabbim-Re'ut (39), Ramat HaSharon (35), Hod HaSharon (34), Yirka (34), Kisra-Sumei (31), Yanuh-Jat (30), Isifya (26), Julis (19), Mughar (15), Sajur (7)
- Supporter-list ground: Netanya (83), Be'er Sheva (45), Bet Shemesh (8)
- Persuasion battleground: Petah Tiqwa (72)

## Segments

segment,label,localities,eligible,turnout_2022,p26_change,p26_nb,p26_arab,persuadable_voters,rescue_voters,change_govt__potential,change_govt__share,block_nb__potential
arab_bedouin_south,Arab – Negev Bedouin,38,144860,0.51,0.049,0.01,0.94,0.0,95.247,14.825,0.004,1662.496
arab_christian,Arab – Christian localities,6,27005,0.59,0.184,0.027,0.783,6.645,79.595,8.89,0.003,110.867
arab_north_triangle,Arab – Galilee & Triangle,84,670493,0.541,0.054,0.009,0.935,0.0,510.851,73.504,0.022,5290.037
druze,Druze & Circassian,18,96043,0.485,0.648,0.129,0.192,573.768,1162.851,292.41,0.086,416.653
haredi,Haredi,28,378343,0.747,0.076,0.912,0.009,916.977,589.085,20.88,0.006,19.19
jerusalem,Jerusalem,1,432125,0.616,0.236,0.722,0.03,6473.67,2285.139,107.918,0.032,98.96
kibbutz,Kibbutz,256,143566,0.699,0.81,0.133,0.019,786.631,3215.472,163.612,0.048,156.768
liberal_urban,Secular-liberal urban,45,1355203,0.666,0.655,0.282,0.027,13443.138,27526.307,1279.979,0.377,1195.56
mixed_city,Mixed Jewish–Arab city,6,219177,0.597,0.254,0.486,0.246,2987.888,1082.584,45.076,0.013,59.051
mixed_urban,Middle Israel (mixed urban),14,982973,0.659,0.484,0.451,0.036,18098.652,14677.26,521.449,0.154,482.476
moshav_rural,Moshav & rural community,458,251812,0.733,0.593,0.354,0.016,3512.595,5340.628,180.909,0.053,160.435
periphery_likud,Likud-leaning cities & development towns,33,1247718,0.626,0.371,0.592,0.014,24969.021,12458.265,424.925,0.125,364.691
religious_zionist,Religious-Zionist (inside Green Line),103,77462,0.771,0.226,0.748,0.01,1724.438,570.9,13.684,0.004,12.543
russian_speaking,Russian-speaking towns,10,580965,0.594,0.401,0.562,0.015,10027.805,5257.719,214.345,0.063,186.188
settlement_rz,West Bank – national-religious,83,102322,0.751,0.144,0.833,0.01,1448.904,345.096,8.678,0.003,7.002
settlement_secular,West Bank – secular & mixed,32,78737,0.698,0.392,0.569,0.013,1864.702,1004.016,22.074,0.007,19.27

## Top 30 localities by change_govt potential (non-Arab)

name_en,segment,eligible,turnout_resident,p26_change,p26_nb,lead_change_list,change_govt__potential,change_govt__area_pot,change_govt__list_pot,change_govt__eff1k,change_govt__tier,low_confidence
Tel Aviv - Yafo,liberal_urban,447576,0.763,0.673,0.241,Yashar,587.36,546.662,40.698,4.723,Turnout engine,
Haifa,mixed_urban,253292,0.738,0.545,0.31,Yashar,181.426,163.037,18.389,2.852,Turnout engine,
Rishon LeZiyyon,mixed_urban,211845,0.806,0.517,0.437,Yashar,132.752,114.34,18.412,1.99,Turnout engine,
Ramat Gan,liberal_urban,139055,0.798,0.624,0.32,Yashar,129.136,118.65,10.487,2.823,Turnout engine,
Jerusalem,jerusalem,432125,0.764,0.236,0.722,Yashar,107.918,55.032,52.886,2.471,Turnout engine,
Herzliyya,liberal_urban,88932,0.802,0.661,0.286,Yashar,86.115,78.794,7.321,2.908,Turnout engine,
Netanya,periphery_likud,195220,0.712,0.395,0.568,Yashar,83.088,40.528,42.56,2.278,Supporter-list ground,
Petah Tiqwa,mixed_urban,197815,0.824,0.435,0.525,Yashar,71.772,52.196,19.576,1.33,Persuasion battleground,
Holon,periphery_likud,159831,0.768,0.444,0.514,Yashar,68.158,47.331,20.826,1.592,Turnout engine,
Bat Yam,russian_speaking,124742,0.663,0.44,0.519,Yashar,65.029,46.151,18.879,2.196,Turnout engine,
Rehovot,mixed_urban,111435,0.836,0.486,0.471,Yashar,63.265,50.249,13.016,2.24,Turnout engine,
Kefar Sava,liberal_urban,81737,0.856,0.647,0.3,Yashar,57.801,50.264,7.537,2.227,Turnout engine,
Giv'atayim,liberal_urban,49341,0.839,0.739,0.202,Yashar,52.064,47.912,4.152,3.124,Turnout engine,
Daliyat Al-Karmel,druze,13249,0.62,0.769,0.122,Yashar,50.776,49.838,0.938,10.464,Turnout engine,Druze vote depends on 2026 list candidates
Ra'annana,liberal_urban,69652,0.82,0.597,0.354,Yashar,48.848,43.642,5.206,2.094,Turnout engine,
Ashdod,russian_speaking,181784,0.832,0.349,0.621,Yashar,48.468,27.286,21.181,1.439,Turnout engine,
Be'er Sheva,periphery_likud,164728,0.753,0.354,0.603,Yashar,44.82,8.952,35.867,1.759,Supporter-list ground,
Beit Jann,druze,9177,0.599,0.814,0.111,Democrats,43.83,43.463,0.367,13.097,Turnout engine,Druze vote depends on 2026 list candidates
Modi'in-Makkabbim-Re'ut,liberal_urban,69212,0.91,0.603,0.347,Yashar,38.919,33.207,5.712,1.665,Turnout engine,
Ramat HaSharon,liberal_urban,38282,0.867,0.728,0.219,Yashar,34.683,31.208,3.475,2.68,Turnout engine,
Hod HaSharon,liberal_urban,48723,0.906,0.701,0.243,Yashar,34.053,29.416,4.637,2.066,Turnout engine,
Yirka,druze,11387,0.579,0.637,0.212,Yashar,33.694,33.187,0.507,8.108,Turnout engine,Druze vote depends on 2026 list candidates
Kisra-Sumei,druze,6066,0.383,0.724,0.139,Yashar,31.182,30.957,0.225,14.1,Turnout engine,Druze vote depends on 2026 list candidates
Ashqelon,russian_speaking,119846,0.803,0.369,0.597,Yashar,31.01,14.768,16.242,1.279,Secondary target,
Hadera,periphery_likud,80141,0.759,0.426,0.531,Yashar,30.938,17.063,13.875,1.793,Secondary target,
Yanuh-Jat,druze,4843,0.459,0.734,0.135,Yisrael Beytenu,29.908,29.721,0.187,16.934,Turnout engine,Druze vote depends on 2026 list candidates
Elat,periphery_likud,51974,0.626,0.39,0.561,Yashar,27.175,4.862,22.313,4.171,Secondary target,
Qiryat Motzkin,periphery_likud,40960,0.765,0.536,0.417,Yashar,25.673,22.708,2.966,1.867,Secondary target,
Isifya,druze,9560,0.586,0.603,0.089,Yashar,25.588,25.19,0.398,8.304,Turnout engine,Druze vote depends on 2026 list candidates
Karmi'el,russian_speaking,42065,0.762,0.533,0.403,Yashar,25.254,23.347,1.907,1.848,Secondary target,

## Robustness (sensitivity; Spearman vs base / top-25 overlap)

- change_govt: Turnout effect about half as large (0.8 instead of 1.5 pts at the reference point): 0.989 / 24; Turnout effect two-thirds larger (2.5 instead of 1.5 pts): 0.995 / 24; No turnout hump: ×0.8 at every turnout level: 0.945 / 21; No turnout hump, same average lift in door turf (×0.32 everywhere): 0.943 / 21; Steeper hump (effect concentrated at 30-50% turnout): 0.991 / 23; Persuasion ×4 (upper end of field estimates): 0.954 / 22; No persuasion effect: 0.993 / 23; No turnout side-effect of persuasion calls: 0.996 / 25; Rescue ×3: 0.998 / 25; Rescue ×0.3: 0.999 / 24; No supporter lists (door canvassing only): 0.837 / 22; Residents abroad ×1.6: 0.997 / 24; Cross-pressured share 10% (national pool about 1%): 0.996 / 23; Cross-pressured share 40% (national pool about 4%): 0.991 / 24; Druze towns: 20 points moved from change to Netanyahu-bloc lists: 0.989 / 21; Pure flow-matrix projection (no uniform-swing blend): 0.987 / 25; Turnout-tilted marginal voters (model rejected out of sample): 0.989 / 22
- block_nb: Turnout effect about half as large (0.8 instead of 1.5 pts at the reference point): 0.996 / 24; Turnout effect two-thirds larger (2.5 instead of 1.5 pts): 0.998 / 24; No turnout hump: ×0.8 at every turnout level: 0.953 / 11; No turnout hump, same average lift in door turf (×0.32 everywhere): 0.948 / 11; Steeper hump (effect concentrated at 30-50% turnout): 0.995 / 22; Persuasion ×4 (upper end of field estimates): 0.976 / 21; No persuasion effect: 0.995 / 23; No turnout side-effect of persuasion calls: 0.998 / 24; Rescue ×3: 1.0 / 25; Rescue ×0.3: 1.0 / 25; No supporter lists (door canvassing only): 0.954 / 24; Residents abroad ×1.6: 0.998 / 23; Cross-pressured share 10% (national pool about 1%): 0.997 / 24; Cross-pressured share 40% (national pool about 4%): 0.997 / 24; Druze towns: 20 points moved from change to Netanyahu-bloc lists: 0.981 / 25; Pure flow-matrix projection (no uniform-swing blend): 0.999 / 24; Turnout-tilted marginal voters (model rejected out of sample): 0.989 / 21

## Strategic levers (exact scenario engine; effect if the lever happens)

Base: P(change-led govt) 28.2%, P(NB<61) 90.9%, expected change seats 51.8.
- [agreements] Reservists-Economic withdraws (60% to change lists): 84,833 votes. Change-led govt +2.64 pts; deny-61 -0.79 pts; change seats +0.98. (All Reservists votes move: 60% to change lists in proportion to their size, 40% to Likud (the atlas's rescue assumption).)
- [agreements] Reservists-Economic withdraws (mostly to the right): 84,833 votes. Change-led govt -0.61 pts; deny-61 -2.56 pts; change seats +0.36. (All Reservists votes move: 35% to change lists, 65% to Likud and Otzma. A pessimistic split for a right-of-centre list.)
- [agreements] Amcha withdraws (the opponent consolidates): 85,063 votes. Change-led govt -0.98 pts; deny-61 +0.50 pts; change seats +0.01. (All Amcha votes move: 80% to Likud and Otzma, 20% to change lists. Shows what consolidation on the other side would cost.)
- [persuasion] 0.5 point of the vote moves from Likud to change lists: 24,115 votes. Change-led govt +3.41 pts; deny-61 +1.49 pts; change seats +0.67. (0.5% of the national vote leaves Likud for the four change lists, in proportion to their size.)
- [persuasion] 1 point of the vote moves from Likud to change lists: 48,230 votes. Change-led govt +6.98 pts; deny-61 +3.05 pts; change seats +1.33. (1% of the national vote leaves Likud for the four change lists, in proportion to their size.)
- [persuasion] 2 point of the vote moves from Likud to change lists: 96,461 votes. Change-led govt +14.02 pts; deny-61 +4.87 pts; change seats +2.66. (2% of the national vote leaves Likud for the four change lists, in proportion to their size.)
- [persuasion] 0.5 point moves from Shas/UTJ to change lists: 24,115 votes. Change-led govt +2.95 pts; deny-61 +1.44 pts; change seats +0.67. (0.5% of the vote leaves Shas and UTJ for the change lists (traditional voters on the draft).)
- [turnout] 25,000 extra change-list votes (turnout): 25,000 votes. Change-led govt +1.93 pts; deny-61 +0.80 pts; change seats +0.43. (25,000 new votes for the four change lists, in proportion to their size.)
- [turnout] 50,000 extra change-list votes (turnout): 50,000 votes. Change-led govt +3.66 pts; deny-61 +1.58 pts; change seats +0.84. (50,000 new votes for the four change lists, in proportion to their size.)
- [turnout] Haredi turnout falls 10%: 63,740 votes. Change-led govt +3.00 pts; deny-61 +2.11 pts; change seats +0.71. (Shas and UTJ lose 10% of their votes to abstention (UTJ's own reported fear after the draft-law failure).)
- [turnout] 25,000 extra Netanyahu-bloc votes (counter-mobilisation): 25,000 votes. Change-led govt -1.40 pts; deny-61 -1.19 pts; change seats -0.28. (25,000 new votes for the Netanyahu-bloc lists, in proportion to their size: the cost of triggering the other side's turnout.)
- [turnout] Arab turnout +5 points (~46,000 votes): 46,000 votes. Change-led govt -1.59 pts; deny-61 +1.75 pts; change seats -0.57. (Votes added to (or removed from) the Joint List and Ra'am in proportion to their size.)
- [turnout] Arab turnout -5 points (~46,000 votes): 46,000 votes. Change-led govt +1.82 pts; deny-61 -2.39 pts; change seats +0.61. (Votes added to (or removed from) the Joint List and Ra'am in proportion to their size.)
- [allies] 0.5 point moves from Yashar to the Democrats: 24,115 votes. Change-led govt +0.03 pts; deny-61 -0.01 pts; change seats +0.01. (Within-bloc move: 0.5% of the vote shifts from Yashar to the Democrats.)
- [allies] 0.5 point moves from the Joint List to Ra'am: 24,115 votes. Change-led govt +0.80 pts; deny-61 +0.45 pts; change seats -0.09. (Within the Arab lists: 0.5% of the vote shifts from the Joint List to Ra'am (threshold insurance for Ra'am).)