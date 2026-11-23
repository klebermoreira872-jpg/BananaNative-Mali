#!/usr/bin/env python3
"""The run-time shader layer of a game: the shaders its play asked for and the prepared library lacks, built into a small library of their own.

    python3 shader_layer.py --game <title ID> --root <layer folder> [--build]

The host (dm/gfx/vk_android/vka_shader.c, DM_VK_LAYER) writes, for a program with a shader the library lacks, the control section and code of each of the program's stages
to <layer folder>/req/<key>.ctl and <key>.code, and the pairs (vertex key, pixel key) of its stages to <layer folder>/req/pairs.tsv. This tool makes a package of those records, a
temporary profile folder that is the game's own with a shader_map.tsv of the requests (and their pairs added to shader_pairs.tsv) and runs vk_android_build.py on them
(DM_GAMES_DIR + DM_GAMES_FIRST: the build tool reads that profile), so every module is the one a full build makes of the same shader. The library is
<layer folder>/lib/v-<DMSH_VK_CHAIN>/dmsh_vk.lib; the prepared library (shaders/v-<V>/) is never touched, and this file is not one of the chain's files, so no library version moves.
The build's results are one file per shader (<layer folder>/lib/v-<V>/results), so a rerun with more requests translates only the new ones. What each version built is its own
lib/v-<V>/built.tsv: two apps of other versions sharing a pack folder do not settle each other's requests.
Without --build it only makes the package and the profile (--work, for tests). Exit code: the build's, 2 on a bad request, 3 when the layer folder is past --max-bytes.

Speed (android/SHADERS.md, "Build order and cost"): a run builds the requests in the order the game asked for them (the .ctl files' times), a program's vertex and pixel shaders
together, at most --batch new ones (default max(64, half of those already built)), so the first library appears after one small batch and later runs grow with the layer. The
layer's profile tables change with every new request, which changes the profile's inputs digest that each result file is stamped with: without care every run would translate
every request again. carry_results moves the results of the last run over to the new digest when nothing a shader's translation reads has changed (the game's own inputs the
same, and for a vertex shader the same pixel shaders paired with it among the layer's keys); the others are translated again. The state it compares with is saved before the
build starts, so the results of a run that was killed (lmkd, a Prepare that stopped it) are carried as well as those of a run that ended."""
import argparse
import json
import os
import re
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'games'))
if '--game' in sys.argv: os.environ.setdefault('DM_GAME', sys.argv[sys.argv.index('--game') + 1])   # (shader_split.py and the build tool read the profile of DM_GAME when imported)
import shader_split as S   # noqa: E402
import game as G           # noqa: E402
import dmsh_chain          # noqa: E402

LONG = {'vs': 'vertex', 'hs': 'hull', 'ds': 'domain', 'gs': 'geometry', 'ps': 'pixel', 'cs': 'compute', 'ts': 'task', 'ms': 'mesh'}
OWN = ('shader_map.tsv', 'shader_pairs.tsv', 'shader_seen.tsv', 'vk_delta.tsv')   # the tables the layer's profile makes itself (the manifest is the game's full build's)
STATE = 'layer_state.json'   # in lib/v-<V>/: the inputs digests and vertex pairs of the last run, saved as it starts (carry_results)
BUILT = 'built.tsv'          # in lib/v-<V>/: what that version built (write_built); <layer folder>/built.tsv is the older place, read for its rows of that version
GRACE_S = 60                 # a request pair younger than this that does not read back may still be being written by the host: left for the next run
VERIFY_BATCH = 32            # new shaders a verify run translates at most (a kept library's played shaders, a few at a time, in the background)
BATCH_MIN = 64               # new shaders a run builds at least (programs stay whole, so a run may take a few more)


def chain_version():
    """DMSH_VK_CHAIN of these tools (dm/gfx/nvn/dmsh_chain_vk.h, which the APK's tools.zip carries): the layer's lib/v-<V>/; None when the header cannot be read"""
    try: m = re.search(r'#define DMSH_VK_CHAIN "([0-9a-f]+)"', (HERE.parent / 'nvn' / 'dmsh_chain_vk.h').read_text())
    except OSError: return None
    return m.group(1) if m else None


