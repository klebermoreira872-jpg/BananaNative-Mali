#!/usr/bin/env python3
"""Shaders that players' runs asked for and the game's shader library lacked, merged into a profile's shader_seen.tsv.

    python3 scripts/shader_harvest.py [PATH ...] [--game <title ID>] [--apply] [--note TEXT]

PATH is a log, a missing_shaders.tsv, a zip of them or a folder (searched for *.log, *.txt, missing_shaders.tsv and *.zip); default $BN_ISSUES_DIR, else
the folder `$BN_ISSUES_DIR` names, or the paths given (scripts/issue_digest.py keeps the issues' logs in its issues folder). Three sources are read:
  - `[shaders-missing] <key><TAB><stage>` lines of a game's log (the host notes each missing key once),
  - the rows `key<TAB>stage` of a missing_shaders.tsv (the host's $DM_TEMP file; a player attaches it to an issue),
  - older logs' `[RED] vk: shader <key> (program stage N) is not in the shader library` lines (no stage: taken from the profile's shader_map.tsv).
The game is the title ID in the log's file name (`issue-<title ID>-<time>.log`), its header, or --game (needed for a bare .tsv). Only a profile that has a
shader_seen.tsv (a selected set, android/SHADERS.md "Selected shaders") takes keys; a game that builds its whole map is listed and left alone. Without --apply
nothing is written. With it the new keys of each such game are appended to its shader_seen.tsv (one `# Added later:` comment line, then rows key<TAB>stage), each key
once; a key the profile's shader_map.tsv does not have cannot be built by the pack's step: it is reported and not added (the run-time layer builds it, or it is a
shader of another build of the game). A key's pixel shaders are not listed: the build adds the pairs itself.
Exit code: 0, 2 on a bad argument."""
import argparse
import datetime
import io
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / 'dm/games'
NEW_RX = re.compile(r'\[shaders-missing\] ([0-9a-f]{16})\t(\S+)')
OLD_RX = re.compile(r'\[RED\] vk: shader ([0-9a-f]{16}) \(program stage \d+\) is not in the shader library')
ROW_RX = re.compile(r'^([0-9a-f]{16})\t(\S+)\s*$')
TID_RX = re.compile(r'(?<![0-9A-Fa-f])(0[14][0-9A-Fa-f]{2}[0-9A-Fa-f]{12})(?![0-9A-Fa-f])')
STAGES = ('vertex', 'pixel', 'compute', 'geometry', 'hull', 'domain', 'task', 'mesh', '?')


def parse_text(text, tsv=False):
    """{key: stage or None} of a log's or a missing_shaders.tsv's text (a key's stage once known is kept)"""
    out = {}
    for ln in text.splitlines():
        if tsv:
            m = ROW_RX.match(ln)
            if m: out[m.group(1)] = out.get(m.group(1)) or (m.group(2) if m.group(2) != '?' else None)
            continue
        m = NEW_RX.search(ln)
        if m: out[m.group(1)] = out.get(m.group(1)) or (m.group(2) if m.group(2) != '?' else None)
        else:
            m = OLD_RX.search(ln)
            if m: out.setdefault(m.group(1), None)
    return out


def game_of(name, text):
    for s in (name, text[:20000]):
        m = TID_RX.search(s)
        if m: return m.group(1).upper()
    return None


