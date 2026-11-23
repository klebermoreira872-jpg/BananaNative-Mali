#!/usr/bin/env python3
"""Sampled keep (dm/gfx/tools/shader_sample.py, android/SHADERS.md "Sampled keep"): the stratified sample (every stage and size class in it, the same for the same seed), the
vertex shaders' pixel mates, the entry comparison on synthetic libraries (an untouched library is accepted and taken over by its header with its marker and inputs, a tampered
entry in the sample is not, one outside it passes: the limit the documentation names), the verify step's counts, the layer's split of verification requests from missing ones, and
the wiring (the host reads the marker, the service runs the tool, the chain's files are untouched). No game files, no translator: the translation is replaced."""
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools')); sys.path.insert(0, str(REPO / 'dm/games')); sys.path.insert(0, str(REPO / 'dm/tools/tests'))
GAME = '0400A3A01EE4C000'
os.environ.setdefault('DM_GAME', GAME)
import vk_android_delta as delta   # noqa: E402
import shader_sample as SS         # noqa: E402
import shader_layer as LAYER       # noqa: E402
from test_android_shader_delta import write_lib, spirv, zstd   # noqa: E402

ABI = delta.abi_digest(); INPUTS = '5dd843bed8d1'


def key(i): return f'{i:016x}'


class FakeGame:
    def __init__(self, d): self.id, self.dir = GAME, d
    def table(self, n): return self.dir / n


