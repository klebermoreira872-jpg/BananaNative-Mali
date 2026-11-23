#!/usr/bin/env python3
"""Sampled keep: a quick check that lets a pack's older Android shader library stand as this version's (android/SHADERS.md, "Sampled keep").

    python3 shader_sample.py --game <title ID> --pack <pack folder> --old <older version> --abi <12 hex> --inputs <12 hex> --work <folder>
                             --romfs <spec> [--main <spec>] [--n 300] [--first 200] [--seed S] [--jobs J]

An APK update that moves DMSH_VK_CHAIN leaves a pack with the older library (it plays meanwhile). When a full build, a delta manifest or a stamp row is not at hand, this tool
asks whether the new tools would have made the same library: it translates at most N shaders IN ALL (default 300, DM_SHADER_SAMPLE), a vertex shader counted with the
pixel shaders paired with it. It draws the first F of the game's starter set (default 200, DM_SHADER_SAMPLE_FIRST; dm/games/<id>/shader_first.tsv in its order, the ones
the older library has and the game's RomFS holds: what a start draws first), the rest a stratified random sample of the others (by stage and by size, the large and the rare
ones included; a recorded seed, so a run can be repeated; all random for a game with no starter set), and takes them with their mates while the total stays within N: the
random part is cut first, then the starter set's tail (draw_capped). It has the CURRENT tools translate just those from the game's own files (the requests shader_seed.py writes,
translated by shader_layer.py, so every entry is the one a full build makes), and compares each entry's hash (vk_android_delta.entry_hash) with the older library's entry for the key.
All the same: the older library is taken over as this version's (header version, abi and chain rewritten, as ShaderLibs.restamp does; the older one stays) with a marker,
<library folder>/sampled-keep.json, that says what was proved. Any difference: nothing is taken over and the pack updates as before (delta, layer, full build).

What it proves and does not: the starter set's entries are the ones a start uses first; the random part's identical entries show, at the usual confidence, that fewer than about 1 in N of the library's entries changed; a rare change below
that can pass. The verify step covers it for what is played (shader_layer.py --verify: the shaders the game draws are translated again in the background and compared).
Not one of the chain's files (android/SHADERS.md, Versions): no library version moves. Exit code: 0 accepted, 10 differences (not accepted), 11 not eligible or too few shaders
could be checked, 2 a bad argument, other: a failure of the translation. The result is also written to <pack>/shaders/.sample-<V>.json, accepted or not, so it is not asked again.

Resume: a check that is stopped (exit 12: the player started a game or skipped it) or killed keeps what it translated in <work>/layer (the requests and the layer's one result file
a shader), with <work>/resume.json, the key of that run (the older version, this version, the chain, the profile's inputs, the ABI, the game file, the sample size, the seed and
the drawn keys' digest). A later run with the same key translates only the shaders that have no result yet; any other key starts afresh. The seed is stable for an older
library and these tools (stable_seed; DM_SHADER_SAMPLE_SEED or --seed wins), so a rerun draws the same sample. A stop writes <work>/stopped.json (the time, counts only),
which the launcher reads to hold the next start back (SampleQueue.BACKOFF_MS). A verdict removes all of it."""
import argparse
import hashlib
import json
import math
import os
import random
import re
import shutil
import struct
import threading
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def TMPWORK(game_id):
    """The translation's temporary profile folder: in the temp folder, never in the work folder (the phone's shared storage takes no symlinks, which the layer's profile uses)"""
    import tempfile
    return Path(tempfile.gettempdir()) / ('shader_sample_' + game_id)
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'games'))
import vk_android_delta as delta   # noqa: E402  (read only: the entry hash and the library reader are the delta update's own)

try: from compression import zstd   # Python 3.14; before it, backports.zstd (as vk_android_build.py)
except ImportError:
    try: from backports import zstd   # pyright: ignore[reportMissingImports]
    except ImportError: zstd = None

DEFAULT_N = 300
DEFAULT_FIRST = 200                 # of the sample, taken from the game's starter set (shader_first.tsv) in its order
SEED_ENV, N_ENV, FIRST_ENV = 'DM_SHADER_SAMPLE_SEED', 'DM_SHADER_SAMPLE', 'DM_SHADER_SAMPLE_FIRST'
FIRST_LIST = 'shader_first.tsv'     # the profile's starter set (shader_seed.py read_first)
KEEP_FILE = 'sampled-keep.json'     # in the kept library's folder
BATCH = 16                          # shaders a translator call in the check (DMSH_VK_BATCH; a build's default is 64): the launcher's stop (Play) lands between calls, and on a warm
                                    # phone a call of 64 took some 50 s, all of which the game's own layer build waited behind the check (2026-11-16 phone test)