def files(paths):
    """(name, text, is tsv) of every readable source under the paths"""
    for p in map(Path, paths):
        cand = sorted(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else [p]
        for q in cand:
            if q.name.endswith('.digest') or q.name.endswith('.digest.txt'): continue
            if q.suffix == '.zip':
                try:
                    with zipfile.ZipFile(q) as z:
                        for i in z.infolist():
                            if i.is_dir() or i.file_size > 256 << 20: continue
                            if i.filename.endswith(('.log', '.txt', 'missing_shaders.tsv')):
                                yield f'{q.name}/{i.filename}', io.TextIOWrapper(z.open(i), encoding='utf-8', errors='replace').read(), i.filename.endswith('.tsv')
                except (OSError, zipfile.BadZipFile): pass
            elif q.suffix in ('.log', '.txt') or q.name.endswith('missing_shaders.tsv'):
                try: yield q.name, q.read_text(encoding='utf-8', errors='replace'), q.name.endswith('missing_shaders.tsv')
                except OSError: pass


def collect(paths, game=None):
    """{title ID or None: {key: stage or None}} over every source"""
    by = {}
    for name, text, tsv in files(paths):
        g = game or game_of(name, text)
        d = parse_text(text, tsv)
        if not d: continue
        m = by.setdefault(g, {})
        for k, st in d.items(): m[k] = m.get(k) or st
    return by


def read_rows(path):
    out = {}
    if path.is_file():
        for ln in path.read_text(encoding='utf-8').splitlines():
            if ln and not ln.startswith('#'):
                c = ln.split('\t')
                if len(c) >= 2: out[c[0]] = c[1]
    return out


def shader_map(g):
    """{key: stage} of the profile's shader_map.tsv (column 3 stage, column 4 key)"""
    out = {}
    p = GAMES / g / 'shader_map.tsv'
    if p.is_file():
        for ln in p.read_text(encoding='utf-8').splitlines():
            c = ln.split('\t')
            if len(c) >= 4 and not ln.startswith('#') and len(c[3]) == 16: out[c[3]] = c[2]
    return out


def plan(by):
    """[(game, new rows [(key, stage)], keys outside the map, known count, selected?)]"""
    res = []
    for g, keys in sorted(by.items(), key=lambda x: x[0] or ''):
        seen_p = GAMES / g / 'shader_seen.tsv' if g else None
        if not g or not (GAMES / g).is_dir():
            res.append((g, [], sorted(keys), 0, False)); continue
        mp = shader_map(g); seen = read_rows(seen_p)
        new, out = [], []
        for k, st in sorted(keys.items()):
            if k in seen: continue
            if k not in mp: out.append(k); continue
            new.append((k, mp[k]))
        res.append((g, new, out, len(keys) - len(new) - len(out), seen_p.is_file()))
    return res


def apply(g, new, note, today):
    p = GAMES / g / 'shader_seen.tsv'
    txt = p.read_text(encoding='utf-8')
    if not txt.endswith('\n'): txt += '\n'
    by = {}
    for k, st in new: by.setdefault(st, []).append(k)
    what = ', '.join(f'{st} {", ".join(ks)}' for st, ks in sorted(by.items()))
    txt += f'# Added later ({today}): {len(new)} shaders ({what}) that play reached and the library lacked, from players\' logs{": " + note if note else ""}.\n'
    txt += ''.join(f'{k}\t{st}\n' for k, st in new)
    p.write_text(txt, encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--game', help='title ID of the sources that name none')
    ap.add_argument('--apply', action='store_true', help='append the new keys to each selected-set profile\'s shader_seen.tsv')
    ap.add_argument('--note', default='')
    a = ap.parse_args(argv)
    paths = a.paths or ([os.environ['BN_ISSUES_DIR']] if os.environ.get('BN_ISSUES_DIR') else [])
    if not paths: sys.exit('shader_harvest: name a folder of logs or set BN_ISSUES_DIR')
    for p in paths:
        if not Path(p).exists(): print(f'[RED] {p}: not found', file=sys.stderr); return 2
    by = collect(paths, a.game.upper() if a.game else None)
    if not by: print('no missing shaders in the sources'); return 0
    today = datetime.date.today().isoformat()
    for g, new, out, known, selected in plan(by):
        name = g or '(game not known: give --game)'
        print(f'{name}: {len(new)} new, {known} already listed, {len(out)} not in the profile\'s shader map')
        if g and new and not selected:
            print('  this game builds its whole map (no shader_seen.tsv): nothing to add; these keys are not in its library, which is a defect to look at:')
        for k, st in new: print(f'  {k}\t{st}')
        for k in out: print(f'  {k}\tnot in the map')
        if a.apply and g and new and selected:
            apply(g, new, a.note, today); print(f'  appended to dm/games/{g}/shader_seen.tsv')
    return 0


if __name__ == '__main__':
    sys.exit(main())