class Pick(unittest.TestCase):
    def infos(self):
        out = []
        for i in range(2000): out.append((key(i), 4, 100 + i % 50))          # many small pixel shaders
        for i in range(2000, 2300): out.append((key(i), 4, 5000 + i))        # large pixel shaders
        for i in range(2300, 2340): out.append((key(i), 0, 300 + i % 7))     # vertex shaders
        for i in range(2340, 2343): out.append((key(i), 5, 90))              # three compute shaders: a rare stage
        return out

    def test_size_determinism_and_strata(self):
        inf = self.infos()
        a, b = SS.pick_sample(inf, 300, 7), SS.pick_sample(inf, 300, 7)
        self.assertEqual(a, b); self.assertEqual(len(a), 300); self.assertEqual(len(set(a)), 300)
        self.assertNotEqual(a, SS.pick_sample(inf, 300, 8), 'another seed, another sample')
        st = SS.strata(inf)
        for name, keys in st.items(): self.assertTrue(set(keys) & set(a), f'stratum {name} is in the sample')
        stage = {k: s for k, s, _ in inf}
        self.assertTrue([k for k in a if stage[k] == 5], 'the rare stage is drawn')
        big = {k for k, s, z in inf if z >= 5000}
        self.assertGreater(len(big & set(a)), 20, 'the large shaders are drawn in numbers, not by their share of the library alone')

    def test_small_library_and_zero(self):
        inf = [(key(i), 4, 10) for i in range(5)]
        self.assertEqual(SS.pick_sample(inf, 300, 1), [key(i) for i in range(5)], 'more asked than there are: all of them')
        self.assertEqual(SS.pick_sample(inf, 0, 1), []); self.assertEqual(SS.pick_sample([], 10, 1), [])

    def test_mates(self):
        inf = [(key(1), 0, 10), (key(2), 4, 10), (key(3), 4, 10), (key(4), 0, 10), (key(5), 4, 10)]
        pairs = {key(1): [key(2), key(3), 'ffffffffffffffff'], key(2): [key(1)], key(4): [key(5)]}
        keys, dropped = SS.with_mates([key(1), key(4)], inf, pairs)
        self.assertEqual(keys, [key(1), key(2), key(3), key(4), key(5)]); self.assertEqual(dropped, [])
        keys, dropped = SS.with_mates([key(1), key(4)], inf, pairs, limit=1)
        self.assertEqual((keys, dropped), ([key(4), key(5)], [key(1)]), 'a vertex shader with more pixel mates than the limit is left out')

    def test_capped_total_counts_the_mates(self):
        """DM_SHADER_SAMPLE caps the shaders translated, mates included: the random part is cut first, then the starter set's tail"""
        inf = self.infos()
        pairs = {key(2300 + v): [key(v * 10 + j) for j in range(9)] for v in range(40)}   # each vertex shader with 9 pixel mates (a unit of 10)
        for v, ps in list(pairs.items()):
            for p in ps: pairs.setdefault(p, []).append(v)
        first = [key(2300 + v) for v in range(40)]   # a starter set of vertex shaders only
        s, nf, nr, keys, dropped = SS.draw_capped(inf, pairs, 300, 200, first, 7)
        self.assertLessEqual(len(keys), 300); self.assertEqual((nf, nr), (30, 0), '30 units of 10 fill the 300: no random part')
        self.assertEqual(s, sorted(first[:30]), 'the starter set\'s head, in its order'); self.assertEqual(dropped, [])
        s, nf, nr, keys, _ = SS.draw_capped(inf, pairs, 300, 5, first, 7)
        self.assertEqual(nf, 5); self.assertGreater(nr, 0); self.assertLessEqual(len(keys), 300)
        self.assertTrue(set(keys) >= {k for v in first[:5] for k in [v] + pairs[v]}, 'the starter part is whole, with its mates')
        self.assertEqual((s, keys), SS.draw_capped(inf, pairs, 300, 5, first, 7)[0:4:3], 'the same for the same seed')
        s, nf, nr, keys, _ = SS.draw_capped(inf, {}, 300, 200, [], 7)
        self.assertEqual((nf, nr, len(keys)), (0, 300, 300), 'no pairs, no starter set: the 300 drawn')

    def test_pairs_read_both_tables(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); (t / 'shader_pairs.tsv').write_text(f'# c\n{key(1)}\t{key(2)}\n'); (t / 'pso_pairs.tsv').write_text(f'{key(1)} {key(3)} 9\n')
            self.assertEqual(SS.read_pairs(t, {key(1)}), {key(1): [key(2), key(3)]})

    def test_starter_set_first_then_random(self):
        inf = self.infos()
        first = [key(2341), key(9999), key(5), key(2301), key(5)] + [key(i) for i in range(100, 400)]   # one key not in the library, one twice
        a, nf = SS.draw(inf, 300, 200, first, 7)
        self.assertEqual(nf, 200); self.assertEqual(len(a), 300); self.assertEqual(len(set(a)), 300)
        want = [k for k in dict.fromkeys(first) if k != key(9999)][:200]
        self.assertTrue(set(want) <= set(a), 'the starter set\'s first 200 the library has, in its order')
        self.assertNotIn(key(9999), a)
        self.assertEqual(a, SS.draw(inf, 300, 200, first, 7)[0], 'the same for the same seed')
        b, nf = SS.draw(inf, 300, 200, [], 7)
        self.assertEqual((b, nf), (SS.pick_sample(inf, 300, 7), 0), 'no starter set: all random, as before')
        c, nf = SS.draw(inf, 50, 200, first, 7)
        self.assertEqual(nf, 50); self.assertEqual(sorted(c), sorted(want[:50]), 'a total under the starter share: the starter set only')
        d, nf = SS.draw(inf, 300, 0, first, 7)
        self.assertEqual((d, nf), (SS.pick_sample(inf, 300, 7), 0))

    def test_read_first_keys(self):
        t = Path(tempfile.mkdtemp(prefix='sampfirst_'))
        try:
            f = t / 'shader_first.tsv'
            f.write_text('# starter set\n# key\tstage\n' + f'{key(3)}\tps\n{key(1)}\tvs\n{key(3)}\tps\nnot-a-key\tps\n\n')
            self.assertEqual(SS.read_first_keys(f), [key(3), key(1)])
            self.assertEqual(SS.read_first_keys(t / 'none.tsv'), [])
        finally: shutil.rmtree(t, ignore_errors=True)

    def test_first_size_env(self):
        self.assertEqual(SS.first_size({}), 200); self.assertEqual(SS.first_size({'DM_SHADER_SAMPLE_FIRST': '50'}), 50)
        self.assertEqual(SS.first_size({'DM_SHADER_SAMPLE_FIRST': '0'}), 0); self.assertEqual(SS.first_size({'DM_SHADER_SAMPLE_FIRST': 'x'}), 200)

    def test_sample_size_env(self):
        self.assertEqual(SS.sample_size({}), 300); self.assertEqual(SS.sample_size({'DM_SHADER_SAMPLE': '25'}), 25)
        self.assertEqual(SS.sample_size({'DM_SHADER_SAMPLE': '0'}), 0); self.assertEqual(SS.sample_size({'DM_SHADER_SAMPLE': 'x'}), 300)

    def test_translate_uses_small_translator_calls(self):
        """The check translates BATCH shaders a translator call (a stop lands between calls; 64 a call kept Play waiting ~50 s on a phone), a DMSH_VK_BATCH line wins, and the
        environment is put back"""
        import shader_seed as SEED
        seen = []
        def fake_main(argv): seen.append(os.environ.get('DMSH_VK_BATCH')); return 0
        saved_seed, saved_main, saved_env = SEED.seed, LAYER.main, os.environ.pop('DMSH_VK_BATCH', None)
        SEED.seed = lambda *a, **k: None; LAYER.main = fake_main
        try:
            with tempfile.TemporaryDirectory() as t:
                g = FakeGame(Path(t)); infos = [(key(1), 4, 10)]
                SS.translate(g, Path(t) / 'w1', [key(1)], infos, 'rom', None, 1)
                self.assertNotIn('DMSH_VK_BATCH', os.environ)
                os.environ['DMSH_VK_BATCH'] = '4'
                SS.translate(g, Path(t) / 'w2', [key(1)], infos, 'rom', None, 1)
                self.assertEqual(os.environ.get('DMSH_VK_BATCH'), '4')
        finally:
            SEED.seed, LAYER.main = saved_seed, saved_main
            os.environ.pop('DMSH_VK_BATCH', None)
            if saved_env is not None: os.environ['DMSH_VK_BATCH'] = saved_env
        self.assertEqual(seen, [str(SS.BATCH), '4'])
        self.assertLessEqual(SS.BATCH, 16)