MAX_MATES = 200                     # a vertex shader paired with more pixel shaders than this is not sampled (its padding needs them all in the translation)
MIN_SHARE = 0.5                     # at least this share of the sample must be found in the game's files and translated, or the check proves too little
EXIT_ACCEPTED, EXIT_DIFFERENT, EXIT_INELIGIBLE = 0, 10, 11
EXIT_STOPPED = 12                   # asked to stop (the launcher: the player started a game, or skipped the check): no verdict is written, the check can be asked again
INTERRUPTED = 130                   # a tool stopped by the packer's interrupt (128 + SIGINT)
PROGRESS_FILE = 'progress.json'     # in the work folder, for the launcher's card: {"phase": "seed" | "translate", "done": n, "total": m, "reused": r}, written every few seconds
RESUME_FILE = 'resume.json'         # in the work folder: the key of the run whose translations <work>/layer holds (resume_key); a rerun with the same key reuses them
STOPPED_FILE = 'stopped.json'       # in the work folder: {"at_ms": time of the stop, "done": n, "total": m} (counts only), written when the check is stopped (SampleQueue's backoff)
RESUME_FORMAT = 1                   # what resume.json and the layer folder hold; another format starts afresh
VERTEX = 0                          # the entry's stage byte of a vertex shader (dmsh_abi.h)
CHAIN_AT, CHAIN_LEN = 8, 16         # the header's DMSH_CHAIN field (the STAMP_FIELDS are the version at 24 and the abi at 116)


def sample_size(environ=None):
    """The sample size: DM_SHADER_SAMPLE (0 = no sampled keep), default 300"""
    v = (os.environ if environ is None else environ).get(N_ENV, '').strip()
    try: return max(0, int(v)) if v else DEFAULT_N
    except ValueError: return DEFAULT_N


def first_size(environ=None):
    """How many of the sample come from the starter set: DM_SHADER_SAMPLE_FIRST, default 200"""
    v = (os.environ if environ is None else environ).get(FIRST_ENV, '').strip()
    try: return max(0, int(v)) if v else DEFAULT_FIRST
    except ValueError: return DEFAULT_FIRST


def read_first_keys(path):
    """The starter set's keys in its order, each once ([] when the profile has none or it cannot be read): rows key<TAB>stage, '#' comments (shader_seed.py read_first)"""
    out, seen = [], set()
    try: lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError: return []
    for ln in lines:
        k = ln.split('\t')[0].strip()
        if ln.startswith('#') or len(k) != 16 or any(ch not in '0123456789abcdef' for ch in k) or k in seen: continue
        seen.add(k); out.append(k)
    return out


def draw_parts(infos, n, n_first, first_keys, seed):
    """(the starter part in first_keys' order, the random part sorted): the first min(n_first, n) keys of first_keys that infos has, then n minus those drawn at random
    (pick_sample) from the other infos; all n random when first_keys is empty. The same for the same arguments"""
    have = {k for k, _, _ in infos}
    taken, t = [], set()
    for k in first_keys:
        if len(taken) >= min(n_first, n): break
        if k in have and k not in t: taken.append(k); t.add(k)
    return taken, pick_sample([i for i in infos if i[0] not in t], n - len(taken), seed)


def draw(infos, n, n_first, first_keys, seed):
    """(the sample, how many of it are from the starter set): draw_parts as one sorted list"""
    taken, rest = draw_parts(infos, n, n_first, first_keys, seed)
    return sorted(taken + rest), len(taken)


def draw_capped(infos, pairs, n, n_first, first_keys, seed, limit=MAX_MATES):
    """The sample with its mates held to n shaders IN ALL (DM_SHADER_SAMPLE counts the translated shaders, not the drawn keys: OoT's 300 keys came to about 1,000 with
    the pixel shaders paired with its vertex ones, 2026-11-16). draw_parts' keys are taken in order, each with its mates (with_mates), while the total stays within n:
    the starter part first, in its order (its tail is what is cut), then the random part in an order shuffled by the seed (cut first: nothing of it is taken once the starter
    part has filled n). A vertex shader with more than limit mates is left out (with_mates). → (the drawn keys sorted, how many from the starter set, how many random,
    every key to translate sorted, the vertex shaders left out)"""
    taken, rest = draw_parts(infos, n, n_first, first_keys, seed)
    chosen, dropped = set(), []
    def take(order):
        got = []
        for k in order:
            u, d = with_mates([k], infos, pairs, limit)
            if d: dropped.extend(d); continue
            if len(chosen | set(u)) > n: return got, False
            chosen.update(u); got.append(k)
        return got, True
    first, whole = take(taken)
    rnd = []
    if whole:
        order = sorted(rest); random.Random(seed).shuffle(order)
        rnd, _ = take(order)
    return sorted(first + rnd), len(first), len(rnd), sorted(chosen), sorted(dropped)


