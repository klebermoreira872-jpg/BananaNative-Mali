#!/usr/bin/env python3
"""dm/gfx/tools/shader_seed.py without game data: records are made up and the readers replaced, so the request writer (code first, .ctl last, the control cut to the host's 0xd8
bytes), the check that the bytes hash to the key, the order the .ctl times give, the pairs, the skipped requests, the dry run and the counts are tested. shader_layer.py's
read_requests reads the seeds back. With an Ocarina of Time .nup in the folder `$BN_NUP_DIR` names the real scan is tried too (skipped without it)."""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools')); sys.path.insert(0, str(REPO / 'dm/games'))
GAME = '0400A3A01EE4C000'
os.environ.setdefault('DM_GAME', GAME)
import shader_seed as D   # noqa: E402
L = D.L; S = D.S


def nvn2(stage_byte, seed, extra=0):
    ctl = bytearray(0xd8 + extra); ctl[:4] = bytes.fromhex('34127698'); ctl[4:8] = b'\xc9\0\0\0'; ctl[0x56] = stage_byte; ctl[0x60] = seed
    code = bytes([seed]) * 64
    struct.pack_into('<I', ctl, 0x44, len(code))
    return bytes(ctl), code


def entry(stage_byte, seed, extra=0):
    ctl, code = nvn2(stage_byte, seed, extra)
    S.KEY_SKIP = (0, 0)
    cut = ctl[:D.CTL_LEN]
    return S.skey(cut, code), ('where', 'vs', ctl, code, ())