def read_requests(req, game, now=None, grace=GRACE_S):
    """({key: (control, code, stage)} in the order the game asked for them (the .ctl file's time, then the key), [problems], [(vertex key, pixel key)]) of a request folder.
    A pair of files whose bytes do not hash to the name (a control file cut short when the game's process was stopped, a code file gone) is a problem; when it is older than
    grace seconds its files are removed, so the host writes the request again when the game next asks for the program (it skips a key whose .ctl exists); a younger one may be
    being written and is left for the next run"""
    S.KEY_SKIP = tuple(int(x, 0) for x in game.get('shader_key_skip', '0+0').split('+'))
    now = time.time() if now is None else now
    found, bad = [], []
    for c in Path(req).glob('*.ctl'):
        try: found.append((c.stat().st_mtime, c.stem, c))
        except OSError: pass
    out = {}
    for mt, key, c in sorted(found):
        code_p = c.with_suffix('.code'); why = None
        try:
            if not code_p.is_file(): why = 'no .code'
            else:
                ctl, code = c.read_bytes(), code_p.read_bytes()
                if S.skey(ctl, code) != key: why = f'its bytes hash to {S.skey(ctl, code)}'
                elif not (st := S.glslc_stage(ctl, code)): why = 'no stage'
                else: out[key] = (ctl, code, st)
        except Exception as e: why = f'{type(e).__name__}: {e}'   # (a file cut short can fail any of the readers: struct.error, IndexError, ...)
        if why is None: continue
        if now - mt >= grace:
            for f in (c, code_p): f.unlink(missing_ok=True)
            why += ': removed, the game asks for it again'
        else: why += ': left for the next run (it may be being written)'
        bad.append(f'{key}: {why}')
    pairs, have = [], set()
    p = Path(req) / 'pairs.tsv'
    if p.is_file():
        for ln in p.read_text(errors='replace').splitlines():   # (the host appends a program's pairs: a last line cut short has no key among the requests)
            c = tuple(ln.split('\t'))
            if len(c) == 2 and c[0] in out and c[1] in out and c not in have: have.add(c); pairs.append(c)
    return out, bad, pairs


def built_path(root, version):
    """lib/v-<version>/built.tsv: the requests that version of the tools settled"""
    return Path(root) / 'lib' / f'v-{version or ""}' / BUILT


def read_built(root, version=None):
    """{key: (status, version)} of the version's lib/v-<version>/built.tsv (rows key, ok | fail, the DMSH_VK_CHAIN that built it). Without that file, the rows of that version in
    <root>/built.tsv, the older place every version shared (a row of another version settles nothing here: its shader is not in this version's library). version None: the
    older file as it is (every row)"""
    out = {}
    own = version is not None and built_path(root, version).is_file()
    try: text = (built_path(root, version) if own else Path(root) / 'built.tsv').read_text()
    except (OSError, UnicodeDecodeError): return out
    for ln in text.splitlines():
        c = ln.split('\t')
        if len(c) >= 2 and len(c[0]) == 16:
            v = c[2] if len(c) > 2 else ''
            if version is None or own or v == version: out[c[0]] = (c[1], v)
    return out


def settled(row, version):
    """Whether a built.tsv row settles its request: built, or failed with this version of the tools (a failure is tried once more by the next DMSH_VK_CHAIN: a translator fix)"""
    return row is not None and (row[0] == 'ok' or row[1] == version)


