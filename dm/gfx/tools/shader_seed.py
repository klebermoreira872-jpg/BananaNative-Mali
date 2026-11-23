#!/usr/bin/env python3
"""Seeds the run-time shader layer before the game asks (android/SHADERS.md, Seeding a first start): the requests of a starter list, written as the host writes them.

Usage: shader_seed.py --game <title ID> --root <layer folder> --first <shader_first.tsv> --romfs <spec> [--main <spec>] [--limit N] [--dry-run] [--jobs J]

--first: rows `key<TAB>stage` ('#' comments), most wanted first. For each key not requested yet, <root>/req/<key>.code and then <key>.ctl are written (the control section cut to the
host's 0xd8 bytes, the code unchanged; a .ctl is renamed into place last, so a request is whole when its .ctl exists), only when skey(ctl, code) of shader_split.py is the key.
The .ctl files' times run in the list's order, a few minutes in the past, so a build takes the list in its order (shader_layer.py read_requests sorts by that time) and every
request the game writes later is younger. The profile's pairs (shader_pairs.tsv) of two requested keys are appended to req/pairs.tsv, each once.
--romfs / --main: what shader_split.py takes (a folder, `game.nup:update/<v>/romfs`, `game.nup`, comma lists, the base game first). The records come from the RomFS files the profile's
shader_map.tsv names for the keys, read by shader_split.py's own readers (scan_jobs, scan_file; the phone's targeted split). A key whose source is no RomFS file (main's, a captured
one) or that is not found is counted and left out. Environment as the phone's split: DM_NUP_FD, J (workers; --jobs, default 2).
Exit 0 (seeded, or nothing to do), 2 a bad argument, 130 stopped (SIGINT: what was written is whole; the run can be repeated)."""
import argparse
import concurrent.futures as cf
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'games'))
if '--game' in sys.argv[:-1]: os.environ.setdefault('DM_GAME', sys.argv[sys.argv.index('--game') + 1])   # (shader_split.py reads the profile of DM_GAME when imported)
os.environ['DM_SPLIT_SELECTED'] = '0'   # the records are kept whole (shader_split.py keep_set)
import shader_split as S   # noqa: E402
import shader_layer as L   # noqa: E402

CTL_LEN = 0xd8        # the host's PROG_CTL_LEN_HOST (vka_shader.c layer_request): the control bytes a request keeps
AGE_S = 300           # the newest seed's age: past L.GRACE_S, so no run takes it for a request still being written
STEP_S = 0.001        # between two seeds' times: the list's order
NOT_ROMFS = S.NOT_ROMFS


class Bad(Exception): pass


def read_first(path, limit=None):
    """[(key, stage)] of a starter list, in order, each key once"""
    out, seen = [], set()
    try: lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError as e: raise Bad(f'--first {path}: {e}')
    for ln in lines:
        c = ln.split('\t')
        if not ln.strip() or ln.startswith('#'): continue
        if len(c[0]) != 16 or any(ch not in '0123456789abcdef' for ch in c[0]): raise Bad(f'--first {path}: "{ln[:40]}" is no row key<TAB>stage')
        if c[0] not in seen: seen.add(c[0]); out.append((c[0], c[1] if len(c) > 1 else ''))
    return out[:limit] if limit else out


def read_sources(map_path, keys):
    """{key: source} of the profile's shader_map.tsv (column 4 the key, column 5 where it first appears), for these keys"""
    out = {}
    with open(map_path, encoding='utf-8') as f:
        for ln in f:
            c = ln.rstrip('\n').split('\t')
            if len(c) > 4 and c[3] in keys and c[3] not in out: out[c[3]] = c[4]
    return out


def rel_of(source, rels):
    """The RomFS file of a map source ('/Shader/a.bfsha.zs#BNSH@0x10#var0', '/Lib/x.sarc.zs/member#BAHS...': the longest prefix ending at '/' or '#' or the end that is a file), None for
    main's and the captured ones (shader_split.py profile_files)"""
    if not source.startswith('/') or source.startswith(NOT_ROMFS): return None
    s = source[1:]
    return next((s[:i] for i in [i for i, ch in enumerate(s) if ch in '/#'] + [len(s)] if s[:i] in rels), None)


