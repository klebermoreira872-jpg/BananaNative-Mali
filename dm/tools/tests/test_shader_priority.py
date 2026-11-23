"""dm/tools/shader_priority.py: a static order of a profile's shaders (android/SHADERS.md, "A shader order without playing"). Synthetic profiles in a temporary
games folder; the real profiles are checked for exit code and determinism only when their tables are there."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shader_priority as P  # noqa: E402

HEAD = '# map\n# col\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n'


def key(n):
    return '%016x' % n


def make(root, game, rows, seen=None, facts=None):
    d = root / game
    d.mkdir(parents=True)
    (d / 'shader_map.tsv').write_text(HEAD + ''.join('p.bin\t%d\t%s\t%s\t%s\n' % (i, st, key(k), src) for i, (k, st, src) in enumerate(rows)), encoding='utf-8')
    if seen is not None:
        (d / 'shader_seen.tsv').write_text('# seen\n' + ''.join('%s\t%s\n' % (key(k), 'pixel') for k in seen), encoding='utf-8')
    if facts:
        (d / 'shader_facts.tsv').write_text('# facts\n' + ''.join('%s\t%s\n' % (key(k), json.dumps(v)) for k, v in facts.items()), encoding='utf-8')


def bulk(n0, count, cont, stage='pixel'):
    return [(n0 + i, stage, '/a/bulk.fdata#IDRK@%s#GLSLC@0x%x' % (cont, 0x1000 + 64 * i)) for i in range(count)]


class Order(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._games = P.GAMES
        P.GAMES = self.root

    def tearDown(self):
        P.GAMES = self._games
        self.tmp.cleanup()

    def rows(self):
        r = bulk(1000, 300, '0x10') + bulk(2000, 300, '0x20', 'vertex')
        r += [(1, 'pixel', 'main#GLSLC@0x10'), (2, 'compute', 'main#GLSLC@0x20')]
        r += [(3, 'pixel', '/a/other.fdata#IDRK@0x30#GLSLC@0x10'), (4, 'domain', '/a/other.fdata#IDRK@0x30#GLSLC@0x90')]
        r += [(5, 'compute', '/a/bulk.fdata#IDRK@0x40#GLSLC@0x10')]
        return r

    def test_loose_and_executable_come_first_rare_stage_lower_deterministic(self):
        make(self.root, 'g', self.rows(), facts={5: {'local': [64, 1, 1], 'shared': 0}})
        a = P.rank('g', sibling=False)
        self.assertEqual(a, P.rank('g', sibling=False))
        order = [k for k, *_ in a]
        self.assertEqual(order[0], key(1))                       # in the executable
        self.assertLess(order.index(key(3)), order.index(key(1000)))   # loose file before the bulk archive
        self.assertLess(order.index(key(4)), order.index(key(1000)) + 600)
        self.assertLess(order.index(key(3)), order.index(key(4)))      # domain shader after the pixel one beside it
        self.assertLess(order.index(key(5)), order.index(key(1000)))   # 64x1x1 compute
        self.assertEqual(len(order), len(set(order)))

    def test_unique_shape_before_repeated_shape(self):
        r = []
        for j in range(3):
            r += [(1000 + 100 * j + i, 'pixel', '/a/bulk.fdata#IDRK@0x%x#GLSLC@0x%x' % (0x50 + j, 0x1000 + 17 * i)) for i in range(30)]
        r += [(5000 + i, 'pixel', '/a/bulk.fdata#IDRK@0x99#GLSLC@0x%x' % (0x1000 + 99 * i)) for i in range(30)]
        make(self.root, 'g', r)
        order = [k for k, *_ in P.rank('g', sibling=False)]
        self.assertLess(order.index(key(5000)), order.index(key(1000)))

    def test_sibling_seen_container_is_lifted_and_own_seen_is_not_read(self):
        def game(base, step_x, step_y):
            return ([(base + i, 'pixel', '/a/bulk.fdata#IDRK@0x1#GLSLC@0x%x' % (0x1000 + step_x * i)) for i in range(40)]
                    + [(base + 100 + i, 'pixel', '/a/bulk.fdata#IDRK@0x2#GLSLC@0x%x' % (0x1000 + step_y * i)) for i in range(40)]
                    + [(base + 200 + i, 'pixel', '/a/bulk.fdata#IDRK@0x3#GLSLC@0x%x' % (0x1000 + 7 * i)) for i in range(40)])
        make(self.root, 'a', game(1000, 31, 37), seen=range(1000, 1040))
        make(self.root, 'b', game(7000, 31, 37), seen=range(7100, 7140))   # b's own seen list must not matter
        self.assertEqual(sorted(P.sibling_prior('a').values()), [0.0, 0.0, 1.0])   # from b's list only (container 2 of b), not a's own
        order = [k for k, *_ in P.rank('b', sibling=True)]
        self.assertEqual(set(order[:40]), {key(7000 + i) for i in range(40)})
        self.assertTrue(any('sibling asked for 100%' in w for *_, w in P.rank('b', sibling=True)))
        self.assertFalse(any('sibling' in w for *_, w in P.rank('b', sibling=False)))

    def test_cli_writes_file_and_eval(self):
        make(self.root, 'g', self.rows(), seen=[1, 2, 3])
        out = self.root / 'out.tsv'
        self.assertEqual(P.main(['g', '--top', '5', '--out', str(out), '--no-sibling']), 0)
        lines = out.read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[1].split('\t')[0], key(1))
        self.assertEqual(len(lines[1].split('\t')), 4)
        self.assertEqual(P.main(['g', '--eval', '--no-sibling']), 0)
        self.assertEqual(P.main(['nope']), 2)

    def test_coverage(self):
        order = [(key(i), 'pixel', 1.0, '') for i in range(3000)]
        c = P.coverage(order, {key(1): None, key(2500): None})
        self.assertEqual(c[1000], (1, 0.5))
        self.assertEqual(c[5000], (2, 1.0))


class RealProfile(unittest.TestCase):
    @unittest.skipUnless((P.GAMES / '0400A3A01EE4C000/shader_map.tsv').exists(), 'no Pokopia profile')
    def test_real_profile_is_stable(self):
        a = P.rank('0400A3A01EE4C000', sibling=False)
        b = P.rank('0400A3A01EE4C000', sibling=False)
        self.assertEqual(a[:2000], b[:2000])
        seen = P.read_seen(P.GAMES / '0400A3A01EE4C000/shader_seen.tsv')
        self.assertGreater(P.coverage(a, seen)[5000][1], 0.4)


if __name__ == '__main__':
    unittest.main()
