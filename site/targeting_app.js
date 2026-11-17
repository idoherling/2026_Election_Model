(function () {
"use strict";
const D = JSON.parse(document.getElementById("atlas-data").textContent);
const S = D.summary, L = D.loc, H = D.hist, C = D.content || {};
const N = L.id.length;
const IDX = new Map(L.id.map((id, i) => [id, i]));
const ALL = d3.range(N);
const TIERS = D.tiers;
const hasOwn = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

/* ------------------------------------------------------------ state */
const store = {
  get(k, d) { try { const v = localStorage.getItem("atlas." + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("atlas." + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
};
const OBJS = ["change_govt", "block_nb", "change_seats"];
let OBJ = store.get("obj", "change_govt");
if (!OBJS.includes(OBJ)) OBJ = "change_govt";
const OBJ_SHORT = { change_govt: "a change-led government", block_nb: "denying Netanyahu 61", change_seats: "change-bloc seats" };
const OBJ_GOAL = { change_govt: "P(change-led government)", block_nb: "P(Netanyahu bloc below 61)", change_seats: "expected change-bloc seats" };

/* ------------------------------------------------------------ format */
const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const fmtInt = x => x == null || !isFinite(x) ? "—" : (Math.round(x) < 0 ? "−" : "") + nf0.format(Math.abs(Math.round(x)));
const fmtNV = x => {
  if (x == null || !isFinite(x)) return "—";
  const small = Math.abs(x) < 10, r = small ? Math.round(x * 10) / 10 : Math.round(x);
  if (r === 0) return small ? "0.0" : "0";
  return (r < 0 ? "−" : "") + (small ? nf1 : nf0).format(Math.abs(r));
};
// headline model totals: two significant figures, so they do not read as exact
const fmtSig = x => { if (x == null || !isFinite(x)) return "—"; if (Math.abs(x) < 100) return fmtInt(x); const m = Math.pow(10, Math.floor(Math.log10(Math.abs(x))) - 1); return fmtInt(Math.round(x / m) * m); };
const fmtK = x => x >= 1e6 ? (x / 1e6).toFixed(x % 1e6 ? 1 : 0) + " million" : fmtInt(x);
const pct = (x, d = 0) => x == null || !isFinite(x) ? "—" : (x * 100).toFixed(d) + "%";
const pp = (x, d = 2) => x == null || !isFinite(x) ? "—" : (x >= 0 ? "+" : "−") + Math.abs(x * 100).toFixed(d) + " pts";
const sgn = (x, d = 2) => x == null || !isFinite(x) ? "—" : (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(d);
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ov = (part, i, obj) => { const a = L[(obj || OBJ) + "." + part]; return a ? a[i] : null; };
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isArab = i => L.seg[i].startsWith("arab");
const isTarget = i => !isArab(i) && !L.excl[i];
const RM = (() => { try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } })();
const tierOf = (i, obj) => TIERS[L[(obj || OBJ) + ".tier"][i]];
const norm = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/['’‘`"׳״\-–\s.(),]/g, "");

const SEG_LABEL = {};
D.segments.forEach(s => SEG_LABEL[s.segment] = s.label);
const SEG_ORDER = D.segments.slice().sort((a, b) => b.eligible - a.eligible).map(s => s.segment);
const segRow = seg => D.segments.find(s => s.segment === seg) || {};
const SEG_SHORT = { arab_bedouin_south: "Arab – Negev Bedouin", arab_christian: "Arab – Christian", arab_north_triangle: "Arab – Galilee & Triangle", druze: "Druze & Circassian", haredi: "Haredi", jerusalem: "Jerusalem", kibbutz: "Kibbutz", liberal_urban: "Secular-liberal urban", mixed_city: "Mixed Jewish–Arab city", mixed_urban: "Middle Israel", moshav_rural: "Moshav & rural", periphery_likud: "Likud-leaning towns", religious_zionist: "Religious-Zionist towns", russian_speaking: "Russian-speaking towns", settlement_rz: "W. Bank national-religious", settlement_secular: "W. Bank secular & mixed" };

const TIER_STYLE = {
  "Turnout engine": { fill: "--t-engine" },
  "Supporter-list ground": { ring: "--t-engine" },
  "Persuasion battleground": { fill: "--t-pers" },
  "Secondary target": { fill: "--t-second" },
  "Arab-list turf (partner-led)": { fill: "--t-block" },
  "Netanyahu-bloc stronghold": { ring: "--t-strong" },
  "Low yield": { fill: "--t-low" },
  "Not targeted (access)": { ring: "--t-none", dash: true },
};
const TIER_DESC = {
  "Turnout engine": "Large or efficient targets where door conversations pay on selected polling-station areas. Canvass the positive stations only.",
  "Supporter-list ground": "Netanyahu-majority towns with many change-bloc voters. Door canvassing across the town nets votes for the other side; door teams go only to the few positive stations, and identified supporters are reached by call, text and friend-to-friend ask.",
  "Persuasion battleground": "Persuasion of soft Netanyahu-bloc voters is the largest lever. Persuade at the door on positive stations and call identified soft voters elsewhere.",
  "Secondary target": "Positive but modest returns. Use phones, texts and relational asks; send door teams only to the best stations.",
  "Arab-list turf (partner-led)": "Arab localities. Turnout here helps deny Netanyahu 61 but, in the formation model, not a change-led government. Whether to support Arab turnout is a leadership decision. Any support should be independent, transparent and cleared by election counsel. There is no change-bloc-run GOTV.",
  "Netanyahu-bloc stronghold": "The Netanyahu bloc takes 70% or more, and a turnout contact is net negative almost everywhere. No door work; calls to identified change-bloc supporters and to identified soft Netanyahu-bloc voters only.",
  "Low yield": "Little to gain per contact from door teams. Use relational asks through members' own networks and texts to identified supporters; no door teams unless the realistic plans reach its positive stations.",
  "Not targeted (access)": "Access-restricted, or most residents are not Israeli citizens and voting in Knesset elections carries a social cost (Golan Druze villages, Ghajar). Not targeted.",
};
function swatch(t) {
  const st = TIER_STYLE[t] || {};
  return st.fill ? `<span class="sw" style="background:var(${st.fill})"></span>` : `<span class="sw" style="background:transparent;border:2px ${st.dash ? "dashed" : "solid"} var(${st.ring})"></span>`;
}
const tierChip = t => `<span class="chip tierchip">${swatch(t)}${esc(t)}</span>`;
const segChip = s => `<span class="chip segchip">${esc(SEG_LABEL[s] || s)}</span>`;
const LEAD_VAR = { Yashar: "--l-yashar", Together: "--l-together", Democrats: "--l-dem", "Yisrael Beytenu": "--l-yb" };
const leadOK = i => L.pch[i] >= 0.15 && !isArab(i);
const leadChip = (name) => name ? `<span class="chip segchip" style="gap:5px"><span class="sw" style="background:var(${LEAD_VAR[name] || "--muted"});border-radius:50%"></span>${esc(name)}</span>` : "—";
function flags(i) {
  let h = "";
  if (L.excl[i]) h += `<span class="flag x" title="${esc(L.excl[i])}">not targeted</span>`;
  if (L.disp[i]) h += `<span class="flag" title="${esc(L.disp[i])}: residents may not be at home; capacity halved">displaced</span>`;
  if (L.lowc[i]) h += `<span class="flag" title="${esc(L.lowc[i])}">low confidence</span>`;
  return h;
}
const locName = i => `<a href="#loc-${L.id[i]}"><b>${esc(L.en[i])}</b></a> <span class="he" dir="rtl" lang="he">${esc(L.he[i])}</span>${flags(i)}`;

/* ------------------------------------------------------------ units */
const seatsOf = ve => ve * S.mv_ref.change_seats;
function effOf(ve, obj) { return ve * S.mv_ref[obj || OBJ]; }
function dpText(ve, obj) {
  const o = obj || OBJ, d = effOf(ve, o);
  if (o === "change_seats") { if (Math.abs(d) < 0.0005) return (d >= 0 ? "+" : "−") + "<0.001 expected change-bloc seats"; return sgn(d, Math.abs(d) < 0.01 ? 3 : 2) + " expected change-bloc seats"; }
  const v = d * 100;
  if (Math.abs(v) < 0.005) return (v >= 0 ? "+" : "−") + "<0.01 pts in " + OBJ_GOAL[o];
  return pp(d, Math.abs(v) < 0.1 ? 3 : 2) + " in " + OBJ_GOAL[o];
}
// net votes under "deny 61" include Arab-list-equivalent value, so they do
// not convert into change-bloc seats
const seatsOK = obj => (obj || OBJ) !== "block_nb";
const effShort = (ve, obj) => (obj || OBJ) === "change_seats" ? sgn(effOf(ve, obj), 3) + " seats" : pp(effOf(ve, obj), Math.abs(effOf(ve, obj) * 100) < 0.1 ? 3 : 2);

/* ------------------------------------------------------------ dates */
function isoToday() { try { return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()); } catch (e) { return new Date().toISOString().slice(0, 10); } }
const daysTo = iso => Math.round((Date.parse(iso + "T00:00:00Z") - Date.parse(isoToday() + "T00:00:00Z")) / 86400000);
const fmtDate = s => { const d = new Date(s + "T12:00:00Z"); return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }); };
const fmtDay = s => { const d = new Date(s + "T12:00:00Z"); return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }); };
const DAYS = daysTo(S.dates.election);
document.getElementById("dl-asof").textContent = fmtDate(S.asof);
document.getElementById("dl-days").textContent = DAYS > 0 ? DAYS : 0;
if (DAYS <= 0) document.getElementById("dl-days").parentElement.textContent = DAYS === 0 ? "Election day" : "Election held 27 Oct";
document.getElementById("ft-built").textContent = fmtDate(S.built);
document.getElementById("ft-asof").textContent = fmtDate(S.asof);
document.querySelectorAll("[data-k]").forEach(el => { const x = S[el.getAttribute("data-k")]; el.textContent = typeof x === "number" ? fmtInt(x) : (x || "—"); });

/* ------------------------------------------------------------ citations */
const SRC = (C.sources || []);
const CITE_MAP = new Map();
SRC.forEach((s, k) => {
  const ids = String(s.id || "").split(",").concat(s.aliases || []).map(x => String(x).trim()).filter(Boolean);
  ids.forEach(id => { if (!CITE_MAP.has(id)) CITE_MAP.set(id, []); const a = CITE_MAP.get(id); if (!a.includes(k)) a.push(k); });
});
function shortCite(s, id) {
  const c = String(s.citation || "");
  const head = c.split("(")[0];
  const pm = c.match(/\(([^)]*)\)/);
  let yr = "";
  if (pm) yr = (pm[1].match(/\b(?:19|20)\d{2}\b/) || [""])[0] || (/n\.d\./.test(pm[1]) ? "n.d." : "");
  if (!yr) yr = (c.match(/\b(?:19|20)\d{2}\b/) || [""])[0];
  let au = head.split(/[.,]/)[0].replace(/^the\s+/i, "").trim();
  if (au.length > 22) au = au.slice(0, 22).replace(/\s+\S*$/, "") + "…";
  const multi = /et al|,\s*[A-Z]\.\s*(,|&| and )/.test(head);
  return au ? `${au}${multi ? " et al." : ""}${yr ? " " + yr : ""}` : id;
}
function cites(arr) {
  if (!arr || !arr.length) return "";
  const seen = new Set(), out = [];
  arr.forEach(id => (CITE_MAP.get(String(id).trim()) || []).forEach(k => {
    if (seen.has(k)) return;
    seen.add(k);
    out.push(`<a class="cite" href="#src-${k}" title="${esc(SRC[k].citation)}">[${esc(shortCite(SRC[k], id))}]</a>`);
  }));
  return out.length ? " " + out.join(" ") : "";
}

/* ------------------------------------------------------------ theme */
const themeBtn = document.getElementById("themebtn");
let theme = store.get("theme", null);
function applyTheme() {
  if (theme) document.documentElement.setAttribute("data-theme", theme); else document.documentElement.removeAttribute("data-theme");
  themeBtn.textContent = theme === "dark" ? "Light theme" : theme === "light" ? "Dark theme" : "Theme";
}
themeBtn.addEventListener("click", () => {
  const dark = theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  theme = dark ? "light" : "dark";
  store.set("theme", theme);
  applyTheme();
  rerender();
});
applyTheme();

/* skip link: the router owns the hash, so focus main directly */
document.getElementById("skiplink").addEventListener("click", e => { e.preventDefault(); document.getElementById("main").focus(); });

/* ------------------------------------------------------------ objective */
const objSel = document.getElementById("objective");
objSel.value = OBJ;
objSel.addEventListener("change", () => { OBJ = objSel.value; store.set("obj", OBJ); rerender(); });

/* ------------------------------------------------------------ tooltip */
const tip = document.getElementById("tip");
function showTip(html, ev) {
  tip.innerHTML = html; tip.style.display = "block";
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > innerWidth - 8) x = ev.clientX - w - pad;
  if (y + h > innerHeight - 8) y = ev.clientY - h - pad;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => { tip.style.display = "none"; };
window.addEventListener("scroll", hideTip, { passive: true });

/* ------------------------------------------------------------ planner core (mirrors src/targeting_planner.py) */
const PROGS = ["area", "sup", "pers", "resc"];
function allocate(obj, budget, opt) {
  const tr = D.planner[obj], ident = opt.ident, mult = opt.mult || 1, ex = opt.exclude, progs = opt.progs || PROGS;
  const minA = opt.minArea == null ? S.min_area : opt.minArea;
  const areaCap = new Map();
  tr.area.forEach(([i, c]) => areaCap.set(i, (areaCap.get(i) || 0) + c));
  const units = [];
  progs.forEach(p => tr[p].forEach(([i, c, v]) => {
    if (ex && ex(i)) return;
    if (p === "area" && (areaCap.get(i) || 0) < minA) return;
    const cc = p === "area" ? c : c * ident;
    if (cc > 0) units.push([v * (p === "area" ? 1 : mult), cc, i, p]);
  }));
  units.sort((a, b) => b[0] - a[0]);
  const dropped = new Set();
  let alloc = new Map(), left = budget;
  for (let it = 0; it < 5; it++) {
    left = budget; alloc = new Map();
    for (const [v, c, i, p] of units) {
      if (left <= 0) break;
      if (p === "area" && dropped.has(i)) continue;
      const take = Math.min(left, c);
      left -= take;
      let a = alloc.get(i);
      if (!a) { a = { area: 0, sup: 0, pers: 0, resc: 0, ve: 0, vp: { area: 0, sup: 0, pers: 0, resc: 0 } }; alloc.set(i, a); }
      a[p] += take; a.ve += take * v / 1000; a.vp[p] += take * v / 1000;
    }
    const small = [...alloc].filter(([i, a]) => a.area > 0 && a.area < minA && !dropped.has(i)).map(([i]) => i);
    if (!small.length) break;
    small.forEach(i => dropped.add(i));
  }
  let ve = 0; const contacts = { area: 0, sup: 0, pers: 0, resc: 0 }, vp = { area: 0, sup: 0, pers: 0, resc: 0 };
  alloc.forEach(a => { ve += a.ve; PROGS.forEach(p => { contacts[p] += a[p]; vp[p] += a.vp[p]; }); });
  const curve = [[0, 0]];
  if (opt.curve) {
    let cum = 0, cumV = 0, step = 0;
    for (const [v, c, i, p] of units) {
      if (p === "area" && dropped.has(i)) continue;
      cum += c; cumV += c * v / 1000;
      if (++step % 8 === 0 || cum < 2e5) curve.push([cum, cumV]);
      if (cum > 3e6) break;
    }
    curve.push([cum, cumV]);
  }
  return { ve, vp, used: budget - Math.max(0, left), left: Math.max(0, left), contacts, alloc, curve, doorLocs: [...alloc.values()].filter(a => a.area > 0).length };
}
const SCEN_CACHE = {};
// summary budgets leave out Arab localities, access-excluded villages and the
// low-confidence Druze towns (held until a candidate check)
const scenEx = i => isArab(i) || !!L.excl[i] || !!L.lowc[i];
function scenarios(o) {
  if (SCEN_CACHE[o]) return SCEN_CACHE[o];
  const r = {};
  [[150000, 0], [150000, S.list_identified], [400000, 0], [400000, S.list_identified]].forEach(([b, id]) => { r[b + "_" + id] = allocate(o, b, { ident: id, exclude: scenEx }); });
  r.druze = [150000, 400000].map(b => allocate(o, b, { ident: S.list_identified, exclude: i => isArab(i) || !!L.excl[i] }).ve - r[b + "_" + S.list_identified].ve);
  return (SCEN_CACHE[o] = r);
}
// range of a summary budget across the sensitivity scenarios
const RANGE_SKIP = new Set(["base", "lists_off", "druze_minus20", "persuasion_no_side"]);
function budgetRange(o, b, id) {
  const B = (D.sensitivity || {}).budgets;
  if (!B) return null;
  const key = `${b}_${id ? id : "0.0"}`;
  const v = Object.entries(B).filter(([n]) => !RANGE_SKIP.has(n)).map(([, d]) => (d[o] || {})[key]).filter(x => x != null);
  return v.length ? [d3.min(v), d3.max(v)] : null;
}

/* ------------------------------------------------------------ chart helpers (sized to their container) */
const widthOf = (el, min = 300) => Math.max(min, Math.floor((el.getBoundingClientRect().width || el.parentElement.getBoundingClientRect().width || 600)));
function hbars(el, rows, opt) {
  const W = widthOf(el), narrow = W < 520;
  const rh = opt.rowH || 22, lw = Math.min(opt.labelW || 210, Math.round(W * (narrow ? 0.42 : 0.36))), top = 6;
  const Hh = top + rows.length * rh + 26;
  const max = opt.max || d3.max(rows, r => d3.sum(r.parts, p => Math.max(0, p.v))) || 1;
  const x = d3.scaleLinear().domain([0, max]).range([0, W - lw - (narrow ? 52 : 74)]);
  const svg = d3.select(el).html("").append("svg").attr("class", "chart").attr("width", W).attr("height", Hh).attr("viewBox", `0 0 ${W} ${Hh}`).attr("role", "img").attr("aria-label", opt.aria || "bar chart");
  const g = svg.append("g").attr("transform", `translate(${lw},${top})`);
  const ticks = x.ticks(narrow ? 3 : 4);
  g.append("g").attr("class", "grid").selectAll("line").data(ticks).join("line").attr("x1", d => x(d)).attr("x2", d => x(d)).attr("y1", 0).attr("y2", rows.length * rh);
  g.append("g").attr("transform", `translate(0,${rows.length * rh + 4})`).selectAll("text").data(ticks).join("text").attr("x", d => x(d)).attr("y", 12).attr("text-anchor", "middle").text(d => opt.tickFmt ? opt.tickFmt(d) : d);
  rows.forEach((r, k) => {
    const y = k * rh;
    const lab = narrow && r.label.length > 26 ? r.label.slice(0, 24) + "…" : r.label;
    svg.append("text").attr("class", "lbl").attr("x", lw - 8).attr("y", top + y + rh / 2 + 4).attr("text-anchor", "end").text(lab).append("title").text(r.label);
    let acc = 0;
    r.parts.forEach(p => {
      const w = Math.max(0, x(acc + Math.max(0, p.v)) - x(acc));
      if (w > 0.2) g.append("rect").attr("x", x(acc)).attr("y", y + 4).attr("width", Math.max(0, w - (w > 3 ? 2 : 0))).attr("height", rh - 8)
        .attr("fill", p.color).on("mousemove", ev => showTip(`<b>${esc(r.label)}</b><div class="r"><span>${esc(p.name)}</span><span>${opt.valFmt ? opt.valFmt(p.v) : p.v}</span></div>`, ev)).on("mouseleave", hideTip);
      acc += Math.max(0, p.v);
    });
    g.append("text").attr("x", x(acc) + 6).attr("y", y + rh / 2 + 4).attr("class", "lbl").text(opt.totFmt ? opt.totFmt(r.total != null ? r.total : acc) : "");
  });
}
function lineChart(el, series, opt) {
  const W = widthOf(el), Hh = W < 420 ? 190 : 210, m = { t: 12, r: W < 420 ? 52 : 70, b: 24, l: 40 };
  const xs = d3.scalePoint().domain(opt.x).range([m.l, W - m.r]);
  const vals = series.flatMap(s => s.values.filter(x => x != null));
  const y = d3.scaleLinear().domain(opt.yDomain || [0, Math.max(0.1, d3.max(vals) * 1.08)]).nice().range([Hh - m.b, m.t]);
  const svg = d3.select(el).html("").append("svg").attr("class", "chart").attr("width", W).attr("height", Hh).attr("viewBox", `0 0 ${W} ${Hh}`).attr("role", "img").attr("aria-label", opt.aria || "line chart");
  svg.append("g").attr("class", "grid").selectAll("line").data(y.ticks(4)).join("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", d => y(d)).attr("y2", d => y(d));
  svg.append("g").selectAll("text").data(y.ticks(4)).join("text").attr("x", m.l - 6).attr("y", d => y(d) + 3).attr("text-anchor", "end").text(d => opt.yFmt ? opt.yFmt(d) : d);
  svg.append("g").selectAll("text").data(opt.x).join("text").attr("x", d => xs(d)).attr("y", Hh - 6).attr("text-anchor", "middle").text(d => W < 420 ? String(d).replace(/^20/, "’") : d);
  const line = d3.line().defined(d => d[1] != null).x(d => xs(d[0])).y(d => y(d[1]));
  series.forEach(s => {
    const pts = opt.x.map((xk, k) => [xk, s.values[k]]);
    svg.append("path").attr("d", line(pts)).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 2).attr("stroke-dasharray", s.dash || null);
    svg.append("g").selectAll("circle").data(pts.filter(p => p[1] != null)).join("circle").attr("cx", d => xs(d[0])).attr("cy", d => y(d[1])).attr("r", 4)
      .attr("fill", s.color).attr("stroke", css("--paper")).attr("stroke-width", 2);
    const last = pts.filter(p => p[1] != null).pop();
    if (last && opt.endLabels !== false) svg.append("text").attr("class", "lbl").attr("x", xs(last[0]) + 8).attr("y", y(last[1]) + 4).text(s.name);
  });
  const hov = svg.append("line").attr("stroke", css("--muted")).attr("y1", m.t).attr("y2", Hh - m.b).style("display", "none");
  svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", Hh - m.t - m.b).attr("fill", "transparent")
    .on("mousemove", ev => {
      const [mx] = d3.pointer(ev);
      const k = d3.minIndex(opt.x, xk => Math.abs(xs(xk) - mx));
      hov.style("display", null).attr("x1", xs(opt.x[k])).attr("x2", xs(opt.x[k]));
      showTip(`<b>${esc(opt.x[k])}</b>` + series.map(s => `<div class="r"><span>${esc(s.name)}</span><span>${s.values[k] == null ? "—" : (opt.yFmt ? opt.yFmt(s.values[k]) : s.values[k])}</span></div>`).join(""), ev);
    }).on("mouseleave", () => { hov.style("display", "none"); hideTip(); });
}
function mixBar(g, p, r, big) {
  const G = Math.max(0, g), P = Math.max(0, p), R = Math.max(0, r), t = Math.max(1e-9, G + P + R);
  const lab = `Turnout ${pct(G / t)}, persuasion ${pct(P / t)}, rescue ${pct(R / t)}`;
  return `<span class="minibar" role="img" aria-label="${lab}" title="${lab}"${big ? ' style="width:100%;height:14px"' : ""}><span style="width:${100 * G / t}%;background:var(--c-gotv)"></span><span style="width:${100 * P / t}%;background:var(--c-pers)"></span><span style="width:${100 * R / t}%;background:var(--c-resc)"></span></span>`;
}
function bindRows(table) {
  table.querySelectorAll("tbody tr[data-id]").forEach(tr => {
    tr.addEventListener("click", e => { if (e.target.closest("a,button")) return; location.hash = "loc-" + tr.dataset.id; });
  });
}

