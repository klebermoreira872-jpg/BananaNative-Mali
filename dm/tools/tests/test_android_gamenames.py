"""A game's own name (Home's long press > Rename game, Forgejo #420) on the JVM: javac compiles GameNames (and GameOrder, for the ids) with
android/app/src/jvmtest's GameNamesJvmTest. Also a source check: the options menu offers Rename game (and Reset name when the game has one) and Game.save writes
the player's name through GameNames. Skipped without a JDK (the JVM part)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'android/app/src/main/java/dev/nxnative/android'
TEST = REPO / 'android/app/src/jvmtest/java/dev/nxnative/android/GameNamesJvmTest.java'


@unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK')
class GameNamesJvm(unittest.TestCase):
    def test_names(self):
        tmp = Path(tempfile.mkdtemp(prefix='gamenames_'))
        try:
            r = subprocess.run(['javac', '-Xlint:all', '-Werror', '-d', str(tmp), str(SRC / 'GameNames.java'), str(SRC / 'GameOrder.java'), str(TEST)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run(['java', '-cp', str(tmp), 'dev.nxnative.android.GameNamesJvmTest'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r'^ok \d+')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class GameNamesSource(unittest.TestCase):
    def test_menu_and_save(self):
        main = (SRC / 'MainActivity.java').read_text()
        menu = main[main.index('private void optionsMenu(Game g)'):]
        menu = menu[:menu.index('// ---- Move')]
        for key in ('home_rename_game', 'home_reset_name'):
            self.assertIn('R.string.' + key, menu)
        game = (SRC / 'Game.java').read_text()
        save = game[game.index('static void save(Context c'):]
        self.assertIn('GameNames.apply', save[:save.index('// ---- One entry')])