class Seed(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = Path(self.t.name)
        self.game = L.G.load(GAME)
        self.keys, self.ents = [], {}
        for i in range(1, 7):
            k, e = entry(5 + i % 3, i, extra=0x20 if i == 3 else 0)   # (the third has a longer control section: the host cuts it)
            self.keys.append(k); self.ents[k] = e
        self.first = self.d / 'first.tsv'
        self.first.write_text('# starter\n' + ''.join(f'{k}\t{"pixel" if i % 2 == 0 else "vertex"}\n' for i, k in enumerate(self.keys)))
        # keys 0,1 in file A; 2,3,4 in file B; 5 in main; one more key is in file A's map row but its record is missing from the scan
        self.maprows = {self.keys[0]: '/A.bin#BNSH@0x0#var0', self.keys[1]: '/A.bin#BNSH@0x0#var1', self.keys[2]: '/dir/B.zs/x#BAHS@1', self.keys[3]: '/dir/B.zs#BAHS@2',
                        self.keys[4]: '/dir/B.zs/y#BAHS@3', self.keys[5]: 'main'}
        self.pairs = d = self.d / 'pairs_src.tsv'
        d.write_text('# pairs\n' + f'{self.keys[0]}\t{self.keys[1]}\n{self.keys[2]}\t{self.keys[3]}\n{self.keys[0]}\t{self.keys[5]}\nffffffffffffffff\t{self.keys[1]}\n')
        mp = self.d / 'map.tsv'
        mp.write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(f'p.bin\t0\tvertex\t{k}\t{s}\n' for k, s in self.maprows.items()))

        class G:
            def get(_, k, d=None): return d
            def table(_, n): return str({'shader_map.tsv': mp, 'shader_pairs.tsv': d}[n])
        self.fake = G()
        self.scanned = []
        self.saved = D.list_files, D.scan_files
        D.list_files = lambda rom: ([('/x/A.bin', 'A.bin'), ('/x/dir/B.zs', 'dir/B.zs'), ('/x/C', 'C')], {})
        def scan(files, zd, want, rom, main, jobs):
            self.scanned.append(set(want))
            for rel in sorted(want):
                yield rel, {k: e for k, e in self.ents.items() if self.maprows[k].startswith('/' + rel)}
        D.scan_files = scan
        self.root = self.d / 'layer'
        self.out = []

    def tearDown(self):
        D.list_files, D.scan_files = self.saved; self.t.cleanup()

    def run_seed(self, **kw):
        return D.seed(self.fake, self.root, self.first, 'rom', out=self.out.append, **kw)

    def test_seed_writes_whole_requests_in_list_order(self):
        self.assertEqual(self.run_seed(), (5, 1, 0, 2))   # the main's key is counted, two pairs have both keys requested
        req = self.root / 'req'
        self.assertEqual(sorted(p.name for p in req.iterdir() if p.suffix == '.tmp'), [])
        reqs, bad, pairs = L.read_requests(req, self.game)
        self.assertEqual(bad, [])
        self.assertEqual(list(reqs), self.keys[:5])   # read_requests orders by the .ctl times: the list's order
        self.assertEqual(len((req / f'{self.keys[2]}.ctl').read_bytes()), D.CTL_LEN)   # the host's cut
        self.assertEqual((req / f'{self.keys[2]}.code').read_bytes(), self.ents[self.keys[2]][3])
        self.assertEqual(pairs, [(self.keys[0], self.keys[1]), (self.keys[2], self.keys[3])])
        self.assertEqual((req / 'pairs.tsv').read_text(), f'{self.keys[0]}\t{self.keys[1]}\n{self.keys[2]}\t{self.keys[3]}\n')
        import time
        ages = [time.time() - (req / f'{k}.ctl').stat().st_mtime for k in self.keys[:5]]
        self.assertTrue(all(a > L.GRACE_S for a in ages)); self.assertEqual(ages, sorted(ages, reverse=True))
        self.assertEqual(self.out[-1], 'seeded 5 requests (1 keys not found, 0 already requested), 2 pairs')
        self.assertIn('seed 5 5', self.out)

    def test_second_run_skips_and_keeps_pairs_once(self):
        self.run_seed(); self.out.clear()
        (self.root / 'req' / 'pairs.tsv').write_text(f'{self.keys[0]}\t{self.keys[1]}')   # a last line cut short, no newline
        self.assertEqual(self.run_seed(), (0, 1, 5, 1))
        self.assertEqual((self.root / 'req' / 'pairs.tsv').read_text(), f'{self.keys[0]}\t{self.keys[1]}\n{self.keys[2]}\t{self.keys[3]}\n')
        self.assertEqual(len(self.scanned), 1)   # the second run reads nothing: only main's key is left, and it has no file

    def test_limit_dry_run_and_bad_record(self):
        self.assertEqual(self.run_seed(dry=True, limit=2), (2, 0, 0, 1))
        self.assertFalse(self.root.exists())   # nothing written
        self.assertEqual(self.scanned[-1], {'A.bin'})   # only the files of the first two keys
        self.ents[self.keys[1]] = ('where', 'vs', self.ents[self.keys[1]][2], b'\x07' * 64, ())   # code that does not hash to the key
        self.assertEqual(self.run_seed(limit=2), (1, 1, 0, 0))
        self.assertTrue((self.root / 'req' / f'{self.keys[0]}.ctl').is_file()); self.assertFalse((self.root / 'req' / f'{self.keys[1]}.ctl').exists())

    def test_stop_leaves_whole_requests(self):
        def scan(files, zd, want, rom, main, jobs):
            yield 'A.bin', {k: self.ents[k] for k in self.keys[:2]}
            raise KeyboardInterrupt
        D.scan_files = scan
        with self.assertRaises(KeyboardInterrupt): self.run_seed()
        req = self.root / 'req'
        self.assertEqual(sorted(p.name for p in req.glob('*.ctl')), sorted(f'{k}.ctl' for k in self.keys[:2]))
        self.assertEqual(L.read_requests(req, self.game)[1], [])
        self.assertEqual(len((req / 'pairs.tsv').read_text().splitlines()), 1)

    def test_list_and_args(self):
        self.first.write_text('# c\n\n0123456789abcdef\tvertex\n0123456789abcdef\tpixel\nfedcba9876543210\n')
        self.assertEqual(D.read_first(self.first), [('0123456789abcdef', 'vertex'), ('fedcba9876543210', '')])
        self.first.write_text('nothex\tvertex\n')
        with self.assertRaises(D.Bad): D.read_first(self.first)
        self.assertEqual(D.main(['--game', GAME, '--root', str(self.root), '--first', str(self.d / 'none.tsv'), '--romfs', 'x']), 2)
        self.assertEqual(D.main(['--game', GAME, '--root', str(self.root)]), 2)
        self.assertEqual(D.main(['--game', GAME, '--root', str(self.root), '--first', str(self.first), '--romfs', 'x', '--limit', '0']), 2)

    def test_rel_of(self):
        rels = {'Shader/a.bfsha.zs', 'Lib/x.sarc.zs'}
        self.assertEqual(D.rel_of('/Shader/a.bfsha.zs#BNSH@0x10#var0', rels), 'Shader/a.bfsha.zs')
        self.assertEqual(D.rel_of('/Lib/x.sarc.zs/m#BAHS@3', rels), 'Lib/x.sarc.zs')
        self.assertIsNone(D.rel_of('main', rels)); self.assertIsNone(D.rel_of('/glslc_capture/a.glslc', rels)); self.assertIsNone(D.rel_of('/Other/b', rels))


OOT = '0400486024DEC000'
_ND = Path(os.environ['BN_NUP_DIR']) if os.environ.get('BN_NUP_DIR') else None
NUP = next(iter(sorted(_ND.glob('The Legend of Zelda Ocarina of Time*.nup'))), None) if _ND and _ND.is_dir() else None


@unittest.skipUnless(NUP, 'the Ocarina of Time .nup is not here')
class Real(unittest.TestCase):
    def test_real_scan(self):
        game = L.G.load(OOT)
        with open(game.table('shader_map.tsv'), encoding='utf-8') as f: rows = [ln.split('\t') for ln in f if not ln.startswith('#')][1:]
        pick = [r for r in rows if r[4].startswith('/Shader/')][:3]
        with tempfile.TemporaryDirectory() as t:
            first = Path(t) / 'first.tsv'; first.write_text(''.join(f'{r[3]}\t{r[2]}\n' for r in pick))
            res = D.seed(game, Path(t) / 'layer', first, str(NUP), jobs=1, out=lambda s: None)
            self.assertEqual(res[:3], (3, 0, 0))
            reqs, bad, _ = L.read_requests(Path(t) / 'layer' / 'req', game)
            self.assertEqual((sorted(reqs), bad), (sorted(r[3] for r in pick), []))


if __name__ == '__main__':
    unittest.main()