/* ============================================================ SUMMARY */
function renderSummary() {
  const o = OBJ, P = S.potential[o];
  document.getElementById("sum-eyebrow").textContent = DAYS > 0 ? `the final ${DAYS} days` : "election 2026";
  const SC = scenarios(o);
  const id = S.list_identified, k15 = "150000_" + id, k40 = "400000_" + id;
  const linkName = i => `<a href="#loc-${L.id[i]}">${esc(L.en[i])}</a>`;
  const listNames = arr => arr.length > 1 ? arr.slice(0, -1).join(", ") + " and " + arr[arr.length - 1] : (arr[0] || "");
  const tgt = ALL.filter(isTarget);
  const top = tgt.slice().sort((a, b) => (ov("potential", b) ?? -1e9) - (ov("potential", a) ?? -1e9));
  const mvl = n => (D.mv.find(r => r.list === n) || {});
  const s40_0 = SC["400000_0"], s40 = SC[k40], s15_0 = SC["150000_0"];
  const bw = mvl("Blue & White"), res = mvl("Reservists");
  const arabSh = S.arab_share || {};
  // supporter-list ground under the CURRENT objective
  const supPool = tgt.filter(i => tierOf(i) === "Supporter-list ground").sort((a, b) => ov("list_pot", b) - ov("list_pot", a));
  const supTop = supPool.filter(i => ov("list_pot", i) >= 20).slice(0, 4).map(linkName);
  // identified people the 30% plans assume (half of each list is reached)
  const idPeople = (s40.contacts.sup + s40.contacts.pers + s40.contacts.resc) / 0.5;
  const rng = (b, idn) => { const r = budgetRange(o, b, idn); return r ? `${fmtSig(r[0])}–${fmtSig(r[1])}` : "—"; };

  // ---- decisions
  const dec = [
    { k: "objective", h: "Choose the objective", when: "Now", p: `A change-led government and a Netanyahu bloc below 61 point to different places. Per 10,000 votes, the Joint List moves ${OBJ_GOAL.change_govt} by ${sgn(mvl("Joint List").change_govt || 0)} points and ${OBJ_GOAL.block_nb} by ${sgn(mvl("Joint List").block_nb || 0)}. Outside Arab localities the two goals mostly agree. The objective bar at the top re-ranks every page.` },
    { k: "arab", h: "Hold the Arab-sector posture at leadership level", when: "To Tue 27 Oct", p: `Arab localities hold about ${pct(arabSh.block_nb)} of the modelled field potential for denying Netanyahu 61 and ${pct(arabSh.change_govt)} for a change-led government; the share depends on the assumed turnout effect. The atlas makes no field recommendation there, and none in polling stations where Arab lists lead elsewhere. Any support for Arab turnout should be independent, transparent and cleared by election counsel, and never run or branded by the change bloc.` },
    { k: "turf", h: "Keep the turf split between the four lists", when: "Sat 24 – Tue 27 Oct", p: `Four lists will canvass the same streets. Assign each polling station to its lead change list, shown on every locality page; where that list cannot staff a station, the locality's lead list takes it, or the locality's runner-up if that is the same list. Yashar leads most target stations, so staffing decides the rest. Share the station map and daily aggregate counts; share no voter-level records between lists unless election counsel has cleared the format in writing.` },
    { k: "lists", h: "Work the supporter lists the four campaigns hold", when: "Now to Tue 27 Oct", p: `Calls to identified supporters are the safe way to reach change voters ${supTop.length ? `inside Netanyahu-majority towns such as ${listNames(supTop)}` : "in Netanyahu-majority areas, where door canvassing backfires"}. If the four lists already hold ${pct(id)} of their target voters nationwide (about ${fmtSig(idPeople)} identified people across all target towns), 400,000 contacts buy about ${fmtSig(s40.ve)} net votes instead of ${fmtSig(s40_0.ve)}. Building those lists from scratch costs extra ID contacts that are not counted here.` },
    { k: "rescue", h: "Run rescue as a media programme from the final polls", when: `Launch ${fmtDay(S.dates.final_polls)}; calls to Mon 26 Oct`, p: `${bw.share > 0.001 ? `The forecast puts Blue and White at about ${pct(bw.share, 1)} (pass chance ${pct(bw.p_pass)}) and` : "Blue and White withdrew on 19 Oct, so rescue now concerns the Reservists only. The forecast puts"} the Reservists at about ${pct(res.share, 1)} (${pct(res.p_pass)}), though ${S.reservists_polls ? `${S.reservists_polls.above} of ${S.reservists_polls.n}` : "about half of the"} published polls since mid-September show the Reservists at 4–5 seats. Insurance messages work best when the final published polls, on ${fmtDay(S.dates.final_polls)}, show a list below the line. From ${fmtDay(S.dates.blackout)} the poll ban applies: rescue messages and call scripts use threshold arithmetic and quote no poll figures.${o === "block_nb" ? " Under this objective, rescuing Reservists voters slightly hurts: their vote counts against a Netanyahu 61 if the list passes, and some movers go to Likud." : ""}` },
    { k: "reservists", h: "Decide whether to call Reservists voters", when: `${fmtDay(S.dates.final_polls)}, after the final polls`, p: `The ${pct(id)}-identified budgets include about ${fmtSig(SC[k15].vp.resc)}–${fmtSig(s40.vp.resc)} net votes from rescue calls to Reservists voters. The playbook runs those calls only if leadership approves them and the final polls on ${fmtDay(S.dates.final_polls)} show the list below the line. Speak to them with respect: the bloc's equal-burden message depends on that constituency.` },
    { k: "druze", h: "Check the Druze candidate slots before any Druze work", when: "Before Tue 27 Oct", p: `Check the published CEC lists for Druze and Circassian candidates in winnable slots and any Druze polling. The summary budgets leave these towns out until then; if both clear them, they add about ${fmtSig(SC.druze[0])}–${fmtSig(SC.druze[1])} net votes. Any work there is then led by the candidates' own local teams.` },
  ];
  // leadership decisions: the objective, the content's strategic calls, then
  // the model-sized calls the content does not already cover; field calls go
  // to the field section
  const V = C.victory || {};
  const cdec = (V.decisions || []).map(d => ({ k: d.key || "", h: d.h, when: d.when, p: esc(d.p) + cites(d.cites), owner: d.owner }));
  const ckeys = new Set(cdec.map(d => d.k));
  const lead = [dec[0]].concat(cdec, dec.filter(d => ["arab", "rescue", "reservists"].includes(d.k) && !ckeys.has(d.k)));
  const fdec = dec.filter(d => ["turf", "lists", "druze"].includes(d.k));
  const card = d => `<div class="dec"><h3>${esc(d.h)}</h3><p>${d.p}</p><span class="when">${esc(d.when || "")}${d.owner ? " · " + esc(d.owner) : ""}</span></div>`;
  const dsub = document.getElementById("sum-dec-sub");
  if (dsub) dsub.textContent = `${lead.length} calls for bloc leadership, in rough order of what they are worth.`;
  document.getElementById("sum-decisions").innerHTML = lead.map(card).join("");
  const fd = document.getElementById("sum-field-dec");
  if (fd) fd.innerHTML = fdec.map(card).join("");
  if (V.lede) document.getElementById("sum-lede").textContent = V.lede;
  document.getElementById("sum-lev-sub").innerHTML = `Effect on ${esc(OBJ_GOAL[o])} if each lever happens, from the forecast's 8,000 simulated elections run through the seat law and the formation model. Sizes, not predictions: the <a href="#strategy">Strategy</a> page weighs whether each can be done.`;
  levChart(document.getElementById("sum-levchart"));
  const th = document.getElementById("sum-theory");
  if (th) th.innerHTML = (V.theory || []).map(f => `<div class="finding"><h3>${esc(f.title)}</h3><p>${esc(f.text)}${cites(f.cites)}</p>${f.go ? `<a class="go" href="${esc(f.go)}">More →</a>` : ""}</div>`).join("") || `<p class="muted">Not available in this build.</p>`;

  // ---- realistic value
  document.getElementById("sum-real-sub").innerHTML = `Field work is a margin lever. Under the objective <b>${esc(D.objectives[o])}</b>, a realistic programme of 150,000–400,000 completed contacts is worth about ${fmtSig(s15_0.ve)}–${fmtSig(s40.ve)} net votes, and roughly ${(() => { const lo = budgetRange(o, 150000, 0), hi = budgetRange(o, 400000, id); return lo && hi ? `${fmtSig(lo[0])} to ${fmtSig(hi[1])}` : "—"; })()} across the alternative assumption sets on the Method page; the size and shape of the turnout effect drive most of that range. That is small next to a 120-seat Knesset. It can still decide a threshold or the 61st seat: in 2022 Meretz missed the threshold by 4,061 votes.`;
  const tiles = [
    [`400,000 contacts, ${pct(id)} identified`, fmtSig(s40.ve), `net votes (range ${rng(400000, id)}), ${dpText(s40.ve)}${seatsOK(o) && o !== "change_seats" ? `; worth about ${seatsOf(s40.ve).toFixed(3)} expected change-bloc seats` : ""}.`],
    ["Same budget, door teams only", fmtSig(s40_0.ve), `net votes (range ${rng(400000, 0)}) with no supporter lists: door conversations on positive polling-station areas only.`],
    ["Saturation ceiling", fmtSig(P.potential), `net votes if every positive station area outside Arab localities were canvassed at 35% and every identified voter called: about ${fmtK(Math.round((P.area_contacts + P.list_contacts) / 1e5) * 1e5)} contacts. An upper bound, not a plan.`],
    ["Persuadable and rescue pool (modelled)", fmtSig(S.persuadable_voters + S.rescue_voters), `About ${fmtSig(S.persuadable_voters)} soft Netanyahu-bloc voters open to a change list, a calibration at the upper end of measured between-bloc indecision, plus about ${fmtSig(S.rescue_voters)} projected Blue and White and Reservists voters.`],
  ];
  document.getElementById("sum-tiles").innerHTML = tiles.map(t => `<div class="tile"><div class="k">${t[0]}</div><div class="v">${t[1]}</div><div class="d">${t[2]}</div></div>`).join("");
  const scRows = [["150,000", "150000_0", "none", 150000, 0], ["150,000", k15, pct(id), 150000, id], ["400,000", "400000_0", "none", 400000, 0], ["400,000", k40, pct(id), 400000, id]];
  const dz = SC.druze;
  document.getElementById("sum-scen").innerHTML = `<div style="overflow-x:auto"><table class="scen"><thead><tr><th>Contacts</th><th>Identified</th><th>Net votes</th><th>Range</th><th>Effect</th><th>Door towns</th></tr></thead><tbody>${scRows.map(([b, k, idt, bb, ii]) => `<tr><td>${b}</td><td>${idt}</td><td>${fmtSig(SC[k].ve)}</td><td>${rng(bb, ii)}</td><td>${effShort(SC[k].ve)}</td><td>${fmtInt(SC[k].doorLocs)}</td></tr>`).join("")}</tbody></table></div>
  <p class="note">Effect: change in ${OBJ_GOAL[o]} (baseline ${o === "change_seats" ? S.forecast.baseline.change_seats.toFixed(1) : pct(S.forecast.baseline[o], 1)}). Range: lowest and highest result across the alternative assumption sets (Method, section 11). Identified: share of change-bloc voters, soft Netanyahu-bloc voters and Blue and White or Reservists voters the campaign holds on lists; half of those are reached. Druze towns are held until a candidate check; if it clears them, they add about ${fmtSig(dz[0])} (150,000 contacts) to ${fmtSig(dz[1])} (400,000) net votes.</p>`;
  const nx = [...SC[k15].alloc].sort((a, b) => b[1].ve - a[1].ve).slice(0, 12);
  document.getElementById("sum-next-sub").textContent = `The first 150,000 contacts with ${pct(id)} of voters identified, best first, outside Arab localities and Druze towns. Door contacts go to positive polling-station areas; list contacts are calls, texts and relational asks to identified voters.`;
  document.getElementById("sum-next").innerHTML = `<thead><tr><th>Locality</th><th>Lead list</th><th class="n">Door</th><th class="n">List</th><th class="n">Net votes</th></tr></thead><tbody>${nx.map(([i, a]) => `<tr data-id="${L.id[i]}"><td class="loc">${locName(i)}</td><td>${leadOK(i) ? leadChip(L.lead[i]) : "—"}</td><td class="n">${fmtInt(a.area)}</td><td class="n">${fmtInt(a.sup + a.pers + a.resc)}</td><td class="n">${fmtNV(a.ve)}</td></tr>`).join("")}</tbody>`;
  bindRows(document.getElementById("sum-next"));

  // ---- findings
  const engines = top.filter(i => tierOf(i) === "Turnout engine" && !L.lowc[i]).slice(0, 6);
  const eng = tgt.filter(i => tierOf(i) === "Turnout engine" && !L.lowc[i] && ov("area_contacts", i) > 0);
  const turfY = d3.sum(eng, i => ov("area_pot", i)) / Math.max(1, d3.sum(eng, i => ov("area_contacts", i))) * 1000;
  const allY = d3.sum(eng, i => ov("area_avg_ve1k", i) * L.elig26[i]) / Math.max(1, d3.sum(eng, i => L.elig26[i]));
  const tgtc = tgt.filter(i => !L.lowc[i]);
  const natUnt = d3.sum(tgtc, i => ov("area_avg_ve1k", i) * L.elig26[i] * (1 - L.abroad[i]) * 0.35 / 1000);
  const natGain = d3.sum(tgtc, i => ov("area_pot", i));
  const cancel = 1 - natUnt / Math.max(1e-9, natGain);
  const supL = supPool.filter(i => ov("list_pot", i) >= 20).slice(0, 5);
  const supChange = d3.sum(supL, i => L.chsup[i]);
  const persTop = tgt.slice().sort((a, b) => ov("pers_pot", b) - ov("pers_pot", a)).slice(0, 5);
  const rescTop = tgt.slice().sort((a, b) => L.rescv[b] - L.rescv[a]).slice(0, 5);
  const druze = segRow("druze");
  const F = [
    { h: "There are no swing seats. There are swing people.", p: `One national district means a vote counts the same in Ofakim as in Ra'anana. A locality matters only for how many target voters it holds and how cheaply they can be reached. The atlas therefore ranks places by expected net votes per contact and in total, not by how close the local race is.`, go: "#method", gl: "Method" },
    { h: "Turnout engines: canvass the change-leaning stations of the big cities", p: `${listNames(engines.map(linkName))} lead on total potential. Choosing stations matters. Inside the turnout engines, a door conversation on the selected stations nets ${fmtNV(turfY)} per 1,000 against ${fmtNV(allY)} if every door were knocked. Outside Arab localities and Druze towns, knocking every door nationwide would ${natUnt < 0 ? `lose about ${fmtSig(-natUnt)} net votes, because losses in Netanyahu-majority areas outweigh the gains` : `net only about ${fmtSig(natUnt)} votes, because losses in Netanyahu-majority areas cancel ${cancel >= 0.5 ? "most" : "about " + pct(cancel)} of the gains`}.`, go: "#rankings", gl: "Door ranking" },
    supL.length ? { h: "Supporter-list ground: change voters inside Netanyahu-majority cities", p: `${listNames(supL.map(linkName))} ${supL.length > 1 ? "hold" : "holds"} about ${fmtSig(supChange)} projected change-bloc voters, but door canvassing beyond their few positive stations nets votes for the other side. Calls, texts and friend-to-friend asks to identified supporters reach them without mobilising their neighbours.`, go: "#planner", gl: "Planner" } : null,
    { h: "Persuasion is real but small", p: `About ${fmtSig(S.persuadable_voters)} soft Netanyahu-bloc voters (about ${pct(S.persuadable_voters / S.voters_2026, 0)} of projected voters, a modelled figure) are open to a change list. Persuasion is ${pct(Math.max(0, P.pers_pot) / Math.max(1e-9, P.potential))} of the saturation potential, concentrated in ${listNames(persTop.map(linkName))}. Run it inside the door conversation on positive stations and by calls to identified soft voters. It will not carry the campaign.`, go: "#rankings", gl: "Persuasion ranking" },
    { h: "Rescue is a media job, launched with the final polls", p: P.resc_pot > 0.5 ? `${bwOut() ? "Blue and White withdrew on 19 Oct, so the rescue pool is the Reservists' voters. They" : "Projected Blue and White and Reservists voters"} number about ${fmtSig(S.rescue_voters)}, largest in ${listNames(rescTop.map(linkName))}. They are about 2% of a typical station's voters, too thin for door teams. Rescue belongs in media, digital and calls to identified voters, framed around threshold arithmetic and respectful of the Reservists' constituency. Rescue calls to identified voters are ${pct(P.resc_pot / Math.max(1e-9, P.potential))} of the field potential under this objective.` : `Under this objective rescue adds little (${fmtNV(P.resc_pot)} net votes at saturation): a Reservists vote counts against a Netanyahu 61 if the list passes, and some movers go to Likud, ${bwOut() ? "so rescue calls are worth making only under the change-led objective." : "so only Blue and White voters are worth moving."}`, go: "#playbook", gl: "Playbook" },
    { h: "Arab turnout is a leadership decision, not a field target", p: `Arab-list votes are among the most valuable for denying Netanyahu 61. In the formation model, though, they mostly turn Netanyahu majorities into deadlock while diluting change-list seats, so they do little for a change-led government. Arab localities hold about ${pct(arabSh.block_nb)} of the modelled blocking potential and ${pct(arabSh.change_govt)} of the change-led-government potential, depending on the assumed turnout effect. The atlas ranks no Arab locality and plans no change-bloc work there.`, go: "#segments", gl: "Segments" },
    { h: "Druze towns: high returns on paper, lowest confidence", p: `Druze localities score well per contact (${pct((druze[o + "__share"]) || 0)} of potential). Low turnout meets a 2022 vote that leaned to the change camp. That vote followed home-village candidates, so the projection depends on which lists placed Druze candidates in winnable slots. The atlas holds these towns out of the summary budgets until that check and a Druze poll are done. Work there through Druze figures on the lists, not outside canvassers.`, go: "#seg-druze", gl: "Druze segment" },
  ].filter(Boolean);
  document.getElementById("sum-findings").innerHTML = F.map((f, k) => k === 0
    ? `<div class="finding lead"><h3>${f.h}</h3><div><p>${f.p}</p><a class="go" href="${f.go}">${f.gl} →</a></div></div>`
    : `<div class="finding"><h3>${f.h}</h3><p>${f.p}</p><a class="go" href="${f.go}">${f.gl} →</a></div>`).join("");

  // ---- three lists
  const pool = tgt.filter(i => L.elig[i] >= 5000 && !L.lowc[i]);
  const lists3 = [
    ["Swing localities", "persuadable + rescuable voters", i => L.persv[i] + L.rescv[i], fmtInt],
    ["Turnout potential", "net votes from turnout work", i => ov("gotv_pot", i), fmtNV],
    ["Highest impact", "total potential, net votes", i => ov("potential", i), fmtNV],
  ];
  document.getElementById("sum-three").innerHTML = lists3.map(([h, sub, f, fm]) => {
    const t10 = pool.slice().sort((a, b) => f(b) - f(a)).slice(0, 10);
    return `<div class="card"><h3>${h}</h3><p class="sub">${sub}</p><table class="t" style="margin-top:8px"><tbody>${t10.map((i, k) => `<tr data-id="${L.id[i]}"><td class="n" style="width:24px">${k + 1}</td><td class="loc" style="min-width:0">${locName(i)}</td><td class="n">${fm(f(i))}</td></tr>`).join("")}</tbody></table></div>`;
  }).join("");
  document.querySelectorAll("#sum-three table").forEach(bindRows);

  // ---- segment chart (segment totals; no town-level Arab values)
  const posTot = d3.sum(D.segments, s => Math.max(0, s[o + "__potential"]));
  const segRows = D.segments.map(s => ({
    label: SEG_SHORT[s.segment] || s.label, total: s[o + "__potential"],
    parts: [{ v: s[o + "__gotv_pot"], color: css("--c-gotv"), name: "Turnout" }, { v: s[o + "__pers_pot"], color: css("--c-pers"), name: "Persuasion" }, { v: s[o + "__resc_pot"], color: css("--c-resc"), name: "Rescue" }],
  })).sort((a, b) => b.total - a.total);
  hbars(document.getElementById("sum-segchart"), segRows, { labelW: 230, valFmt: x => fmtNV(x) + " net votes", totFmt: x => pct(x / Math.max(1e-9, posTot)), tickFmt: x => fmtInt(x), aria: "Potential by segment" });

  // ---- don'ts (the content's cited list when present, else the built-in list)
  const donts = (V.donts && V.donts.length) ? V.donts.map(d => [d.title, d.text, d.cites]) : [
    ["Don't knock every door", "Door GOTV in Netanyahu-majority polling stations nets votes for the other side. Canvass only stations with positive value, listed on each locality's page."],
    ["Don't run change-bloc GOTV among Arab voters", "Arab-sector turnout is a leadership decision, in Arab towns and in mixed-city stations where Arab lists lead. Any support should be independent, transparent and cleared by election counsel."],
    ["Don't drain the Reservists on the doorstep", "Rescue works through media and threshold arithmetic. Speak to Reservists voters with respect: the bloc's equal-burden message depends on that constituency."],
    ["Don't headline the Druze numbers", "Their 2026 vote depends on which lists placed Druze candidates in winnable slots. Check the filed CEC lists and hold the Druze rankings until that check and a Druze poll are done."],
    ["Don't break the blackout or the polling-station rules", `No poll may be published, or quoted in campaign material, from ${fmtDay(S.dates.blackout)}. Election-day transport, gifts and activity near polling stations are regulated: check with election counsel.`],
  ];
  document.getElementById("sum-donts").innerHTML = donts.map(d => `<div><h4>${esc(d[0])}</h4><p>${esc(d[1])}${d[2] ? cites(d[2]) : ""}</p></div>`).join("");

  // ---- top table
  const rows = tgt.filter(i => L.elig[i] >= 1000 && !L.lowc[i] && ov("rank", i) != null).sort((a, b) => ov("rank", a) - ov("rank", b)).slice(0, 20);
  document.getElementById("sum-top").innerHTML = `<thead><tr><th class="n">#</th><th>Locality</th><th>Segment</th><th class="n">Eligible</th><th class="n">Change bloc 2026</th><th>Lead list</th><th>Tier</th><th class="n">Potential, net votes</th><th class="n">Per 1,000 contacts</th><th>Mix</th></tr></thead><tbody>` +
    rows.map(i => `<tr data-id="${L.id[i]}"><td class="n">${fmtInt(ov("rank", i))}</td><td class="loc">${locName(i)}</td><td>${segChip(L.seg[i])}</td><td class="n">${fmtInt(L.elig[i])}</td><td class="n">${pct(L.pch[i])}</td><td>${leadOK(i) ? leadChip(L.lead[i]) : "—"}</td><td>${tierChip(tierOf(i))}</td><td class="n">${fmtNV(ov("potential", i))}</td><td class="n">${fmtNV(ov("eff1k", i))}</td><td>${mixBar(ov("gotv_pot", i), ov("pers_pot", i), ov("resc_pot", i))}</td></tr>`).join("") + `</tbody>`;
  bindRows(document.getElementById("sum-top"));
}


