"""Render docs/priors_dossier.md as output/site/decision-log.html, a supporting
page published with the forecast so that every citation of the model's own
measurements ("decision log, s.43") links to the exact section.

The markdown is embedded verbatim and rendered client-side by marked
(cdnjs, pinned version); every "## N." heading gets the stable anchor #sN.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "priors_dossier.md"
OUT = ROOT / "output" / "site" / "decision-log.html"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision Log</title>
<style>
:root{--paper:#f5f3ee;--ink:#141412;--muted:#6f6b64;--accent:#0038b8;--rule:#14141222}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--paper:#101010;--ink:#f2efe8;--muted:#8f8b82;--accent:#5b8ded;--rule:#f2efe822}}
:root[data-theme="dark"]{--paper:#101010;--ink:#f2efe8;--muted:#8f8b82;--accent:#5b8ded;--rule:#f2efe822}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.6 "IBM Plex Sans","Helvetica Neue",Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:28px 16px 80px}
header{border-bottom:2px solid var(--ink);padding-bottom:12px;margin-bottom:18px}
header a{color:var(--accent)}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:20px;border-top:2px solid var(--ink);padding-top:18px;margin-top:34px;scroll-margin-top:12px}
h2:target{background:color-mix(in srgb,var(--accent) 10%,transparent)}
h3{font-size:16px}
a{color:var(--accent)}
code{font:13px "IBM Plex Mono",ui-monospace,monospace;background:var(--rule);padding:0 3px}
pre{overflow-x:auto;background:var(--rule);padding:10px}
table{border-collapse:collapse;font-size:13.5px;display:block;overflow-x:auto;max-width:100%}
th,td{border-bottom:1px solid var(--rule);padding:4px 8px;text-align:left;vertical-align:top}
blockquote{border-left:3px solid var(--muted);margin:0;padding-left:12px;color:var(--muted)}
.note{color:var(--muted);font-size:14px}
</style>
</head>
<body><div class="wrap">
<header><h1>Decision log</h1>
<div class="note">Every parameter and modelling decision behind <a href="index.html">The Knesset Model</a>,
with the measurements that justified it, in the order they were made. Sections are cited from the
forecast as "decision log, s.N". Rendered from the repository file docs/priors_dossier.md as of __ASOF__.</div>
</header>
<main id="log">Loading...</main>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/4.3.0/marked.min.js"></script>
<script>
const MD = __MD__;
const el = document.getElementById("log");
try {
  el.innerHTML = marked.parse(MD, {mangle:false, headerIds:false});
} catch (e) {
  el.textContent = MD;
}
el.querySelectorAll("h2").forEach(h => {
  const m = h.textContent.match(/^(\\d+)\\./);
  if (m) h.id = "s" + m[1];
});
el.querySelectorAll("a[href^='http']").forEach(a => a.rel = "noopener");
if (location.hash) { const t = document.querySelector(location.hash); if (t) t.scrollIntoView(); }
</script>
</body>
</html>
"""


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    import datetime as _dt
    asof = _dt.date.fromtimestamp(SRC.stat().st_mtime).isoformat()
    html = PAGE.replace("__MD__", json.dumps(md, ensure_ascii=False).replace("</", "<\\/")) \
               .replace("__ASOF__", asof)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(html)//1024} KB, {md.count(chr(10)+'## ')} sections)")


if __name__ == "__main__":
    main()
