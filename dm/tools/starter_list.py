#!/usr/bin/env python3
"""Make a game's starter set (dm/games/<id>/shader_first.tsv) from phone runs that started with no shader library.

    python3 starter_list.py --game <title ID> --harvest <folder> [--harvest <folder> ...] [--limit N] [--out FILE]

A harvest folder (made by a run of the test app with the game's shader library moved away and a fresh save; the requests are game data and stay in the game's work folder, never in
the repository) holds `req/<key>.ctl` and `.code` and `order.txt` (`<seconds> <key>` per request: when the run asked for it, oldest first). The list is the keys in the order they were asked for, the first
harvest first, a key that two harvests share once; each row is `key<TAB>stage`. Only keys of the game's own shader_map.tsv are kept (shader_seed.py finds a record by that map); the others are counted.
The file carries a header comment with the run's size and no game data: a key is a hash.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_order(folder):
    """[key, ...] of a harvest folder in the order the run asked for them (order.txt: `<time> <key>`; without it the .ctl files' times)"""
    folder = Path(folder)
    keys = []
    o = folder / 'order.txt'
    if o.is_file():
        rows = [ln.split() for ln in o.read_text().splitlines() if ln.strip()]
        keys = [r[1] for r in sorted(rows, key=lambda r: (int(r[0]), r[1])) if len(r) >= 2]
    else:
        keys = [p.stem for p in sorted((folder / 'req').glob('*.ctl'), key=lambda p: (p.stat().st_mtime, p.name))]
    return keys


def stages_of(folder, keys, game):
    """{key: stage} from each request's control and code (dm/gfx/tools/shader_layer.py read_requests: the stage is not stored in a request)"""
    os.environ.setdefault('DM_GAME', game)
    sys.path.insert(0, str(HERE.parent / 'gfx' / 'tools')); sys.path.insert(0, str(HERE.parent / 'games'))
    import shader_layer as L   # noqa: E402
    import game as G           # noqa: E402
    reqs, _bad, _pairs = L.read_requests(Path(folder) / 'req', G.load(game), now=0, grace=0)   # (now=0: nothing is old enough to be deleted)
    return {k: v[2] for k, v in reqs.items() if k in set(keys)}


def map_keys(game):
    keys = set()
    with open(HERE.parent / 'games' / game / 'shader_map.tsv', encoding='utf-8') as f:
        for ln in f:
            c = ln.rstrip('\n').split('\t')
            if len(c) >= 4 and not ln.startswith('#'): keys.add(c[3])
    return keys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', required=True)
    ap.add_argument('--harvest', action='append', required=True)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    inmap = map_keys(a.game)
    rows, seen, outside = [], set(), 0
    for h in a.harvest:
        stages = stages_of(h, read_order(h), a.game)
        for k in read_order(h):
            if k in seen or k not in stages: continue
            seen.add(k)
            if k not in inmap: outside += 1; continue
            rows.append((k, stages[k]))
    if a.limit: rows = rows[:a.limit]
    out = Path(a.out) if a.out else HERE.parent / 'games' / a.game / 'shader_first.tsv'
    text = (f'# starter set: the shaders a first start with no shader library asks for first, in that order ({len(rows)} keys of {len(a.harvest)} run(s); {outside} asked-for keys are not in shader_map.tsv)\n'
            '# key\tstage; made by dm/tools/starter_list.py, read by dm/gfx/tools/shader_seed.py\n') + ''.join(f'{k}\t{s}\n' for k, s in rows)
    out.write_text(text, encoding='utf-8')
    print(f'{out}: {len(rows)} keys ({outside} not in the map)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