/* ============================================================ LEVERS (shared) */
const LEV = D.levers || {};
const LEV_BY = new Map((LEV.scenarios || []).map(x => [x.key, x]));
// change in the objective for a scenario, in display units (pts or seats)
const levDelta = (x, o) => (o || OBJ) === "change_seats" ? x.delta.change_seats : x.delta[o || OBJ] * 100;
const levFmt = (v, o) => (o || OBJ) === "change_seats" ? sgn(v, 2) + " seats" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(Math.abs(v) < 0.1 ? 2 : 1) + " pts";
// the field programme as a lever: 400,000 contacts, 30% identified (summary exclusions)
function fieldLever(o) {
  const r = scenarios(o)["400000_" + S.list_identified];
  const d = effOf(r.ve, o);
  return { key: "field", group: "field", title: "Field programme: 400,000 contacts, 30% of voters identified", votes: Math.round(r.ve),
           what: "Door canvassing on positive polling-station areas plus calls to identified voters, allocated by the planner (Field pages).",
           delta: { [o]: o === "change_seats" ? d : d } };
}
// Blue and White withdrew on 19 Oct: the forecast routes its vote and the list has no row in the exchange rates
const bwOut = () => !(((D.mv || []).find(r => r.list === "Blue & White") || {}).share > 0.001);
const LEV_ACT = ["bw_withdraws", "res_withdraws", "pers_likud_0.5", "pers_likud_1.0", "pers_haredi_0.5", "ch_turnout_25000", "ch_turnout_50000", "bw_plus_pers_0.5"];
const LEV_RISK = ["res_withdraws_right", "amcha_withdraws", "nb_turnout_25000", "arab_turnout_+5"];
const LEV_SHORT = {
  bw_withdraws: "Blue and White withdraws and endorses", res_withdraws: "Reservists withdraw (60% to change lists)",
  "pers_likud_0.5": "0.5 pt of the vote moves from Likud", "pers_likud_1.0": "1 pt of the vote moves from Likud",
  "pers_haredi_0.5": "0.5 pt moves from Shas and UTJ", ch_turnout_25000: "25,000 extra change-bloc votes",
  ch_turnout_50000: "50,000 extra change-bloc votes", "bw_plus_pers_0.5": "Blue and White withdraws + 0.5 pt from Likud",
  res_withdraws_right: "Reservists withdraw, mostly to the right", amcha_withdraws: "Amcha withdraws (right consolidates)",
  nb_turnout_25000: "25,000 extra Netanyahu-bloc votes", "arab_turnout_+5": "Arab turnout up 5 points", field: "Field programme (400,000 contacts)",
};
function levChart(el) {
  const o = OBJ;
  const rows = [];
  const push = (x, grp) => rows.push({ label: LEV_SHORT[x.key] || x.title, v: x.key === "field" ? (o === "change_seats" ? x.delta[o] : x.delta[o] * 100) : levDelta(x, o), grp, x });
  LEV_ACT.forEach(k => { if (LEV_BY.has(k)) push(LEV_BY.get(k), "act"); });
  push(fieldLever(o), "act");
  LEV_RISK.forEach(k => { if (LEV_BY.has(k)) push(LEV_BY.get(k), "risk"); });
  const act = rows.filter(r => r.grp === "act").sort((a, b) => b.v - a.v), risk = rows.filter(r => r.grp === "risk").sort((a, b) => a.v - b.v);
  const all = act.concat(risk);
  const W = widthOf(el), narrow = W < 560, rh = 24, gap = 26, lw = Math.min(250, Math.round(W * (narrow ? 0.46 : 0.34)));
  const Hh = all.length * rh + gap + 40;
  const ext = d3.max(all, r => Math.abs(r.v)) || 1;
  const x = d3.scaleLinear().domain([Math.min(0, d3.min(all, r => r.v)), Math.max(0, d3.max(all, r => r.v))]).nice().range([lw, W - (narrow ? 48 : 70)]);
  const svg = d3.select(el).html("").append("svg").attr("class", "chart").attr("width", W).attr("height", Hh).attr("viewBox", `0 0 ${W} ${Hh}`).attr("role", "img").attr("aria-label", `Levers by modelled effect on ${OBJ_GOAL[o]}`);
  const yOf = (r, k) => 18 + k * rh + (r.grp === "risk" ? gap : 0);
  svg.append("g").attr("class", "grid").selectAll("line").data(x.ticks(5)).join("line").attr("x1", d => x(d)).attr("x2", d => x(d)).attr("y1", 12).attr("y2", Hh - 22);
  svg.append("g").selectAll("text").data(x.ticks(5)).join("text").attr("x", d => x(d)).attr("y", Hh - 6).attr("text-anchor", "middle").text(d => o === "change_seats" ? d : d + "");
  svg.append("text").attr("x", lw).attr("y", 10).attr("class", "lbl").text("What the bloc can move");
  svg.append("text").attr("x", lw).attr("y", 18 + act.length * rh + gap - 8).attr("class", "lbl").text("What could go against it");
  all.forEach((r, k) => {
    const y = yOf(r, k);
    const maxc = Math.max(12, Math.floor((lw - 14) / 6.7));
    const lab = r.label.length > maxc ? r.label.slice(0, maxc - 1).replace(/\s+\S*$/, "") + "…" : r.label;
    svg.append("text").attr("class", "lbl").attr("x", lw - 8).attr("y", y + rh / 2 + 4).attr("text-anchor", "end").text(lab).append("title").text(r.label);
    const x0 = x(Math.min(0, r.v)), w = Math.abs(x(r.v) - x(0));
    svg.append("rect").attr("x", x0).attr("y", y + 4).attr("width", Math.max(1, w)).attr("height", rh - 8).attr("fill", r.v >= 0 ? css("--c-change") : css("--c-nb"))
      .on("mousemove", ev => showTip(`<b>${esc(r.x.title)}</b><div style="opacity:.85;margin-top:3px">${esc(r.x.what || "")}</div><div class="r"><span>Votes involved</span><span>${fmtInt(r.x.votes)}</span></div><div class="r"><span>Effect</span><span>${esc(levFmt(r.v, o))}</span></div>`, ev)).on("mouseleave", hideTip);
    svg.append("text").attr("class", "lbl").attr("x", r.v >= 0 ? x(r.v) + 6 : x(0) + 6).attr("y", y + rh / 2 + 4).attr("text-anchor", "start").text(levFmt(r.v, o));
  });
  svg.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 12).attr("y2", Hh - 22).attr("stroke", css("--ink")).attr("stroke-width", 1);
}

/* ============================================================ STRATEGY */
const GROUP_TITLE = { agreements: "Agreements between lists", persuasion: "Persuasion and issue salience", turnout: "Turnout at national scale", allies: "Allies and thresholds", coalition: "Coalition signals", field: "Field programme", arab: "Arab-sector turnout (leadership decision)", risks: "Risks to manage" };
function effRows(keys) {
  return (keys || []).map(k => {
    const x = k === "field" ? null : LEV_BY.get(k);
    if (k === "field") { const f = fieldLever(OBJ); return `<div><span>${esc(LEV_SHORT.field)}</span><b>${esc(levFmt(OBJ === "change_seats" ? f.delta[OBJ] : f.delta[OBJ] * 100))}</b><span>${fmtInt(f.votes)} net votes</span></div>`; }
    if (!x) return "";
    return `<div><span>${esc(x.title)}</span><b>${esc(levFmt(levDelta(x)))}</b><span>${fmtInt(x.votes)} votes · ${OBJ === "block_nb" ? "change-led govt " + levFmt(levDelta(x, "change_govt"), "change_govt") : "deny 61 " + levFmt(levDelta(x, "block_nb"), "block_nb")}</span></div>`;
  }).join("");
}
function renderStrategy() {
  const C4 = C.strategy || {};
  const root = document.getElementById("st-root");
  if (C4.intro) document.getElementById("st-lede").textContent = C4.intro;
  const base = LEV.base || {};
  let h = `<section class="block"><h2 class="h2">The levers, by size</h2><p class="sub">Effect on ${esc(OBJ_GOAL[OBJ])} if each lever happens, from the forecast's 8,000 simulated elections run through the seat law and the formation model (baseline ${OBJ === "change_seats" ? (base.change_seats || 0).toFixed(1) + " seats" : pct(base[OBJ], 1)}). These are sizes, not predictions that a lever will work; feasibility is assessed lever by lever below.</p><div id="st-chart"></div></section>`;
  if (C4.principles && C4.principles.length) h += `<section class="block"><h2 class="h2">Principles</h2><div class="kvlist">${C4.principles.map(x => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(x.title)}</h3><p>${esc(x.text)}${cites(x.cites)}</p></div>`).join("")}</div></section>`;
  const levers = C4.levers || [];
  const groups = [...new Set(levers.map(l => l.group))];
  h += groups.map(g => `<section class="block levgroup"><h3>${esc(GROUP_TITLE[g] || g)}</h3>${levers.filter(l => l.group === g).map(l => `<div class="levcard" id="lev-${esc(l.key)}">
    <h4>${esc(l.title)}</h4>
    <div class="meta">${l.feasibility ? `<span class="feas ${esc(l.feasibility)}">feasibility: ${esc(l.feasibility)}</span>` : ""}${l.timing ? `<span>When: ${esc(l.timing)}</span>` : ""}${l.owner ? `<span>Who: ${esc(l.owner)}</span>` : ""}</div>
    ${l.scenarios && l.scenarios.length ? `<div class="eff">${effRows(l.scenarios)}</div>` : ""}
    <p>${esc(l.summary || "")}</p>
    ${l.evidence ? `<p><b>Evidence.</b> ${esc(l.evidence)}${cites(l.cites)}</p>` : (l.cites && l.cites.length ? `<p>${cites(l.cites)}</p>` : "")}
    ${l.feasibility_note ? `<p><b>Can it be done?</b> ${esc(l.feasibility_note)}</p>` : ""}
    ${l.actions && l.actions.length ? `<p><b>Actions</b></p><ul>${l.actions.map(a => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
    ${l.risks && l.risks.length ? `<p><b>Risks</b></p><ul>${l.risks.map(a => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
  </div>`).join("")}</section>`).join("");
  if (!levers.length) h += `<section class="block"><p class="muted">Lever-by-lever guidance is not available in this build.</p></section>`;
  root.innerHTML = h;
  levChart(document.getElementById("st-chart"));
}

/* ============================================================ MESSAGING */
function renderMessaging() {
  const M = C.messaging || {};
  const root = document.getElementById("ms-root");
  if (M.intro) document.getElementById("ms-lede").textContent = M.intro;
  if (!M.principles && !M.issues) { root.innerHTML = `<p class="muted" style="padding:30px 0">Messaging guidance is not available in this build.</p>`; return; }
  const verdictColor = { core: "var(--good)", "use selectively": "var(--accent)", "low value": "var(--muted)", avoid: "var(--bad)" };
  const tl = arr => `<div class="timeline">${arr.map(t => `<div class="tl-row"><div class="when">${esc(t.when)}<small>${esc(t.dates || "")}</small></div><div class="what"><p style="font-size:14.5px;color:var(--ink2)">${esc(t.what)}${cites(t.cites)}</p></div></div>`).join("")}</div>`;
  root.innerHTML = `
  ${M.principles ? `<section class="block"><h2 class="h2">What the evidence says about campaign messages</h2><div class="kvlist">${M.principles.map(x => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(x.title)}</h3><p>${esc(x.text)}${cites(x.cites)}</p></div>`).join("")}</div></section>` : ""}
  ${M.issues ? `<section class="block"><h2 class="h2">The issues</h2><p class="sub">Which issues to raise, who they move and the frame that works, with the risk of each.</p><div class="tblwrap" style="max-height:none;margin-top:16px"><table class="t static"><thead><tr><th>Issue</th><th>Who it moves</th><th>Frame</th><th>Risk</th></tr></thead><tbody>${M.issues.map(x => `<tr><td style="white-space:normal;min-width:140px"><b>${esc(x.issue)}</b>${x.owner ? `<div class="muted" style="font-size:12px;margin-top:4px">Owned by: ${esc(x.owner)}</div>` : ""}</td><td style="white-space:normal;min-width:180px">${esc(x.who_it_moves)}</td><td style="white-space:normal;min-width:280px">${esc(x.frame)}${cites(x.cites)}</td><td style="white-space:normal;min-width:180px">${esc(x.risk || "")}</td></tr>`).join("")}</tbody></table></div></section>` : ""}
  ${M.audiences ? `<section class="block"><h2 class="h2">Audiences</h2><div class="segcards">${M.audiences.map(a => `<div class="segcard"><h3>${esc(a.audience)}</h3>${a.size_note ? `<div class="stats"><span>${esc(a.size_note)}</span></div>` : ""}<dl><dt>What moves them</dt><dd>${esc(a.what_moves)}${cites(a.cites)}</dd><dt>Message</dt><dd>${esc(a.message)}</dd><dt>Messenger</dt><dd>${esc(a.messenger)}</dd><dt>Channel</dt><dd>${esc(a.channel || "")}</dd><dt>Avoid</dt><dd>${esc(a.avoid || "")}</dd></dl></div>`).join("")}</div></section>` : ""}
  ${M.media ? `<section class="block"><h2 class="h2">Media and digital</h2><div class="tblwrap" style="max-height:none;margin-top:16px"><table class="t static"><thead><tr><th>Channel</th><th>Role</th><th>Evidence</th><th>Rules</th><th>Verdict</th></tr></thead><tbody>${M.media.map(x => `<tr><td style="white-space:normal;min-width:130px"><b>${esc(x.channel)}</b></td><td style="white-space:normal;min-width:180px">${esc(x.role)}</td><td style="white-space:normal;min-width:260px">${esc(x.evidence)}${cites(x.cites)}</td><td style="white-space:normal;min-width:200px">${esc(x.rules || "")}</td><td><span class="chip" style="color:${verdictColor[x.verdict] || "var(--ink)"}">${esc(x.verdict || "")}</span></td></tr>`).join("")}</tbody></table></div></section>` : ""}
  ${M.rapid_response ? `<section class="block"><h2 class="h2">Rapid response and misinformation</h2><div class="kvlist">${M.rapid_response.map(x => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(x.title)}</h3><p>${esc(x.text)}${cites(x.cites)}</p></div>`).join("")}</div></section>` : ""}
  ${M.calendar ? `<section class="block"><h2 class="h2">The message calendar</h2>${tl(M.calendar)}</section>` : ""}`;
}

/* ============================================================ COALITION */
const OUTCOME_CAMP = { "Netanyahu rightist coalition": "nb", "Netanyahu + unaligned / defector coalition": "nb", "Change coalition (without Ra'am)": "ch", "Change coalition with unaligned / Amcha": "ch", "Change coalition with a haredi party": "ch", "Centre minority backed by the Joint List": "ch", "Change coalition with Ra'am": "ch", "Unity government (Likud without Netanyahu)": "un", "Repeat election": "rep" };
function renderCoalition() {
  const Q = C.coalition || {};
  const root = document.getElementById("co-root");
  if (Q.intro) document.getElementById("co-lede").textContent = Q.intro;
  const gov = (S.forecast.gov || []).slice().sort((a, b) => b.p - a.p);
  const pOf = k => { const g = gov.find(x => x.outcome === k); return g ? g.p : null; };
  root.innerHTML = `
  <section class="block"><h2 class="h2">What the forecast says happens after the vote</h2><p class="sub">Government outcomes in the forecast's formation model (published forecast, polls to ${fmtDate(S.asof)}). Change-led outcomes in orange, Netanyahu-led in blue.</p><div id="co-chart"></div>${Q.outcomes_note ? `<p class="note">${esc(Q.outcomes_note)}</p>` : ""}</section>
  ${Q.paths ? `<section class="block"><h2 class="h2">Paths to a change-led government</h2><div class="tblwrap" style="max-height:none;margin-top:16px"><table class="t static"><thead><tr><th>Path</th><th class="n">Forecast chance</th><th>Partners</th><th>How</th><th>Obstacles</th></tr></thead><tbody>${Q.paths.map(x => `<tr><td style="white-space:normal;min-width:150px"><b>${esc(x.path)}</b></td><td class="n">${x.outcome_key && pOf(x.outcome_key) != null ? pct(pOf(x.outcome_key), 1) : "—"}</td><td style="white-space:normal;min-width:150px">${esc(x.partners || "")}</td><td style="white-space:normal;min-width:240px">${esc(x.how || "")}${cites(x.cites)}</td><td style="white-space:normal;min-width:200px">${esc(x.obstacles || "")}</td></tr>`).join("")}</tbody></table></div></section>` : ""}
  ${Q.signals ? `<section class="block"><h2 class="h2">Signals before the vote</h2><p class="sub">What the bloc says now about the government it would form changes how some voters choose and what is possible afterwards.</p><div class="kvlist">${Q.signals.map(x => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(x.title)}</h3><p>${esc(x.text)}${cites(x.cites)}</p>${x.risk ? `<p><b>Risk.</b> ${esc(x.risk)}</p>` : ""}</div>`).join("")}</div></section>` : ""}
  ${Q.formation ? `<section class="block"><h2 class="h2">The formation timeline</h2><div class="timeline">${Q.formation.map(t => `<div class="tl-row"><div class="when">${esc(t.step)}<small>${esc(t.when || "")}</small></div><div class="what"><p style="font-size:14.5px;color:var(--ink2)">${esc(t.what)}${cites(t.cites)}</p></div></div>`).join("")}</div></section>` : ""}
  ${Q.prepare ? `<section class="block"><h2 class="h2">Prepare now</h2><div class="kvlist">${Q.prepare.map(x => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(x.title)}</h3><p>${esc(x.text)}${cites(x.cites)}</p></div>`).join("")}</div></section>` : ""}
  ${Q.repeat ? `<section class="block"><h2 class="h2">${esc(Q.repeat.title || "If it goes to a repeat election")}</h2><div class="prose"><p>${esc(Q.repeat.text)}${cites(Q.repeat.cites)}</p></div></section>` : ""}`;
  const el = document.getElementById("co-chart");
  const colorOf = k => ({ ch: css("--c-change"), nb: css("--c-nb"), un: css("--c-una"), rep: css("--t-second") })[OUTCOME_CAMP[k] || "un"];
  hbars(el, gov.map(g => ({ label: g.outcome, total: g.p, parts: [{ v: g.p, color: colorOf(g.outcome), name: g.outcome }] })),
    { labelW: 280, valFmt: x => pct(x, 1), totFmt: x => pct(x, 1), tickFmt: x => pct(x), aria: "Government outcomes in the formation model" });
}

/* ============================================================ MAP */
const METRICS = [
  { k: "potential", label: "Priority: total potential", sub: "net votes", type: "seq", get: i => ov("potential", i), fmt: x => fmtNV(x) + " net votes" },
  { k: "eff", label: "Door efficiency", sub: "per 1,000", type: "seq", get: i => ov("area_eff1k", i), fmt: x => fmtNV(x) + " net votes per 1,000 door conversations" },
  { k: "tier", label: "Priority tier", sub: "category", type: "tier", get: i => tierOf(i) },
  { k: "lead", label: "Lead change list", sub: "turf split", type: "lead", get: i => leadOK(i) ? L.lead[i] : "" },
  { k: "lean26", label: "2026 lean (projected)", sub: "change − NB", type: "div", get: i => L.pch[i] - L.pnb[i], fmt: x => (x >= 0 ? "Change +" : "Netanyahu bloc +") + Math.abs(x * 100).toFixed(0) + " pts" },
  { k: "lean22", label: "2022 lean (actual)", sub: "centre-left − right", type: "div", get: i => L.s22C[i] - L.s22R[i], fmt: x => (x >= 0 ? "Centre-left +" : "Right +") + Math.abs(x * 100).toFixed(0) + " pts" },
  { k: "swing", label: "Persuadable density", sub: "% of voters", type: "seq", get: i => L.pers[i], fmt: x => pct(x, 1) + " persuadable" },
  { k: "turnout", label: "Turnout opportunity", sub: "net per 1,000", type: "seq", get: i => Math.max(0, L.netg[i]), fmt: x => fmtNV(x) + " net change votes per 1,000 turnout conversations on the best stations" },
  { k: "rescue", label: "Wasted-vote pool", sub: "% Reservists (and B&W)", type: "seq", get: i => L.resc[i], fmt: x => pct(x, 1) + " projected below-threshold vote (Reservists; Blue and White withdrew on 19 Oct)" },
  { k: "tres", label: "Resident turnout 2022", sub: "estimated", type: "seq", get: i => L.tres[i], fmt: x => pct(x) + " resident turnout" },
  { k: "block", label: "Blocking value", sub: "net votes", type: "seq", get: i => L["block_nb.potential"][i], fmt: x => fmtNV(x) + " net votes (deny 61)" },
];
// metrics that carry targeting values: Arab localities are shown as not ranked
const VALUE_METRICS = new Set(["potential", "eff", "block", "turnout"]);

let mapMetric = store.get("mapMetric", "potential");
if (!METRICS.some(m => m.k === mapMetric)) mapMetric = "potential";
const _ms = store.get("mapSegs", SEG_ORDER);
let mapSegs = new Set(Array.isArray(_ms) ? _ms.filter(x => SEG_LABEL[x]) : SEG_ORDER);
let mapMin = store.get("mapMin", 0);
if (![0, 1000, 5000, 20000].includes(+mapMin)) mapMin = 0;
let mapSel = null, mapInit = false, mapZoom, mapG, mapProj, mapSvg, mapCircles, mapLabels, mapW = 600, mapH = 900, mapK = 1;
const PRESETS = [
  ["Israel", null], ["Gush Dan", [34.70, 31.94, 34.97, 32.19]], ["Sharon", [34.80, 32.12, 35.08, 32.45]],
  ["Jerusalem", [35.08, 31.70, 35.30, 31.88]], ["Haifa & Krayot", [34.94, 32.73, 35.16, 32.92]],
  ["Galilee", [35.05, 32.62, 35.72, 33.30]], ["Negev", [34.35, 30.80, 35.35, 31.62]],
];
function fixRing(ring) {
  const f = { type: "Polygon", coordinates: [ring] };
  if (d3.geoArea(f) > 2 * Math.PI) f.coordinates = [ring.slice().reverse()];
  return f;
}
function colorScale(metric, idxs) {
  const m = METRICS.find(x => x.k === metric);
  if (m.type === "div") {
    const th = [-0.5, -0.25, -0.08, 0.08, 0.25, 0.5];
    const cols = ["--div-nb3", "--div-nb2", "--div-nb1", "--div-mid", "--div-ch1", "--div-ch2", "--div-ch3"].map(css);
    return { f: x => cols[d3.bisect(th, x)], th, cols, m };
  }
  if (m.type === "tier") return { f: t => { const st = TIER_STYLE[t] || {}; return st.fill ? css(st.fill) : "transparent"; }, m };
  if (m.type === "lead") return { f: l => l ? css(LEAD_VAR[l]) : css("--t-low"), m };
  const vals = idxs.filter(i => !isArab(i) || !VALUE_METRICS.has(m.k)).map(m.get).filter(x => x != null && x > 0).sort(d3.ascending);
  const qs = [0.2, 0.4, 0.6, 0.8, 0.95].map(q => d3.quantileSorted(vals, q) || 0);
  const cols = ["--seq0", "--seq1", "--seq2", "--seq3", "--seq4", "--seq5"].map(css);
  return { f: x => (x == null || x <= 0) ? css("--t-low") : cols[d3.bisect(qs, x)], th: qs, cols, m };
}
function initMap(keep) {
  mapSvg = d3.select("#mapsvg");
  const col = document.querySelector(".mapcol");
  let center = null, k = 1;
  if (keep && mapProj && mapSvg.node()) {
    const t = d3.zoomTransform(mapSvg.node());
    k = t.k; center = mapProj.invert(t.invert([mapW / 2, mapH / 2]));
  }
  mapW = col.clientWidth || 600; mapH = col.clientHeight || 900;
  mapSvg.attr("viewBox", `0 0 ${mapW} ${mapH}`);
  const isr = { type: "GeometryCollection", geometries: D.geo.israel.map(fixRing).concat(Object.values(D.geo.palestine).flat().map(fixRing)) };
  mapProj = d3.geoMercator().fitExtent([[16, 16], [mapW - 16, mapH - 56]], isr);
  const path = d3.geoPath(mapProj);
  mapSvg.selectAll("*").remove();
  mapSvg.append("rect").attr("width", mapW).attr("height", mapH).attr("fill", "var(--sea)");
  mapG = mapSvg.append("g");
  mapG.append("g").selectAll("path").data(D.geo.neighbors.map(fixRing)).join("path").attr("d", path).attr("fill", "var(--land-ext)").attr("stroke", "var(--border-geo)").attr("stroke-width", 0.6);
  mapG.append("g").selectAll("path").data(D.geo.israel.map(fixRing)).join("path").attr("d", path).attr("fill", "var(--land)").attr("stroke", "var(--border-geo)").attr("stroke-width", 0.8);
  mapG.append("g").selectAll("path").data(Object.values(D.geo.palestine).flat().map(fixRing)).join("path").attr("d", path).attr("fill", "var(--land-wb)").attr("stroke", "var(--border-geo)").attr("stroke-width", 0.9).attr("stroke-dasharray", "3 2");
  mapG.append("g").selectAll("path").data(D.geo.districts.map(fixRing)).join("path").attr("d", path).attr("fill", "none").attr("stroke", "var(--border-geo)").attr("stroke-width", 0.5).attr("stroke-opacity", 0.7);
  const lbl = [["Mediterranean Sea", 34.12, 32.55], ["West Bank", 35.28, 31.95], ["Gaza", 34.36, 31.42], ["Jordan", 35.75, 31.0], ["Lebanon", 35.55, 33.36], ["Egypt", 34.3, 30.4]];
  mapG.append("g").selectAll("text").data(lbl).join("text").attr("x", d => mapProj([d[1], d[2]])[0]).attr("y", d => mapProj([d[1], d[2]])[1])
    .attr("text-anchor", "middle").attr("fill", "var(--muted)").attr("font-family", "var(--f-mono)").attr("font-size", 10).attr("letter-spacing", ".08em").attr("class", "geo-lbl").text(d => d[0].toUpperCase());
  const rmax = Math.min(mapW, mapH) / 32;
  const r = d3.scaleSqrt().domain([0, d3.max(L.elig)]).range([0, rmax]);
  const baseR = i => Math.max(1.6, r(L.elig[i]));
  const order = ALL.filter(i => L.lat[i] != null).sort((a, b) => L.elig[b] - L.elig[a]);
  mapCircles = mapG.append("g").selectAll("circle").data(order).join("circle")
    .attr("cx", i => mapProj([L.lon[i], L.lat[i]])[0]).attr("cy", i => mapProj([L.lon[i], L.lat[i]])[1])
    .attr("data-r", baseR).attr("r", baseR).style("cursor", "pointer")
    .on("mousemove", (ev, i) => showTip(mapTip(i), ev)).on("mouseleave", hideTip)
    .on("click", (ev, i) => { ev.stopPropagation(); selectLoc(i); });
  const lblIdx = order.filter(i => L.elig[i] >= 12000);
  mapLabels = mapG.append("g").selectAll("text").data(lblIdx).join("text")
    .attr("x", i => mapProj([L.lon[i], L.lat[i]])[0]).attr("y", i => mapProj([L.lon[i], L.lat[i]])[1])
    .attr("text-anchor", "middle").attr("font-family", "var(--f-sans)").attr("font-weight", 600)
    .attr("fill", "var(--ink)").attr("stroke", "var(--paper)").attr("stroke-width", 3).attr("paint-order", "stroke")
    .attr("pointer-events", "none").text(i => L.en[i]).style("display", "none");
  mapG.selectAll("path,circle").attr("vector-effect", "non-scaling-stroke");
  mapZoom = d3.zoom().scaleExtent([1, 60])
    .filter(ev => ev.type === "wheel" ? true : (ev.type.startsWith("touch") ? (ev.touches && ev.touches.length >= 2) : (!ev.ctrlKey && !ev.button)))
    .on("zoom", ev => {
      const kk = ev.transform.k; mapK = kk;
      mapG.attr("transform", ev.transform);
      const shrink = Math.pow(kk, 0.72);
      mapCircles.attr("r", function () { return (+this.getAttribute("data-r")) / shrink; });
      mapG.selectAll(".geo-lbl").attr("font-size", 10 / kk);
      mapLabels.style("display", i => (kk >= 5 && L.elig[i] >= 12000) || (kk >= 2.4 && L.elig[i] >= 40000) || (kk >= 1.5 && L.elig[i] >= 150000) ? null : "none")
        .attr("font-size", 11 / kk).attr("stroke-width", 3 / kk)
        .attr("dy", i => -(baseR(i) / shrink + 3 / kk));
    });
  if (!center) { mapSvg.property("__zoom", d3.zoomIdentity); mapK = 1; }
  mapSvg.call(mapZoom).on("dblclick.zoom", null);
  if (center) {
    const p = mapProj(center);
    mapSvg.call(mapZoom.transform, d3.zoomIdentity.translate(mapW / 2, mapH / 2).scale(k).translate(-p[0], -p[1]));
  }
  mapInit = true;
}
function zoomTo(box) {
  if (!box) { mapSvg.transition().duration(RM ? 0 : 500).call(mapZoom.transform, d3.zoomIdentity); return; }
  const [x0, y0] = mapProj([box[0], box[3]]), [x1, y1] = mapProj([box[2], box[1]]);
  const k = Math.min(60, 0.92 / Math.max((x1 - x0) / mapW, (y1 - y0) / mapH));
  const t = d3.zoomIdentity.translate(mapW / 2, mapH / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
  mapSvg.transition().duration(RM ? 0 : 600).call(mapZoom.transform, t);
}
function mapTip(i) {
  const m = METRICS.find(x => x.k === mapMetric);
  const val = m.type === "tier" ? tierOf(i) : m.type === "lead" ? (m.get(i) || "no clear change-bloc lead") : (isArab(i) && VALUE_METRICS.has(m.k)) ? "not ranked (Arab locality)" : m.fmt(m.get(i));
  return `<b>${esc(L.en[i])}</b> <span class="he" dir="rtl">${esc(L.he[i])}</span><div style="opacity:.8">${esc(SEG_LABEL[L.seg[i]])} · ${fmtInt(L.elig[i])} eligible</div>
  <div class="r"><span>${esc(m.label)}</span><span>${esc(val)}</span></div>
  <div class="r"><span>2026 change / NB</span><span>${pct(L.pch[i])} / ${pct(L.pnb[i])}</span></div>
  ${isArab(i) ? "" : `<div class="r"><span>Potential</span><span>${fmtNV(ov("potential", i))}</span></div>`}
  <div class="r"><span>Tier</span><span>${esc(tierOf(i))}</span></div>${L.disp[i] ? `<div style="margin-top:4px">Displaced: ${esc(L.disp[i])}</div>` : ""}${L.lowc[i] ? `<div style="margin-top:4px">Low confidence: ${esc(L.lowc[i])}</div>` : ""}${L.excl[i] ? `<div style="margin-top:4px">Not targeted: ${esc(L.excl[i])}</div>` : ""}`;
}
const visible = i => mapSegs.has(L.seg[i]) && L.elig[i] >= mapMin;
function legendHtml(sc) {
  const m = sc.m;
  if (m.type === "tier") return `<div class="lab">${m.label}</div><div class="cat">` + TIERS.map(t => { const st = TIER_STYLE[t]; return `<span><i class="${st.fill ? "" : "ring"}" style="${st.fill ? `background:var(${st.fill})` : `border:2px ${st.dash ? "dashed" : "solid"} var(${st.ring})`}"></i>${t}</span>`; }).join("") + `</div>`;
  if (m.type === "lead") return `<div class="lab">${m.label}</div><div class="cat">` + Object.keys(LEAD_VAR).map(l => `<span><i style="background:var(${LEAD_VAR[l]})"></i>${l}</span>`).join("") + `<span><i style="background:var(--t-low)"></i>Arab or under 15% change</span></div>`;
  if (m.type === "div") {
    const left = m.k === "lean26" ? "Netanyahu bloc" : "Right", right = m.k === "lean26" ? "Change bloc" : "Centre-left";
    return `<div class="lab">${m.label}</div><div class="bar">${sc.cols.map(c => `<span style="background:${c}"></span>`).join("")}</div><div class="ticks"><span>${left} +50</span><span>even</span><span>${right} +50</span></div><div class="ticks"><span>bins at ±8, ±25, ±50 pts</span></div>`;
  }
  const fm = m.k === "swing" || m.k === "rescue" || m.k === "tres" ? (x => pct(x, m.k === "tres" ? 0 : 1)) : (x => fmtNV(x));
  const n = sc.cols.length + 1;
  return `<div class="lab">${m.label} <span class="muted">(quantile bins${VALUE_METRICS.has(m.k) ? "; Arab localities not ranked" : ""})</span></div><div class="bar"><span style="background:var(--t-low)"></span>${sc.cols.map(c => `<span style="background:${c}"></span>`).join("")}</div><div class="ticks pos"><span style="left:${100 / n}%;transform:translateX(-50%)">0</span>${sc.th.map((t, k) => `<span style="left:${100 * (k + 2) / n}%;transform:translateX(-50%)">${fm(t)}</span>`).join("")}</div>`;
}
function renderMap() {
  if (!mapInit) initMap(false);
  document.getElementById("mapmetrics").innerHTML = METRICS.map(m => `<button type="button" data-k="${m.k}" aria-pressed="${m.k === mapMetric}"><span>${m.label}</span><small>${m.sub}</small></button>`).join("");
  document.querySelectorAll("#mapmetrics button").forEach(b => b.addEventListener("click", () => { mapMetric = b.dataset.k; store.set("mapMetric", mapMetric); renderMap(); const nb = document.querySelector(`#mapmetrics button[data-k="${mapMetric}"]`); if (nb) nb.focus(); }));
  document.getElementById("mapsegs").innerHTML = `<button type="button" data-s="__all">All</button><button type="button" data-s="__none">None</button>` + SEG_ORDER.map(s => `<button type="button" data-s="${s}" aria-pressed="${mapSegs.has(s)}">${esc(SEG_LABEL[s])}</button>`).join("");
  document.querySelectorAll("#mapsegs button").forEach(b => b.addEventListener("click", () => {
    const s = b.dataset.s;
    if (s === "__all") mapSegs = new Set(SEG_ORDER); else if (s === "__none") mapSegs = new Set(); else { mapSegs.has(s) ? mapSegs.delete(s) : mapSegs.add(s); }
    store.set("mapSegs", [...mapSegs]); renderMap();
    const nb = document.querySelector(`#mapsegs button[data-s="${s}"]`); if (nb) nb.focus();
  }));
  document.getElementById("mapsize").value = String(mapMin);
  const vis = ALL.filter(visible);
  const sc = colorScale(mapMetric, vis);
  const m = sc.m, ring = css("--dot-ring");
  mapCircles.each(function (i) {
    const el = d3.select(this);
    let fill, stroke = ring, sw = 0.7, dash = null;
    if (m.type === "tier") {
      const st = TIER_STYLE[tierOf(i)] || {};
      if (st.fill) fill = css(st.fill); else { fill = "transparent"; stroke = css(st.ring); sw = 1.8; dash = st.dash ? "2 2" : null; }
    } else fill = sc.f(m.get(i));
    el.attr("fill", fill).attr("stroke", stroke).attr("stroke-width", sw).attr("stroke-dasharray", dash).attr("fill-opacity", 0.95).style("display", visible(i) ? null : "none");
  });
  if (mapSel != null) mapCircles.filter(i => i === mapSel).raise().attr("stroke", css("--ink")).attr("stroke-width", 2.6).attr("stroke-dasharray", null);
  const lg = legendHtml(sc);
  document.getElementById("maplegend").innerHTML = lg + (OBJ !== "change_govt" && (m.type === "tier" || m.k === "potential" || m.k === "eff") ? `<div class="muted" style="margin-top:4px">Objective: ${esc(OBJ_SHORT[OBJ])}</div>` : "");
  document.getElementById("maplegend-float").innerHTML = `<div class="legend">${lg}</div>`;
  renderMapSel();
}
function selectLoc(i) {
  mapSel = i;
  renderMap();
  if (window.innerWidth < 960) document.getElementById("mapsel").scrollIntoView({ behavior: RM ? "auto" : "smooth", block: "nearest" });
}
function renderMapSel() {
  const box = document.getElementById("mapsel");
  if (mapSel == null) { box.innerHTML = `<p class="muted" style="font-size:13px;margin-top:16px">Select a locality on the map or search for one.</p>`; return; }
  const i = mapSel;
  box.innerHTML = `<div class="selcard"><div class="lab">${esc(SEG_LABEL[L.seg[i]])}</div><h3>${esc(L.en[i])} <span class="he muted" dir="rtl" style="font-size:16px">${esc(L.he[i])}</span></h3>
  <div style="margin-top:8px">${tierChip(tierOf(i))}${flags(i)}</div>
  <dl class="kv"><dt>Eligible voters (2022)</dt><dd>${fmtInt(L.elig[i])}</dd><dt>Turnout 2022, regular stations</dt><dd>${pct(L.t22[i])}</dd>
  <dt>2026: change / NB / Arab lists</dt><dd>${pct(L.pch[i])} / ${pct(L.pnb[i])} / ${pct(L.par[i])}</dd>
  ${leadOK(i) ? `<dt>Lead change list</dt><dd>${esc(L.lead[i])}</dd>` : ""}
  ${isArab(i) ? `<dt>Rank</dt><dd>not ranked</dd>` : `<dt>Potential, net votes</dt><dd>${fmtNV(ov("potential", i))}</dd><dt>of which door / lists</dt><dd>${fmtNV(ov("area_pot", i))} / ${fmtNV(ov("list_pot", i))}</dd>
  <dt>Rank by potential</dt><dd>${ov("rank", i) == null ? "not ranked" : "#" + fmtInt(ov("rank", i))}</dd>`}</dl>
  ${isArab(i) ? "" : `<div style="margin-top:10px">${mixBar(ov("gotv_pot", i), ov("pers_pot", i), ov("resc_pot", i), true)}</div>`}
  <p style="margin-top:12px"><a class="btn primary" href="#loc-${L.id[i]}">Full profile →</a></p></div>`;
}
function findLoc(q) {
  const n = norm(q);
  if (!n) return null;
  const byE = i => norm(L.en[i]), byH = i => norm(L.he[i]);
  const bigFirst = ALL.slice().sort((a, b) => L.elig[b] - L.elig[a]);
  return bigFirst.find(i => byE(i) === n || byH(i) === n) ?? bigFirst.find(i => byE(i).startsWith(n) || byH(i).startsWith(n)) ?? bigFirst.find(i => byE(i).includes(n) || byH(i).includes(n)) ?? null;
}
function setupMapControls() {
  document.getElementById("mappresets").innerHTML = PRESETS.map((p, k) => `<button type="button" data-k="${k}">${p[0]}</button>`).join("");
  document.querySelectorAll("#mappresets button").forEach(b => b.addEventListener("click", () => zoomTo(PRESETS[+b.dataset.k][1])));
  document.getElementById("zin").addEventListener("click", () => mapSvg.transition().duration(250).call(mapZoom.scaleBy, 1.8));
  document.getElementById("zout").addEventListener("click", () => mapSvg.transition().duration(250).call(mapZoom.scaleBy, 1 / 1.8));
  document.getElementById("mapsize").addEventListener("change", e => { mapMin = +e.target.value; store.set("mapMin", mapMin); renderMap(); });
  const dl = document.getElementById("locnames");
  dl.innerHTML = ALL.slice().sort((a, b) => L.elig[b] - L.elig[a]).map(i => `<option value="${esc(L.en[i])}">${esc(L.he[i])}</option>`).join("");
  const inp = document.getElementById("mapsearch"), msg = document.getElementById("mapsearch-msg");
  const run = () => {
    const q = inp.value.trim();
    if (!q) { msg.textContent = ""; return; }
    const i = findLoc(q);
    if (i == null) { msg.textContent = `No locality matches “${q}”.`; return; }
    msg.textContent = L.en[i] === q ? "" : `Showing ${L.en[i]}.`;
    if (!mapSegs.has(L.seg[i])) mapSegs.add(L.seg[i]);
    if (L.elig[i] < mapMin) { mapMin = 0; store.set("mapMin", 0); }
    selectLoc(i);
    const d = 0.06; zoomTo([L.lon[i] - d, L.lat[i] - d, L.lon[i] + d, L.lat[i] + d]);
  };
  inp.addEventListener("change", run);
  inp.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); run(); } });
}