def library_infos(L):
    """[(key, stage, size)] of every entry of a delta.Library: the stage byte and the sum of its modules' SPIR-V sizes (no module is decoded)"""
    out = []
    for i in range(L.ne):
        key, _, stage, mc, _, m0, _, _ = struct.unpack_from('<QQBBHIIH', L.m, L.eo + delta.ENTRY.size * i)
        size = sum(delta.MOD.unpack_from(L.m, L.mo + delta.MOD.size * j)[1] for j in range(m0, min(m0 + mc, L.nm)))
        out.append((f'{key:016x}', stage, size))
    return out


def strata(infos):
    """{(stage, size class): [keys]}: the size classes are the library's own quantiles (under the median, the median to the 90th percentile, the top tenth), so the large shaders,
    which cost most to get wrong, are a class of their own whatever the game's sizes are"""
    sizes = sorted(s for _, _, s in infos)
    lo = sizes[len(sizes) // 2] if sizes else 0
    hi = sizes[min(len(sizes) - 1, len(sizes) * 9 // 10)] if sizes else 0
    out = {}
    for k, st, s in infos: out.setdefault((st, 0 if s < lo else 1 if s < hi else 2), []).append(k)
    return out


def pick_sample(infos, n, seed):
    """n keys drawn from the infos [(key, stage, size)], sorted, the same for the same (infos, n, seed): every stratum gets a share of the square root of its size (a rare
    stage or the large class is not drowned by the many small pixel shaders) and at least one when n allows, the rounding of the shares by the largest remainders, a stratum
    never more than it has; the keys of a stratum are drawn by random.Random(seed) from the sorted keys"""
    st = strata(infos); names = sorted(st)
    n = min(n, sum(len(v) for v in st.values()))
    if n <= 0: return []
    rng = random.Random(seed)
    want = {s: min(len(st[s]), 1 if n >= len(names) else 0) for s in names}
    left = n - sum(want.values())
    w = {s: math.sqrt(len(st[s])) for s in names}
    while left > 0:
        room = [s for s in names if want[s] < len(st[s])]
        if not room: break
        tot = sum(w[s] for s in room)
        quota = {s: left * w[s] / tot for s in room}
        add = {s: min(int(quota[s]), len(st[s]) - want[s]) for s in room}
        rest = left - sum(add.values())
        for s in sorted(room, key=lambda s: (-(quota[s] - int(quota[s])), s)):
            if rest <= 0: break
            if want[s] + add[s] < len(st[s]): add[s] += 1; rest -= 1
        for s in room: want[s] += add[s]
        left = n - sum(want.values())
    out = []
    for s in names: out += rng.sample(sorted(st[s]), want[s])
    return sorted(out)


def read_pairs(prof, keys):
    """{key: sorted partner keys}: the profile's (vertex, pixel) pairs (shader_pairs.tsv, pso_pairs.tsv: what a vertex shader's padding reads) of the keys given, both ways"""
    keys = set(keys); out = {}
    for t in ('shader_pairs.tsv', 'pso_pairs.tsv'):
        f = Path(prof) / t
        if not f.is_file(): continue
        for ln in f.read_text(errors='replace').splitlines():
            c = ln.split()
            if len(c) < 2 or ln.startswith('#'): continue
            if c[0] in keys: out.setdefault(c[0], set()).add(c[1])
            if c[1] in keys: out.setdefault(c[1], set()).add(c[0])
    return {k: sorted(v) for k, v in out.items()}


def with_mates(sample, infos, pairs, limit=MAX_MATES):
    """(the sample and the pixel shaders paired with its vertex shaders, the vertex shaders dropped for having more than limit partners): a vertex shader's library entry is padded
    for every pixel shader paired with it, so its check needs them all in the translation (they are compared too when the older library has them)"""
    stage = {k: s for k, s, _ in infos}; have = set(stage); out = set(sample); dropped = []
    for k in sample:
        p = [x for x in pairs.get(k, []) if x in have and stage.get(x) != stage.get(k)]
        if len(p) > limit: out.discard(k); dropped.append(k)
        elif stage[k] == VERTEX: out.update(p)
    return sorted(out), dropped


def compare(old, new_path, keys):
    """(the keys compared, [keys whose entry differs or is missing in the new library]) of an older delta.Library and the new library file: entry hashes (vk_android_delta.entry_hash)"""
    N = delta.Library(new_path)
    try:
        same, diff = [], []
        for k in keys:
            io, i = old.index.get(k), N.index.get(k)
            if io is None: continue   # (not in the older library: nothing to compare)
            try: ho = old.hash_of(io, zstd)[1]
            except Exception: diff.append(k); continue
            try: hn = N.hash_of(i, zstd)[1] if i is not None else None
            except Exception: hn = None
            (same if hn == ho else diff).append(k)
        return sorted(same + diff), sorted(diff), (N.sg, N.sa)
    finally: N.close()


def header_problem(old, game, inputs, abi, same_abis=()):
    """Why an older library cannot be kept by a sample, None when it can: it is the game's, of this ABI (a library of another ABI is read by the host another way) and of the profile's inputs"""
    if old.game != game: return f'the library is of {old.game}, not {game}'
    if old.abi != abi and old.abi not in same_abis: return f'its ABI {old.abi or "(none)"} is not this APK\'s {abi}'
    if old.inputs != inputs: return f'its inputs {old.inputs} are not the profile\'s {inputs}'
    return None


KNOWN_FILE = HERE.parent / 'vk_android' / 'vka_known_transitions.tsv'   # rows <old VK chain> <new VK chain> <note> (android/SHADERS.md, Known transitions)


def known_transitions(path=KNOWN_FILE):
    """{(old VK chain, new VK chain)} of the table (its '#' lines are comments); the empty set when it cannot be read"""
    out = set()
    try: lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError: return out
    for ln in lines:
        c = ln.split('\t')
        if ln.startswith('#') or len(c) < 2 or not re.fullmatch(r'[0-9a-f]{12}', c[0]) or not re.fullmatch(r'[0-9a-f]{12}', c[1]): continue
        out.add((c[0], c[1]))
    return out


def known_record(old_version, from_chain, version, when=None):
    """The marker of a library kept by a known transition (no sample: the table's row is what was proved; ShaderLibs.knownRecord)"""
    return {'kind': 'known-transition', 'old': old_version, 'from_chain': from_chain, 'version': version, 'sample': 0, 'mismatches': 0,
            'date': time.strftime('%Y-%m-%d', time.gmtime(when if when is not None else time.time()))}


def keep_record(old_version, version, n, requested, seed, diff, when=None):
    return {'kind': 'sampled-keep', 'old': old_version, 'version': version, 'sample': n, 'requested': requested, 'seed': seed, 'mismatches': diff,
            'date': time.strftime('%Y-%m-%d', time.gmtime(when if when is not None else time.time()))}


def restamp_copy(src, dst, version, abi, chain, chunk=1 << 22):
    """src copied to dst with the header's version, abi and chain fields set (delta.restamped_header, and the chain field)"""
    with open(src, 'rb') as a, open(dst, 'wb') as b:
        h = bytearray(delta.restamped_header(a.read(128), version, abi))
        h[CHAIN_AT:CHAIN_AT + CHAIN_LEN] = chain.encode('ascii').ljust(CHAIN_LEN, b'\0')
        b.write(h)
        while True:
            x = a.read(chunk)
            if not x: break
            b.write(x)
        b.flush(); os.fsync(b.fileno())


def accept(shaders, old_version, version, abi, chain, record):
    """Takes the older library over as this version's: shaders/v-<old>/dmsh_vk.lib copied with its header's fields set, with its inputs.tsv and the marker KEEP_FILE, into
    shaders/.restamp-<version>/, then moved to shaders/v-<version>/ by rename (a pack that has one meanwhile keeps its own). The older library stays. → whether it was moved"""
    shaders = Path(shaders); src, want, tmp = shaders / f'v-{old_version}', shaders / f'v-{version}', shaders / f'.restamp-{version}'
    if (want / 'dmsh_vk.lib').is_file(): return False
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    try:
        restamp_copy(src / 'dmsh_vk.lib', tmp / 'dmsh_vk.lib', version, abi, chain)
        if (src / 'inputs.tsv').is_file(): shutil.copy2(src / 'inputs.tsv', tmp / 'inputs.tsv')
        (tmp / KEEP_FILE).write_text(json.dumps(record, sort_keys=True) + '\n')
        if want.is_dir() and not any(want.iterdir()): want.rmdir()
        os.rename(tmp, want)
        return True
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True); raise


def write_fields(lib, version, abi, chain):
    """The header's version, abi and chain fields rewritten in place (zero-padded ASCII, as restamp_copy), synced"""
    with open(lib, 'r+b') as f:
        for at, ln, v in ((CHAIN_AT, CHAIN_LEN, chain), (24, 16, version), (116, 12, abi)):
            f.seek(at); f.write((v or '').encode('ascii')[:ln].ljust(ln, b'\0'))
        f.flush(); os.fsync(f.fileno())


KNOWN_DIR, KNOWN_JOURNAL = '.known-', 'known-move.txt'   # as ShaderLibs.knownKeep


def known_move(shaders, old_version, version, abi, chain, record):
    """A known transition MOVES the older library in (ShaderLibs.knownKeep, the same steps): a journal in v-<old>, v-<old> renamed to .known-<version>, the header's fields
    rewritten in place, the marker last, renamed to v-<version>. A first rename that fails leaves the older library where it was; a later failure puts it back. → whether it moved"""
    shaders = Path(shaders); src, want, mid = shaders / f'v-{old_version}', shaders / f'v-{version}', shaders / f'{KNOWN_DIR}{version}'
    if (want / 'dmsh_vk.lib').is_file() or mid.exists(): return False
    if want.is_dir():
        try: want.rmdir()
        except OSError: return False
    old = delta.Library(str(src / 'dmsh_vk.lib')); fields = (old.version, old.abi, old.chain); old.close()
    (src / KNOWN_JOURNAL).write_text('\t'.join([old_version, record.get('from_chain', ''), fields[1] or '-', fields[2] or '-', version, abi, chain]) + '\n')
    try: os.rename(src, mid)
    except OSError: (src / KNOWN_JOURNAL).unlink(missing_ok=True); return False
    try:
        write_fields(mid / 'dmsh_vk.lib', version, abi, chain)
        (mid / KEEP_FILE).write_text(json.dumps(record, sort_keys=True) + '\n')   # the marker last
        (mid / KNOWN_JOURNAL).unlink(missing_ok=True)
        os.rename(mid, want)
        return True
    except OSError:
        write_fields(mid / 'dmsh_vk.lib', *fields)
        (mid / KEEP_FILE).unlink(missing_ok=True); (mid / KNOWN_JOURNAL).unlink(missing_ok=True)
        os.rename(mid, src)
        return False


def result_path(shaders, version): return Path(shaders) / f'.sample-{version}.json'


def write_result(shaders, version, rec):
    p = result_path(shaders, version); tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(rec, sort_keys=True) + '\n'); os.replace(tmp, p)


def decide(checked, diff, requested):
    """('accept' | 'different' | 'few', why): no difference among enough checked shaders (MIN_SHARE of the sample) accepts"""
    if diff: return 'different', f'{len(diff)} of {len(checked)} shaders differ'
    if not checked or len(checked) < max(1, math.ceil(requested * MIN_SHARE)): return 'few', f'only {len(checked)} of {requested} shaders could be checked'
    return 'accept', ''


class Progress:
    """Writes work/progress.json every few seconds for the launcher's card: the requests written (seed phase) or the results made (translate phase) of the keys. Counts only; a failure to write is ignored"""
    EVERY_S = 3.0

    def __init__(self, work, root, total, reused=0):
        self.work, self.root, self.total, self.phase, self.reused = Path(work), Path(root), total, 'seed', reused
        self._stop = threading.Event(); self._t = threading.Thread(target=self._run, daemon=True)

    def count(self):
        if self.phase == 'seed': return sum(1 for _ in (self.root / 'req').glob('*.ctl'))
        return sum(1 for _ in (self.root / 'lib').glob('v-*/results/*.r'))

    def write(self):
        try:
            p = self.work / PROGRESS_FILE; tmp = p.with_name(p.name + '.tmp')
            rec = {'phase': self.phase, 'done': min(self.count(), self.total), 'total': self.total}
            if self.reused: rec['reused'] = self.reused   # (translated by an earlier run that was stopped: the card says "Resuming")
            tmp.write_text(json.dumps(rec) + '\n'); os.replace(tmp, p)
        except OSError: pass

    def _run(self):
        while not self._stop.is_set():
            self.write(); self._stop.wait(self.EVERY_S)

    def start(self): self._t.start()

    def stop(self): self._stop.set(); self._t.join(2)


def translate(game, work, keys, infos, rom, main_spec, jobs):
    """The requests of keys written from the game's files (shader_seed.py) in work/layer, translated by shader_layer.py as a layer is → the new library's path or None. What a
    stopped run of the same key left there (run: prepare_resume) is kept: the requests written are not read again from the game's files, and shaders with a result are not
    translated again (shader_layer.py's results, one file a shader)"""
    import shader_seed as SEED, shader_layer as LAYER   # noqa: E402  (they read the profile of DM_GAME when imported)
    root = Path(work) / 'layer'
    root.mkdir(parents=True, exist_ok=True)
    stage = {k: s for k, s, _ in infos}
    first = Path(work) / 'first.tsv'
    first.write_text(''.join(f'{k}\t{stage[k]}\n' for k in keys))
    ticker = Progress(work, root, len(keys), reused_results(work, keys)); ticker.start()
    try:
        ticker.phase = 'seed'
        SEED.seed(game, root, first, rom, main_spec, None, False, jobs)
        ticker.phase = 'translate'
        saved = os.environ.get('DMSH_VK_BATCH'); os.environ['DMSH_VK_BATCH'] = saved or str(BATCH)
        try: rc = LAYER.main(['--game', game.id, '--root', str(root), '--work', str(TMPWORK(game.id)), '--build', '--batch', str(10 ** 6)])
        finally:
            if saved is None: os.environ.pop('DMSH_VK_BATCH', None)
    finally: ticker.stop()
    lib = root / 'lib' / f'v-{LAYER.chain_version() or ""}' / 'dmsh_vk.lib'
    return (str(lib) if lib.is_file() else None), rc, sum(1 for _ in (root / 'req').glob('*.ctl'))


VERIFIED = 'verified.tsv'    # in the layer's lib/v-<V>/: key<TAB>same|diff for each shader compared with the kept library
VERIFY_JSON = 'verify.json'  # beside it: {"verified": n, "mismatched": m}, counts only (the game page may read them; nothing in it is alarming)


def read_verified(vdir):
    out = {}
    try: text = (Path(vdir) / VERIFIED).read_text()
    except OSError: return out
    for ln in text.splitlines():
        c = ln.split('\t')
        if len(c) == 2 and len(c[0]) == 16 and c[1] in ('same', 'diff'): out[c[0]] = c[1]
    return out


def record_verify(root, version, kept_lib, layer_lib):
    """The layer's entries that the kept library also has, compared with the kept library's entry (entry hashes), the ones not compared before: lib/v-<version>/verified.tsv gains
    a row each and verify.json the counts. A shader whose entry differs stays in the layer's library, which wins over the kept library's in the host (vka_shader.c, kept library).
    → one log line (counts only)"""
    vdir = Path(root) / 'lib' / f'v-{version}'
    done = read_verified(vdir)
    K, N = delta.Library(str(kept_lib)), delta.Library(str(layer_lib))
    try:
        new = []
        for k, i in sorted(N.index.items()):
            if k in done or k not in K.index: continue
            try: hn = N.hash_of(i, zstd)[1]
            except Exception: hn = None
            try: hk = K.hash_of(K.index[k], zstd)[1]
            except Exception: hk = None
            new.append((k, 'same' if hn is not None and hn == hk else 'diff'))
    finally: K.close(); N.close()
    done.update(new)
    tmp = vdir / (VERIFIED + '.tmp'); tmp.write_text(''.join(f'{k}\t{v}\n' for k, v in sorted(done.items()))); os.replace(tmp, vdir / VERIFIED)
    n_same, n_diff = sum(v == 'same' for v in done.values()), sum(v == 'diff' for v in done.values())
    tmp = vdir / (VERIFY_JSON + '.tmp'); tmp.write_text(json.dumps({'verified': n_same, 'mismatched': n_diff}) + '\n'); os.replace(tmp, vdir / VERIFY_JSON)
    return f'sampled keep verify: {n_same} of {n_same + n_diff} played shaders identical' + (f', {n_diff} differ (the layer\'s entries are used)' if n_diff else '')


def stable_seed(game_id, old_version, version, chain):
    """The seed of a check when none is given: the same for one older library and these tools (the game, the older version, DMSH_VK_CHAIN and DMSH_CHAIN), so a check that was
    stopped draws the same sample when it runs again and reuses what it translated; another version of the tools draws anew"""
    h = hashlib.sha256(f'sampled-keep\0{game_id}\0{old_version}\0{version}\0{chain}'.encode()).digest()
    return int.from_bytes(h[:4], 'big') & 0x7fffffff


def file_stamp(spec):
    """[spec, size, mtime_ns] of the game file a spec names (its nearest part that exists: a .nup spec names a path inside the file), [spec] when none can be read"""
    if not spec: return [spec or '']
    p = Path(spec)
    for q in [p] + list(p.parents):
        try: st = q.stat()
        except OSError: continue
        return [str(spec), st.st_size, st.st_mtime_ns]
    return [str(spec)]


def resume_key(game_id, old_version, version, chain, inputs, abi, rom, main_spec, n, n_first, seed, keys):
    """What the translations a stopped check left are valid for: another chain, inputs, game file, sample size or seed (another draw) starts afresh"""
    return {'format': RESUME_FORMAT, 'game': game_id, 'old': old_version, 'version': version, 'chain': chain, 'inputs': inputs, 'abi': abi,
            'files': [file_stamp(rom), file_stamp(main_spec)], 'n': n, 'first': n_first, 'seed': seed,
            'keys': hashlib.sha256('\n'.join(sorted(keys)).encode()).hexdigest()[:16], 'count': len(keys)}


def read_json(path):
    try: return json.loads(Path(path).read_text())
    except (OSError, ValueError): return None


def write_json(path, obj):
    p = Path(path); tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, sort_keys=True) + '\n'); os.replace(tmp, p)