@unittest.skipIf(zstd is None, 'no zstd in this Python')
class Check(unittest.TestCase):
    N = 40

    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix='sampkeep_'))
        self.pack = self.t / 'pack'; self.prof = self.t / 'prof'; self.prof.mkdir()
        self.mods = {key(i): [spirv(20 + i % 9, i)] for i in range(1, self.N + 1)}
        self.sh = [(k, m, b'\x01' * 8) for k, m in self.mods.items()]
        write_lib(self.pack / 'shaders/v-111111111111/dmsh_vk.lib', '111111111111', game=GAME, abi=ABI, shaders=self.sh, inputs=INPUTS)
        (self.pack / 'shaders/v-111111111111/inputs.tsv').write_text(f'game\t{GAME}\ninputs\t{INPUTS}\n')
        (self.prof / 'shader_map.tsv').write_text('package\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(f'a.bin\t{i}\tpixel\t{k}\t/Shader/a.bfsha.zs\n' for i, k in enumerate(self.mods)))
        self.game = FakeGame(self.prof)

    def tearDown(self): shutil.rmtree(self.t, ignore_errors=True)

    def translate(self, tamper=()):
        """a translate_fn that 'translates' the requested keys: the older library's modules, or other ones for the tampered keys"""
        def fn(game, work, keys, infos, rom, main, jobs):
            sh = [(k, [spirv(33, 99)] if k in tamper else self.mods[k], b'\x01' * 8) for k in keys]
            out = Path(work) / 'new' / 'dmsh_vk.lib'
            write_lib(out, LAYER.chain_version(), game=GAME, abi=ABI, shaders=sh, inputs=INPUTS)
            return str(out), 0, len(keys)
        return fn

    def run_check(self, n, seed=5, tamper=(), inputs=INPUTS, abi=ABI):
        return SS.run(self.game, self.pack, '111111111111', abi, inputs, self.t / 'work', 'romfs', None, n, seed, 1, translate_fn=self.translate(tamper), out=lambda *_: None)

    def test_the_starter_set_is_drawn_first_and_logged(self):
        ks = list(self.mods)
        (self.prof / 'shader_first.tsv').write_text('# starter\n' + ''.join(f'{k}\tps\n' for k in ks[::-1][:6]))
        seen, lines = [], []
        def fn(game, work, keys, infos, rom, main, jobs):
            seen.extend(keys); return self.translate()(game, work, keys, infos, rom, main, jobs)
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'wf', 'romfs', None, 10, 3, 1, translate_fn=fn, out=lines.append, n_first=4)
        self.assertEqual(code, SS.EXIT_ACCEPTED)
        self.assertTrue(set(ks[::-1][:4]) <= set(seen)); self.assertEqual(len(seen), 10); self.assertEqual(rec['from_first'], 4)
        self.assertIn('4 from the starter set, 6 random, 10 in all', lines[0])

    def test_identical_is_accepted_and_taken_over(self):
        code, rec = self.run_check(self.N)
        self.assertEqual(code, SS.EXIT_ACCEPTED); self.assertTrue(rec['accepted'])
        V = LAYER.chain_version(); new = self.pack / f'shaders/v-{V}'
        L = delta.Library(str(new / 'dmsh_vk.lib'))
        self.assertEqual((L.version, L.abi, L.game, L.inputs), (V, ABI, GAME, INPUTS), 'the header says this version')
        self.assertEqual(L.chain, SS.chain_of_tree())
        self.assertEqual(len(L.index), self.N)
        old = (self.pack / 'shaders/v-111111111111/dmsh_vk.lib').read_bytes(); got = (new / 'dmsh_vk.lib').read_bytes()
        self.assertEqual(old[128:], got[128:], 'every byte after the header is the older library\'s'); self.assertTrue((self.pack / 'shaders/v-111111111111/dmsh_vk.lib').is_file(), 'the older library stays')
        marker = json.loads((new / SS.KEEP_FILE).read_text())
        self.assertEqual((marker['kind'], marker['old'], marker['sample'], marker['mismatches'], marker['seed']), ('sampled-keep', '111111111111', self.N, 0, 5))
        self.assertIn(INPUTS, (new / 'inputs.tsv').read_text())
        self.assertTrue(json.loads(SS.result_path(self.pack / 'shaders', V).read_text())['accepted'])
        self.assertFalse((self.pack / f'shaders/.restamp-{V}').exists())

    def test_older_abi_with_no_difference_is_stamped_forward(self):
        """a library of an older ABI whose compat row differs in nothing (--same-abis): identical entries are what this ABI holds, the stamp sets the ABI; another older ABI is still refused"""
        write_lib(self.pack / 'shaders/v-111111111111/dmsh_vk.lib', '111111111111', game=GAME, abi='228b73bd10f6', shaders=self.sh, inputs=INPUTS)
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'work', 'romfs', None, self.N, 5, 1, translate_fn=self.translate(), out=lambda *_: None)
        self.assertEqual(code, SS.EXIT_INELIGIBLE, 'without the list the older ABI is refused')
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'work', 'romfs', None, self.N, 5, 1, translate_fn=self.translate(), out=lambda *_: None, same_abis=('228b73bd10f6',))
        self.assertEqual(code, SS.EXIT_ACCEPTED)
        L = delta.Library(str(self.pack / f'shaders/v-{LAYER.chain_version()}/dmsh_vk.lib'))
        self.assertEqual(L.abi, ABI, 'the stamped library carries this ABI')
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'work2', 'romfs', None, self.N, 5, 1, translate_fn=self.translate(), out=lambda *_: None, same_abis=('aaaaaaaaaaaa',))
        self.assertNotEqual(code, SS.EXIT_ACCEPTED)

    def test_tampered_entry_in_the_sample_is_not_accepted(self):
        code, rec = self.run_check(self.N, tamper={key(7)})
        self.assertEqual(code, SS.EXIT_DIFFERENT); self.assertFalse(rec['accepted']); self.assertEqual(rec['mismatches'], 1)
        V = LAYER.chain_version()
        self.assertFalse((self.pack / f'shaders/v-{V}').exists(), 'nothing is taken over')
        self.assertTrue((self.pack / 'shaders/v-111111111111/dmsh_vk.lib').is_file())
        r = json.loads(SS.result_path(self.pack / 'shaders', V).read_text()); self.assertFalse(r['accepted']); self.assertEqual(r['old'], '111111111111')
        self.assertNotIn(key(7), json.dumps(r), 'the record holds counts, no key')

    def test_a_change_outside_the_sample_passes(self):
        """The limit of the method: a change nobody drew is missed (the verify step is what covers it for what is played)"""
        inf = SS.library_infos(delta.Library(str(self.pack / 'shaders/v-111111111111/dmsh_vk.lib')))
        drawn = set(SS.pick_sample(inf, 10, 3)); other = next(k for k, _, _ in inf if k not in drawn)
        code, rec = self.run_check(10, seed=3, tamper={other})
        self.assertEqual(code, SS.EXIT_ACCEPTED); self.assertEqual(rec['sample'], 10)

    def test_not_eligible(self):
        for kw, why in ((dict(inputs='bbbbbbbbbbbb'), 'inputs'), (dict(abi='aaaaaaaaaaaa'), 'ABI')):
            code, rec = self.run_check(self.N, **kw)
            self.assertEqual(code, SS.EXIT_INELIGIBLE, why); self.assertIn(why, rec['why'])
            self.assertFalse((self.pack / f'shaders/v-{LAYER.chain_version()}').exists())

    def test_too_few_found(self):
        """Keys the game's files do not hold (not in the map) cannot be checked: a sample of what could be is too small to prove anything"""
        (self.prof / 'shader_map.tsv').write_text('package\tindex\tstage\tdm_ctl_sha16\tsource\n' + f'a.bin\t0\tpixel\t{key(1)}\t/Shader/a.bfsha.zs\n')
        code, rec = self.run_check(self.N)
        self.assertEqual((code, rec['accepted']), (SS.EXIT_ACCEPTED, True), 'the one shader that is in the map is compared: all of what could be')
        def fewer(game, work, keys, infos, rom, main, jobs):   # the translation lost every request
            return None, 0, 0
        shutil.rmtree(self.pack / f'shaders/v-{LAYER.chain_version()}')
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'w2', 'romfs', None, self.N, 1, 1, translate_fn=fewer, out=lambda *_: None)
        self.assertEqual(code, SS.EXIT_INELIGIBLE)

    def test_a_stop_writes_no_verdict(self):
        """The launcher stops the check (the player starts a game, or skips it): exit EXIT_STOPPED, no result file, so the check can be asked again"""
        def stopped(game, work, keys, infos, rom, main, jobs): return None, SS.INTERRUPTED, 0
        def raised(game, work, keys, infos, rom, main, jobs): raise KeyboardInterrupt
        for fn in (stopped, raised):
            code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'ws', 'romfs', None, self.N, 1, 1, translate_fn=fn, out=lambda *_: None)
            self.assertEqual(code, SS.EXIT_STOPPED)
            self.assertFalse(SS.result_path(self.pack / 'shaders', LAYER.chain_version()).exists(), 'no verdict recorded')

    def resumable(self, stop_after=None, made=None):
        """a translate_fn as the real one keeps its work: a result file a shader in work/layer (only the keys without one are 'translated', into made), then the library;
        stop_after: a KeyboardInterrupt (the launcher's stop) after that many new results"""
        def fn(game, work, keys, infos, rom, main, jobs):
            res = Path(work) / 'layer' / 'lib' / 'v-x' / 'results'; res.mkdir(parents=True, exist_ok=True)
            new = 0
            for k in keys:
                if (res / f'{k}.r').is_file(): continue
                if stop_after is not None and new >= stop_after: raise KeyboardInterrupt
                (res / f'{k}.r').write_bytes(b'r'); new += 1
                if made is not None: made.append(k)
            return self.translate()(game, work, keys, infos, rom, main, jobs)
        return fn

    def run_resumable(self, work, fn, n=None, seed=None, rom='romfs', lines=None):
        return SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, work, rom, None, n or self.N, seed, 1, translate_fn=fn, out=(lines.append if lines is not None else lambda *_: None), n_first=0)

    def test_the_seed_is_stable(self):
        a = SS.stable_seed(GAME, '111111111111', 'aaaaaaaaaaaa', 'cccc')
        self.assertEqual(a, SS.stable_seed(GAME, '111111111111', 'aaaaaaaaaaaa', 'cccc')); self.assertLess(a, 1 << 31)
        self.assertNotEqual(a, SS.stable_seed(GAME, '111111111111', 'bbbbbbbbbbbb', 'cccc'), 'another version of the tools draws anew')
        self.assertNotEqual(a, SS.stable_seed(GAME, '222222222222', 'aaaaaaaaaaaa', 'cccc'))
        code, rec = self.run_resumable(self.t / 'wseed', self.translate(), n=10)
        self.assertEqual(rec['seed'], SS.stable_seed(GAME, '111111111111', LAYER.chain_version(), SS.chain_of_tree()), 'no seed given: the stable one')

    def test_a_stopped_check_resumes_from_what_it_translated(self):
        """A stop keeps the translations and writes stopped.json (counts only); the next run with the same key translates only the rest; a verdict removes it all"""
        w = self.t / 'wr'; made1, made2, lines = [], [], []
        code, rec = self.run_resumable(w, self.resumable(stop_after=15, made=made1))
        self.assertEqual(code, SS.EXIT_STOPPED); self.assertEqual(len(made1), 15)
        self.assertFalse(SS.result_path(self.pack / 'shaders', LAYER.chain_version()).exists(), 'no verdict')
        st = json.loads((w / SS.STOPPED_FILE).read_text())
        self.assertEqual((st['done'], st['total']), (15, self.N)); self.assertGreater(st['at_ms'], 0)
        self.assertNotIn(key(1), (w / SS.STOPPED_FILE).read_text() + (w / SS.RESUME_FILE).read_text(), 'counts and digests, no key')
        code, rec = self.run_resumable(w, self.resumable(made=made2), lines=lines)
        self.assertEqual(code, SS.EXIT_ACCEPTED)
        self.assertEqual(len(made2), self.N - 15); self.assertFalse(set(made1) & set(made2), 'nothing translated twice')
        self.assertEqual(rec['reused'], 15); self.assertTrue(any('resuming, 15 of' in ln for ln in lines))
        self.assertFalse((w / 'layer').exists() or (w / SS.RESUME_FILE).exists() or (w / SS.STOPPED_FILE).exists(), 'a verdict removes the resume state')

    def test_a_changed_key_starts_afresh(self):
        """Another sample size, game file, seed (or chain, inputs: the same key) throws the earlier translations away"""
        w = self.t / 'wk'
        for change in (dict(n=self.N - 1), dict(rom='other-romfs'), dict(seed=99)):
            shutil.rmtree(w, ignore_errors=True)
            self.assertEqual(self.run_resumable(w, self.resumable(stop_after=5))[0], SS.EXIT_STOPPED)
            made = []
            self.run_resumable(w, self.resumable(stop_after=10 ** 6, made=made), **change)
            self.assertGreaterEqual(len(made), self.N - 1, f'{change}: translated afresh')
            shutil.rmtree(self.pack / f'shaders/v-{LAYER.chain_version()}', ignore_errors=True); SS.result_path(self.pack / 'shaders', LAYER.chain_version()).unlink(missing_ok=True)
        k1 = SS.resume_key(GAME, 'o', 'v', 'c', 'i', 'a', 'r', None, 300, 200, 5, ['a', 'b'])
        for i, other in enumerate((SS.resume_key(GAME, 'o', 'v', 'c2', 'i', 'a', 'r', None, 300, 200, 5, ['a', 'b']), SS.resume_key(GAME, 'o', 'v', 'c', 'i2', 'a', 'r', None, 300, 200, 5, ['a', 'b']),
                                   SS.resume_key(GAME, 'o', 'v2', 'c', 'i', 'a', 'r', None, 300, 200, 5, ['a', 'b']), SS.resume_key(GAME, 'o', 'v', 'c', 'i', 'a', 'r', None, 300, 200, 5, ['a', 'c']))):
            self.assertNotEqual(k1, other, i)

    def test_a_known_transition_is_kept_with_no_sample(self):
        """An older library whose header's VK chain the table pairs with this chain is MOVED in without translating anything (no copy: the older folder is gone), with a
        known-transition marker; another pair still samples"""
        V = LAYER.chain_version(); table = self.t / 'known.tsv'
        table.write_text(f'# comment\n111111111111\t{V}\tsynthetic\nnot a row\n')
        before = (self.pack / 'shaders/v-111111111111/dmsh_vk.lib').read_bytes()
        def never(*a): raise AssertionError('no translation for a known transition')
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'wkn', 'romfs', None, self.N, 5, 1, translate_fn=never, out=lambda *_: None, known=table)
        self.assertEqual(code, SS.EXIT_ACCEPTED); self.assertEqual(rec['kind'], 'known-transition')
        new = self.pack / f'shaders/v-{V}'
        marker = json.loads((new / SS.KEEP_FILE).read_text())
        self.assertEqual((marker['kind'], marker['old'], marker['from_chain'], marker['version'], marker['sample']), ('known-transition', '111111111111', '111111111111', V, 0))
        L = delta.Library(str(new / 'dmsh_vk.lib')); self.assertEqual((L.version, L.abi, L.chain), (V, ABI, SS.chain_of_tree())); L.close()
        self.assertEqual((new / 'dmsh_vk.lib').read_bytes()[128:], before[128:]); self.assertIn(INPUTS, (new / 'inputs.tsv').read_text())
        self.assertFalse((self.pack / 'shaders/v-111111111111').exists(), 'moved, not copied')
        self.assertFalse(list((self.pack / 'shaders').glob('.known-*')) or (new / SS.KNOWN_JOURNAL).exists())
        self.assertTrue(json.loads(SS.result_path(self.pack / 'shaders', V).read_text())['accepted'])
        os.rename(new, self.pack / 'shaders/v-111111111111'); (self.pack / 'shaders/v-111111111111' / SS.KEEP_FILE).unlink()
        write_lib(self.pack / 'shaders/v-111111111111/dmsh_vk.lib', '111111111111', game=GAME, abi=ABI, shaders=self.sh, inputs=INPUTS); SS.result_path(self.pack / 'shaders', V).unlink()
        table.write_text(f'222222222222\t{V}\tanother older chain\n111111111111\taaaaaaaaaaaa\tanother new chain\n')
        made = []
        code, rec = SS.run(self.game, self.pack, '111111111111', ABI, INPUTS, self.t / 'wkn2', 'romfs', None, self.N, 5, 1, translate_fn=self.resumable(made=made), out=lambda *_: None, known=table)
        self.assertEqual(code, SS.EXIT_ACCEPTED); self.assertEqual(len(made), self.N, 'not in the table: the sample runs'); self.assertNotEqual(rec.get('kind'), 'known-transition')

    def test_the_known_transitions_table(self):
        """The repository's table: 12-hex columns, and the row the 2026-11-16 entry diff proved"""
        rows = SS.known_transitions()
        self.assertIn(('65883461079b', '19662e4c4a25'), rows)
        for ln in SS.KNOWN_FILE.read_text().splitlines():
            if ln.startswith('#') or not ln.strip(): continue
            c = ln.split('\t'); self.assertGreaterEqual(len(c), 3, ln); self.assertRegex(c[0], r'^[0-9a-f]{12}$'); self.assertRegex(c[1], r'^[0-9a-f]{12}$'); self.assertTrue(c[2].strip(), 'each row says what the diff found')

    def test_progress_file(self):
        """work/progress.json: the requests written, then the results made, counts only"""
        root = self.t / 'pw' / 'layer'; (root / 'req').mkdir(parents=True); (root / 'lib/v-x/results').mkdir(parents=True)
        for i in range(3): (root / 'req' / f'{i:016x}.ctl').write_text('x')
        (root / 'lib/v-x/results/a.r').write_text('x')
        t = SS.Progress(self.t / 'pw', root, 10); t.write()
        self.assertEqual(json.loads((self.t / 'pw' / SS.PROGRESS_FILE).read_text()), {'phase': 'seed', 'done': 3, 'total': 10})
        t.phase = 'translate'; t.write()
        self.assertEqual(json.loads((self.t / 'pw' / SS.PROGRESS_FILE).read_text()), {'phase': 'translate', 'done': 1, 'total': 10})

    def test_decide(self):
        self.assertEqual(SS.decide(['a'] * 10, [], 10)[0], 'accept'); self.assertEqual(SS.decide(['a'] * 4, [], 10)[0], 'few')
        self.assertEqual(SS.decide(['a'] * 10, ['a'], 10)[0], 'different'); self.assertEqual(SS.decide([], [], 0)[0], 'few')

    def test_verify_counts(self):
        """The shaders the game played, translated again in the layer, are compared with the kept library; a difference is counted (and its entry stays in the layer)"""
        kept = self.t / 'kept' / 'dmsh_vk.lib'; write_lib(kept, '222222222222', game=GAME, abi=ABI, shaders=self.sh, inputs=INPUTS)
        lay = self.t / 'layer'; V = '333333333333'; (lay / 'lib' / f'v-{V}').mkdir(parents=True)
        def layer_lib(tamper, extra=()):
            sh = [(k, [spirv(33, 99)] if k in tamper else self.mods[k], b'\x01' * 8) for k in (key(1), key(2), key(3))] + list(extra)
            write_lib(lay / 'lib' / f'v-{V}' / 'dmsh_vk.lib', V, game=GAME, abi=ABI, shaders=sh, inputs=INPUTS)
        layer_lib({key(2)}, extra=[(key(900), [spirv(9, 1)], b'')])   # (key 900: a missing shader of the layer, not in the kept library: not compared)
        line = SS.record_verify(lay, V, kept, lay / 'lib' / f'v-{V}' / 'dmsh_vk.lib')
        self.assertIn('2 of 3', line); self.assertIn('1 differ', line)
        self.assertEqual(json.loads((lay / 'lib' / f'v-{V}' / SS.VERIFY_JSON).read_text()), {'verified': 2, 'mismatched': 1})
        self.assertEqual(SS.read_verified(lay / 'lib' / f'v-{V}'), {key(1): 'same', key(2): 'diff', key(3): 'same'})
        layer_lib({key(2)}, extra=[(key(4), self.mods[key(4)], b'\x01' * 8)])   # a later run: one more, the earlier ones are not compared again
        SS.record_verify(lay, V, kept, lay / 'lib' / f'v-{V}' / 'dmsh_vk.lib')
        self.assertEqual(json.loads((lay / 'lib' / f'v-{V}' / SS.VERIFY_JSON).read_text()), {'verified': 3, 'mismatched': 1})