/* ============================================================ RANKINGS */
const COLS = {
  rank: { l: "#", n: 1, get: i => ov("rank", i), f: fmtInt },
  loc: { l: "Locality", get: i => L.en[i], html: i => locName(i), cls: "loc" },
  seg: { l: "Segment", get: i => SEG_LABEL[L.seg[i]], html: i => segChip(L.seg[i]) },
  dist: { l: "District", get: i => L.dist[i] },
  elig: { l: "Eligible 2022", n: 1, get: i => L.elig[i], f: fmtInt },
  pch: { l: "Change bloc 2026", n: 1, get: i => L.pch[i], f: x => pct(x) },
  pnb: { l: "Netanyahu bloc 2026", n: 1, get: i => L.pnb[i], f: x => pct(x) },
  par: { l: "Arab lists 2026", n: 1, get: i => L.par[i], f: x => pct(x) },
  lead: { l: "Lead change list", get: i => leadOK(i) ? L.lead[i] : "", html: i => leadOK(i) ? leadChip(L.lead[i]) : "—" },
  tier: { l: "Tier", get: i => tierOf(i), html: i => tierChip(tierOf(i)) },
  pot: { l: "Potential, net votes", n: 1, get: i => ov("potential", i), f: fmtNV },
  eff: { l: "Net votes per 1,000 contacts", n: 1, get: i => ov("eff1k", i), f: fmtNV },
  area: { l: "Door potential", n: 1, get: i => ov("area_pot", i), f: fmtNV },
  acont: { l: "Door contacts available", n: 1, get: i => ov("area_contacts", i), f: fmtInt },
  aeff: { l: "Per 1,000 door conversations", n: 1, get: i => ov("area_eff1k", i), f: fmtNV },
  list: { l: "List potential", n: 1, get: i => ov("list_pot", i), f: fmtNV },
  lcont: { l: "List contacts available", n: 1, get: i => ov("list_contacts", i), f: fmtInt },
  leff: { l: "Per 1,000 list calls", n: 1, get: i => ov("list_eff1k", i), f: fmtNV },
  chsup: { l: "Change-bloc voters 2026", n: 1, get: i => L.chsup[i], f: fmtInt },
  hr: { l: "Net votes per 100 door-hours", n: 1, get: i => ov("per100h", i), f: x => x.toFixed(2) },
  mix: { l: "Mix", get: i => ov("gotv_pot", i) / Math.max(1e-9, ov("potential", i)), html: i => mixBar(ov("gotv_pot", i), ov("pers_pot", i), ov("resc_pot", i)) },
  persv: { l: "Persuadable voters", n: 1, get: i => L.persv[i], f: fmtInt },
  pers: { l: "Persuadable share", n: 1, get: i => L.pers[i], f: x => pct(x, 1) },
  open: { l: "Openness index", n: 1, get: i => L.open[i], f: x => x.toFixed(2) },
  ppot: { l: "Persuasion potential", n: 1, get: i => ov("pers_pot", i), f: fmtNV },
  swi: { l: "Swing index", n: 1, get: i => L.swi[i], f: fmtInt },
  t22: { l: "Turnout 2022 (regular)", n: 1, get: i => L.t22[i], f: x => pct(x) },
  tres: { l: "Resident turnout est.", n: 1, get: i => L.tres[i], f: x => pct(x) },
  abroad: { l: "Roll abroad est.", n: 1, get: i => L.abroad[i], f: x => pct(x) },
  chabst: { l: "Change voters who abstained 2022 est.", n: 1, get: i => L.chabst[i], f: fmtInt },
  aavg: { l: "Per 1,000 door conversations, every door", n: 1, get: i => ov("area_avg_ve1k", i), f: fmtNV },
  gpot: { l: "Turnout potential", n: 1, get: i => ov("gotv_pot", i), f: fmtNV },
  tui: { l: "Turnout index", n: 1, get: i => L.tui[i], f: fmtInt },
  resc: { l: "B&W + Reservists 2026", n: 1, get: i => L.resc[i], f: x => pct(x, 1) },
  rbw: { l: "Blue & White", n: 1, get: i => L.rbw[i], f: x => pct(x, 1) },
  rres: { l: "Reservists", n: 1, get: i => L.rres[i], f: x => pct(x, 1) },
  rescv: { l: "Rescue voters", n: 1, get: i => L.rescv[i], f: fmtInt },
  rpot: { l: "Rescue potential", n: 1, get: i => ov("resc_pot", i), f: fmtNV },
  rei: { l: "Rescue index", n: 1, get: i => L.rei[i], f: fmtInt },
  bpot: { l: "Blocking potential (deny 61)", n: 1, get: i => L["block_nb.potential"][i], f: fmtNV },
  btier: { l: "Tier, blocking", get: i => tierOf(i, "block_nb"), html: i => tierChip(tierOf(i, "block_nb")) },
  bgpot: { l: "Turnout potential, blocking", n: 1, get: i => L["block_nb.gotv_pot"][i], f: fmtNV },
};
const VIEWS = [
  { k: "overall", l: "Overall", cols: ["rank", "loc", "seg", "elig", "pch", "lead", "tier", "pot", "eff", "mix"], sort: "pot", desc: "All programmes under the selected objective. Potential is the saturation total: door conversations on positive polling-station areas plus calls to identified voters elsewhere. Efficiency is net votes per 1,000 completed contacts." },
  { k: "door", l: "Door canvass", cols: ["loc", "seg", "elig", "pch", "t22", "tres", "area", "acont", "aeff", "aavg", "hr"], sort: "area", desc: "Door teams on polling-station areas where one conversation (turnout and persuasion together) has positive value under the selected objective. 'Every door' shows what untargeted canvassing of the whole locality would net." },
  { k: "lists", l: "Supporter lists", cols: ["loc", "seg", "elig", "pch", "pnb", "lead", "chsup", "list", "lcont", "leff"], sort: "list", desc: "Calls, texts and friend-to-friend asks to identified voters: change-bloc supporters (turnout) and soft Netanyahu-bloc voters (persuasion) where door canvassing is net negative, and Blue and White or Reservists voters (rescue) anywhere. Assumes 30% identified and half of those reached." },
  { k: "persuasion", l: "Persuasion", cols: ["loc", "seg", "elig", "pnb", "persv", "pers", "open", "ppot", "swi"], sort: "persv", desc: "Where the soft, cross-pressured Netanyahu-bloc voters are. Openness is the out-of-sample-validated index of past cross-camp movement, soft-right footprint and bloc balance (1 = national average)." },
  { k: "turnout", l: "Turnout", cols: ["loc", "seg", "elig", "pch", "t22", "tres", "abroad", "chabst", "gpot", "tui"], sort: "gpot", desc: "Turnout potential from door and supporter-list work. Resident turnout adds back double-envelope votes and removes residents abroad. Abstainers: 2021 change-camp voters estimated to have stayed home in 2022 (Kolot Nodedim rates)." },
  { k: "rescue", l: "Rescue", cols: ["loc", "seg", "elig", "resc", "rbw", "rres", "rescv", "rpot", "rei"], sort: "rescv", desc: "Projected Blue and White and Reservists voters. Both lists are likely below the threshold. Rescue is mainly a media and list-call programme; this view shows where those voters live." },
  { k: "blocking", l: "Blocking", cols: ["loc", "seg", "elig", "par", "pnb", "bpot", "bgpot", "btier"], sort: "bpot", desc: "Value for denying Netanyahu a 61-seat majority, whatever the objective selected above, outside Arab localities. Arab localities are not ranked: any Arab-sector turnout work is a leadership decision, independent, transparent and cleared by election counsel." },
  { k: "councils", l: "Regional councils", cols: [], sort: "pot", desc: "Localities grouped by regional council, for planning field teams across dispersed kibbutzim, moshavim and community settlements. Select a council to list its localities." },
  { k: "efficiency", l: "Per volunteer-hour", cols: ["loc", "seg", "elig", "pch", "aeff", "hr", "pot", "tier"], sort: "hr", desc: "Net votes per 100 door-hours, using assumed completed conversations per hour by turf: 4 in dense apartment blocks, 3 in other urban turf, 2 in rural communities, 1.5 in Bedouin villages." },
];
let rkView = store.get("rkView", "overall"), rkSort = null, rkDir = -1, rkRows = [], rkCouncil = "", rkCouncilRows = [], rkPrevSize = null;
if (!VIEWS.some(v => v.k === rkView)) rkView = "overall";
function setupRankings() {
  const sel = (id, opts) => { document.getElementById(id).innerHTML = opts.map(o => `<option value="${esc(o[0])}">${esc(o[1])}</option>`).join(""); };
  sel("rk-seg", [["", "All segments"]].concat(SEG_ORDER.map(s => [s, SEG_LABEL[s]])));
  sel("rk-dist", [["", "All districts"]].concat([...new Set(L.dist)].filter(Boolean).sort().map(d => [d, d])));
  sel("rk-tier", [["", "All tiers"]].concat(TIERS.filter(t => t !== "Arab-list turf (partner-led)" && t !== "Not targeted (access)").map(t => [t, t])));
  sel("rk-seg", [["", "All segments"]].concat(SEG_ORDER.filter(x => !x.startsWith("arab")).map(x => [x, SEG_LABEL[x]])));
  ["rk-search", "rk-seg", "rk-dist", "rk-tier", "rk-size"].forEach(id => document.getElementById(id).addEventListener(id === "rk-search" ? "input" : "change", () => renderRankings()));
  document.getElementById("rk-copy").addEventListener("click", copyCSV);
}
function renderCouncils() {
  const t = document.getElementById("rk-table");
  const q = norm(document.getElementById("rk-search").value);
  t.classList.add("static");
  rkCouncilRows = d3.rollups(ALL.filter(i => isTarget(i) && /Regional Council/.test(L.council[i] || "")), v => ({
    n: v.length, elig: d3.sum(v, i => L.elig[i]), pot: d3.sum(v, i => ov("potential", i)),
    g: d3.sum(v, i => ov("gotv_pot", i)), p: d3.sum(v, i => ov("pers_pot", i)), r: d3.sum(v, i => ov("resc_pot", i)),
    pch: d3.sum(v, i => L.pch[i] * L.elig[i]) / Math.max(1, d3.sum(v, i => L.elig[i])),
    top: v.slice().sort((a, b) => ov("potential", b) - ov("potential", a)).slice(0, 3),
  }), i => L.council[i]).filter(([c]) => !q || norm(c).includes(q)).sort((a, b) => b[1].pot - a[1].pot);
  document.getElementById("rk-count").textContent = `${rkCouncilRows.length} regional council${rkCouncilRows.length === 1 ? "" : "s"}`;
  t.innerHTML = `<thead><tr><th scope="col">Regional council</th><th scope="col" class="n">Localities</th><th scope="col" class="n">Eligible</th><th scope="col" class="n">Change bloc 2026</th><th scope="col" class="n">Potential, net votes</th><th scope="col">Mix</th><th scope="col">Top localities</th></tr></thead><tbody>` +
    rkCouncilRows.map(([c, a]) => `<tr><td><button type="button" class="btn" data-council="${esc(c)}" style="min-height:28px;padding:2px 8px;text-align:start">${esc(c)}</button></td><td class="n">${a.n}</td><td class="n">${fmtInt(a.elig)}</td><td class="n">${pct(a.pch)}</td><td class="n">${fmtNV(a.pot)}</td><td>${mixBar(a.g, a.p, a.r)}</td><td style="white-space:normal">${a.top.map(i => `<a href="#loc-${L.id[i]}">${esc(L.en[i])}</a>`).join(", ")}</td></tr>`).join("") + "</tbody>";
  t.querySelectorAll("button[data-council]").forEach(b => b.addEventListener("click", () => {
    rkCouncil = b.dataset.council; rkView = "overall"; rkSort = null; rkPrevSize = document.getElementById("rk-size").value; document.getElementById("rk-size").value = "0"; renderRankings();
    const h = document.querySelector("#rk-views button[aria-pressed=true]"); if (h) h.focus();
  }));
}
function renderRankings(focusCol) {
  const cbx = document.querySelector("#p-rankings textarea.copybox"); if (cbx) cbx.remove();
  const view = VIEWS.find(v => v.k === rkView) || VIEWS[0];
  document.getElementById("rk-views").innerHTML = VIEWS.map(v => `<button type="button" data-k="${v.k}" aria-pressed="${v.k === view.k}">${v.l}</button>`).join("");
  document.querySelectorAll("#rk-views button").forEach(b => b.addEventListener("click", () => { rkView = b.dataset.k; rkSort = null; store.set("rkView", rkView); renderRankings(); const nb = document.querySelector(`#rk-views button[data-k="${rkView}"]`); if (nb) nb.focus(); }));
  const mixLegend = view.cols.includes("mix") || view.k === "councils" ? ` <span class="legend-inline" style="display:inline-flex;margin:0 0 0 6px">Mix: <span><i class="sq" style="background:var(--c-gotv)"></i>turnout</span><span><i class="sq" style="background:var(--c-pers)"></i>persuasion</span><span><i class="sq" style="background:var(--c-resc)"></i>rescue</span></span>` : "";
  document.getElementById("rk-desc").innerHTML = esc(view.desc) + mixLegend + (rkCouncil && view.k !== "councils" ? ` <b>Showing ${esc(rkCouncil)}.</b> <button type="button" class="btn" id="rk-clearc" style="min-height:28px;padding:2px 8px;margin-inline-start:6px">Show all</button>` : "");
  const cb = document.getElementById("rk-clearc"); if (cb) cb.addEventListener("click", () => { rkCouncil = ""; if (rkPrevSize != null) { document.getElementById("rk-size").value = rkPrevSize; rkPrevSize = null; } renderRankings(); const h = document.querySelector("#rk-views button[aria-pressed=true]"); if (h) h.focus(); });
  if (view.k === "councils") { rkCouncil = ""; renderCouncils(); return; }
  document.getElementById("rk-table").classList.remove("static");
  const q = norm(document.getElementById("rk-search").value);
  const seg = document.getElementById("rk-seg").value, dist = document.getElementById("rk-dist").value, tier = document.getElementById("rk-tier").value;
  const min = +document.getElementById("rk-size").value;
  const sortKey = rkSort || view.sort;
  const sc = COLS[sortKey];
  rkRows = ALL.filter(i => isTarget(i) && L.elig[i] >= min && (!seg || L.seg[i] === seg) && (!dist || L.dist[i] === dist) && (!tier || tierOf(i) === tier) && (!rkCouncil || L.council[i] === rkCouncil) &&
    (!q || norm(L.en[i]).includes(q) || norm(L.he[i]).includes(q)));
  const dir = rkSort ? rkDir : (sortKey === "rank" ? 1 : -1);
  rkRows.sort((a, b) => { const x = sc.get(a), y = sc.get(b); return (typeof x === "string" ? String(x).localeCompare(y) : ((x ?? -1e9) - (y ?? -1e9))) * dir; });
  document.getElementById("rk-count").textContent = `${fmtInt(rkRows.length)} of ${fmtInt(ALL.filter(isTarget).length)} ranked localities`;
  const t = document.getElementById("rk-table");
  t.innerHTML = `<thead><tr>${view.cols.map(c => `<th scope="col" class="${COLS[c].n ? "n" : ""}" ${c === sortKey ? `aria-sort="${dir < 0 ? "descending" : "ascending"}"` : ""}><button type="button" class="sb" data-c="${c}">${COLS[c].l}</button></th>`).join("")}</tr></thead><tbody>` +
    rkRows.slice(0, 400).map(i => `<tr data-id="${L.id[i]}">${view.cols.map(c => { const cc = COLS[c]; return `<td class="${cc.n ? "n" : ""} ${cc.cls || ""}">${cc.html ? cc.html(i) : esc(cc.f ? cc.f(cc.get(i)) : cc.get(i))}</td>`; }).join("")}</tr>`).join("") + `</tbody>`;
  if (rkRows.length > 400) t.insertAdjacentHTML("beforeend", `<tfoot><tr><td colspan="${view.cols.length}" class="muted" style="padding:10px">Showing the first 400 rows. Narrow the filters or copy the full view as CSV.</td></tr></tfoot>`);
  if (!rkRows.length) t.insertAdjacentHTML("beforeend", `<tfoot><tr><td colspan="${view.cols.length}" class="muted" style="padding:10px">No locality matches these filters.</td></tr></tfoot>`);
  t.querySelectorAll("th button.sb").forEach(b => b.addEventListener("click", () => {
    const c = b.dataset.c; if (rkSort === c) rkDir = -rkDir; else { rkSort = c; rkDir = COLS[c].n ? -1 : 1; }
    renderRankings(c);
  }));
  if (focusCol) { const fb = t.querySelector(`th button.sb[data-c="${focusCol}"]`); if (fb) fb.focus(); }
  bindRows(t);
}
// Clipboard writes can be refused inside the artifact frame: fall back to a
// selected text box next to the button so the reader can copy by hand.
function copyText(text, btn, label) {
  const fallback = () => {
    let box = btn.parentElement.querySelector("textarea.copybox");
    if (!box) { box = document.createElement("textarea"); box.className = "copybox"; box.readOnly = true; box.setAttribute("aria-label", "CSV text to copy"); btn.insertAdjacentElement("afterend", box); }
    box.value = text; box.style.cssText = "display:block;width:100%;height:140px;margin-top:8px;font:12px var(--f-mono);background:var(--panel);color:var(--ink);border:2px solid var(--ink)";
    box.focus(); box.select();
    btn.textContent = "Select all and copy below";
    setTimeout(() => btn.textContent = label, 3000);
  };
  try {
    navigator.clipboard.writeText(text).then(() => { btn.textContent = "Copied"; setTimeout(() => btn.textContent = label, 1800); }, fallback);
  } catch (e) { fallback(); }
}
function toCSV(lines) { return lines.map(r => r.map(x => { const s = String(x == null ? "" : x); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }).join(",")).join("\n"); }
function copyCSV() {
  const view = VIEWS.find(v => v.k === rkView) || VIEWS[0];
  let lines;
  if (view.k === "councils") {
    lines = [["Regional council", "Localities", "Eligible", "Change bloc 2026", "Potential (net votes)", "Turnout", "Persuasion", "Rescue", "Top localities"]]
      .concat(rkCouncilRows.map(([c, a]) => [c, a.n, a.elig, +a.pch.toFixed(4), +a.pot.toFixed(2), +a.g.toFixed(2), +a.p.toFixed(2), +a.r.toFixed(2), a.top.map(i => L.en[i]).join("; ")]));
  } else {
    const cols = view.cols.filter(c => c !== "loc" && c !== "mix");
    lines = [["Locality (English)", "Locality (Hebrew)", "CBS code"].concat(cols.map(c => COLS[c].l), ["Objective"])]
      .concat(rkRows.map(i => [L.en[i], L.he[i], L.id[i]].concat(cols.map(c => { const x = COLS[c].get(i); return typeof x === "number" ? +x.toFixed(4) : x; }), [OBJ_SHORT[OBJ]])));
  }
  copyText(toCSV(lines), document.getElementById("rk-copy"), "Copy as CSV");
}

