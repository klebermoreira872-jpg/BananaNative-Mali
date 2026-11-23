#!/usr/bin/env python3
"""A ranked order of a game's shaders from the profile's static tables alone (no play, no game files, no network).

    python3 dm/tools/shader_priority.py <title ID> [--top N] [--no-sibling] [--eval] [--out FILE]

Reads dm/games/<id>/shader_map.tsv (key, stage, source; the source names where a key first appears), shader_facts.tsv (the thread group of compute shaders) and,
unless --no-sibling, the shader_map.tsv + shader_seen.tsv of the OTHER profiles (never the game's own shader_seen.tsv). Writes dm/games/<id>/shader_priority.tsv:
`key<TAB>stage<TAB>score<TAB>reason`, best first, the first --top rows (default 20000; 0 = all). The file is generated and git ignores it. The order is
deterministic: equal scores order by the size of the shader's container (small first), then the map's order.

What the tables offer (android/SHADERS.md, "A shader order without playing"): `shader_pairs.tsv` / `pso_pairs.tsv` carry no signal (every vertex shader is paired
with the same one or two pixel shaders), `shader_facts.tsv` only the thread group of compute shaders. The usable signals are
  - where the shader lives: inside the executable or a file that is not the game's bulk archive ("loose"), against the bulk file holding most shaders;
  - the stage (tessellation, geometry and mesh shaders are rarely asked for early);
  - the container (a shader archive's resource, or a UE asset) as a unit: play asks for a whole container or none, so a container whose shape (stage order and
    code sizes from the GLSLC offsets) occurs once in the game is likelier than one repeated many times (per-material variants);
  - a sibling profile: a container of the same shape in another game of the same engine, and what share of it that game's play asked for.
`--eval` prints the coverage of the game's own shader_seen.tsv by the top N (N = 1000, 2000, 5000, 10000, 20000), against the share a random order gives.
Exit code: 0, 2 on a bad argument."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAMES = ROOT / 'dm/games'
KEY_RX = re.compile(r'^[0-9a-f]{16}$')
RARE_STAGES = ('domain', 'hull', 'geometry', 'mesh', 'task')
TOPS = (1000, 2000, 5000, 10000, 20000)
MIN_CONTAINER = 20      # a container smaller than this is not judged by its shape


def read_map(path):
    """[(key, stage, source)] in file order"""
    out = []
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        if ln.startswith('#') or not ln.strip():
            continue
        f = ln.split('\t')
        if len(f) >= 5 and KEY_RX.match(f[3]):
            out.append((f[3], f[2], f[4]))
    return out


def read_seen(path):
    """{key: stage} of a shader_seen.tsv (rows key<TAB>stage; a bare key column is read too)"""
    out = {}
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        f = ln.split('\t')
        if f and KEY_RX.match(f[0].strip()):
            out[f[0].strip()] = f[1].strip() if len(f) > 1 else None
    return out


def read_facts(path):
    out = {}
    p = Path(path)
    if not p.exists():
        return out
    for ln in p.read_text(encoding='utf-8').splitlines():
        if ln.startswith('#') or '\t' not in ln:
            continue
        k, j = ln.split('\t', 1)
        try:
            out[k] = json.loads(j)
        except ValueError:
            pass
    return out


def container_of(source):
    """The container a source names: `<file>#IDRK@<id>` of a Kids-platform archive, else the source without its member suffix (`#UE...`, `#GLSLC@...`)"""
    m = re.match(r'^(.*?#IDRK@0x[0-9a-f]+)', source)
    if m:
        return m.group(1)
    return re.sub(r'#(UE[0-9a-f]+|GLSLC@0x[0-9a-f]+)$', '', source)


def file_of(source):
    return re.sub(r'#.*', '', source)


def code_offset(source):
    m = re.search(r'GLSLC@0x([0-9a-f]+)', source)
    return int(m.group(1), 16) if m else 0


def containers(rows):
    """{container: [row index]} in map order"""
    out = {}
    for i, (_, _, src) in enumerate(rows):
        out.setdefault(container_of(src), []).append(i)
    return out


def shape(rows, idx):
    """A container's shape: the stage order and the gaps between its code offsets (the shaders' sizes), hashed. Equal in the games of one engine."""
    offs = [code_offset(rows[i][2]) for i in idx]
    s = ''.join(rows[i][1][0] for i in idx) + '|' + ','.join(str(offs[j + 1] - offs[j]) for j in range(len(offs) - 1))
    return hashlib.md5(s.encode()).hexdigest()[:12]


def sibling_prior(own_id):
    """{shape: share of the container's shaders that a sibling's play asked for (the highest of the siblings')} from every other profile with a map and a seen list"""
    out = {}
    for d in sorted(GAMES.iterdir()):
        if d.name == own_id or not (d / 'shader_map.tsv').exists() or not (d / 'shader_seen.tsv').exists():
            continue
        rows = read_map(d / 'shader_map.tsv')
        seen = read_seen(d / 'shader_seen.tsv')
        for idx in containers(rows).values():
            if len(idx) < MIN_CONTAINER:
                continue
            f = sum(rows[i][0] in seen for i in idx) / len(idx)
            sh = shape(rows, idx)
            out[sh] = max(out.get(sh, 0.0), f)
    return out


def rank(game, sibling=True):
    """[(key, stage, score, reason)] best first, deterministic"""
    d = GAMES / game
    rows = read_map(d / 'shader_map.tsv')
    facts = read_facts(d / 'shader_facts.tsv')
    cont = containers(rows)
    files = {}
    for _, _, src in rows:
        files[file_of(src)] = files.get(file_of(src), 0) + 1
    bulk = max(files, key=lambda f: (files[f], f)) if files else ''
    prior = sibling_prior(game) if sibling else {}
    shapes = {c: shape(rows, idx) for c, idx in cont.items() if len(idx) >= MIN_CONTAINER}
    mult = {}
    for sh in shapes.values():
        mult[sh] = mult.get(sh, 0) + 1
    out = []
    for c, idx in cont.items():
        sh = shapes.get(c)
        for i in idx:
            key, stage, src = rows[i]
            p, why = 0.03, ['bulk']
            if file_of(src) != bulk:
                p, why = (0.6, ['in the executable']) if file_of(src) == 'main' else (0.3, ['loose file'])
            if stage in RARE_STAGES:
                p *= 0.2
                why.append(stage)
            elif stage == 'compute' and facts.get(key, {}).get('local') == [64, 1, 1]:
                p = max(p, 0.5)
                why.append('compute 64x1x1')
            if sh is not None:
                if mult[sh] == 1:
                    p *= 2
                    why.append('unique container shape')
                elif mult[sh] >= 3:
                    p *= 0.5
                    why.append('shape repeated %d times' % mult[sh])
                if prior.get(sh, 0) >= 0.5:
                    p = max(p, 0.9 * prior[sh])
                    why.append('sibling asked for %d%% of the same container' % round(100 * prior[sh]))
            out.append((len(idx), i, key, stage, p, '; '.join(why)))
    out.sort(key=lambda t: (-t[4], t[0], t[1]))
    return [(k, s, p, w) for _, _, k, s, p, w in out]


def coverage(order, seen):
    """{N: (found, share of seen)} for the top N of order"""
    res = {}
    total = max(1, len(seen))
    for n in TOPS:
        found = sum(1 for k, *_ in order[:n] if k in seen)
        res[n] = (found, found / total)
    return res


def write(game, order, top, out):
    rows = order[:top] if top else order
    lines = ['# Static order of the shaders (dm/tools/shader_priority.py, generated, do not edit): key\tstage\tscore\treason']
    lines += ['%s\t%s\t%.4f\t%s' % (k, s, p, w) for k, s, p, w in rows]
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('game')
    ap.add_argument('--top', type=int, default=20000)
    ap.add_argument('--no-sibling', action='store_true')
    ap.add_argument('--eval', action='store_true')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    d = GAMES / a.game
    if not (d / 'shader_map.tsv').exists():
        print('no shader_map.tsv in dm/games/%s' % a.game, file=sys.stderr)
        return 2
    order = rank(a.game, not a.no_sibling)
    if a.eval:
        if not (d / 'shader_seen.tsv').exists():
            print('no shader_seen.tsv to measure against', file=sys.stderr)
            return 2
        seen = {k: s for k, s in read_seen(d / 'shader_seen.tsv').items()}
        mapkeys = {k for k, *_ in order}
        seen = {k: s for k, s in seen.items() if k in mapkeys}
        print('%s: map %d, seen %d (%.1f%% of the map)' % (a.game, len(order), len(seen), 100 * len(seen) / len(order)))
        for n, (f, sh) in coverage(order, seen).items():
            rnd = min(1.0, n / len(order))
            print('  top %6d: %5d seen keys = %5.1f%% of seen (precision %4.1f%%, random order %4.1f%%)' % (n, f, 100 * sh, 100 * f / n, 100 * rnd))
        return 0
    write(a.game, order, a.top, a.out or d / 'shader_priority.tsv')
    return 0


if __name__ == '__main__':
    sys.exit(main())
