"""A game with several registered builds (Mario Kart World 1.0.0 and 1.8.0: the same game, another module set and another RomFS) packs from a dump of either:
scripts/pack_android.py dump_modules takes the modules of the build row a dump matches, and optional_keys reads a profile's shader_optional.tsv, the shader keys only some builds have."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('pack_android', REPO / 'scripts/pack_android.py')
pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)

A, B, C, D = ('%032x' % n for n in (1, 2, 3, 4))   # build IDs


class Profile:   # what dump_modules asks of a game profile
    dir = Path('.')
    def __init__(self, modules, builds): self._m, self._b = modules, builds
    def words(self, key): return self._m.split()
    def builds(self): return self._b


def nso(path, build_id):
    path.write_bytes(b'NSO0' + bytes(0x3c) + bytes.fromhex(build_id) + bytes(0x10))


class DumpModules(unittest.TestCase):
    G = Profile('main subsdk0 subsdk1 sdk', {'v0': {'display': '1.0.0', 'main': A, 'subsdk0': B, 'sdk': C},
                                             'v524288': {'display': '1.8.0', 'main': D, 'subsdk0': C, 'subsdk1': B, 'sdk': A}})

    def exefs(self, files):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for n, i in files.items(): nso(d / n, i)
        return d

    def test_every_module_there(self):
        self.assertEqual(pa.dump_modules(self.G, self.exefs({'main': D, 'subsdk0': C, 'subsdk1': B, 'sdk': A})), ['main', 'subsdk0', 'subsdk1', 'sdk'])

    def test_build_with_one_module_less(self):
        self.assertEqual(pa.dump_modules(self.G, self.exefs({'main': A, 'subsdk0': B, 'sdk': C})), ['main', 'subsdk0', 'sdk'])

    def test_unregistered_set_takes_the_modules_there(self):
        self.assertEqual(pa.dump_modules(self.G, self.exefs({'main': A, 'subsdk0': D, 'sdk': C})), ['main', 'subsdk0', 'sdk'])   # ids of no row: Try anyway

    def test_no_main_is_left_to_the_caller(self):
        self.assertEqual(pa.dump_modules(self.G, self.exefs({'subsdk0': D, 'sdk': C})), ['main', 'subsdk0', 'subsdk1', 'sdk'])   # the caller says what is missing


class OptionalKeys(unittest.TestCase):
    def test_file(self):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (d / 'shader_optional.tsv').write_text('# comment\n00aa\t1.0.0\n11bb\t1.8.0\n')
        g = Profile('main', {}); g.dir = d
        self.assertEqual(pa.optional_keys(g), {'00aa', '11bb'})
        g.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.assertEqual(pa.optional_keys(g), set())


class SplitAbsent(unittest.TestCase):
    """split_shaders: the keys of the profile's map that the dump lacks and shader_optional.tsv names go to <package>/_absent.tsv; any other missing key stops the pack"""

    def run_split(self, dump_keys, optional, profile_keys=('k1', 'k2', 'k3'), note=None, capture=None):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        prof = root / 'profile'; prof.mkdir()
        row = lambda k: f'cs_x.bin\t0\tcompute\t{k}\tsrc\n'
        (prof / 'shader_map.tsv').write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(row(k) for k in profile_keys))
        if optional: (prof / 'shader_optional.tsv').write_text(''.join(f'{k}\t1.0.0\n' for k in optional))
        if capture: (prof / capture).write_text('')
        g = Profile('main', {}); g.dir = prof; g.id = '0000000000000000'
        if note is not None: g.get = lambda key, default=None: note if key == 'shader_note' else default
        def fake_run(cmd, env=None):   # shader_split.py: <romfs> <main> <pkg> <map> <facts> <pairs> <pso_pairs>
            Path(cmd[4]).mkdir(parents=True)
            Path(cmd[5]).write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(row(k) for k in dump_keys))
            for f in cmd[6:]: Path(f).write_text('')
            return type('R', (), {'returncode': 0})()
        args = type('A', (), {'shader_python': None})()
        pkg = root / 'pkg'
        old = pa.subprocess.run, pa.shader_python, pa.child_env
        pa.subprocess.run, pa.shader_python, pa.child_env = fake_run, lambda *a, **k: 'python', lambda **k: {}
        try: pa.split_shaders(args, g, root / 'v', pkg, (root / 'romfs', root / 'exefs'))
        finally: pa.subprocess.run, pa.shader_python, pa.child_env = old
        return pkg

    def test_optional_keys_are_listed(self):
        pkg = self.run_split(['k1', 'k2'], ['k3'])
        self.assertEqual((pkg / '_absent.tsv').read_text(), 'k3\n')

    def test_complete_dump_has_no_list(self):
        pkg = self.run_split(['k1', 'k2', 'k3'], ['k3'])
        self.assertFalse((pkg / '_absent.tsv').exists())

    def test_other_missing_key_stops(self):
        with self.assertRaises(pa.Error) as e: self.run_split(['k1'], ['k3'])
        self.assertIn('lack 1 of the 3', str(e.exception))

    def test_missing_shaders_say_how_many_files_are_not_there(self):   # lacking_shaders: a count and an example, and add-on content named only when nothing else explains it
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        prof, rd = root / 'profile', root / 'romfs'; prof.mkdir(); (rd / 'Common/agl.sarc').parent.mkdir(parents=True)
        (rd / 'Common/agl.sarc').write_text('x'); (rd / 'Course').mkdir()
        rows = [('k1', '/Common/agl.sarc/agl_common.sharcb#BAHS@0x10'), ('k2', '/Course/Dlc/course.ptcl#BNSH@0xab000#var0'), ('k3', '/Course/Dlc/course.ptcl#BNSH@0x1#var1'),
                ('k4', 'main#BNSH@0x128f000#var0')]
        (prof / 'shader_map.tsv').write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(f'cs_x.bin\t{i}\tcompute\t{k}\t{s}\n' for i, (k, s) in enumerate(rows)))
        g = Profile('main', {}); g.dir = prof
        said = pa.lacking_shaders(g, rd, ['k2', 'k3'], 4, 0, root / 'tmp')   # their file is not there, and the dump has no add-on content
        self.assertIn('lack 2 of the 4 in the profile\'s shader_map.tsv (e.g. k2, k3): all of them come from files the game files do not have (e.g. /Course/Dlc/course.ptcl)', said)
        self.assertIn('one possible reason (not seen with any game yet) is that these files belong to add-on content (DLC) the dump does not have', said)
        self.assertNotIn('another version', said); self.assertNotIn('usually', said, 'no more is said than the files show')
        said = pa.lacking_shaders(g, rd, ['k1', 'k2', 'k3'], 4, 0, root / 'tmp')   # one of the missing shaders comes from a file that is there: DLC does not explain the dump
        self.assertIn('lack 3 of the 4', said); self.assertIn('2 of them from files the game files do not have (e.g. /Course/Dlc/course.ptcl): the dump is of another version or incomplete', said)
        self.assertNotIn('DLC', said)
        said = pa.lacking_shaders(g, rd, ['k2', 'k3'], 4, 1, root / 'tmp')   # the same with add-on content in the dump: not the DLC
        self.assertIn('2 of them from files the game files do not have (e.g. /Course/Dlc/course.ptcl): the dump is of another version or incomplete', said)
        self.assertNotIn('DLC', said)
        said = pa.lacking_shaders(g, rd, ['k1', 'k4'], 4, 0, root / 'tmp')   # the container is there (its shaders differ), and main always is
        self.assertIn('lack 2 of the 4 in the profile\'s shader_map.tsv (e.g. k1, k4): the dump is of another version or incomplete', said)
        self.assertNotIn('DLC', said)
        said = pa.lacking_shaders(g, rd, ['k2'], 4, None, root / 'tmp')   # how much add-on content the dump has is not known: the count, and no guess
        self.assertIn('1 of them from files the game files do not have (e.g. /Course/Dlc/course.ptcl): the dump is of another version or incomplete', said)
        self.assertNotIn('DLC', said)
        said = pa.lacking_shaders(g, f'{root}/game.nup:base/romfs', ['k2'], 4, 0, root / 'tmp')   # a RomFS in a .nup is not asked: what the tables say
        self.assertIn('lack 1 of the 4 in the profile\'s shader_map.tsv (e.g. k2): the dump is of another version or incomplete', said)
        self.assertNotIn('DLC', said)

    def test_a_split_without_shaders_stops(self):
        for keys in ((), ('k1',)):   # with rows in the profile's map too: the same words, not "lack 1 of the 1"
            with self.assertRaises(pa.Error) as e: self.run_split([], [], keys, note='Some Game shaders (provisional profile; none read yet)')
            self.assertIn('the shader split read no shader', str(e.exception)); self.assertIn('--no-shaders packs the code alone', str(e.exception))

    def test_a_game_without_nvn_shaders_packs_an_empty_split(self):
        for kw in ({'note': 'Hades has no NVN shaders (its SPIR-V shaders go through the Vulkan layer)'}, {'capture': 'gl_capture.tsv'}, {'capture': 'vk_capture.tsv'}):
            self.assertTrue(self.run_split([], [], (), **kw).is_dir(), kw)

    def test_the_profiles_say_which_games_have_no_nvn_shaders(self):   # the profiles as they are: every map without rows, and what its profile says
        none = sorted(d.name for d in (REPO / 'dm/games').iterdir() if (d / 'shader_map.tsv').is_file() and not pa.map_keys(d / 'shader_map.tsv'))
        said = [t for t in none if pa.no_nvn_shaders(pa.game.load(t))]
        self.assertEqual([t for t in none if t not in said], [], 'a profile with an empty map says why')
        for t in none: pa.require_shaders(pa.game.load(t))
        pa.require_shaders(pa.game.load('0100152000022000'))   # a map with rows: nothing to ask
        g = Profile('main', {}); g.dir = Path(self.enterContext(tempfile.TemporaryDirectory())); g.id = '0000000000000000'
        (g.dir / 'shader_map.tsv').write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n')
        with self.assertRaises(pa.Error) as e: pa.require_shaders(g)
        self.assertIn('has no shader in its shader_map.tsv', str(e.exception))
        src = (REPO / 'scripts/pack_android.py').read_text(encoding='utf-8')
        body = src[src.index('def pack_shaders('):]
        self.assertLess(body.index('require_shaders(g)'), body.index('library_current(lib, g)'), 'before a cached library is taken')

    def test_absent_optional(self):
        """pack_shaders builds the library without the keys of _absent.tsv only when the profile's shader_optional.tsv names every one"""
        pkg = self.run_split(['k1', 'k2'], ['k3'])
        g = Profile('main', {}); g.dir = pkg.parent / 'profile'
        self.assertEqual(pa.absent_optional(g, pkg), {'k3'})
        (pkg / '_absent.tsv').write_text('k2\nk3\n')
        self.assertEqual(pa.absent_optional(g, pkg), set(), 'k2 is not optional')
        (pkg / '_absent.tsv').unlink()
        self.assertEqual(pa.absent_optional(g, pkg), set())