def reused_results(work, keys):
    """How many of keys have a result file in the layer a stopped check left (<work>/layer/lib/v-*/results/<key>.r)"""
    keys = set(keys)
    return sum(1 for f in (Path(work) / 'layer' / 'lib').glob('v-*/results/*.r') if f.name[:-2] in keys)


def prepare_resume(work, key):
    """→ whether the layer of a stopped run with this key is kept (resumed); any other is removed and this key written"""
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    (work / STOPPED_FILE).unlink(missing_ok=True)
    if read_json(work / RESUME_FILE) == key and (work / 'layer').is_dir(): return True
    shutil.rmtree(work / 'layer', ignore_errors=True)
    write_json(work / RESUME_FILE, key)
    return False


def clear_resume(work):
    """A verdict: nothing of the check is kept (the launcher removes the rest of the work folder)"""
    work = Path(work)
    shutil.rmtree(work / 'layer', ignore_errors=True)
    for f in (RESUME_FILE, STOPPED_FILE, PROGRESS_FILE): (work / f).unlink(missing_ok=True)


def chain_of_tree():
    """DMSH_CHAIN of these tools (dm/gfx/nvn/dmsh_chain.h)"""
    m = re.search(r'#define DMSH_CHAIN "([0-9a-f]+)"', (HERE.parent / 'nvn' / 'dmsh_chain.h').read_text())
    return m.group(1) if m else ''