def list_files(romfs_l):
    """[(path, relative path)] of the RomFS list (shader_split.py main: the later versions' paths carry their folder's name), and the zstd dictionaries"""
    romfs_v = [S.nup.default_romfs(r) for r in romfs_l.split(',')]
    files = []
    for i, romfs in enumerate(romfs_v):
        tag = os.path.basename(os.path.dirname(os.path.abspath(romfs))) if i else ''
        files += sorted(((os.path.join(dp, f), (tag + '/' if tag else '') + S.posix_rel(os.path.join(dp, f), romfs)) for dp, _, fs in S.os.walk(romfs) for f in fs), key=lambda t: t[1])
    return files, {k: v for r in romfs_v for k, v in S.zs_dicts(r).items()}


def scan_files(files, zdicts, want, romfs_l, main_l, jobs):
    """Yields (relative path, {key: entry}) of the wanted RomFS files as each is scanned (scan_file's results; a file that holds nothing, or that no reader can read, gives {})"""
    mains = [m for m in (main_l or '').split(',') if m]
    common, nros = None, []
    if mains:
        try:
            import unityfs
            common = unityfs.common_strings(S.nso_image(mains[0]))
        except (ValueError, ImportError, OSError): common = None
        try: nros = S.runtime_nros(S.nup.default_romfs(romfs_l.split(',')[0]), mains[0])
        except Exception: nros = []
    big, todo = S.scan_jobs(files, want, mains, nros)
    batches = [[j] for j in big + todo]
    with S.pool(jobs, common, {}, zdicts) as ex:
        if isinstance(ex, S.InProcess):
            for b in batches:
                for rel, uniq, _, _ in S.scan_batch(b): yield rel, uniq
            return
        pending = {ex.submit(S.scan_batch_spilled, b) for b in batches}
        try:
            while pending:
                done, pending = cf.wait(pending, timeout=0.5, return_when=cf.FIRST_COMPLETED)
                for f in done:
                    for rel, uniq, _, _ in S.unspill(f.result()): yield rel, uniq
        finally:
            for f in pending: f.cancel()


def record(key, entry):
    """(control, code) as the host writes a request, or why the record is no request of that key: None when it is not the key's"""
    st, ctl, code = entry[1], bytes(entry[2]), bytes(entry[3])
    cut = ctl[:CTL_LEN]
    if S.skey(cut, code) != key: return None
    if not S.glslc_stage(cut, code): return None
    return cut, code


def write_request(req, key, ctl, code, when):
    """req/<key>.code, then req/<key>.ctl renamed into place with its time set: the request is whole when the .ctl exists. A failure leaves no .ctl"""
    req = Path(req); tmp_c, tmp_l = req / f'{key}.code.tmp', req / f'{key}.ctl.tmp'
    try:
        tmp_c.write_bytes(code); os.replace(tmp_c, req / f'{key}.code')
        tmp_l.write_bytes(ctl); os.utime(tmp_l, (when, when)); os.replace(tmp_l, req / f'{key}.ctl')
    finally:
        for t in (tmp_c, tmp_l): t.unlink(missing_ok=True)


def append_pairs(req, pairs_path, keys, dry=False):
    """The profile's (vertex, pixel) pairs of two keys in keys that req/pairs.tsv lacks, appended in the host's format. → number"""
    p = Path(req) / 'pairs.tsv'
    have = set()
    text = p.read_text(errors='replace') if p.is_file() else ''
    for ln in text.splitlines():
        c = ln.split('\t')
        if len(c) == 2: have.add((c[0], c[1]))
    new = []
    if Path(pairs_path).is_file():
        with open(pairs_path, encoding='utf-8') as f:
            for ln in f:
                if ln.startswith('#'): continue
                c = ln.rstrip('\n').split('\t')
                if len(c) == 2 and c[0] in keys and c[1] in keys and (c[0], c[1]) not in have: have.add((c[0], c[1])); new.append((c[0], c[1]))
    if new and not dry:
        with open(p, 'a', encoding='utf-8') as f:
            if text and not text.endswith('\n'): f.write('\n')   # (a last line cut short)
            f.write(''.join(f'{v}\t{x}\n' for v, x in new))
    return len(new)