def pick(reqs, pairs, built, version, batch=None):
    """The keys of this run, in the order asked: every request already built (the library is written from all of them; their result files make that cheap) and, of the
    rest, at most batch new ones in the order the game asked (default max(BATCH_MIN, half the built ones)), each with the shaders paired with it among the requests, so a
    program's stages come in the same run. A failure settled for this version is left out. → [keys]"""
    done = [k for k in reqs if built.get(k, ('',))[0] == 'ok']
    new = [k for k in reqs if not settled(built.get(k), version)]
    batch = max(BATCH_MIN, len(done) // 2) if batch is None else batch
    mate = {}
    for v, p in pairs: mate.setdefault(v, []).append(p); mate.setdefault(p, []).append(v)
    chosen, seen = [], set(done)
    for k in new:
        if len(chosen) >= batch: break
        for x in [k] + mate.get(k, []):
            if x not in seen and not settled(built.get(x), version): seen.add(x); chosen.append(x)
    return done + chosen


def kept_keys(lib):
    """The keys of a kept library (shader_sample.py), the empty set when it cannot be read"""
    try:
        import vk_android_delta as delta
        L = delta.Library(str(lib)); keys = set(L.index); L.close(); return keys
    except (OSError, ValueError, ImportError): return set()


def split_requests(reqs, pairs, kept, built):
    """(the keys of an ordinary run, the keys to verify) when a kept library plays: a request whose key the kept library has is only to verify, unless it is built already (the
    layer's entry wins over the library's in the host, so it stays in the layer) or it is paired with a request the kept library lacks (that program takes its stages from the layer
    as before). Every other request is the ordinary run's"""
    mate = {}
    for v, p in pairs: mate.setdefault(v, []).append(p); mate.setdefault(p, []).append(v)
    missing = {k for k in reqs if k not in kept}
    verify = {k for k in reqs if k in kept and built.get(k, ('',))[0] != 'ok' and not any(m in missing for m in mate.get(k, ()))}
    return set(reqs) - verify, verify


def make_inputs(game, reqs, pairs, work):
    """<work>/pkg (the package: <stage>_req.bin, one record per key) and <work>/profile/<id>/ (the game's profile with the requests' map and pairs) → (pkg, profile root)"""
    work = Path(work)
    if work.exists(): shutil.rmtree(work)
    pkg, prof = work / 'pkg', work / 'profile' / game.id
    pkg.mkdir(parents=True); prof.mkdir(parents=True)
    rows, by = [], {}
    for k, (ctl, code, st) in sorted(reqs.items()): by.setdefault(st, []).append((k, S.package_record(ctl, code)))
    for st, recs in sorted(by.items()):
        name = f'{st}_req.bin'
        (pkg / name).write_bytes(b''.join(bytes(r) for _, r in recs))
        rows += [f'{name}\t{i}\t{LONG[st]}\t{k}\trequested at run time' for i, (k, _) in enumerate(recs)]
    for f in game.dir.iterdir():
        if f.name not in OWN: (prof / f.name).symlink_to(f)
    (prof / 'shader_map.tsv').write_text('package\tindex\tstage\tdm_ctl_sha16\tsource\n' + '\n'.join(rows) + '\n')
    old = game.table('shader_pairs.tsv'); keep = [ln for ln in old.read_text().splitlines() if ln.strip() and not ln.startswith('#')] if old.is_file() else []
    (prof / 'shader_pairs.tsv').write_text('# the game\'s pairs and the requested programs\' (shader_layer.py)\n' + '\n'.join(keep + [f'{v}\t{p}' for v, p in pairs]) + '\n')
    return pkg, prof.parent


def vs_partners(prof, keys):
    """{vertex key: sorted pixel keys paired with it among keys} as the build reads the layer's profile (its shader_pairs.tsv and pso_pairs.tsv): what a vertex shader's padding
    depends on"""
    keys = set(keys); out = {}
    for t in ('shader_pairs.tsv', 'pso_pairs.tsv'):
        f = Path(prof) / t
        if not f.is_file(): continue
        for ln in f.read_text().splitlines():
            c = ln.split()
            if len(c) >= 2 and not ln.startswith('#') and c[0] in keys and c[1] in keys: out.setdefault(c[0], set()).add(c[1])
    return {v: sorted(p) for v, p in out.items()}


def carry_results(res, state, game_in, layer_in, partners):
    """The result files of the last run moved over to this run's profile inputs digest (layer_in), when only the layer's own request tables changed: the game's inputs are the
    state's (game_in), and the head's digest is the state's layer digest. A vertex shader whose paired pixel shaders among the layer's keys changed is removed (its padding
    changes: it is translated again). The digest is 12 hex digits in the JSON head, rewritten in place at the same length, so a stop in the middle leaves a result the build
    finds stale and translates again, never a wrong one. The state is the one main() saved as the last run
    started (its digests and its vertex shaders' pairs), so every result that run wrote, whether it ended or was killed, has the state's digest; a result of any other digest is
    never moved. → (carried, removed)"""
    old = (state or {}).get('layer')
    if not old or (state or {}).get('game') != game_in or old == layer_in or not Path(res).is_dir(): return 0, 0
    was = state.get('vs', {}); carried = removed = 0
    pat_old, pat_new = f'"inputs":"{old}"'.encode(), f'"inputs":"{layer_in}"'.encode()
    for f in Path(res).glob('*.r'):
        k = f.name[:-2]
        if k in partners or k in was:
            if partners.get(k) != was.get(k): f.unlink(missing_ok=True); removed += 1; continue
        try:
            with open(f, 'r+b') as h:
                d = h.read(12)
                if len(d) != 12 or d[:8] != b'DMVKRES1': continue
                head = h.read(int.from_bytes(d[8:], 'little')); i = head.find(pat_old)
                if i < 0: continue
                h.seek(12 + i); h.write(pat_new); carried += 1
        except OSError: pass
    return carried, removed


def layer_bytes(root, version=None):
    """Bytes under the layer folder that this version's build answers for (requests, this version's results and library, the folder's own files): what --max-bytes limits. The
    folders of other versions (lib/v-<other>, another app's or an older one's, which the host of this version never maps) are not counted, as LayerGuard.usage does not count
    them: they are the launcher's to remove (LayerDir.tidy), never a reason to stop this game's build. version None: everything"""
    n, other = 0, set() if version is None else {p for p in (Path(root) / 'lib').glob('v-*') if p.name != f'v-{version}'}
    for d, ds, fs in os.walk(root):
        if other: ds[:] = [x for x in ds if Path(d) / x not in other]
        for f in fs:
            try: n += os.lstat(os.path.join(d, f)).st_size
            except OSError: pass
    return n


class PhaseClock:
    """Where a run's time goes, cheaply and without touching the chain's tools: stdout is passed through as it is and the lines the build prints (`progress <done> <total> <phase>`:
    translate, library, check, done) are timestamped, with the process's CPU times (os.times: the translator runs in this process, so a CPU time far under the wall time means
    the run waits for memory or storage). `line()` is the one summary the app puts in logcat (tag nxlayer) after each run: the per-phase split, the shaders it built, the
    process's peak memory and what the phone had free. Not one of the chain's files: no library version moves."""
    PHASES = ('translate', 'library', 'check', 'done')

    def __init__(self, clock=time.time, cpu=lambda: (os.times().user + os.times().children_user, os.times().system + os.times().children_system)):
        self.clock, self.cpu = clock, cpu
        self.t0, self.c0 = clock(), cpu()
        self.at = {}          # phase -> (wall, user, system) at its first progress line
        self.marks = []       # (name, wall, user, system) the tool sets itself (mark)
        self._buf = ''

    def mark(self, name):
        u, sy = self.cpu(); self.marks.append((name, self.clock(), u, sy))

    def feed(self, text):
        """The stdout text as written: complete lines are looked at"""
        self._buf += text
        *lines, self._buf = self._buf.split('\n')
        for l in lines:
            m = re.match(r'progress \d+ \d+ (\w+)', l)
            if m and m.group(1) in self.PHASES and m.group(1) not in self.at:
                u, sy = self.cpu(); self.at[m.group(1)] = (self.clock(), u, sy)

    @staticmethod
    def meminfo():
        """MemAvailable and swap used in MB from /proc/meminfo, None when unreadable"""
        try:
            kv = {l.split(':')[0]: int(l.split()[1]) for l in open('/proc/meminfo') if ':' in l}
            return kv['MemAvailable'] >> 10, (kv.get('SwapTotal', 0) - kv.get('SwapFree', 0)) >> 10
        except (OSError, KeyError, ValueError, IndexError): return None

    def line(self, shaders, mem0=None, mem1=None, peak_mb=None):
        """shader_layer timing: <n> shaders in <wall> s (cpu <user>+<sys> s): setup .. s, translate .. s (cpu ..), library .. s, check .. s, finish .. s; peak .. MB; free A to B MB, swap C to D MB"""
        t1 = self.clock(); u1, s1 = self.cpu()
        order = [('translate', self.at.get('translate'))] + [(p, self.at.get(p)) for p in self.PHASES[1:]]
        pts = [(n, v) for n, v in order if v]
        parts = []
        first = pts[0][1][0] if pts else t1
        parts.append(f'setup {first - self.t0:.1f} s')
        for i, (n, v) in enumerate(pts):
            if n == 'done': break
            end = pts[i + 1][1] if i + 1 < len(pts) else (t1, u1, s1)
            w = end[0] - v[0]; c = (end[1] - v[1]) + (end[2] - v[2])
            parts.append(f'{n} {w:.1f} s' + (f' (cpu {c:.1f})' if n == 'translate' else ''))
        done = self.at.get('done')
        parts.append(f'after {t1 - done[0]:.1f} s' if done else f'tail {t1 - (pts[-1][1][0] if pts else self.t0):.1f} s')
        for n, w, u, sy in self.marks: parts.append(f'{n} at {w - self.t0:.1f} s')
        n = f'{shaders} shader{"" if shaders == 1 else "s"}'
        rate = f', {shaders / (t1 - self.t0):.2f}/s' if shaders and t1 > self.t0 else ''
        out = f'shader_layer timing: {n} in {t1 - self.t0:.1f} s{rate} (cpu {u1 - self.c0[0]:.1f}+{s1 - self.c0[1]:.1f} s): ' + ', '.join(parts)
        if peak_mb is not None: out += f'; peak {peak_mb} MB'
        if mem0 and mem1: out += f'; free {mem0[0]} to {mem1[0]} MB, swap {mem0[1]} to {mem1[1]} MB'
        return out


class _Tee:
    def __init__(self, inner, clock): self.inner, self.clock = inner, clock
    def write(self, t): self.clock.feed(t); return self.inner.write(t)
    def flush(self): return self.inner.flush()
    def __getattr__(self, n): return getattr(self.inner, n)


def peak_mb():
    """This process's peak resident memory in MB (resource.getrusage; Linux reports kB), None when not known"""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >> 10
    except (ImportError, OSError, ValueError): return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', required=True); ap.add_argument('--root', required=True); ap.add_argument('--work')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--batch', type=int, help='new shaders this run builds at most (default max(64, half of those already built))')
    ap.add_argument('--kept', help='the folder of a library kept by a sample (shader_sample.py: v-<V> with sampled-keep.json): the requests of shaders it has are not built by an ordinary run; with --verify they are, and compared with it')
    ap.add_argument('--verify', action='store_true', help='with --kept: build the requests the kept library covers (at most --verify-batch new ones) and compare them with its entries')
    ap.add_argument('--verify-batch', type=int, default=VERIFY_BATCH)
    ap.add_argument('--max-bytes', type=int, default=0, help='no build when the layer folder holds more than this (the app\'s quota, LayerGuard); 0: no limit')
    a = ap.parse_args(argv)
    game = G.load(a.game)
    root = Path(a.root)
    version = chain_version() or ''
    if a.max_bytes and (used := layer_bytes(root, version)) > a.max_bytes:
        print(f'[RED] shader_layer: the layer folder holds {used >> 20} MB, past its quota of {a.max_bytes >> 20} MB: nothing is built'); return 3
    reqs, bad, pairs = read_requests(root / 'req', game)
    for b in bad: print(f'[RED] shader_layer: {b}', file=sys.stderr)
    if not reqs: print('shader_layer: no requests'); return 2 if bad else 0
    built = read_built(root, version)
    kept_lib = None
    if a.kept:   # a kept library plays: what it covers is verified in runs of their own, never in the ordinary ones (the missing shaders come first)
        kept_lib = Path(a.kept) / 'dmsh_vk.lib'
        covered = kept_keys(kept_lib)
        misses, verify = split_requests(reqs, pairs, covered, built)
        if a.verify:
            reqs = {k: v for k, v in reqs.items() if k in verify or built.get(k, ('',))[0] == 'ok'}
            a.batch = a.verify_batch
            if not verify: print('shader_layer: nothing to verify'); return 0
        else: reqs = {k: v for k, v in reqs.items() if k in misses}
        pairs = [(v, p) for v, p in pairs if v in reqs and p in reqs]
        if not reqs: print('shader_layer: no requests'); return 0
    keys = pick(reqs, pairs, built, version, a.batch)
    todo = [k for k in keys if built.get(k, ('',))[0] != 'ok']
    if not todo: print(f'shader_layer: {len(reqs)} requests, every one settled'); return 0
    run = {k: reqs[k] for k in keys}; run_pairs = [(v, p) for v, p in pairs if v in run and p in run]
    work = Path(a.work) if a.work else Path(tempfile.gettempdir()) / f'shader_layer_{game.id}'   # (not under root: the phone's shared storage takes no symlinks; TMPDIR is the app's cache)
    pkg, profs = make_inputs(game, run, run_pairs, work)
    print(f'shader_layer: {len(run)} shaders ({len(todo)} new of the {len(reqs) - (len(run) - len(todo))} not built yet, in the order asked), {len(run_pairs)} pairs, package {pkg}')
    if not a.build: return 0
    game_in, layer_in = dmsh_chain.inputs(game), dmsh_chain.inputs(G.Game(profs / game.id))
    partners = vs_partners(profs / game.id, run)
    lib = root / 'lib'; lib.mkdir(exist_ok=True)
    vdir = lib / f'v-{version}'
    try: state = json.loads((vdir / STATE).read_text())
    except (OSError, ValueError): state = None
    c, r = carry_results(vdir / 'results', state, game_in, layer_in, partners)
    if c or r: print(f'shader_layer: {c} results of the last run kept for the new request tables, {r} vertex shaders with new pairs translated again')
    # The state of this run, before it starts: every result it writes has this digest and, for a vertex shader, these pairs, so a run killed half way (lmkd, a Prepare that
    # stopped it) leaves results the next run carries over; saved after the carry, which made the results of the last state this one's
    save_state(vdir, game_in, layer_in, partners)
    env = {'DM_GAME': game.id, 'DM_GAMES_DIR': str(profs), 'DM_GAMES_FIRST': '1', 'DMSH_VK_KEEP': '1', 'DMSH_VK_DELTA_FROM': '', 'DMSH_VK_REQUIRE_ALL': '', 'DMSH_VK_RESULTS': ''}   # (a failed shader is left out of the layer, not a stop for the others)
    clock = PhaseClock(clock=time.time); clock.t0 = T0   # (the run's start: argument parsing, the request list and the package are "setup")
    mem0 = clock.meminfo(); out0 = sys.stdout; sys.stdout = _Tee(out0, clock)
    try: rc = run_build(str(pkg), str(lib), env)
    finally: sys.stdout = out0
    shutil.rmtree(work, ignore_errors=True)
    if rc == 0: write_built(root, keys, version)
    if rc == 0 and kept_lib is not None:
        try:
            import shader_sample
            print(shader_sample.record_verify(root, version, kept_lib, vdir / 'dmsh_vk.lib'), flush=True)
        except Exception as e: print(f'shader_layer: verify not recorded: {type(e).__name__}: {e}', file=sys.stderr)   # (the layer itself is built: a count is lost, not a shader)
    clock.mark('built.tsv')
    print(clock.line(len(todo), mem0, clock.meminfo(), peak_mb()), flush=True)
    return rc


