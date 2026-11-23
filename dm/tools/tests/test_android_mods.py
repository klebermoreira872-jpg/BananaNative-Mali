"""Mods (android/app/.../Mods.java: the data mods' folders, the zip import and the RomFS overlay line) on the JVM, and the launcher wiring: the profile key, the row, the picker result, the start's overlay."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/ModsJvmTest.java'
GRADLE = REPO / 'android/app/build.gradle'


class Mods(unittest.TestCase):
    def test_wiring(self):
        self.assertIn("modsOf(g)", GRADLE.read_text(encoding='utf-8'))
        self.assertIn('p.mods = c.length > 31', (SRC / 'Profile.java').read_text(encoding='utf-8'))
        self.assertIn('ModsUi.row(a, g, options::add, again)', (SRC / 'GameSettings.java').read_text(encoding='utf-8'))
        self.assertIn('ModsUi.documentResult(this, request, data.getData())', (SRC / 'MainActivity.java').read_text(encoding='utf-8'))
        self.assertIn('Mods.addTo(env, ModsUi.overlay(this, id));', (SRC / 'GameActivity.java').read_text(encoding='utf-8'))
        self.assertIn('\nmods\t1\n', (REPO / 'dm/games/0400A3A01EE4C000/game.tsv').read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
    def test_jvm(self):
        with tempfile.TemporaryDirectory(prefix='mods_') as tmp:
            subprocess.run(['javac', '-Xlint:all', '-Werror', '-encoding', 'UTF-8', '-d', tmp, str(SRC / 'Mods.java'), str(TEST)], check=True, capture_output=True, text=True)
            r = subprocess.run(['java', '-cp', tmp, 'dev.nxnative.android.ModsJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(r.stdout.strip(), 'ok')


if __name__ == '__main__':
    unittest.main()
