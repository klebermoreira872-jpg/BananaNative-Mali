#!/usr/bin/env python3
"""dm/gfx/tools/shader_layer.py without a build: requests (control + code files the host dumps) become a package and a profile folder the build tool reads: the records hash to
their keys, a bad file is a problem (removed once it is old enough), the temporary profile is the game's own with a map of the requests and the game's pairs plus theirs, and the
game's manifest is left out; a run takes the requests in the order asked, programs whole, at most a batch of new ones; lib/v-<V>/built.tsv records each key's status and tools
version, one file per version; the last run's results (also of a run that was killed) are carried over to the new request tables' digest unless a vertex shader's pairs changed;
the quota, which counts only this version's folder and the requests, stops a build."""
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools')); sys.path.insert(0, str(REPO / 'dm/games'))
import shader_layer as L   # noqa: E402

GAME = '0400A3A01EE4C000'


def nvn2(stage_byte, seed):
    ctl = bytearray(0xd8); ctl[:4] = bytes.fromhex('34127698'); ctl[4:8] = b'\xc9\0\0\0'; ctl[0x56] = stage_byte; ctl[0x60] = seed
    code = bytes([seed]) * 64
    struct.pack_into('<I', ctl, 0x44, len(code))
    return bytes(ctl), code


class Layer(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = Path(self.t.name)
        self.game = L.G.load(GAME)
        self.req = self.d / 'req'; self.req.mkdir()

    def tearDown(self): self.t.cleanup()

    def put(self, stage_byte, seed, name=None):
        ctl, code = nvn2(stage_byte, seed)
        L.S.KEY_SKIP = (0, 0)
        key = L.S.skey(ctl, code)
        (self.req / f'{name or key}.ctl').write_bytes(ctl); (self.req / f'{name or key}.code').write_bytes(code)
        return key

    def test_requests_package_profile(self):
        a = self.put(5, 1); self.put(5, 2, name='0123456789abcdef')   # the second is not its bytes' hash
        reqs, bad, pairs = L.read_requests(self.req, self.game)
        self.assertEqual(list(reqs), [a]); self.assertEqual(len(bad), 1); self.assertIn('0123456789abcdef', bad[0])
        self.assertEqual(reqs[a][2], 'cs')
        (self.req / 'pairs.tsv').write_text(f'{a}\t{a}\nffffffffffffffff\t{a}\n')
        reqs, bad, pairs = L.read_requests(self.req, self.game)
        self.assertEqual(pairs, [(a, a)])   # a pair needs both keys among the requests
        pkg, profs = L.make_inputs(self.game, reqs, pairs, self.d / 'work')
        rec = (pkg / 'cs_req.bin').read_bytes()
        self.assertEqual(rec[:8], b'BTCDBTCD'); self.assertEqual(struct.unpack_from('<2I', rec, 0x28), (0xd8, 64))
        prof = profs / GAME
        rows = (prof / 'shader_map.tsv').read_text().splitlines()
        self.assertEqual(rows[1].split('\t'), ['cs_req.bin', '0', 'compute', a, 'requested at run time'])
        self.assertTrue((prof / 'game.tsv').is_file()); self.assertFalse((prof / 'vk_delta.tsv').exists()); self.assertFalse((prof / 'shader_seen.tsv').exists())
        self.assertIn(f'{a}\t{a}', (prof / 'shader_pairs.tsv').read_text())
        self.assertGreater(len((prof / 'shader_pairs.tsv').read_text().splitlines()), 17000)   # the game's own pairs stay

    def test_built_tsv(self):
        a = self.put(5, 1); b = self.put(5, 3)
        reqs, _, _ = L.read_requests(self.req, self.game)
        root = self.d / 'layer'; (root / 'lib' / 'v-x').mkdir(parents=True)
        (root / 'lib' / 'v-x' / '_vk_build.json').write_text('[{"key": "%s", "st": "ok", "err": ""}]' % a)
        L.write_built(root, reqs, 'x')
        own = root / 'lib' / 'v-x' / 'built.tsv'
        self.assertEqual(own.read_text(), ''.join(f'{k}\t{"ok" if k == a else "fail"}\tx\n' for k in sorted(reqs)))   # a request the build did not report is settled as a failure
        self.assertFalse((root / 'built.tsv').exists())   # each version has its own list
        # a later run of b alone keeps a's row; a row of a key no longer requested goes
        (root / 'lib' / 'v-x' / '_vk_build.json').write_text('[{"key": "%s", "st": "ok", "err": ""}]' % b)
        (root / 'req').mkdir(); (root / 'req' / f'{a}.ctl').write_bytes(b'x'); (root / 'req' / f'{b}.ctl').write_bytes(b'x')
        with open(own, 'a') as f: f.write('ffffffffffffffff\tok\tx\n')
        L.write_built(root, [b], 'x')
        self.assertEqual(L.read_built(root, 'x'), {a: ('ok', 'x'), b: ('ok', 'x')})
        # another version (the other app sharing the pack folder) has its own list: x's rows settle nothing for it, and its run leaves x's alone
        self.assertEqual(L.read_built(root, 'y'), {})
        (root / 'lib' / 'v-y').mkdir(); (root / 'lib' / 'v-y' / '_vk_build.json').write_text('[{"key": "%s", "st": "ok", "err": ""}]' % a)
        L.write_built(root, [a], 'y')
        self.assertEqual(L.read_built(root, 'y'), {a: ('ok', 'y')}); self.assertEqual(L.read_built(root, 'x'), {a: ('ok', 'x'), b: ('ok', 'x')})
        # the older shared list at the folder's top: only its rows of the version asked count, until that version has its own
        (root / 'built.tsv').write_text(f'{a}\tok\tz\n{b}\tok\tw\n')
        self.assertEqual(L.read_built(root, 'z'), {a: ('ok', 'z')}); self.assertEqual(L.read_built(root, 'x'), {a: ('ok', 'x'), b: ('ok', 'x')})

    def test_order_and_bad_pairs(self):
        a = self.put(5, 1); b = self.put(5, 2); c = self.put(5, 3)
        now = 1_000_000
        for k, t in ((a, 30), (b, 10), (c, 20)): os.utime(self.req / f'{k}.ctl', (now - t, now - t))
        (self.req / 'dead000000000000.ctl').write_bytes(b'cut'); (self.req / 'dead000000000000.code').write_bytes(b'x'); os.utime(self.req / 'dead000000000000.ctl', (now - 5, now - 5))
        (self.req / 'old0000000000000.ctl').write_bytes(b'cut'); os.utime(self.req / 'old0000000000000.ctl', (now - 600, now - 600))
        reqs, bad, _ = L.read_requests(self.req, self.game, now=now)
        self.assertEqual(list(reqs), [a, c, b])   # the order the game asked for them
        self.assertEqual(len(bad), 2)
        self.assertTrue((self.req / 'dead000000000000.ctl').exists())   # young: may be being written
        self.assertFalse((self.req / 'old0000000000000.ctl').exists())   # old: removed, the host asks again

    def test_pick(self):
        reqs = {k: None for k in ('k1', 'k2', 'k3', 'k4', 'k5', 'k6')}   # in the order asked
        pairs = [('k5', 'k2')]
        built = {'k1': ('ok', 'v1'), 'k3': ('fail', 'v1'), 'k4': ('fail', 'v0')}
        self.assertEqual(L.pick(reqs, pairs, built, 'v1', batch=1), ['k1', 'k2', 'k5'])   # the built one, then the first new one with its program's other stage
        self.assertEqual(L.pick(reqs, pairs, built, 'v1', batch=3), ['k1', 'k2', 'k5', 'k4'])   # k3 failed with this version: left out; k4 with an older one: tried again
        self.assertEqual(L.pick(reqs, pairs, built, 'v1'), ['k1', 'k2', 'k5', 'k4', 'k6'])   # the default batch is at least BATCH_MIN
        self.assertTrue(L.settled(('fail', 'v1'), 'v1')); self.assertFalse(L.settled(('fail', ''), 'v1')); self.assertTrue(L.settled(('ok', 'v0'), 'v1'))

    def test_carry_results(self):
        res = self.d / 'res'; res.mkdir()
        def result(key, inputs):
            j = json.dumps({'vk': 't', 'inputs': inputs, 'key': key, 'modules': []}, separators=(',', ':')).encode()
            (res / f'{key}.r').write_bytes(b'DMVKRES1' + struct.pack('<I', len(j)) + j)
        def inputs(key):
            b = (res / f'{key}.r').read_bytes(); return json.loads(b[12:12 + struct.unpack_from('<I', b, 8)[0]])['inputs']
        for k in ('aaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbb', 'cccccccccccccccc', 'dddddddddddddddd'): result(k, '111111111111')
        result('eeeeeeeeeeeeeeee', '999999999999')   # of another run: left as it is
        state = {'game': 'g00000000000', 'layer': '111111111111', 'vs': {'bbbbbbbbbbbbbbbb': ['aaaaaaaaaaaaaaaa'], 'cccccccccccccccc': ['aaaaaaaaaaaaaaaa']}}
        partners = {'bbbbbbbbbbbbbbbb': ['aaaaaaaaaaaaaaaa'], 'cccccccccccccccc': ['aaaaaaaaaaaaaaaa', 'ffffffffffffffff'], 'dddddddddddddddd': ['aaaaaaaaaaaaaaaa']}
        self.assertEqual(L.carry_results(res, state, 'g00000000000', '222222222222', partners), (2, 2))
        self.assertEqual(inputs('aaaaaaaaaaaaaaaa'), '222222222222'); self.assertEqual(inputs('bbbbbbbbbbbbbbbb'), '222222222222')
        self.assertFalse((res / 'cccccccccccccccc.r').exists()); self.assertFalse((res / 'dddddddddddddddd.r').exists())   # their pixel shaders changed: translated again
        self.assertEqual(inputs('eeeeeeeeeeeeeeee'), '999999999999')
        result('aaaaaaaaaaaaaaaa', '111111111111')
        self.assertEqual(L.carry_results(res, state, 'g11111111111', '222222222222', partners), (0, 0))   # the game's own inputs changed: nothing is carried
        self.assertEqual(L.carry_results(res, None, 'g00000000000', '222222222222', partners), (0, 0))
        self.assertEqual(inputs('aaaaaaaaaaaaaaaa'), '111111111111')

    def test_quota_stops_the_build(self):
        root = self.d / 'layer'; (root / 'req').mkdir(parents=True); (root / 'req' / 'x.code').write_bytes(b'x' * 2000)
        self.assertEqual(L.layer_bytes(root), 2000)
        self.assertEqual(L.main(['--game', GAME, '--root', str(root), '--max-bytes', '1000']), 3)
        # another version's folder (an older APK's, or the other app's) is not this version's to answer for: it never stops this build
        v = L.chain_version()
        (root / 'lib' / 'v-000000000000' / 'results').mkdir(parents=True); (root / 'lib' / 'v-000000000000' / 'dmsh_vk.lib').write_bytes(b'o' * 5000)
        (root / 'lib' / 'v-000000000000' / 'results' / 'k.r').write_bytes(b'r' * 5000)
        (root / 'lib' / f'v-{v}').mkdir(); (root / 'lib' / f'v-{v}' / 'dmsh_vk.lib').write_bytes(b'n' * 500)
        self.assertEqual(L.layer_bytes(root, v), 2500); self.assertEqual(L.layer_bytes(root), 12500)
        self.assertEqual(L.main(['--game', GAME, '--root', str(root), '--max-bytes', '3000']), 0)   # (no request that reads back: nothing to build, and no quota stop)

    def test_killed_run_is_carried(self):
        """A run killed half way (lmkd; a Prepare that stopped it) leaves the results it wrote: the next run, whose request tables differ, carries them to its digest instead
        of translating them again, and never carries a result of another digest"""
        root = self.d / 'layer'; root.mkdir()
        self.req = root / 'req'; self.req.mkdir()
        a = self.put(5, 1); b = self.put(5, 2)
        v = L.chain_version(); vdir = root / 'lib' / f'v-{v}'
        seen = []
        def head(k):
            f = vdir / 'results' / f'{k}.r'; d = f.read_bytes(); return json.loads(d[12:12 + struct.unpack_from('<I', d, 8)[0]])
        def fake_build(killed):
            def run(pkg, lib, env):
                st = json.loads((vdir / L.STATE).read_text())   # saved before the build: the digest this run writes its results with
                seen.append(st['layer'])
                (vdir / 'results').mkdir(parents=True, exist_ok=True)
                keys = [ln.split('\t')[3] for ln in (Path(env['DM_GAMES_DIR']) / GAME / 'shader_map.tsv').read_text().splitlines()[1:]]
                for k in keys[:1] if killed else keys:
                    if (vdir / 'results' / f'{k}.r').is_file() and head(k)['inputs'] == st['layer']: continue   # (a current result: the build keeps it)
                    j = json.dumps({'vk': 't', 'inputs': st['layer'], 'key': k, 'modules': [], 'translated_in': len(seen)}, separators=(',', ':')).encode()
                    (vdir / 'results' / f'{k}.r').write_bytes(b'DMVKRES1' + struct.pack('<I', len(j)) + j)
                if killed: return 137   # the process went: no built.tsv, but the state was saved as it started
                (vdir / '_vk_build.json').write_text(json.dumps([{'key': k, 'st': 'ok'} for k in keys])); return 0
            return run
        orig = L.run_build
        try:
            L.run_build = fake_build(True)
            self.assertEqual(L.main(['--game', GAME, '--root', str(root), '--build', '--work', str(self.d / 'w')]), 137)
            self.assertFalse(L.built_path(root, v).exists())
            done = [p.name[:-2] for p in (vdir / 'results').glob('*.r')]; self.assertEqual(len(done), 1)
            stray = 'eeeeeeeeeeeeeeee'   # a result of some other digest: never moved
            j = json.dumps({'vk': 't', 'inputs': '999999999999', 'key': stray, 'modules': []}, separators=(',', ':')).encode()
            (vdir / 'results' / f'{stray}.r').write_bytes(b'DMVKRES1' + struct.pack('<I', len(j)) + j)
            c = self.put(5, 3)   # a new request: the layer's tables, and so the digest, change
            L.run_build = fake_build(False)
            self.assertEqual(L.main(['--game', GAME, '--root', str(root), '--build', '--work', str(self.d / 'w')]), 0)
        finally: L.run_build = orig
        self.assertNotEqual(seen[0], seen[1])
        self.assertEqual(head(done[0])['inputs'], seen[1]); self.assertEqual(head(done[0])['translated_in'], 1)   # carried from the killed run, not translated again
        for k in {a, b, c} - {done[0]}: self.assertEqual(head(k)['translated_in'], 2)
        self.assertEqual(head(stray)['inputs'], '999999999999')
        self.assertEqual(set(L.read_built(root, v)), {a, b, c})

    def test_chain_version(self):
        self.assertRegex(L.chain_version(), r'^[0-9a-f]{12}$')

    def test_run_build_runs_the_tool_in_process(self):
        tool = L.HERE / 'vk_android_build.py'
        calls = []
        orig = L.runpy.run_path
        L.runpy.run_path = lambda path, run_name=None: (calls.append((path, list(L.sys.argv), L.os.environ.get('DM_GAME'))), L.sys.exit(3))
        try: rc = L.run_build('/p', '/l', {'DM_GAME': 'X'})
        finally: L.runpy.run_path = orig
        self.assertEqual(rc, 3); self.assertEqual(calls, [(str(tool), [str(tool), '--target', 'vulkan', '/p', '/l'], 'X')])
        self.assertNotEqual(L.os.environ.get('DM_GAME'), 'X')   # the environment is put back


class Timing(unittest.TestCase):
    """The per-run timing line (PhaseClock): the phases are read from the build's own progress lines, nothing of the chain's tools is touched"""
    def test_split(self):
        t = [100.0]; c = [(0.0, 0.0)]
        clk = L.PhaseClock(clock=lambda: t[0], cpu=lambda: c[0])
        def at(dt, user, sys_): t[0] = 100.0 + dt; c[0] = (user, sys_)
        at(2.0, 1.5, 0.2); clk.feed('progress 0 90 transla'); clk.feed('te\nstage: reading\nprogress 10 90 translate\n')
        at(30.0, 40.0, 3.0); clk.feed('progress 90 90 library\n')
        at(34.0, 43.0, 3.5); clk.feed('progress 90 90 check\nprogress 90 90 done\n')
        at(35.0, 43.5, 3.6); clk.mark('built.tsv')
        line = clk.line(90, (900, 4000), (300, 4700), 3100)
        self.assertEqual(line, 'shader_layer timing: 90 shaders in 35.0 s, 2.57/s (cpu 43.5+3.6 s): setup 2.0 s, translate 28.0 s (cpu 41.3), library 4.0 s, check 0.0 s, '
                               'after 1.0 s, built.tsv at 35.0 s; peak 3100 MB; free 900 to 300 MB, swap 4000 to 4700 MB')

    def test_no_progress(self):
        t = [0.0]; clk = L.PhaseClock(clock=lambda: t[0], cpu=lambda: (0.0, 0.0)); t[0] = 5.0
        self.assertTrue(clk.line(1).startswith('shader_layer timing: 1 shader in 5.0 s, 0.20/s'))
        self.assertIn('setup 5.0 s', clk.line(1)); self.assertIn('tail 5.0 s', clk.line(1))

    def test_tee_passes_text_through(self):
        import io
        clk = L.PhaseClock(); out = io.StringIO(); tee = L._Tee(out, clk)
        tee.write('progress 1 2 translate\nhello'); tee.flush(); tee.write('\n')
        self.assertEqual(out.getvalue(), 'progress 1 2 translate\nhello\n'); self.assertIn('translate', clk.at)


if __name__ == '__main__':
    unittest.main()