/* ============================================================ LOCALITY PROFILE */
const PARTY_CAMP = { Likud: "nb", Yashar: "ch", Together: "ch", Democrats: "ch", "Yisrael Beytenu": "ch", Shas: "nb", UTJ: "nb", Otzma: "nb", "RZP-Zehut": "nb", "Ra'am": "ar", "Joint List": "ar", "Blue & White": "un", Reservists: "un", Amcha: "nb" };
const CAMP_VAR = { ch: "--c-change", nb: "--c-nb", ar: "--c-arab", un: "--c-una" };
const KV_IDX = { change_govt: 8, block_nb: 11, change_seats: 12 };
function nScen() { const lab = (D.sensitivity || {}).labels; return lab ? Object.keys(lab).length - 1 : 0; }
function renderLoc(id) {
  const i = IDX.get(+id);
  const root = document.getElementById("loc-root");
  if (i == null) { root.innerHTML = `<div class="pagehead"><h1>Locality not found</h1><p class="lede"><a href="#rankings">Back to the rankings</a></p></div>`; return; }
  const seg = L.seg[i], tier = tierOf(i);
  const pot = ov("potential", i), g = ov("gotv_pot", i), p = ov("pers_pot", i), r = ov("resc_pot", i);
  const segC = (C.segments || []).find(s => s.segment === seg);
  const k = D.kalpi[String(L.id[i])];
  const notes = [];
  if (L.excl[i]) notes.push(`<b>Not targeted:</b> ${esc(L.excl[i])}. Access is restricted, or most residents are not Israeli citizens and voting in Knesset elections carries a social cost there, so the atlas does not plan field work here.`);
  if (L.disp[i]) notes.push(`<b>Displaced residents (${esc(L.disp[i])}):</b> many residents may not be living at home. Door capacity is halved; confirm who has returned before sending teams, and reach the rest by phone.`);
  if (L.lowc[i]) notes.push(`<b>Low confidence:</b> ${esc(L.lowc[i])}. The 2022 vote here followed home-village candidates, so the projection depends on which lists placed ${CIRC.has(L.id[i]) ? "Circassian" : "Druze"} candidates in winnable slots. Check the filed CEC lists and run a community poll before committing volunteers.`);
  if (L.phantom[i] >= 0.03) notes.push(`<b>Roll check:</b> regular-station turnout here sits well below similar towns, a sign that about ${pct(L.phantom[i])} of the roll lives elsewhere. Turnout is estimated on the resident base.`);
  if (isArab(i)) notes.push(`<b>Arab locality:</b> the atlas makes no change-bloc field recommendation here and publishes no town-level targeting values. Whether to support Arab turnout is a leadership decision; any support should be independent, transparent and cleared by election counsel.`);
  root.innerHTML = `
  <div class="pagehead">
    <div class="eyebrow"><a href="#rankings" style="text-decoration:none">← Rankings</a> · <a href="#map" style="text-decoration:none">Map</a> · Locality profile · CBS code ${L.id[i]}</div>
    <div class="prof-head"><div><h1>${esc(L.en[i])}</h1><div class="hen" dir="rtl" lang="he">${esc(L.he[i])}</div></div>
      <div style="text-align:end">${ov("rank", i) == null ? `<div class="lab">Rank</div><div style="font-size:22px;font-weight:700;line-height:1.2">Not ranked</div><div class="muted" style="font-size:12.5px;margin-top:4px">${isArab(i) ? "Arab locality: leadership decision" : "Not targeted"}</div>` : `<div class="lab">Rank by potential · ${esc(D.objectives[OBJ])}</div><div style="font-size:40px;font-weight:700;line-height:1">#${fmtInt(ov("rank", i))}<span class="muted" style="font-size:16px;font-weight:500"> of ${fmtInt(ALL.filter(isTarget).length)}</span></div>${rankRange(i)}`}</div></div>
    <div class="prof-meta">${tierChip(tier)} ${segChip(seg)} <span class="chip segchip">${esc(L.dist[i] || "")} district</span> ${L.council[i] ? `<span class="chip segchip">${esc(L.council[i])}</span>` : ""} ${leadOK(i) ? `<span class="chip segchip">Lead change list: ${esc(L.lead[i])}${L.lead2[i] ? " · then " + esc(L.lead2[i]) : ""}</span>` : ""}</div>
    ${notes.map(n => `<div class="callout">${n}</div>`).join("")}
  </div>
  <div class="tiles">
    <div class="tile"><div class="k">Eligible voters</div><div class="v">${fmtInt(L.elig[i])}</div><div class="d">2022 roll · about ${fmtInt(L.elig26[i])} in 2026</div></div>
    <div class="tile"><div class="k">Turnout 2022</div><div class="v">${pct(L.t22[i])}</div><div class="d">Regular stations. Resident estimate ${pct(L.tres[i])}, with double envelopes added back and about ${pct(L.abroad[i])} of the roll treated as living elsewhere.</div></div>
    <div class="tile"><div class="k">2026 projection</div><div class="v">${pct(L.pch[i])}</div><div class="d">Change bloc. Netanyahu bloc ${pct(L.pnb[i])}, Arab lists ${pct(L.par[i])}, unaligned ${pct(L.pun[i])}.</div></div>
    ${isArab(i) || L.excl[i] ? `<div class="tile"><div class="k">Field programme</div><div class="v" style="font-size:26px">None planned</div><div class="d">${isArab(i) ? "Arab-sector turnout is a leadership decision. The atlas publishes no town-level targeting values for Arab localities." : "Not targeted for access reasons."}</div></div>` : `<div class="tile"><div class="k">Potential</div><div class="v">${fmtNV(pot)}</div><div class="d">Net votes at saturation: ${fmtNV(ov("area_pot", i))} from door work, ${fmtNV(ov("list_pot", i))} from list calls. ${fmtNV(ov("eff1k", i))} per 1,000 contacts.</div></div>`}
  </div>
  <section class="block"><div class="grid2">
    <div class="card"><h3>${isArab(i) || L.excl[i] ? "Why there is no programme" : "Why it ranks here"}</h3><p class="why">${whyText(i)}</p>
      ${isArab(i) || L.excl[i] ? "" : `<div style="margin-top:14px">${mixBar(g, p, r, true)}</div>
      <div class="legend-inline"><span><i class="sq" style="background:var(--c-gotv)"></i>Turnout ${fmtNV(g)}</span><span><i class="sq" style="background:var(--c-pers)"></i>Persuasion ${fmtNV(p)}</span><span><i class="sq" style="background:var(--c-resc)"></i>Rescue calls ${fmtNV(r)}</span></div>
      <p class="note">Effect on the objective at saturation: ${dpText(pot)}. Net votes are vote-equivalents for an average change-bloc list under the objective selected at the top.</p>`}
    </div>
    ${isArab(i) ? `<div class="card"><h3>About this locality</h3><dl class="kv" style="margin-top:10px"><dt>Arab lists, 2026 projection</dt><dd>${pct(L.par[i])}</dd><dt>Turnout 2022, regular stations</dt><dd>${pct(L.t22[i])}</dd><dt>Change bloc, 2026 projection</dt><dd>${pct(L.pch[i])}</dd></dl></div>` : `<div class="card"><h3>Indices</h3><p class="sub">Percentile rank among all ${fmtInt(N)} localities (100 = highest).</p>
      ${[["Swing", L.swi[i], "persuadable and rescue density"], ["Turnout", L.tui[i], "net votes per turnout conversation on the best stations"], ["Rescue", L.rei[i], "share of Blue and White + Reservists votes"], ["Impact", L.imi[i], "total potential, change-led government"]].map(x => `<div class="idx"><span>${x[0]} <span class="muted" style="font-size:11.5px;display:block">${x[2]}</span></span><span class="track" role="img" aria-label="${x[0]} index ${x[1]}"><span style="width:${x[1]}%"></span></span><span class="val">${x[1]}</span></div>`).join("")}
      <dl class="kv" style="margin-top:16px">
        <dt>Persuadable voters</dt><dd>${fmtInt(L.persv[i])} (${pct(L.pers[i], 1)})</dd>
        <dt>Openness (1 = national average)</dt><dd>${L.open[i] != null ? L.open[i].toFixed(2) : "—"}</dd>
        <dt>Blue & White / Reservists 2026</dt><dd>${pct(L.rbw[i], 1)} / ${pct(L.rres[i], 1)}</dd>
        <dt>Change-camp abstainers 2021→22, est.</dt><dd>${fmtInt(L.chabst[i])}</dd>
        <dt>Turnout lift per door conversation</dt><dd>${L.lift[i] != null ? L.lift[i].toFixed(2) + " pts" : "—"}</dd>
        <dt>Door conversations per hour (assumed)</dt><dd>${L.cph[i] != null ? L.cph[i].toFixed(1) : "—"}</dd>
      </dl></div>`}
  </div></section>
  <section class="block"><div class="grid2">
    <div class="card"><h3>Vote by camp, 2013–2022</h3><p class="sub">Share of valid votes at regular stations. Change camp = centre-left and anti-Netanyahu lists of each election; right = Likud, haredi and religious-Zionist lists.</p><div id="lc-camp"></div><div class="legend-inline"><span><i style="background:var(--c-change)"></i>Change camp</span><span><i style="background:var(--c-nb)"></i>Right camp</span><span><i style="background:var(--c-arab)"></i>Arab lists</span></div></div>
    <div class="card"><h3>Turnout, 2013–2022</h3><p class="sub">Regular stations only, so lower than official turnout. Dashed line: national figure on the same basis.</p><div id="lc-turn"></div></div>
  </div></section>
  <section class="block"><div class="grid2">
    <div class="card"><h3>2026 projection by list</h3><p class="sub">2022 vote carried through the 2022→2026 flows, blended with uniform camp swing and raked to the national forecast of ${fmtDate(S.asof)}.</p><div id="lc-proj"></div></div>
    <div class="card"><h3>What to do here</h3>${recoHtml(i, segC)}</div>
  </div></section>
  ${stationSection(i, k)}
  <section class="block"><div class="card"><h3>Who lives here</h3><p class="sub">CBS 2022 census and locality file. Used for segmentation and context, not for the vote projection.</p>
    <dl class="kv" style="max-width:520px">
      <dt>Population (2023)</dt><dd>${fmtInt(L.pop[i])}</dd><dt>Median age</dt><dd>${L.age[i] ?? "—"}</dd>
      <dt>Academic degree</dt><dd>${L.acad[i] != null ? L.acad[i] + "%" : "—"}</dd><dt>Born in Europe incl. former USSR</dt><dd>${L.eur[i] != null ? L.eur[i] + "%" : "—"}</dd>
      <dt>Born in Asia or Africa</dt><dd>${L.asaf[i] != null ? L.asaf[i] + "%" : "—"}</dd><dt>Most common household religiosity</dt><dd>${esc(L.relig[i] || "—")}</dd>
      <dt>Distance to Tel Aviv</dt><dd>${L.km[i] != null ? L.km[i] + " km" : "—"}</dd><dt>Settlement type</dt><dd>${esc((L.stype[i] || "").replace(/_/g, " "))}</dd>
    </dl></div></section>`;
  lineChart(document.getElementById("lc-camp"), [
    { name: "Change", color: css("--c-change"), values: H.C[i] }, { name: "Right", color: css("--c-nb"), values: H.R[i] }, { name: "Arab", color: css("--c-arab"), values: H.A[i] },
  ], { x: H.cycles, yDomain: [0, 1], yFmt: x => pct(x), aria: "Camp vote shares over time" });
  const natT = S.national.map(n => n.turnout_regular);
  const tv = H.turnout[i].filter(x => x != null);
  lineChart(document.getElementById("lc-turn"), [
    { name: L.en[i].length > 12 ? L.en[i].slice(0, 11) + "…" : L.en[i], color: css("--accent"), values: H.turnout[i] }, { name: "National", color: css("--muted"), values: natT, dash: "4 3" },
  ], { x: H.cycles, yDomain: [Math.min(0.3, (d3.min(tv) ?? 0.5) - 0.05), Math.max(0.9, (d3.max(tv) ?? 0.8) + 0.03)], yFmt: x => pct(x), aria: "Turnout over time" });
  const proj = D.lists.map((n, kk) => ({ n, v: L.p26[i][kk], c: PARTY_CAMP[n] })).filter(x => x.v >= 0.002).sort((a, b) => b.v - a.v);
  hbars(document.getElementById("lc-proj"), proj.map(x => ({ label: x.n, parts: [{ v: x.v, color: css(CAMP_VAR[x.c]), name: { ch: "Change bloc", nb: "Netanyahu bloc", ar: "Arab list", un: "Unaligned" }[x.c] }], total: x.v })),
    { labelW: 140, rowH: 20, valFmt: x => pct(x, 1), totFmt: x => pct(x, 1), tickFmt: x => pct(x), aria: "Projected 2026 vote by list" });
  if (k && !isArab(i) && !L.excl[i]) renderKalpi(i, k);
}
function rankRange(i) {
  const o = OBJ === "block_nb" ? "block_nb" : "change_govt";
  const a = L[o + ".rmin"], b = L[o + ".rmax"];
  if (!a || a[i] == null) return "";
  return `<div class="muted" style="font-size:12.5px;margin-top:6px">Range across ${nScen()} alternative assumption sets: #${a[i]}–#${b[i]}${OBJ === "change_seats" ? " (change-led government)" : ""}</div>`;
}
function whyText(i) {
  const pot = ov("potential", i), g = ov("gotv_pot", i), p = ov("pers_pot", i), r = ov("resc_pot", i);
  const name = esc(L.en[i]), parts = [];
  if (L.excl[i]) return `${name} is not targeted (${esc(L.excl[i])}).`;
  if (isArab(i)) {
    parts.push(`${name} is an Arab locality: Arab lists take about ${pct(L.par[i])} of its projected vote.`);
    parts.push(`Extra Arab-list votes help deny Netanyahu 61 but, in the formation model, do little for a change-led government, because they mostly turn Netanyahu wins into deadlock. Whether to support Arab turnout at all is a leadership decision; any support should be independent, transparent and cleared by election counsel. The atlas plans no change-bloc work here.`);
    return parts.join(" ");
  }
  if (!(pot > 0.5)) {
    parts.push(`${name} offers little or nothing to gain from field work under this objective (${fmtNV(pot)} net votes at saturation).`);
    if (L.pnb[i] >= 0.6) parts.push(`The Netanyahu bloc takes about ${pct(L.pnb[i])} of its projected vote, so a door conversation mobilises mostly opposing voters.`);
    else if (L.elig[i] < 1500) parts.push(`It is small: ${fmtInt(L.elig[i])} eligible voters.`);
    if (L.chsup[i] >= 300) parts.push(`About ${fmtInt(L.chsup[i])} change-bloc voters live here; reach identified ones by phone or through their own networks.`);
    return parts.join(" ");
  }
  const t = Math.max(1e-9, Math.max(0, g) + Math.max(0, p) + Math.max(0, r));
  const ap = ov("area_pot", i), lp = ov("list_pot", i), avg = ov("area_avg_ve1k", i), best = ov("area_eff1k", i), negs = ov("neg_share", i);
  const split = ap < 0.5 ? `No polling-station area here has positive door value, so it all comes from calls to identified voters.`
    : lp < 0.5 ? `It all comes from door conversations on its positive polling-station areas.`
    : `${fmtNV(ap)} comes from door conversations on its positive polling-station areas and ${fmtNV(lp)} from calls to identified voters.`;
  parts.push(`${name} offers <b>${fmtNV(pot)}</b> net votes at saturation. ${split} By mechanism, turnout is ${pct(Math.max(0, g) / t)}, persuasion ${pct(Math.max(0, p) / t)} and rescue calls ${pct(Math.max(0, r) / t)}.`);
  if (avg > 0 && negs < 0.2) parts.push(`A door conversation has positive value almost everywhere here: about ${fmtNV(avg)} net votes per 1,000 if every door were knocked${best > avg * 1.15 ? `, ${fmtNV(best)} on the best stations` : ""}.`);
  else if (avg > 0) parts.push(`Knocking every door here would still net about ${fmtNV(avg)} per 1,000 door conversations, but the selected stations net ${fmtNV(best)}.`);
  else if (Math.abs(avg) < 0.05) parts.push(`Knocking every door here would net about zero; only the selected stations are positive${best > 0 ? `, at ${fmtNV(best)} per 1,000` : ""}.`);
  else if (ap >= 0.5) parts.push(`Knocking every door here would net votes for the other side (${fmtNV(avg)} per 1,000 door conversations). Only the selected stations are positive, at ${fmtNV(best)} per 1,000.`);
  else parts.push(`Knocking doors here would net votes for the other side (${fmtNV(avg)} per 1,000 door conversations).`);
  if (L.pers[i] > 0.025) parts.push(`About ${pct(L.pers[i], 1)} of its voters (${fmtInt(L.persv[i])}, modelled) are soft Netanyahu-bloc supporters open to a change list; past cross-camp movement here is ${L.open[i] >= 1.1 ? "above" : L.open[i] <= 0.9 ? "below" : "close to"} the national rate.`);
  if (L.resc[i] > 0.025) parts.push(`The Reservists are projected at ${pct(L.resc[i], 1)}, a rescue pool of about ${fmtInt(L.rescv[i])} votes for media and calls.`);
  return parts.join(" ");
}
const CIRC = new Set([508, 540]);
// does a realistic plan (400,000 contacts, with or without lists) send a door team here?
function doorPlanned(i) {
  const SC = scenarios(OBJ);
  return ["400000_0", "400000_" + S.list_identified].some(k => ((SC[k].alloc.get(i) || {}).area || 0) > 0);
}
function recoHtml(i, segC) {
  const tier = tierOf(i);
  const planned = doorPlanned(i);
  const lead = leadOK(i) ? `${L.lead[i]}${L.lead2[i] ? ` (then ${L.lead2[i]})` : ""}` : "";
  let lines = {
    "Turnout engine": ["Canvass only the polling stations with positive door value (below); skip the rest.", lead ? `Split turf by station lead list: ${lead} leads here.` : "", "Move from supporter ID to turnout contact from Sat 17 Oct: vote plans, volunteer calls, friend-to-friend asks.", "On election day, after each CEC release, rank target stations by how far they trail their locality's turnout in the same release and send callers to the bottom fifth."],
    "Supporter-list ground": [planned ? "Door teams only on the positive stations listed below; most stations here are net negative." : "Mostly calls and texts: most stations here are net negative, and the realistic plans send no door team.", `Call, text and ask identified change-bloc supporters (about ${fmtInt(L.chsup[i])} change-bloc voters live here).`, "Recruit relational askers among supporters' own friends, family and neighbours; never through IDF units, unit chat groups or employers."],
    "Persuasion battleground": ["Lead with persuasion in the door conversation on positive stations; call identified soft Netanyahu-bloc voters elsewhere.", "Use credible local messengers: local leaders, former Likud voters, and reservists speaking as civilians only (never on duty, in uniform or with IDF insignia, and never recruited through IDF units, unit chat groups or employers).", lead ? `Lead list for turf: ${lead}.` : ""],
    "Secondary target": ["Use phones, peer-to-peer texts and relational asks rather than door teams.", "Door time only on the best stations, if a team is nearby."],
    "Arab-list turf (partner-led)": ["No change-bloc field programme.", "Arab-sector turnout is a leadership decision. Any support should be independent, transparent and cleared by election counsel, with no change-bloc branding or staff-run GOTV."],
    "Netanyahu-bloc stronghold": [planned ? "Door teams only on the few positive stations listed below; turnout contact elsewhere mobilises mostly Netanyahu-bloc voters." : "No door work: turnout contact here mobilises mostly Netanyahu-bloc voters.", "Calls to identified change-bloc supporters and to identified soft Netanyahu-bloc voters only."],
    "Low yield": L.pch[i] >= 0.5 ? ["Base network: members contact members through their own personal networks, never through the official channels of councils, committees or movements.", planned ? "Texts and calls to identified supporters; the realistic plans also send a door team to the positive stations listed below." : "Texts and calls to identified supporters; no door teams."] : ["National media, digital and SMS; calls to identified supporters only."],
    "Not targeted (access)": [`Not targeted: ${L.excl[i]}.`],
  }[tier].filter(Boolean);
  const held = L.lowc[i] && !isArab(i) && !L.excl[i];
  const comm = CIRC.has(L.id[i]) ? "Circassian" : "Druze";
  if (held) lines.splice(0, lines.length, `Held until the candidate check (filed CEC lists) and a ${comm} community poll.`, `Any work is then led by the ${comm} candidates' own local teams; no outside canvassers.`, lead ? `Provisional lead list: ${lead}.` : "");
  const desc = held ? `${comm} town: held out of the plans until the filed-list check and a community poll. The tier shows its modelled value only.` : (TIER_DESC[tier] || "");
  return `<div class="reco"><h4>${esc(tier)}${held ? " (held)" : ""}</h4><p style="font-size:14px;margin-top:4px;color:var(--ink2)">${esc(desc)}</p><ul>${lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>
  ${segC ? `<h4 style="margin-top:14px">${esc(SEG_LABEL[L.seg[i]])} playbook</h4><p style="font-size:14px;margin-top:4px">${esc(segC.approach)}</p><p style="font-size:14px;margin-top:6px"><b>Message.</b> ${esc(segC.message)}</p><p style="font-size:14px;margin-top:6px"><b>Messenger.</b> ${esc(segC.messenger)}</p><p style="font-size:14px;margin-top:6px"><b>Avoid.</b> ${esc(segC.avoid)}</p>${segC.caveat ? `<p style="font-size:14px;margin-top:6px"><b>Caveat.</b> ${esc(segC.caveat)}</p>` : ""}<p style="margin-top:8px"><a href="#seg-${L.seg[i]}" class="go" style="font:600 11px var(--f-mono);letter-spacing:.1em;text-transform:uppercase;text-decoration:none;color:var(--accent)">Segment playbook →</a></p>` : ""}</div>`;
}
function stationSection(i, k) {
  if (!k) return "";
  if (isArab(i) || L.excl[i]) return `<section class="block"><h2 class="h2">Polling stations</h2><p class="sub">${k.length} polling station${k.length === 1 ? "" : "s"} (2022 numbering). Station targeting is not shown for ${isArab(i) ? "Arab localities: the atlas makes no change-bloc field recommendation there" : "localities that are not targeted"}.</p></section>`;
  const big = k.filter(d => !d[13]).length >= 8;
  // door label follows the realistic plans, not the tier
  const noDoor = !doorPlanned(i) || !!L.lowc[i];
  if (!k.some(d => !d[13])) return `<section class="block"><h2 class="h2">Polling stations</h2><p class="sub">${k.length} polling station${k.length === 1 ? "" : "s"}, all where Arab lists lead: the atlas makes no field recommendation there.</p></section>`;
  return `<section class="block"><h2 class="h2">Polling-station turf</h2><p class="sub">${k.length} polling station${k.length === 1 ? "" : "s"} (2022 numbering; map to 2026 stations by address before deployment). Door value combines turnout and persuasion for one conversation under the selected objective, per 1,000 conversations; rescue runs by calls and media, not at the door. Use with the Central Elections Committee's live turnout on election day. <a href="kalpi_targets.csv" target="_blank" rel="noopener">Every targetable station (CSV)</a>.</p>
    <div class="grid2" style="margin-top:12px">${big ? `<div class="card" style="border-top:0;padding-top:0"><div id="lc-kscatter"></div><div class="legend-inline"><span><i class="sq" style="background:var(--c-change)"></i>positive door value</span><span><i class="sq" style="background:var(--c-nb)"></i>negative: do not canvass</span><span>size: eligible voters</span></div></div>` : ""}
    <div class="card" style="border-top:0;padding-top:0"><h3>${noDoor ? "Positive-value stations (no door team planned)" : "Stations to canvass"}</h3>${noDoor ? `<p class="note" style="margin-top:6px">${L.lowc[i] ? "Held until the Druze candidate check." : `The realistic plans (up to 400,000 contacts) send no door team here: reach identified supporters by phone and through their own networks.`}</p>` : ""}<div class="tblwrap" style="max-height:340px;margin-top:8px"><table class="t static" id="lc-ktop"></table></div>
    <h3 style="margin-top:18px">Do-not-canvass stations</h3><div class="tblwrap" style="max-height:220px;margin-top:8px"><table class="t static" id="lc-kbot"></table></div><p class="note" id="lc-knote"></p></div></div></section>`;
}
function renderKalpi(i, kAll) {
  // rows: [kalpi, elig, t22, tres, pch, pnb, par, lead, g_area, g_gotv, g_pers, b_area, s_area, arab_led]
  // Stations where Arab lists lead are left out (they carry no values): the
  // atlas makes no field recommendation for Arab voters, mixed cities included.
  const vi = KV_IDX[OBJ];
  const k = kAll.filter(d => !d[13]);
  const nAr = kAll.length - k.length;
  const nt = document.getElementById("lc-knote");
  if (nt) nt.textContent = nAr ? `${nAr} station${nAr > 1 ? "s" : ""} where Arab lists lead ${nAr > 1 ? "are" : "is"} not shown: the atlas makes no field recommendation there.` : "";
  if (!k.length) return;
  const sc = document.getElementById("lc-kscatter");
  if (sc) {
    const W = widthOf(sc), Hh = Math.min(340, Math.round(W * 0.66)), m = { t: 10, r: 14, b: 34, l: 44 };
    const x = d3.scaleLinear().domain([0, Math.max(0.5, d3.max(k, d => d[4]) + 0.05)]).nice().range([m.l, W - m.r]);
    const y = d3.scaleLinear().domain([Math.max(0, d3.min(k, d => d[2]) - 0.05), Math.min(1, d3.max(k, d => d[2]) + 0.05)]).nice().range([Hh - m.b, m.t]);
    const rr = d3.scaleSqrt().domain([0, d3.max(k, d => d[1])]).range([0, 7]);
    const mx = d3.max(k, d => Math.abs(d[vi])) || 1;
    const svg = d3.select(sc).html("").append("svg").attr("class", "chart").attr("width", W).attr("height", Hh).attr("viewBox", `0 0 ${W} ${Hh}`).attr("role", "img").attr("aria-label", "Polling stations by projected change-bloc share and 2022 turnout");
    svg.append("g").attr("class", "grid").selectAll("line").data(y.ticks(5)).join("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", d => y(d)).attr("y2", d => y(d));
    svg.append("g").selectAll("text").data(y.ticks(5)).join("text").attr("x", m.l - 6).attr("y", d => y(d) + 3).attr("text-anchor", "end").text(d => pct(d));
    svg.append("g").selectAll("text").data(x.ticks(5)).join("text").attr("x", d => x(d)).attr("y", Hh - m.b + 16).attr("text-anchor", "middle").text(d => pct(d));
    svg.append("text").attr("x", (m.l + W - m.r) / 2).attr("y", Hh - 4).attr("text-anchor", "middle").text("Projected change-bloc share, 2026");
    svg.append("text").attr("transform", `translate(11,${(m.t + Hh - m.b) / 2}) rotate(-90)`).attr("text-anchor", "middle").text("Turnout 2022");
    const cpos = css("--c-change"), cneg = css("--c-nb");
    svg.append("g").selectAll("circle").data(k.slice().sort((a, b) => b[1] - a[1])).join("circle")
      .attr("cx", d => x(d[4])).attr("cy", d => y(d[2])).attr("r", d => Math.max(2, rr(d[1])))
      .attr("fill", d => d[vi] >= 0 ? cpos : cneg).attr("fill-opacity", d => 0.3 + 0.65 * Math.min(1, Math.abs(d[vi]) / mx))
      .attr("stroke", css("--paper")).attr("stroke-width", 0.8)
      .on("mousemove", (ev, d) => showTip(`<b>Station ${esc(d[0])}</b><div class="r"><span>Eligible</span><span>${fmtInt(d[1])}</span></div><div class="r"><span>Turnout 2022</span><span>${pct(d[2])}</span></div><div class="r"><span>Change / NB 2026</span><span>${pct(d[4])} / ${pct(d[5])}</span></div><div class="r"><span>Lead change list</span><span>${esc(d[7] || "—")}</span></div><div class="r"><span>Door value per 1,000</span><span>${fmtNV(d[vi])}</span></div>`, ev)).on("mouseleave", hideTip);
  }
  const split = OBJ === "change_govt";
  const head = `<thead><tr><th>Station</th><th class="n">Eligible</th><th class="n">Turnout 2022</th><th class="n">Change 2026</th><th class="n">NB 2026</th><th>Lead list</th><th class="n">Door value per 1,000</th>${split ? `<th class="n">turnout</th><th class="n">persuasion</th>` : ""}</tr></thead>`;
  const row = d => `<tr><td class="mono">${esc(d[0])}</td><td class="n">${fmtInt(d[1])}</td><td class="n">${pct(d[2])}</td><td class="n">${pct(d[4])}</td><td class="n">${pct(d[5])}</td><td>${esc(d[7] || "—")}</td><td class="n">${fmtNV(d[vi])}</td>${split ? `<td class="n">${fmtNV(d[9])}</td><td class="n">${fmtNV(d[10])}</td>` : ""}</tr>`;
  const cols = split ? 9 : 7;
  const best = k.filter(d => d[vi] > 0).sort((a, b) => b[vi] - a[vi]).slice(0, 20);
  const worst = k.filter(d => d[vi] < 0).sort((a, b) => a[vi] - b[vi]).slice(0, 12);
  document.getElementById("lc-ktop").innerHTML = head + "<tbody>" + (best.length ? best.map(row).join("") : `<tr><td colspan="${cols}" class="muted">No station here where a door conversation has positive value under this objective. Use calls to identified supporters instead.</td></tr>`) + "</tbody>";
  document.getElementById("lc-kbot").innerHTML = head + "<tbody>" + (worst.length ? worst.map(row).join("") : `<tr><td colspan="${cols}" class="muted">No station where a door conversation is net negative.</td></tr>`) + "</tbody>";
}

