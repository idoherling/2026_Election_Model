"""Build the gh-pages branch: the built sites as plain static files, for
GitHub Pages.

    python src/publish_pages.py     build or refresh the local gh-pages branch
    git push origin gh-pages        publish it

Layout of the branch (https://idoherling.github.io/2026_Election_Model/):

    /                 output/site/        the Knesset Model: forecast, insights,
                                          scorecard, election night, decision log
    /victory-guide/   output/targeting/   the Change Bloc Victory Guide and its
                                          two CSV downloads

Every file is taken from the committed tree (HEAD), never from the working
tree, so the hosted pages are exactly a commit of main. The branch is
written with git plumbing (a temporary index, write-tree, commit-tree): no
checkout, and the working tree and the real index are untouched.

The Victory Guide was written for a host that supplies the document
skeleton, so it starts at <title>. SKELETON gives it a doctype, charset,
viewport and the same small reset; the file on main is not changed.
"""
from __future__ import annotations   # the venv is Python 3.9

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = "gh-pages"
URL = "https://idoherling.github.io/2026_Election_Model/"

SKELETON = (
    '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
    "padding-bottom:env(safe-area-inset-bottom,0px)}"
    'body{margin:0;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}'
    "img{max-width:100%}[hidden]{display:none!important}</style>\n")

# (path on main, path on the branch, wrap in SKELETON)
SINGLE = [
    ("output/targeting/index.html", "victory-guide/index.html", True),
    ("output/targeting/localities.csv", "victory-guide/localities.csv", False),
    ("output/targeting/kalpi_targets.csv", "victory-guide/kalpi_targets.csv", False),
]
SITE_DIR = "output/site"      # every committed file under it goes to the root

BRANCH_README = """# Hosted pages (generated)

This branch is built by `src/publish_pages.py` from a commit of `main` and
served by GitHub Pages at {url}

Do not edit it by hand: change the sources on `main`, rebuild, and run the
script again.
"""


def git(*args: str, data: bytes | None = None, env: dict | None = None) -> bytes:
    out = subprocess.run(["git", *args], cwd=ROOT, input=data, capture_output=True,
                         env=dict(os.environ, **(env or {})))
    if out.returncode:
        raise SystemExit(f"git {' '.join(args)}: {out.stderr.decode().strip()}")
    return out.stdout


def blob_of(path: str) -> str:
    """The blob id of a committed file."""
    line = git("ls-tree", "HEAD", "--", path).decode().strip()
    if not line:
        raise SystemExit(f"{path} is not committed on HEAD")
    return line.split()[2]


def new_blob(data: bytes) -> str:
    return git("hash-object", "-w", "--stdin", data=data).decode().strip()


def entries() -> dict:
    """{path on the branch: blob id}."""
    out = {}
    for line in git("ls-tree", "-r", "HEAD", "--", SITE_DIR).decode().splitlines():
        meta, path = line.split("\t", 1)
        out[path[len(SITE_DIR) + 1:]] = meta.split()[2]
    if "index.html" not in out:
        raise SystemExit(f"{SITE_DIR}/index.html is not committed on HEAD")
    for src, dst, wrap in SINGLE:
        if wrap:
            page = git("show", f"HEAD:{src}")
            if page.lstrip()[:9].lower().startswith(b"<!doctype"):
                out[dst] = blob_of(src)          # already a whole document
            else:
                out[dst] = new_blob(SKELETON.encode() + page)
        else:
            out[dst] = blob_of(src)
    out[".nojekyll"] = new_blob(b"")
    out["README.md"] = new_blob(BRANCH_README.format(url=URL).encode())
    return out


def build() -> str:
    head = git("rev-parse", "--short", "HEAD").decode().strip()
    files = entries()
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        for path, blob in sorted(files.items()):
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env).decode().strip()
    old = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{BRANCH}"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if old and git("rev-parse", f"{old}^{{tree}}").decode().strip() == tree:
        print(f"{BRANCH} is already the site of {head} ({len(files)} files): nothing to do")
        return old
    parents = ["-p", old] if old else []
    commit = git("commit-tree", tree, *parents, "-m", f"Hosted pages from main {head}").decode().strip()
    git("update-ref", f"refs/heads/{BRANCH}", commit)
    print(f"{BRANCH} -> {commit[:7]}: {len(files)} files from main {head}")
    print(f"publish with: git push origin {BRANCH}    ({URL})")
    return commit


if __name__ == "__main__":
    if sys.argv[1:]:
        raise SystemExit(__doc__)
    build()