class SplitOtherVersions(unittest.TestCase):
    """Tables that are the union of two versions (game.tsv shader_versions), a dump of one of them (may_lack): the rows tagged with the other listed version may be lacking"""

    def union(self, versions='v100 v200'):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        prof = root / 'profile'; prof.mkdir()
        srcs = {'k1': '/Common/a.ptcl#BNSH@0x1', 'k2': 'main#BNSH@0x2', 'k3': '/v200/Common/a.ptcl#BNSH@0x3', 'k4': 'main@v200#BNSH@0x4'}
        row = lambda k: f'cs_x.bin\t0\tcompute\t{k}\t{srcs[k]}\n'
        (prof / 'shader_map.tsv').write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(row(k) for k in srcs))
        g = Profile('main', {}); g.dir = prof; g.id = '0000000000000000'; g.words = lambda key: versions.split() if key == 'shader_versions' else ['main']
        def split(dump_keys, ver):
            def fake_run(cmd, env=None):
                Path(cmd[4]).mkdir(parents=True)
                Path(cmd[5]).write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\n' + ''.join(row(k) for k in dump_keys))
                for f in cmd[6:]: Path(f).write_text('')
                return type('R', (), {'returncode': 0})()
            args = type('A', (), {'shader_python': None, 'pack_ver': ver})()
            pkg = root / f'pkg{len(list(root.iterdir()))}'
            old = pa.subprocess.run, pa.shader_python, pa.child_env
            pa.subprocess.run, pa.shader_python, pa.child_env = fake_run, lambda *a, **k: 'python', lambda **k: {}
            import contextlib, io
            said = io.StringIO()
            try:
                with contextlib.redirect_stdout(said): pa.split_shaders(args, g, root / 'v', pkg, (root / 'romfs', root / 'exefs'))
            finally: pa.subprocess.run, pa.shader_python, pa.child_env = old
            return pkg, said.getvalue()
        return g, split

    def test_a_dump_of_one_listed_version_builds(self):
        g, split = self.union()
        self.assertEqual(pa.other_versions(g, 100), ['v200'])
        self.assertEqual(pa.other_version_keys(g, 100), {'k3', 'k4'})
        pkg, said = split(['k1', 'k2'], 100)
        self.assertEqual((pkg / '_absent.tsv').read_text(), 'k3\nk4\n')
        self.assertIn('shaders: 2 of 4 shaders in this app\'s table belong to other versions of the game (v200): not needed for v100\n', said)
        self.assertEqual(pa.absent_optional(g, pkg, 100), {'k3', 'k4'}, 'the library is built without them, as for shader_optional.tsv')
        self.assertEqual(pa.absent_optional(g, pkg), set(), 'not without the dump\'s version')

    def test_an_unlisted_version_is_refused_as_before(self):
        g, split = self.union()
        self.assertEqual(pa.other_version_keys(g, 300), set())
        with self.assertRaises(pa.Error) as e: split(['k1', 'k2'], 300)
        self.assertIn('lack 2 of the 4', str(e.exception)); self.assertIn('the dump is of another version or incomplete', str(e.exception))

    def test_all_versions_keys_are_required_otherwise(self):
        g, split = self.union()
        pkg, said = split(['k1', 'k2', 'k3', 'k4'], 100)   # nothing lacking
        self.assertFalse((pkg / '_absent.tsv').exists()); self.assertNotIn('other versions', said)
        with self.assertRaises(pa.Error) as e: split(['k1', 'k3', 'k4'], 100)   # an untagged shader missing: the versions do not explain it
        self.assertIn('lack 1 of the 4', str(e.exception))
        with self.assertRaises(pa.Error): split(['k1', 'k3', 'k4'], 200)   # the tags do not say what a later version dropped
        g1, split1 = self.union('v100')   # one version: every key
        self.assertEqual(pa.other_version_keys(g1, 100), set())
        with self.assertRaises(pa.Error): split1(['k1', 'k2'], 100)
        g2, _ = self.union('v100 v2000')   # v200 is not v2000
        self.assertEqual(pa.other_version_keys(g2, 100), set())

    def test_mario_kart_8_deluxe_is_two_versions(self):   # the profile as it is: 135 of 29,785 rows are 4.0.1's own
        g = pa.game.load('0100152000022000')
        self.assertEqual(pa.shader_versions(g), ['v1441792', 'v1507328'])
        self.assertEqual(len(pa.other_version_keys(g, 1441792)), 135)
        self.assertEqual(len(pa.map_keys(g.dir / 'shader_map.tsv')), 29785)
        self.assertEqual(pa.other_version_keys(g, 1507328), set(), 'what 4.0.1 dropped of 4.0.0 is not in the tags: its shader_optional.tsv names those')
        named = {l.split('\t')[0] for l in (g.dir / 'shader_optional.tsv').read_text().splitlines() if '4.0.1 only' in l}
        self.assertEqual(pa.other_version_keys(g, 1441792), named, 'the tags agree with the profile\'s own list of 4.0.1\'s shaders')

    def test_super_mario_bros_wonder_names_both_sides(self):   # its shader_optional.tsv already names each version's own keys: the tags agree with it
        g = pa.game.load('010015100B514000')
        tagged = pa.other_version_keys(g, 0)
        named = {l.split('\t')[0] for l in (g.dir / 'shader_optional.tsv').read_text().splitlines() if '(v327680) only' in l}
        self.assertEqual(tagged, named); self.assertEqual(len(tagged), 3457)