def save_state(vdir, game_in, layer_in, partners):
    """lib/v-<V>/layer_state.json, written by rename: the digests and the vertex shaders' pairs of the run that starts (carry_results)"""
    vdir = Path(vdir); vdir.mkdir(parents=True, exist_ok=True)
    tmp = vdir / (STATE + '.tmp'); tmp.write_text(json.dumps({'game': game_in, 'layer': layer_in, 'vs': partners})); os.replace(tmp, vdir / STATE)


def run_build(pkg, lib, env):
    """vk_android_build.py in this process (the phone's app may not start programs: android/ONDEVICE.md, No subprocesses), as `python3 vk_android_build.py --target vulkan pkg lib` with env
    added to the environment; the environment and sys.argv are put back"""
    tool = str(HERE / 'vk_android_build.py')
    saved = {k: os.environ.get(k) for k in env}; argv0 = sys.argv
    os.environ.update(env); sys.argv = [tool, '--target', 'vulkan', pkg, lib]
    try:
        runpy.run_path(tool, run_name='__main__'); return 0
    except SystemExit as e:
        if e.code is None or e.code == 0: return 0
        if isinstance(e.code, int): return e.code
        print(e.code, file=sys.stderr); return 1
    finally:
        sys.argv = argv0
        for k, v in saved.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v


def write_built(root, keys, version=''):
    """lib/v-<version>/built.tsv: each key of this run with what the build did (ok, or fail) and the tools' version (DMSH_VK_CHAIN), so the app knows which requests are
    settled (LayerPending: the pending ones are the requests it does not settle; a failure settles only for its own version, and each version has its own file). The rows of
    requests this run left out are kept; rows of keys no longer requested go. The status is this version's (lib/v-<version>/_vk_build.json). Written by rename"""
    root = Path(root); keys = list(keys); version = version or ''
    status = {}
    try: status.update({r['key']: r['st'] for r in json.loads((root / 'lib' / f'v-{version}' / '_vk_build.json').read_text())})
    except (OSError, ValueError, KeyError, TypeError): pass
    rows = {k: v for k, v in read_built(root, version).items() if (root / 'req' / f'{k}.ctl').is_file()}
    for k in keys: rows[k] = ('ok' if status.get(k) == 'ok' else 'fail', version)
    out = built_path(root, version); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(BUILT + '.tmp')
    tmp.write_text(''.join(f'{k}\t{st}\t{v}\n' for k, (st, v) in sorted(rows.items())))
    os.replace(tmp, out)


if __name__ == '__main__':
    sys.exit(main())
