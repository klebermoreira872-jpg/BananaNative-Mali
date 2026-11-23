"""The launcher's shared-font stand-ins (GameFonts.java with android/app/src/jvmtest's GameFontsJvmTest): the APK carries Noto Sans Regular (dm/third_party/fonts), the launcher places it as
<files>/fonts/standard.ttf and passes DM_FONT_DIR, so shared-font text does not depend on the phone's fonts (issue #223). The JVM part is skipped without a JDK."""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
JAVA = REPO / 'android/app/src/main/java/dev/nxnative/android'
SRC = JAVA / 'GameFonts.java'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/GameFontsJvmTest.java'
FONTS = REPO / 'dm/third_party/fonts'


class Wiring(unittest.TestCase):
    def test_activity_sets_the_folder_before_the_players_lines(self):
        t = (JAVA / 'GameActivity.java').read_text(encoding='utf-8')
        self.assertIn('GameFonts.envLine(', t)
        self.assertLess(t.index('GameFonts.envLine('), t.index('env.addAll(user);'))   # the player's DM_FONT_DIR line comes later and wins

    def test_gradle_copies_the_font_from_third_party(self):
        g = (REPO / 'android/app/build.gradle').read_text(encoding='utf-8')
        self.assertIn("'dm/third_party/fonts'", g)
        self.assertIn('NotoSans-Regular-subset.ttf', g)

    def test_asset_name_exists(self):
        self.assertTrue((FONTS / Path('NotoSans-Regular-subset.ttf')).is_file())
        self.assertTrue((FONTS / 'OFL.txt').is_file())

    def test_font_matches_its_record(self):
        # dm/third_party/fonts/README.md names the file's size and sha256; a changed font needs the record changed
        readme = (FONTS / 'README.md').read_text(encoding='utf-8')
        data = (FONTS / 'NotoSans-Regular-subset.ttf').read_bytes()
        self.assertIn(hashlib.sha256(data).hexdigest(), readme)
        self.assertIn(f'{len(data):,} bytes', readme)
        self.assertEqual(data[:4], b'\x00\x01\x00\x00')   # plain TrueType: not a collection, not CFF
        self.assertNotIn(b'fvar', data[:512])             # static: no variations table in the directory

    def test_font_has_the_symbols(self):
        # Games' font code may take a glyph of the console's standard font for granted: Echoes of Wisdom reads through a missing U+25A1 (docs/reference/services.md,
        # "A game crashes on a glyph the standard shared font lacks"). The merged font has every geometric shape, arrow and operator
        cps = cmap((FONTS / 'NotoSans-Regular-subset.ttf').read_bytes())
        self.assertIn(0x25A1, cps)
        for name, a, b in (('arrows', 0x2190, 0x21FF), ('mathematical operators', 0x2200, 0x22FF), ('geometric shapes', 0x25A0, 0x25FF)):
            self.assertEqual([hex(c) for c in range(a, b + 1) if c not in cps], [], name)
        for c in (0x41, 0x3A9, 0x416, 0x20AC, 0xFFFD, 0x2605, 0x2665, 0x2713):   # A, Omega, Zhe, euro, replacement; star, heart, check mark
            self.assertIn(c, cps, hex(c))

    def test_line_metrics_are_noto_sans(self):
        # The SDK's font engine fits glyphs to the line metrics: Noto Sans Math's win ascent / descent (3105 / 2550), which a plain merge takes, drew all text squashed
        # (Mario Kart 8 Deluxe's quit dialog). Noto Sans Regular v2.015's own: hhea 1069 / -293 / 0, OS/2 typo 1069 / -293 / 0, win 1124 / 395
        import struct
        data = (FONTS / 'NotoSans-Regular-subset.ttf').read_bytes()
        n = struct.unpack('>H', data[4:6])[0]
        tab = {data[12 + 16 * i:16 + 16 * i]: struct.unpack('>I', data[20 + 16 * i:24 + 16 * i])[0] for i in range(n)}
        h, o = tab[b'hhea'], tab[b'OS/2']
        self.assertEqual(struct.unpack('>hhh', data[h + 4:h + 10]), (1069, -293, 0))
        self.assertEqual(struct.unpack('>hhhHH', data[o + 68:o + 78]), (1069, -293, 0, 1124, 395))


def cmap(data):
    # The code points of a TrueType font's cmap subtables (formats 4 and 12), without fontTools
    import struct
    n = struct.unpack('>H', data[4:6])[0]
    tab = {data[12 + 16 * i:16 + 16 * i]: struct.unpack('>II', data[20 + 16 * i:28 + 16 * i]) for i in range(n)}
    o = tab[b'cmap'][0]
    cps = set()
    for i in range(struct.unpack('>H', data[o + 2:o + 4])[0]):
        s = o + struct.unpack('>I', data[o + 8 + 8 * i:o + 12 + 8 * i])[0]
        fmt = struct.unpack('>H', data[s:s + 2])[0]
        if fmt == 4:
            x = struct.unpack('>H', data[s + 6:s + 8])[0]
            ends = struct.unpack(f'>{x // 2}H', data[s + 14:s + 14 + x]); starts = struct.unpack(f'>{x // 2}H', data[s + 16 + x:s + 16 + 2 * x])
            for a, b in zip(starts, ends): cps.update(range(a, b + 1))
        elif fmt == 12:
            for g in range(struct.unpack('>I', data[s + 12:s + 16])[0]):
                a, b, _ = struct.unpack('>III', data[s + 16 + 12 * g:s + 28 + 12 * g]); cps.update(range(a, b + 1))
    cps.discard(0xFFFF)
    return cps


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class GameFontsJvm(unittest.TestCase):
    def test_jvm(self):
        with tempfile.TemporaryDirectory() as d:
            c = subprocess.run(['javac', '-Xlint:all', '-Werror', '-encoding', 'UTF-8', '-d', d, str(SRC), str(TEST)], capture_output=True, text=True)
            self.assertEqual(c.returncode, 0, c.stderr)
            r = subprocess.run(['java', '-cp', d, 'dev.nxnative.android.GameFontsJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