def run(game, pack, old_version, abi, inputs, work, rom, main_spec, n, seed, jobs, translate_fn=translate, out=print, same_abis=(), n_first=None, known=KNOWN_FILE):
    """The whole check → (exit code, result record). translate_fn(game, work, keys, infos, rom, main, jobs) → (new library path or None, the translation's exit code, requests written).
    seed None: stable_seed (the same draw for this older library and these tools, so a stopped check resumes)"""
    import shader_layer as LAYER
    version = LAYER.chain_version() or ''
    if seed is None: seed = stable_seed(game.id, old_version, version, chain_of_tree())
    shaders = Path(pack) / 'shaders'
    oldlib = shaders / f'v-{old_version}' / 'dmsh_vk.lib'
    rec = {'kind': 'sampled-keep', 'old': old_version, 'version': version, 'seed': seed, 'requested': 0, 'sample': 0, 'mismatches': 0, 'accepted': False, 'why': ''}
    decided = [False]
    def done(code, why):
        rec['why'] = why; write_result(shaders, version, rec); decided[0] = True; out(f'sampled keep: {why}'); return code, rec
    def stopped():
        # nothing is decided: the check is asked again, and what it translated stays in the work folder for that run (resume.json); the stop's time holds the next start back
        try: write_json(Path(work) / STOPPED_FILE, {'at_ms': int(time.time() * 1000), 'done': reused_results(work, keys), 'total': len(keys)})
        except OSError: pass
        rec['why'] = 'stopped'; out(f'sampled keep: stopped, no verdict ({reused_results(work, keys)} of {len(keys)} shaders translated are kept for the next run)'); return EXIT_STOPPED, rec
    keys = []
    try: old = delta.Library(str(oldlib))
    except (OSError, ValueError) as e: return done(EXIT_INELIGIBLE, f'the older library cannot be read: {e}')
    try:
        bad = header_problem(old, game.id, inputs, abi, same_abis)
        if bad: return done(EXIT_INELIGIBLE, bad)
        if (old.version, version) in known_transitions(known):   # a known transition of the tools: kept with no sample (the host verifies what is played)
            rec.update(kind='known-transition', from_chain=old.version)
            old.close()   # (it is moved: nothing may hold it open)
            if not known_move(shaders, old_version, version, abi, chain_of_tree(), known_record(old_version, rec['from_chain'], version)): return done(EXIT_INELIGIBLE, 'the known transition could not move the library (left where it was)')
            rec['accepted'] = True
            return done(EXIT_ACCEPTED, f'known transition {rec["from_chain"]} to {version}: the library moved in with no sample')
        infos = library_infos(old)
        srcs = rom_sources(game, {k for k, _, _ in infos})
        infos = [i for i in infos if i[0] in srcs]
        if not infos: return done(EXIT_INELIGIBLE, 'no shader of the older library is in the game\'s RomFS files')
        pairs = read_pairs(game.dir, {k for k, _, _ in infos})
        sample, from_first, from_random, keys[:], dropped = draw_capped(infos, pairs, n, first_size() if n_first is None else n_first, read_first_keys(game.table(FIRST_LIST)), seed)
        out(f'sampled keep: seed {seed}, {from_first} from the starter set, {from_random} random, {len(keys)} in all with the pixel shaders paired with the vertex ones'
            f' (at most {n}), of {len(infos)} shaders' + (f'; {len(dropped)} vertex shaders left out for their many pairs' if dropped else ''))
        rec['requested'] = len(sample); rec['from_first'] = from_first; rec['from_random'] = from_random; rec['total'] = len(keys)
        n_first_used = first_size() if n_first is None else n_first
        if prepare_resume(work, resume_key(game.id, old_version, version, chain_of_tree(), inputs, old.abi, rom, main_spec, n, n_first_used, seed, keys)):
            rec['reused'] = reused_results(work, keys)
            out(f'sampled keep: resuming, {rec["reused"]} of {len(keys)} shaders translated by an earlier run that was stopped')
        try: new, rc, nreq = translate_fn(game, work, keys, infos, rom, main_spec, jobs)
        except KeyboardInterrupt: return stopped()
        if rc == INTERRUPTED: return stopped()
        if new is None: return done(EXIT_INELIGIBLE if rc == 0 else rc, f'the translation made no library (exit {rc}, {nreq} requests written)')
        checked, diff, sgsa = compare(old, new, keys)
        if sgsa != (old.sg, old.sa): diff = sorted(set(diff) | set(checked)); out(f'sampled keep: the new tools answer {sgsa}, the older library was made for {(old.sg, old.sa)}')
        rec.update(sample=len(checked), mismatches=len(diff))
        verdict, why = decide(checked, diff, len(keys))
        if verdict == 'different': return done(EXIT_DIFFERENT, f'not accepted: {len(diff)} of {len(checked)} checked shaders differ')   # (a count, never the keys)
        if verdict == 'few': return done(EXIT_INELIGIBLE, why)
        record = keep_record(old_version, version, len(checked), len(keys), seed, 0)
        if not accept(shaders, old_version, version, abi, chain_of_tree(), record): return done(EXIT_INELIGIBLE, 'the pack has a library of this version already')
        rec['accepted'] = True
        return done(EXIT_ACCEPTED, f'sampled keep: {len(checked)} of {len(checked)} shaders identical')
    finally:
        old.close()
        if decided[0]: clear_resume(work)   # (a verdict: the translation's requests, results and library are not kept; a stop or a failure keeps them for the next run)
        shutil.rmtree(TMPWORK(game.id), ignore_errors=True)