class Split(unittest.TestCase):
    def test_verification_requests_apart_from_missing_ones(self):
        a, b, c, d, e = (key(i) for i in range(1, 6))
        reqs = {k: None for k in (a, b, c, d, e)}
        kept = {a, b, c}                    # d, e are missing from the kept library
        normal, verify = LAYER.split_requests(reqs, [(a, d)], kept, {})
        self.assertEqual(verify, {b, c}, 'a is the vertex shader of a program with a missing pixel shader: an ordinary request'); self.assertEqual(normal, {a, d, e})
        normal, verify = LAYER.split_requests(reqs, [(a, d)], kept, {b: ('ok', 'v')})
        self.assertEqual(verify, {c}, 'a built one stays in the layer (its entry wins in the host)'); self.assertIn(b, normal)
        self.assertEqual(LAYER.kept_keys(Path('/nonexistent/dmsh_vk.lib')), set())


class Wiring(unittest.TestCase):
    J = REPO / 'android/app/src'

    def text(self, p): return (REPO / p).read_text(encoding='utf-8')

    def test_chain_files_untouched(self):
        """The sampled keep is not one of the chain's files: the version covers exactly these five (vk_android_build.py VK_FILES), and none of them is named in the new tool's imports as one to change"""
        b = self.text('dm/gfx/tools/vk_android_build.py')
        files = re.search(r'VK_FILES\s*=\s*([^\n]+)', b).group(1)
        self.assertNotIn('shader_sample', files); self.assertNotIn('shader_layer', files)
        self.assertNotIn('shader_sample', self.text('dm/gfx/tools/vk_android_delta.py'))

    def test_wired(self):
        host = self.text('dm/gfx/vk_android/vka_shader.c')
        self.assertIn('sampled-keep.json', host); self.assertIn('g_kept && (LY || layer_root())', host)
        svc = self.text('android/app/src/ondevice/java/dev/nxnative/android/LayerService.java')
        self.assertIn('dm/gfx/tools/shader_sample.py', svc); self.assertIn('"--kept"', svc); self.assertIn('"--verify"', svc)
        self.assertIn('sampledKeep(a, dump, packDir, titleId)', self.text('android/app/src/ondevice/java/dev/nxnative/android/Ondevice.java'))
        self.assertIn('layer.keep(runKept', self.text('android/app/src/main/java/dev/nxnative/android/GameActivity.java'))
        self.assertIn('ShaderLibs.kept(lib)', self.text('android/app/src/main/java/dev/nxnative/android/LayerGuard.java'))
        self.assertIn('DM_SHADER_SAMPLE\t', self.text('docs/env_switches.tsv'))
        self.assertIn('Sampled keep', self.text('android/SHADERS.md'))
        pt = self.text('android/app/src/main/java/dev/nxnative/android/PrepareText.java')
        self.assertRegex(pt, r'CHECKING_SHADERS\(\) \{ return Words\.s\("[a-z0-9_]+", "Ready \\u00b7 checking shaders'); self.assertIn('"Shaders up to date"', pt)   # the words the player reads: neither says "older"


if __name__ == '__main__':
    unittest.main()
