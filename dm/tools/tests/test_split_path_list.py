"""shader_split.py's list arguments (RomFS, main, DLC) with paths that hold a comma, brackets, spaces and letters outside ASCII.
The lists were parted at every ',', so one game file named with a comma ("Yoru, Tomosu [0100C2901153C000].nup", or a folder above it) became two paths that do not
exist and the split stopped with FileNotFoundError. path_list takes an argument that names something there whole, parts at its own separator when the argument has
one, and only otherwise at ',' (the Mac script's lists). No game files needed: a synthetic RomFS and profile, as test_split_targeted.py's."""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools'))
_had = os.environ.get('DM_GAME'); os.environ['DM_GAME'] = '01007BB017812000'   # shader_split loads a profile at import; other tests expect no default game
import shader_split as ss   # noqa: E402
if _had is None: del os.environ['DM_GAME']
else: os.environ['DM_GAME'] = _had

GAME = '0100F00DF00D0000'   # a profile only this test has (DM_GAMES_DIR)
BUILD = bytes(range(0x10, 0x20))
TABLES = ('shader_map.tsv', 'shader_facts.tsv', 'shader_pairs.tsv', 'pso_pairs.tsv')
ODD = 'Yoru, Tomosu [0100C2901153C000] (夜、灯す), v0'   # a comma, brackets, spaces, letters outside ASCII


def stage(sph_type, n):   # (control section, code area) of one stage (test_split_targeted.py's)
    code = bytearray(ss.GFX_MAGIC + bytes(0x2c)); code += struct.pack('<I', sph_type) + bytes(0x4c); code += bytes.fromhex('0f00000000000000') * 7 + struct.pack('<Q', n)
    ctl = bytearray(0x880); ctl[:4] = ss.CTL_MAGIC; struct.pack_into('<I', ctl, 0x20, 0x880); struct.pack_into('<I', ctl, 0x704, len(code))
    return bytes(ctl), bytes(code)


def bnsh(n):   # a BNSH of one variation: vertex and pixel shader n (test_split_targeted.py's)
    d = bytearray(0x300); d[:8] = b'BNSH\0\0\0\0'; d[0x60:0x64] = b'grsc'
    struct.pack_into('<IQ', d, 0x7c, 1, 0x100); struct.pack_into('<Q', d, 0x110, 0x140)
    for si, desc, (ctl, code) in ((0, 0x200, stage(0x0461, n)), (4, 0x240, stage(0x1462, n))):
        struct.pack_into('<Q', d, 0x148 + 8 * si, desc)
        at = len(d); d += ctl + code
        struct.pack_into('<QQII', d, desc + 8, at, at + len(ctl), len(code), len(ctl))
    struct.pack_into('<I', d, 0x1c, len(d))
    return bytes(d)


class PathList(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(lambda: shutil.rmtree(self.tmp))
        prof = self.tmp / 'profiles' / GAME; prof.mkdir(parents=True)
        (prof / 'game.tsv').write_text(f'title_id\t{GAME}\nbuild\tv0\t1.0.0\tmain={BUILD.hex()}\nshader_groups\t/Shader/=shader\nshader_note\tTest shaders\n')

    def dump(self, name, n):   # <tmp>/<name>/romfs with one BNSH of shader n, and <tmp>/<name>/exefs/main
        d = self.tmp / name
        (d / 'romfs' / 'Shader').mkdir(parents=True); (d / 'romfs' / 'Shader' / f's{n}.bnsh').write_bytes(bnsh(n))
        (d / 'exefs').mkdir(); (d / 'exefs' / 'main').write_bytes(b'NSO0' + bytes(0x3c) + BUILD + bytes(0x100 - 0x50))
        return str(d / 'romfs'), str(d / 'exefs' / 'main')

    def split(self, out, *lists):
        out = self.tmp / out
        env = dict(os.environ, DM_GAME=GAME, DM_GAMES_DIR=str(self.tmp / 'profiles'), J='1', DM_SPLIT_SELECTED='0', PYTHONUTF8='1')
        for k in ('DM_SPLIT_RESUME', 'DM_SPLIT_TARGETED', 'DM_SPLIT_FILES'): env.pop(k, None)
        r = subprocess.run([sys.executable, REPO / 'dm/gfx/tools/shader_split.py', *lists[:2], out / 'pkg', *[out / t for t in TABLES], *lists[2:]],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return [l.split('\t')[4] for l in (out / 'shader_map.tsv').read_text(encoding='utf-8').splitlines() if l.startswith(('vs_', 'ps_', 'cs_')) or '.bin\t' in l]

    def test_path_list(self):
        a, b = str(self.tmp / 'one, two'), str(self.tmp / 'three')
        self.assertEqual(ss.path_list(f'{a},{b}'), [str(self.tmp / 'one'), ' two', b], 'neither is there: parted at every comma, as before')
        os.mkdir(a)
        self.assertEqual(ss.path_list(a), [a], 'a path that is there is one path, whatever it holds')
        self.assertEqual(ss.path_list(a + ss.LIST_SEP + b), [a, b], 'the separator parts a list, and a comma is then a character of a path')
        self.assertEqual(ss.path_list('x/romfs,y/romfs'), ['x/romfs', 'y/romfs'])

    def test_one_dump_named_with_a_comma(self):   # what pack_android.py and the phone's split pass: one RomFS, one main
        rom, main = self.dump(ODD, 1)
        plain = self.split('plain', *self.dump('plain-dump', 1))
        self.assertEqual(len(plain), 2)
        self.assertEqual(self.split('odd', rom, main), plain, 'the same shaders from the same files under another name')

    def test_two_versions_and_dlc_named_with_commas(self):
        r0, m0 = self.dump(ODD, 1)
        r1, m1 = self.dump('v65536, update', 2)
        dlc = self.tmp / 'dlc, [0001]' / '1'; (dlc / 'Shader').mkdir(parents=True); (dlc / 'Shader' / 's3.bnsh').write_bytes(bnsh(3))
        sep = ss.LIST_SEP
        src = self.split('both', r0 + sep + r1, m0 + sep + m1, str(dlc))   # one DLC root that is there: whole
        self.assertEqual(len(src), 6)
        self.assertTrue(any(s.startswith('/v65536, update/Shader/s2.bnsh') for s in src), src)
        self.assertTrue(any(s.startswith('/aoc/1/Shader/s3.bnsh') for s in src), src)


if __name__ == '__main__':
    unittest.main()