/* ============================================================ SEGMENTS */
function renderSegments() {
  const o = OBJ;
  const posTot = d3.sum(D.segments, s => Math.max(0, s[o + "__potential"]));
  const rows = D.segments.map(s => ({ label: SEG_SHORT[s.segment] || s.label, total: s[o + "__potential"], parts: [{ v: s[o + "__gotv_pot"], color: css("--c-gotv"), name: "Turnout" }, { v: s[o + "__pers_pot"], color: css("--c-pers"), name: "Persuasion" }, { v: s[o + "__resc_pot"], color: css("--c-resc"), name: "Rescue" }] })).sort((a, b) => b.total - a.total);
  hbars(document.getElementById("seg-chart"), rows, { labelW: 240, valFmt: x => fmtNV(x) + " net votes", totFmt: x => fmtNV(x) + "  (" + pct(x / Math.max(1e-9, posTot)) + ")", tickFmt: fmtInt, aria: "Potential by segment" });
  const segs = D.segments.slice().sort((a, b) => b[o + "__potential"] - a[o + "__potential"]);
  document.getElementById("seg-table").innerHTML = `<thead><tr><th>Segment</th><th class="n">Localities</th><th class="n">Eligible</th><th class="n">Turnout 2022</th><th class="n">Change 2026</th><th class="n">NB 2026</th><th class="n">Arab 2026</th><th class="n">Persuadable</th><th class="n">Rescue pool</th><th class="n">Potential</th><th class="n">Share</th></tr></thead><tbody>` +
    segs.map(s => `<tr><td><a href="#seg-${s.segment}">${esc(s.label)}</a></td><td class="n">${fmtInt(s.localities)}</td><td class="n">${fmtInt(s.eligible)}</td><td class="n">${pct(s.turnout_2022)}</td><td class="n">${pct(s.p26_change)}</td><td class="n">${pct(s.p26_nb)}</td><td class="n">${pct(s.p26_arab)}</td><td class="n">${fmtInt(s.persuadable_voters)}</td><td class="n">${fmtInt(s.rescue_voters)}</td><td class="n">${fmtNV(s[o + "__potential"])}</td><td class="n">${pct(s[o + "__share"])}</td></tr>`).join("") + "</tbody>";
  const cc = (C.segments || []);
  const objNote = o !== "change_govt" ? `<p class="note" style="grid-column:1/-1;margin-top:0">Tiers and net-vote figures quoted in these playbooks refer to the default objective, a change-led government. The bars and table above use ${esc(D.objectives[o])}.</p>` : "";
  document.getElementById("seg-cards").innerHTML = objNote + segs.map(s => {
    const c = cc.find(x => x.segment === s.segment);
    const ex = s.segment.startsWith("arab") ? [] : ALL.filter(i => L.seg[i] === s.segment && isTarget(i)).sort((a, b) => (ov("potential", b) ?? -1e9) - (ov("potential", a) ?? -1e9)).slice(0, 6);
    return `<div class="segcard" id="seg-${s.segment}"><div class="lab">${pct(s[o + "__share"])} of potential · ${fmtInt(s.eligible)} eligible</div><h3>${esc(s.label)}</h3>
    <div class="stats"><span>turnout ${pct(s.turnout_2022)}</span><span>change ${pct(s.p26_change)}</span><span>NB ${pct(s.p26_nb)}</span><span>Arab ${pct(s.p26_arab)}</span></div>
    ${c ? `<p style="margin-top:10px;font-weight:600">${esc(c.role)}</p><dl><dt>Who</dt><dd>${esc(c.who)}</dd><dt>What moves them</dt><dd>${esc(c.moves)}${cites(c.cites)}</dd><dt>Approach</dt><dd>${esc(c.approach)}</dd><dt>Message</dt><dd>${esc(c.message)}</dd><dt>Messenger</dt><dd>${esc(c.messenger)}</dd><dt>Avoid</dt><dd>${esc(c.avoid)}</dd>${c.caveat ? `<dt>Caveat</dt><dd>${esc(c.caveat)}</dd>` : ""}</dl>` : ""}
    ${ex.length ? `<dl><dt>Top localities by potential</dt><dd>${ex.map(i => `<a href="#loc-${L.id[i]}">${esc(L.en[i])}</a>`).join(", ")}</dd></dl>` : s.segment.startsWith("arab") ? `<dl><dt>Localities</dt><dd>Not ranked: the atlas makes no field recommendation for Arab localities.</dd></dl>` : ""}</div>`;
  }).join("");
}