def rom_sources(game, keys):
    """{key: source} of the profile's shader_map.tsv for the keys whose source is a RomFS file (shader_seed.py read_sources; main's and captured shaders cannot be read back)"""
    import shader_seed as SEED
    src = SEED.read_sources(game.table('shader_map.tsv'), set(keys))
    return {k: s for k, s in src.items() if s.startswith('/') and not s.startswith(SEED.NOT_ROMFS)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--game', required=True); ap.add_argument('--pack', required=True); ap.add_argument('--old', required=True)
    ap.add_argument('--same-abis', default=''); ap.add_argument('--abi', required=True); ap.add_argument('--inputs', required=True); ap.add_argument('--work', required=True)
    ap.add_argument('--romfs', required=True); ap.add_argument('--main')
    ap.add_argument('--n', type=int); ap.add_argument('--first', type=int); ap.add_argument('--seed', type=int)
    ap.add_argument('--jobs', type=int, default=int(os.environ.get('J', '1')))
    try: a = ap.parse_args(argv)
    except SystemExit as e: return 2 if e.code else 0
    n = sample_size() if a.n is None else a.n
    if n <= 0: print('sampled keep: switched off (DM_SHADER_SAMPLE=0)'); return EXIT_INELIGIBLE
    seed = a.seed if a.seed is not None else int(os.environ[SEED_ENV]) if os.environ.get(SEED_ENV, '').strip().isdigit() else None   # (None: stable_seed, so a stopped check resumes)
    os.environ['DM_GAME'] = a.game
    sys.path.insert(0, str(HERE.parent.parent / 'games'))   # dm/games (HERE is dm/gfx/tools; the packer's interpreter has no 'game' on its path otherwise: 2026-11-16 phone test)
    import game as G
    import faulthandler
    stacks = open(Path(a.work) / 'stacks.txt', 'w')   # (its own file: the packer's stdout is not a file descriptor faulthandler can write to)
    faulthandler.dump_traceback_later(90, repeat=True, file=stacks)   # where a slow or stuck check waits, every 1.5 minutes (cancelled at the end)
    try:
        code, _ = run(G.load(a.game), a.pack, a.old, a.abi, a.inputs, a.work, a.romfs, a.main, n, seed, a.jobs, same_abis=tuple(a.same_abis.split()),
                       n_first=first_size() if a.first is None else max(0, a.first))
    finally:
        faulthandler.cancel_dump_traceback_later(); stacks.close()
    return code


if __name__ == '__main__':
    sys.exit(main())
