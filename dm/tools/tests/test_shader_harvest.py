#!/usr/bin/env python3
"""scripts/shader_harvest.py: the host's `[shaders-missing]` lines, a missing_shaders.tsv and older `[RED] vk: shader ... is not in the shader library` lines are read, a key
already in shader_seen.tsv is not new, a key outside the shader map is not added, and --apply appends each new key once to a selected-set profile only."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
import shader_harvest as H   # noqa: E402

A, B, C, D = '1111111111111111', '2222222222222222', '3333333333333333', '4444444444444444'
TID = '0400A3A01EE4C000'


class Harvest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = Path(self.t.name)
        self.games = self.d / 'games'; (self.games / TID).mkdir(parents=True)
        (self.games / TID / 'shader_map.tsv').write_text('package\tindex\tstage\tdm_ctl_sha16\tsource\n' + f'vs_a.bin\t0\tvertex\t{A}\tx\nps_b.bin\t1\tpixel\t{B}\tx\nvs_c.bin\t2\tvertex\t{C}\tx\n')
        (self.games / TID / 'shader_seen.tsv').write_text(f'# c\n{C}\tvertex\nkey\tstage\n')
        self._g = H.GAMES; H.GAMES = self.games

    def tearDown(self): H.GAMES = self._g; self.t.cleanup()

    def test_parse(self):
        txt = f'[dm] [shaders-missing] {A}\tvertex\n[dm] [RED] vk: shader {B} (program stage 1) is not in the shader library\n[dm] [shaders-missing] {B}\tpixel\nnoise\n'
        self.assertEqual(H.parse_text(txt), {A: 'vertex', B: 'pixel'})
        self.assertEqual(H.parse_text(f'# x\n{A}\tpixel\n{B}\t?\n', tsv=True), {A: 'pixel', B: None})

    def test_plan_and_apply(self):
        log = self.d / f'issue-{TID}-1.log'
        log.write_text(f'[dm] [shaders-missing] {A}\tvertex\n[dm] [shaders-missing] {B}\t?\n[dm] [shaders-missing] {C}\tvertex\n[dm] [shaders-missing] {D}\tvertex\n')
        by = H.collect([self.d])
        self.assertEqual(set(by[TID]), {A, B, C, D})
        (g, new, out, known, sel), = H.plan(by)
        self.assertEqual((g, new, out, known, sel), (TID, [(A, 'vertex'), (B, 'pixel')], [D], 1, True))   # B's stage comes from the map
        H.apply(TID, new, 'issue 1', '2026-11-15')
        rows = H.read_rows(self.games / TID / 'shader_seen.tsv')
        self.assertEqual(rows, {C: 'vertex', A: 'vertex', B: 'pixel', 'key': 'stage'})
        self.assertEqual(H.plan(H.collect([self.d]))[0][1], [])   # a second run adds nothing


if __name__ == '__main__':
    unittest.main()