class MarioKartWorldOptional(unittest.TestCase):
    """Mario Kart World 1.8.0 as update 917504 (Forgejo #50): its split lacks only the profile's optional key, which the profile's map has"""

    def test_profile(self):
        d = REPO / 'dm/games/0400C3F00006E000'
        g = Profile('main', {}); g.dir = d
        self.assertEqual(pa.optional_keys(g), {'797e77c2ec4341c5'})
        self.assertLessEqual(pa.optional_keys(g), pa.map_keys(d / 'shader_map.tsv'))


class SplitForwardsJobs(unittest.TestCase):
    """pack_android.py split_shaders forwards -J to shader_split.py as J (#482)"""

    def test_j_passed_to_shader_split(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            g = Profile('main', {}); g.id = '0100000000000000'; g.dir = root / 'prof'; g.dir.mkdir()
            seen = []

            def fake_run(cmd, env=None, **kw):
                seen.append(env)
                Path(cmd[4]).mkdir(parents=True, exist_ok=True)
                Path(cmd[5]).write_text('# map\npackage\tindex\tstage\tdm_ctl_sha16\tsource\na.bin\t0\tvs\tk1\tsrc\n')
                for f in cmd[6:]: Path(f).write_text('')
                return type('R', (), {'returncode': 0})()

            old = pa.subprocess.run, pa.shader_python
            pa.subprocess.run, pa.shader_python = fake_run, lambda *a, **k: 'python'
            try: pa.split_shaders(type('A', (), {'shader_python': None, 'J': 1})(), g, root / 'v', root / 'pkg', (root / 'romfs', root / 'exefs'))
            finally: pa.subprocess.run, pa.shader_python = old
            self.assertEqual(seen[0].get('J'), '1')


if __name__ == '__main__':
    unittest.main()