def seed(game, root, first, rom, main=None, limit=None, dry=False, jobs=2, out=print):
    """→ (seeded, not found, already requested, pairs)"""
    rows = read_first(first, limit)
    req = Path(root) / 'req'
    S.KEY_SKIP = tuple(int(x, 0) for x in game.get('shader_key_skip', '0+0').split('+'))
    order = {k: i for i, (k, _) in enumerate(rows)}
    already = {k for k in order if (req / f'{k}.ctl').is_file()}
    todo = [k for k in order if k not in already]
    keyset = set(already)
    seeded = missing = 0
    if todo:
        src = read_sources(game.table('shader_map.tsv'), set(todo))
        files, zdicts = list_files(rom)
        rels = {r for _, r in files}
        by_rel, lost = {}, []
        for k in todo:
            r = rel_of(src[k], rels) if k in src else None
            if r is None: lost.append(k)
            else: by_rel.setdefault(r, []).append(k)
        missing = len(lost)
        if lost: out(f'seed: {len(lost)} keys have no RomFS file to read ({sum(1 for k in lost if k not in src)} not in the profile\'s map, the others in main or a captured shader or not in this dump)')
        base = time.time() - AGE_S - len(order) * STEP_S
        if not dry: req.mkdir(parents=True, exist_ok=True)
        total, n, left = len(todo) - missing, 0, {k for ks in by_rel.values() for k in ks}
        out(f'seed 0 {total}')
        try:
            for rel, uniq in (scan_files(files, zdicts, set(by_rel), rom, main, jobs) if by_rel else ()):
                for k in by_rel.get(rel, ()):
                    if k not in left: continue
                    rec = record(k, uniq[k]) if k in uniq else None
                    if rec is None: continue
                    if not dry: write_request(req, k, rec[0], rec[1], base + order[k] * STEP_S)
                    left.discard(k); keyset.add(k); n += 1; seeded += 1
                    out(f'seed {n} {total}')
                if not left: break
        except KeyboardInterrupt:
            out(f'seed: stopped after {seeded} requests (each written whole)')
            append_pairs(req, game.table('shader_pairs.tsv'), keyset, dry)
            raise
        missing += len(left)
        if left: out(f'seed: {len(left)} keys not found in {len(by_rel)} files')
    pairs = append_pairs(req, game.table('shader_pairs.tsv'), keyset, dry)
    out(f'seeded {seeded} requests ({missing} keys not found, {len(already)} already requested), {pairs} pairs' + (' (dry run: nothing written)' if dry else ''))
    return seeded, missing, len(already), pairs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', required=True); ap.add_argument('--root', required=True); ap.add_argument('--first', required=True)
    ap.add_argument('--romfs', required=True); ap.add_argument('--main')
    ap.add_argument('--limit', type=int); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--jobs', type=int, default=int(os.environ.get('J', '2')), help='scan workers (default J, else 2; 1 scans in this process)')
    try: a = ap.parse_args(argv)
    except SystemExit as e: return 2 if e.code else 0
    try:
        if a.limit is not None and a.limit < 1: raise Bad('--limit must be at least 1')
        if a.jobs < 1: raise Bad('--jobs must be at least 1')
        if not Path(a.first).is_file(): raise Bad(f'--first {a.first}: no such file')
        try: game = L.G.load(a.game)
        except (SystemExit, Exception) as e: raise Bad(f'--game {a.game}: {e}')
        if not os.path.isfile(game.table('shader_map.tsv')): raise Bad(f'the profile of {a.game} has no shader_map.tsv')
        read_first(a.first, a.limit)
    except Bad as e:
        print(f'shader_seed: {e}', file=sys.stderr); return 2
    try: seed(game, a.root, a.first, a.romfs, a.main, a.limit, a.dry_run, a.jobs)
    except KeyboardInterrupt: return 130
    except Bad as e:
        print(f'shader_seed: {e}', file=sys.stderr); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