/* ============================================================ PLAYBOOK */
function renderPlaybook() {
  const P = C.playbook;
  const root = document.getElementById("pb-root");
  if (!P || !P.timeline) { root.innerHTML = `<p class="muted" style="padding:30px 0">Playbook content is not available in this build.</p>`; return; }
  const verdictColor = { core: "var(--good)", "use selectively": "var(--accent)", "low value": "var(--muted)", avoid: "var(--bad)" };
  const SEC = P.sections || [];
  const sec = key => SEC.find(s => s.key === key);
  const secHtml = s => s ? `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:19px">${esc(s.title)}</h3><p style="margin-top:8px;font-size:15px;color:var(--ink2)">${esc(s.text)}${cites(s.cites)}</p>${s.bullets && s.bullets.length ? `<ul style="margin:8px 0 0;padding-inline-start:20px;font-size:14.5px;color:var(--ink2)">${s.bullets.map(b => `<li style="margin-top:4px">${esc(b)}</li>`).join("")}</ul>` : ""}</div>` : "";
  root.innerHTML = `
  <section class="block"><div class="prose"><p>${esc(P.intro)}</p></div></section>
  ${sec("realistic") ? `<section class="block"><div class="grid2">${secHtml(sec("realistic"))}${secHtml(sec("coordination"))}</div></section>` : ""}
  <section class="block"><h2 class="h2">The calendar to election day</h2><p class="sub">From today to the count of the double envelopes. Persuasion decays within days; turnout contact works best in the final ten.</p>
    <div class="timeline">${P.timeline.map(t => `<div class="tl-row"><div class="when">${esc(t.when)}<small>${esc(t.dates)}</small></div><div class="what"><h4>${esc(t.title)}</h4><ul>${(t.actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>${t.cites && t.cites.length ? `<p style="font-size:12px;margin-top:6px">${cites(t.cites)}</p>` : ""}</div></div>`).join("")}</div></section>
  ${sec("rescue") || sec("young") ? `<section class="block"><div class="grid2">${secHtml(sec("rescue"))}${secHtml(sec("young"))}</div></section>` : ""}
  <section class="block"><h2 class="h2">Tactics and their evidence</h2><p class="sub">Effects per completed contact unless stated, scaled to a high-salience election with roughly 70% turnout. Ranges reflect the spread across experiments.</p>
    <div class="tblwrap" style="max-height:none;margin-top:16px"><table class="t static"><thead><tr><th>Tactic</th><th>Mechanism</th><th>Effect</th><th>Use in Israel 2026</th><th>Verdict</th></tr></thead><tbody>
    ${(P.tactics || []).map(t => `<tr><td style="white-space:normal;min-width:150px"><b>${esc(t.tactic)}</b></td><td style="white-space:normal;min-width:110px">${esc(t.mechanism)}</td><td style="white-space:normal;min-width:200px">${esc(t.effect)}${cites(t.cites)}</td><td style="white-space:normal;min-width:260px">${esc(t.israel)}</td><td><span class="chip" style="color:${verdictColor[t.verdict] || "var(--ink)"}">${esc(t.verdict)}</span></td></tr>`).join("")}
    </tbody></table></div></section>
  <section class="block"><h2 class="h2">Election day</h2><div class="grid3" style="margin-top:16px">${(P.election_day || []).map(e => `<div class="card"><h3 style="text-transform:none;letter-spacing:0;font-size:17px">${esc(e.title)}</h3><p style="margin-top:6px;font-size:14.5px;color:var(--ink2)">${esc(e.text)}${cites(e.cites)}</p></div>`).join("")}</div></section>
  ${sec("arab") || sec("legal") ? `<section class="block"><div class="grid2">${secHtml(sec("arab"))}${secHtml(sec("legal"))}</div></section>` : ""}
  <section class="block"><h2 class="h2">Do and don't</h2><div class="dontlist">${(P.dos || []).map(d => `<div class="do"><h4>Do: ${esc(d.title)}</h4><p>${esc(d.text)}${cites(d.cites)}</p></div>`).join("")}${(P.donts || []).map(d => `<div><h4>Don't: ${esc(d.title)}</h4><p>${esc(d.text)}${cites(d.cites)}</p></div>`).join("")}</div></section>
  <section class="block"><h2 class="h2">Messages that fit the 2026 electorate</h2><p class="sub">Campaigns move votes by raising the salience of issues they own more than by changing views. Test before scaling: ads routinely differ by half their average effect.</p>
    <div class="tblwrap" style="max-height:none;margin-top:16px"><table class="t static"><thead><tr><th>Issue</th><th>Who it moves</th><th>Frame</th></tr></thead><tbody>${(P.messages || []).map(m => `<tr><td style="white-space:normal;min-width:140px"><b>${esc(m.issue)}</b></td><td style="white-space:normal;min-width:200px">${esc(m.who_it_moves)}</td><td style="white-space:normal;min-width:320px">${esc(m.frame)}${cites(m.cites)}</td></tr>`).join("")}</tbody></table></div></section>`;
}

/* ============================================================ PLANNER */
const MODES = { base: ["As calibrated: door conversations and live calls", 1.0], phone: ["Mostly volunteer phone calls", 0.67], relational: ["Mostly friend-to-friend asks", 2.0] };
const PROG_LABEL = { area: "Door canvass", sup: "Supporter turnout calls", pers: "Persuasion calls", resc: "Rescue calls" };
const PROG_VAR = { area: "--c-gotv", sup: "--div-ch1", pers: "--c-pers", resc: "--c-resc" };
let plan = { budget: store.get("planBudget", 400000), ident: store.get("planIdent", Math.round(S.list_identified * 100)), mode: store.get("planMode", "base"), druze: false, progs: { area: true, sup: true, pers: true, resc: true } };
if (!(plan.budget >= 20000 && plan.budget <= 1500000)) plan.budget = 400000;
if (!(plan.ident >= 0 && plan.ident <= 100)) plan.ident = Math.round(S.list_identified * 100);
if (!hasOwn(MODES, plan.mode)) plan.mode = "base";
function renderPlanner() {
  const pin = document.getElementById("plan-in");
  if (!pin.dataset.ready) {
    pin.innerHTML = `
    <div class="f"><label class="lab" for="pl-budget">Completed contacts before election day</label><input type="range" id="pl-budget" min="20000" max="1500000" step="10000"><div><output id="pl-bout" for="pl-budget"></output></div><p class="hint">For scale: 10,000 volunteers each completing 4 contacts a day for 10 days is 400,000.</p></div>
    <div class="f"><label class="lab" for="pl-ident">Voters identified on lists</label><input type="range" id="pl-ident" min="0" max="100" step="5"><div><output id="pl-iout" for="pl-ident"></output></div><p class="hint">Share of change-bloc supporters, soft Netanyahu-bloc voters and Blue and White or Reservists voters the campaign holds on lists. Half of those are reached. List calls reach change voters inside Netanyahu-majority towns, where door canvassing backfires.</p></div>
    <div class="f"><label class="lab" for="pl-mode">Quality of list contacts</label><div class="ctl" style="margin:4px 0 0"><select id="pl-mode" style="width:100%">${Object.entries(MODES).map(([k, m]) => `<option value="${k}">${m[0]} (×${m[1]})</option>`).join("")}</select></div><p class="hint">Applies to calls, texts and relational asks to identified voters, using meta-analytic ratios relative to a door conversation. Door canvassing stays at ×1.0.</p></div>
    <fieldset class="f" style="border:0;padding:0;margin:14px 0 0"><legend class="lab">Programmes</legend>
      ${PROGS.map(p => `<label class="cb"><input type="checkbox" id="pl-${p}" checked> ${PROG_LABEL[p]}</label>`).join("")}
      <label class="cb"><input type="checkbox" id="pl-druze"> Include Druze and Circassian towns (after the candidate check and a community poll)</label></fieldset>
    <p class="hint" style="margin-top:10px">Arab localities, and polling stations where Arab lists lead, are never planned: any Arab-sector turnout work is a leadership decision.</p>
    <p class="hint" style="margin-top:14px">Objective: <b id="pl-obj"></b>. Change it in the bar at the top. Door teams go only to localities with at least ${fmtInt(S.min_area)} positive-value contacts.</p>`;
    pin.dataset.ready = "1";
    const b = document.getElementById("pl-budget");
    b.value = plan.budget; b.addEventListener("input", () => { plan.budget = +b.value; store.set("planBudget", plan.budget); renderPlanner(); });
    const idn = document.getElementById("pl-ident");
    idn.value = plan.ident; idn.addEventListener("input", () => { plan.ident = +idn.value; store.set("planIdent", plan.ident); renderPlanner(); });
    const md = document.getElementById("pl-mode"); md.value = plan.mode; md.addEventListener("change", () => { plan.mode = md.value; store.set("planMode", plan.mode); renderPlanner(); });
    const dz = document.getElementById("pl-druze"); dz.checked = plan.druze; dz.addEventListener("change", () => { plan.druze = dz.checked; renderPlanner(); });
    PROGS.forEach(p => document.getElementById("pl-" + p).addEventListener("change", e => { plan.progs[p] = e.target.checked; renderPlanner(); }));
  }
  document.getElementById("pl-bout").textContent = fmtInt(plan.budget) + " contacts";
  document.getElementById("pl-iout").textContent = plan.ident + "% identified";
  document.getElementById("pl-obj").textContent = OBJ_SHORT[OBJ];
  const res = allocate(OBJ, plan.budget, { ident: plan.ident / 100, mult: MODES[plan.mode][1], exclude: i => !!L.excl[i] || isArab(i) || (!plan.druze && !!L.lowc[i]), progs: PROGS.filter(p => plan.progs[p]), curve: true });
  const total = res.ve, used = res.used;
  const rows = [...res.alloc.entries()].sort((a, b) => b[1].ve - a[1].ve);
  const ct = res.contacts, ctot = Math.max(1, d3.sum(PROGS, p => ct[p]));
  const out = document.getElementById("plan-out");
  out.innerHTML = `
    <div class="tiles" style="margin-top:0;grid-template-columns:repeat(auto-fit,minmax(min(230px,100%),1fr))"><div class="tile"><div class="k">Net votes</div><div class="v">${fmtInt(total)}</div><div class="d">${(total / Math.max(1, used) * 1000).toFixed(1)} per 1,000 contacts</div></div>
    <div class="tile"><div class="k">Effect on the objective</div><div class="v" style="font-size:30px">${effShort(total)}</div><div class="d">${OBJ_GOAL[OBJ]}</div></div>
    <div class="tile"><div class="k">Expected seats' worth</div><div class="v">${seatsOK() ? seatsOf(total).toFixed(3) : "—"}</div><div class="d">${seatsOK() ? "Change-bloc seats from the same number of votes for an average change list" : "Not comparable under this objective: deny-61 net votes are not change-list votes"}</div></div>
    <div class="tile"><div class="k">Localities</div><div class="v">${fmtInt(rows.length)}</div><div class="d">${fmtInt(res.doorLocs)} with door teams. ${!PROGS.some(p => plan.progs[p]) ? "No programme selected" : res.left > 0 ? fmtInt(res.left) + " contacts unspent: no positive turf left" : "Budget fully allocated"}</div></div></div>
    <div class="card" style="margin-top:24px"><h3>Contacts by programme</h3><div class="bars2" role="img" aria-label="${PROGS.map(p => `${PROG_LABEL[p]} ${pct(ct[p] / ctot)}`).join(", ")}">${PROGS.map(p => `<span style="width:${100 * ct[p] / ctot}%;background:var(${PROG_VAR[p]})"></span>`).join("")}</div>
      <div class="legend-inline">${PROGS.map(p => `<span><i class="sq" style="background:var(${PROG_VAR[p]})"></i>${PROG_LABEL[p]} ${fmtInt(ct[p])}</span>`).join("")}</div></div>
    <div class="card" style="margin-top:24px"><h3>Returns curve</h3><p class="sub">Cumulative net votes as contacts are added in order of value. The marker shows your budget.</p><div id="pl-curve"></div></div>
    <div class="card" style="margin-top:24px"><h3>Where the contacts go</h3><div class="tblwrap" style="margin-top:10px;max-height:520px"><table class="t" id="pl-table"><thead><tr><th>Locality</th><th>Lead list</th><th class="n">Door</th><th class="n">Supporter calls</th><th class="n">Persuasion calls</th><th class="n">Rescue calls</th><th class="n">Net votes</th><th class="n">Share</th></tr></thead><tbody>
    ${rows.slice(0, 150).map(([i, a]) => `<tr data-id="${L.id[i]}"><td class="loc">${locName(i)}</td><td>${leadOK(i) ? leadChip(L.lead[i]) : "—"}</td><td class="n">${fmtInt(a.area)}</td><td class="n">${fmtInt(a.sup)}</td><td class="n">${fmtInt(a.pers)}</td><td class="n">${fmtInt(a.resc)}</td><td class="n">${fmtNV(a.ve)}</td><td class="n">${pct(a.ve / Math.max(1e-9, total), 1)}</td></tr>`).join("")}</tbody>${rows.length > 150 ? `<tfoot><tr><td colspan="8" class="muted" style="padding:10px;white-space:normal">Showing the 150 largest of ${fmtInt(rows.length)} localities; copy the allocation for the full list.</td></tr></tfoot>` : ""}</table></div>
    <p style="margin-top:10px"><button type="button" class="btn" id="pl-copy">Copy allocation as CSV</button></p></div>`;
  bindRows(document.getElementById("pl-table"));
  document.getElementById("pl-copy").addEventListener("click", () => {
    const lines = [["Locality (English)", "Locality (Hebrew)", "CBS code", "Lead change list", "Door contacts", "Supporter calls", "Persuasion calls", "Rescue calls", "Net votes", "Objective"]]
      .concat(rows.map(([i, a]) => [L.en[i], L.he[i], L.id[i], leadOK(i) ? L.lead[i] : "", Math.round(a.area), Math.round(a.sup), Math.round(a.pers), Math.round(a.resc), +a.ve.toFixed(2), OBJ_SHORT[OBJ]]));
    copyText(toCSV(lines), document.getElementById("pl-copy"), "Copy allocation as CSV");
  });
  const el = document.getElementById("pl-curve");
  const W = widthOf(el), Hh = 220, m = { t: 12, r: 20, b: 30, l: 56 };
  const curve = res.curve;
  const xmax = Math.min(curve[curve.length - 1][0], Math.max(plan.budget * 1.6, 600000), 3e6);
  const pts = curve.filter(p => p[0] <= xmax);
  const x = d3.scaleLinear().domain([0, xmax]).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([0, (d3.max(pts, p => p[1]) || 1) * 1.05]).nice().range([Hh - m.b, m.t]);
  const svg = d3.select(el).html("").append("svg").attr("class", "chart").attr("width", W).attr("height", Hh).attr("viewBox", `0 0 ${W} ${Hh}`).attr("role", "img").attr("aria-label", "Returns curve");
  svg.append("g").attr("class", "grid").selectAll("line").data(y.ticks(4)).join("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", d => y(d)).attr("y2", d => y(d));
  svg.append("g").selectAll("text").data(y.ticks(4)).join("text").attr("x", m.l - 6).attr("y", d => y(d) + 3).attr("text-anchor", "end").text(fmtInt);
  svg.append("g").selectAll("text").data(x.ticks(W < 480 ? 3 : 5)).join("text").attr("x", d => x(d)).attr("y", Hh - 10).attr("text-anchor", "middle").text(d => d >= 1e6 ? (d / 1e6) + "m" : (d / 1e3) + "k");
  svg.append("path").attr("d", d3.area().x(p => x(p[0])).y0(y(0)).y1(p => y(p[1]))(pts)).attr("fill", css("--accent")).attr("fill-opacity", 0.12);
  svg.append("path").attr("d", d3.line().x(p => x(p[0])).y(p => y(p[1]))(pts)).attr("fill", "none").attr("stroke", css("--accent")).attr("stroke-width", 2);
  const bx = Math.min(used, xmax);
  svg.append("line").attr("x1", x(bx)).attr("x2", x(bx)).attr("y1", m.t).attr("y2", Hh - m.b).attr("stroke", css("--ink")).attr("stroke-dasharray", "3 3");
  svg.append("circle").attr("cx", x(bx)).attr("cy", y(total)).attr("r", 5).attr("fill", css("--ink")).attr("stroke", css("--paper")).attr("stroke-width", 2);
  svg.append("text").attr("class", "lbl").attr("x", x(bx) + (x(bx) > W * 0.65 ? -8 : 8)).attr("y", Math.max(14, y(total) - 8)).attr("text-anchor", x(bx) > W * 0.65 ? "end" : "start").text(fmtInt(total) + " net votes");
}

/* ============================================================ METHODOLOGY */
function renderMethod() {
  const V = D.validation, ins = V.projection_in_sample_2021_2022 || {}, ho = V.projection_holdout || {}, op = V.openness_out_of_sample, cp = V.composition_out_of_sample;
  const mvRows = D.mv.filter(r => r.share > 0.003).sort((a, b) => b.change_govt - a.change_govt);
  const specRows = Object.entries(op.specs).sort((a, b) => b[1].mean_spearman - a[1].mean_spearman);
  const hoRow = (fold) => { const f = ho[fold] || {}; return ["transfer", "uniform", "blend"].map(mm => `<tr${mm === "blend" ? ' style="font-weight:600"' : ""}><td>${fold.replace("->", "→")}</td><td>${{ transfer: "Flow matrix only", uniform: "Uniform camp swing", blend: "50/50 blend (used)" }[mm]}</td><td class="n">${(f[mm] || {}).C ?? "—"}</td><td class="n">${(f[mm] || {}).R ?? "—"}</td><td class="n">${(f[mm] || {}).A ?? "—"}</td></tr>`).join(""); };
  const sv = D.sensitivity || {}, so = sv.objectives || {};
  document.getElementById("m-root").innerHTML = `
  <section class="block"><div class="prose">
    <h3>1. The question in a proportional system</h3>
    <p>In single-member systems, campaigns pour resources into marginal districts because one vote there can flip a seat. Israel elects all 120 members of the Knesset by national list proportional representation, with a 3.25% threshold and Bader-Ofer (D'Hondt) allocation with surplus agreements. A vote has the same seat value wherever it is cast, so a locality's closeness carries no value of its own.${cites(["P-F21"])} What varies from place to place is the density of the voters a campaign wants to reach and the cost of reaching them. Swing-voter and core-voter models both recognise this.${cites(["P-F18", "P-F19", "P-F20"])} The atlas therefore scores places by the expected net effect of campaign contact, in total and per contact, rather than by competitiveness.</p>
    <p>A vote's value does vary by <i>list</i>. A vote for a list near the threshold, for a list in a surplus pair close to its next seat, or for a list in the bloc that is close to 61 moves the outcome more than others. That is why the exchange rate in section 6 comes from the forecast's own simulations.</p>
    <h3>2. Data</h3>
    <ul>
      <li><b>Official results.</b> Central Elections Committee results for every locality in the seven Knesset elections 2013–2022 (K19–K25), and for every polling station in 2022: ${fmtInt(S.n_localities)} localities and ${fmtInt(S.n_kalpiot)} regular stations.${cites(["DATA-CEC"])}</li>
      <li><b>Locality attributes.</b> CBS locality file 2023 (coordinates, district, regional council, settlement type, population), the 2022 Census by locality (religion, household religiosity, age, education, country of birth, income), and the CBS socio-economic cluster.${cites(["DATA-CBS", "DATA-CENSUS", "DATA-SES"])}</li>
      <li><b>The forecast.</b> The Knesset Model's registration-mixture projection as of ${fmtDate(S.asof)}: 8,000 simulated election-day vote shares, the seat law, and the government-formation model.</li>
      <li><b>Vote-transfer evidence.</b> The Kolot Nodedim polling-station transition matrices (2021→2022, with abstention), used to calibrate the 2026 lineages and the abstention estimate.${cites(["DATA-KN"])}</li>
      <li><b>Map geometry.</b> Natural Earth via world-atlas, and geoBoundaries district outlines.${cites(["DATA-GEO"])}</li>
    </ul>
    <h3>3. Harmonising seven elections</h3>
    <p>Each ballot letter with a meaningful share is mapped to a party lineage, a family that survives mergers, and a camp. Expected national shares are checked at load, so a mis-mapped letter fails loudly. Camps are ideological and consistent across cycles. <i>Right</i> means Likud, the haredi lists and the religious-Zionist lists, including Kulanu and Yamina. <i>Change</i> means the centre-left and anti-Netanyahu lists, including New Hope in 2021. Yisrael Beytenu is counted on the right until April 2019 and in the change camp from September 2019, so that transition is excluded from volatility measures. Double-envelope votes (soldiers, hospitals, prisons, accessible stations: 462,807 in 2022) are counted centrally by the CEC and appear in no locality.${cites(["D2-F03", "D2-F04", "DATA-CEC-GUIDE"])}</p>
    <h3>4. Segments</h3>
    <p>Each locality is assigned to one of sixteen segments by ordered rules. The rules use census religion (Druze, Christian, Muslim), the CBS settlement type (kibbutz, moshav, community settlement, Bedouin tribe), the district (Judea and Samaria), the Arab share of a mixed city, and the 2022 vote: haredi share of 45% or more, religious-Zionist 30% or more, Yisrael Beytenu 12% or more on average since 2019, centre-left 48% or more, and Likud 30% or more in a lower-income town or a mid-income town more than 45 km from Tel Aviv. Kafr Kama and Reihaniye, Circassian towns whose voting follows the Druze pattern, are grouped with the Druze.</p>
    <h3>5. The 2026 projection for every locality and station</h3>
    <p>Each 2026 list is described by the 2022 electorates it draws from: the forecast's lineage composition, calibrated to the measured 2021→2022 transition matrix and to vote-recall polling.${cites(["D5-F10"])} From these compositions the atlas builds one national 2022→2026 flow matrix and rakes it so that it reproduces both the 2022 result and the 2026 forecast. Applied to a locality's 2022 vote, it gives a first projection.</p>
    <p>A held-out test showed that flows alone can mislead locally, so each locality's camp totals are then pulled halfway toward uniform national camp swing from its own 2022 camp shares. Lists are rescaled within each camp. Iterative proportional fitting then rakes the locality-by-list matrix until every locality keeps its own total and every list matches the national forecast, converted to regular-station votes with each lineage's 2022 envelope ratio. Polling stations get the same treatment, then are rescaled within their locality to add up to the locality projection.</p>
    <p>In Druze localities, the 2022 vote followed home-village candidates: Beit Jann gave Meretz 62% because of a local candidate. Their split among non-Arab lists is therefore pooled 60% toward the Druze average. Each town keeps its own Arab-list share, so mixed Druze, Muslim and Christian towns such as Mughar keep their Arab-list voters.</p>
    <div class="eq">P0[i,j] = Σ_s sh22[i,s] · F[s→j]              (F: national flow matrix, raked to 2022 and 2026 margins)
camp_c[i] ← ½ · Σ_(j in c) P0[i,j] + ½ · (S22_c[i] + ΔS_c)   (ΔS_c: national camp swing)
P = IPF(P_blend; rows = locality totals, columns = forecast shares)</div>
    <p><b>Held-out test of the local-allocation assumption.</b> A national party-to-party flow matrix of the same form was fitted on a random half of localities and used to project the other half from its own previous vote, with the true national totals given to every method, so these errors are a lower bound for 2026. Three random splits per fold. Weighted mean absolute error in camp shares, points:</p>
    <div class="tblwrap" style="max-height:none;margin-top:10px"><table class="t static"><thead><tr><th>Fold</th><th>Method</th><th class="n">Change camp</th><th class="n">Right</th><th class="n">Arab lists</th></tr></thead><tbody>${hoRow("2020->2021")}${hoRow("2021->2022")}</tbody></table></div>
    <p class="note">Flows alone failed badly in 2020→21, and uniform swing failed for Arab lists in 2021→22. The blend had the lowest average error across the six cells (about 1.26 points, against about 1.48 for each pure method), though it was not best in every cell, and the 50/50 weight was chosen on these same folds. An earlier check projected 2022 from 2021 with the Kolot Nodedim matrix (change camp ${ins.mae_C_transfer_pp ?? "—"} points, right ${ins.mae_R_transfer_pp ?? "—"}, Arab ${ins.mae_A_transfer_pp ?? "—"}). That matrix was estimated from the same stations, so the check is an in-sample fit and is reported only as such.</p>
    <h3>6. The exchange rate: what a vote is worth</h3>
    <p>For each list, one vote's marginal value is measured by perturbing the forecast's 8,000 election-day share draws by ±0.2% of the vote (about 9,600 votes). The perturbed draws are re-run through the full seat law (threshold, surplus pairs, Bader-Ofer) and through the government-formation model with the first 60 of the forecast's 200 parameter vectors, including its post-deadlock stage (a deadlock can still resolve into a unity, defector or change government before a repeat election), and common random numbers. Adding votes to a list is the arithmetic of mobilising new voters; moving a voter from list A to list B is worth the difference of the two values.</p>
    <div class="tblwrap" style="max-height:none;margin-top:14px"><table class="t static"><thead><tr><th>List</th><th>Camp</th><th class="n">Mean share</th><th class="n">P(pass)</th><th class="n">Change-led government</th><th class="n">Deny Netanyahu 61</th><th class="n">Change-bloc seats</th></tr></thead><tbody>
    ${mvRows.map(r => `<tr><td><b>${esc(r.list)}</b></td><td>${{ ch: "Change", nb: "Netanyahu", ar: "Arab", un: "Unaligned", ot: "Other" }[r.camp]}</td><td class="n">${pct(r.share, 1)}</td><td class="n">${pct(r.p_pass)}</td><td class="n">${sgn(r.change_govt)}</td><td class="n">${sgn(r.block_nb)}</td><td class="n">${sgn(r.change_seats, 3)}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">The seat law here carries all six signed or expected surplus agreements (Likud–RZP-Zehut, Together–Yisrael Beytenu, Yashar–Democrats, Shas–UTJ, Otzma–Amcha, Joint List–Ra'am). The published forecast carries the same pairs. The baselines below use 60 of the forecast's 200 formation behaviour vectors, so they can differ by a few tenths of a point from the published headline. Probability columns: change in percentage points per 10,000 extra votes for the list. Seats column: change in expected change-bloc seats per 10,000 votes. Baseline: P(change-led government) ${pct(S.forecast.baseline.change_govt, 1)}, P(Netanyahu bloc below 61) ${pct(S.forecast.baseline.block_nb, 1)}, expected change-bloc seats ${S.forecast.baseline.change_seats.toFixed(1)}.</p>
    <p>Two results drive the atlas. First, change lists are worth about the same per vote, except Yisrael Beytenu, which is worth less for a change-led government because of Liberman's veto on haredi partners. Second, Arab-list votes cut both ways. They are among the most valuable votes for denying Netanyahu 61 seats. In the formation model, though, they mostly turn Netanyahu majorities into deadlock while diluting change-list seats, so they are worth close to zero (Ra'am) or less (Joint List) for a change-led government. A seat gained by one change list is sometimes taken from another, so about ${fmtSig(1 / S.mv_ref.change_seats)} average change-list votes buy one expected change-bloc seat. Results are expressed in <b>net votes</b>: the number of extra votes for an average change-bloc list that would move the objective by the same amount.</p>
    <h3>7. The field model</h3>
    <h4>One conversation, two effects</h4>
    <p>A door conversation is one contact, whatever its purpose. Its value in a polling-station area is the sum of two effects, turnout and persuasion. Rescue asks are not made at the door; rescue runs through media and calls to identified voters (below). Door teams are sent only to areas where the sum is positive ("turf selection"), up to 35% of the resident roll, and never to polling stations where Arab lists lead.</p>
    <p><b>Turnout.</b> A completed door conversation raises the contacted person's turnout by 1.5 points where 15% of residents vote, the hump's ×1.0 point. The effect follows a hump in baseline turnout: largest where 30–55% of residents vote and close to zero above 85%.${cites(["D3-F03"])} It is multiplied by 1.3 for spillover to other household members.${cites(["D3-F15", "D3-F10"])} Most door turf in Israel votes at 75–90%, so the lift actually applied there averages about ${doorLift().toFixed(2)} points including spillover, below the European pooled canvassing estimate of about 0.8 and far below the US high-salience estimate of about 3.${cites(["D3-F01", "D3-F22"])} The hump rests on US evidence; the sensitivity runs replace it with a flat effect.</p>
    <div class="tblwrap" style="max-height:none;margin-top:10px"><table class="t static"><thead><tr><th>Resident turnout</th>${[15, 30, 42.5, 55, 65, 75, 85, 95].map(x => `<th class="n">${x}%</th>`).join("")}</tr></thead><tbody><tr><td>Multiplier on 1.5 pts</td>${[1.0, 1.5, 1.8, 1.2, 0.7, 0.4, 0.22, 0.10].map(x => `<td class="n">×${x.toFixed(2)}</td>`).join("")}</tr></tbody></table></div>
    <p>Who turns out matters as much as how many. A turnout contact mobilises the local electorate, so its net value is the station's projected vote weighted by each list's marginal value. In Netanyahu-majority turf it is negative. We tested whether the marginal voter differs from the average voter by segment, using a multiplicative propensity model fitted on 2019–2021 and checked on 2022. It fitted the change camp slightly better but the right and Arab lists worse, and was worse overall. Weighted error per 1,000 eligible, simple versus model: change camp ${cp.naive.C} vs ${cp.multiplicative.C}, right ${cp.naive.R} vs ${cp.multiplicative.R}, Arab ${cp.naive.A} vs ${cp.multiplicative.A}. The atlas therefore assumes new voters look like existing voters in the same polling station.</p>
    <p><b>Persuasion.</b> Cross-bloc persuasion close to a high-salience election is small.${cites(["P-F01", "D3-F27"])} The persuadable universe is each Netanyahu-bloc list's soft supporters (one minus the forecast's certainty), times 22% who are cross-pressured enough to consider a change list. The 22% is a calibration constant, not a measurement: the resulting national pool, about 2% of projected voters, sits at the upper end of N12's measured 0.6–1.6% undecided between blocs.${cites(["D5-F08", "D5-F09", "D5-F07"])} A conversation with a soft Netanyahu-bloc voter switches about 0.3% of them (about 1.4% of the cross-pressured among them).${cites(["P-F02"])} Persuasion is set to zero in Muslim and Bedouin localities, ×0.3 in Christian Arab localities, and scaled down where the soft right is religious: haredi ×0.15, national-religious settlements ×0.35, religious-Zionist towns ×0.6.${cites(["D1-F20"])}</p>
    <p>The universe is localised by an <b>openness index</b>, built from three features of a locality's own history. The first is the size of its past cross-camp movement beyond the national swing, with sampling noise removed and shrunk to its segment. The second is its vote for soft-right swing lists (Kadima and Am Shalem 2013, Kulanu, Gesher, Yisrael Beytenu in April 2019, Yamina 2021, New Hope 2021, Jewish Home 2022). The third is how evenly it splits between the camps. The weights were chosen out of sample: indices built only from elections up to <i>t</i> were scored on how well they ranked each locality's movement in <i>t</i>→<i>t+1</i>, for two folds.</p>
    <div class="tblwrap" style="max-height:none;margin-top:14px"><table class="t static"><thead><tr><th>Openness specification</th><th class="n">Spearman, 2020→21</th><th class="n">Spearman, 2021→22</th><th class="n">Mean</th><th class="n">Top / bottom quintile</th></tr></thead><tbody>
    ${specRows.map(([kk, s]) => `<tr${kk === op.chosen ? ' style="font-weight:600"' : ""}><td>${esc(kk)}${kk === op.chosen ? " (used)" : ""}</td><td class="n">${s.spearman_by_fold[0].toFixed(2)}</td><td class="n">${s.spearman_by_fold[1].toFixed(2)}</td><td class="n">${s.mean_spearman.toFixed(2)}</td><td class="n">${s.top_bottom_quintile_ratio.map(x => x.toFixed(1) + "×").join(" / ")}</td></tr>`).join("")}
    </tbody></table></div>
    <p class="note">Localities in the top quintile of the chosen index moved about three times as much as those in the bottom quintile in the following election. n = ${op.n_by_fold["2020->2021"]} and ${op.n_by_fold["2021->2022"]} Jewish-majority localities with at least 400 valid votes.</p>
    <p><b>Wasted-vote rescue (calls and media only).</b> The Reservists are projected below the threshold in most simulations; Blue and White withdrew on 19 Oct, and the forecast routes its vote to other lists. Supporters of sub-threshold lists desert them in the final days anyway, and insurance-voting appeals work best when polls show the list below the line.${cites(["P-F25", "P-F28", "D1-F28"])} The atlas assumes 5% of contacted supporters move to a viable list: 60% to a change list and 40% to Likud. The value is computed per list. Moving a Reservists voter helps a change-led government but slightly hurts the blocking objective: a vote that stays with the Reservists counts against a Netanyahu 61 if the list passes (pass chance about ${pct((D.mv.find(r => /^Reservists/.test(r.list)) || {}).p_pass)}), and 40% of movers are assumed to go to Likud.</p>
    <h4>List programmes</h4>
    <p>List programmes reach only identified voters by call, text or friend-to-friend ask. Where the door conversation is net negative, the atlas counts turnout contact with identified change-bloc supporters, whose turnout is assumed 10 points above their area's, and persuasion of identified soft Netanyahu-bloc voters, each call switching the same share as a door conversation with a soft voter there (about 0.3%, scaled by the openness index and the segment multiplier), with half the turnout side-effect of a turnout call. Rescue calls to identified Blue and White or Reservists voters run in any station where they have positive value. None runs in polling stations where Arab lists lead. The planning assumption is that 30% of each group is already identified and half of those are reached; the planner lets you change the identified share. Building the lists costs ID contacts that the atlas does not count.</p>
    <h4>Resident turnout and the roll</h4>
    <p>Baseline turnout is <i>resident</i> turnout. A locality's 2022 regular-station turnout gets its district's double-envelope add-back (2.9 points in Arab localities, 3.5 in haredi and 4.5 in Druze towns, with the other localities' rate per district set so that each district's 2022 envelope total is preserved). It is then divided by the share of the roll living in Israel.${cites(["D2-F04"])} With the add-back the range runs from 2.9 points (Arab localities) to about 13 points (West Bank settlements). The share abroad is set by segment around a national 8%: 13% in Russian-speaking towns, 10% in liberal cities, 3–5% in haredi, settler, Arab and Bedouin localities.${cites(["D2-F14", "D2-F15"])} Towns whose turnout sits more than 8 points below their segment's typical level, such as Eilat, carry registrants who live elsewhere; 70% of the excess gap is treated as non-resident roll. The 2026 roll grows faster in younger segments: haredi ×1.16, national-religious settlements ×1.13, Bedouin ×1.12, others about ×1.05.</p>
    <h4>Flags</h4>
    <p>${S.flags.displaced_lebanon} localities within 5 km of Lebanon and ${S.flags.displaced_gaza} within 7 km of Gaza are flagged <i>displaced</i>: door capacity is halved because many residents may not be home.${cites(["D5-F20", "D6-F37"])} Four Golan Druze villages and Ghajar are <i>not targeted</i>. ${S.flags.low_confidence} Druze and Circassian localities are flagged <i>low confidence</i>.${cites(["D2-F11"])} Polling stations where Arab lists lead outside Arab localities (${fmtInt(S.arab_led_stations)}) get no door or list programme.</p>
    <h3>8. From contact to potential</h3>
    <div class="eq">door value per conversation, station u =
      lift(p̃_u) · Σ_j m_uj · MV_j                                          turnout
    + p_u · min(0.25, soft_u · 0.22 · open_u · seg_u) · ρ_p · ΔMV_persuade    persuasion
p̃_u = max(station resident turnout, locality resident turnout − 0.12);  ρ_p = 0.003 / 0.22
resident roll_u = roll_u · growth · (1 − abroad) · capacity
door potential = Σ_(u positive, not Arab-led) value_u · 0.35 · resident roll_u
list potential = Σ_(u negative) value_list,u · 0.30 · 0.50 · target group_u  (+ rescue calls in any station)</div>
    <p>Values are computed for every polling station; the turnout lift uses the guarded turnout p̃ so that stations far below their locality, often stale rolls, do not look like mobilisable abstainers. A locality's potential adds door potential on its positive stations and list potential on the rest. Efficiency per volunteer-hour assumes completed door conversations per hour of 4 in dense apartment blocks, 3 in other urban turf, 2 in rural communities and 1.5 in Bedouin villages.</p>
    <h3>9. The planner</h3>
    <p>Each locality's stations are grouped into four capacity tranches per programme, best first. The planner sorts every tranche in the country by value per contact and spends the budget from the top. Door teams go only to localities with at least ${fmtInt(S.min_area)} positive-value contacts available and allocated. List programmes scale with the identified share. The executive summary's four budgets use the same allocation, excluding Arab localities, polling stations where Arab lists lead, the access-excluded villages and, until the candidate check, Druze and Circassian towns.</p>
    <h3>10. Tiers</h3>
    <p>Arab localities are always <i>Arab-list turf (partner-led)</i>. Access-restricted localities are <i>not targeted</i>. Among the remaining localities with at least 2,000 eligible voters and a real programme (1,000+ contacts, potential above the median), those in the top 15% by potential or by efficiency get one of three tiers. They are <i>persuasion battlegrounds</i> if persuasion is their largest mechanism, <i>supporter-list ground</i> if list programmes are worth more than door work, and <i>turnout engines</i> otherwise. Localities where the Netanyahu bloc takes 70% or more and over 80% of the roll sits in net-negative stations are <i>Netanyahu-bloc strongholds</i>. Others are secondary targets (above the median potential) or low yield.</p>
    <h3>11. How robust are the rankings?</h3>
    <p>Every locality was re-ranked under ${nScen()} alternative assumptions covering the parameters the literature leaves most uncertain. The table shows how closely each alternative ranking of total potential tracks the base case among the ${fmtInt(so.change_govt ? so.change_govt.n_target : 0)} targetable localities with 1,000+ eligible voters (Spearman correlation, and how many of the top 25 stay in the top 25), and how many of the top 25 localities by door efficiency (net votes per door conversation) stay there. Total potential is largely a size measure, so it is stable; the per-contact order is much less so.</p>
    ${sensTable()}
    <p class="note">${so.change_govt ? `${so.change_govt.n_always_top25_target} localities are in the top 25 for a change-led government under every scenario, and ${so.block_nb.n_always_top25_target} for denying Netanyahu 61. Each locality profile shows its rank range across the scenarios.` : ""} For total potential, the supporter-list assumption and the shape of the turnout effect move the order most, with persuasion strength close behind. For door efficiency, the shape of the turnout effect dominates: without the hump, fewer than half of the top 25 stay. Residents abroad, rescue rates and the projection blend barely move either.</p>
    <h3>12. Parameters</h3>
    <div class="tblwrap" style="max-height:none;margin-top:14px"><table class="t static"><thead><tr><th>Parameter</th><th>Value used</th><th>Range in the literature</th><th>Basis</th></tr></thead><tbody>
    ${[
      ["Door-conversation turnout effect", `1.5 pts at 15% resident turnout; about ${doorLift().toFixed(2)} pts as applied in door turf`, "0.5–3.0", "US high-salience CACE about 3; European pooled 0.8", ["D3-F01", "D3-F22"]],
      ["Turnout hump", "×1.0 at 15%, ×1.8 at 42.5%, ×0.4 at 75%, ×0.1 at 95% resident turnout", "peak 1.2–2.5×", "Canvassing CACE by control-group turnout band", ["D3-F03"]],
      ["Household spillover", "×1.3", "1.0–1.6", "About 60% to the second household member, discounted", ["D3-F15", "D3-F10"]],
      ["Cross-bloc persuasion", "0.3% of contacted soft Netanyahu-bloc voters, at the door or by call", "0–1.5%", "General-election contact about 0.1–0.6 pts", ["P-F01", "P-F02"]],
      ["Cross-pressured share of soft NB voters", "22% (national pool about 2% of voters)", "measured 0.6–1.6% undecided between blocs", "Calibration constant at the upper end of measured indecision; sensitivity runs at 10% and 40%", ["D5-F08", "D5-F09"]],
      ["Rescue (calls to identified voters)", "5% of contacted move; 60% to change lists, 40% to Likud", "2–15%", "Insurance voting, late desertion of sub-threshold lists", ["P-F23", "P-F26"]],
      ["List programmes", "30% identified, half reached", "planner slider", "Planning assumption", []],
      ["Supporter turnout gap", "+10 pts over the area", "—", "Planning assumption", []],
      ["Residents abroad on the roll", "8% national (3–13% by segment)", "6–10%", "INSS and CBS estimates; post-2022 emigration", ["D2-F14", "D2-F15"]],
      ["Double-envelope add-back", "2.9–13 pts by district and segment", "—", "Envelope-adjusted 2022 locality turnout", ["D2-F04"]],
      ["Contact capacity", "35% of the resident roll", "25–40%", "Practitioner contact rates", ["D3-F01"]],
      ["Projection blend; Druze pooling", "50% uniform camp swing; 60% toward the Druze mean", "—", "Held-out test (section 5)", []],
    ].map(r => `<tr><td style="white-space:normal;min-width:180px"><b>${r[0]}</b></td><td style="white-space:normal">${r[1]}</td><td style="white-space:normal">${r[2]}</td><td style="white-space:normal;min-width:240px">${r[3]}${cites(r[4])}</td></tr>`).join("")}
    </tbody></table></div>
    <h3>13. Sizing the strategic levers</h3>
    <p>The Strategy page and the levers chart size each lever with a scenario engine. For every one of the forecast's 8,000 simulated elections, it moves votes between lists as the scenario states: for example, all of Blue and White's votes to Yashar (60%) and Together (25%) with the rest abstaining, the list's 2022 transfer pattern; or half a point of the national vote from Likud to the four change lists in proportion to their size. It then re-runs the full seat law, with the threshold, the six surplus pairs and Bader-Ofer, and the government-formation model with the same 60 behaviour vectors and random numbers as the baseline. Because nothing is linearised, threshold effects are captured: a list that falls out or gets in changes the seat count the way it would on the night. The field programme is sized with the planner instead (section 9) and converted with the exchange rate (section 6).</p>
    <p>The engine answers "what is this worth if it happens", not "will it happen". Whether a lever can be pulled in the time left is a separate judgement, which the Strategy page makes lever by lever from the research literature and the 2026 reporting.</p>
    <h3>14. What the atlas does not do</h3>
    <ul>
      <li>It does not estimate how much a given message or ad budget will move. The persuasion and turnout levers are sized as scenarios ("if half a point moves"), and the Messaging page draws on experiments mostly from other countries; ad effects decay within days.${cites(["P-F06", "P-F07"])}</li>
      <li>It ranks places, not people. Campaigns with good supporter files can target individuals within a station, which raises yields above these turf-level figures.</li>
      <li>Polling-station numbers are from 2022. The 2026 station list differs, so map 2022 stations to 2026 stations by address before deployment.</li>
      <li>Druze and displaced border communities are the least certain projections: local candidates dominate Druze voting, and many residents near the borders have not returned.${cites(["D2-F11", "D5-F20"])}</li>
      <li>Effect sizes come from experiments abroad. Our research desks found no randomised turnout experiment from Israel, so every parameter carries a range, and rankings are more reliable than absolute totals.</li>
      <li>The formation model behind the main objective rests on judgements about coalition behaviour. The blocking objective rests only on seat arithmetic and is offered for that reason.</li>
      <li>It gives no legal advice. Election-day transport, gifts, propaganda near polling stations and poll publication are regulated; check with election counsel.</li>
    </ul>
    <h3>15. Data files</h3>
    <p><a href="localities.csv" target="_blank" rel="noopener">localities.csv</a>: one row per locality with projections, flags, tiers and potentials (columns ending <code>__potential</code>, <code>__area_pot</code> and so on, per objective); Arab localities carry no targeting values. <a href="kalpi_targets.csv" target="_blank" rel="noopener">kalpi_targets.csv</a>: every targetable 2022 polling station (outside Arab localities, excluding stations where Arab lists lead) with its projection, lead change list and door value per 1,000 conversations per objective.</p>
  </div></section>`;
}
function sensTable() {
  const SV = D.sensitivity;
  if (!SV || !SV.objectives) return "";
  const a = SV.objectives.change_govt.scenarios, b = SV.objectives.block_nb.scenarios;
  const sp = x => x && x.target ? x.target.spearman.toFixed(2) : "—";
  const kept = x => x && x.target ? x.target.top25_overlap + " / 25" : "—";
  const eff = x => x && x.door_eff ? x.door_eff.top25_overlap + " / 25" : "—";
  return `<div class="tblwrap" style="max-height:none;margin-top:14px"><table class="t static"><thead><tr><th>Scenario</th><th class="n">Potential: Spearman, change-led govt</th><th class="n">Top 25 kept</th><th class="n">Door efficiency: top 25 kept</th><th class="n">Potential: Spearman, deny 61</th><th class="n">Top 25 kept</th><th class="n">Door efficiency: top 25 kept</th></tr></thead><tbody>` +
    Object.keys(a).filter(kk => kk !== "base").map(kk => `<tr><td style="white-space:normal">${esc(SV.labels[kk] || kk)}</td><td class="n">${sp(a[kk])}</td><td class="n">${kept(a[kk])}</td><td class="n">${eff(a[kk])}</td><td class="n">${sp(b[kk])}</td><td class="n">${kept(b[kk])}</td><td class="n">${eff(b[kk])}</td></tr>`).join("") + `</tbody></table></div>`;
}
// average turnout lift applied in door turf (change-led government), points
function doorLift() {
  const ids = ALL.filter(i => isTarget(i) && (ov("area_contacts", i, "change_govt") || 0) > 0);
  const w = d3.sum(ids, i => ov("area_contacts", i, "change_govt"));
  return w ? d3.sum(ids, i => (L.lift[i] || 0) * ov("area_contacts", i, "change_govt")) / w : 0;
}

/* ============================================================ SOURCES */
function renderSources() {
  const root = document.getElementById("src-root");
  if (!SRC.length) { root.innerHTML = `<p class="muted" style="padding:30px 0">Bibliography not available in this build.</p>`; return; }
  const groups = ["Official data", "Data and model inputs", "Israeli voting behaviour", "Turnout in Israel", "Coordination and coalitions", "Messaging and media", "Field experiments: turnout", "Persuasion and targeting", "Campaign law and operations", "2026 campaign reporting"];
  const other = SRC.map((s, k) => [s, k]).filter(([s]) => !groups.includes(s.group));
  root.innerHTML = groups.map(g => {
    const items = SRC.map((s, k) => [s, k]).filter(([s]) => s.group === g);
    if (!items.length) return "";
    return `<section class="block srcgroup"><h3 class="h2">${esc(g)}</h3><ol class="srclist">${items.map(srcItem).join("")}</ol></section>`;
  }).join("") + (other.length ? `<section class="block srcgroup"><h3 class="h2">Other</h3><ol class="srclist">${other.map(srcItem).join("")}</ol></section>` : "");
}
function srcItem([s, k]) {
  const safeUrl = /^https?:\/\//i.test(s.url || "") ? s.url : "";
  const st = /unverif|unconfirm/i.test(s.checked || "") ? " · not independently verified" : "";
  return `<li id="src-${k}">${esc(s.citation)} ${safeUrl ? `<a href="${esc(safeUrl)}" target="_blank" rel="noopener">Link</a>` : ""} <span class="used">· ${esc(s.status || "")}${st}${s.note ? " · " + esc(s.note) : ""}</span></li>`;
}

/* ============================================================ ROUTER */
let route = "summary";
const ROUTES = { summary: renderSummary, strategy: renderStrategy, messaging: renderMessaging, coalition: renderCoalition, map: renderMap, rankings: () => renderRankings(), segments: renderSegments, playbook: renderPlaybook, planner: renderPlanner, method: renderMethod, sources: renderSources };
const FIELD = new Set(["playbook", "map", "rankings", "segments", "planner", "loc"]);
function go() {
  let h;
  try { h = decodeURIComponent((location.hash || "#summary").slice(1)); } catch (e) { h = "summary"; }
  let r = h, arg = null;
  if (h.startsWith("loc-")) { r = "loc"; arg = h.slice(4); }
  else if (h.startsWith("src-")) { r = "sources"; arg = h; }
  else if (h.startsWith("seg-")) { r = "segments"; arg = h; }
  else if (!hasOwn(ROUTES, h)) r = "summary";
  route = r;
  document.querySelectorAll(".page").forEach(p => p.classList.toggle("on", p.id === "p-" + r));
  const top = FIELD.has(r) ? "field" : r;
  document.querySelectorAll(".nav a[data-route]").forEach(a => { if (a.dataset.route === top) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  const sub = document.getElementById("subnav");
  if (sub) { sub.hidden = !FIELD.has(r); sub.querySelectorAll("a[data-sub]").forEach(a => { if (a.dataset.sub === (r === "loc" ? "rankings" : r)) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); }); }
  hideTip();
  if (r === "loc") renderLoc(arg); else ROUTES[r]();
  const navA = document.querySelector(`.subnav a[data-sub="${r}"]`) || document.querySelector(`.nav a[data-route="${r}"]`);
  document.title = (r === "loc" ? (IDX.has(+arg) ? L.en[IDX.get(+arg)] : "Locality") : (navA ? navA.textContent : "Summary")) + " · Change Bloc Victory Guide";
  const el = arg && (r === "sources" || r === "segments") ? document.getElementById(arg) : null;
  if (el) setTimeout(() => el.scrollIntoView({ block: "start" }), 30);
  else window.scrollTo({ top: 0, behavior: "instant" });
}
function rerender() {
  hideTip();
  if (route === "loc") { let a = ""; try { a = decodeURIComponent((location.hash || "").slice(5)); } catch (e) { a = ""; } renderLoc(a); }
  else ROUTES[route]();
}
let lastW = window.innerWidth;
let rt;
window.addEventListener("resize", () => {
  clearTimeout(rt);
  rt = setTimeout(() => {
    if (window.innerWidth === lastW) return;
    lastW = window.innerWidth;
    if (route === "map") { initMap(true); renderMap(); } else { mapInit = false; rerender(); }
  }, 250);
});
setupMapControls();
setupRankings();
window.addEventListener("hashchange", go);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (!theme) rerender(); });
go();
})();
