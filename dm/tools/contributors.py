#!/usr/bin/env python3
"""The README's contributor list: everyone with a merged pull request on Forgejo (moceure/BananaNative), plus the
GitHub-era and collaborator rows of contributors_extra.tsv. Rewrites the block between the contributors markers in
README.md; run it before a release snapshot (it reads Forgejo's public API, no token).

    python3 dm/tools/contributors.py           rewrite README.md
    python3 dm/tools/contributors.py --print   print the list only
"""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://git.eden-emu.dev/api/v1/repos/moceure/BananaNative/pulls?state=closed&limit=50&page={}"
SKIP = {"moceure", "seedds"}
START, END = "<!-- contributors:start -->", "<!-- contributors:end -->"


def forgejo_authors():
    out = set()
    for page in range(1, 200):
        req = urllib.request.Request(API.format(page), headers={"User-Agent": "BananaNative-contributors"})
        with urllib.request.urlopen(req, timeout=30) as r:
            prs = json.load(r)
        if not prs:
            break
        out |= {p["user"]["login"] for p in prs if p.get("merged")}
    return out


def extra():
    rows = {}
    for line in (ROOT / "dm/tools/contributors_extra.tsv").read_text().splitlines():
        if line and not line.startswith("#"):
            login, where = line.split("\t")[:2]
            rows[login] = where
    return rows


def block(forgejo, more):
    names = {n: "forgejo" for n in forgejo}
    for n, w in more.items():
        names.setdefault(n, w)
    links = []
    for n in sorted((n for n in names if n not in SKIP), key=str.lower):
        host = "https://git.eden-emu.dev" if names[n] == "forgejo" else "https://github.com"
        links.append(f"[{n}]({host}/{n})")
    return f"{START}\n{', '.join(links)}\n{END}"


def main():
    b = block(forgejo_authors(), extra())
    if "--print" in sys.argv:
        print(b)
        return
    readme = ROOT / "README.md"
    t = readme.read_text()
    i, j = t.index(START), t.index(END) + len(END)
    readme.write_text(t[:i] + b + t[j:])
    print(f"README.md: {b.count('](')} contributors")


if __name__ == "__main__":
    main()
